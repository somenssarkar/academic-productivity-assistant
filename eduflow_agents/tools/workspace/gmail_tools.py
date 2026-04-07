"""Gmail function tools for ADK agents."""

import base64
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from .auth import get_credentials


def send_email(to: str, subject: str, body_html: str, cc: str = None) -> str:
    """Send an email via Gmail.

    Used for three scenarios:
    - Learning plan sent to student + parent after planning_pipeline
    - Session reminder sent before a scheduled study session
    - Progress report sent to parent after assessment_pipeline

    Args:
        to: Recipient email address
        subject: Email subject line
        body_html: HTML email body (supports <b>, <ul>, <a>, etc.)
        cc: Optional CC email address (e.g. parent email when sending to student)

    Returns:
        JSON string with message_id confirming delivery.
    """
    service = build("gmail", "v1", credentials=get_credentials())

    message = MIMEMultipart("alternative")
    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    message.attach(MIMEText(body_html, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()

    return json.dumps({
        "message_id": result["id"],
        "status": "sent",
        "to": to,
    })
