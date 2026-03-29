from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.tasks_agent_prompt import TASKS_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band
from ..tools.workspace import create_task_list, create_task, complete_task

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject student profile and session context for task creation."""
    student_name = context.state.get("user:name", "Student")
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    session_topic = context.state.get("session_topic", "")
    task_list_id = context.state.get("task_list_id", "")

    header = f"## Active Student Context\n"
    header += f"- Name: {student_name}\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    if session_topic:
        header += f"- Current Topic: {session_topic}\n"
    if task_list_id:
        header += f"- Existing TaskList ID: {task_list_id}\n"

    return TASKS_AGENT_INSTRUCTION + f"\n\n{header}"


tasks_agent = LlmAgent(
    name="tasks_agent",
    model=MODEL,
    instruction=_build_instruction,
    tools=[create_task_list, create_task, complete_task],
    description=(
        "Creates Google Tasks lists and tasks per study session. "
        "Marks tasks complete as sessions finish."
    ),
    output_key="task_list_id",
)
