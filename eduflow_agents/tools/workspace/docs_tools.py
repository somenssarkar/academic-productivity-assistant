"""Google Docs function tools for ADK agents."""

import re
import json
from googleapiclient.discovery import build
from .auth import get_credentials


def _strip_markdown(text: str) -> str:
    """Convert markdown/LaTeX formatted text to clean plain text for Google Docs.

    Google Docs insertText writes literal characters — markdown symbols like **,
    $, ``` all appear verbatim. This helper strips them before insertion.
    """
    # Remove fenced code blocks — keep only the code lines, drop the fences
    text = re.sub(r"```(?:python|)\n(.*?)```", lambda m: m.group(1).strip(), text, flags=re.DOTALL)
    # Remove inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove LaTeX math delimiters $...$ and $$...$$
    text = re.sub(r"\$\$([^$]+)\$\$", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\$([^$\n]+)\$", r"\1", text)
    # Remove bold/italic: **text** → text, *text* → text
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    # Remove markdown headings: ## Heading → Heading
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove emoji section headers like 🎯 Hook, 📖 Explanation, ✏️ Worked Example
    text = re.sub(r"^[^\w\s]*\s*(Hook|Explanation|Worked Example|Spark)\s*$", r"\1", text, flags=re.MULTILINE | re.IGNORECASE)
    return text.strip()


def create_study_notes_doc(title: str, folder_id: str = None, chapter_title: str = "") -> str:
    """Create a new Google Doc for chapter study notes with a formatted title heading.

    Creates the document, moves it into the Drive folder, and adds a HEADING_1
    chapter title so the doc looks polished from the first open.

    Args:
        title: Document title shown in Drive (e.g. "Study Notes: Quadratic Equations — Math Grade 8")
        folder_id: Drive folder ID to place the doc in (from get_or_create_folder)
        chapter_title: Chapter name shown as HEADING_1 inside the doc body (e.g. "Quadratic Equations")

    Returns:
        JSON string with doc_id and doc_url.
    """
    docs_service = build("docs", "v1", credentials=get_credentials())
    drive_service = build("drive", "v3", credentials=get_credentials())

    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    if folder_id:
        file_meta = drive_service.files().get(fileId=doc_id, fields="parents").execute()
        previous_parents = ",".join(file_meta.get("parents", []))
        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()

    # Add chapter title as HEADING_1 inside the doc body
    heading = chapter_title or title
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {"insertText": {"location": {"index": 1}, "text": heading + "\n"}},
                {
                    "updateParagraphStyle": {
                        "range": {"startIndex": 1, "endIndex": len(heading) + 2},
                        "paragraphStyle": {"namedStyleType": "HEADING_1"},
                        "fields": "namedStyleType",
                    }
                },
            ]
        },
    ).execute()

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return json.dumps({"doc_id": doc_id, "doc_url": doc_url, "title": title, "status": "created"})


def append_session_to_doc(
    doc_id: str,
    session_number: int,
    topic_title: str,
    key_concepts: str,
    video_url: str,
    duration_minutes: int,
) -> str:
    """Append a richly formatted session section to a study notes Google Doc.

    Formatting applied:
    - Session heading  → HEADING_2 (large, dark)
    - "Key Concepts"   → HEADING_3 (medium sub-heading)
    - Concept text     → normal paragraph
    - "Video"          → HEADING_3
    - Video URL        → blue hyperlink (#1155CC, underlined)
    - "Duration:"      → bold label + normal value

    Args:
        doc_id: The Google Doc ID (from create_study_notes_doc)
        session_number: Session number (1, 2, 3 ...)
        topic_title: Exact topic title from YAML curriculum — copy verbatim
        key_concepts: Comma-separated list of concepts for this session
        video_url: Real YouTube URL — must start with https://
        duration_minutes: Session duration in minutes (e.g. 35)

    Returns:
        JSON string confirming append with doc_id and doc_url.
    """
    docs_service = build("docs", "v1", credentials=get_credentials())

    doc = docs_service.documents().get(documentId=doc_id).execute()
    E = doc["body"]["content"][-1]["endIndex"] - 1  # current end position

    # --- Build text block and track positions ---
    sep          = "\n"
    heading_line = f"Session {session_number} — {topic_title}\n"
    kc_label     = "Key Concepts\n"
    concepts_txt = key_concepts.strip() + "\n"
    blank        = "\n"
    vid_label    = "Video\n"
    url_text     = (video_url.strip() if video_url and video_url.startswith("http") else "Video coming soon")
    url_line     = url_text + "\n"
    dur_label    = "Duration: "
    dur_value    = f"{duration_minutes} min\n"

    full_text = sep + heading_line + kc_label + concepts_txt + blank + vid_label + url_line + blank + dur_label + dur_value

    # Character positions AFTER insertion (relative to E)
    p = E
    p += len(sep)
    p_h_start = p;  p += len(heading_line);  p_h_end = p
    p_kc_start = p; p += len(kc_label);      p_kc_end = p
    p_cn_start = p; p += len(concepts_txt);  p_cn_end = p
    p += len(blank)
    p_vl_start = p; p += len(vid_label);     p_vl_end = p
    p_url_start = p; p += len(url_line);     p_url_end = p
    p += len(blank)
    p_dl_start = p; p += len(dur_label);     p_dl_end = p

    requests = [
        # Insert all text in one call
        {"insertText": {"location": {"index": E}, "text": full_text}},
        # Session heading → HEADING_2
        {
            "updateParagraphStyle": {
                "range": {"startIndex": p_h_start, "endIndex": p_h_end},
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType",
            }
        },
        # "Key Concepts" → HEADING_3
        {
            "updateParagraphStyle": {
                "range": {"startIndex": p_kc_start, "endIndex": p_kc_end},
                "paragraphStyle": {"namedStyleType": "HEADING_3"},
                "fields": "namedStyleType",
            }
        },
        # "Video" → HEADING_3
        {
            "updateParagraphStyle": {
                "range": {"startIndex": p_vl_start, "endIndex": p_vl_end},
                "paragraphStyle": {"namedStyleType": "HEADING_3"},
                "fields": "namedStyleType",
            }
        },
        # "Duration:" → bold
        {
            "updateTextStyle": {
                "range": {"startIndex": p_dl_start, "endIndex": p_dl_end},
                "textStyle": {"bold": True},
                "fields": "bold",
            }
        },
    ]

    # Video URL → blue hyperlink (only for real URLs)
    if video_url and video_url.startswith("http"):
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": p_url_start, "endIndex": p_url_end - 1},  # exclude \n
                "textStyle": {
                    "foregroundColor": {
                        "color": {"rgbColor": {"red": 0.067, "green": 0.333, "blue": 0.800}}
                    },
                    "link": {"url": video_url.strip()},
                    "underline": True,
                },
                "fields": "foregroundColor,link,underline",
            }
        })

    docs_service.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()

    return json.dumps({
        "doc_id": doc_id,
        "doc_url": f"https://docs.google.com/document/d/{doc_id}/edit",
        "status": "appended",
        "session": session_number,
    })


def append_to_doc(doc_id: str, heading: str, content: str) -> str:
    """Append a plain-text section to an existing study notes Google Doc.

    Used for MODE B (post-tutor notes) where content is unstructured.
    For plan-time session overviews use append_session_to_doc instead.

    Args:
        doc_id: The Google Doc ID
        heading: Section heading (e.g. "Session 2 — Factoring Method (Tutor Notes)")
        content: Free-form session notes text

    Returns:
        JSON string confirming the append with doc_id.
    """
    docs_service = build("docs", "v1", credentials=get_credentials())

    doc = docs_service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1

    # Strip markdown/LaTeX so symbols don't appear literally in Google Docs plain text
    clean_content = _strip_markdown(content)
    full_text = f"\n{heading}\n{clean_content}\n"
    heading_end = end_index + len(f"\n{heading}\n")  # heading spans \n + heading text + \n

    requests = [
        {"insertText": {"location": {"index": end_index}, "text": full_text}},
        {
            "updateParagraphStyle": {
                "range": {"startIndex": end_index + 1, "endIndex": heading_end},
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
