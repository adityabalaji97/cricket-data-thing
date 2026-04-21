-- Chunk 4 migration: persistent NL query logging and feedback learning table.
CREATE TABLE IF NOT EXISTS nl_query_log (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    parsed_filters JSONB,
    query_mode VARCHAR(50),
    group_by JSONB,
    explanation TEXT,
    confidence VARCHAR(20),
    model_used VARCHAR(50),
    execution_success BOOLEAN,
    result_row_count INTEGER,
    user_feedback VARCHAR(20),
    refined_query_text TEXT,
    ip_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    execution_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_nl_query_log_created_at
    ON nl_query_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nl_query_log_feedback
    ON nl_query_log (user_feedback);

CREATE INDEX IF NOT EXISTS idx_nl_query_log_mode_feedback
    ON nl_query_log (query_mode, user_feedback);
