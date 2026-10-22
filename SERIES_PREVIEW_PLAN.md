# Series so far: plan

Status: **signed off** (22 Oct 2026). Owner: Claude Code / Codex, one chunk per session.

## The idea

From the second meeting of two teams on, the preview opens with a debrief of the games so far: where each side won and
lost it, whether each bowled and batted to the conditions (lines, lengths, pace v spin), what worked for the other side
that they could borrow, and what to keep doing or try. Two teams playing each other on the same kind of pitch in the
same week are each other's best evidence; history at the ground is second-hand by comparison.

## Decisions (22 Oct 2026)

1. **Scope: any repeat meeting.** A bilateral series, a tournament rematch, two franchises meeting again in a season.
   "The games so far" = the earlier meetings of the same two teams in the same series/season (event + season).
2. **Keep / try card: shown straight away**, written by fixed rules from the other cards (no review gate).
3. **First live: NZ v India, match 2 (24 Oct, Hagley Oval)**, if match 1's data is in by 23 Oct. Cards that need
   line/length tracking appear when it lands (the story cache is keyed by data load, so it rebuilds itself).

## Rules

- Player and number first ([[content-rules]]): every card title leads with a player or a side and one number.
- No blame ([[no-blame-framing]]): "the length that went for 11 an over", never "X bowled badly". Both ways.
- One game is a small sample: a side bowls ~120 balls. Every cell shows its balls; floors per card (below); words say
  "in game 1". Each side's last-12-months baseline says whether a game was unusual for them or their normal.
- House vocabulary (docs/social_rules.md): Impact, runs above par, win probability added, control %, balls per wicket,
  SR / scores at, lengths, lines, phase names.
- Chart choice ([[chart-choice]]): pitch maps for line/length, the win-probability line for the game, not bars.

## The chapter: "Series so far" (first chapter, only when there's an earlier meeting)

| # | Card | Visual | Data | Floor |
|---|---|---|---|---|
| 1 | **How it turned**: the biggest swings and the top Impact each side ("Samson's 67 (33) added +31% win probability") | win_prob_line with the 2-3 biggest overs marked | ball-by-ball | - |
| 2 | **Phase by phase v par**: each side's powerplay / middle / death runs (and wickets) against par at that ground | dumbbell or phase_diverging | ball-by-ball | - |
| 3 | **Bowling to the conditions**: each side's seamers, where they pitched and what it cost; the cells that worked for the other side outlined | pitch_map pair (pace; spin if enough) | line/length | 6 balls a cell |
| 4 | **Pace v spin**: overs and returns of each, against how the ground usually goes | share_bars + economy | ball-by-ball | - |
| 5 | **Batting to the conditions**: control % and scoring by length, v pace and v spin, each side | pitch_map / metric_bars | line/length | 8 balls |
| 6 | **Used to their strengths?**: each batter's entry (phase, bowling faced) against where his record is strongest; mismatches flagged ("Tilak came in at 3 and faced spin: 6 (11). His record: SR 1xx v pace at the death") | dumbbell (this game v his record) | ball-by-ball + record | 30 balls of record |
| 7 | **Matchups that showed**: batter v bowler from the series worth watching again (dismissals, dominance) | battles | ball-by-ball | - |
| 8 | **Keep / try**: two per side, by rule from 3-6 (below) | text card with chips | derived | - |
| 9 | **New ground?** If the next game moves, how it differs from the last (pace/spin returns, scoring, length profile) so a lesson isn't carried to different conditions | dumbbell (ground A v ground B) | history | ground thinness flag |
| 10 | **Did they adjust?** (game 3 on) each side's length mix and pace/spin share game by game | metric_lines | line/length | - |

### Keep / try rules (card 8)
- **Keep**: a length (bowling) or matchup (batting) that beat the side's own baseline and the game's average, 12+ balls.
- **Try**: the length that worked best for the other side in the same conditions, 12+ balls, that this side used
  under half as often.
- **Usage**: a card-6 mismatch becomes "try: X against pace at the death, where his record is".
- At most two each; ties broken by balls. Worded as options, never verdicts.

## Chunks

### Chunk 1: find the games so far (small)
- `context.series_so_far()`: earlier completed meetings of the two teams with the same event + season (or a tournament
  where they met), with match ids, grounds, results, and whether line/length is present for each.
- Test: NZ v India match 2 finds match 1; a first meeting finds nothing (chapter skipped).

### Chunk 2: ball-by-ball cards (1, 2, 4, 7, 9)
- Reuse win_prob_line, dumbbell, share_bars, battles. Titles from numbers.

### Chunk 3: line/length cards (3, 5, 10)
- Pitch maps per side from delivery_details (p_match / team_bat joins). Graceful skip when tracking hasn't landed.

### Chunk 4: usage and keep/try (6, 8)
- Card 6 needs each batter's record by phase x bowling type (last 2-3 years, all T20s); the mismatch rule.
- Card 8 from 3-6.

### Chunk 5: social
- The match-day post for a repeat meeting leads with the series' player and number, then the lesson. Voiced v2 Reel.

### Chunk 6: data lag
- Measure how long line/length tracking takes to land after a big match (scorecards: same day/next day). Log it per
  match; if it's usually > 2 days, a series preview runs on ball-by-ball cards and says the pitch maps are coming.

## Tracker

| Chunk | Status |
|---|---|
| 1 Games so far | [x] 2026-10-22 (PreviewContext.series_games; bilateral: games ≤14 days apart; leagues: same year) |
| 2 Ball-by-ball cards | [~] 2026-10-22: 1 turn, 2 phases, 4 pace/spin, 9 new ground done; 7 matchups to do |
| 3 Line/length cards | [~] 2026-10-22: 3 bowling pitch maps (one per side), 5 batting control map (the starkest weak spot; feeds keep/try) done; 10 adjustments to do |
| 4 Usage + keep/try | [x] 2026-10-22: 6 usage (batters at 3+, below par last game, 25+ gap); 8 keep/try (keep: 1+ run an over under the series' pace average, 12+ balls; try: the other side's cheap lengths used under half as often, and usage moves) |
| 5 Social | [ ] |
| 6 Data lag | [ ] |
