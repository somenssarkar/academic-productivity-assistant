from google.adk.agents import LlmAgent

from ..prompts.response_formatter_prompt import RESPONSE_FORMATTER_INSTRUCTION

MODEL = "gemini-2.5-flash"


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
        instruction=RESPONSE_FORMATTER_INSTRUCTION,
        description="Formats the tutor's raw response into clean textbook-style output.",
        # include_contents='none' — formatter only reads tutor_solution from state,
        # does not need the full conversation history.
        include_contents="none",
        output_key="formatted_response",
    )
