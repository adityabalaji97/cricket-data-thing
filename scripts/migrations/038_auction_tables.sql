-- IPL auction lots and bids (SOCIAL_CALENDAR.md "Auction data"; 10 Nov 2026). From Cricbuzz's auction pages
-- (data/auction_raw, scraped by the user): 2018-26 complete, 2008-17 the top 20 lots a year. Facts only (status,
-- team, prices, bids); no Cricbuzz text or images. pid: our player id (ESPNcricinfo's), matched by name; NULL when
-- no single player matched.
CREATE TABLE IF NOT EXISTS auction_lots (
    tournament   varchar(16)  NOT NULL,
    year         smallint     NOT NULL,
    cb_player_id integer      NOT NULL,
    player_name  varchar(120) NOT NULL,
    pid          integer,
    country      varchar(60),
    role         varchar(40),
    status       varchar(20)  NOT NULL,   -- sold, unsold, retained, rtm, traded, drafted, replacement
    team         varchar(10),
    base_lakh    numeric(8, 2),
    price_lakh   numeric(8, 2),
    capped       boolean,
    overseas     boolean,
    bids         smallint,
    PRIMARY KEY (tournament, year, cb_player_id)
);
CREATE INDEX IF NOT EXISTS auction_lots_pid ON auction_lots (pid);

-- One row per bid, bid_no 1 the opening bid (Cricbuzz lists the winning bid first).
CREATE TABLE IF NOT EXISTS auction_bids (
    tournament   varchar(16)  NOT NULL,
    year         smallint     NOT NULL,
    cb_player_id integer      NOT NULL,
    bid_no       smallint     NOT NULL,
    team         varchar(10),
    price_lakh   numeric(8, 2),
    PRIMARY KEY (tournament, year, cb_player_id, bid_no)
);
