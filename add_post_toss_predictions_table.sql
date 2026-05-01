-- Audit trail for post-toss xPoints computations.
-- Stores the request payload and derived outputs so we can evaluate model
-- quality against hindsight results later.

CREATE TABLE IF NOT EXISTS post_toss_predictions (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(255) REFERENCES matches(id),
    computed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    payload JSONB NOT NULL,
    result JSONB NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'manual'
);

CREATE INDEX IF NOT EXISTS idx_post_toss_predictions_match_id
ON post_toss_predictions(match_id);

CREATE INDEX IF NOT EXISTS idx_post_toss_predictions_computed_at
ON post_toss_predictions(computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_post_toss_predictions_source
ON post_toss_predictions(source);

