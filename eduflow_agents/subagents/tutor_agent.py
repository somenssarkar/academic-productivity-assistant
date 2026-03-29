from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.code_executors import BuiltInCodeExecutor

from ..prompts.tutor_agent_prompt import TUTOR_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject active grade band and current topic into tutor instruction."""
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    session_topic = context.state.get("session_topic", "the current topic")
    student_name = context.state.get("user:name", "")

    header = f"## Active Session\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    header += f"- Topic: {session_topic}\n"
    if student_name:
        header += f"- Student: {student_name}\n"

    return TUTOR_AGENT_INSTRUCTION + f"\n\n{header}"


# NOTE: code_executor cannot coexist with MCP/function tools in the same agent.
tutor_agent = LlmAgent(
    name="tutor_agent",
    model=MODEL,
    instruction=_build_instruction,
    code_executor=BuiltInCodeExecutor(),
    description=(
        "Grade-aware math and physics tutor. Explains concepts using the "
        "HOOK→EXPLAIN→EXAMPLE→SPARK structure. Uses code execution for "
        "math verification and physics simulations."
    ),
    output_key="tutor_solution",
)
