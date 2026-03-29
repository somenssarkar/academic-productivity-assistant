from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool

from .prompts.orchestrator_prompt import ORCHESTRATOR_INSTRUCTION
from .tools.profile_tool import set_user_profile
from .subagents.curriculum_planner import curriculum_planner_agent
from .subagents.content_agent import content_agent
from .subagents.calendar_agent import calendar_agent
from .subagents.tasks_agent import tasks_agent
from .subagents.email_agent import email_agent
from .subagents.docs_agent import docs_agent
from .subagents.tutor_agent import tutor_agent
from .subagents.assessment_agent import assessment_agent
from .subagents.response_formatter import make_response_formatter

MODEL = "gemini-2.5-flash"

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
        "Handles all scheduling and communication: creates Google Calendar events, "
        "Google Tasks list, and sends emails to student + parent."
    ),
    sub_agents=[calendar_agent, tasks_agent, email_agent],
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
    instruction=ORCHESTRATOR_INSTRUCTION,
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
