-- app_events.path: 200 -> 1000 characters (8 Nov 2026). A query builder run's page carries its whole question (q=),
-- and the 200 cut left "Recently asked" with partial questions and links that can't be replayed.
-- Widening a varchar is a catalogue change in Postgres (no rewrite). Apply before deploying the code that sends
-- longer paths (routers/usage.py, src/utils/analytics.js).
ALTER TABLE app_events ALTER COLUMN path TYPE varchar(1000);
