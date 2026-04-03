from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.content_agent_prompt import CONTENT_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band
from ..tools.youtube_search import youtube_search

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject active grade band and language so the agent applies the right search modifiers."""
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    language = context.state.get("user:preferred_language", "English")

    header = (
        f"## Active Context\n"
        f"Grade Band: {grade_band}\n"
        f"Preferred Language: {language}\n\n"
        f"## Language Rules\n"
        f"- Always append the language name to your search query (e.g. add '{language}' to queries).\n"
        f"- Prefer videos where the title or channel is in {language}.\n"
        f"- If no {language} results exist for a topic, fall back to English.\n"
        f"- NEVER return a video in a language other than {language} or English.\n"
    )
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
