CREATE SCHEMA IF NOT EXISTS ai_sync;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS ai_sync.review_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id text NOT NULL,
    issue_number integer,
    agent text NOT NULL DEFAULT 'claude-code',
    changed_files text[] NOT NULL DEFAULT '{}'::text[],
    score integer NOT NULL CHECK (score >= 0 AND score <= 120),
    reward_delta integer NOT NULL,
    verdict text NOT NULL CHECK (verdict IN ('PASS', 'PASS_WITH_ADVISORY', 'FAIL', 'UNKNOWN', 'NOT_APPLICABLE')),
    findings_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    report_json jsonb,
    report_digest text,
    house_rules_ver integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS review_runs_agent_created_at_idx
    ON ai_sync.review_runs (agent, created_at DESC);

CREATE TABLE IF NOT EXISTS ai_sync.reward_ledger (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent text NOT NULL,
    session_id text,
    cumulative_coins numeric(10, 2) NOT NULL DEFAULT 0,
    last_delta integer,
    last_verdict text CHECK (last_verdict IN ('PASS', 'PASS_WITH_ADVISORY', 'FAIL', 'UNKNOWN', 'NOT_APPLICABLE')),
    streak_pass integer NOT NULL DEFAULT 0 CHECK (streak_pass >= 0),
    streak_block integer NOT NULL DEFAULT 0 CHECK (streak_block >= 0),
    updated_at timestamptz NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS reward_ledger_agent_updated_at_idx
    ON ai_sync.reward_ledger (agent, updated_at DESC);

-- Backward-compatible C14 migration for already-created tables. Existing rows remain valid;
-- legacy rows retain NULL canonical-report fields.
ALTER TABLE ai_sync.review_runs
    ADD COLUMN IF NOT EXISTS report_json jsonb,
    ADD COLUMN IF NOT EXISTS report_digest text;

ALTER TABLE ai_sync.review_runs
    DROP CONSTRAINT IF EXISTS review_runs_verdict_check;
ALTER TABLE ai_sync.review_runs
    ADD CONSTRAINT review_runs_verdict_check
    CHECK (verdict IN ('PASS', 'PASS_WITH_ADVISORY', 'FAIL', 'UNKNOWN', 'NOT_APPLICABLE'));

ALTER TABLE ai_sync.reward_ledger
    DROP CONSTRAINT IF EXISTS reward_ledger_last_verdict_check;
ALTER TABLE ai_sync.reward_ledger
    ADD CONSTRAINT reward_ledger_last_verdict_check
    CHECK (last_verdict IN ('PASS', 'PASS_WITH_ADVISORY', 'FAIL', 'UNKNOWN', 'NOT_APPLICABLE'));
