from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.docs_agent_prompt import DOCS_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band
from ..tools.workspace import create_study_notes_doc, append_session_to_doc, append_to_doc, get_or_create_folder, share_file_with_student

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Detect MODE A (plan-time overview) or MODE B (post-tutor append) and inject
    all relevant state so the agent has everything it needs without guessing."""
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    student_email = context.state.get("user:email", "")
    session_topic = context.state.get("session_topic", "")
    doc_url = context.state.get("doc_url", "")
    drive_folder_id = context.state.get("drive_folder_id", "")
    formatted_response = context.state.get("formatted_response", "")
    curriculum_plan = context.state.get("curriculum_plan", "")
    session_videos = context.state.get("session_videos", "")

    # Determine mode using doc_url as the primary signal.
    # doc_url present = doc already exists = NEVER create a new one.
    # doc_url absent  = doc not yet created = MODE A.
    if not doc_url:
        mode = "A"
        mode_instruction = (
            "MODE A — no doc exists yet. Create the chapter overview doc now. "
            "Follow MODE A steps in full."
        )
    elif formatted_response:
        mode = "B"
        mode_instruction = (
            f"MODE B — doc already exists at {doc_url}. "
            "Append the tutor session notes to it using append_to_doc. "
            "Do NOT call create_study_notes_doc — that would create a duplicate."
        )
    else:
        # doc_url exists but no tutor notes to append (e.g. called without tutoring).
        # Just return the existing URL — do nothing.
        mode = "B_IDLE"
        mode_instruction = (
            f"MODE B-IDLE — doc already exists at {doc_url}. "
            "No tutor notes to append right now. "
            "Do NOT create a new doc. Return the existing doc URL immediately."
        )

    header = f"## Active Student Context\n"
    header += f"- Mode: {mode_instruction}\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    if student_email:
        header += f"- Student Email: {student_email} (share the doc with this email after creating)\n"
    if session_topic:
        header += f"- Current Topic: {session_topic}\n"
    if drive_folder_id:
        header += f"- Existing Drive Folder ID: {drive_folder_id}\n"

    plan_section = ""
    if curriculum_plan:
        plan_section = (
            f"\n\n## Curriculum Plan — one doc section per session\n"
            f"Copy topic_title and concepts VERBATIM. Do not rename or paraphrase.\n\n"
            f"{curriculum_plan}"
        )

    videos_section = ""
    if session_videos:
        videos_section = (
            f"\n\n## Session Videos (REAL URLs — embed exactly as shown, never invent)\n"
            f"{session_videos}"
        )

    tutor_section = ""
    if formatted_response:
        tutor_section = (
            f"\n\n## Tutor Session Content (MODE B — append the FULL content below to the doc)\n"
            f"{formatted_response}\n"
        )

    return DOCS_AGENT_INSTRUCTION + f"\n\n{header}" + plan_section + videos_section + tutor_section


docs_agent = LlmAgent(
    name="docs_agent",
    model=MODEL,
    instruction=_build_instruction,
    tools=[create_study_notes_doc, append_session_to_doc, append_to_doc, get_or_create_folder, share_file_with_student],
    description=(
        "Creates and updates Google Docs study notes per chapter. "
        "Organizes files in Drive: EduFlow/{Subject}/Grade {N}/."
    ),
    output_key="doc_url",
)
