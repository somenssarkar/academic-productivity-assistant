from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.agent_tool import AgentTool

from .prompts.orchestrator_prompt import ORCHESTRATOR_INSTRUCTION
from .tools.curriculum_loader import get_grade_band
from .tools.profile_tool import set_user_profile
from .subagents.curriculum_planner import curriculum_planner_agent
from .subagents.content_agent import content_agent
from .subagents.calendar_agent import calendar_agent
from .subagents.email_agent import email_agent
from .subagents.docs_agent import docs_agent
from .subagents.tutor_agent import tutor_agent
from .subagents.assessment_agent import assessment_agent
from .subagents.response_formatter import make_response_formatter

MODEL = "gemini-2.5-flash"


def _build_orchestrator_instruction(context: ReadonlyContext) -> str:
    """Inject student profile and latest tutor lesson into orchestrator prompt."""
    name = context.state.get("user:name", "")
    email = context.state.get("user:email", "")
    parent_email = context.state.get("user:parent_email", "")
    grade_level = context.state.get("user:grade_level", "")
    language = context.state.get("user:preferred_language", "")
    grade_band = context.state.get("user:grade_band", "")
    formatted_response = context.state.get("formatted_response", "")

    if grade_level and not grade_band:
        grade_band = get_grade_band(grade_level)

    profile_lines = []
    if name:
        profile_lines.append(f"- Name: {name}")
    if email:
        profile_lines.append(f"- Email: {email}")
    if parent_email:
        profile_lines.append(f"- Parent Email: {parent_email}")
    if grade_level:
        profile_lines.append(f"- Grade: {grade_level} (Band: {grade_band})")
    if language:
        profile_lines.append(f"- Language: {language}")

    if profile_lines:
        profile_section = (
            "\n\n## Known Student Profile (already in state — DO NOT ask for these)\n"
            + "\n".join(profile_lines)
        )
    else:
        profile_section = (
            "\n\n## Known Student Profile\n"
            "No profile saved yet. Ask for grade first, then proceed."
        )

    # Inject the formatted lesson so the orchestrator can reproduce it verbatim.
    # This is set by response_formatter after every tutoring_pipeline call.
    lesson_section = ""
    if formatted_response:
        lesson_section = (
            "\n\n## Latest Tutor Lesson (MUST be shown to student)\n"
            "The tutoring_pipeline just produced this lesson. "
            "Copy it WORD FOR WORD into your response — do not summarise or shorten it:\n\n"
            f"{formatted_response}"
        )

    return ORCHESTRATOR_INSTRUCTION + profile_section + lesson_section


# ---------------------------------------------------------------------------
# Pipelines (SequentialAgent — run silently, only orchestrator output is shown)
# ---------------------------------------------------------------------------

planning_pipeline = SequentialAgent(
    name="planning_pipeline",
    description=(
        "Plans a complete learning schedule: reads YAML curriculum, "
        "determines sessions, finds YouTube videos per topic."
    ),
    sub_agents=[curriculum_planner_agent, content_agent],
)

scheduling_pipeline = SequentialAgent(
    name="scheduling_pipeline",
    description=(
        "Handles all scheduling and communication: creates Google Calendar events "
        "and sends emails to student + parent."
    ),
    sub_agents=[calendar_agent, email_agent],
)

tutoring_pipeline = SequentialAgent(
    name="tutoring_pipeline",
    description=(
        "Delivers a tutoring session: teaches the concept with grade-aware persona "
        "and formats the response for clean display."
    ),
    sub_agents=[tutor_agent, make_response_formatter("tutoring_formatter")],
)

notes_pipeline = SequentialAgent(
    name="notes_pipeline",
    description=(
        "Saves session notes to Google Docs and organizes them in Google Drive."
    ),
    sub_agents=[docs_agent],
)

assessment_pipeline = SequentialAgent(
    name="assessment_pipeline",
    description=(
        "Runs a quiz on the completed topic, evaluates answers, stores scores, "
        "and generates feedback."
    ),
    sub_agents=[assessment_agent],
)

# ---------------------------------------------------------------------------
# Root agent (orchestrator)
# ---------------------------------------------------------------------------

root_agent = LlmAgent(
    name="orchestrator_agent",
    model=MODEL,
    instruction=_build_orchestrator_instruction,
    tools=[
        set_user_profile,
        AgentTool(agent=planning_pipeline),
        AgentTool(agent=scheduling_pipeline),
        AgentTool(agent=tutoring_pipeline),
        AgentTool(agent=notes_pipeline),
        AgentTool(agent=assessment_pipeline),
    ],
    description=(
        "EduFlow orchestrator — understands student intent, coordinates multi-agent "
        "workflows for planning, scheduling, tutoring, notes, and assessment."
    ),
)
