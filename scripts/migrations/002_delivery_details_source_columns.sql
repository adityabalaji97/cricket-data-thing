-- 002_delivery_details_source_columns.sql
--
-- Preserve five columns the ball-by-ball CSVs have always carried and the loader has always
-- thrown away (scripts/load_delivery_details_full.py maps `competition` and then skips
-- straight to `bat_hand`).
--
-- They matter now because:
--   * tournament  - the ODI feed leaves `competition` empty for bilateral series (56% of
--                   matches in the sample) and puts the series name here instead. It is the
--                   only source for matches.event_name on those matches.
--   * daynight    - matches.day_or_night is currently NULL for 92% of matches because it is
--                   filled by an IPL-only heuristic. The feed ships it as real data for every
--                   match, so this replaces a guess with a fact.
--   * season      - '2005/06' style label, useful for grouping.
--   * trophy_name - the cleanest signal for normalising competition names, e.g.
--                   'ICC Champions Trophy (ICC KnockOut)' where competition says 'ICC KnockOut'.
--   * rain        - flag for rain-affected matches; explains reduced innings lengths.
--
-- The Test feed (test_bbb.csv) carries four more columns that no other format has, and drops
-- several the others do -- notably it has **no `max_balls` at all**, which is why nothing may
-- depend on that column being present. Adding the Test columns here rather than in a later
-- migration keeps the schema in one place:
--   * day, session   - real day (1-5) and session (1-3) numbers. Far better than deriving Test
--                      phases from over numbers, since sessions are how the game is actually
--                      structured.
--   * trail_by, lead_by - match state, and the signal for follow-on detection.
--
-- All nullable with no default: existing rows genuinely have no value until a refresh
-- backfills them, and a default would assert something untrue. Every format leaves some of
-- these NULL -- Tests have no `rain`/`max_balls`, limited-overs have no `day`/`session`.
--
-- Apply locally first:
--   psql postgresql://localhost:5432/hindsight_local -f scripts/migrations/002_delivery_details_source_columns.sql
-- Then as an explicit promotion step:
--   heroku pg:psql -a cricket-data-thing -f scripts/migrations/002_delivery_details_source_columns.sql
--
-- Idempotent: safe to re-run.

BEGIN;

ALTER TABLE delivery_details
    ADD COLUMN IF NOT EXISTS tournament  VARCHAR,
    ADD COLUMN IF NOT EXISTS season      VARCHAR(16),
    ADD COLUMN IF NOT EXISTS daynight    VARCHAR(24),
    ADD COLUMN IF NOT EXISTS trophy_name VARCHAR,
    ADD COLUMN IF NOT EXISTS rain        REAL;

-- Test-only match state.
ALTER TABLE delivery_details
    ADD COLUMN IF NOT EXISTS day      SMALLINT,
    ADD COLUMN IF NOT EXISTS session  SMALLINT,
    ADD COLUMN IF NOT EXISTS trail_by INTEGER,
    ADD COLUMN IF NOT EXISTS lead_by  INTEGER;

COMMIT;
