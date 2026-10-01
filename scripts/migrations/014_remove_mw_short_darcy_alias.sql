-- Remove a wrong alias row: 'MW Short' -> 'D''Arcy Short'.
--
-- MW Short is Matthew (William) Short; D'Arcy Short's legacy name is 'DJM Short'. The wrong row made
-- 'MW Short' ambiguous (it also maps to 'Matthew Short'), and ambiguous legacy names are left
-- unmerged, so Matthew Short's legacy innings under that name stayed split from his record.
-- Matched by name, not id, so it applies to any database. Idempotent.

BEGIN;
DELETE FROM player_aliases WHERE player_name = 'MW Short' AND alias_name = 'D''Arcy Short';
COMMIT;

REFRESH MATERIALIZED VIEW CONCURRENTLY player_alias_unambiguous;
REFRESH MATERIALIZED VIEW CONCURRENTLY player_alias_map;
ANALYZE player_alias_unambiguous;
ANALYZE player_alias_map;
