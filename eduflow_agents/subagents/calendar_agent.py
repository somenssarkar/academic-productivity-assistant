import os
from datetime import date
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.calendar_agent_prompt import CALENDAR_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band
from ..tools.workspace import create_calendar_event, update_calendar_event

MODEL = "gemini-2.5-pro"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject student profile, curriculum plan, session videos, and backend URL
    so the agent can create event descriptions with real video links."""
    student_email = context.state.get("user:email", "")
    student_name = context.state.get("user:name", "Student")
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    session_topic = context.state.get("session_topic", "")
    curriculum_plan = context.state.get("curriculum_plan", "")
    session_videos = context.state.get("session_videos", "")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:8501")

    today = date.today().isoformat()

    header = f"## Active Student Context\n"
    header += f"- Name: {student_name}\n"
    header += f"- Email: {student_email}\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    header += f"- Today's Date: {today}\n"
    if session_topic:
        header += f"- Current Topic: {session_topic}\n"
    header += f"- EduFlow App URL: {frontend_url}\n"

    plan_section = ""
    if curriculum_plan:
        plan_section = (
            f"\n\n## Curriculum Plan — Create a Calendar Event for Each Session\n"
            f"Use the session dates and durations from this plan.\n\n"
            f"{curriculum_plan}"
        )

    videos_section = ""
    if session_videos:
        videos_section = (
            f"\n\n## Session Videos (REAL URLs from YouTube API — use EXACTLY as shown)\n"
            f"Use the `url` for the matching session_number in the event description Video field. "
            f"Do NOT invent or modify these URLs.\n\n"
            f"{session_videos}"
        )
    else:
        videos_section = (
            "\n\n## Session Videos\n"
            "No session_videos in state. Omit the Video line from event descriptions — "
            "do NOT invent YouTube URLs."
        )

    return CALENDAR_AGENT_INSTRUCTION + f"\n\n{header}" + plan_section + videos_section


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
