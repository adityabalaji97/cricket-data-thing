-- Notes, steps 3-7: the site owner's byline, and one bot draft per match and kind.
-- Idempotent: safe to re-run.

BEGIN;

-- The admin's own byline. Notes created from the admin queue are signed with this row unless
-- another author is chosen; friends are added later through POST /admin/authors.
INSERT INTO note_authors (slug, name, bio, is_bot)
VALUES ('aditya', 'Aditya Balaji', 'Builds Hindsight.', FALSE)
ON CONFLICT (slug) DO NOTHING;

-- The nightly drafter (scripts/draft_notes.py) writes at most one recap and one preview per
-- match, however often it runs. Human articles carry no match_id and are unaffected.
CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_bot_match
    ON notes (kind, match_id) WHERE match_id IS NOT NULL AND kind IN ('recap', 'preview');

-- A note made from a content pack ("Make note" in the Social queue) points back at it, so the
-- pack's first-comment link can land on the post instead of a bare query.
ALTER TABLE notes ADD COLUMN IF NOT EXISTS pack_id INTEGER REFERENCES content_packs(id);

COMMIT;
