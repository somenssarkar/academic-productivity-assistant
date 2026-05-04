import os
import re

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.adk.tools.tool_context import ToolContext

from ..prompts.assessment_agent_prompt import ASSESSMENT_AGENT_INSTRUCTION
from ..tools.curriculum_loader import (
    load_curriculum,
    get_chapter,
    get_topic,
    get_grade_band,
)

MODEL = "gemini-2.5-flash-lite"

# MCP Toolbox URL — use env var so it works both locally and on Cloud Run
_TOOLBOX_URL = os.environ.get("MCP_TOOLBOX_URL", "http://localhost:5000/mcp")

# Database MCP (MCP Toolbox) — for saving assessment results
_db_mcp = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(url=_TOOLBOX_URL),
    tool_filter=["save-assessment", "update-progress", "get-student-progress"],
)


def update_quiz_state(next_q: int, tool_context: ToolContext) -> str:
    """Track quiz position in session state.

    Call with next_q=N immediately after showing Question N.
    Call with next_q=0 after the quiz ends to reset for the next quiz.
    """
    tool_context.state["quiz_next_q"] = next_q
    return f"quiz_next_q set to {next_q}"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject grade band, session topic, quiz position, and YAML quiz questions."""
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    session_topic = context.state.get("session_topic", "")
    current_session_id = context.state.get("current_session_id", "")
    user_id = context.state.get("user:id", "")
    quiz_next_q = context.state.get("quiz_next_q", 0)

    match = re.search(r"\d+", str(grade_level))
    grade = int(match.group()) if match else 8

    header = "## Active Session Context\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    if session_topic:
        header += f"- Topic: {session_topic}\n"
    if current_session_id:
        header += f"- Session ID: {current_session_id}\n"
    if user_id:
        header += f"- User ID: {user_id}\n"
    header += f"- Quiz Position: {quiz_next_q}\n"

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
                # Questions shown to student — NO answers here to prevent self-answering
                lines = [f"\n## Quiz Questions for: {matched_topic.title}"]
                lines.append(f"Total questions: {len(matched_topic.questions)}")
                for i, q in enumerate(matched_topic.questions, 1):
                    lines.append(f"\nQuestion {i} (difficulty {q.difficulty}):")
                    lines.append(f"  Q: {q.question}")
                    for j, opt in enumerate(q.options):
                        lines.append(f"  {chr(65+j)}) {opt}")

                # Answers in a clearly separated section — for evaluation only after student answers
                lines.append(
                    "\n## Evaluation Key — NEVER reveal to student, "
                    "ONLY use AFTER student submits an answer"
                )
                for i, q in enumerate(matched_topic.questions, 1):
                    lines.append(f"  Q{i} correct answer: {q.answer}")
                    if q.explanation:
                        lines.append(f"  Q{i} explanation: {q.explanation}")
                questions_context = "\n".join(lines)
        except Exception as exc:
            questions_context = f"\nCurriculum questions unavailable: {exc}"

    return ASSESSMENT_AGENT_INSTRUCTION + f"\n\n{header}" + questions_context


assessment_agent = LlmAgent(
    name="assessment_agent",
    model=MODEL,
    instruction=_build_instruction,
    tools=[_db_mcp, update_quiz_state],
    description=(
        "Generates quizzes from YAML curriculum questions, evaluates student answers, "
        "stores scores and weak areas in the database, and provides feedback."
    ),
    output_key="assessment_result",
)
