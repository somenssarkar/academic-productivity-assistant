from google.adk.agents import LlmAgent

from ..prompts.calendar_agent_prompt import CALENDAR_AGENT_INSTRUCTION
from ..tools.workspace import create_calendar_event, update_calendar_event

MODEL = "gemini-2.5-flash"

calendar_agent = LlmAgent(
    name="calendar_agent",
    model=MODEL,
    instruction=CALENDAR_AGENT_INSTRUCTION,
    tools=[create_calendar_event, update_calendar_event],
    description=(
        "Creates and manages Google Calendar events for study sessions. "
        "Stores calendar_event_id for each session."
    ),
    output_key="calendar_events",
)
