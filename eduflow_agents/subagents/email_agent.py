from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

from ..prompts.email_agent_prompt import EMAIL_AGENT_INSTRUCTION

MODEL = "gemini-2.5-flash"

_workspace_mcp = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://localhost:3000/mcp",
    ),
    tool_filter=["gmail_send_email", "gmail_reply", "gmail_search"],
)

email_agent = LlmAgent(
    name="email_agent",
    model=MODEL,
    instruction=EMAIL_AGENT_INSTRUCTION,
    tools=[_workspace_mcp],
    description=(
        "Sends learning plan emails to student + parent. "
        "Sends progress reports after assessments."
    ),
    output_key="email_sent",
)
