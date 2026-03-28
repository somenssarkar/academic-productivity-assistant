"""Google Docs function tools for ADK agents."""

import json
from googleapiclient.discovery import build
from .auth import get_credentials


def create_study_notes_doc(title: str, folder_id: str = None) -> str:
    """Create a new Google Doc for chapter study notes.

    Creates a blank document then moves it into the specified Drive folder.
    The docs_agent appends session content via append_to_doc after each session.

    Args:
        title: Document title (e.g. "Study Notes: Quadratic Equations — Math Grade 8")
        folder_id: Drive folder ID to place the doc in (from get_or_create_folder)

    Returns:
        JSON string with doc_id and doc_url for storage in AlloyDB and sharing.
    """
    docs_service = build("docs", "v1", credentials=get_credentials())
    drive_service = build("drive", "v3", credentials=get_credentials())

    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    if folder_id:
        # Move into the target folder
        file_meta = drive_service.files().get(
            fileId=doc_id, fields="parents"
        ).execute()
        previous_parents = ",".join(file_meta.get("parents", []))
        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return json.dumps({
        "doc_id": doc_id,
        "doc_url": doc_url,
        "title": title,
        "status": "created",
    })


def append_to_doc(doc_id: str, heading: str, content: str) -> str:
    """Append a new section to an existing study notes Google Doc.

    Appends a Heading 2 section followed by plain text content.
    Called after each tutoring session to add session notes.

    Args:
        doc_id: The Google Doc ID (from create_study_notes_doc)
        heading: Section heading (e.g. "Session 2 — Factoring Method")
        content: Session notes text — key concepts, YouTube link, practice problems

    Returns:
        JSON string confirming the append with doc_id.
    """
    docs_service = build("docs", "v1", credentials=get_credentials())

    doc = docs_service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1

    full_text = f"\n{heading}\n{content}\n"
    heading_end = end_index + len(f"\n{heading}\n")

    requests = [
        {
            "insertText": {
                "location": {"index": end_index},
                "text": full_text,
            }
        },
        {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": end_index + 1,
                    "endIndex": heading_end,
                },
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType",
            }
        },
    ]

    docs_service.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()

    return json.dumps({
        "doc_id": doc_id,
        "doc_url": f"https://docs.google.com/document/d/{doc_id}/edit",
        "status": "appended",
        "section": heading,
    })
