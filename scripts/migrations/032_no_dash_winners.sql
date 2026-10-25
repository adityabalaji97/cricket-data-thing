-- Migration 032: matches loaded from the ball-by-ball feed (data_source 'bbb') with winner '-' (136 T20s, Apr 2015 -
-- Feb 2026): the feed's blank result for a tie, a no-result or a match it caught unfinished. '-' read as a team that
-- won, so anything counting "winner <> team" scored them as defeats (India's 2023 Asian Games final and the Jan 2024
-- double Super Over tie with Afghanistan among them). Winner becomes NULL, as for every other tie or no-result; the
-- derived win columns go with it. services/match_results.py then records each outcome from ESPN; the two India
-- matches are recorded here.

BEGIN;

UPDATE matches
SET winner = NULL, win_toss_win_match = NULL, won_batting_first = NULL, won_fielding_first = NULL,
    winner_match_combo = NULL
WHERE winner IN ('-', '--', '');

-- Afghanistan v India, Asian Games final, Hangzhou, 7 Oct 2023: no result (India gold on seeding).
UPDATE matches SET outcome = '{"result": "no result"}'::json WHERE id = '1399120' AND winner IS NULL;
-- India v Afghanistan, Bengaluru, 17 Jan 2024: tied, India won the second Super Over.
UPDATE matches SET outcome = '{"result": "tie", "eliminator": "India"}'::json WHERE id = '1389398' AND winner IS NULL;

COMMIT;
