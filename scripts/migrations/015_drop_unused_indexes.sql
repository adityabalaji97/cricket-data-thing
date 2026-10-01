-- Drop indexes production has never used (audit C8, AUDIT_CODEBASE_2026-10.md). ~300 MB on production
-- (4.18 GB database, 2026-10-01), most of it on the legacy deliveries table, whose indexes were 514 MB
-- for an 840 MB table.
--
-- Evidence: production pg_stat_user_indexes on 2026-10-01, read-only; statistics never reset, so the
-- counts cover the database's whole life (idx_dd_p_match: 14.4M scans, matches_pkey: 10.6M). Every
-- index below shows idx_scan = 0 and is either an exact duplicate, a single low-cardinality column,
-- or served features that no longer query it. Indexes that are used but only redundant as prefixes
-- of composites are NOT dropped here (listed in the audit report).
--
-- DROP INDEX CONCURRENTLY cannot run in a transaction block: run this file without BEGIN/COMMIT
-- (psql -f does that). IF EXISTS makes it idempotent and safe on databases missing some of them.
-- To undo one, re-create it from the definition in the comment beside it.

-- delivery_details
DROP INDEX CONCURRENTLY IF EXISTS idx_dd_match;                         -- (p_match): duplicate of idx_dd_p_match, 29 MB

-- deliveries (legacy table)
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_match_innings_over_ball; -- (match_id, innings, over, ball), 71 MB
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_over;                  -- (over)
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_ball;                  -- (ball)
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_bowler_type;           -- (bowler_type)
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_legal_balls;           -- (bowler, wides, noballs) WHERE legal
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_bowler_over_phase;     -- (bowler, over) WHERE <always true>
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_powerplay;             -- (bowler, batter) WHERE over < 6
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_middle;                -- (bowler, batter) WHERE over 6-14
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_death;                 -- (bowler, batter) WHERE over >= 15
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_striker_batter_type;   -- (striker_batter_type)
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_crease_combo;          -- (crease_combo)
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_ball_direction;        -- (ball_direction)
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_batter_bowler_types;   -- (striker_batter_type, non_striker_batter_type, bowler_type)
DROP INDEX CONCURRENTLY IF EXISTS idx_deliveries_left_right_analysis;   -- (crease_combo, ball_direction, striker_batter_type, bowler_type)

-- batting_stats / bowling_stats
DROP INDEX CONCURRENTLY IF EXISTS idx_batting_stats_match_innings;      -- (match_id, innings)
DROP INDEX CONCURRENTLY IF EXISTS idx_batting_stats_fantasy_points;     -- (striker, fantasy_points DESC)
DROP INDEX CONCURRENTLY IF EXISTS idx_batting_stats_fantasy_team;       -- (batting_team, fantasy_points DESC)
DROP INDEX CONCURRENTLY IF EXISTS idx_bowling_stats_fantasy_points;     -- (bowler, fantasy_points DESC)
DROP INDEX CONCURRENTLY IF EXISTS idx_bowling_stats_fantasy_team;       -- (bowling_team, fantasy_points DESC)
