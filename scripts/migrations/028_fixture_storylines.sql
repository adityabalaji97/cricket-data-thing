-- Talking points per fixture (MATCH_PREVIEW_STORYLINES_PLAN.md chunks 2 and 7; services/preview_storylines.py): what
-- the headlines (fixture_news) are arguing about, as short claims a data tester can check. Every point starts
-- 'pending'; only the user's 'approved' ones reach a preview or a post (decision 1, the review gate).
CREATE TABLE IF NOT EXISTS fixture_storylines (
    id            BIGSERIAL PRIMARY KEY,
    fixture_key   VARCHAR(200) NOT NULL,
    match_date    DATE NOT NULL,
    team1         VARCHAR(100) NOT NULL,
    team2         VARCHAR(100) NOT NULL,
    rank          SMALLINT,
    claim         TEXT NOT NULL,              -- as extracted
    edited_claim  TEXT,                       -- the user's wording, when changed in review
    kind          VARCHAR(20) NOT NULL,       -- selection | form | matchup | conditions | milestone | record | injury | tactics
    players       JSONB NOT NULL DEFAULT '[]',
    team          VARCHAR(100),
    sources       JSONB NOT NULL DEFAULT '[]', -- [{title, outlet, url, published_at}]
    appeal        REAL,
    appeal_by     VARCHAR(20),
    status        VARCHAR(12) NOT NULL DEFAULT 'pending',  -- pending | approved | dropped
    model         VARCHAR(60),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at   TIMESTAMPTZ,
    UNIQUE (fixture_key, claim)
);
CREATE INDEX IF NOT EXISTS idx_fixture_storylines_fixture ON fixture_storylines (fixture_key, status);
