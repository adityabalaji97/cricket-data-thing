-- Materialised player-alias lookups (audit C3, AUDIT_CODEBASE_2026-10.md).
--
-- services/player_aliases.py's ALIAS_MAP_CTE and UNAMBIGUOUS_ALIASES were derived tables that every
-- query rebuilt (DISTINCT ON over a UNION / GROUP BY ... HAVING over player_aliases): ~40 ms each,
-- misestimated by the planner (200 rows estimated vs 7,256 real), and in the match preview probed
-- once per joined ball (3,325 probes, 1.8 s). These views hold the same rows -- the SQL below is
-- the definitions verbatim -- with unique indexes, and the Python constants now read from them.
--
-- MUST be applied before deploying code that references them (the constants name these views).
-- player_aliases changes only through migrations and the alias maintenance scripts; each of those
-- calls services.player_aliases.refresh_alias_views(), and the nightly workflow refreshes too.
-- A migration that edits player_aliases should end with the two REFRESH statements below.
--
-- Idempotent: safe to re-run.

BEGIN;

-- Legacy -> canonical pairs for legacy names that map to exactly one canonical name.
CREATE MATERIALIZED VIEW IF NOT EXISTS player_alias_unambiguous AS
    SELECT pa.player_name, pa.alias_name
    FROM player_aliases pa
    JOIN (
        SELECT player_name
        FROM player_aliases
        WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
        GROUP BY player_name
        HAVING COUNT(DISTINCT alias_name) = 1
    ) unambiguous ON unambiguous.player_name = pa.player_name;

-- (player_name, alias_name) is unique in player_aliases and each kept player_name has one
-- alias, so player_name is unique here; the unique index also enables REFRESH ... CONCURRENTLY.
CREATE UNIQUE INDEX IF NOT EXISTS idx_player_alias_unambiguous_player
    ON player_alias_unambiguous (player_name);

-- Any spelling (lower-cased) -> canonical name. Canonical names map to themselves first.
CREATE MATERIALIZED VIEW IF NOT EXISTS player_alias_map AS
    SELECT DISTINCT ON (name_key) name_key, canonical_name
    FROM (
        SELECT LOWER(alias_name) AS name_key, alias_name AS canonical_name, 0 AS priority
        FROM player_aliases
        WHERE alias_name IS NOT NULL

        UNION ALL

        SELECT LOWER(pa.player_name) AS name_key, pa.alias_name AS canonical_name, 1 AS priority
        FROM player_aliases pa
        JOIN (
            SELECT player_name
            FROM player_aliases
            WHERE player_name IS NOT NULL AND alias_name IS NOT NULL
            GROUP BY player_name
            HAVING COUNT(DISTINCT alias_name) = 1
        ) unambiguous ON unambiguous.player_name = pa.player_name
        WHERE pa.player_name IS NOT NULL AND pa.alias_name IS NOT NULL
    ) mapped
    ORDER BY name_key, priority, canonical_name;

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_alias_map_key ON player_alias_map (name_key);

COMMIT;

-- Populate (a no-op on first creation, which already fills the views; correct on re-runs).
REFRESH MATERIALIZED VIEW player_alias_unambiguous;
REFRESH MATERIALIZED VIEW player_alias_map;
ANALYZE player_alias_unambiguous;
ANALYZE player_alias_map;
