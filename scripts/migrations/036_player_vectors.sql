-- Migration 036 (28 Oct 2026): player_vectors, the statistical twins' feature table (DOPPELGANGER_PLAN.md S1).
--
-- One row per player, role and period: a season ("2025") for twins across eras, or a window
-- ("2024-01-01..2026-10-28") for careers. features holds the raw numbers by group (usage, scoring, shots, matchups,
-- value...); the engine (services/twins.py) turns them into percentiles within the period. Rebuilt by
-- scripts/build_player_vectors.py: nightly for the current and previous season, --all for the backfill from 2015.

BEGIN;

CREATE TABLE IF NOT EXISTS player_vectors (
    unit          text        NOT NULL,          -- 'season' | 'window'
    period        text        NOT NULL,          -- '2025' | '2024-01-01..2026-10-28'
    role          text        NOT NULL,          -- 'bat' | 'bowl'
    scope         text        NOT NULL,          -- 'strong' | 'all' (services/player_verdict.scope_params)
    player        text        NOT NULL,          -- canonical name, as the query builder returns it
    balls         integer     NOT NULL,
    innings       integer     NOT NULL,
    qualified     boolean     NOT NULL,          -- cleared the period's floor (services/qualification.py)
    floor_balls   integer     NOT NULL,
    kind          text,                          -- bowlers: 'pace bowler' | 'spin bowler' (style twins match within it)
    tracked_share real,                          -- share of balls with shot / line / length tags
    features      jsonb       NOT NULL,
    built_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (unit, period, role, scope, player)
);

CREATE INDEX IF NOT EXISTS player_vectors_period ON player_vectors (unit, role, scope, period) WHERE qualified;
CREATE INDEX IF NOT EXISTS player_vectors_player ON player_vectors (player);

COMMIT;
