-- Headlines per upcoming fixture (MATCH_PREVIEW_STORYLINES_PLAN.md chunk 1; services/preview_news.py): what is being
-- said before a match, for the storylines. Only the headline, outlet, link, time and the feed's own one-line summary;
-- never article text (decision 3). One row per fixture and link; a later fetch refreshes fetched_at.
CREATE TABLE IF NOT EXISTS fixture_news (
    id            BIGSERIAL PRIMARY KEY,
    fixture_key   VARCHAR(200) NOT NULL,      -- "2026-10-24|New Zealand|India"
    match_date    DATE NOT NULL,
    team1         VARCHAR(100) NOT NULL,
    team2         VARCHAR(100) NOT NULL,
    series        VARCHAR(200),
    title         TEXT NOT NULL,
    outlet        VARCHAR(200),
    url           TEXT NOT NULL,
    published_at  TIMESTAMPTZ,
    summary       TEXT,
    source        VARCHAR(50) NOT NULL,       -- "Google News", "r/Cricket", "Cricinfo"
    query         TEXT,                       -- the search that found it (Google News)
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fixture_key, url)
);
CREATE INDEX IF NOT EXISTS idx_fixture_news_fixture ON fixture_news (fixture_key, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_fixture_news_date ON fixture_news (match_date);
