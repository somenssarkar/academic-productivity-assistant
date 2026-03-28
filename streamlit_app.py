"""EduFlow — Student-facing Streamlit UI.

Connects to the FastAPI backend via SSE streaming.
"""

import os
import uuid
import json
import time
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
    if "profile_saved" not in st.session_state:
        st.session_state.profile_saved = False
    # Persist uid/sid in URL (survives page refresh)
    st.query_params.update({"uid": st.session_state.uid, "sid": st.session_state.sid})


_init_session()

# ---------------------------------------------------------------------------
# Backend health check (cached 30s to avoid hammering)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30)
def _backend_status(backend_url: str) -> bool:
    try:
        r = httpx.get(f"{backend_url}/health", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Profile state delta builder
# ---------------------------------------------------------------------------

def _build_state_delta(profile: dict) -> dict:
    """Convert profile form values to ADK user: state keys."""
    return {
        f"user:{k}": v
        for k, v in profile.items()
        if v
    }


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
            timeout=120.0,
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
                    # ADK SSE format: content → parts → text
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
        name = st.text_input("Name", placeholder="Your name")
        email = st.text_input("Email", placeholder="student@email.com")
        parent_email = st.text_input("Parent Email", placeholder="parent@email.com")
        grade = st.selectbox("Grade", ["Grade 7", "Grade 8", "Grade 9", "Grade 10"])
        language = st.selectbox("Language", ["English", "Hindi", "Tamil", "Telugu",
                                              "Kannada", "Malayalam", "Bengali"])
        save_profile = st.form_submit_button("Save Profile")

    if save_profile:
        st.session_state.profile = {
            "name": name, "email": email, "parent_email": parent_email,
            "grade_level": grade, "preferred_language": language,
        }
        st.session_state.profile_saved = True
        st.success("Profile saved!")

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

    # Backend status indicator
    is_online = _backend_status(BACKEND_URL)
    status_icon = "🟢" if is_online else "🔴"
    status_text = "Backend connected" if is_online else "Backend offline"
    st.caption(f"{status_icon} {status_text}")

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

# Video embed area (shown when session_video_url is in state)
if video_url := st.session_state.get("session_video_url"):
    st.video(video_url)
    st.divider()

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle quick action buttons
if quick_action := st.session_state.pop("quick_action", None):
    st.session_state.messages.append({"role": "user", "content": quick_action})
    with st.chat_message("user"):
        st.markdown(quick_action)
    with st.chat_message("assistant"):
        state_delta = _build_state_delta(st.session_state.get("profile", {}))
        response = st.write_stream(_stream_agent_response(quick_action, state_delta))
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# Chat input
if prompt := st.chat_input("Ask EduFlow anything about your studies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        state_delta = _build_state_delta(st.session_state.get("profile", {})) \
            if not st.session_state.profile_saved else None
        response = st.write_stream(_stream_agent_response(prompt, state_delta))
    st.session_state.messages.append({"role": "assistant", "content": response})
