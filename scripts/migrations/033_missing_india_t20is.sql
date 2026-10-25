-- Migration 033: four India men's T20Is missing from matches (296 against ESPNcricinfo's 300, checked 25 Oct 2026 by
-- year). Two were abandoned after the toss (ESPNcricinfo counts those as no-results; abandoned before a toss isn't a
-- match, e.g. Dharamsala 2019, so it stays out), and two India wins over Afghanistan at World Twenty20s. No
-- ball-by-ball for any of them (abandoned, or before 2015): match records only, from the ESPNcricinfo scorecards;
-- toss only where the scorecard gives it. data_source 'manual'.

BEGIN;

INSERT INTO matches (id, date, venue, city, event_name, event_match_number, team1, team2, toss_winner, toss_decision,
                     winner, outcome, player_of_match, overs, balls_per_over, bat_first, bowl_first,
                     won_batting_first, won_fielding_first, match_type, competition, format, gender, data_source)
VALUES
  -- India v Scotland, 7th match, Group D, Kingsmead, 13 Sep 2007: no result (abandoned with a toss). Scorecard 287859.
  ('287859', '2007-09-13', 'Kingsmead, Durban', 'Durban', 'ICC World Twenty20', 7, 'India', 'Scotland',
   'Scotland', 'field', NULL, '{"result": "no result"}', NULL, 20, 6, NULL, NULL, NULL, NULL,
   'international', 'T20I', 'T20', 'male', 'manual'),
  -- Afghanistan v India, 3rd match, Group C, Gros Islet, 1 May 2010: India won by 7 wickets (Afghanistan 115/8, India
  -- 116/3 in 14.5 overs). Scorecard 412679.
  ('412679', '2010-05-01', 'Beausejour Stadium, Gros Islet', 'St Lucia', 'ICC World Twenty20', 3, 'Afghanistan', 'India',
   NULL, NULL, 'India', '{"winner": "India", "by": {"wickets": 7}}', 'Ashish Nehra', 20, 6, 'Afghanistan', 'India',
   FALSE, TRUE, 'international', 'T20I', 'T20', 'male', 'manual'),
  -- Afghanistan v India, 3rd match, Group A, Colombo, 19 Sep 2012: India won by 23 runs (India 159/5, Afghanistan 136).
  -- Scorecard 533274.
  ('533274', '2012-09-19', 'R.Premadasa Stadium, Khettarama, Colombo', 'Colombo', 'ICC World Twenty20', 3, 'Afghanistan',
   'India', NULL, NULL, 'India', '{"winner": "India", "by": {"runs": 23}}', NULL, 20, 6, 'India', 'Afghanistan',
   TRUE, FALSE, 'international', 'T20I', 'T20', 'male', 'manual'),
  -- India v Sri Lanka, 1st T20I, Guwahati, 5 Jan 2020: no result (abandoned with a toss). Scorecard 1202242.
  ('1202242', '2020-01-05', 'Barsapara Cricket Stadium, Guwahati', 'Guwahati', 'Sri Lanka tour of India', 1, 'India',
   'Sri Lanka', 'India', 'field', NULL, '{"result": "no result"}', NULL, 20, 6, NULL, NULL, NULL, NULL,
   'international', 'T20I', 'T20', 'male', 'manual')
ON CONFLICT (id) DO NOTHING;

COMMIT;
