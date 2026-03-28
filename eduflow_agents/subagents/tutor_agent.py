from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor

from ..prompts.tutor_agent_prompt import TUTOR_AGENT_INSTRUCTION

MODEL = "gemini-2.5-flash"

# NOTE: code_executor cannot coexist with MCP/function tools in the same agent.
# The tutor agent uses ONLY code_executor — no MCP tools.
tutor_agent = LlmAgent(
    name="tutor_agent",
    model=MODEL,
    instruction=TUTOR_AGENT_INSTRUCTION,
    code_executor=BuiltInCodeExecutor(),
    description=(
        "Grade-aware math and physics tutor. Explains concepts using the "
        "HOOK→EXPLAIN→EXAMPLE→SPARK structure. Uses code execution for "
        "math verification and physics simulations."
    ),
    output_key="tutor_solution",
)
