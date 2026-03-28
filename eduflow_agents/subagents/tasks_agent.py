from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

from ..prompts.tasks_agent_prompt import TASKS_AGENT_INSTRUCTION

MODEL = "gemini-2.5-flash"

_workspace_mcp = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://localhost:3000/mcp",
    ),
    tool_filter=["tasks_create_list", "tasks_create_task",
                 "tasks_update_task", "tasks_list_tasks"],
)

tasks_agent = LlmAgent(
    name="tasks_agent",
    model=MODEL,
    instruction=TASKS_AGENT_INSTRUCTION,
    tools=[_workspace_mcp],
    description=(
        "Creates Google Tasks lists and tasks per study session. "
        "Marks tasks complete as sessions finish."
    ),
    output_key="task_list_id",
)
