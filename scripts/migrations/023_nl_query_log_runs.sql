-- What happened after a natural-language question was parsed. Before this, nl_query_log only knew the parse:
-- execution_success meant "the model returned JSON" and rows were filled in only on a thumbs up/down.
-- log_ref ties a row to the query-builder run (/query/deliveries?nl_ref=) or graphic attempt that follows it;
-- the first run's outcome is kept and run_count counts re-runs.
ALTER TABLE nl_query_log
    ADD COLUMN IF NOT EXISTS log_ref    VARCHAR(32),
    ADD COLUMN IF NOT EXISTS run_status VARCHAR(16),   -- ok | empty | error | refused (graphic plan) | no_chart
    ADD COLUMN IF NOT EXISTS run_error  TEXT,
    ADD COLUMN IF NOT EXISTS run_ms     INTEGER,
    ADD COLUMN IF NOT EXISTS run_at     TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS run_count  INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_nl_query_log_log_ref ON nl_query_log (log_ref);
