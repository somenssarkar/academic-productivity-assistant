from google.adk.agents import LlmAgent

from ..prompts.email_agent_prompt import EMAIL_AGENT_INSTRUCTION
from ..tools.workspace import send_email

MODEL = "gemini-2.5-flash"

email_agent = LlmAgent(
    name="email_agent",
    model=MODEL,
    instruction=EMAIL_AGENT_INSTRUCTION,
    tools=[send_email],
    description=(
        "Sends learning plan emails to student + parent. "
        "Sends progress reports after assessments."
    ),
    output_key="email_sent",
)
