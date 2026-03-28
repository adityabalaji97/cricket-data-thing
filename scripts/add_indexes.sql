-- Performance indexes for cricket-data-thing
-- Run on Heroku Postgres during low traffic. CONCURRENTLY avoids table locks.
-- Usage: heroku pg:psql < scripts/add_indexes.sql

-- matches table (most queried)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_team1_date ON matches(team1, date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_team2_date ON matches(team2, date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_venue_date ON matches(venue, date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_date ON matches(date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_competition ON matches(competition);

-- deliveries table (~50M rows - CRITICAL)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_deliveries_match_id ON deliveries(match_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_deliveries_batter ON deliveries(batter);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_deliveries_bowler ON deliveries(bowler);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_deliveries_batting_team ON deliveries(batting_team);

-- delivery_details table (~100M rows - CRITICAL)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_p_match ON delivery_details(p_match);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_bat ON delivery_details(bat);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_bowl ON delivery_details(bowl);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_team_bat ON delivery_details(team_bat);

-- batting_stats / bowling_stats (used by team_roster.py)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_batting_stats_match_team ON batting_stats(match_id, team);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bowling_stats_match_team ON bowling_stats(match_id, team);

-- player_aliases (scanned in full by every matchup call before caching)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_aliases_alias ON player_aliases(alias_name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_aliases_player ON player_aliases(player_name);
