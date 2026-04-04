# EduFlow — AI Academic Productivity Assistant

**Hackathon:** Google Cloud Gen AI Academy — APAC Edition (Hack2Skill)
**Submission deadline:** 2026-04-08

A multi-agent AI system built on **Google ADK** with **Gemini 2.5 Pro** that helps students manage their complete learning lifecycle — from planning study sessions to tracking progress and keeping parents informed.

---

## What EduFlow Does

A student says: *"I want to learn Squares and Square Roots in 3 days"* — EduFlow handles everything:

1. **Plans** — reads CBSE curriculum, breaks the topic into grade-appropriate sessions, finds YouTube videos per topic
2. **Schedules** — creates Google Calendar events with video links and tutor starter prompts
3. **Notifies** — emails the plan to student and parent with a Google Docs study notes link
4. **Teaches** — delivers grade-aware tutoring with live code verification
5. **Assesses** — runs quizzes from YAML curriculum questions, stores scores in database
6. **Reports** — emails progress reports to parents after each assessment

---

## Architecture

### Agent Hierarchy

```
orchestrator_agent  (LlmAgent — understands intent, coordinates workflow)
│
├── planning_pipeline  (SequentialAgent)
│   ├── curriculum_planner_agent   — reads YAML syllabus, structures sessions
│   ├── content_agent              — finds YouTube videos per topic
│   └── plan_saver_agent           — persists plan + sessions to Cloud SQL
│
├── scheduling_pipeline  (SequentialAgent)
│   ├── calendar_agent             — creates Google Calendar events
│   └── email_agent                — sends plan email to student + parent
│
├── tutoring_pipeline  (SequentialAgent)
│   ├── tutor_agent                — teaches concepts with live code execution
│   └── response_formatter         — formats output for clean UI display
│
├── notes_pipeline  (SequentialAgent)
│   └── docs_agent                 — creates/appends Google Docs study notes
│
├── assessment_pipeline  (SequentialAgent)
│   └── assessment_agent           — serves YAML quiz questions, evaluates answers, stores scores in DB
│
└── report_pipeline  (SequentialAgent)
    └── report_email_agent         — sends progress report email to student + parent after assessment
```

### Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | Google ADK (`google-adk`) |
| LLM (most agents) | `gemini-2.5-pro` — orchestrator, curriculum planner, content, calendar, email, docs, tutor, assessment |
| LLM (plan saver) | `gemini-2.5-flash-lite` — simple MCP tool calls only; Pro's thinking mode suppresses output_key writes for pure tool-call sequences |
| LLM (audio transcription) | `gemini-2.5-flash-lite` — separate quota, Streamlit layer only; never touches agent quota |
| Code Execution | `BuiltInCodeExecutor` — sandboxed Python for math verification |
| Curriculum Data | YAML files — syllabus + quiz questions (zero DB cost) |
| Database | Cloud SQL PostgreSQL 15 — plans, sessions, assessments, progress |
| Database MCP | MCP Toolbox for Databases |
| Workspace Tools | Google API Python Client — Calendar, Gmail, Docs, Drive (OAuth2) |
| Video Search | YouTube Data API v3 |
| Frontend | Streamlit — streaming chat, video embed, voice input |
| Backend API | FastAPI + ADK `get_fast_api_app()` |
| Deployment | Google Cloud Run (3 services) |

---

## Key Features

### Grade-Aware Teaching
Four grade bands (Foundation 5-6 / Building 7-8 / Bridging 9-10 / Advanced 11-12) each with a distinct tutor persona — vocabulary, examples, hooks, and YouTube content all adapt to the student's grade.

### Voice Input (Multilingual)
Students speak in any language (Hindi, Tamil, Telugu, Bengali, and 70+ more). `gemini-2.5-flash-lite` transcribes in Streamlit before the text reaches the backend — main agents never process raw audio, preserving their quota.

### YAML Curriculum (Zero DB Cost)
Syllabus structure and quiz questions live in `data/curricula/cbse/math/grade-{7-10}.yaml`. Auto-discovered at startup. Community-extensible — add a new grade by adding a YAML file, no code change.

### Google Workspace Integration
Real Calendar events with tutor starter prompts, real Gmail delivery to student + parent, real Google Docs study notes that grow session-by-session in Google Drive.

### Duplicate-Safe Notes
`notes_saved_topics` in session state tracks which topics have already been appended to the study doc. If a student re-asks to learn the same topic, the orchestrator skips `notes_pipeline` — no duplicate sections in the doc.

### Post-Assessment Parent Report
After every quiz, `report_pipeline` automatically emails a structured progress report (score, weak areas, doc link, next session) to the parent. Uses a dedicated `report_email_agent` instance — separate from the `email_agent` in `scheduling_pipeline` due to ADK's one-parent-per-agent rule.

---

## Repository Structure

```
├── eduflow_agents/          # ADK agent package
│   ├── agent.py             # root_agent + all 5 pipelines
│   ├── subagents/           # 8 individual agents
│   ├── prompts/             # all instruction strings
│   └── tools/               # YouTube search, curriculum loader, workspace tools
├── data/curricula/          # YAML curriculum files (CBSE Math Grade 7-10)
├── mcp_servers/database/    # MCP Toolbox config (tools.yaml)
├── scripts/infra/           # DB setup, Toolbox start scripts
├── main.py                  # FastAPI backend
├── streamlit_app.py         # Student-facing UI
├── Dockerfile.backend
├── Dockerfile.frontend
└── Dockerfile.toolbox
```

---

## Local Setup

### Prerequisites
- Python 3.12+
- Google Cloud project with Vertex AI, Cloud SQL, YouTube Data API enabled
- OAuth2 credentials for Google Workspace (Calendar, Gmail, Docs, Drive)
- `gcloud` CLI authenticated (`gcloud auth application-default login`)
- MCP Toolbox binary

### Steps

```bash
# 1. Clone and create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell

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

---

## Database Schema (Cloud SQL)

4 custom tables alongside ADK's auto-managed session tables:

| Table | Purpose |
|---|---|
| `learning_plans` | One row per student learning goal |
| `study_sessions` | Individual sessions within a plan, with Calendar/Doc IDs |
| `assessments` | Quiz scores, correct answers, weak areas per topic |
| `progress` | Aggregated mastery level per student per topic |

Student profile (name, email, grade, language) is stored in ADK's `user_states` table via `user:` prefixed state — no custom students table needed.

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `GOOGLE_GENAI_USE_VERTEXAI` | `1` for Vertex AI, `0` for API key |
| `GOOGLE_API_KEY` | Gemini API key (dev) |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` |
| `YOUTUBE_API_KEY` | YouTube Data API v3 |
| `GOOGLE_OAUTH_CLIENT_ID` | Google Workspace OAuth2 client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google Workspace OAuth2 client secret |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | Pre-authorized OAuth2 refresh token |
| `MCP_TOOLBOX_URL` | `http://localhost:5000/mcp` (local) or Cloud Run URL |
| `SESSION_DB_URI` | `postgresql+asyncpg://...` for Cloud SQL (production) |
| `BACKEND_URL` | Backend URL for Streamlit frontend |

---

## Cloud Run Deployment

Three services deployed to Google Cloud Run:

| Service | Purpose |
|---|---|
| `eduflow-frontend` | Streamlit UI |
| `eduflow-backend` | FastAPI + ADK agents |
| `eduflow-toolbox` | MCP Toolbox → Cloud SQL |
