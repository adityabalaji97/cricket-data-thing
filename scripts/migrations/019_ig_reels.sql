-- Instagram Reels (services/ig_slides.make_reel): a 9:16 MP4 of a carousel's rendered slides, crossfaded, made with
-- ffmpeg right after the slides render. Served at /snapshots/<carousel>/reel.mp4. One to three MB each.
CREATE TABLE IF NOT EXISTS ig_reels (
    carousel_id  TEXT PRIMARY KEY,
    mp4          BYTEA NOT NULL,
    seconds      REAL NOT NULL,
    made_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
