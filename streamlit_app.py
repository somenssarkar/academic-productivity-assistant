"""EduFlow — Student-facing Streamlit UI.

Connects to the FastAPI backend via SSE streaming.
"""

import os
import re
import uuid
import json
import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv("eduflow_agents/.env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
APP_NAME = "eduflow_agents"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="EduFlow — AI Study Assistant",
    page_icon="📚",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session initialisation
# ---------------------------------------------------------------------------

def _init_session():
    params = st.query_params
    if "uid" not in st.session_state:
        st.session_state.uid = params.get("uid") or str(uuid.uuid4())
    if "sid" not in st.session_state:
        st.session_state.sid = params.get("sid") or str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "profile" not in st.session_state:
        st.session_state.profile = {}
    if "session_video_url" not in st.session_state:
        st.session_state.session_video_url = ""
    # Persist uid/sid in URL (survives page refresh)
    st.query_params.update({"uid": st.session_state.uid, "sid": st.session_state.sid})


_init_session()

# ---------------------------------------------------------------------------
# Backend health check (cached 30s)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30)
def _backend_status(backend_url: str) -> bool:
    try:
        # /health is exposed by ADK's get_fast_api_app
        r = httpx.get(f"{backend_url}/health", timeout=3.0)
        return r.status_code == 200
    except Exception:
        try:
            r = httpx.get(f"{backend_url}/apps", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Profile state delta builder
# ---------------------------------------------------------------------------

def _build_state_delta(profile: dict) -> dict | None:
    """Convert profile form values to ADK user: state keys."""
    if not profile:
        return None
    delta = {f"user:{k}": v for k, v in profile.items() if v}
    return delta or None


# ---------------------------------------------------------------------------
# Fetch ADK session state from backend (for video URL, plan state, etc.)
# ---------------------------------------------------------------------------

def _fetch_adk_state() -> dict:
    """Query the backend for current ADK session state after each response."""
    try:
        url = (
            f"{BACKEND_URL}/apps/{APP_NAME}"
            f"/users/{st.session_state.uid}"
            f"/sessions/{st.session_state.sid}"
        )
        r = httpx.get(url, timeout=5.0)
        if r.status_code == 200:
            return r.json().get("state", {})
    except Exception:
        pass
    return {}


def _extract_youtube_url(text: str) -> str:
    """Pull the first YouTube URL out of a text response."""
    match = re.search(r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w\-]+", text)
    return match.group(0) if match else ""


# ---------------------------------------------------------------------------
# SSE streaming
# ---------------------------------------------------------------------------

def _stream_agent_response(message: str, state_delta: dict | None = None):
    """Stream a response from the backend via SSE and yield text chunks."""
    payload = {
        "app_name": APP_NAME,
        "user_id": st.session_state.uid,
        "session_id": st.session_state.sid,
        "new_message": {"role": "user", "parts": [{"text": message}]},
    }
    if state_delta:
        payload["state_delta"] = state_delta

    full_text = ""
    try:
        with httpx.stream(
            "POST",
            f"{BACKEND_URL}/run_sse",
            json=payload,
            timeout=180.0,
            headers={"Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if not data_str or data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                    for part in event.get("content", {}).get("parts", []):
                        chunk = part.get("text", "")
                        if chunk:
                            full_text += chunk
                            yield chunk
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        yield f"\n\n_(Error connecting to EduFlow backend: {e})_"

    if not full_text.strip():
        yield "_EduFlow is warming up — please try again in a moment._"


def _handle_message(message: str):
    """Send a message, stream the response, then sync state from backend."""
    # Always inject profile so backend state stays current
    state_delta = _build_state_delta(st.session_state.profile)

    with st.chat_message("assistant"):
        response = st.write_stream(_stream_agent_response(message, state_delta))

    st.session_state.messages.append({"role": "assistant", "content": response})

    # Sync video URL from ADK state (content_agent writes session_video_url)
    adk_state = _fetch_adk_state()
    video_url = adk_state.get("session_video_url") or _extract_youtube_url(response)
    if video_url:
        st.session_state.session_video_url = video_url


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("📚 EduFlow")
    st.caption("AI Study Assistant")
    st.divider()

    # Student profile form
    st.subheader("Your Profile")
    with st.form("profile_form"):
        name = st.text_input("Name", value=st.session_state.profile.get("name", ""),
                             placeholder="Your name")
        email = st.text_input("Email", value=st.session_state.profile.get("email", ""),
                              placeholder="student@gmail.com")
        parent_email = st.text_input("Parent Email",
                                     value=st.session_state.profile.get("parent_email", ""),
                                     placeholder="parent@gmail.com")
        grade_options = ["Grade 7", "Grade 8", "Grade 9", "Grade 10"]
        current_grade = st.session_state.profile.get("grade_level", "Grade 8")
        grade = st.selectbox("Grade", grade_options,
                             index=grade_options.index(current_grade) if current_grade in grade_options else 1)
        lang_options = ["English", "Hindi", "Tamil", "Telugu", "Kannada", "Malayalam", "Bengali"]
        current_lang = st.session_state.profile.get("preferred_language", "English")
        language = st.selectbox("Language", lang_options,
                                index=lang_options.index(current_lang) if current_lang in lang_options else 0)
        save_profile = st.form_submit_button("Save Profile", use_container_width=True)

    if save_profile:
        st.session_state.profile = {
            "name": name,
            "email": email,
            "parent_email": parent_email,
            "grade_level": grade,
            "preferred_language": language,
        }
        st.success(f"Profile saved! Welcome, {name or 'Student'}!")

    st.divider()

    # Quick actions
    st.subheader("Quick Actions")
    if st.button("📅 Plan a Study Session", use_container_width=True):
        st.session_state.quick_action = "I want to plan a new study session"
    if st.button("▶️ Start Next Session", use_container_width=True):
        st.session_state.quick_action = "Start my next scheduled study session"
    if st.button("📝 Take a Quiz", use_container_width=True):
        st.session_state.quick_action = "I want to take a quiz on what I've learned"
    if st.button("📊 View My Progress", use_container_width=True):
        st.session_state.quick_action = "Show me my learning progress"

    st.divider()

    # Backend status
    is_online = _backend_status(BACKEND_URL)
    st.caption(f"{'🟢 Backend connected' if is_online else '🔴 Backend offline'}")

# ---------------------------------------------------------------------------
# Main content — session video embed
# ---------------------------------------------------------------------------

if st.session_state.session_video_url:
    st.subheader("📺 Session Video")
    st.video(st.session_state.session_video_url)
    st.divider()

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Handle quick action buttons
# ---------------------------------------------------------------------------

if quick_action := st.session_state.pop("quick_action", None):
    st.session_state.messages.append({"role": "user", "content": quick_action})
    with st.chat_message("user"):
        st.markdown(quick_action)
    _handle_message(quick_action)
    st.rerun()

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask EduFlow anything about your studies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    _handle_message(prompt)
