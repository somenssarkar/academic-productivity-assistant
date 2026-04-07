import json
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.code_executors import BuiltInCodeExecutor

from ..prompts.tutor_agent_prompt import TUTOR_AGENT_INSTRUCTION
from ..tools.curriculum_loader import get_grade_band

MODEL = "gemini-2.5-pro"


def _build_instruction(context: ReadonlyContext) -> str:
    """Inject grade band, current topic, and YAML concepts into tutor instruction."""
    grade_level = context.state.get("user:grade_level", "Grade 8")
    grade_band = context.state.get("user:grade_band") or get_grade_band(grade_level)
    session_topic = context.state.get("session_topic", "")
    student_name = context.state.get("user:name", "")
    curriculum_plan = context.state.get("curriculum_plan", "")
    language = context.state.get("user:preferred_language", "English")

    header = "## Active Session\n"
    header += f"- Grade: {grade_level} | Band: {grade_band}\n"
    header += f"- Language: {language}\n"
    if student_name:
        header += f"- Student: {student_name}\n"
    if session_topic:
        header += f"- Chapter/Topic: {session_topic}\n"

    # Extract concepts for the requested topic from curriculum_plan in state.
    # curriculum_plan is the JSON string written by curriculum_planner_agent.
    concepts_section = ""
    if curriculum_plan:
        try:
            plan = json.loads(curriculum_plan)
            sessions = plan.get("sessions", [])

            # Find the session whose topic_title best matches session_topic
            matched = None
            topic_lower = session_topic.lower() if session_topic else ""
            for s in sessions:
                if topic_lower and topic_lower in s.get("topic_title", "").lower():
                    matched = s
                    break
            # Fall back to first session if no specific match
            if not matched and sessions:
                matched = sessions[0]

            if matched:
                concepts = matched.get("concepts", [])
                topic_title = matched.get("topic_title", session_topic)
                header += f"- Teaching Topic: {topic_title}\n"
                if concepts:
                    concepts_section = (
                        "\n\n## Concepts to Cover (from YAML curriculum — teach all of these)\n"
                        + "\n".join(f"- {c}" for c in concepts)
                        + "\n\nCover these concepts in sequence using the HOOK→EXPLAIN→EXAMPLE→SPARK "
                        "structure. Do not invent concepts outside this list."
                    )
        except (json.JSONDecodeError, KeyError):
            pass

    return TUTOR_AGENT_INSTRUCTION + f"\n\n{header}" + concepts_section


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
