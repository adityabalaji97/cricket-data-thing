-- Playing XIs from Cricsheet (info.players): who actually played, not just who batted or bowled. Written by
-- scripts/load_cricsheet.py for every match in its archive that's in `matches`, and backfilled by
-- scripts/backfill_match_players.py. Read by the match preview's likely XIs (services/preview_cards/context.last_xis).
-- position: the order Cricsheet lists the side in (usually, not always, the batting order). Names are the database's
-- (Cricsheet -> ESPNcricinfo id -> the ball-by-ball feed's name), as in the rest of the loader.
CREATE TABLE IF NOT EXISTS match_players (
    match_id   TEXT NOT NULL,
    team       TEXT NOT NULL,
    player     TEXT NOT NULL,
    position   SMALLINT,
    PRIMARY KEY (match_id, team, player)
);
CREATE INDEX IF NOT EXISTS match_players_team_match ON match_players (team, match_id);
