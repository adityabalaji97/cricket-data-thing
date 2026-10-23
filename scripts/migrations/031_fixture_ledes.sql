-- The preview's lede (MATCH_PREVIEW_STORYLINES_PLAN.md chunk 5): two or three sentences written from the fixture's
-- approved, tested talking points only, every number checked against their findings (services/summary_check.py).
-- Written when a point is approved, edited or re-tested; the preview reads it, never writes it.
CREATE TABLE IF NOT EXISTS fixture_ledes (
    fixture_key  VARCHAR(200) PRIMARY KEY,
    lede         TEXT NOT NULL,
    point_ids    JSONB NOT NULL DEFAULT '[]',
    dropped      JSONB NOT NULL DEFAULT '[]',  -- sentences the number check refused
    model        VARCHAR(60),
    written_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
