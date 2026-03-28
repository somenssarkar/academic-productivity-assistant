from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

from ..prompts.docs_agent_prompt import DOCS_AGENT_INSTRUCTION

MODEL = "gemini-2.5-flash"

_workspace_mcp = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://localhost:3000/mcp",
    ),
    tool_filter=["docs_create_document", "docs_append_text", "docs_get_document",
                 "drive_create_folder", "drive_list_files"],
)

docs_agent = LlmAgent(
    name="docs_agent",
    model=MODEL,
    instruction=DOCS_AGENT_INSTRUCTION,
    tools=[_workspace_mcp],
    description=(
        "Creates and updates Google Docs study notes per chapter. "
        "Organizes files in Drive: EduFlow/{Subject}/Grade {N}/."
    ),
    output_key="doc_url",
)
