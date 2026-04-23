-- Chunk 9 migration: foresight/hindsight prediction storage tables.

CREATE TABLE IF NOT EXISTS match_predictions (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(255) REFERENCES matches(id),
    prediction_date TIMESTAMP DEFAULT NOW(),
    model_version VARCHAR(50) NOT NULL,

    -- Match winner prediction
    predicted_winner VARCHAR(255),
    win_probability DECIMAL(5,3),

    -- Score predictions
    predicted_1st_innings_score_low INTEGER,
    predicted_1st_innings_score_high INTEGER,
    predicted_1st_innings_score_mean DECIMAL(6,2),
    predicted_2nd_innings_score_low INTEGER,
    predicted_2nd_innings_score_high INTEGER,
    predicted_2nd_innings_score_mean DECIMAL(6,2),

    -- Structured prediction payloads
    predicted_phase_performance JSONB,
    predicted_player_performance JSONB,
    feature_snapshot JSONB,

    -- Existing preview signal snapshots
    preview_lean_score INTEGER,
    preview_lean_direction VARCHAR(50),

    CONSTRAINT uq_match_predictions_match_model UNIQUE (match_id, model_version)
);

CREATE INDEX IF NOT EXISTS idx_match_predictions_match_id
    ON match_predictions (match_id);

CREATE INDEX IF NOT EXISTS idx_match_predictions_prediction_date
    ON match_predictions (prediction_date DESC);


CREATE TABLE IF NOT EXISTS hindsight_comparisons (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(255) REFERENCES matches(id),
    prediction_id INTEGER REFERENCES match_predictions(id),
    computed_at TIMESTAMP DEFAULT NOW(),

    -- Outcome accuracy
    winner_correct BOOLEAN,
    score_1st_innings_actual INTEGER,
    score_1st_innings_error DECIMAL(6,2),
    score_2nd_innings_actual INTEGER,
    score_2nd_innings_error DECIMAL(6,2),

    -- Detailed accuracy payloads
    phase_accuracy JSONB,
    player_accuracy JSONB,
    metric_accuracies JSONB,
    calibration_score DECIMAL(5,3),

    CONSTRAINT uq_hindsight_match_prediction UNIQUE (match_id, prediction_id)
);

CREATE INDEX IF NOT EXISTS idx_hindsight_comparisons_match_id
    ON hindsight_comparisons (match_id);

CREATE INDEX IF NOT EXISTS idx_hindsight_comparisons_prediction_id
    ON hindsight_comparisons (prediction_id);

CREATE INDEX IF NOT EXISTS idx_hindsight_comparisons_computed_at
    ON hindsight_comparisons (computed_at DESC);
