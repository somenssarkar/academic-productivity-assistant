"""Google Calendar function tools for ADK agents."""

import json
from googleapiclient.discovery import build
from .auth import get_credentials


def create_calendar_event(
    summary: str,
    description: str,
    start_datetime: str,
    end_datetime: str,
    timezone: str = "Asia/Kolkata",
) -> str:
    """Create a Google Calendar event for a study session.

    Args:
        summary: Event title (e.g. "Session 1: Quadratic Equations — Basics")
        description: Event body — topic overview, YouTube link, key concepts
        start_datetime: ISO 8601 start time (e.g. "2026-04-01T10:00:00")
        end_datetime: ISO 8601 end time (e.g. "2026-04-01T10:45:00")
        timezone: IANA timezone string (default "Asia/Kolkata")

    Returns:
        JSON string with event_id and event_link for storage in AlloyDB.
    """
    service = build("calendar", "v3", credentials=get_credentials())
    event = service.events().insert(
        calendarId="primary",
        body={
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_datetime, "timeZone": timezone},
            "end": {"dateTime": end_datetime, "timeZone": timezone},
        },
    ).execute()
    return json.dumps({
        "event_id": event["id"],
        "event_link": event.get("htmlLink", ""),
        "status": "created",
    })


def update_calendar_event(
    event_id: str,
    summary: str = None,
    description: str = None,
    start_datetime: str = None,
    end_datetime: str = None,
    timezone: str = "Asia/Kolkata",
) -> str:
    """Update an existing Google Calendar event.

    Args:
        event_id: The Calendar event ID (stored in AlloyDB study_sessions table)
        summary: New title (optional)
        description: New description (optional)
        start_datetime: New ISO 8601 start time (optional)
        end_datetime: New ISO 8601 end time (optional)
        timezone: IANA timezone string (default "Asia/Kolkata")

    Returns:
        JSON string confirming update with event_id.
    """
    service = build("calendar", "v3", credentials=get_credentials())
    event = service.events().get(calendarId="primary", eventId=event_id).execute()

    if summary:
        event["summary"] = summary
    if description:
        event["description"] = description
    if start_datetime:
        event["start"] = {"dateTime": start_datetime, "timeZone": timezone}
    if end_datetime:
        event["end"] = {"dateTime": end_datetime, "timeZone": timezone}

    updated = service.events().update(
        calendarId="primary", eventId=event_id, body=event
    ).execute()
    return json.dumps({
        "event_id": updated["id"],
        "event_link": updated.get("htmlLink", ""),
        "status": "updated",
    })
