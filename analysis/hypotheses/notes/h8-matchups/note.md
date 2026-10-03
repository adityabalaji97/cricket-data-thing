*Leg-spin to left-handers: -5.90 (95% CI -8.29 to -3.69, p < 0.01) RAA per 100 balls vs the same bowlers to right-handers; left-arm pace to right-handers in the powerplay: +0.76 (95% CI -1.57 to +3.21, p = 0.52).*

## The claim

A common claim is that bowling matchups (leg-spin to left-handers, left-arm pace to right-handers in the powerplay) are overrated.

## How we tested it

The definitions, thresholds and minimum samples below were written down and committed before the analysis was run ([pre-registration](https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration/h8_matchups.md)).

* **Scope**: men's T20, 2015-01-01 to 2026-10-03. Bowling view.
* **Matchup A**: leg-spinners (`bowl_style` LB, LBG) bowling to left-handed batters, vs the same
  bowlers to right-handers. All overs.
* **Matchup B**: left-arm pace (`bowl_style` LF, LFM, LMF, LM) bowling to right-handed batters in
  the powerplay (overs 1-6, 0-indexed 0-5), vs the same bowlers to left-handers in the powerplay.
* **Unit**: a bowler with at least 120 balls to each hand in the matchup's scope. Within-bowler
  difference in RAA per 100 balls (matchup hand − other hand), averaged across bowlers weighted by
  the bowler's smaller ball count. Bootstrap over bowlers.
* **Claim "overrated"**: each matchup's effect lies within an **equivalence band of ±3 RAA per
  100 balls** (about 0.18 runs per over, or 0.7 runs across a four-over spell).
* **Verdict per matchup**: Supported (overrated) if the CI lies within ±3; Not supported if the CI
  excludes zero in the matchup's favour (positive); "Not supported — the matchup backfires" if it
  excludes zero negatively; else Inconclusive. Overall: Partly if the two matchups differ.
* **Context**: raw economy by hand; WAA per 100 by hand.
* **Minimum**: 10 qualifying bowlers per matchup.

## What the numbers say

**Leg-spin to left-handers: RAA per 100 balls by batter's hand (bowling view)**

{{chart:A_pooled}}

**Left-arm pace to right-handers, powerplay: RAA per 100 balls by batter's hand (bowling view)**

{{chart:B_pooled}}

**Leg-spin to left-handers: each bowler by batter's hand (120+ balls)**

{{chart:A_bowlers}}

**Left-arm pace to right-handers, powerplay: each bowler by batter's hand (120+ balls)**

{{chart:B_bowlers}}

| Effect | Estimate | 95% CI | p | Test | n |
|---|---|---|---|---|---|
| leg-spin to left-handers: within-bowler RAA per 100 balls, matchup hand minus other hand | -5.9 | -8.3 to -3.7 | < 0.01 | weighted mean of within-bowler differences, bootstrap over bowlers | bowlers: 94 |
| left-arm pace to right-handers, powerplay: within-bowler RAA per 100 balls, matchup hand minus other hand | +0.8 | -1.6 to +3.2 | 0.52 | weighted mean of within-bowler differences, bootstrap over bowlers | bowlers: 87 |

## Verdict: Partly

- A. leg-spin to left-handers: **Not supported — the matchup backfires**
- B. left-arm pace to right-handers, powerplay: **Inconclusive**

Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.

## Caveats and sample sizes

- Balls to each hand come from the overs captains chose; a bowler kept away from a hand faces it in different situations. RAA adjusts for game state, not for that selection.
- 'Overrated' is tested as an equivalence band of +/-3 RAA per 100 balls.
- A: 25
- B: 25
- Data through 2026-10-03.

## Reproduce this

- [Leg-spin to left-handers: RAA per 100 balls by batter's hand (bowling view)](https://hindsightcricket.com/query?bowl_style=LB&bowl_style=LBG&metrics_perspective=bowling&start_date=2015-01-01&group_by=bat_hand&fmt=mens-t20)
- [Left-arm pace to right-handers, powerplay: RAA per 100 balls by batter's hand (bowling view)](https://hindsightcricket.com/query?bowl_style=LF&bowl_style=LFM&bowl_style=LMF&bowl_style=LM&metrics_perspective=bowling&over_min=0&over_max=5&start_date=2015-01-01&group_by=bat_hand&fmt=mens-t20)
- [Leg-spin to left-handers: each bowler by batter's hand (120+ balls)](https://hindsightcricket.com/query?bowl_style=LB&bowl_style=LBG&metrics_perspective=bowling&start_date=2015-01-01&min_balls=120&group_by=bowler&group_by=bat_hand&fmt=mens-t20)
- [Left-arm pace to right-handers, powerplay: each bowler by batter's hand (120+ balls)](https://hindsightcricket.com/query?bowl_style=LF&bowl_style=LFM&bowl_style=LMF&bowl_style=LM&metrics_perspective=bowling&over_min=0&over_max=5&start_date=2015-01-01&min_balls=120&group_by=bowler&group_by=bat_hand&fmt=mens-t20)
- Code: `analysis/hypotheses` in the Hindsight repository.

## Credits

- Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).
- Ball-by-ball data before 2015, and recent matches not yet in the main feed: [Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).
- Ball-by-ball data from 2015, including line, length and shot: [2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed].
- Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo](https://twitter.com/hganjoo_153), *T20 Metrics: A Primer*).
- Methodology: weighted mean of within-bowler differences, bootstrap over bowlers. Confidence intervals are 95% bootstrap percentile intervals (10,000 resamples of matches or innings). Definitions were registered before the analysis was run (analysis/hypotheses/preregistration).
