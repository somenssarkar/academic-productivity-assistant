from google.adk.agents import LlmAgent

from ..prompts.curriculum_planner_prompt import CURRICULUM_PLANNER_INSTRUCTION

MODEL = "gemini-2.5-flash"

curriculum_planner_agent = LlmAgent(
    name="curriculum_planner_agent",
    model=MODEL,
    instruction=CURRICULUM_PLANNER_INSTRUCTION,
    description=(
        "Plans a structured multi-session learning schedule from YAML curriculum data. "
        "Determines session count, duration, and topic sequencing."
    ),
    output_key="curriculum_plan",
)
