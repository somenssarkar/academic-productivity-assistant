from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.email_agent_prompt import EMAIL_AGENT_INSTRUCTION
from ..tools.workspace import send_email

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject student and parent contact details so agent uses correct recipients."""
    student_name = context.state.get("user:name", "Student")
    student_email = context.state.get("user:email", "")
    parent_email = context.state.get("user:parent_email", "")
    grade_level = context.state.get("user:grade_level", "Grade 8")
    session_topic = context.state.get("session_topic", "")
    doc_url = context.state.get("doc_url", "")
    assessment_result = context.state.get("assessment_result", "")

    header = f"## Active Student Context\n"
    header += f"- Name: {student_name}\n"
    header += f"- Student Email: {student_email}\n"
    header += f"- Parent Email: {parent_email}\n"
    header += f"- Grade: {grade_level}\n"
    if session_topic:
        header += f"- Current Topic: {session_topic}\n"
    if doc_url:
        header += f"- Study Notes Doc: {doc_url}\n"
    if assessment_result:
        header += f"- Assessment Result: {assessment_result}\n"

    return EMAIL_AGENT_INSTRUCTION + f"\n\n{header}"


email_agent = LlmAgent(
    name="email_agent",
    model=MODEL,
    instruction=_build_instruction,
    tools=[send_email],
    description=(
        "Sends learning plan emails to student + parent. "
        "Sends progress reports after assessments."
    ),
    output_key="email_sent",
)
