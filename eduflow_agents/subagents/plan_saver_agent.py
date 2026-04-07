"""Plan Saver Agent — persists learning plans and sessions to Cloud SQL via MCP Toolbox."""

import os
from datetime import date
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

from ..prompts.plan_saver_prompt import PLAN_SAVER_INSTRUCTION

MODEL = "gemini-2.5-flash-lite"

# MCP Toolbox URL — use env var so it works both locally and on Cloud Run
_TOOLBOX_URL = os.environ.get("MCP_TOOLBOX_URL", "http://localhost:5000/mcp")

_db_mcp = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(url=_TOOLBOX_URL),
    tool_filter=["save-learning-plan", "save-study-session"],
)


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject user_id, curriculum_plan, and session_videos so the agent
    has everything it needs to persist the plan to the database."""
    user_id = context.state.get("user:id", "")
    curriculum_plan = context.state.get("curriculum_plan", "")
    session_videos = context.state.get("session_videos", "")
    today = date.today().isoformat()

    header = (
        f"## Active Context\n"
        f"- User ID: {user_id}\n"
        f"- Today's Date: {today}\n"
    )

    plan_section = (
        f"\n\n## Curriculum Plan JSON (save this to the database)\n"
        f"{curriculum_plan}"
    ) if curriculum_plan else "\n\n## Curriculum Plan\nNo curriculum_plan in state — output 'no-plan' and stop."

    videos_section = (
        f"\n\n## Session Videos (use url and title fields per session_number)\n"
        f"{session_videos}"
    ) if session_videos else ""

    return PLAN_SAVER_INSTRUCTION + f"\n\n{header}" + plan_section + videos_section


plan_saver_agent = LlmAgent(
    name="plan_saver_agent",
    model=MODEL,
    instruction=_build_instruction,
    tools=[_db_mcp],
    description=(
        "Persists the generated learning plan and each study session to "
        "Cloud SQL via MCP Toolbox. Sets current_plan_id in session state."
    ),
    output_key="current_plan_id",
)
