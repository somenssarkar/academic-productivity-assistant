from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.content_agent_prompt import CONTENT_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band
from ..tools.youtube_search import youtube_search

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject grade band, language, and the curriculum plan so the agent knows
    exactly which topics to search for and which youtube_search_hints to use."""
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    language = context.state.get("user:preferred_language", "English")
    curriculum_plan = context.state.get("curriculum_plan", "")

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

    plan_section = ""
    if curriculum_plan:
        plan_section = (
            f"\n\n## Curriculum Plan — Search a Video for Each Session\n"
            f"The following plan was produced by the curriculum planner. "
            f"For EVERY session listed, you MUST call `youtube_search` using the "
            f"`youtube_search_hint` as your query (with grade-band modifier and language appended). "
            f"Copy the returned `url` value exactly — do NOT invent URLs.\n\n"
            f"{curriculum_plan}"
        )
    else:
        plan_section = (
            "\n\n## No Curriculum Plan Found\n"
            "No curriculum_plan is in session state. Ask the orchestrator to run "
            "curriculum_planner_agent first before calling this agent."
        )

    return CONTENT_AGENT_INSTRUCTION + f"\n\n{header}" + plan_section


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
