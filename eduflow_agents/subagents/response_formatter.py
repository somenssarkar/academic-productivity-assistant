from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.response_formatter_prompt import RESPONSE_FORMATTER_INSTRUCTION

MODEL = "gemini-2.5-pro"


def _build_formatter_instruction(context: ReadonlyContext) -> str:
    """Inject tutor_solution from state so the formatter can actually see the content."""
    tutor_solution = context.state.get("tutor_solution", "")

    if tutor_solution:
        content_section = (
            "\n\n## Tutor Response to Format\n"
            "The following is the raw tutor response. Format it exactly as specified above "
            "— do NOT summarise, truncate, or skip any section:\n\n"
            f"{tutor_solution}"
        )
    else:
        content_section = (
            "\n\n## Tutor Response to Format\n"
            "No tutor_solution found in state. Return an empty string."
        )

    return RESPONSE_FORMATTER_INSTRUCTION + content_section


def make_response_formatter(name: str = "response_formatter") -> LlmAgent:
    """Factory that creates a fresh response_formatter instance.

    ADK enforces the one-parent rule: each agent instance can only belong to one
    SequentialAgent. Use this factory whenever you need a formatter in a pipeline
    to avoid re-using the same instance across multiple pipelines.

    Args:
        name: Unique name for this formatter instance.

    Returns:
        A new LlmAgent configured as a response formatter.
    """
    return LlmAgent(
        name=name,
        model=MODEL,
        instruction=_build_formatter_instruction,
        description="Formats the tutor's raw response into clean textbook-style output.",
        # include_contents='none' — formatter only reads tutor_solution injected via
        # _build_formatter_instruction; does not need the full conversation history.
        include_contents="none",
        output_key="formatted_response",
    )
