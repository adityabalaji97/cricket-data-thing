-- 003_primer_metrics.sql
--
-- Contextual T20 metrics from Himanish Ganjoo's "T20 Metrics: A Primer" (Aug 2026): par scores,
-- DL-Pro Impact, RAA/WAA, win probability, WPA and leverage. Computed offline by
-- scripts/compute_primer_metrics.py (services/metrics/*) and bulk-loaded here.
--
-- Side tables, deliberately: delivery_details is ~4 GB and every UPDATE there would leave a dead
-- tuple per row, briefly doubling the table on Essential-1's 10 GB cap. These are additive --
-- nothing existing is altered -- so rolling back is DROP TABLE.
--
--   metric_models  one row per fitted model version: DL curve parameters, WP exponent, par
--                  method and the validation summary, so any number here can be traced to the
--                  exact parameters that produced it.
--   match_par      per match: the nested-shrinkage par score and the DL-Pro lambda it implies.
--   ball_metrics   per delivery (delivery_details.id), batting-side perspective; bowling
--                  figures are the negation. Wides carry impact/WP (they move the score and the
--                  chase) but no RAA/WAA, which follow the Primer in excluding wides.
--
-- REAL (float4) throughout: 7 significant digits is far more precision than these numbers have,
-- at half the storage of DOUBLE. ~2.4M men's T20 balls x ~80 bytes ~= 0.2 GB with indexes.

CREATE TABLE IF NOT EXISTS metric_models (
    version      SMALLINT NOT NULL,
    format       VARCHAR(8) NOT NULL,
    gender       VARCHAR(6) NOT NULL,
    fitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    params       JSONB NOT NULL,
    validation   JSONB,
    PRIMARY KEY (version, format, gender)
);

CREATE TABLE IF NOT EXISTS match_par (
    p_match      VARCHAR NOT NULL,
    format       VARCHAR(8) NOT NULL,
    gender       VARCHAR(6) NOT NULL,
    par          REAL,
    lam          REAL,
    par_source   VARCHAR(16),
    version      SMALLINT NOT NULL,
    PRIMARY KEY (p_match)
);

CREATE TABLE IF NOT EXISTS ball_metrics (
    delivery_id  INTEGER PRIMARY KEY,   -- delivery_details.id
    p_match      VARCHAR NOT NULL,
    inns         SMALLINT NOT NULL,
    exp_runs     REAL,
    exp_wkts     REAL,
    raa          REAL,
    waa          REAL,
    impact       REAL,
    wp_before    REAL,
    wp_after     REAL,
    wpa          REAL,
    leverage     REAL,
    version      SMALLINT NOT NULL
);

-- Incremental loads and per-match reads (scorecard, match preview) go by match.
CREATE INDEX IF NOT EXISTS idx_ball_metrics_match ON ball_metrics (p_match);
