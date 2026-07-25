-- Drop and recreate delivery_details with ALL columns from CSV
-- Run: heroku pg:psql -a cricket-data-thing

DROP TABLE IF EXISTS delivery_details;

CREATE TABLE delivery_details (
    id SERIAL PRIMARY KEY,
    p_match VARCHAR NOT NULL,
    inns INTEGER,
    bat VARCHAR,
    p_bat INTEGER,
    team_bat VARCHAR,
    bowl VARCHAR,
    p_bowl INTEGER,
    team_bowl VARCHAR,
    ball INTEGER,
    ball_id FLOAT,
    outcome VARCHAR,
    score INTEGER,
    out VARCHAR,
    dismissal VARCHAR,
    p_out INTEGER,
    over INTEGER,
    noball INTEGER,
    wide INTEGER,
    byes INTEGER,
    legbyes INTEGER,
    cur_bat_runs INTEGER,
    cur_bat_bf INTEGER,
    cur_bowl_ovr FLOAT,
    cur_bowl_wkts INTEGER,
    cur_bowl_runs INTEGER,
    inns_runs INTEGER,
    inns_wkts INTEGER,
    inns_balls INTEGER,
    inns_runs_rem VARCHAR,
    inns_balls_rem INTEGER,
    inns_rr FLOAT,
    inns_rrr VARCHAR,
    target VARCHAR,
    max_balls INTEGER,
    match_date VARCHAR,
    year INTEGER,
    ground VARCHAR,
    country VARCHAR,
    winner VARCHAR,
    toss VARCHAR,
    competition VARCHAR,
    bat_hand VARCHAR(10),
    bowl_style VARCHAR(10),
    bowl_kind VARCHAR(30),
    batruns INTEGER,
    ballfaced INTEGER,
    bowlruns INTEGER,
    bat_out VARCHAR,
    wagon_x INTEGER,
    wagon_y INTEGER,
    wagon_zone INTEGER,
    line VARCHAR(30),
    length VARCHAR(30),
    shot VARCHAR(30),
    control INTEGER,
    pred_score FLOAT,
    win_prob FLOAT,
    -- Cricket format and gender (added by scripts/migrations/001_multi_format_columns.sql).
    -- Denormalized rather than joined from matches: the hot query-builder paths never join
    -- matches, so a WHERE predicate here is far cheaper than adding a join to each of them.
    format VARCHAR(8) NOT NULL DEFAULT 'T20',   -- 'T20' | 'ODI' | 'TEST'
    gender VARCHAR(6) NOT NULL DEFAULT 'male',  -- 'male' | 'female'
    CHECK (format IN ('T20', 'ODI', 'TEST')),
    CHECK (gender IN ('male', 'female')),
    UNIQUE(p_match, inns, over, ball)
);

CREATE INDEX idx_dd_match ON delivery_details(p_match);
CREATE INDEX idx_dd_bat ON delivery_details(bat);
CREATE INDEX idx_dd_bowl ON delivery_details(bowl);
CREATE INDEX idx_dd_competition ON delivery_details(competition);
CREATE INDEX idx_dd_year ON delivery_details(year);
-- Partial: men's T20 remains the dominant workload and keeps using the indexes above,
-- so this only has to make the smaller non-T20 slices selective.
CREATE INDEX idx_dd_format_gender ON delivery_details(format, gender)
    WHERE format <> 'T20' OR gender <> 'male';
