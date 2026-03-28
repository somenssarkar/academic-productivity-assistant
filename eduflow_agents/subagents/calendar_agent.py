from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

from ..prompts.calendar_agent_prompt import CALENDAR_AGENT_INSTRUCTION

MODEL = "gemini-2.5-flash"

# Google Workspace MCP — Calendar only
# gws mcp must be running: gws mcp -s calendar,tasks,gmail,docs,drive
_workspace_mcp = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://localhost:3000/mcp",  # gws mcp default port
    ),
    # Filter to Calendar tools only — other agents get their own MCPToolset
    tool_filter=["calendar_create_event", "calendar_list_events",
                 "calendar_update_event", "calendar_delete_event"],
)

calendar_agent = LlmAgent(
    name="calendar_agent",
    model=MODEL,
    instruction=CALENDAR_AGENT_INSTRUCTION,
    tools=[_workspace_mcp],
    description=(
        "Creates and manages Google Calendar events for study sessions. "
        "Stores calendar_event_id for each session."
    ),
    output_key="calendar_events",
)
