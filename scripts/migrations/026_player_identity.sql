-- Players by ESPNcricinfo id, not by name (PLAYER_IDS_PLAN.md chunk 0). delivery_details carries each player's id on
-- every ball (p_bat, p_bowl); names collide (Rohit Sharma is India's 34102, Indonesia's 1542004, Haryana's 934943).
-- player_identity gives every id one display name: where ids share a name, the one with the most balls keeps it and
-- the others carry their main side ("Rohit Sharma (Indonesia)"). Rebuilt nightly (scripts/build_player_identity.py).
CREATE TABLE IF NOT EXISTS player_identity (
    pid           BIGINT PRIMARY KEY,
    display_name  TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,              -- the canonical spelling (alias map) the id is known by
    main_side     TEXT,                       -- national side if any, else the side with most balls
    balls         INTEGER NOT NULL,
    first_date    DATE,
    last_date     DATE,
    built_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_player_identity_name ON player_identity (name);

-- Looking balls up by player id (no index today; the Cricsheet loader notes ~3 s full scans). CONCURRENTLY: no lock
-- on the nightly load or the site while they build. Run outside a transaction (psql -f does).
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_p_bat ON delivery_details (p_bat);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_p_bowl ON delivery_details (p_bowl);
