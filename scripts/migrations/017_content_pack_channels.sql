-- Content packs for more than one channel (services/ig_backlog.py).
--
-- Until now every pack was a Reddit/X post: one image, a title and a first comment, due by `post_by`. An Instagram
-- account needs a planned calendar instead (one post a day, lined up ~30 days ahead, with a pillar mix), so packs
-- gain a channel, the day they are planned for, their content pillar and an Instagram caption. Existing packs are
-- Reddit packs. The Social tab lists one channel at a time.
ALTER TABLE content_packs ADD COLUMN IF NOT EXISTS channel     TEXT NOT NULL DEFAULT 'reddit';  -- reddit | instagram
ALTER TABLE content_packs ADD COLUMN IF NOT EXISTS planned_for DATE;   -- the day it is meant to go out (NULL = bench)
ALTER TABLE content_packs ADD COLUMN IF NOT EXISTS pillar      TEXT;   -- debate | myth | play | weird | reactive
ALTER TABLE content_packs ADD COLUMN IF NOT EXISTS caption     TEXT;   -- Instagram caption (Reddit uses title + first_comment)

CREATE INDEX IF NOT EXISTS idx_content_packs_channel_plan ON content_packs (channel, planned_for);
