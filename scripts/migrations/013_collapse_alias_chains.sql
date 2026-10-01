-- Collapse alias chains: A -> X where X itself maps on (X -> Y) becomes A -> Y.
--
-- The alias map's rule is that a canonical name maps to itself, so a chain splits one player:
-- "MJ Owen" -> "Mitchell Owen" plus "Mitchell Owen" -> "Mitch Owen" left the feed's "Mitchell Owen"
-- (all of his 1,512 local balls) canonical in his own right, apart from the roster's "Mitch Owen";
-- likewise "Raj<NBSP>Bawa" (the feed spelling) vs "Raj Angad Bawa". Both chains came from
-- audit_roster_names.py --fix inserting a roster alias onto a name that was already canonical;
-- that script now resolves chains when it inserts.
--
-- Generic, so it fixes any chain production has: run until nothing changes (chains here are one
-- hop deep; the two passes cover two). Idempotent.

BEGIN;

DO $$
DECLARE
    pass INT;
BEGIN
    FOR pass IN 1..2 LOOP
        -- A -> X with X -> Y, where A -> Y already exists: the A -> X row is redundant.
        DELETE FROM player_aliases c
        USING player_aliases p
        WHERE p.player_name = c.alias_name
          AND p.alias_name <> c.alias_name
          AND EXISTS (SELECT 1 FROM player_aliases d
                      WHERE d.player_name = c.player_name AND d.alias_name = p.alias_name);

        -- Remaining A -> X with X -> Y: repoint to A -> Y.
        UPDATE player_aliases c
        SET alias_name = p.alias_name
        FROM player_aliases p
        WHERE p.player_name = c.alias_name
          AND p.alias_name <> c.alias_name
          AND c.player_name <> p.alias_name;
    END LOOP;
END $$;

COMMIT;

REFRESH MATERIALIZED VIEW CONCURRENTLY player_alias_unambiguous;
REFRESH MATERIALIZED VIEW CONCURRENTLY player_alias_map;
