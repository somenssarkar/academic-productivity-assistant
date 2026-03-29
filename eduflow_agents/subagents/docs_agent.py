from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.docs_agent_prompt import DOCS_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band
from ..tools.workspace import create_study_notes_doc, append_to_doc, get_or_create_folder

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject student context, existing doc/folder IDs, and session topic."""
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    session_topic = context.state.get("session_topic", "")
    doc_url = context.state.get("doc_url", "")
    drive_folder_id = context.state.get("drive_folder_id", "")
    formatted_response = context.state.get("formatted_response", "")

    header = f"## Active Student Context\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    if session_topic:
        header += f"- Current Topic: {session_topic}\n"
    if doc_url:
        header += f"- Existing Study Notes Doc: {doc_url}\n"
    if drive_folder_id:
        header += f"- Existing Drive Folder ID: {drive_folder_id}\n"
    if formatted_response:
        # Truncate to avoid token bloat — first 500 chars of tutor response for notes
        preview = formatted_response[:500] + ("..." if len(formatted_response) > 500 else "")
        header += f"\n## Tutor Session Content (for appending to notes)\n{preview}\n"

    return DOCS_AGENT_INSTRUCTION + f"\n\n{header}"


docs_agent = LlmAgent(
    name="docs_agent",
    model=MODEL,
    instruction=_build_instruction,
    tools=[create_study_notes_doc, append_to_doc, get_or_create_folder],
    description=(
        "Creates and updates Google Docs study notes per chapter. "
        "Organizes files in Drive: EduFlow/{Subject}/Grade {N}/."
    ),
    output_key="doc_url",
)
