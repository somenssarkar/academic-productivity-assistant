import re
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.curriculum_planner_prompt import CURRICULUM_PLANNER_INSTRUCTION
from ..tools.curriculum_loader import (
    load_curriculum,
    curriculum_to_context_string,
    curriculum_to_toc_string,
    get_grade_band,
)

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Dynamically inject the relevant YAML chapter into the planner's instruction.

    Strategy:
    - Read user:grade_level from state → derive grade number
    - Read session_topic from state → fuzzy-match to a chapter ID
    - If chapter matched: inject full chapter data (~400 tokens)
    - If not matched: inject TOC only (~200 tokens) so planner can identify chapter
    """
    grade_level = context.state.get("user:grade_level", "Grade 8")
    match = re.search(r"\d+", str(grade_level))
    grade = int(match.group()) if match else 8

    session_topic = str(context.state.get("session_topic", "")).lower().strip()

    try:
        cf = load_curriculum("cbse", "math", grade)

        # Fuzzy match: topic string against chapter title or id
        chapter_id = None
        if session_topic:
            for chapter in cf.chapters:
                if (session_topic in chapter.title.lower()
                        or session_topic in chapter.id.lower()
                        or chapter.title.lower() in session_topic
                        or chapter.id.lower() in session_topic):
                    chapter_id = chapter.id
                    break

        if chapter_id:
            curriculum_context = curriculum_to_context_string(cf, chapter_id=chapter_id)
        else:
            # No match yet — inject TOC so planner can identify the right chapter
            # from the student's message
            curriculum_context = curriculum_to_toc_string(cf)

    except Exception as exc:
        curriculum_context = f"Curriculum data unavailable: {exc}"

    grade_band = get_grade_band(grade_level)

    return (
        CURRICULUM_PLANNER_INSTRUCTION
        + f"\n\n## Student Context\nGrade: {grade} | Grade Band: {grade_band}\n"
        + f"\n## Curriculum Data\n{curriculum_context}"
    )


curriculum_planner_agent = LlmAgent(
    name="curriculum_planner_agent",
    model=MODEL,
    instruction=_build_instruction,
    description=(
        "Plans a structured multi-session learning schedule from YAML curriculum data. "
        "Determines session count, duration, and topic sequencing."
    ),
    output_key="curriculum_plan",
)
