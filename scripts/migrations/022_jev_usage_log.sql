-- Every Jev (TypeSafe) call: what it cost in tokens and which process made it (services/jev_client.ask). TypeSafe's
-- API reports usage only per call, so this is the running total; the admin usage report sums it by week.
CREATE TABLE IF NOT EXISTS jev_usage_log (
    id            BIGSERIAL PRIMARY KEY,
    ts            TIMESTAMPTZ NOT NULL DEFAULT now(),
    source        TEXT,          -- the script (deep_cut_backfill.py, ig_match_day.py ...) or "web"
    questions     INTEGER,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    ms            INTEGER,
    ok            BOOLEAN NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jev_usage_log_ts ON jev_usage_log (ts);
