from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.content_agent_prompt import CONTENT_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band
from ..tools.youtube_search import youtube_search

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject active grade band so the agent applies the right search modifiers."""
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)

    header = f"## Active Context\nGrade Band: {grade_band}\n"
    return CONTENT_AGENT_INSTRUCTION + f"\n\n{header}"


content_agent = LlmAgent(
    name="content_agent",
    model=MODEL,
    instruction=_build_instruction,
    tools=[youtube_search],
    description=(
        "Finds YouTube educational videos for each study session topic "
        "and generates session summaries."
    ),
    output_key="session_videos",
)
