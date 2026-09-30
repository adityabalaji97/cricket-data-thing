-- Notes, chart snapshots, content packs, a persistent query cache, and match data provenance.
-- See the Notes plan (bot + human posts, phone approval queue, embeds, Reddit-ready packs).
-- Idempotent: safe to re-run.

BEGIN;

-- Data version: bumped by the nightly load; part of every query-cache key, so new data
-- invalidates cached results without a sweep.
CREATE TABLE IF NOT EXISTS app_meta (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO app_meta (key, value) VALUES ('data_version', to_char(now(), 'YYYY-MM-DD"T"HH24:MI'))
ON CONFLICT (key) DO NOTHING;

-- Query builder results, keyed by sha256(normalized params + data_version). Shared by the site,
-- the connector and embeds; survives dyno restarts.
CREATE TABLE IF NOT EXISTS query_cache (
    key          TEXT PRIMARY KEY,
    params       JSONB NOT NULL,
    result       JSON NOT NULL,                -- json, not jsonb: keeps key (column) order
    data_version TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    hits         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_query_cache_version ON query_cache (data_version);

-- Frozen chart data that notes, embeds and share images render. params_hash de-duplicates.
CREATE TABLE IF NOT EXISTS chart_snapshots (
    id          TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,              -- query | win_prob | recap
    params      JSONB NOT NULL,
    params_hash TEXT NOT NULL,
    data        JSON NOT NULL,                 -- json, not jsonb: keeps key (column) order
    title       TEXT,
    created_by  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_chart_snapshots_hash ON chart_snapshots (kind, params_hash);

CREATE TABLE IF NOT EXISTS note_authors (
    id         SERIAL PRIMARY KEY,
    slug       TEXT UNIQUE NOT NULL,
    name       TEXT NOT NULL,
    bio        TEXT,
    is_bot     BOOLEAN NOT NULL DEFAULT FALSE,
    token_hash TEXT,                        -- sha256 of a personal token (friends: drafts only)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO note_authors (slug, name, bio, is_bot)
VALUES ('hindsight-bot', 'Hindsight Bot', 'An AI analyst. Numbers from Hindsight; method: Ganjoo''s T20 Primer.', TRUE)
ON CONFLICT (slug) DO NOTHING;

CREATE TABLE IF NOT EXISTS notes (
    id           SERIAL PRIMARY KEY,
    slug         TEXT UNIQUE NOT NULL,
    title        TEXT NOT NULL,
    dek          TEXT,
    body_md      TEXT NOT NULL DEFAULT '',
    kind         TEXT NOT NULL DEFAULT 'article',   -- recap | preview | analysis | article
    author_id    INTEGER NOT NULL REFERENCES note_authors(id),
    status       TEXT NOT NULL DEFAULT 'draft',     -- draft | published | rejected
    match_id     TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_notes_status ON notes (status, published_at DESC);

-- Reddit/X-ready packs: image + title + first comment, generated per newly loaded match.
CREATE TABLE IF NOT EXISTS content_packs (
    id            SERIAL PRIMARY KEY,
    match_id      TEXT,
    snapshot_id   TEXT REFERENCES chart_snapshots(id),
    angle_key     TEXT,                    -- de-dupes the same angle across runs
    title         TEXT NOT NULL,
    first_comment TEXT,
    subreddit     TEXT,
    flair         TEXT,
    facts         JSONB,
    rule_warnings JSONB,
    status        TEXT NOT NULL DEFAULT 'ready',   -- ready | posted | skipped | expired
    post_by       TIMESTAMPTZ,
    posted_url    TEXT,
    source        TEXT NOT NULL DEFAULT 'scanner', -- scanner | recap | idea
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_packs_angle ON content_packs (angle_key) WHERE angle_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_content_packs_status ON content_packs (status, created_at DESC);

-- Ideas parked until the match they need is loaded.
CREATE TABLE IF NOT EXISTS content_ideas (
    id          SERIAL PRIMARY KEY,
    text        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'parked',  -- parked | resolved | failed
    params      JSONB,
    pack_id     INTEGER REFERENCES content_packs(id),
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

-- Where a match came from, so a Cricsheet-loaded match can be upgraded when the ball-by-ball
-- CSV arrives (refresh the row, recompute stats) instead of being left on the basic data.
ALTER TABLE matches ADD COLUMN IF NOT EXISTS data_source TEXT;
UPDATE matches m SET data_source = 'bbb'
WHERE data_source IS NULL AND EXISTS (SELECT 1 FROM delivery_details d WHERE d.p_match = m.id);
UPDATE matches SET data_source = 'legacy' WHERE data_source IS NULL;

COMMIT;
