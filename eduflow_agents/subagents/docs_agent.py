from google.adk.agents import LlmAgent

from ..prompts.docs_agent_prompt import DOCS_AGENT_INSTRUCTION
from ..tools.workspace import create_study_notes_doc, append_to_doc, get_or_create_folder

MODEL = "gemini-2.5-flash"

docs_agent = LlmAgent(
    name="docs_agent",
    model=MODEL,
    instruction=DOCS_AGENT_INSTRUCTION,
    tools=[create_study_notes_doc, append_to_doc, get_or_create_folder],
    description=(
        "Creates and updates Google Docs study notes per chapter. "
        "Organizes files in Drive: EduFlow/{Subject}/Grade {N}/."
    ),
    output_key="doc_url",
)
