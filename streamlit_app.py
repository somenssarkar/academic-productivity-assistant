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
    if "show_mic" not in st.session_state:
        st.session_state.show_mic = False
    if "_audio_error" not in st.session_state:
        st.session_state["_audio_error"] = ""
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

def _build_state_delta(profile: dict) -> dict:
    """Convert profile form values to ADK user: state keys.
    Always includes user:id (the Streamlit uid) so agents can use it for DB operations.
    """
    delta = {f"user:{k}": v for k, v in profile.items() if v}
    delta["user:id"] = st.session_state.uid  # Always send — needed by plan_saver + assessment
    return delta


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
# Audio transcription — dedicated model (gemini-2.0-flash-exp-audio)
# Kept separate from the main orchestrator (gemini-2.5-flash) to preserve
# quota for planning/teaching/assessment agents.
# ---------------------------------------------------------------------------

@st.cache_resource
def _get_genai_client():
    """Lazy-initialize the google.genai client for audio transcription only."""
    from google import genai as _genai  # noqa: PLC0415
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "0") == "1":
        return _genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
    return _genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def _transcribe_audio(audio_bytes) -> tuple[str, str]:
    """Transcribe WAV audio using gemini-2.5-flash-lite (separate quota pool).

    gemini-live-2.5-flash-native-audio requires the Live API (websocket streaming)
    and cannot be used for batch transcription via generate_content.
    gemini-2.5-flash-lite is the correct choice: same 2.5 generation, lighter weight,
    supports audio input via generate_content, and has its own quota separate from
    the gemini-2.5-flash agents.

    Audio bytes are consumed entirely in the Streamlit layer — the ADK backend
    never receives raw audio, only the clean transcript text.

    Returns (transcript, error_message). On success error_message is "".
    The main orchestrator (gemini-2.5-flash) never sees the raw audio bytes —
    only the clean transcript text is forwarded, preserving its quota entirely.
    """
    try:
        from google.genai import types as _types  # noqa: PLC0415
        client = _get_genai_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                _types.Content(
                    role="user",
                    parts=[
                        _types.Part(
                            inline_data=_types.Blob(
                                mime_type="audio/wav",
                                data=audio_bytes.getvalue(),
                            )
                        ),
                        _types.Part(
                            text=(
                                "Transcribe this student's spoken message exactly as heard. "
                                "Return only the transcribed words — no commentary, no punctuation "
                                "corrections, no explanations."
                            )
                        ),
                    ]
                )
            ],
        )
        return (response.text or "").strip(), ""
    except Exception as exc:
        return "", str(exc)


# ---------------------------------------------------------------------------
# SSE streaming
# ---------------------------------------------------------------------------

def _stream_agent_response(message: str, state_delta: dict | None = None):
    """Stream a response from the backend via SSE and yield text chunks.

    Args:
        message: Text message to send. Audio is pre-transcribed before reaching here
                 (gemini-2.0-flash-exp-audio handles transcription separately) so the
                 main orchestrator always receives plain text.
        state_delta: Optional ADK session state updates to apply before the agent runs.
    """
    parts = [{"text": message}]

    payload = {
        "app_name": APP_NAME,
        "user_id": st.session_state.uid,
        "session_id": st.session_state.sid,
        "new_message": {"role": "user", "parts": parts},
    }
    if state_delta:
        payload["state_delta"] = state_delta

    full_text = ""
    try:
        with httpx.stream(
            "POST",
            f"{BACKEND_URL}/run_sse",
            json=payload,
            timeout=httpx.Timeout(connect=10.0, read=360.0, write=30.0, pool=10.0),
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
    """Send a message, stream the response, then sync state.

    Audio is always pre-transcribed by _transcribe_audio() before this is called,
    so this function only ever handles plain text — keeping the main model clean.
    """
    state_delta = _build_state_delta(st.session_state.profile)

    with st.chat_message("assistant"):
        response = st.write_stream(
            _stream_agent_response(message, state_delta)
        )

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

    # Voice input — sidebar keeps it always visible regardless of chat scroll
    st.subheader("Voice Input")
    mic_label = "🎤 Stop Recording" if st.session_state.show_mic else "🎤 Use Microphone"
    if st.button(mic_label, use_container_width=True, key="mic_toggle"):
        st.session_state.show_mic = not st.session_state.show_mic
        st.rerun()
    if st.session_state.show_mic:
        st.caption("Speak, then click stop. Transcript appears in chat.")
    else:
        st.caption("Click to speak instead of typing.")

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
# Persistent error banner (survives st.rerun — cleared after display)
# ---------------------------------------------------------------------------

if st.session_state["_audio_error"]:
    st.error(
        f"**Audio transcription failed.** The error was:\n\n"
        f"```\n{st.session_state['_audio_error']}\n```\n\n"
        "Please type your message instead, or try recording again.",
        icon="🎤",
    )
    if st.button("Dismiss", key="dismiss_audio_error"):
        st.session_state["_audio_error"] = ""
        st.rerun()

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
# Audio recorder — shown in main area only when mic is toggled ON via sidebar.
# Toggling is in the sidebar (always visible, never scrolls away).
# Transcription: gemini-2.0-flash-exp-audio (dedicated 4M tokens/min quota).
# Orchestrator (gemini-2.5-flash) receives plain text only — quota preserved.
# ---------------------------------------------------------------------------

if st.session_state.show_mic:
    audio_input = st.audio_input("🎤 Speak your message, then click stop", key="mic_input")

    if audio_input:
        audio_key = hash(audio_input.getvalue())
        if st.session_state.get("_last_audio_key") != audio_key:
            st.session_state["_last_audio_key"] = audio_key
            st.session_state.show_mic = False  # Auto-close — sidebar button resets on rerun

            # Step 1 — Transcribe via gemini-2.0-flash (separate quota from gemini-2.5-flash)
            with st.spinner("Transcribing your message..."):
                transcript, err = _transcribe_audio(audio_input)

            # Step 2 — Show transcript (or error) as the user message
            if transcript:
                display_text = f"🎤 {transcript}"
                forward_text = transcript
                st.session_state["_audio_error"] = ""  # Clear any previous error
            else:
                display_text = "🎤 _[Could not transcribe — please repeat or type your message]_"
                st.session_state["_audio_error"] = err or "Unknown error"
                forward_text = None

            st.session_state.messages.append({"role": "user", "content": display_text})
            with st.chat_message("user"):
                st.markdown(display_text)
                st.audio(audio_input)  # Playback so student can verify

            # Step 3 — Forward clean transcript text to orchestrator (no audio bytes)
            if forward_text:
                _handle_message(forward_text)

            # Always rerun so sidebar button label reflects show_mic=False immediately
            st.rerun()

# ---------------------------------------------------------------------------
# Text chat input — always visible, pinned to bottom by Streamlit
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask EduFlow anything about your studies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    _handle_message(prompt)
