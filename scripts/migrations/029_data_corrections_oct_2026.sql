-- Data corrections found 22-23 Oct 2026 (RECORD_RADAR_PLAN.md chunk 0). Idempotent; re-run after a full reload.
--
-- 1. Namibia A's games in Kenya (Jul 2025) were stored as T20Is. A sides don't have T20I status; labelled like the
--    other A-side tours ("Pakistan A v England Lions unofficial T20I Series"), so they leave every T20I count and
--    stay in all men's T20s.
UPDATE matches SET competition = 'Namibia A in Kenya (unofficial T20Is)', event_name = 'Namibia A in Kenya (unofficial T20Is)'
WHERE id IN ('1494104', '1494107', '1494112', '1494117') AND competition = 'T20I';
UPDATE delivery_details SET competition = 'Namibia A in Kenya (unofficial T20Is)'
WHERE p_match IN ('1494104', '1494107', '1494112', '1494117') AND competition = 'T20I';
--
-- 2. Known bad source data, not corrected: Bhutan v Bahrain, 8 Dec 2025 (1513098). The feed's balls mix both sides'
--    players under each innings' batting side. Player numbers are right (players are counted by id); that match's
--    team totals are not. Fix by re-importing it from Cricsheet if it ever matters.
