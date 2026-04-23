-- Migration: add foresight prediction columns to match_predictions table.
-- Safe to run multiple times (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

-- New columns for the foresight UI
ALTER TABLE match_predictions ADD COLUMN IF NOT EXISTS league VARCHAR(255);
ALTER TABLE match_predictions ADD COLUMN IF NOT EXISTS team1 VARCHAR(255);
ALTER TABLE match_predictions ADD COLUMN IF NOT EXISTS team2 VARCHAR(255);
ALTER TABLE match_predictions ADD COLUMN IF NOT EXISTS team1_win_prob FLOAT;
ALTER TABLE match_predictions ADD COLUMN IF NOT EXISTS team2_win_prob FLOAT;
ALTER TABLE match_predictions ADD COLUMN IF NOT EXISTS top_features JSONB;
ALTER TABLE match_predictions ADD COLUMN IF NOT EXISTS gates_passed VARCHAR(10);

-- Index for team-pair lookups from the API
CREATE INDEX IF NOT EXISTS idx_mp_teams ON match_predictions(team1, team2);
