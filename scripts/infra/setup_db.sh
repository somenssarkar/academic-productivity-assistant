#!/usr/bin/env bash
# setup_db.sh — Creates EduFlow custom tables in Cloud SQL (PostgreSQL 15)
# Run ONCE against a fresh database.
# ADK auto-creates its own tables (sessions, events, user_states, etc.) on first run.
# DO NOT manually create a table named 'sessions' — ADK owns that name.
#
# Usage:
#   DB_HOST=<cloud-sql-public-ip> DB_USER=eduflow_user PGPASSWORD=<password> bash scripts/infra/setup_db.sh

set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-eduflow}"
DB_USER="${DB_USER:-postgres}"

echo "==> Connecting to Cloud SQL at $DB_HOST:$DB_PORT/$DB_NAME as $DB_USER"

psql "host=$DB_HOST port=$DB_PORT dbname=$DB_NAME user=$DB_USER" <<'SQL'

-- Ensure uuid-ossp is available
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------
-- learning_plans
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS learning_plans (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     VARCHAR(128) NOT NULL,
    subject     VARCHAR(50)  NOT NULL,
    goal        TEXT         NOT NULL,
    start_date  DATE         NOT NULL,
    end_date    DATE         NOT NULL,
    total_sessions INT       NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_plan_status CHECK (status IN ('active', 'completed', 'paused'))
);
CREATE INDEX IF NOT EXISTS idx_learning_plans_user_status
    ON learning_plans (user_id, status);

-- -----------------------------------------------------------------------
-- study_sessions  (RENAMED — ADK owns the 'sessions' table name)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS study_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id             UUID REFERENCES learning_plans(id) ON DELETE CASCADE,
    topic_key           VARCHAR(200) NOT NULL,
    session_number      INT          NOT NULL,
    scheduled_date      DATE,
    scheduled_time      TIME,
    video_url           TEXT,
    video_title         VARCHAR(500),
    summary             TEXT,
    calendar_event_id   VARCHAR(200),
    task_id             VARCHAR(200),
    doc_id              VARCHAR(200),
    status              VARCHAR(20)  NOT NULL DEFAULT 'pending',
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_session_status CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped'))
);
CREATE INDEX IF NOT EXISTS idx_study_sessions_plan
    ON study_sessions (plan_id, session_number);

-- -----------------------------------------------------------------------
-- assessments
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES study_sessions(id) ON DELETE SET NULL,
    user_id         VARCHAR(128) NOT NULL,
    topic_key       VARCHAR(200) NOT NULL,
    score           DECIMAL(5,2),
    total_questions INT,
    correct_answers INT,
    weak_areas      TEXT[],
    feedback        TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_assessments_user_topic
    ON assessments (user_id, topic_key);

-- -----------------------------------------------------------------------
-- progress
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         VARCHAR(128) NOT NULL,
    topic_key       VARCHAR(200) NOT NULL,
    mastery_level   VARCHAR(20)  NOT NULL DEFAULT 'not_started',
    best_score      DECIMAL(5,2),
    attempts        INT          NOT NULL DEFAULT 0,
    last_assessed   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, topic_key),
    CONSTRAINT chk_mastery CHECK (mastery_level IN ('not_started', 'beginner', 'intermediate', 'mastered'))
);
CREATE INDEX IF NOT EXISTS idx_progress_user
    ON progress (user_id);

SQL

echo "==> EduFlow tables created successfully."
echo "    ADK session tables will be auto-created on first backend startup."
echo "    Set SESSION_DB_URI in eduflow_agents/.env to connect the backend."
