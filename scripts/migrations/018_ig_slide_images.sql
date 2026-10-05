-- Instagram carousel slides as rendered PNGs (services/ig_slides.py, scripts/render_ig_slides.mjs).
--
-- A carousel's slides are drawn by the app's own React components (/ig/<carousel>/<n>, the same visuals as the match
-- preview story) and screenshotted in headless Chrome at 1080x1350. The PNGs live here and are served at
-- /snapshots/<carousel>/slides/<n>.png; api/img.mjs returns them for /img/<carousel>.png?slide=n and falls back to its
-- own drawing for a carousel with no rendered slides. About 120 KB a slide.
CREATE TABLE IF NOT EXISTS ig_slide_images (
    carousel_id  TEXT NOT NULL,
    n            SMALLINT NOT NULL,
    png          BYTEA NOT NULL,
    rendered_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (carousel_id, n)
);
