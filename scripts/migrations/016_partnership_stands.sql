-- 016: partnership_stands -- every stand (partnership) in delivery_details, rebuilt from the striker
-- sequence (docs/query_builder_metrics.md, "Partnerships").
--
-- delivery_details.non_striker is wrong around wickets in the feed: on the ball a batter is out it
-- often names the incoming batter, and for a ball or two after it the dismissed one (about 45% of
-- ODI wicket balls since 2000 name a non-striker who never faced in that stand). Grouping by
-- (bat, non_striker) therefore credited the wicket that ended a stand -- and a few balls around it --
-- to a pair that never batted together: Rohit Sharma & Shubman Gill read 22 dismissals in 47 ODI
-- stands (average 140) instead of 46 (66.6).
--
-- A stand is the run of balls between one dismissal (or retirement: any out = 'true') and the next in
-- an innings. Its batters are the distinct strikers in that run, which the feed records reliably;
-- when only one of them faced, the partner is the run's most common non-striker. Canonical names
-- (player_alias_unambiguous). A ball's stand: same p_match and inns, (over, ball) between the stand's
-- first and last ball (delivery_details is unique on p_match, inns, over, ball).
--
-- Built and refreshed by scripts/build_partnership_stands.py (full, or new matches after each load).
-- About 210,000 stands (~25 MB) in Oct 2026, ~22,000 (~3 MB) a year.

CREATE TABLE IF NOT EXISTS partnership_stands (
    p_match     varchar  NOT NULL,
    inns        smallint NOT NULL,
    seq         smallint NOT NULL,          -- 0 = opening stand, 1 = after the first dismissal, ...
    batter_a    varchar,                    -- the pair in alphabetical order; NULL if not determinable
    batter_b    varchar,
    first_over  smallint NOT NULL,
    first_ball  smallint NOT NULL,
    last_over   smallint NOT NULL,
    last_ball   smallint NOT NULL,
    strikers    smallint NOT NULL,          -- distinct batters who faced (more than 2: left unpaired)
    PRIMARY KEY (p_match, inns, seq)
);
