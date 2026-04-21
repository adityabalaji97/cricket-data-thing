-- Chunk 8 migration: add token usage tracking columns to nl_query_log
-- for GPT-4o primary / 4o-mini fallback cost management.

ALTER TABLE nl_query_log ADD COLUMN IF NOT EXISTS prompt_tokens INTEGER;
ALTER TABLE nl_query_log ADD COLUMN IF NOT EXISTS completion_tokens INTEGER;
ALTER TABLE nl_query_log ADD COLUMN IF NOT EXISTS estimated_cost_usd DECIMAL(8,6);

CREATE INDEX IF NOT EXISTS idx_nl_query_log_cost_month
    ON nl_query_log (created_at, estimated_cost_usd)
    WHERE estimated_cost_usd IS NOT NULL;
