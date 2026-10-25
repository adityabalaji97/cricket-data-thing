-- Migration 035 (25 Oct 2026).
--
-- 1. A no-ball that also went for byes or leg-byes: the ball-by-ball feed stores the ball's runs as the no-ball alone
--    (score 1) and the batter's as score minus every extra (1 - 1 - 4 = -4), so the batter loses the byes and the
--    ball loses them too. 365 deliveries in 355 matches, 2016-2026 (Rohit Sharma 4 short in Pune 2017, Suryakumar
--    Yadav in Hyderabad 2024, Hardik Pandya in Bristol 2018, against ESPNcricinfo and Cricsheet). A batter scores
--    nothing off byes or leg-byes: batruns 0, and the ball's runs are its extras. sync_from_delivery_details /
--    load pipeline: see services/delivery_fixes.py for the guard on future loads.
-- 2. The toss in India's two wins over Afghanistan added in 033 (ESPNcricinfo scorecards): India won it and fielded in
--    Gros Islet 2010; Afghanistan won it and fielded in Colombo 2012.

BEGIN;

UPDATE delivery_details
SET batruns = 0,
    score = COALESCE(noball, 0) + COALESCE(wide, 0) + COALESCE(byes, 0) + COALESCE(legbyes, 0)
WHERE batruns < 0;

UPDATE matches SET toss_winner = 'India', toss_decision = 'field', win_toss_win_match = TRUE WHERE id = '412679';
UPDATE matches SET toss_winner = 'Afghanistan', toss_decision = 'field', win_toss_win_match = FALSE WHERE id = '533274';

COMMIT;
