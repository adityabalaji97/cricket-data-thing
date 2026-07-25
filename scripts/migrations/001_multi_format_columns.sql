-- 001_multi_format_columns.sql
--
-- Adds the format/gender discriminators that the multi-format expansion (ODIs, women's
-- T20s, Tests) hangs off. See MULTI_FORMAT_PLAN.md decision D1.
--
-- Every row that exists today is a men's T20 delivery, so the column defaults are already
-- correct for the whole table and no data backfill is needed. On PostgreSQL 11+ adding a
-- column with a non-volatile DEFAULT is a catalogue-only change, so this stays fast even
-- on the 2.3M-row delivery_details table.
--
-- Apply locally first:
--   psql postgresql://localhost:5432/hindsight_local -f scripts/migrations/001_multi_format_columns.sql
-- Then, as an explicit promotion step:
--   heroku pg:psql -a cricket-data-thing -f scripts/migrations/001_multi_format_columns.sql
--
-- Idempotent: safe to re-run.

BEGIN;

-- ---------------------------------------------------------------------------------------
-- 1. Format / gender columns
-- ---------------------------------------------------------------------------------------
-- 'T20' | 'ODI' | 'TEST'   and   'male' | 'female'
--
-- NB: matches.match_type already exists and means 'league' vs 'international'. It is
-- orthogonal to the cricket format and is deliberately left untouched.

ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS format VARCHAR(8) NOT NULL DEFAULT 'T20',
    ADD COLUMN IF NOT EXISTS gender VARCHAR(6) NOT NULL DEFAULT 'male';

ALTER TABLE delivery_details
    ADD COLUMN IF NOT EXISTS format VARCHAR(8) NOT NULL DEFAULT 'T20',
    ADD COLUMN IF NOT EXISTS gender VARCHAR(6) NOT NULL DEFAULT 'male';

ALTER TABLE batting_stats
    ADD COLUMN IF NOT EXISTS format VARCHAR(8) NOT NULL DEFAULT 'T20',
    ADD COLUMN IF NOT EXISTS gender VARCHAR(6) NOT NULL DEFAULT 'male';

ALTER TABLE bowling_stats
    ADD COLUMN IF NOT EXISTS format VARCHAR(8) NOT NULL DEFAULT 'T20',
    ADD COLUMN IF NOT EXISTS gender VARCHAR(6) NOT NULL DEFAULT 'male';

-- The legacy `deliveries` table intentionally gets no columns: it holds pre-2015 men's T20
-- data only, and table routing (plan decision D5) keeps other formats out of it.

ALTER TABLE players
    ADD COLUMN IF NOT EXISTS gender VARCHAR(6) NOT NULL DEFAULT 'male';

-- ---------------------------------------------------------------------------------------
-- 2. Value constraints
-- ---------------------------------------------------------------------------------------
-- Cheap insurance against a mis-set --format flag in the loader writing e.g. 'odi' or 'Test'
-- and quietly splitting the data into two buckets that no query joins back together.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'matches_format_check') THEN
        ALTER TABLE matches ADD CONSTRAINT matches_format_check
            CHECK (format IN ('T20', 'ODI', 'TEST'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'matches_gender_check') THEN
        ALTER TABLE matches ADD CONSTRAINT matches_gender_check
            CHECK (gender IN ('male', 'female'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'delivery_details_format_check') THEN
        ALTER TABLE delivery_details ADD CONSTRAINT delivery_details_format_check
            CHECK (format IN ('T20', 'ODI', 'TEST'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'delivery_details_gender_check') THEN
        ALTER TABLE delivery_details ADD CONSTRAINT delivery_details_gender_check
            CHECK (gender IN ('male', 'female'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'players_gender_check') THEN
        ALTER TABLE players ADD CONSTRAINT players_gender_check
            CHECK (gender IN ('male', 'female'));
    END IF;
END $$;

-- ---------------------------------------------------------------------------------------
-- 3. players: UNIQUE(name) -> UNIQUE(name, gender)
-- ---------------------------------------------------------------------------------------
-- Women's and men's cricket share plenty of player names. Nothing references players(name)
-- by foreign key (lookups are by name string), so swapping the constraint is safe.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'players_name_key') THEN
        ALTER TABLE players DROP CONSTRAINT players_name_key;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'players_name_gender_key') THEN
        ALTER TABLE players ADD CONSTRAINT players_name_gender_key UNIQUE (name, gender);
    END IF;
END $$;

COMMIT;

-- ---------------------------------------------------------------------------------------
-- 4. Indexes
-- ---------------------------------------------------------------------------------------
-- Partial on purpose. Men's T20 stays the dominant workload and its queries keep using the
-- existing venue/date/competition indexes exactly as before; this one only has to make the
-- comparatively small non-T20 slices selective. Keeping T20 rows out of it also keeps it
-- tiny. Revisit with EXPLAIN ANALYZE after the Phase A load if T20 latency regresses.
--
-- CONCURRENTLY cannot run inside a transaction block, hence its position after COMMIT.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_format_gender
    ON delivery_details (format, gender)
    WHERE format <> 'T20' OR gender <> 'male';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_matches_format_gender
    ON matches (format, gender, date);
