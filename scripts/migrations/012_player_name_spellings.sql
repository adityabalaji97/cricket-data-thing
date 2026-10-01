-- Every player-name spelling actually stored in the ball tables, keyed by lower case (audit C2).
--
-- Matchups filtered on COALESCE(alias.canonical_name, dd.bat) = ANY(:players), which no index can
-- serve: every T20 ball was scanned and alias-joined to keep ~1k (5 s in the match preview once
-- the planner saw real alias statistics). The service now expands the players to their stored
-- spellings first and pre-filters dd.bat / dd.bowl = ANY(:spellings), which idx_dd_bat /
-- idx_dd_bowl serve. Alias rows are not enough for that expansion: the alias map matches names
-- case-insensitively, and the feed can store a case variant no alias row spells
-- ("Aravinda de Silva" vs "Aravinda De Silva"), which an exact pre-filter would silently drop.
--
-- A new player needs no row here to be found (his canonical name is his stored spelling); this
-- only adds case variants, so the nightly refresh after the loads keeps it current.
-- MUST be applied before deploying code that references it. Idempotent.

BEGIN;

CREATE MATERIALIZED VIEW IF NOT EXISTS player_name_spellings AS
    SELECT DISTINCT LOWER(name) AS name_key, name
    FROM (
        SELECT bat AS name FROM delivery_details WHERE bat IS NOT NULL
        UNION SELECT bowl FROM delivery_details WHERE bowl IS NOT NULL
        UNION SELECT batter FROM deliveries WHERE batter IS NOT NULL
        UNION SELECT bowler FROM deliveries WHERE bowler IS NOT NULL
    ) n;

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_name_spellings_name ON player_name_spellings (name);
CREATE INDEX IF NOT EXISTS idx_player_name_spellings_key ON player_name_spellings (name_key);

COMMIT;

REFRESH MATERIALIZED VIEW player_name_spellings;
ANALYZE player_name_spellings;
