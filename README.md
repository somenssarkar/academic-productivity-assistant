# EduFlow — Multi-Agent AI Academic Assistant

> **Built for Google Cloud Gen AI Academy — APAC Hackathon (Hack2Skill)**

[![Google ADK](https://img.shields.io/badge/Google%20ADK-Multi--Agent-blue?logo=google)](https://google.github.io/adk-docs/)
[![Gemini 2.5 Pro](https://img.shields.io/badge/Gemini-2.5%20Pro-orange?logo=google)](https://deepmind.google/technologies/gemini/)
[![Cloud Run](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-4285F4?logo=googlecloud)](https://cloud.google.com/run)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-green?logo=python)](https://python.org)

**[Try EduFlow Live →](https://eduflow-frontend-538280901412.asia-southeast1.run.app)**

**EduFlow turns a student's learning goal into a complete, automated study journey** — planning sessions, scheduling calendar events, teaching grade-aware lessons with live code verification, running quizzes, and emailing progress reports to parents. All from a single student message.

---

## Demo

**Watch the 3-minute demo:**

[![EduFlow Demo](https://img.youtube.com/vi/dR4lAGPrs6I/maxresdefault.jpg)](https://www.youtube.com/watch?v=dR4lAGPrs6I)

> *Student says: "I want to learn Squares and Square Roots in 3 days"*
> *EduFlow plans 3 sessions, books calendar events, sends the parent an email with a study notes link, teaches the lesson in grade-appropriate language, runs a quiz, and emails the parent a progress report — all automatically.*

---

## What It Does

A student types one goal. EduFlow orchestrates 11 AI agents across 6 pipelines to handle their entire learning lifecycle:

| Stage | What happens |
|---|---|
| **Plan** | Reads CBSE YAML curriculum, structures sessions by topic depth, finds YouTube videos per topic |
| **Schedule** | Creates Google Calendar events with video links and tutor starter prompts |
| **Notify** | Emails the plan to student + parent with a Google Docs study notes link |
| **Teach** | Delivers grade-aware tutoring with live Python code verification |
| **Assess** | Runs quizzes from YAML curriculum questions, stores scores in Cloud SQL |
| **Report** | Emails a progress report (score, weak areas, doc link) to parents after every quiz |

---

## Architecture

**1 orchestrator + 10 specialist agents across 6 pipelines.**

```
orchestrator_agent  (understands intent, coordinates all pipelines)
│
├── planning_pipeline
│   ├── curriculum_planner_agent   — reads YAML syllabus, structures sessions
│   ├── content_agent              — finds grade-appropriate YouTube videos
│   └── plan_saver_agent           — persists plan + sessions to Cloud SQL
│
├── scheduling_pipeline
│   ├── calendar_agent             — creates Google Calendar events
│   └── email_agent                — sends plan email to student + parent
│
├── tutoring_pipeline
│   ├── tutor_agent                — teaches with live code execution (BuiltInCodeExecutor)
│   └── tutoring_formatter         — formats output into clean textbook-style lesson
│
├── notes_pipeline
│   └── docs_agent                 — creates/appends Google Docs study notes in Drive
│
├── assessment_pipeline
│   └── assessment_agent           — YAML quiz questions, evaluates answers, saves scores
│
└── report_pipeline
    └── report_email_agent         — sends parent progress report after assessment
```

**Key orchestration patterns:**
- `_build_orchestrator_instruction` rebuilds the system prompt every turn — injects student profile, grade band, topics saved to notes, and the last formatted lesson
- `set_user_profile` function tool — sets `session_topic` before planning, tracks `notes_saved_topics` to prevent duplicate doc insertions
- Factory functions (`make_email_agent`, `make_response_formatter`) — ADK's one-parent-per-agent rule means each pipeline gets its own instance

---

## Tech Stack

| Component | Technology |
|---|---|
| **Agent Framework** | Google ADK (`google-adk`) |
| **LLM** | `gemini-2.5-pro` — all 8 main agents |
| **LLM (plan saver + audio)** | `gemini-2.5-flash-lite` — tool-call-only sequences and transcription |
| **Code Execution** | `BuiltInCodeExecutor` — sandboxed Python for math/physics verification |
| **Workspace Integrations** | Google Calendar, Gmail, Docs, Drive — via `google-api-python-client` + OAuth2 |
| **Video Search** | YouTube Data API v3 |
| **Curriculum Data** | YAML files (`data/curricula/cbse/math/grade-7..10.yaml`) — auto-discovered, no DB needed |
| **Database** | Cloud SQL PostgreSQL 15 — 4 custom tables + 5 ADK-managed tables |
| **Database MCP** | MCP Toolbox for Databases |
| **Frontend** | Streamlit — streaming SSE chat, voice input, progress tracker |
| **Backend** | FastAPI + ADK `get_fast_api_app()` + `DatabaseSessionService` |
| **Deployment** | Google Cloud Run — 3 services (frontend, backend, toolbox) |

---

## Key Differentiators

### Grade-Aware Teaching
Four grade bands (Foundation 5-6 / Building 7-8 / Bridging 9-10 / Advanced 11-12) — each with a distinct tutor persona. The same topic, taught differently:
- **Grade 6:** Area of a circle — thin segments rearranged into a rectangle (visual proof)
- **Grade 10:** Same topic — derived using integration (concentric rings of width dr)

### Voice Input + Multilingual
Students speak in Hindi, Tamil, Bengali, or 70+ other languages. `gemini-2.5-flash-lite` transcribes in Streamlit before the text reaches the backend — main agent quota is fully preserved.

### Living Google Docs Study Notes
`docs_agent` creates a Google Doc at plan time with a chapter overview, then appends each session's formatted lesson after tutoring. The doc grows with the student. `notes_saved_topics` in state prevents duplicate insertions if a topic is revisited.

### Real Google Workspace Integration
- **Calendar:** Events include the video link and a tutor starter prompt ("Ask EduFlow → 'Teach me Perfect Squares'")
- **Gmail:** Plan emails with the study doc link, progress report emails with scores and weak areas
- **Docs + Drive:** Organized folders (`EduFlow/Math/Grade 8/`), formatted docs with headings

---

## Repository Structure

```
├── eduflow_agents/          # ADK agent package
│   ├── agent.py             # root_agent + all 6 pipelines
│   ├── subagents/           # 10 specialist agents
│   ├── prompts/             # all instruction strings
│   └── tools/               # YouTube search, curriculum loader, workspace tools
├── data/curricula/          # YAML curriculum (CBSE Math Grade 7-10)
├── mcp_servers/database/    # MCP Toolbox config (tools.yaml)
├── scripts/infra/           # DB setup, Toolbox start scripts
├── main.py                  # FastAPI backend
├── streamlit_app.py         # Student-facing Streamlit UI
├── Dockerfile.backend
├── Dockerfile.frontend
└── Dockerfile.toolbox
```

---

## How to Run Locally

### Prerequisites
- Python 3.12+
- Google Cloud project with Vertex AI, Cloud SQL, YouTube Data API v3 enabled
- OAuth2 credentials for Google Workspace (Calendar, Gmail, Docs, Drive)
- `gcloud` CLI authenticated
- MCP Toolbox binary in `scripts/infra/`

### Steps

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate          # Linux/macOS

# 2. Install dependencies
pip install -r requirements-backend.txt
pip install -r requirements-ui.txt

# 3. Configure environment
cp eduflow_agents/.env.example eduflow_agents/.env
# Fill in: GOOGLE_API_KEY, YOUTUBE_API_KEY, GOOGLE_OAUTH_*, DB credentials

# 4. Start MCP Toolbox (database tools)
.\scripts\infra\start_toolbox.ps1

# 5. Start backend
uvicorn main:app --reload --port 8000

# 6. Start frontend (separate terminal)
streamlit run streamlit_app.py
```

Open `http://localhost:8501`, fill in the student profile sidebar, and type:
> *"I want to learn Quadratic Equations in 3 days"*

---

## Database Schema

4 custom tables + 5 ADK-managed session tables (auto-created by `DatabaseSessionService`):

| Table | Purpose |
|---|---|
| `learning_plans` | One row per student learning goal |
| `study_sessions` | Individual sessions with Calendar/Doc IDs and status |
| `assessments` | Quiz scores, correct answers, weak areas per topic |
| `progress` | Aggregated mastery level per student per topic |

Student profile (name, email, grade, language) is stored in ADK's `user_states` table via `user:` prefixed state — no custom students table needed.

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `GOOGLE_GENAI_USE_VERTEXAI` | `1` for Vertex AI (prod), `0` for API key (dev) |
| `GOOGLE_API_KEY` | Gemini API key (dev only) |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `GOOGLE_OAUTH_CLIENT_ID` | Google Workspace OAuth2 client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google Workspace OAuth2 client secret |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | Pre-authorized OAuth2 refresh token |
| `MCP_TOOLBOX_URL` | `http://localhost:5000/mcp` (local) or Cloud Run URL |
| `SESSION_DB_URI` | `postgresql+asyncpg://...` for Cloud SQL (production) |
| `BACKEND_URL` | Backend Cloud Run URL (frontend service) |

---

## Cloud Run Deployment

Three services deployed to Google Cloud Run:

| Service | Image | Purpose | URL |
|---|---|---|---|
| `eduflow-frontend` | `Dockerfile.frontend` | Streamlit UI | [eduflow-frontend-538280901412.asia-southeast1.run.app](https://eduflow-frontend-538280901412.asia-southeast1.run.app) |
| `eduflow-backend` | `Dockerfile.backend` | FastAPI + ADK agents | internal |
| `eduflow-toolbox` | `Dockerfile.toolbox` | MCP Toolbox → Cloud SQL | internal |
