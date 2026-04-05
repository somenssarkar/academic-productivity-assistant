# CLAUDE.md — EduFlow: Multi-Agent Academic Productivity System

This file defines the project conventions, architecture decisions, and guidelines for Claude Code
when working in this repository. Read this before making any changes.

---

## 1. Project Overview

A multi-agent AI system built on **Google ADK** (Agent Development Kit) with **Gemini 2.5 Pro**
that helps students manage their learning lifecycle — from planning study sessions to tracking
progress and keeping parents informed. Students describe a learning goal (e.g., "learn quadratic
equations in 1 week") and the system plans sessions, schedules calendar events, finds video
resources, teaches concepts, assesses understanding, and emails progress reports.

**Hackathon:** Google Cloud Gen AI Academy — APAC Edition (Hack2Skill Vision platform)
**Submission deadline:** 2026-04-08
**Problem statement:** Build a multi-agent AI system that helps users manage tasks, schedules, and
information by interacting with multiple tools and data sources.
**Demo scope:** Two subjects only — **Math + Physics** (Grade 7-10, CBSE-aligned). Math is the
universal pain point; Physics showcases `code_executor` with live simulations (projectile motion,
graphs). Together they prove multi-subject capability without scope creep.

### How EduFlow maps to the problem statement

| Requirement | EduFlow implementation |
|---|---|
| Primary agent coordinating sub-agents | Orchestrator coordinates 8 sub-agents via 5 pipelines |
| Store and retrieve structured data | YAML curriculum files (syllabus, questions) + Cloud SQL PostgreSQL 15 (plans, progress, assessments) |
| Multiple tools via MCP | Calendar, Gmail, Docs/Drive (via `gws` MCP) + Database (MCP Toolbox) |
| Multi-step workflows | Plan → Schedule → Notes → Teach → Assess → Report |
| API-based deployment | FastAPI on Cloud Run (3 services) |

### Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | Google ADK (`google-adk`) |
| LLM (agents) | `gemini-2.5-pro` (all 8 agents — planning, teaching, assessment; hackathon project quota for gemini-2.5-flash is exhausted; gemini-2.5-pro has 1M tokens/min quota in us-central1) |
| LLM (audio) | `gemini-2.5-flash-lite` (transcription only — separate quota from agents; `gemini-live-2.5-flash-native-audio` requires Live API/websockets, not usable for batch transcription) |
| Code Execution | `BuiltInCodeExecutor` (sandboxed Python, math/physics only) |
| Web Search | `GoogleSearchTool` (Gemini-native grounding) |
| Curriculum Data | YAML files in `data/curricula/` (syllabus, questions — static) |
| Database | Cloud SQL PostgreSQL 15 (runtime state only: plans, progress, assessments) |
| Database MCP | MCP Toolbox for Databases (`tools.yaml`) |
| Workspace Tools | Python function tools via `google-api-python-client` + OAuth2 — Calendar, Gmail, Docs, Drive (located in `eduflow_agents/tools/workspace/`) |
| Video Search | YouTube Data API v3 (function tool) |
| Frontend | Streamlit (streaming chat + video embed + progress dashboard) |
| Backend API | FastAPI (`get_fast_api_app()` + `DatabaseSessionService`) |
| Runtime | Python 3.12+ |
| Dev runner | `adk web` (local dev), Cloud Run (production) |
| Deployment | Google Cloud Run (3 services) + Cloud SQL PostgreSQL 15 |

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
│   │   ├── youtube_search.py           # YouTube Data API v3 function tool
│   │   └── curriculum_loader.py        # Loads YAML curriculum files at agent construction
│   ├── subagents/                      # Self-contained agents
│   │   ├── __init__.py
│   │   ├── curriculum_planner.py       # Plans learning sessions from syllabus
│   │   ├── content_agent.py            # Finds YouTube videos, generates summaries
│   │   ├── calendar_agent.py           # Workspace MCP: Google Calendar events
│   │   ├── email_agent.py              # Workspace MCP: Gmail — plans, reports
│   │   ├── docs_agent.py               # Workspace MCP: Google Docs study notes
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
│       ├── docs_agent_prompt.py
│       ├── tutor_agent_prompt.py
│       ├── assessment_agent_prompt.py
│       └── response_formatter_prompt.py
├── data/
│   └── curricula/                      # YAML curriculum files (replaces DB syllabus)
│       ├── _schema.yaml                # Pydantic validation schema
│       └── cbse/                       # Board/curriculum system
│           └── math/                   # Subject
│               ├── grade-7.yaml        # One file per grade+subject
│               ├── grade-8.yaml
│               ├── grade-9.yaml
│               └── grade-10.yaml
├── mcp_servers/                        # MCP server configurations
│   └── database/                       # MCP Toolbox config (AlloyDB)
│       └── tools.yaml
│   # Note: Calendar, Gmail, Docs, Drive all use Google Workspace
│   # CLI (`gws mcp`) — no custom MCP servers needed for these.
├── scripts/
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
│   ├── curriculum_planner_agent    (LlmAgent — YAML curriculum in context)
│   │   Breaks "learn X in Y days" into structured sessions
│   │   Uses YAML curriculum data injected into instruction at construction
│   │   Determines session count based on topic depth + prerequisites
│   ├── content_agent               (LlmAgent — youtube_search tool)
│   │   Finds YouTube videos per topic
│   │   Generates session summaries and study material outlines
│   └── plan_saver_agent            (LlmAgent — database MCP, gemini-2.5-flash-lite)
│       Saves learning plan + study sessions to Cloud SQL
│       Uses flash-lite: Pro's thinking mode suppresses output_key on pure tool-call sequences
│
├── scheduling_pipeline (SequentialAgent)
│   ├── calendar_agent              (LlmAgent — Workspace MCP: Calendar)
│   │   Creates Google Calendar events for each session
│   │   Includes video link, key concepts, and tutor starter prompt in event description
│   │   e.g. "Start your session: Ask EduFlow → 'Teach me Perfect Squares'"
│   └── email_agent                 (LlmAgent — Workspace MCP: Gmail)
│       Sends learning plan to student + parent (with Study Notes doc link)
│
│   NOTE: tasks_agent removed — Google Tasks API has restrictions on free personal
│   accounts that make it unsuitable for demo. Calendar + Docs + Gmail provide
│   equivalent scheduling and tracking capability.
│
├── tutoring_pipeline (SequentialAgent)
│   ├── tutor_agent                 (LlmAgent — code_executor)
│   │   Explains concepts, answers questions
│   │   Uses code execution for math/physics verification
│   └── response_formatter          (LlmAgent — include_contents='none')
│       Formats tutor output into clean textbook-style response
│
├── notes_pipeline (SequentialAgent)
│   └── docs_agent                  (LlmAgent — Workspace MCP: Docs + Drive)
│       Creates/updates formatted Google Doc study notes per chapter
│       Organizes in Drive folders: EduFlow/{Subject}/{Grade}/
│       Appends session summaries, key concepts, YouTube links
│       notes_saved_topics in state prevents duplicate insertions across sessions
│
├── assessment_pipeline (SequentialAgent)
│   └── assessment_agent            (LlmAgent — YAML questions + database MCP)
│       Quiz questions injected from YAML into instruction at runtime (no tool call needed)
│       Fuzzy case-insensitive topic matching across all chapters
│       Evaluates answers, stores scores + weak areas in DB via database MCP
│
└── report_pipeline (SequentialAgent)
    └── report_email_agent          (LlmAgent — Workspace MCP: Gmail)
        Separate email_agent instance (ADK one-parent rule — make_email_agent factory)
        Reads assessment_result from state
        Sends progress report to student + parent after quiz completion
```

### 3.2 Agent Roles

| Agent | Model | MCP/Tools | Role |
|---|---|---|---|
| `orchestrator_agent` | gemini-2.5-pro | — | Understands student intent, routes to correct pipeline, manages multi-step workflow state |
| `curriculum_planner_agent` | gemini-2.5-pro | YAML curriculum (in context) | Reads syllabus from YAML, creates structured multi-session learning plans |
| `content_agent` | gemini-2.5-pro | `youtube_search` | Finds relevant educational videos per topic, generates summaries |
| `calendar_agent` | gemini-2.5-pro | Workspace function tools (Calendar) | Creates Google Calendar events with topic, video link, and tutor starter prompt |
| `email_agent` | gemini-2.5-pro | Workspace function tools (Gmail) | Sends plans (with doc link) to student and parent via `scheduling_pipeline` |
| `report_email_agent` | gemini-2.5-pro | Workspace function tools (Gmail) | Sends progress reports after assessment via `report_pipeline` (separate instance due to one-parent rule) |
| `docs_agent` | gemini-2.5-pro | Workspace function tools (Docs+Drive) | Creates formatted study notes, organizes in Drive folders; skips if topic already in notes_saved_topics |
| `tutor_agent` | gemini-2.5-pro | `code_executor` | Teaches concepts, explains step-by-step, answers follow-up questions |
| `assessment_agent` | gemini-2.5-pro | Database MCP | YAML questions injected into context; evaluates answers, stores scores in DB |
| `plan_saver_agent` | gemini-2.5-flash-lite | Database MCP | Saves learning plan + sessions to Cloud SQL; flash-lite avoids Pro thinking-mode output suppression |
| `response_formatter` | gemini-2.5-pro | — | Pure formatting of tutor output (no tools, `include_contents='none'`) |

### 3.3 Orchestration Pattern

Same as the tutor project: `orchestrator_agent` is an **LlmAgent with AgentTool-wrapped pipelines**.
Each pipeline is a SequentialAgent that runs silently — only the orchestrator's final relay is visible
to the student. This prevents intermediate agent outputs from cluttering the chat.

### 3.4 Multi-Step Workflow (The Core Demo)

Five-stage flow centred on one student's complete learning journey.

```
Student: "I want to learn Squares and Square Roots in 3 days"
  │
  ├─► Stage 1 — PLAN
  │       curriculum_planner reads Grade 8 YAML → exact topic titles, session count,
  │         concepts, prerequisites, grade-appropriate duration
  │       content_agent searches YouTube → 3 real grade-appropriate videos
  │       Output: structured curriculum_plan + session_videos in state
  │
  ├─► Stage 2 — SCHEDULE  (automatic, same orchestrator turn)
  │       calendar_agent creates 3 Calendar events, each containing:
  │         - Topic title (verbatim from YAML), duration, YouTube video link
  │         - Tutor starter prompt: "Ask EduFlow → 'Teach me Perfect Squares'"
  │         - Link to EduFlow Streamlit app
  │       email_agent sends to student + parent:
  │         - Session plan table with video links
  │         - Link to Study Notes Google Doc (created in Stage 3)
  │         - Encouraging sign-off
  │       Output: calendar invites sent + parent email delivered
  │
  ├─► Stage 3 — NOTES  (triggered after scheduling, same turn)
  │       docs_agent creates Google Doc in Drive: EduFlow/Math/Grade 8/
  │         "Study Notes: Squares and Square Roots — Math Grade 8"
  │         Full chapter overview at plan time:
  │           H1: Chapter title
  │           H2 per session: topic title, key concepts, YouTube link
  │         Grows session-by-session: tutor appends notes after each lesson
  │       Output: doc_url stored in state → passed to email_agent + orchestrator
  │
  │   ── Student returns for Session 1 (sees calendar prompt, opens Streamlit) ──
  │
  ├─► Stage 4 — TUTOR
  │       tutor_agent teaches using:
  │         - Grade 8 "building" band persona (formal but approachable)
  │         - YAML concepts for the session topic injected via _build_instruction
  │           (reads curriculum_plan from state → matches topic → extracts concepts)
  │         - HOOK → EXPLAIN (ALL concepts) → EXAMPLE → SPARK structure enforced
  │         - code_executor: live Python verification (e.g. print(2**3), print(a**m))
  │         - Writes raw lesson to tutor_solution (output_key)
  │       response_formatter:
  │         - Reads tutor_solution from state via _build_formatter_instruction
  │         - include_contents='none' (no conversation history — only injected content)
  │         - Adds bold section headers: 🎯 Hook, 📖 Explanation, ✏️ Example, 💡 Spark
  │         - Writes formatted lesson to formatted_response (output_key)
  │       orchestrator displays formatted_response VERBATIM (never summarises)
  │       notes_pipeline (MODE B): docs_agent appends formatted_response to Drive doc
  │       Output: full formatted lesson in UI + session notes appended to Drive doc
  │
  └─► Stage 5 — ASSESS + REPORT
          assessment_agent serves YAML quiz questions for the session topic
          Evaluates answers, stores score + weak_areas in DB
          email_agent sends parent report:
            - Score, weak areas, Google Doc link, next session preview
          If weak areas detected → tutor revisits them in next session
          Output: parent notified + student progress tracked in DB
```

**Tool purpose mapping:**
- **Calendar** = WHEN + HOW TO START (time-blocked sessions + tutor prompt in invite)
- **Docs + Drive** = KNOWLEDGE (chapter overview at plan time, grows per session)
- **Gmail** = COMMUNICATION (plan email with doc link, parent progress reports)
- **AlloyDB** = DATA (structured persistence for plans, progress, assessments)
- **YouTube API** = CONTENT (grade-appropriate videos per topic)

> **Session count & duration:** The `curriculum_planner_agent` determines how many sessions
> a topic needs based on concept depth, prerequisite count, and grade band. Session duration
> is optimized for student attention: Foundation ~25 min, Building ~35 min, Bridging ~45 min,
> Advanced ~60 min.

### 3.5 Session State Keys

> ADK state prefixes: `user:` persists across ALL sessions for a user (stored in
> `user_states` table). No prefix = current session only. `temp:` = current turn only.
> See Section 5.1 for full ADK session architecture.

**User-scoped state (`user:` prefix — persists across sessions):**

| Key | Set by | Used by | Purpose |
|---|---|---|---|
| `user:name` | UI profile form | orchestrator prompt | Student's name |
| `user:email` | UI profile form | email_agent | Student's email for Calendar/Gmail |
| `user:parent_email` | UI profile form | email_agent | Parent's email for reports |
| `user:grade_level` | UI profile form | curriculum_planner | Grade-appropriate content |
| `user:preferred_language` | UI profile form | All agents | Response language |
| `user:grade_band` | orchestrator | tutor, content, curriculum_planner | `foundation`/`building`/`bridging`/`advanced` |

**Session-scoped state (no prefix — current conversation only):**

| Key | Set by | Used by | Purpose |
|---|---|---|---|
| `current_plan_id` | curriculum_planner | All agents | Active learning plan reference |
| `current_session_id` | orchestrator | tutor, assessment | Current study session reference |
| `session_topic` | curriculum_planner | tutor, content | Current session's topic |
| `session_video_url` | content_agent | UI (embed) | YouTube video for current session |
| `doc_url` | docs_agent | orchestrator, email | Google Doc URL for study notes |
| `drive_folder_id` | docs_agent | docs_agent | Drive folder ID (EduFlow/{Subject}/{Grade}/) |
| `tutor_solution` | tutor_agent | response_formatter | Raw tutor output (same pattern as AI Tutor project) |
| `formatted_response` | response_formatter | orchestrator | Formatted tutor output |
| `assessment_result` | assessment_agent | orchestrator, report_email_agent | Quiz score + feedback |
| `notes_saved_topics` | `set_user_profile(notes_saved=...)` | orchestrator | List of topics already appended to Google Doc; prevents duplicate insertions |
| `email_sent` | email_agent / report_email_agent | — | Confirmation that email was sent (output_key) |

---

## 4. MCP Tool Architecture

### 4.1 Tool Assignment by Agent

| Agent | Database MCP | Workspace (Cal) | Workspace (Gmail) | Workspace (Docs/Drive) | `youtube_search` | `code_executor` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `orchestrator_agent` | — | — | — | — | — | — |
| `curriculum_planner_agent` | — | — | — | — | — | — |
| `content_agent` | — | — | — | — | ✓ | — |
| `plan_saver_agent` | ✓ | — | — | — | — | — |
| `calendar_agent` | — | ✓ | — | — | — | — |
| `email_agent` | — | — | ✓ | — | — | — |
| `report_email_agent` | — | — | ✓ | — | — | — |
| `docs_agent` | — | — | — | ✓ | — | — |
| `tutor_agent` | — | — | — | — | — | ✓ |
| `assessment_agent` | ✓ | — | — | — | — | — |
| `response_formatter` | — | — | — | — | — | — |

> **Constraint carried from AI Tutor project:** `code_executor` (Gemini built-in) cannot coexist
> with function-calling tools (MCP tools) in the same agent. This is why `tutor_agent` uses ONLY
> `code_executor` and database access is on separate agents.

### 4.2 MCP Servers

#### MCP Server 1: Google Workspace CLI (`gws mcp`)

**One MCP server covers all Google Workspace tools.** No custom MCP servers needed.

```bash
# Install
npm install -g @googleworkspace/cli

# Run as MCP server (exposes Calendar + Tasks + Gmail + Docs + Drive)
gws mcp -s calendar,gmail,docs,drive

# OAuth setup
gws auth setup    # configure OAuth client
gws auth login    # authorize with Google account
```

**Auth:** OAuth2 via `gws auth login`. Pre-authorize before demo. Same OAuth client
covers all 5 services.

**Tools exposed per service:**

| Service | Key tools used by EduFlow | Agent |
|---|---|---|
| **Calendar** | Create/update/delete events, list events | `calendar_agent` |
| **Gmail** | Send email, reply, search | `email_agent` |
| **Docs** | Create document, append text, format headings | `docs_agent` |
| **Drive** | Create folder, upload, organize files | `docs_agent` |

**ADK integration:** Google Workspace tools are implemented as Python function tools
using `google-api-python-client` with OAuth2 credentials from environment variables.
Located in `eduflow_agents/tools/workspace/`. No MCP server required for Workspace.
(`gws mcp` subcommand does not exist in any released version of `@googleworkspace/cli`.)

#### MCP Server 2: Database MCP (MCP Toolbox for Databases → AlloyDB)

Reuses the exact pattern from the AI Tutor project. `tools.yaml` defines parameterised SQL tools.

**Tools exposed (runtime state only — syllabus/questions in YAML, profile in ADK user_states):**

| Tool | Purpose | SQL pattern |
|---|---|---|
| `save-learning-plan` | Insert a new learning plan | `INSERT INTO learning_plans ...` |
| `save-study-session` | Insert a study session within a plan | `INSERT INTO study_sessions ...` |
| `update-study-session` | Update session status/integration IDs | `UPDATE study_sessions SET status=$1 ...` |
| `save-assessment` | Store quiz result + weak areas | `INSERT INTO assessments ...` — session_id uses `NULLIF($1, '')::uuid` to handle empty `current_session_id` gracefully |
| `get-student-progress` | Fetch progress for adaptation | `SELECT ... FROM progress WHERE user_id=$1` |
| `update-progress` | Update mastery level after assessment | `UPDATE progress SET mastery_level=$1 ...` |

### 4.3 Google Docs: Study Notes Structure

```
Google Doc: "Study Notes: Quadratic Equations — Math Grade 8"
│
├── Heading 1: Quadratic Equations
│
├── Heading 2: Session 1 — Basics & Standard Form
│     Key Concepts:
│       • A quadratic equation has the form ax² + bx + c = 0
│       • 'a' is the coefficient of x², 'b' of x, 'c' is the constant
│     Video: [Standard Form Explained — YouTube link]
│     Practice: Identify a, b, c in: 3x² - 5x + 2 = 0
│
├── Heading 2: Session 2 — Factoring Method
│     (appended after Session 2 tutoring completes)
│
└── ... (grows session by session — living document)

Saved in Drive: EduFlow/Math/Grade 8/Study Notes - Quadratic Equations.gdoc
```

**Docs API approach:** Use Drive API to upload HTML content as a Google Doc (simpler than
`batchUpdate`). Headings via `<h1>`, `<h2>` tags auto-convert to Doc headings.

### 4.4 YouTube Search Function Tool

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

## 5. Data Persistence Architecture

EduFlow uses a **two-layer** data strategy:

- **YAML curriculum files** (static) — syllabus structure, concepts, quiz questions.
  Lives in codebase at `data/curricula/`. Zero cost. See Section 5.2.
- **AlloyDB** (dynamic) — runtime state that changes per student.
  Only 4 custom tables. ADK auto-manages 5 more tables for session/state.

### 5.1 ADK Session Tables (Auto-Managed)

`DatabaseSessionService` auto-creates these 5 tables. **Do not modify manually.**

| ADK Table | Purpose | Key columns |
|---|---|---|
| `sessions` | Conversation sessions | `app_name`, `user_id`, `id`, `state` (JSONB) |
| `events` | Full conversation history (messages, tool calls) | `session_id`, `event_data` (JSONB) |
| `user_states` | `user:` prefixed state — persists across ALL sessions for a user | `app_name`, `user_id`, `state` (JSONB) |
| `app_states` | `app:` prefixed state — shared across ALL users | `app_name`, `state` (JSONB) |
| `adk_internal_metadata` | Schema version tracking | `key`, `value` |

**State prefix system:**

| Prefix | Scope | Persists across sessions? | Storage |
|---|---|---|---|
| `user:` | Per user, all sessions | **Yes** | `user_states` table |
| `app:` | Global, all users | **Yes** | `app_states` table |
| *(no prefix)* | Current session only | **No** | `sessions.state` column |
| `temp:` | Current agent turn only | **Never stored** | Stripped before persistence |

**Student profile via `user:` state** (replaces a custom `students` table):

ADK's `user:` prefix means profile data set once persists across every future session
for that user — no custom `students` table needed.

| State key | Set by | Stored in | Available in all sessions? |
|---|---|---|---|
| `user:name` | UI profile form | `user_states` | Yes |
| `user:email` | UI profile form | `user_states` | Yes |
| `user:parent_email` | UI profile form | `user_states` | Yes |
| `user:grade_level` | UI profile form | `user_states` | Yes |
| `user:preferred_language` | UI profile form | `user_states` | Yes |
| `user:grade_band` | orchestrator | `user_states` | Yes |

### 5.2 Custom Tables (4 tables — runtime business data)

> **IMPORTANT:** ADK auto-creates a table named `sessions`. Our custom table for study
> sessions is named **`study_sessions`** to avoid collision. Same AlloyDB database,
> same connection string — they coexist.

```sql
-- NOTE: Student profiles are stored in ADK's user_states table via user: prefix.
-- No custom students table needed. All custom tables reference user_id VARCHAR(128)
-- which matches ADK's user_id format.

-- NOTE: Syllabus and quiz questions are in YAML curriculum files.
-- See Section 5.3.

-- Learning plans
CREATE TABLE learning_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(128) NOT NULL,        -- ADK user_id (same as user_states)
    subject VARCHAR(50) NOT NULL,
    goal TEXT NOT NULL,                   -- "Learn Quadratic Equations"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_sessions INT NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'paused'
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON learning_plans (user_id, status);

-- Individual study sessions within a plan (RENAMED to avoid ADK collision)
CREATE TABLE study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES learning_plans(id),
    topic_key VARCHAR(200) NOT NULL,      -- YAML topic ref: "quadratic-equations.standard-form"
    session_number INT NOT NULL,          -- 1, 2, 3, ...
    scheduled_date DATE,
    scheduled_time TIME,
    video_url TEXT,                        -- YouTube video link
    video_title VARCHAR(500),
    summary TEXT,                          -- AI-generated session summary
    calendar_event_id VARCHAR(200),       -- Google Calendar event ID (for updates)
    doc_id VARCHAR(200),                  -- Google Docs document ID (for appending notes)
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'skipped'
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON study_sessions (plan_id, session_number);

-- Assessment results
CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES study_sessions(id),
    user_id VARCHAR(128) NOT NULL,        -- ADK user_id
    topic_key VARCHAR(200) NOT NULL,      -- YAML topic ref: "quadratic-equations.standard-form"
    score DECIMAL(5,2),                    -- Percentage score
    total_questions INT,
    correct_answers INT,
    weak_areas TEXT[],                     -- Array of identified weak sub-topics
    feedback TEXT,                         -- AI-generated feedback summary
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON assessments (user_id, topic_key);

-- Aggregated progress tracking
CREATE TABLE progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(128) NOT NULL,        -- ADK user_id
    topic_key VARCHAR(200) NOT NULL,      -- YAML topic ref: "quadratic-equations.standard-form"
    mastery_level VARCHAR(20) DEFAULT 'not_started',  -- 'not_started', 'beginner', 'intermediate', 'mastered'
    best_score DECIMAL(5,2),
    attempts INT DEFAULT 0,
    last_assessed TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, topic_key)
);
CREATE INDEX ON progress (user_id);
```

**What goes where (the clean split):**

| Data | Where it lives | Why |
|---|---|---|
| Student profile (name, email, grade) | ADK `user_states` via `user:` prefix | Persists across sessions automatically, no custom table needed |
| Conversation context (current topic, plan ID) | ADK `sessions.state` (no prefix) | Scoped to current conversation, auto-managed |
| Conversation history | ADK `events` table | Auto-stored by ADK on every interaction |
| Learning plans | Custom `learning_plans` | Needs relational queries, joins, status tracking |
| Study session schedule + integration IDs | Custom `study_sessions` | Links to Calendar/Tasks/Docs, tracks completion |
| Quiz scores + weak areas | Custom `assessments` | Needs aggregation, reporting, trend analysis |
| Topic mastery levels | Custom `progress` | Drives adaptation — "skip review if mastered" |

**How data helps the student:**

```
[1] Student returns for new session
    │
    ├── ADK loads user: state automatically
    │   → Agent knows: name, grade, language, grade_band
    │
    ├── get-student-progress (DB MCP) → reads progress table
    │   → Agent knows: which topics mastered, which need work
    │
    └── Curriculum planner has YAML in context
        → Agent knows: full topic structure, prerequisites, concepts
        → Plans sessions intelligently (skip mastered, focus on weak)

[2] After assessment
    │
    ├── save-assessment → stores score + weak_areas in assessments table
    │   → Next session: tutor focuses on weak_areas
    │
    ├── update-progress → updates mastery_level in progress table
    │   → If mastery_level stays low → planner adds review session
    │   → If mastery_level reaches 'mastered' → move to next topic
    │
    └── email_agent sends report to parent (from user:parent_email)
        → Parent sees: score, weak areas, Google Doc link for notes
```

### 5.3 YAML Curriculum Files (Replaces DB Syllabus)

Syllabus and quiz questions are **static reference data** — they don't change per student.
Storing them in YAML files instead of AlloyDB eliminates DB cost for syllabus, makes the
system community-extensible, and gives agents zero-latency access (no MCP round-trip).

**Format:** YAML (best LLM accuracy for Gemini family, human-editable, natural hierarchy).

**Directory:** `data/curricula/{board}/{subject}/grade-{N}.yaml` — one file per grade+subject.

**Auto-discovery:** System scans `data/curricula/` at startup, discovers all available
boards/subjects/grades. No registration step needed.

**YAML file structure:**

```yaml
# data/curricula/cbse/math/grade-8.yaml
curriculum:
  board: CBSE
  subject: math
  grade: 8
  language: English

chapters:
  - id: quadratic-equations
    title: Quadratic Equations
    sequence: 1

    topics:
      - id: standard-form
        title: Basics & Standard Form
        sequence: 1
        estimated_minutes: 35
        prerequisites: []
        concepts:
          - Quadratic equation definition
          - Standard form ax² + bx + c = 0
          - Identifying coefficients a, b, c
        youtube_search_hints:
          - "quadratic equation standard form grade 8 tutorial"
        questions:
          - question: "In 3x² - 5x + 2 = 0, what is the value of 'a'?"
            options: ["1", "3", "-5", "2"]
            answer: "3"
            explanation: "In ax² + bx + c form, 'a' is the coefficient of x²"
            difficulty: 1

      - id: factoring-method
        title: Factoring Method
        sequence: 2
        estimated_minutes: 45
        prerequisites: [standard-form]
        concepts:
          - Splitting the middle term
          - Finding factor pairs
          - Zero product property
        youtube_search_hints:
          - "factoring quadratic equations grade 8"
        questions:
          - question: "Solve x² + 5x + 6 = 0 by factoring"
            options: ["x = -2, -3", "x = 2, 3", "x = -1, -6", "x = 1, 6"]
            answer: "x = -2, -3"
            explanation: "x² + 5x + 6 = (x+2)(x+3) = 0"
            difficulty: 2
```

**Prerequisites as DAG (dotted paths):**
- Same chapter: `prerequisites: [standard-form]`
- Cross-chapter: `prerequisites: [algebraic-expressions.polynomials]`
- Cross-subject (future): `prerequisites: [math/grade-8/algebra.linear-equations]`

**Agent consumption — load at construction time:**

```python
import yaml
from pathlib import Path

def load_curriculum(board: str, subject: str, grade: int) -> dict:
    path = Path(f"data/curricula/{board}/{subject}/grade-{grade}.yaml")
    return yaml.safe_load(path.read_text())

def discover_curricula(base_path: str = "data/curricula") -> dict:
    """Scan curriculum directory and return all available options."""
    curricula = {}
    for yaml_file in Path(base_path).rglob("*.yaml"):
        if yaml_file.name.startswith("_"):
            continue
        data = yaml.safe_load(yaml_file.read_text())
        key = f"{data['curriculum']['board']}/{data['curriculum']['subject']}/grade-{data['curriculum']['grade']}"
        curricula[key] = data
    return curricula
```

**Pydantic validation (in `_schema.yaml` / `curriculum_loader.py`):**

```python
from pydantic import BaseModel
from typing import Optional

class Question(BaseModel):
    question: str
    options: list[str]
    answer: str
    explanation: str = ""
    difficulty: int = 1

class Topic(BaseModel):
    id: str
    title: str
    sequence: int
    estimated_minutes: int = 45
    prerequisites: list[str] = []
    concepts: list[str] = []
    youtube_search_hints: list[str] = []
    questions: list[Question] = []

class Chapter(BaseModel):
    id: str
    title: str
    sequence: int
    topics: list[Topic]

class CurriculumMeta(BaseModel):
    board: str
    subject: str
    grade: int
    language: str = "English"

class CurriculumFile(BaseModel):
    curriculum: CurriculumMeta
    chapters: list[Chapter]
```

**Math chapters for demo (Grade 7-10, CBSE-aligned):**

| Chapter | Topics (3-5 each) | Why |
|---|---|---|
| Number Systems | Rational numbers, Irrational numbers, Real number line | Foundation concept, grade differentiation is clear |
| Algebraic Expressions | Polynomials, Factoring, Linear equations | Bread-and-butter tutoring demand |
| Quadratic Equations | Standard form, Factoring method, Quadratic formula, Completing the square | **Primary demo chapter** |
| Geometry | Triangles, Circle theorems, Coordinate geometry | Visual + code_executor for plotting |
| Statistics & Probability | Mean/median/mode, Probability basics | Code_executor for data visualization |

**Physics (backlog):** Structurally identical YAML files. Add once Math flow is complete.
Chapters: Motion, Force & Laws of Motion, Gravitation, Work & Energy, Light.

**Community extensibility:** Anyone adds a new board/subject/grade by creating a YAML file
in `data/curricula/{board}/{subject}/grade-{N}.yaml` and opening a PR. No DB migration,
no code change. The system auto-discovers it at startup.

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
| Curriculum file | `grade-{N}.yaml` in `data/curricula/{board}/{subject}/` | `data/curricula/cbse/math/grade-8.yaml` |
| Topic ID in YAML | `kebab-case` | `standard-form`, `factoring-method` |
| Topic key in DB | `chapter.topic` dotted path | `quadratic-equations.standard-form` |

### 6.2 Agent Construction Rules

1. **Prompts in `prompts/` only.** Never inline instruction strings in agent files.
2. **Tools from `tools/` only.** Import shared tool instances; never instantiate in agent files.
3. **Relative imports within `eduflow_agents` package.**
4. **One `output_key` per pipeline role:** tutors write `tutor_solution`, formatter writes `formatted_response`.
5. **`include_contents='none'` on response_formatter** — same pattern as AI Tutor project.
6. **`before_agent_callback` requires documented reason** — same discipline as AI Tutor project.
7. **Each formatter instance via `make_response_formatter(name)`** — one-parent rule.
8. **Each email_agent instance via `make_email_agent(name)`** — one-parent rule. `scheduling_pipeline` uses `email_agent` (default name); `report_pipeline` uses `make_email_agent("report_email_agent")`. Never add the same instance to two pipelines.
9. **plan_saver_agent uses `gemini-2.5-flash-lite`** — gemini-2.5-pro's thinking mode produces no final text after pure tool-call sequences, so `output_key` is never written. Flash-lite outputs the UUID correctly. Do not change this model for plan_saver.

### 6.3 Model

Default: `gemini-2.5-pro` for all agents except `plan_saver_agent` (uses `gemini-2.5-flash-lite` — see rule 9 above).

**Why Pro:** Hackathon Vertex AI project (genai-apac-hackathon) has no usable RPM quota for `gemini-2.5-flash`. Available models with real quota: `gemini-2.5-pro` (1M tokens/min in us-central1). Flash-lite has 5 RPM — only used for plan_saver where output is simple (a UUID).

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
    ├─► Google Workspace function tools (google-api-python-client + OAuth2)
    │       ├── Calendar (schedule sessions)
    │       ├── Tasks (track progress)
    │       ├── Gmail (notify parent)
    │       ├── Docs (study notes)
    │       └── Drive (organize files)
    │
    ├─► MCP Toolbox ─── Cloud Run: eduflow-toolbox
    │                       │
    │                       ▼
    │                   Cloud SQL PostgreSQL 15 (asia-southeast1)
    │                       ├── ADK: sessions, events, user_states (auto)
    │                       └── Custom: learning_plans, study_sessions,
    │                           assessments, progress
    │
    ▼
Google APIs (YouTube Data API v3)
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
| `GOOGLE_OAUTH_CLIENT_ID` | backend | OAuth2 for Workspace MCP (Calendar, Tasks, Gmail, Docs, Drive) |
| `GOOGLE_OAUTH_CLIENT_SECRET` | backend | OAuth2 for Workspace MCP |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | backend | Pre-authorized token for demo |
| `BACKEND_URL` | frontend | URL to backend Cloud Run service |

### 8.3 Known Gotchas (Carried from AI Tutor + EduFlow-specific)

- **`GOOGLE_CLOUD_LOCATION`**: Must be `us-central1`, not `asia-southeast1` (Gemini DNS fails in SEA)
- **MCP Toolbox IAM**: Needs `allUsers` invoker — ADK MCPToolset uses plain httpx with no auth
- **Alpine + Go binary**: Toolbox Dockerfile needs `apk add gcompat` for glibc shim
- **`PORT` is reserved**: Never set as env var on Cloud Run
- **AlloyDB `@` in password**: URL-encode as `%40`
- **Cold start**: Handle empty SSE response gracefully in frontend
- **ADK one-parent rule**: Each LlmAgent instance can only belong to one SequentialAgent parent. Use factory functions (`make_response_formatter`, `make_email_agent`) when the same agent logic is needed in multiple pipelines.
- **MCP Toolbox restart required**: Toolbox reads `tools.yaml` at startup only. Any change to `tools.yaml` requires a full Toolbox restart to take effect.
- **Pro thinking mode + output_key**: `gemini-2.5-pro` generates thought tokens before tool calls but often produces no final text after pure tool-call sequences. `output_key` is never written in these cases. Use `gemini-2.5-flash-lite` for agents whose only job is tool invocation (e.g. `plan_saver_agent`).
- **InMemorySessionService on restart**: Local dev uses `InMemorySessionService` — all session state (including `user:` prefixed profile) is lost on backend restart. Students must re-enter their profile. Production uses `DatabaseSessionService` which persists state.
- **save-assessment empty session_id**: `current_session_id` is empty unless a study session was explicitly started. SQL uses `NULLIF($1, '')::uuid` so empty string becomes NULL rather than crashing the INSERT.

---

## 9. Implementation Phases (10-Day Plan)

### Phase 1: Foundation + Research (Days 1-2) ✅ COMPLETE
> **Goal:** Project setup, schema design, validate Google Workspace tool approach.
> **Note:** `gws mcp` subcommand does not exist in any released version of `@googleworkspace/cli`.
> Workspace tools implemented as Python function tools using `google-api-python-client` instead.

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| 1.1 | **Project scaffold** | Critical | ✅ Done | Git repo, virtualenv, `eduflow_agents/` package, CLAUDE.md, .gitignore, .env.example |
| 1.2 | **AlloyDB schema** | Critical | ✅ Done | Switched to Cloud SQL PostgreSQL 15 (cheaper, same compatibility). 4 tables created via `scripts/infra/setup_db.py`. |
| 1.3 | **YAML curriculum files** | Critical | ✅ Done | Grade 7-10 CBSE Math YAML created and Pydantic-validated. |
| 1.4 | **Google Workspace tools** | Critical | ✅ Done | OAuth2 function tools in `eduflow_agents/tools/workspace/` (calendar, tasks, gmail, docs, drive). |
| 1.5 | **YouTube API setup** | High | ✅ Done | Dedicated API key created, restricted to YouTube Data API v3. `youtube_search` tested and working. |
| 1.6 | **OAuth2 setup** | High | ✅ Done | All 5 scopes verified: calendar, tasks, gmail.send, documents, drive. Refresh token in `.env`. |

### Phase 2: MCP Tools + Database Layer (Days 3-4) ✅ COMPLETE
> **Goal:** All tools working and tested independently.
> **Note:** Workspace tools are Python function tools (not MCP). Only Database uses MCP Toolbox.
> **Note:** MCP Toolbox v0.30.0 requires dict-format tools (not list), all parameters need description, no `number` type (use `string` + SQL cast).

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| 2.1 | **Database MCP (MCP Toolbox)** | Critical | ✅ Done | `tools.yaml` fixed for v0.30.0 format. 6 tools loading. Toolbox runs via `start_toolbox.ps1`. |
| 2.2 | **Workspace tools — Calendar** | Critical | ✅ Done | `create_calendar_event` tested — returns event_id + event_link. |
| 2.3 | **Workspace tools — Gmail** | Critical | ✅ Done | `send_email` tested — message_id returned, email delivered. |
| 2.5 | **Workspace tools — Docs+Drive** | Critical | ✅ Done | Drive folders created (EduFlow/Math/Grade 8), Doc created with URL, section appended. |
| 2.6 | **YouTube function tool** | High | ✅ Done | Tested and working. |
| 2.7 | **Curriculum loader** | High | ✅ Done | Pydantic-validated. All 4 grades load correctly. |

### Phase 3: Agent Implementation (Days 5-6)
> **Goal:** All agents implemented and tested via Streamlit + uvicorn (not adk web).
> **Status legend:** ✅ Tested & confirmed | 🔧 Implemented, needs test | ⏳ Not started

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| 3.1 | **orchestrator_agent** | Critical | ✅ Tested | Dynamic instruction with profile + lesson injection. session_topic set before planning. |
| 3.2 | **curriculum_planner_agent** | Critical | ✅ Tested | Matched-chapter path (~500 tokens) triggered when orchestrator sets session_topic. |
| 3.3 | **content_agent** | Critical | ✅ Tested | youtube_search returning real URLs. Grade-band query modifiers working. |
| 3.4 | **calendar_agent** | Critical | ✅ Tested | Calendar events created with real video links and tutor starter prompts. |
| 3.5 | **email_agent** | Critical | ✅ Tested | Plan email with HTML table confirmed received. Doc link fix implemented (separate turn) — needs re-test. |
| 3.6 | **docs_agent** | Critical | ✅ Tested | MODE A (plan overview) and MODE B (tutor notes append) confirmed in GDrive. Markdown stripping implemented — needs re-test. |
| 3.7 | **plan_saver_agent** | Critical | ✅ Tested | Uses gemini-2.5-flash-lite (Pro thinking mode suppresses output_key on pure tool-call sequences). learning_plans + study_sessions rows confirmed in DB. |
| 3.8 | **tutor_agent** | High | ✅ Tested | All concepts covered (4-section structure). Grade-band personas working (Grade 8 building). Code verification ✅ Verified note shown. |
| 3.9 | **assessment_agent** | High | ✅ Tested | YAML questions injected into context (no tool call). Fuzzy case-insensitive topic matching. Quiz completed (100% score confirmed). Both save-assessment + update-progress confirmed in DB (see 3B.6). |
| 3.10 | **response_formatter** | High | ✅ Tested | Clean output confirmed in UI. |
| 3.11 | **Pipeline wiring** | Critical | ✅ Tested | All 6 pipelines wired: planning, scheduling, tutoring, notes, assessment, report. |
| 3.12 | **report_pipeline** | Critical | ✅ Tested | New pipeline with report_email_agent (make_email_agent factory). Parent progress report email confirmed received with score, weak areas, doc link. |

### Phase 3B: DB Persistence + Voice Input (Added Apr 4)
> **Goal:** Persist plans/assessments to Cloud SQL. Enable microphone input for students.
> **Prerequisite for DB tests:** MCP Toolbox must be running — `.\scripts\infra\start_toolbox.ps1`

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| 3B.1 | **user:id in state_delta** | Critical | ✅ Tested | Streamlit sends `user:id = st.session_state.uid` with every message so DB agents have the user key. |
| 3B.2 | **plan_saver_agent** | Critical | ✅ Tested | `eduflow_agents/subagents/plan_saver_agent.py` — gemini-2.5-flash-lite, confirmed rows in learning_plans + study_sessions. |
| 3B.3 | **MCP_TOOLBOX_URL env var** | Critical | ✅ Tested | plan_saver_agent + assessment_agent both use `os.environ.get("MCP_TOOLBOX_URL", "http://localhost:5000/mcp")`. Toolbox running confirmed. |
| 3B.4 | **Microphone / audio input** | High | ✅ Tested | `st.audio_input()` → `gemini-2.5-flash-lite` transcribes → clean text forwarded to orchestrator. Voice input + Hindi response confirmed working. |
| 3B.5 | **Test: plan saved to DB** | Critical | ✅ Done | planning_pipeline + Toolbox → learning_plans + study_sessions rows confirmed. |
| 3B.6 | **Test: assessment saved to DB** | Critical | ✅ Done | assessments table row confirmed after fixing: (1) NULLIF($1,'')::uuid in tools.yaml, (2) assessment_agent prompt made MANDATORY for both save-assessment + update-progress — Pro was skipping save-assessment silently. |
| 3B.7 | **Test: audio input** | High | ✅ Done | Voice question → transcript shown → EduFlow responded correctly. |
| 3B.8 | **Notes deduplication** | High | ✅ Done | notes_saved_topics dedup confirmed — same topic taught twice does not duplicate Google Doc section. |
| 3B.9 | **Post-assessment parent email** | Critical | ✅ Done | Parent received progress report email with score, weak areas, Google Doc link. report_pipeline + report_email_agent confirmed working. |
| 3B.10 | **Streamlit read timeout** | High | ✅ Fixed | Changed from `timeout=180.0` to `httpx.Timeout(connect=10.0, read=360.0, write=30.0, pool=10.0)` to handle Pro model's slower generation. |

### Phase 4: Frontend (Days 7-8)
> **Goal:** Polished Streamlit UI with video embedding and progress dashboard.

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| 4.1 | **FastAPI backend** | Critical | ✅ Tested | `main.py` with `get_fast_api_app()` + InMemorySessionService. Working. |
| 4.2 | **Streamlit chat UI** | Critical | ✅ Tested | Streaming SSE chat confirmed working. |
| 4.3 | **Student profile form** | Critical | ✅ Tested | Name, email, parent email, grade, language. Sidebar working. |
| 4.4 | **Microphone input** | High | ✅ Tested | `st.audio_input()` → `_transcribe_audio()` → `gemini-2.5-flash-lite` → transcript text to orchestrator. Voice + Hindi confirmed working. Note: flash-lite has 5 RPM — use sparingly in demo. |
| 4.5 | **Plan progress tracker** | Medium | ⏳ Skipped | Nice-to-have, cut for time. Not needed for demo. |
| 4.6 | **Quick actions** | High | ✅ Tested | Buttons wired and working in sidebar. |

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

## 10. Demo Script (3-Minute Video) & Test Plan

> Full script, exact inputs/outputs, test checkpoints, setup checklist, and fallback
> plan are in **`DEMO_SCRIPT.md`** (kept separate to reduce context load during coding).

### 10.1 Script Overview

| Segment | Duration | Criteria targeted |
|---|---|---|
| A. The Problem | 0:00–0:20 | Impactful Vision |
| B. EduFlow in One Line | 0:20–0:30 | Innovation |
| C. Live Demo — Planning | 0:30–1:10 | Technical Merit, UX |
| D. Live Demo — Grade-Aware Teaching | 1:10–1:50 | Innovation, Impact |
| E. Live Demo — Voice + Multilingual | 1:50–2:15 | Impact, Innovation |
| F. Live Demo — Real Integrations | 2:15–2:35 | Technical Merit |
| G. Architecture Flash | 2:35–2:50 | Technical Merit |
| H. Closing | 2:50–3:00 | Impactful Vision |

### 10.2 Key Test Checkpoints (Summary)

See `DEMO_SCRIPT.md` for full per-segment inputs, expected outputs, and detailed checklists.

| Demo segment | What to verify works |
|---|---|
| C. Planning | YAML read → sessions planned → Calendar events + parent email created |
| D. Grade teaching | `get_grade_band()` correct → persona applied → YouTube differs by grade |
| E. Voice + Hindi | `st.audio_input` → Gemini detects Hindi → response in Hindi |
| F. Integrations | Calendar events (with tutor prompt), Study Notes Doc in Drive, Gmail — all show real AI-created content |

---

## 11. Risks & Mitigations

> **Timeline note:** Planning/research complete as of Day 3. ~7 implementation days remain
> before the 2026-04-08 deadline. Risks are ordered by implementation phase impact.

| Risk | Impact | Mitigation |
|---|---|---|
| **YAML curriculum quality** | High | Author Math Grade 7-10 YAML on Day 1 before any agent work. Validate with Pydantic schema. Test `curriculum_planner_agent` with grade-8 YAML before moving to next phase. All agents depend on this — it is the critical path. |
| **`gws mcp` deployment on Cloud Run** | High | Run `gws mcp` as a 4th Cloud Run service. Test Cloud Run → `gws mcp` connectivity in Phase 2 before building agents that depend on it. Fallback: direct Google API function tools (pre-built backup per demo fallback plan). |
| **Workspace MCP OAuth2 + `gws` stability** | High | Pin `@googleworkspace/cli` to a specific version. Test `gws auth login` + all 4 services (Calendar, Gmail, Docs, Drive) end-to-end in Phase 2. Pre-authorize OAuth refresh token before demo day. |
| **7-day timeline (was 10-day plan)** | High | Prioritize core flow first: planner → calendar → tutor → assessment. Docs/Tasks/email agents are additive — demo still works without them. Cut Phase 4 video embedding if behind schedule. |
| **Vertex AI rate limits** | High | Use API key (not Vertex AI) for demo — proven from AI Tutor project. Request quota increase by Day 5. |
| **`study_sessions` / ADK `sessions` table collision** | Medium | Setup script must never manually create a `sessions` table — ADK owns that name. Add explicit check in `setup_alloydb.sh`. ADK auto-creates its tables on first run via `DatabaseSessionService`. |
| **`user_id` format in custom tables** | Medium | Enforce UUID format for `user_id` in Streamlit profile form (`str(uuid.uuid4())`). Store in `user:id` session state on first visit. Prevents SQL errors from email-style or special-character user IDs. |
| **YAML context window size in planner** | Medium | Keep each grade YAML under 2,000 tokens. Inject only the relevant chapter when a specific learning goal is given — not the entire grade curriculum. Test with grade-8 math before scaling to all grades. |
| **AlloyDB VPC connectivity from Cloud Run** | Medium | Set up Serverless VPC Access connector in Phase 1 infra. Reuse config from AI Tutor project. Verify `MCP_TOOLBOX_URL` is reachable from Cloud Run backend before Phase 3 agent work begins. |
| **YouTube API quota (100 searches/day free)** | Medium | Pre-populate `youtube_search_hints` in YAML with known-good video IDs per topic. Content agent uses hints first, falls back to live search only if hints return no results. Eliminates most API calls. |
| **Scope creep on tutoring quality** | Medium | Workflow is the star, not explanation depth. Grade-band personas in Section 14 are finalised — do not iterate on prompts during implementation. |
| **Cold start on Cloud Run** | Low | Proven pattern from AI Tutor: empty response detection + "warming up" message. Pre-warm backend 5 min before demo recording. |

---

## 12. What's Reused vs New

**Reused from AI Tutor:** ADK framework, SequentialAgent + AgentTool pattern, MCP Toolbox
wiring, AlloyDB cluster (new DB/schema), Cloud Run + Dockerfile patterns, FastAPI backend,
Streamlit SSE streaming, `response_formatter` factory, `code_executor` on tutor agent.

**New for EduFlow:** Google Workspace MCP (`gws`) — Calendar, Gmail, Docs, Drive;
YAML curriculum files (replaces DB syllabus); YouTube search tool; curriculum planner agent;
docs agent; multi-step workflow orchestration; grade-aware teaching personas
(Section 14); voice input + multilingual (Section 15); parent notification system.

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

# Start Google Workspace MCP server (Calendar, Gmail, Docs, Drive)
gws auth login                              # one-time OAuth setup
gws mcp -s calendar,gmail,docs,drive  # runs over stdio (ADK spawns per-agent subprocesses)

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

---

## 14. Grade-Aware Teaching & Content Generation

> **Core idea:** The same topic taught differently per grade. EduFlow's tutor doesn't just
> explain — it hooks the student with grade-appropriate analogies, concise language, and
> curiosity-sparking questions. YouTube links are filtered by grade band.

### 14.1 Design Principles (from Google LearnLM)

LearnLM capabilities are now infused into Gemini 2.5. We encode these five learning science
principles directly into our tutor prompt:

| Principle | Prompt technique |
|---|---|
| **Active Learning** | End each explanation with a thought-provoking question, not a summary |
| **Cognitive Load** | One concept per turn. Short sentences. No walls of text. |
| **Adaptation** | Grade-band persona injected via session state |
| **Curiosity** | Lead with a "hook" — a surprising fact, real-world connection, or "what if?" |
| **Metacognition** | Occasionally ask: "What part clicked? What still feels fuzzy?" |

### 14.2 Grade Bands

| Band | Grades | Vocabulary | Examples | Hook Style |
|---|---|---|---|---|
| **Foundation** | 5-6 | Everyday words. Define math terms on first use. | Pizza slices, marbles, pocket money | "Did you know..." + fun fact |
| **Building** | 7-8 | Formal terms with simple definitions | Speed/distance, simple interest | "What if I told you..." + pattern |
| **Bridging** | 9-10 | Standard math terminology | Textbook-style, multi-step | "Here's the trick that most students miss..." |
| **Advanced** | 11-12 | University-level precision | Competition, proof-based | "This connects to..." + cross-domain link |

### 14.3 Tutor Prompt Pattern

Every tutor response follows this structure:

```
1. HOOK (1 sentence) — Surprise, analogy, or "what if?" to grab attention
2. EXPLAIN (3-5 sentences) — Core concept, grade-appropriate vocabulary
3. EXAMPLE (worked) — Step-by-step, real-world for lower grades, algebraic for higher
4. SPARK (1 question) — "Why do you think...?" / "What would happen if...?"
```

Grade-band persona snippet (injected by orchestrator):

```python
GRADE_BAND_PERSONAS = {
    "foundation": """You are a fun, encouraging math tutor for a Grade {grade} student.
HOOK: Start every explanation with a surprising real-world connection the student can
  see or touch (pizza, playground, coins). Make them go "whoa!"
LANGUAGE: Everyday words only. Max 12 words per sentence. Define any math term simply.
EXAMPLES: Use physical objects and counting. Show pictures in words.
STYLE: One concept at a time. Full worked example first, then guided practice.
TONE: Warm and encouraging. Never say "wrong" — say "Almost! Let's try together."
END: Close with a curiosity question: "What do you think would happen if...?"
""",
    "building": """You are a supportive math tutor for a Grade {grade} student.
HOOK: Start with a "what if" scenario or a pattern to discover.
LANGUAGE: Introduce formal terms with simple definitions on first use.
EXAMPLES: Semi-real scenarios (speed, interest, geometry), then algebraic.
STYLE: One worked example → "Your turn" with hints available.
TONE: Supportive. "Not quite — here's a clue."
END: Ask "Can you spot the pattern?" or "Why does this work?"
""",
    "bridging": """You are a math tutor for a Grade {grade} student preparing for exams.
HOOK: Start with the trick or insight that makes this topic click.
LANGUAGE: Standard mathematical terminology. No simplification needed.
EXAMPLES: Textbook-style. Multi-step problems.
STYLE: Problem → attempt → hints only if stuck → verify.
TONE: Direct. "Your step 3 has an issue — can you find it?"
END: Ask "Why does this method work?" or "When would it fail?"
""",
    "advanced": """You are a rigorous math tutor for a Grade {grade} student targeting
competitive exams.
HOOK: Start with a cross-domain connection or an elegant insight.
LANGUAGE: University-level precision. No dumbing down.
EXAMPLES: Competition-level. Proof-based. Edge cases.
STYLE: Problem → student works → critique approach → discuss alternatives.
END: "Can you generalize?" or "Prove that..."
"""
}

def get_grade_band(grade: str) -> str:
    grade_num = int(''.join(filter(str.isdigit, grade)) or '7')
    if grade_num <= 6: return "foundation"
    elif grade_num <= 8: return "building"
    elif grade_num <= 10: return "bridging"
    return "advanced"
```

### 14.4 YouTube Search Adaptation

`youtube_search` appends grade-appropriate modifiers:

| Band | Query suffix | Why |
|---|---|---|
| Foundation | `"for kids" OR "animated"` | Visual, fun explainers |
| Building | `"tutorial" OR "explained"` | Step-by-step walkthroughs |
| Bridging | `"CBSE" OR "ICSE" OR "board exam"` | Exam-relevant content |
| Advanced | `"proof" OR "advanced" OR "lecture"` | Rigorous, depth-first |

### 14.5 Demo Moment (The "Wow")

Split-screen: same question, two grades.

- **Grade 6:** "What is area of a circle?" → Thin circle segments rearranged into a rectangle (visual proof: long side = πr, short side = r, so area = πr²) + animated YouTube video
- **Grade 10:** Same question → Derive using integration (concentric rings of width dr, integrate 2πr·dr from 0 to R → πR²) + code_executor verification + lecture-style video

Same system. Same agent. Different grade. **Different teacher.**

### 14.6 Research Sources

- [LearnLM — Gemini API docs](https://ai.google.dev/gemini-api/docs/learnlm)
- [Classroom AI: LLMs as Grade-Specific Teachers (Nature, 2026)](https://arxiv.org/abs/2601.06225)
- [Adaptive Scaffolding for LLM Pedagogical Agents (arXiv 2508.01503)](https://arxiv.org/abs/2508.01503)
- [GraphMASAL: Multi-Agent Adaptive Learning (arXiv 2511.11035)](https://www.arxiv.org/pdf/2511.11035)

---

## 15. Voice Input & Multilingual Support

> Students can speak in their native language and receive tutor responses in the same
> language. Removes two barriers at once: typing difficulty and language.

### 15.1 Two-Model Audio Architecture (Quota-Optimised)

**Problem:** Sending raw audio bytes to `gemini-2.5-flash` burns the main agents' quota
on transcription work — a simple task that doesn't need the most capable model.

**Solution:** A dedicated pre-transcription step using `gemini-2.0-flash-exp-audio`, which
has its own independent quota pool (4M tokens/min). The main orchestrator (`gemini-2.5-flash`)
only ever receives clean text — its quota is fully preserved for planning/teaching/assessment.

```
Student speaks (WAV)
      │
      ▼  streamlit_app.py — _transcribe_audio()
gemini-2.0-flash-exp-audio   ← dedicated 4M tokens/min quota
      │  (transcription only, auto-detects language)
      ▼
  "मुझे द्विघात समीकरण समझाओ"   (plain text transcript)
      │
      ▼  /run_sse endpoint
gemini-2.5-flash orchestrator  ← quota preserved for agents
      │
      ▼
  Tutor response in Hindi
```

**Available audio models (GCP quota page — GenAI-APAC-Hackathon project):**

| Model | Type | Use |
|---|---|---|
| `gemini-2.5-flash-lite` | Batch (generate_content) | ✅ Our transcription model — lighter 2.5-gen, separate quota, supports audio input |
| `gemini-live-2.5-flash-native-audio` | Live API (websocket) | ❌ Cannot use for batch transcription — requires real-time streaming connection |
| `gemini-2.5-flash` | Batch (generate_content) | ❌ Avoid for audio — shares quota with all 8 agents |

**Supported languages:** 70+ including Hindi, Bengali, Tamil, Telugu, Kannada, Malayalam,
Marathi, Punjabi, Urdu, Gujarati, Vietnamese, Thai, Indonesian, and more.

**Fallback:** If transcription fails (network/model error), the student sees
"🎤 [Voice message — could not transcribe, please repeat or type]" — text input always available.

### 15.2 Flow (Implemented)

1. `st.audio_input()` captures WAV in Streamlit
2. `_transcribe_audio(audio_bytes)` calls `gemini-2.0-flash-exp-audio` synchronously
3. Transcript displayed in chat with 🎤 prefix (student can verify what was heard)
4. Audio playback widget shown alongside transcript
5. Clean transcript text forwarded to `_handle_message()` → orchestrator
6. Orchestrator + agents respond in `user:preferred_language` (already in tutor prompt)

**Key change:** `streamlit_app.py` no longer passes `audio_bytes` to `_stream_agent_response`
or the `/run_sse` endpoint — audio bytes are consumed entirely in Streamlit, never touching
the ADK backend.

### 15.3 Multilingual Tutor Behaviour

| Scenario | Behaviour |
|---|---|
| Student speaks Hindi | `gemini-2.0-flash-exp-audio` detects Hindi, transcribes in Hindi → orchestrator responds in Hindi |
| Student mixes Hindi + English | Audio model handles code-switching naturally in transcript |
| `preferred_language` set to Tamil | All tutor responses in Tamil, regardless of input language |
| Language not set | Orchestrator mirrors the language in the transcript |

### 15.4 Implementation (in `streamlit_app.py`)

```python
@st.cache_resource
def _get_genai_client():
    # Vertex AI or API key based on GOOGLE_GENAI_USE_VERTEXAI env var
    ...

def _transcribe_audio(audio_bytes) -> str:
    # Calls gemini-2.0-flash-exp-audio, returns transcript or ""
    ...
```

**Dependencies added to `requirements-ui.txt`:** `google-genai>=0.8.0`, `google-auth>=2.29.0`
(needed for Vertex AI ADC in the Streamlit container).

**Local dev prerequisite:** `gcloud auth application-default login` must be run once
when `GOOGLE_GENAI_USE_VERTEXAI=1` (uses ADC for Vertex AI authentication).

### 15.5 Demo Moment

"A Grade 7 student in rural India speaks in Hindi: 'मुझे द्विघात समीकरण समझाओ'
(Explain quadratic equations to me). The transcript appears in the chat. EduFlow responds
with a friendly, grade-appropriate explanation in Hindi, with a YouTube video link.
Meanwhile, the planning and teaching agents ran entirely on their own quota — untouched."

**Same system. Any language. Any grade. Accessible education for all.**
