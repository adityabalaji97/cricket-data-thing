-- Players by id, chunk 2 (PLAYER_IDS_PLAN.md): the ESPNcricinfo id on the stats tables and the playing XIs, so
-- a name shared by several players ("Rohit Sharma": India, Indonesia, Haryana) is told apart there too. Filled by
-- sync_stats_from_dd.py from delivery_details (p_bat / p_bowl) going forward; scripts/backfill_stats_player_ids.py
-- fills the rows already there. NULL where there's no id: pre-2015 legacy matches, and XI players who neither batted
-- nor bowled.
ALTER TABLE batting_stats ADD COLUMN IF NOT EXISTS pid BIGINT;
ALTER TABLE bowling_stats ADD COLUMN IF NOT EXISTS pid BIGINT;
ALTER TABLE match_players ADD COLUMN IF NOT EXISTS pid BIGINT;
CREATE INDEX IF NOT EXISTS idx_batting_stats_pid ON batting_stats (pid);
CREATE INDEX IF NOT EXISTS idx_bowling_stats_pid ON bowling_stats (pid);
CREATE INDEX IF NOT EXISTS idx_match_players_pid ON match_players (pid);
