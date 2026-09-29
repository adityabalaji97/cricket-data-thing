-- Feed spelling changes split a player's record. player_aliases maps every stored spelling to
-- one canonical name (alias_name); the query builder's ALIAS_MAP_CTE and
-- services.player_aliases.expand_name_group read it.
--
-- Vaibhav Sooryavanshi: delivery_details has "Vaibhav Suryavanshi" (216 balls, Apr-Nov 2025) and
-- "Vaibhav Sooryavanshi" (471 balls, May 2025-Jul 2026); the legacy tables have "V Suryavanshi".
-- The alias only linked the legacy name to the older spelling. Canonical = the current spelling.
-- Found with scripts/find_name_variants.py. Idempotent.

BEGIN;

UPDATE player_aliases
SET alias_name = 'Vaibhav Sooryavanshi'
WHERE player_name = 'V Suryavanshi' AND alias_name = 'Vaibhav Suryavanshi';

INSERT INTO player_aliases (player_name, alias_name, source)
SELECT 'Vaibhav Suryavanshi', 'Vaibhav Sooryavanshi', 'spelling_variant'
WHERE NOT EXISTS (
    SELECT 1 FROM player_aliases WHERE player_name = 'Vaibhav Suryavanshi' AND alias_name = 'Vaibhav Sooryavanshi'
);

COMMIT;
