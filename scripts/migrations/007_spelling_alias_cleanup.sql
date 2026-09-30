-- The nightly delivery_details load re-inserted feed aliases that point legacy names at a
-- spelling already linked to a main name (e.g. 'V Suryavanshi' -> 'Vaibhav Suryavanshi', 30 Sep
-- 2026). That gives the legacy name two aliases, the unambiguous-alias map drops it, and the
-- player splits again. The loader now maps such aliases to the main name
-- (scripts/update_players_from_new_data.py); this removes the rows it already added, which each
-- duplicate a legacy -> main-name row from migration 006. Idempotent.

BEGIN;

DELETE FROM player_aliases a
USING player_aliases v
WHERE v.player_name = a.alias_name
  AND v.source = 'spelling_variant'
  AND COALESCE(a.source, '') <> 'spelling_variant'
  AND EXISTS (
      SELECT 1 FROM player_aliases m
      WHERE m.player_name = a.player_name AND m.alias_name = v.alias_name
  );

-- Any such alias without a main-name twin is repointed instead of dropped.
UPDATE player_aliases a
SET alias_name = v.alias_name
FROM player_aliases v
WHERE v.player_name = a.alias_name
  AND v.source = 'spelling_variant'
  AND COALESCE(a.source, '') <> 'spelling_variant';

COMMIT;
