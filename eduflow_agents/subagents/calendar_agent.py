from datetime import date
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.calendar_agent_prompt import CALENDAR_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band
from ..tools.workspace import create_calendar_event, update_calendar_event

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject student profile so agent uses correct email and grade band scheduling."""
    student_email = context.state.get("user:email", "")
    student_name = context.state.get("user:name", "Student")
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    session_topic = context.state.get("session_topic", "")

    header = f"## Active Student Context\n"
    header += f"- Name: {student_name}\n"
    header += f"- Email: {student_email}\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    if session_topic:
        header += f"- Current Topic: {session_topic}\n"

    today = date.today().isoformat()
    header += f"- Today's Date: {today}\n"

    return CALENDAR_AGENT_INSTRUCTION + f"\n\n{header}"


calendar_agent = LlmAgent(
    name="calendar_agent",
    model=MODEL,
    instruction=_build_instruction,
    tools=[create_calendar_event, update_calendar_event],
    description=(
        "Creates and manages Google Calendar events for study sessions. "
        "Stores calendar_event_id for each session."
    ),
    output_key="calendar_events",
)
