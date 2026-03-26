# CLAUDE.md — EduFlow: Multi-Agent Academic Productivity System

This file defines the project conventions, architecture decisions, and guidelines for Claude Code
when working in this repository. Read this before making any changes.

---

## 1. Project Overview

A multi-agent AI system built on **Google ADK** (Agent Development Kit) with **Gemini 2.5 Flash**
that helps students manage their learning lifecycle — from planning study sessions to tracking
progress and keeping parents informed. Students describe a learning goal (e.g., "learn quadratic
equations in 1 week") and the system plans sessions, schedules calendar events, finds video
resources, teaches concepts, assesses understanding, and emails progress reports.

**Hackathon:** Google Cloud Gen AI Academy — APAC Edition (Hack2Skill Vision platform)
**Submission deadline:** 2026-04-08
**Problem statement:** Build a multi-agent AI system that helps users manage tasks, schedules, and
information by interacting with multiple tools and data sources.

### How EduFlow maps to the problem statement

| Requirement | EduFlow implementation |
|---|---|
| Primary agent coordinating sub-agents | Orchestrator routes to 6 specialised agents |
| Store and retrieve structured data | AlloyDB: students, syllabus, plans, progress, assessments |
| Multiple tools via MCP | Google Calendar, Gmail, Database (AlloyDB via MCP Toolbox) |
| Multi-step workflows | Plan → Schedule → Learn → Assess → Report → Adapt |
| API-based deployment | FastAPI on Cloud Run (3 services) |

### Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | Google ADK (`google-adk`) |
| LLM | `gemini-2.5-flash` (default for all agents) |
| Code Execution | `BuiltInCodeExecutor` (sandboxed Python, math/physics only) |
| Web Search | `GoogleSearchTool` (Gemini-native grounding) |
| Database | AlloyDB (PostgreSQL-compatible, pgvector + ScaNN) |
| Database MCP | MCP Toolbox for Databases (`tools.yaml`) |
| Calendar MCP | Google Calendar API via MCP server |
| Email MCP | Gmail API via MCP server |
| Video Search | YouTube Data API v3 (function tool) |
| Frontend | Streamlit (streaming chat + video embed + progress dashboard) |
| Backend API | FastAPI (`get_fast_api_app()` + `DatabaseSessionService`) |
| Runtime | Python 3.12+ |
| Dev runner | `adk web` (local dev), Cloud Run (production) |
| Deployment | Google Cloud Run (3 services) + AlloyDB |

---

## 2. Repository Structure

```
eduflow/
├── eduflow_agents/                     # ADK agent package (entrypoint for `adk web`)
│   ├── __init__.py                     # Imports agent module (required by ADK)
│   ├── agent.py                        # Defines root_agent (orchestrator) + all pipelines
│   ├── .env                            # API keys — never commit
│   ├── tools/                          # Shared tool instances
│   │   ├── __init__.py                 # Exports: google_search, code_executor
│   │   └── youtube_search.py           # YouTube Data API v3 function tool
│   ├── subagents/                      # Self-contained agents
│   │   ├── __init__.py
│   │   ├── curriculum_planner.py       # Plans learning sessions from syllabus
│   │   ├── content_agent.py            # Finds YouTube videos, generates summaries
│   │   ├── calendar_agent.py           # MCP: Google Calendar event management
│   │   ├── email_agent.py              # MCP: Gmail — plans, reports, alerts
│   │   ├── tutor_agent.py              # Teaches concepts with code execution
│   │   ├── assessment_agent.py         # Generates quizzes, evaluates answers
│   │   └── response_formatter.py       # Formats tutor output (reuse pattern)
│   └── prompts/                        # All agent instruction strings
│       ├── __init__.py
│       ├── orchestrator_prompt.py
│       ├── curriculum_planner_prompt.py
│       ├── content_agent_prompt.py
│       ├── calendar_agent_prompt.py
│       ├── email_agent_prompt.py
│       ├── tutor_agent_prompt.py
│       ├── assessment_agent_prompt.py
│       └── response_formatter_prompt.py
├── mcp_servers/                        # Custom MCP server configurations
│   ├── calendar/                       # Google Calendar MCP server
│   │   ├── server.py
│   │   └── requirements.txt
│   ├── gmail/                          # Gmail MCP server
│   │   ├── server.py
│   │   └── requirements.txt
│   └── database/                       # MCP Toolbox config (AlloyDB)
│       └── tools.yaml
├── scripts/
│   ├── data_pipeline/                  # Syllabus and seed data ingestion
│   │   └── seed_syllabus.py
│   └── infra/                          # Infrastructure setup scripts
│       ├── setup_alloydb.sh
│       ├── start_toolbox.sh
│       ├── start_toolbox.ps1
│       └── env.ps1.example
├── main.py                             # FastAPI backend
├── streamlit_app.py                    # Student-facing UI
├── requirements-backend.txt
├── requirements-ui.txt
├── Dockerfile.backend
├── Dockerfile.frontend
├── Dockerfile.toolbox
├── CLAUDE.md                           # This file
└── README.md
```

> **Note:** `eduflow_agents/` is the ADK package root. Run `adk web` from the repo root.
> ADK lists all subdirectories — always select `eduflow_agents` from the dropdown.

---

## 3. Agent Architecture

### 3.1 Hierarchy

```
orchestrator_agent (LlmAgent — root, understands intent, coordinates workflow)
│
├── planning_pipeline (SequentialAgent)
│   ├── curriculum_planner_agent    (LlmAgent — database MCP tools)
│   │   Breaks "learn X in Y days" into structured sessions
│   │   Queries syllabus DB for topics, prerequisites, sequence
│   │   Adapts plan based on student performance data
│   └── content_agent               (LlmAgent — youtube_search tool)
│       Finds YouTube videos per topic
│       Generates session summaries and study material outlines
│
├── scheduling_pipeline (SequentialAgent)
│   ├── calendar_agent              (LlmAgent — Calendar MCP tools)
│   │   Creates Google Calendar events for each session
│   │   Includes video links and topic summaries in event description
│   │   Handles rescheduling when student falls behind
│   └── email_agent                 (LlmAgent — Gmail MCP tools)
│       Sends learning plan to student + parent
│       Sends session reminders
│       Sends progress reports after assessments
│
├── tutoring_pipeline (SequentialAgent)
│   ├── tutor_agent                 (LlmAgent — code_executor)
│   │   Explains concepts, answers questions
│   │   Uses code execution for math/physics verification
│   └── response_formatter          (LlmAgent — include_contents='none')
│       Formats tutor output into clean textbook-style response
│
└── assessment_pipeline (SequentialAgent)
    └── assessment_agent            (LlmAgent — database MCP tools)
        Generates quizzes per topic from DB or AI-generated
        Evaluates answers (deterministic + LLM)
        Stores scores and weak areas in DB
        Triggers email_agent for progress report to parent
```

### 3.2 Agent Roles

| Agent | Type | MCP/Tools | Role |
|---|---|---|---|
| `orchestrator_agent` | LlmAgent | — | Understands student intent, routes to correct pipeline, manages multi-step workflow state |
| `curriculum_planner_agent` | LlmAgent | Database MCP | Queries syllabus, creates structured multi-session learning plans |
| `content_agent` | LlmAgent | `youtube_search` | Finds relevant educational videos per topic, generates summaries |
| `calendar_agent` | LlmAgent | Calendar MCP | Creates/updates/cancels Google Calendar events for study sessions |
| `email_agent` | LlmAgent | Gmail MCP | Sends plans, reminders, progress reports to student and parent |
| `tutor_agent` | LlmAgent | `code_executor` | Teaches concepts, explains step-by-step, answers follow-up questions |
| `assessment_agent` | LlmAgent | Database MCP | Generates quizzes, evaluates answers, tracks performance in DB |
| `response_formatter` | LlmAgent | — | Pure formatting of tutor output (no tools, `include_contents='none'`) |

### 3.3 Orchestration Pattern

Same as the tutor project: `orchestrator_agent` is an **LlmAgent with AgentTool-wrapped pipelines**.
Each pipeline is a SequentialAgent that runs silently — only the orchestrator's final relay is visible
to the student. This prevents intermediate agent outputs from cluttering the chat.

### 3.4 Multi-Step Workflow (The Core Demo)

```
Student: "I want to learn Quadratic Equations in 1 week"
  │
  ├─► [1] Orchestrator identifies: learning goal + timeframe
  │
  ├─► [2] planning_pipeline:
  │       curriculum_planner queries syllabus DB → breaks into 4 sessions
  │       content_agent finds YouTube videos for each session topic
  │       Output: structured plan with topics, videos, dates
  │
  ├─► [3] scheduling_pipeline:
  │       calendar_agent creates 4 Google Calendar events
  │       email_agent sends learning plan to student + parent
  │       Output: confirmation of events created + emails sent
  │
  │   ── Student returns for Session 1 ──
  │
  ├─► [4] tutoring_pipeline:
  │       tutor_agent teaches "Basics & Standard Form"
  │       response_formatter formats the explanation
  │       Output: clean lesson with embedded video reference
  │
  ├─► [5] assessment_pipeline:
  │       assessment_agent generates quiz on session topic
  │       Evaluates answers, stores score + weak areas in DB
  │       Output: feedback + performance summary
  │
  ├─► [6] scheduling_pipeline (again):
  │       email_agent sends progress report to parent
  │       calendar_agent updates remaining sessions if adaptation needed
  │
  └─► [7] Orchestrator: summarises session, previews next session
```

### 3.5 Session State Keys

| Key | Set by | Used by | Purpose |
|---|---|---|---|
| `user:name` | UI profile form | orchestrator prompt | Student's name |
| `user:email` | UI profile form | email_agent | Student's email for Calendar/Gmail |
| `user:parent_email` | UI profile form | email_agent | Parent's email for reports |
| `user:grade_level` | UI profile form | curriculum_planner | Grade-appropriate content |
| `user:preferred_language` | UI profile form | All agents | Response language |
| `current_plan_id` | curriculum_planner | All agents | Active learning plan reference |
| `current_session_id` | orchestrator | tutor, assessment | Current study session reference |
| `session_topic` | curriculum_planner | tutor, content | Current session's topic |
| `session_video_url` | content_agent | UI (embed) | YouTube video for current session |
| `tutor_solution` | tutor_agent | response_formatter | Raw tutor output (same pattern as AI Tutor project) |
| `formatted_response` | response_formatter | orchestrator | Formatted tutor output |
| `assessment_result` | assessment_agent | orchestrator, email | Quiz score + feedback |

---

## 4. MCP Tool Architecture

### 4.1 Tool Assignment by Agent

| Agent | Database MCP | Calendar MCP | Gmail MCP | `youtube_search` | `code_executor` |
|---|:---:|:---:|:---:|:---:|:---:|
| `curriculum_planner_agent` | ✓ | — | — | — | — |
| `content_agent` | — | — | — | ✓ | — |
| `calendar_agent` | — | ✓ | — | — | — |
| `email_agent` | — | — | ✓ | — | — |
| `tutor_agent` | — | — | — | — | ✓ |
| `assessment_agent` | ✓ | — | — | — | — |
| `response_formatter` | — | — | — | — | — |
| `orchestrator_agent` | — | — | — | — | — |

> **Constraint carried from AI Tutor project:** `code_executor` (Gemini built-in) cannot coexist
> with function-calling tools (MCP tools) in the same agent. This is why `tutor_agent` uses ONLY
> `code_executor` and database access is on separate agents.

### 4.2 MCP Servers

#### Database MCP (MCP Toolbox for Databases → AlloyDB)

Reuses the exact pattern from the AI Tutor project. `tools.yaml` defines parameterised SQL tools.

**Tools exposed:**

| Tool | Purpose | SQL pattern |
|---|---|---|
| `get-syllabus-topics` | Fetch topics for a subject + grade in sequence order | `SELECT ... FROM syllabus WHERE grade=$1 AND subject=$2 ORDER BY sequence_order` |
| `get-topic-prerequisites` | Check prerequisite topics | `SELECT ... FROM syllabus WHERE id = ANY($1::uuid[])` |
| `get-student-profile` | Fetch student + parent email | `SELECT ... FROM students WHERE id=$1` |
| `save-learning-plan` | Insert a new learning plan | `INSERT INTO learning_plans ...` |
| `save-session` | Insert a session within a plan | `INSERT INTO sessions ...` |
| `save-assessment` | Store quiz result + weak areas | `INSERT INTO assessments ...` |
| `get-student-progress` | Fetch progress for adaptation | `SELECT ... FROM progress WHERE student_id=$1` |
| `update-progress` | Update mastery level after assessment | `UPDATE progress SET mastery_level=$1 ...` |
| `get-quiz-questions` | Fetch questions for a topic | `SELECT ... FROM questions WHERE topic_id=$1 AND difficulty<=$2` |

#### Google Calendar MCP Server

Custom lightweight MCP server wrapping Google Calendar API v3.

**Tools exposed:**

| Tool | Purpose |
|---|---|
| `create-event` | Create a calendar event (title, datetime, duration, description with video link) |
| `update-event` | Reschedule or update an existing event |
| `delete-event` | Cancel a study session |
| `list-events` | List upcoming study sessions for a student |

**Auth:** OAuth2 with pre-authorized refresh token for demo. Service account for production.
Research needed on Day 1: evaluate existing open-source Calendar MCP servers vs building custom.

#### Gmail MCP Server

Custom lightweight MCP server wrapping Gmail API v1.

**Tools exposed:**

| Tool | Purpose |
|---|---|
| `send-email` | Send email to student or parent (plan, report, alert) |
| `send-email-with-template` | Send using predefined templates (plan summary, progress report) |

**Auth:** Same OAuth2 pattern as Calendar MCP.
Research needed on Day 1: evaluate existing open-source Gmail MCP servers vs building custom.

### 4.3 YouTube Search Function Tool

Not an MCP tool — a regular ADK function tool using YouTube Data API v3.

```python
def youtube_search(query: str, max_results: int = 3) -> str:
    """Search YouTube for educational videos matching the query.

    Args:
        query: Search terms (e.g., "quadratic equations grade 10 tutorial")
        max_results: Number of results to return (default 3)

    Returns:
        JSON string with video titles, URLs, channel names, and durations.
    """
```

**API key:** YouTube Data API v3 key (free tier: 10,000 units/day, search costs 100 units = 100 searches/day).

---

## 5. Database Schema (AlloyDB)

### 5.1 Core Tables

```sql
-- Student profiles
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    email VARCHAR(200),
    parent_email VARCHAR(200),
    grade VARCHAR(20) NOT NULL,          -- 'Grade 5', 'Grade 10', 'Undergraduate'
    preferred_language VARCHAR(50) DEFAULT 'English',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Syllabus structure: grade → subject → chapter → topics
CREATE TABLE syllabus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grade VARCHAR(20) NOT NULL,
    subject VARCHAR(50) NOT NULL,         -- 'math', 'physics', 'biology', etc.
    chapter VARCHAR(200) NOT NULL,        -- 'Quadratic Equations'
    topic VARCHAR(200) NOT NULL,          -- 'Standard Form', 'Factoring Method'
    description TEXT,                     -- Brief topic description for planner context
    prerequisites UUID[],                 -- Array of prerequisite topic IDs
    sequence_order INT NOT NULL,          -- Order within the chapter
    estimated_minutes INT DEFAULT 45,     -- Estimated study time
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON syllabus (grade, subject);
CREATE INDEX ON syllabus (grade, subject, chapter);

-- Learning plans
CREATE TABLE learning_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    subject VARCHAR(50) NOT NULL,
    goal TEXT NOT NULL,                   -- "Learn Quadratic Equations"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_sessions INT NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'paused'
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON learning_plans (student_id, status);

-- Individual study sessions within a plan
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES learning_plans(id),
    topic_id UUID REFERENCES syllabus(id),
    session_number INT NOT NULL,          -- 1, 2, 3, 4...
    scheduled_date DATE,
    scheduled_time TIME,
    video_url TEXT,                        -- YouTube video link
    video_title VARCHAR(500),
    summary TEXT,                          -- AI-generated session summary
    calendar_event_id VARCHAR(200),       -- Google Calendar event ID (for updates)
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'skipped'
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON sessions (plan_id, session_number);

-- Assessment results
CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    student_id UUID REFERENCES students(id),
    topic_id UUID REFERENCES syllabus(id),
    score DECIMAL(5,2),                    -- Percentage score
    total_questions INT,
    correct_answers INT,
    weak_areas TEXT[],                     -- Array of identified weak sub-topics
    feedback TEXT,                         -- AI-generated feedback summary
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON assessments (student_id, topic_id);

-- Aggregated progress tracking
CREATE TABLE progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    topic_id UUID REFERENCES syllabus(id),
    mastery_level VARCHAR(20) DEFAULT 'not_started',  -- 'not_started', 'beginner', 'intermediate', 'mastered'
    best_score DECIMAL(5,2),
    attempts INT DEFAULT 0,
    last_assessed TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(student_id, topic_id)
);
CREATE INDEX ON progress (student_id);

-- Quiz question bank (per topic)
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID REFERENCES syllabus(id),
    difficulty INT CHECK (difficulty BETWEEN 1 AND 5),
    question_text TEXT NOT NULL,
    options JSONB,                          -- MCQ: ["A. ...", "B. ...", "C. ...", "D. ..."]
    correct_option VARCHAR(5),
    explanation TEXT,                       -- Why the answer is correct
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON questions (topic_id, difficulty);
```

### 5.2 Seed Data Strategy

**Syllabus data:** Seed Grade 7-10 Math syllabus (CBSE/ICSE-aligned) covering major chapters.
Start with Math only for the demo — other subjects are structurally identical.

**Quiz questions:** AI-generated via Gemini for seeded syllabus topics. 5-10 questions per topic.

---

## 6. Coding Conventions

### 6.1 File & Variable Naming

Carried forward from AI Tutor project:

| What | Convention | Example |
|---|---|---|
| Agent module | `<role>.py` | `curriculum_planner.py`, `email_agent.py` |
| Prompt module | `<agent_name>_prompt.py` | `curriculum_planner_prompt.py` |
| Agent variable | `<name>_agent` | `curriculum_planner_agent`, `email_agent` |
| Prompt constant | `<AGENT_NAME>_INSTRUCTION` | `CURRICULUM_PLANNER_INSTRUCTION` |
| ADK `name=` field | `snake_case` | `curriculum_planner_agent` |

### 6.2 Agent Construction Rules

1. **Prompts in `prompts/` only.** Never inline instruction strings in agent files.
2. **Tools from `tools/` only.** Import shared tool instances; never instantiate in agent files.
3. **Relative imports within `eduflow_agents` package.**
4. **One `output_key` per pipeline role:** tutors write `tutor_solution`, formatter writes `formatted_response`.
5. **`include_contents='none'` on response_formatter** — same pattern as AI Tutor project.
6. **`before_agent_callback` requires documented reason** — same discipline as AI Tutor project.
7. **Each formatter instance via `make_response_formatter(name)`** — one-parent rule.

### 6.3 Model

Default: `gemini-2.5-flash` for all agents. Do not hardcode in multiple places.

---

## 7. Frontend (Streamlit)

### 7.1 Layout

```
┌─────────────────────────────────────────────────────────┐
│  Sidebar                    │  Main Content              │
│  ┌───────────────────────┐  │  ┌───────────────────────┐ │
│  │ Student Profile        │  │  │ Session Header        │ │
│  │ Name / Email / Grade   │  │  │ Topic + Video embed   │ │
│  │ Parent Email           │  │  │                       │ │
│  │ Language                │  │  └───────────────────────┘ │
│  │ [Save Profile]         │  │  ┌───────────────────────┐ │
│  └───────────────────────┘  │  │ Chat (streaming SSE)   │ │
│  ┌───────────────────────┐  │  │                       │ │
│  │ Quick Actions          │  │  │ Student ↔ Tutor       │ │
│  │ [Plan a Study Session] │  │  │                       │ │
│  │ [Start Next Session]   │  │  │                       │ │
│  │ [Take a Quiz]          │  │  │                       │ │
│  │ [View My Progress]     │  │  │                       │ │
│  └───────────────────────┘  │  │                       │ │
│  ┌───────────────────────┐  │  └───────────────────────┘ │
│  │ Current Plan           │  │  ┌───────────────────────┐ │
│  │ Session 1 ✅           │  │  │ [Chat input]           │ │
│  │ Session 2 🔵 (today)   │  │  └───────────────────────┘ │
│  │ Session 3 ⏳           │  │                            │
│  │ Session 4 ⏳           │  │                            │
│  └───────────────────────┘  │                            │
│  🟢 Backend connected       │                            │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Key UI Features

- **Video embedding:** `st.video(youtube_url)` in the session header area
- **Plan progress tracker:** Sidebar shows session status (completed/current/upcoming)
- **Streaming chat:** SSE from `/run_sse` — same pattern as AI Tutor project
- **Session state in URL:** `uid`, `sid` in query params for refresh persistence
- **Health check:** Cached (30s TTL), no backend URL exposed in UI

### 7.3 Patterns Reused from AI Tutor

- `_init_session()` with conditional `st.query_params` writes
- `_stream_agent_response()` SSE generator with fallback text logic
- `_build_state_delta()` for user profile state injection
- Cached `_backend_status()` for non-blocking health check
- Empty response detection ("tutor is warming up" message)

---

## 8. Cloud Run Deployment

### 8.1 Service Architecture

```
Student Browser
    │
    ▼  HTTPS
Cloud Run: eduflow-frontend (Streamlit)
    │
    ▼  POST /run_sse
Cloud Run: eduflow-backend (FastAPI + ADK agents)
    │
    ├─► Calendar MCP server (in-process or sidecar)
    ├─► Gmail MCP server (in-process or sidecar)
    │
    ├─► MCP Toolbox ─── Cloud Run: eduflow-toolbox
    │                       │
    │                       ▼
    │                   AlloyDB (asia-southeast1)
    │                       ├── students, syllabus, learning_plans
    │                       ├── sessions, assessments, progress
    │                       └── questions
    │
    ▼
Google APIs (Calendar, Gmail, YouTube)
```

### 8.2 Environment Variables

| Variable | Service | Purpose |
|---|---|---|
| `GOOGLE_GENAI_USE_VERTEXAI` | backend | `0` for dev (API key), `1` for prod |
| `GOOGLE_API_KEY` | backend | Gemini API key (dev only) |
| `GOOGLE_CLOUD_PROJECT` | backend | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | backend | `us-central1` (Gemini endpoint — NOT asia-southeast1) |
| `MCP_TOOLBOX_URL` | backend | URL to MCP Toolbox Cloud Run service |
| `SESSION_DB_URI` | backend | `postgresql+asyncpg://...` for AlloyDB |
| `YOUTUBE_API_KEY` | backend | YouTube Data API v3 key |
| `GOOGLE_OAUTH_CLIENT_ID` | backend | OAuth2 for Calendar + Gmail |
| `GOOGLE_OAUTH_CLIENT_SECRET` | backend | OAuth2 for Calendar + Gmail |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | backend | Pre-authorized token for demo |
| `BACKEND_URL` | frontend | URL to backend Cloud Run service |

### 8.3 Known Gotchas (Carried from AI Tutor)

- **`GOOGLE_CLOUD_LOCATION`**: Must be `us-central1`, not `asia-southeast1` (Gemini DNS fails in SEA)
- **MCP Toolbox IAM**: Needs `allUsers` invoker — ADK MCPToolset uses plain httpx with no auth
- **Alpine + Go binary**: Toolbox Dockerfile needs `apk add gcompat` for glibc shim
- **`PORT` is reserved**: Never set as env var on Cloud Run
- **AlloyDB `@` in password**: URL-encode as `%40`
- **Cold start**: Handle empty SSE response gracefully in frontend

---

## 9. Implementation Phases (10-Day Plan)

### Phase 1: Foundation + Research (Days 1-2)
> **Goal:** Project setup, schema design, validate MCP server approach for Calendar/Gmail.

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 1.1 | **Project scaffold** | Critical | Git repo, virtualenv, `eduflow_agents/` package, CLAUDE.md, .gitignore, .env.example |
| 1.2 | **AlloyDB schema** | Critical | Create all tables from Section 5. Reuse AlloyDB cluster from AI Tutor project. |
| 1.3 | **Seed syllabus data** | Critical | Grade 7-10 Math (CBSE-aligned). 4-5 chapters, 3-5 topics each. Script: `seed_syllabus.py` |
| 1.4 | **MCP server research** | Critical | Evaluate existing Calendar/Gmail MCP servers for ADK compatibility. Decision: build custom vs reuse. |
| 1.5 | **YouTube API setup** | High | Get API key, test search endpoint, build `youtube_search` function tool |
| 1.6 | **OAuth2 setup** | High | Google Cloud Console: enable Calendar + Gmail APIs, create OAuth client, get refresh token |

### Phase 2: MCP Tools + Database Layer (Days 3-4)
> **Goal:** All MCP tools working and tested independently.

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 2.1 | **Database MCP (MCP Toolbox)** | Critical | `tools.yaml` with all SQL tools from Section 4.2. Test with `curl` against local toolbox. |
| 2.2 | **Calendar MCP server** | Critical | Build/configure server. Test: create event, list events, update event. |
| 2.3 | **Gmail MCP server** | Critical | Build/configure server. Test: send email to test address. |
| 2.4 | **YouTube function tool** | High | `youtube_search.py` in tools/. Test: search returns video URLs. |
| 2.5 | **Quiz question seeding** | High | AI-generate 5-10 MCQ questions per seeded topic. Script: `seed_questions.py` |

### Phase 3: Agent Implementation (Days 5-6)
> **Goal:** All 7 agents implemented and working in `adk web`.

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 3.1 | **orchestrator_agent** | Critical | Root agent with AgentTool-wrapped pipelines. Routing logic for plan/teach/assess/schedule intents. |
| 3.2 | **curriculum_planner_agent** | Critical | Queries syllabus DB, creates structured session plans. Writes plan to DB. |
| 3.3 | **content_agent** | Critical | Uses youtube_search to find videos per topic. Returns video URLs + titles. |
| 3.4 | **calendar_agent** | Critical | Creates Google Calendar events for planned sessions. Stores event IDs in DB. |
| 3.5 | **email_agent** | Critical | Sends learning plan email + progress reports. Uses templates. |
| 3.6 | **tutor_agent** | High | Teaches concepts with code_executor. Reuse prompt patterns from AI Tutor. |
| 3.7 | **assessment_agent** | High | Fetches quiz from DB, evaluates answers, stores results, triggers progress update. |
| 3.8 | **response_formatter** | High | Reuse `make_response_formatter()` factory pattern from AI Tutor. |
| 3.9 | **Pipeline wiring** | Critical | SequentialAgent pipelines + AgentTool wrappers in `agent.py`. |

### Phase 4: Frontend (Days 7-8)
> **Goal:** Polished Streamlit UI with video embedding and progress dashboard.

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 4.1 | **FastAPI backend** | Critical | `main.py` with `get_fast_api_app()` + `DatabaseSessionService`. Reuse pattern. |
| 4.2 | **Streamlit chat UI** | Critical | Streaming SSE chat. Reuse `_stream_agent_response()` pattern. |
| 4.3 | **Student profile form** | Critical | Name, email, parent email, grade, language. Sidebar. |
| 4.4 | **Video embedding** | High | `st.video()` for YouTube URLs in session header. |
| 4.5 | **Plan progress tracker** | High | Sidebar panel showing session statuses within active plan. |
| 4.6 | **Quick actions** | High | "Plan a Study Session", "Start Next Session", "Take a Quiz", "View Progress" |

### Phase 5: Deployment + Demo (Days 9-10)
> **Goal:** Live on Cloud Run. Demo video recorded. Submission ready.

| # | Item | Priority | Notes |
|---|------|----------|-------|
| 5.1 | **Dockerfiles** | Critical | Backend, frontend, toolbox. Reuse patterns from AI Tutor. |
| 5.2 | **Cloud Run deployment** | Critical | 3 services in asia-southeast1. |
| 5.3 | **End-to-end testing** | Critical | Full workflow: plan → schedule → teach → assess → report. |
| 5.4 | **Demo video (3 min)** | Critical | Problem → Solution → Live demo → Architecture → Impact. Upload to YouTube. |
| 5.5 | **Submission materials** | Critical | README, architecture diagram, judge access instructions. |

---

## 10. Demo Script (3-Minute Video)

```
[0:00-0:30] Problem: "250M+ APAC students lack structured learning support.
             Teachers are overwhelmed. Parents are disconnected from progress."

[0:30-0:50] Solution: "EduFlow — an AI system that plans, schedules, teaches,
             assesses, and reports. Not just a chatbot — a complete learning workflow."

[0:50-2:20] Live Demo:
  1. Student: "I want to learn Quadratic Equations in 1 week"
  2. Show: AI creates 4-session plan with topics and videos
  3. Show: Google Calendar — real events appeared!
  4. Show: Email inbox — parent received the learning plan!
  5. Student starts Session 1 — video embedded, tutor explains concept
  6. Student takes quiz — AI evaluates, stores results
  7. Show: Parent receives progress report email
  8. Show: Progress dashboard in sidebar

[2:20-2:50] Architecture: ADK multi-agent → MCP (Calendar, Gmail, Database) →
             AlloyDB → Cloud Run. Highlight: 7 agents, 4 MCP tools, 11-step workflow.

[2:50-3:00] "EduFlow: Because every student deserves a personal learning manager."
```

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Calendar/Gmail OAuth2 complexity | High | Research Day 1. Fallback: use service account or mock the API for demo |
| YouTube API quota (100 searches/day free) | Medium | Cache results in DB. Pre-seed popular topic videos. |
| Vertex AI rate limits | High | Use API key for demo (same lesson from AI Tutor). Request quota increase early. |
| Scope creep on tutoring quality | Medium | Keep tutor_agent simple. The WORKFLOW is the star, not explanation depth. |
| 10-day timeline pressure | High | Math-only for demo. Other subjects are structurally identical — mention in roadmap. |
| Cold start on Cloud Run | Low | Handled: empty response detection + "warming up" message (proven pattern). |

---

## 12. What's Reused vs New

| Component | Reused from AI Tutor | New for EduFlow |
|---|---|---|
| ADK agent framework | ✓ | — |
| SequentialAgent + AgentTool pattern | ✓ | — |
| MCP Toolbox for Databases | ✓ | New tools.yaml with different SQL |
| AlloyDB cluster | ✓ (same cluster, new DB) | New schema |
| Cloud Run deployment pattern | ✓ | — |
| Dockerfile patterns | ✓ | — |
| Streamlit SSE streaming | ✓ | Video embed + progress panel new |
| FastAPI backend | ✓ | — |
| response_formatter pattern | ✓ | — |
| code_executor on tutor | ✓ | — |
| Google Calendar MCP | — | **New** |
| Gmail MCP | — | **New** |
| YouTube search tool | — | **New** |
| Curriculum planner agent | — | **New** |
| Multi-step workflow orchestration | — | **New** |
| Student progress tracking | — | **New** |
| Parent notification system | — | **New** |

---

## 13. Local Development

```bash
# Create and activate virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install google-adk

# Set up environment
cp eduflow_agents/.env.example eduflow_agents/.env   # fill in API keys

# Start MCP Toolbox (database tools)
# Windows:
.\scripts\infra\start_toolbox.ps1
# Linux/macOS:
bash scripts/infra/start_toolbox.sh

# Run agents locally
adk web   # select 'eduflow_agents' from dropdown

# Run full stack (backend + frontend)
uvicorn main:app --reload --port 8000
streamlit run streamlit_app.py
```

**Required environment variables (local):**
```
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=<gemini-api-key>
YOUTUBE_API_KEY=<youtube-data-api-key>
GOOGLE_OAUTH_REFRESH_TOKEN=<pre-authorized-token>
```
