from datetime import date, timedelta

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.agent_tool import AgentTool

from .prompts.orchestrator_prompt import ORCHESTRATOR_INSTRUCTION
from .tools.curriculum_loader import get_grade_band
from .tools.profile_tool import set_user_profile
from .subagents.curriculum_planner import curriculum_planner_agent
from .subagents.content_agent import content_agent
from .subagents.plan_saver_agent import plan_saver_agent
from .subagents.calendar_agent import calendar_agent
from .subagents.email_agent import email_agent, make_email_agent
from .subagents.docs_agent import docs_agent
from .subagents.tutor_agent import tutor_agent
from .subagents.assessment_agent import assessment_agent
from .subagents.response_formatter import make_response_formatter

MODEL = "gemini-2.5-pro"


def _build_orchestrator_instruction(context: ReadonlyContext) -> str:
    """Inject student profile and latest tutor lesson into orchestrator prompt."""
    name = context.state.get("user:name", "")
    email = context.state.get("user:email", "")
    parent_email = context.state.get("user:parent_email", "")
    grade_level = context.state.get("user:grade_level", "")
    language = context.state.get("user:preferred_language", "")
    grade_band = context.state.get("user:grade_band", "")
    formatted_response = context.state.get("formatted_response", "")
    notes_saved_topics = context.state.get("notes_saved_topics", [])
    curriculum_plan = context.state.get("curriculum_plan", "")
    session_videos = context.state.get("session_videos", "")

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

    # Inject topics already saved to Google Docs so orchestrator can skip duplicates.
    notes_section = (
        f"\n\n## Topics Already Saved to Google Docs\n"
        f"notes_saved_topics = {notes_saved_topics}\n"
        "Before calling notes_pipeline after tutoring, check if the current topic is "
        "already in this list. If it IS — skip notes_pipeline entirely. "
        "If it is NOT — call notes_pipeline, then call "
        "set_user_profile(notes_saved=<current_topic>) to mark it as saved."
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

    # Inject today's date and replace example placeholders in the static prompt.
    today = date.today()
    day1 = f"{today.strftime('%b')} {today.day}"
    day2 = f"{(today + timedelta(days=1)).strftime('%b')} {(today + timedelta(days=1)).day}"
    base_instruction = (
        ORCHESTRATOR_INSTRUCTION
        .replace("DATE_EXAMPLE_1", day1)
        .replace("DATE_EXAMPLE_2", day2)
    )
    date_section = (
        f"\n\n## Today's Date — USE FOR ALL SESSION DATES\n"
        f"Today is **{today.strftime('%A, %B %d, %Y')}** (ISO: {today.isoformat()}).\n"
        f"Session 1 = {day1}, Session 2 = {day2}, and so on (+1 day per session).\n"
        f"NEVER use past dates. NEVER use the placeholder text DATE_EXAMPLE_1 / DATE_EXAMPLE_2 literally."
    )

    # Inject real curriculum plan + video URLs so the orchestrator uses them verbatim
    # instead of reconstructing from memory (which causes hallucinated/wrong URLs in UI).
    plan_section = ""
    if curriculum_plan or session_videos:
        plan_section = "\n\n## Plan Data — USE VERBATIM (do NOT reconstruct from memory)\n"
        if curriculum_plan:
            plan_section += (
                "### Curriculum Plan\n"
                f"{curriculum_plan}\n\n"
            )
        if session_videos:
            plan_section += (
                "### Session Videos — REAL URLs from YouTube API\n"
                "These URLs were verified by the YouTube API. Copy them EXACTLY into "
                "the plan table and any response — do NOT alter, shorten, or invent URLs.\n\n"
                f"{session_videos}\n"
            )
        plan_section += (
            "\nWhen building the plan table: use topic_title from Curriculum Plan "
            "and url from Session Videos matching by session_number. Copy both exactly."
        )

    return base_instruction + profile_section + notes_section + lesson_section + plan_section + date_section


# ---------------------------------------------------------------------------
# Pipelines (SequentialAgent — run silently, only orchestrator output is shown)
# ---------------------------------------------------------------------------

planning_pipeline = SequentialAgent(
    name="planning_pipeline",
    description=(
        "Plans a complete learning schedule: reads YAML curriculum, "
        "determines sessions, finds YouTube videos per topic, "
        "and persists the plan to the database."
    ),
    sub_agents=[curriculum_planner_agent, content_agent, plan_saver_agent],
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

report_pipeline = SequentialAgent(
    name="report_pipeline",
    description=(
        "Sends a progress report email to student and parent after an assessment is complete. "
        "Reads assessment_result from state and emails score, weak areas, and study notes link."
    ),
    sub_agents=[make_email_agent("report_email_agent")],
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
        AgentTool(agent=report_pipeline),
    ],
    description=(
        "EduFlow orchestrator — understands student intent, coordinates multi-agent "
        "workflows for planning, scheduling, tutoring, notes, and assessment."
    ),
)
