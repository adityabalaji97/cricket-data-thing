-- Migration 034: results of the first two New Zealand v India T20Is (Oct 2026). The ball-by-ball feed caught both
-- mid-match and never finished them (1539432: NZ's innings, 118 balls; 1539433: 103 balls), so they were loaded with
-- no winner. Results from the ESPNcricinfo scorecards: India won both by 4 wickets (NZ 225/4, India 230/6 in 19.4;
-- NZ 180/5, India 181/6 in 19.5). Match records only: the balls stay as the feed has them until it (or Cricsheet)
-- completes them.

BEGIN;
UPDATE matches SET winner = 'India', outcome = '{"winner": "India", "by": {"wickets": 4}}'::json
WHERE id IN ('1539432', '1539433') AND winner IS NULL;
COMMIT;
