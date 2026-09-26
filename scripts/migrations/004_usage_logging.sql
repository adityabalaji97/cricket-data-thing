-- 004_usage_logging.sql
--
-- First-party usage measurement, so adoption can be tracked week over week (growth plan G0).
-- Until now the only records were Vercel pageviews and the MCP's lines in Heroku's rolling log
-- buffer (~1,500 lines), so "how many people used the connector this week" was unanswerable.
--
--   mcp_call_log  one row per connector tool call. caller_hash is sha256(salt + first
--                 X-Forwarded-For hop): enough to count distinct callers, not to identify anyone.
--   app_events    product events from the website (page views, query runs, shares, game plays).
--                 anon_id is a random per-browser id kept in localStorage -- no personal data.
--
-- Both are written by services/usage_log.py from a background thread (never on the request
-- path) and pruned by the nightly workflow: raw events older than 90 days are deleted, since
-- weekly counts are all the reports need.

CREATE TABLE IF NOT EXISTS mcp_call_log (
    id           BIGSERIAL PRIMARY KEY,
    ts           TIMESTAMPTZ NOT NULL DEFAULT now(),
    tool         VARCHAR(48) NOT NULL,
    outcome      VARCHAR(16) NOT NULL,
    ms           INTEGER,
    client       VARCHAR(80),
    caller_hash  VARCHAR(16),
    args         JSONB
);
CREATE INDEX IF NOT EXISTS idx_mcp_call_log_ts ON mcp_call_log (ts);

CREATE TABLE IF NOT EXISTS app_events (
    id           BIGSERIAL PRIMARY KEY,
    ts           TIMESTAMPTZ NOT NULL DEFAULT now(),
    anon_id      VARCHAR(40) NOT NULL,
    session_id   VARCHAR(40),
    event        VARCHAR(40) NOT NULL,
    path         VARCHAR(200),
    props        JSONB,
    referrer     VARCHAR(200),
    country      VARCHAR(4)
);
CREATE INDEX IF NOT EXISTS idx_app_events_ts ON app_events (ts);
CREATE INDEX IF NOT EXISTS idx_app_events_event_ts ON app_events (event, ts);
