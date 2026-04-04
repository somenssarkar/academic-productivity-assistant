from google.adk.tools import ToolContext

from .curriculum_loader import get_grade_band


def set_user_profile(
    tool_context: ToolContext,
    name: str = "",
    email: str = "",
    parent_email: str = "",
    grade_level: str = "",
    preferred_language: str = "",
    session_topic: str = "",
) -> dict:
    """Save student profile fields and/or the current session topic to state.

    Call this as soon as any profile detail is known from conversation
    (e.g. student mentions their grade). Also call it BEFORE planning_pipeline
    to set session_topic so the curriculum planner can match the right chapter.

    Args:
        name: Student's first name or full name.
        email: Student's Google account email (used for Calendar, Tasks, Docs).
        parent_email: Parent's email address for progress reports.
        grade_level: Grade as a string, e.g. "Grade 8" or "Grade 10".
        preferred_language: Response language, e.g. "English", "Hindi".
        session_topic: The chapter or topic the student wants to learn,
            extracted from their message (e.g. "Exponents", "Quadratic Equations").
            This helps the curriculum planner find the right chapter in the YAML.

    Returns:
        Dict confirming which fields were saved.
    """
    saved = {}

    if name:
        tool_context.state["user:name"] = name
        saved["name"] = name

    if email:
        tool_context.state["user:email"] = email
        saved["email"] = email

    if parent_email:
        tool_context.state["user:parent_email"] = parent_email
        saved["parent_email"] = parent_email

    if grade_level:
        tool_context.state["user:grade_level"] = grade_level
        grade_band = get_grade_band(grade_level)
        tool_context.state["user:grade_band"] = grade_band
        saved["grade_level"] = grade_level
        saved["grade_band"] = grade_band

    if preferred_language:
        tool_context.state["user:preferred_language"] = preferred_language
        saved["preferred_language"] = preferred_language

    if session_topic:
        # Session-scoped (no user: prefix) — used by curriculum_planner to match chapter
        tool_context.state["session_topic"] = session_topic
        saved["session_topic"] = session_topic

    return {"saved": saved, "status": "profile updated"}
