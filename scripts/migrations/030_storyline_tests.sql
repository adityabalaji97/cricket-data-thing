-- Storyline testers (MATCH_PREVIEW_STORYLINES_PLAN.md chunk 3; services/storyline_testers.py): each approved talking
-- point answered from the data. test = {verdict, finding, card, query_url, direction}; verdict is supported |
-- not supported | partly | too little data | context.
ALTER TABLE fixture_storylines ADD COLUMN IF NOT EXISTS test JSONB;
ALTER TABLE fixture_storylines ADD COLUMN IF NOT EXISTS tested_at TIMESTAMPTZ;
