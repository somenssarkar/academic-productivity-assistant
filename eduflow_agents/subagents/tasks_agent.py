from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext

from ..prompts.tasks_agent_prompt import TASKS_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band
from ..tools.workspace import create_task_list, create_task, complete_task

MODEL = "gemini-2.5-flash"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject student profile, curriculum plan, and session videos so the agent
    creates tasks with real YouTube links, not hallucinated ones."""
    student_name = context.state.get("user:name", "Student")
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    session_topic = context.state.get("session_topic", "")
    task_list_id = context.state.get("task_list_id", "")
    curriculum_plan = context.state.get("curriculum_plan", "")
    session_videos = context.state.get("session_videos", "")

    header = f"## Active Student Context\n"
    header += f"- Name: {student_name}\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    if session_topic:
        header += f"- Current Topic: {session_topic}\n"
    if task_list_id:
        header += f"- Existing TaskList ID: {task_list_id}\n"

    plan_section = ""
    if curriculum_plan:
        plan_section = (
            f"\n\n## Curriculum Plan — Create a Task for Each Session\n"
            f"{curriculum_plan}"
        )

    videos_section = ""
    if session_videos:
        videos_section = (
            f"\n\n## Session Videos (REAL URLs — pass to create_task as video_url exactly as shown)\n"
            f"Match session_number to the corresponding task. "
            f"Do NOT invent or modify these URLs.\n\n"
            f"{session_videos}"
        )
    else:
        videos_section = (
            "\n\n## Session Videos\n"
            "No session_videos in state. Omit video_url from task creation — "
            "do NOT invent YouTube URLs."
        )

    return TASKS_AGENT_INSTRUCTION + f"\n\n{header}" + plan_section + videos_section


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
