-- Resolves the pairs 006 left for review (2026-09-30), on the evidence below. Idempotent.
--
-- M Mohammed / Mohammed Mohammed: both Tamil Nadu, RHB, right-arm medium, Syed Mushtaq Ali
--   Trophy, never in the same match. One player; main name "M Mohammed" (219 of 251 balls).
-- Shehan Madusanka (2025-26) / Shehan Madushanka (2018-20): same club (Badureliya), both RHB;
--   Madushanka is the Sri Lanka international and the later rows are his club cricket.
--   Main name "Shehan Madushanka".
-- Ghulam Shabbir / Shabber (UAE): 006 made "Shabber" the main name by recency; "Shabbir" is the
--   usual spelling and holds most of his balls (824 of 1,026), so it becomes the main name.

BEGIN;

INSERT INTO player_aliases (player_name, alias_name, source)
SELECT 'Mohammed Mohammed', 'M Mohammed', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Mohammed Mohammed' AND alias_name = 'M Mohammed');

UPDATE player_aliases SET alias_name = 'Shehan Madushanka' WHERE alias_name = 'Shehan Madusanka';
INSERT INTO player_aliases (player_name, alias_name, source)
SELECT 'Shehan Madusanka', 'Shehan Madushanka', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Shehan Madusanka' AND alias_name = 'Shehan Madushanka');

DELETE FROM player_aliases WHERE player_name = 'Ghulam Shabbir' AND alias_name = 'Ghulam Shabber';
UPDATE player_aliases SET alias_name = 'Ghulam Shabbir' WHERE alias_name = 'Ghulam Shabber';
INSERT INTO player_aliases (player_name, alias_name, source)
SELECT 'Ghulam Shabber', 'Ghulam Shabbir', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Ghulam Shabber' AND alias_name = 'Ghulam Shabbir');

COMMIT;
