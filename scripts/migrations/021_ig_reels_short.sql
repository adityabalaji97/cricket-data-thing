-- The YouTube Shorts cut of a Reel (services/ig_reel_v2.make_short): the Reel with its 9:16 cover held for the last
-- half-second, so the cover can be picked as the Short's thumbnail (custom thumbnail uploads need the YouTube Partner
-- Program). Served at /snapshots/<carousel>/short.mp4; NULL until made (the route then serves the Reel).
ALTER TABLE ig_reels ADD COLUMN IF NOT EXISTS short_mp4 BYTEA;
