-- Squad moves between auctions (XI_BUILDER_PLAN.md X0; 11 Nov 2026): trades, retentions and releases for the coming
-- season, on top of the last auction's squads (auction_lots, migration 038). A team's squad as of a date =
-- its auction_lots players, minus moves out, plus moves in (services/ipl_squads.py).
--   kind:  trade | retained | released | bought
--   state: confirmed (announced by a team or the league) | reported (agreed in reports, not yet official)
CREATE TABLE IF NOT EXISTS squad_moves (
    id           serial PRIMARY KEY,
    league       varchar(16)  NOT NULL DEFAULT 'ipl',
    season       smallint     NOT NULL,             -- the season the move is for (2027)
    deal         varchar(40),                       -- moves made together (a two-way trade) share a deal id
    player_name  varchar(120) NOT NULL,             -- our display name
    pid          integer,
    from_team    varchar(10),
    to_team      varchar(10),
    price_lakh   numeric(8, 2),
    kind         varchar(12)  NOT NULL,
    state        varchar(12)  NOT NULL DEFAULT 'confirmed',
    source       varchar(200),
    announced    date,
    created_at   timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS squad_moves_season ON squad_moves (league, season);
