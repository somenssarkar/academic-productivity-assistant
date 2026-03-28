from google.adk.agents import LlmAgent

from ..prompts.tasks_agent_prompt import TASKS_AGENT_INSTRUCTION
from ..tools.workspace import create_task_list, create_task, complete_task

MODEL = "gemini-2.5-flash"

tasks_agent = LlmAgent(
    name="tasks_agent",
    model=MODEL,
    instruction=TASKS_AGENT_INSTRUCTION,
    tools=[create_task_list, create_task, complete_task],
    description=(
        "Creates Google Tasks lists and tasks per study session. "
        "Marks tasks complete as sessions finish."
    ),
    output_key="task_list_id",
)
