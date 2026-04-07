"""Google Tasks function tools for ADK agents."""

import json
from googleapiclient.discovery import build
from .auth import get_credentials


def create_task_list(title: str) -> str:
    """Create a new Google Tasks list for a learning plan chapter.

    Args:
        title: Task list name (e.g. "📐 Quadratic Equations — Math Grade 8")

    Returns:
        JSON string with task_list_id for storage in AlloyDB.
    """
    try:
        service = build("tasks", "v1", credentials=get_credentials())
        result = service.tasklists().insert(body={"title": title}).execute()
        return json.dumps({
            "task_list_id": result["id"],
            "title": result["title"],
            "status": "created",
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def create_task(
    task_list_id: str,
    title: str,
    notes: str = None,
    due: str = None,
    video_url: str = None,
    video_title: str = None,
) -> str:
    """Create a task within a task list for a study session.

    Args:
        task_list_id: The Google Tasks list ID (from create_task_list)
        title: Task title (e.g. "Session 1: Basics & Standard Form")
        notes: Key concepts and study notes (max 8192 chars)
        due: Due date in RFC 3339 format (e.g. "2026-04-01T00:00:00.000Z")
        video_url: YouTube video URL to attach as a link
        video_title: Display title for the YouTube link

    Returns:
        JSON string with task_id for storage in AlloyDB.
    """
    try:
        service = build("tasks", "v1", credentials=get_credentials())
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
    body = {"title": title, "status": "needsAction"}
    if notes:
        body["notes"] = notes
    if due:
        body["due"] = due
    if video_url:
        body["links"] = [{"type": "related", "description": video_title or "Video tutorial", "link": video_url}]

    try:
        result = service.tasks().insert(tasklist=task_list_id, body=body).execute()
        return json.dumps({
            "task_id": result["id"],
            "title": result["title"],
            "status": "created",
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def complete_task(task_list_id: str, task_id: str) -> str:
    """Mark a study session task as completed.

    Args:
        task_list_id: The Google Tasks list ID
        task_id: The task ID to mark complete (from create_task)

    Returns:
        JSON string confirming completion.
    """
    service = build("tasks", "v1", credentials=get_credentials())
    task = service.tasks().get(tasklist=task_list_id, task=task_id).execute()
    task["status"] = "completed"
    result = service.tasks().update(
        tasklist=task_list_id, task=task_id, body=task
    ).execute()
    return json.dumps({
        "task_id": result["id"],
        "status": "completed",
    })
