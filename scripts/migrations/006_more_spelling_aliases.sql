-- Link feed spelling variants of the same player (found by scripts/find_name_variants.py:
-- same first name, near-identical surname, same team, never in the same match). Reviewed
-- 2026-09-29: initial-only matches (Rinku Singh / RP Singh etc.) and uncertain pairs
-- (Shehan Madusanka / Madushanka, M Mohammed / Mohammed Mohammed) are deliberately NOT linked.
-- Main name = the full-name spelling, most recent first. Any alias already pointing at the
-- other spelling is repointed to the main name. Idempotent. Reverse: delete rows with
-- source = 'spelling_variant' and restore alias_name from the 'was' comments.

BEGIN;

-- Tharindu Rathnayake -> Tharindu Ratnayake
UPDATE player_aliases SET alias_name = 'Tharindu Ratnayake' WHERE alias_name = 'Tharindu Rathnayake';  -- was Tharindu Rathnayake
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Tharindu Rathnayake', 'Tharindu Ratnayake', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Tharindu Rathnayake' AND alias_name = 'Tharindu Ratnayake');

-- Sachitha Jayathilake -> Sachitha Jayatilake
UPDATE player_aliases SET alias_name = 'Sachitha Jayatilake' WHERE alias_name = 'Sachitha Jayathilake';  -- was Sachitha Jayathilake
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Sachitha Jayathilake', 'Sachitha Jayatilake', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Sachitha Jayathilake' AND alias_name = 'Sachitha Jayatilake');

-- Samay Shrivastav -> Samay Shrivastava
UPDATE player_aliases SET alias_name = 'Samay Shrivastava' WHERE alias_name = 'Samay Shrivastav';  -- was Samay Shrivastav
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Samay Shrivastav', 'Samay Shrivastava', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Samay Shrivastav' AND alias_name = 'Samay Shrivastava');

-- Ghulam Shabbir -> Ghulam Shabber
UPDATE player_aliases SET alias_name = 'Ghulam Shabber' WHERE alias_name = 'Ghulam Shabbir';  -- was Ghulam Shabbir
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Ghulam Shabbir', 'Ghulam Shabber', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Ghulam Shabbir' AND alias_name = 'Ghulam Shabber');

-- Milan Rathnayake -> Milan Rathnayaka
UPDATE player_aliases SET alias_name = 'Milan Rathnayaka' WHERE alias_name = 'Milan Rathnayake';  -- was Milan Rathnayake
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Milan Rathnayake', 'Milan Rathnayaka', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Milan Rathnayake' AND alias_name = 'Milan Rathnayaka');

-- Isitha Wijesundera -> Isitha Wijesundara
UPDATE player_aliases SET alias_name = 'Isitha Wijesundara' WHERE alias_name = 'Isitha Wijesundera';  -- was Isitha Wijesundera
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Isitha Wijesundera', 'Isitha Wijesundara', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Isitha Wijesundera' AND alias_name = 'Isitha Wijesundara');

-- Nipun Dananjaya -> Nipun Dhananjaya
UPDATE player_aliases SET alias_name = 'Nipun Dhananjaya' WHERE alias_name = 'Nipun Dananjaya';  -- was Nipun Dananjaya
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Nipun Dananjaya', 'Nipun Dhananjaya', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Nipun Dananjaya' AND alias_name = 'Nipun Dhananjaya');

-- Nipun Ransika -> Nipun Ranshika
UPDATE player_aliases SET alias_name = 'Nipun Ranshika' WHERE alias_name = 'Nipun Ransika';  -- was Nipun Ransika
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Nipun Ransika', 'Nipun Ranshika', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Nipun Ransika' AND alias_name = 'Nipun Ranshika');

-- Rahul Gunasekera -> Rahul Gunasekara
UPDATE player_aliases SET alias_name = 'Rahul Gunasekara' WHERE alias_name = 'Rahul Gunasekera';  -- was Rahul Gunasekera
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Rahul Gunasekera', 'Rahul Gunasekara', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Rahul Gunasekera' AND alias_name = 'Rahul Gunasekara');

-- Ajeet Dale -> Ajeet Singh Dale
UPDATE player_aliases SET alias_name = 'Ajeet Singh Dale' WHERE alias_name = 'Ajeet Dale';  -- was Ajeet Dale
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Ajeet Dale', 'Ajeet Singh Dale', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Ajeet Dale' AND alias_name = 'Ajeet Singh Dale');

-- Leem Shafeeg -> Leem Shafeeq
UPDATE player_aliases SET alias_name = 'Leem Shafeeq' WHERE alias_name = 'Leem Shafeeg';  -- was Leem Shafeeg
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Leem Shafeeg', 'Leem Shafeeq', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Leem Shafeeg' AND alias_name = 'Leem Shafeeq');

-- Lourenco Solomone -> Lourenco Salomone
UPDATE player_aliases SET alias_name = 'Lourenco Salomone' WHERE alias_name = 'Lourenco Solomone';  -- was Lourenco Solomone
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Lourenco Solomone', 'Lourenco Salomone', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Lourenco Solomone' AND alias_name = 'Lourenco Salomone');

-- Charith Rajapakshe -> Charith Rajapaksa
UPDATE player_aliases SET alias_name = 'Charith Rajapaksa' WHERE alias_name = 'Charith Rajapakshe';  -- was Charith Rajapakshe
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Charith Rajapakshe', 'Charith Rajapaksa', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Charith Rajapakshe' AND alias_name = 'Charith Rajapaksa');

-- Naidoo Krishna -> Naidoo Krishnasamy
UPDATE player_aliases SET alias_name = 'Naidoo Krishnasamy' WHERE alias_name = 'Naidoo Krishna';  -- was Naidoo Krishna
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Naidoo Krishna', 'Naidoo Krishnasamy', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Naidoo Krishna' AND alias_name = 'Naidoo Krishnasamy');

-- Lahiru Dewatage -> Lahiru Dawatage
UPDATE player_aliases SET alias_name = 'Lahiru Dawatage' WHERE alias_name = 'Lahiru Dewatage';  -- was Lahiru Dewatage
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Lahiru Dewatage', 'Lahiru Dawatage', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Lahiru Dewatage' AND alias_name = 'Lahiru Dawatage');

-- Jordan Alegra -> Jordan Alegre
UPDATE player_aliases SET alias_name = 'Jordan Alegre' WHERE alias_name = 'Jordan Alegra';  -- was Jordan Alegra
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Jordan Alegra', 'Jordan Alegre', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Jordan Alegra' AND alias_name = 'Jordan Alegre');

-- Thevindu Senaratne -> Thevindu Senarathne
UPDATE player_aliases SET alias_name = 'Thevindu Senarathne' WHERE alias_name = 'Thevindu Senaratne';  -- was Thevindu Senaratne
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Thevindu Senaratne', 'Thevindu Senarathne', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Thevindu Senaratne' AND alias_name = 'Thevindu Senarathne');

-- Nilanka Premarathna -> Nilanka Premaratne
UPDATE player_aliases SET alias_name = 'Nilanka Premaratne' WHERE alias_name = 'Nilanka Premarathna';  -- was Nilanka Premarathna
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Nilanka Premarathna', 'Nilanka Premaratne', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Nilanka Premarathna' AND alias_name = 'Nilanka Premaratne');

-- Luke Stephen Robinson -> Luke Robinson
UPDATE player_aliases SET alias_name = 'Luke Robinson' WHERE alias_name = 'Luke Stephen Robinson';  -- was Luke Stephen Robinson
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Luke Stephen Robinson', 'Luke Robinson', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Luke Stephen Robinson' AND alias_name = 'Luke Robinson');

-- Ishaan Swaney -> Ishaan Sawney
UPDATE player_aliases SET alias_name = 'Ishaan Sawney' WHERE alias_name = 'Ishaan Swaney';  -- was Ishaan Swaney
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Ishaan Swaney', 'Ishaan Sawney', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Ishaan Swaney' AND alias_name = 'Ishaan Sawney');

-- Davaasuren Jamyansuren -> Davaasuren Jamiyansuren
UPDATE player_aliases SET alias_name = 'Davaasuren Jamiyansuren' WHERE alias_name = 'Davaasuren Jamyansuren';  -- was Davaasuren Jamyansuren
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Davaasuren Jamyansuren', 'Davaasuren Jamiyansuren', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Davaasuren Jamyansuren' AND alias_name = 'Davaasuren Jamiyansuren');

-- Jayant Guatam -> Jayant Gautam
UPDATE player_aliases SET alias_name = 'Jayant Gautam' WHERE alias_name = 'Jayant Guatam';  -- was Jayant Guatam
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Jayant Guatam', 'Jayant Gautam', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Jayant Guatam' AND alias_name = 'Jayant Gautam');

-- Sanjeewan Priyadarshana -> Sanjeewan Priyadharshana
UPDATE player_aliases SET alias_name = 'Sanjeewan Priyadharshana' WHERE alias_name = 'Sanjeewan Priyadarshana';  -- was Sanjeewan Priyadarshana
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Sanjeewan Priyadarshana', 'Sanjeewan Priyadharshana', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Sanjeewan Priyadarshana' AND alias_name = 'Sanjeewan Priyadharshana');

-- S Maleesha -> Shane Maleesha
UPDATE player_aliases SET alias_name = 'Shane Maleesha' WHERE alias_name = 'S Maleesha';  -- was S Maleesha
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'S Maleesha', 'Shane Maleesha', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'S Maleesha' AND alias_name = 'Shane Maleesha');

-- A Aravinddaraj -> Arulprakasam Aravindaraj
UPDATE player_aliases SET alias_name = 'Arulprakasam Aravindaraj' WHERE alias_name = 'A Aravinddaraj';  -- was A Aravinddaraj
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'A Aravinddaraj', 'Arulprakasam Aravindaraj', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'A Aravinddaraj' AND alias_name = 'Arulprakasam Aravindaraj');

-- Nalaka Tenuwara -> Nalaka Thenuwara
UPDATE player_aliases SET alias_name = 'Nalaka Thenuwara' WHERE alias_name = 'Nalaka Tenuwara';  -- was Nalaka Tenuwara
INSERT INTO player_aliases (player_name, alias_name, source) SELECT 'Nalaka Tenuwara', 'Nalaka Thenuwara', 'spelling_variant'
WHERE NOT EXISTS (SELECT 1 FROM player_aliases WHERE player_name = 'Nalaka Tenuwara' AND alias_name = 'Nalaka Thenuwara');

COMMIT;
