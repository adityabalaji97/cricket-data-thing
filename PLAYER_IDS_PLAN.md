# Players by id: plan

Status: **signed off** (22 Oct 2026). Owner: Claude Code / Codex, one chunk per session.

## The problem

Hindsight identifies players by name. Names collide: **148 names belong to more than one player** in the ball-by-ball
data. Rohit Sharma is three players (India 34102, Indonesia 1542004, Haryana 934943); Asif Ali is Pakistan's and
Bahrain's; Rashid Khan, Mohammad Shahzad, Usman Khan, Ross Taylor, Shahid Afridi... Every query, player page, record
and post merges them today. Found 22 Oct 2026: our Rohit Sharma had 101 T20I powerplay sixes, published lists 98; the
3 were Indonesia's Rohit Sharma.

The fix is already in the data: **every ball in delivery_details carries the ESPNcricinfo id** of the batter and the
bowler (`p_bat`, `p_bowl`; 4.2m of 4.2m rows). Only the legacy pre-2015 `deliveries` table has names alone. The record
radar counts by id since PR #179; nothing else does.

## The idea

One table, `player_identity`: ESPNcricinfo id -> display name. Where two ids share a name, the one with the most
balls keeps it and the others carry their main side ("Rohit Sharma (Indonesia)"), as the radar does. Every place that
turns a ball into a player name reads it through one SQL helper; spelling variants (one id, several names) keep going
through the alias map. Pre-2015 balls go by name to the name's main player, as now.

## Chunks

### Chunk 0: the identity table (small)
- Migration: `player_identity (pid PK, display_name UNIQUE, name, main_side, balls, first_date, last_date)`, rebuilt
  nightly from delivery_details (services/record_radar.identities is the logic; move it to services/player_identity.py).
- Indexes on delivery_details (p_bat), (p_bowl): none exist (the Cricsheet loader notes ~3s scans).
- A review list: the namesakes with the most balls, their sides and suffixes, for the user to check once.

### Chunk 1: one helper, every query
- `player_name_sql(id_col, name_col)` -> `COALESCE(pi.display_name, am.canonical_name, name_col)` with the join.
- Replace the 36 `COALESCE(am.canonical_name, ...)` expressions in 15 modules (query builder first).
- Regression goldens (scripts/regression_snapshot.py): the only diffs allowed are namesakes'. Listed, then frozen.

### Chunk 2: stats tables
- batting_stats / bowling_stats / match_players: add the id (from delivery_details per match), read names through it.

### Chunk 3: names in, names out
- Search, find_entities (MCP), NL queries, player URLs: "Rohit Sharma" is the main player; "Rohit Sharma (Indonesia)"
  resolves to his id; a namesake shows a "Did you mean" list.
- Player page header shows the side for namesakes.

### Chunk 4: posts and cards
- Card titles, captions and Reel scripts print display names; a namesake's suffix is shortened on cards where the
  side is obvious (a Bahrain post can say "Asif Ali").

## Risks

- Every query joins one more table: indexed on pid, small (9k rows). Measure the query builder's slowest goldens.
- The indexes on delivery_details: ~200 MB (4.3 GB of 10 GB used after the media cleanup).
- A name change for the minor namesake breaks a saved link to his old name: acceptable, logged.

## Tracker

| Chunk | Status |
|---|---|
| 0 Identity table + indexes | [x] 2026-10-22: migration 026 on production (indexes 28 MB each, built concurrently); 9,791 players, 201 namesakes; rebuilt nightly after the alias refresh (~20s, one bulk insert); the radar reads it |
| 1 One helper, every query | [~] 2026-10-22: query builder (grouping by display name; batters / bowlers / players filters by id, a suffixed name meaning only that namesake, pre-2015 balls to the main player), record ideas (idea_stats), record framings, standout scanner. Kept by name on purpose: scorecards and on-this-day (one match: the side is obvious). Match-ups wait for chunk 2 (XIs are stored by name). Tests 578 pass (3 known legacy failures, as on main); goldens unchanged |
| 2 Stats tables | [ ] |
| 3 Names in, names out | [ ] |
| 4 Posts and cards | [ ] |
