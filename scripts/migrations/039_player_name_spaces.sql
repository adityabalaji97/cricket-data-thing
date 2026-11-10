-- Player names with a non-breaking space or a double space (10 Nov 2026): 19 players from the ball-by-ball feed
-- ("Raj<nbsp>Bawa", "Kavin  Bandara") didn't match anything typed normally (search, query builder, connector).
-- Cleaned to single spaces everywhere they're stored. Checked first on production: no cleaned name belongs to
-- another player (player_identity.display_name is unique). Afterwards bump the data version
-- (services/query_cache.bump_data_version) so cached results drop the old spellings.
-- New feed rows are cleaned on load (scripts/load_delivery_details_full.py).
BEGIN;
CREATE OR REPLACE FUNCTION pg_temp.clean(t text) RETURNS text LANGUAGE sql IMMUTABLE AS
$$ SELECT regexp_replace(btrim(regexp_replace(t, E' ', ' ', 'g')), ' {2,}', ' ', 'g') $$;

UPDATE delivery_details SET bat = pg_temp.clean(bat) WHERE bat ~ E' ' OR bat LIKE '%  %';
UPDATE delivery_details SET bowl = pg_temp.clean(bowl) WHERE bowl ~ E' ' OR bowl LIKE '%  %';
UPDATE delivery_details SET non_striker = pg_temp.clean(non_striker) WHERE non_striker ~ E' ' OR non_striker LIKE '%  %';
UPDATE batting_stats SET striker = pg_temp.clean(striker) WHERE striker ~ E' ' OR striker LIKE '%  %';
UPDATE bowling_stats SET bowler = pg_temp.clean(bowler) WHERE bowler ~ E' ' OR bowler LIKE '%  %';
UPDATE partnership_stands SET batter_a = pg_temp.clean(batter_a) WHERE batter_a ~ E' ' OR batter_a LIKE '%  %';
UPDATE partnership_stands SET batter_b = pg_temp.clean(batter_b) WHERE batter_b ~ E' ' OR batter_b LIKE '%  %';
UPDATE player_identity SET display_name = pg_temp.clean(display_name), name = pg_temp.clean(name)
 WHERE display_name ~ E' ' OR display_name LIKE '%  %' OR name ~ E' ' OR name LIKE '%  %';
UPDATE player_vectors SET player = pg_temp.clean(player) WHERE player ~ E' ' OR player LIKE '%  %';
-- Aliases: a cleaned pair that already exists (the unique (player_name, alias_name)) is dropped, not duplicated.
DELETE FROM player_aliases a USING player_aliases b
 WHERE a.id <> b.id
   AND (a.player_name ~ E' ' OR a.player_name LIKE '%  %' OR a.alias_name ~ E' ' OR a.alias_name LIKE '%  %')
   AND pg_temp.clean(a.player_name) = b.player_name AND pg_temp.clean(a.alias_name) = b.alias_name;
UPDATE player_aliases SET player_name = pg_temp.clean(player_name), alias_name = pg_temp.clean(alias_name)
 WHERE player_name ~ E' ' OR player_name LIKE '%  %' OR alias_name ~ E' ' OR alias_name LIKE '%  %';
-- An alias that now names the player himself is noise.
DELETE FROM player_aliases WHERE player_name = alias_name;
COMMIT;
