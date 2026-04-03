"""Google Drive function tools for ADK agents."""

import json
from googleapiclient.discovery import build
from .auth import get_credentials


def get_or_create_folder(name: str, parent_id: str = None) -> str:
    """Get an existing Drive folder by name or create it if absent.

    Used to organise study notes under EduFlow/{Subject}/Grade {N}/.

    Args:
        name: Folder name (e.g. "EduFlow", "Math", "Grade 8")
        parent_id: Parent folder ID — omit for root Drive level

    Returns:
        JSON string with folder_id for use in create_study_notes_doc.
    """
    service = build("drive", "v3", credentials=get_credentials())

    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query, fields="files(id, name)", pageSize=1
    ).execute()
    files = results.get("files", [])

    if files:
        return json.dumps({"folder_id": files[0]["id"], "name": name, "status": "existing"})

    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]

    folder = service.files().create(body=body, fields="id").execute()
    return json.dumps({"folder_id": folder["id"], "name": name, "status": "created"})


def share_file_with_student(file_id: str, student_email: str) -> str:
    """Share a Google Drive file (doc or folder) with the student as a reader.

    The student receives an email notification and the file appears in their
    'Shared with me' in Google Drive — no separate Drive account needed.

    Args:
        file_id: The Drive file or folder ID to share
        student_email: Student's Google account email (e.g. student@gmail.com)

    Returns:
        JSON string confirming the share permission was granted.
    """
    try:
        service = build("drive", "v3", credentials=get_credentials())
        permission = {
            "type": "user",
            "role": "reader",
            "emailAddress": student_email,
        }
        service.permissions().create(
            fileId=file_id,
            body=permission,
            sendNotificationEmail=False,  # email is sent separately by email_agent
            fields="id",
        ).execute()
        return json.dumps({
            "status": "shared",
            "file_id": file_id,
            "shared_with": student_email,
        })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
