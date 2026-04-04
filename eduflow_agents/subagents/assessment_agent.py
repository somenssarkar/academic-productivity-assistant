import os
import re

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

from ..prompts.assessment_agent_prompt import ASSESSMENT_AGENT_INSTRUCTION
from ..tools.curriculum_loader import (
    load_curriculum,
    get_chapter,
    get_topic,
    get_grade_band,
)

MODEL = "gemini-2.5-pro"

# MCP Toolbox URL — use env var so it works both locally and on Cloud Run
_TOOLBOX_URL = os.environ.get("MCP_TOOLBOX_URL", "http://localhost:5000/mcp")

# Database MCP (MCP Toolbox) — for saving assessment results
_db_mcp = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(url=_TOOLBOX_URL),
    tool_filter=["save-assessment", "update-progress", "get-student-progress"],
)


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject grade band, session topic, and YAML quiz questions into assessment instruction."""
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    session_topic = context.state.get("session_topic", "")
    current_session_id = context.state.get("current_session_id", "")
    user_id = context.state.get("user:id", "")

    match = re.search(r"\d+", str(grade_level))
    grade = int(match.group()) if match else 8

    header = f"## Active Session Context\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    if session_topic:
        header += f"- Topic: {session_topic}\n"
    if current_session_id:
        header += f"- Session ID: {current_session_id}\n"
    if user_id:
        header += f"- User ID: {user_id}\n"

    # Inject YAML questions for the matched topic
    questions_context = ""
    if session_topic:
        try:
            cf = load_curriculum("cbse", "math", grade)
            session_topic_lower = session_topic.lower()
            # Fuzzy match topic across all chapters (case-insensitive)
            matched_topic = None
            for chapter in cf.chapters:
                for topic in chapter.topics:
                    if (session_topic_lower in topic.title.lower()
                            or session_topic_lower in topic.id.lower()
                            or topic.title.lower() in session_topic_lower
                            or topic.id.lower() in session_topic_lower):
                        matched_topic = topic
                        break
                if matched_topic:
                    break

            if matched_topic and matched_topic.questions:
                lines = [f"\n## Quiz Questions for: {matched_topic.title}"]
                for i, q in enumerate(matched_topic.questions, 1):
                    lines.append(f"\nQuestion {i} (difficulty {q.difficulty}):")
                    lines.append(f"  Q: {q.question}")
                    for j, opt in enumerate(q.options):
                        lines.append(f"  {chr(65+j)}) {opt}")
                    lines.append(f"  Answer: {q.answer}")
                    if q.explanation:
                        lines.append(f"  Explanation: {q.explanation}")
                questions_context = "\n".join(lines)
        except Exception as exc:
            questions_context = f"\nCurriculum questions unavailable: {exc}"

    return ASSESSMENT_AGENT_INSTRUCTION + f"\n\n{header}" + questions_context


assessment_agent = LlmAgent(
    name="assessment_agent",
    model=MODEL,
    instruction=_build_instruction,
    tools=[_db_mcp],
    description=(
        "Generates quizzes from YAML curriculum questions, evaluates student answers, "
        "stores scores and weak areas in the database, and provides feedback."
    ),
    output_key="assessment_result",
)
