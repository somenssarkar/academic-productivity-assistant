from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

from ..prompts.assessment_agent_prompt import ASSESSMENT_AGENT_INSTRUCTION

MODEL = "gemini-2.5-flash"

# Database MCP (MCP Toolbox) — for saving assessment results
_db_mcp = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://localhost:5000/mcp",
    ),
    tool_filter=["save-assessment", "update-progress", "get-student-progress"],
    # toolset: eduflow-tools (defined in mcp_servers/database/tools.yaml)
)

assessment_agent = LlmAgent(
    name="assessment_agent",
    model=MODEL,
    instruction=ASSESSMENT_AGENT_INSTRUCTION,
    tools=[_db_mcp],
    description=(
        "Generates quizzes from YAML curriculum questions, evaluates student answers, "
        "stores scores and weak areas in the database, and provides feedback."
    ),
    output_key="assessment_result",
)
