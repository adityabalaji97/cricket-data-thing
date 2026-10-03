*After a 10+ first over, Varun's RAA per over for the rest of the match moves by -0.64 (95% CI -1.87 to +0.55, p = 0.32) vs a 0-6 first over (34 and 69 matches).*

## The claim

A common claim is that Varun Chakravarthy can't recover from an expensive first over, is better used in the middle overs than the powerplay, and suffers when the bowler at the other end leaks runs.

## How we tested it

The definitions, thresholds and minimum samples below were written down and committed before the analysis was run ([pre-registration](https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration/h0_varun_first_over.md)).

Scope (all parts): men's T20, IPL + all T20Is, 2015-01-01 to 2026-10-03. Bowling view.

### H0a — a 10+ first over makes him worse for the rest of the match

* **Unit**: a match in which he bowled at least 2 overs.
* **Exposure**: runs conceded off his first over of the innings (bowler's runs: byes/leg-byes
  excluded), bucketed 0-6 / 7-9 / 10+ (`bowler_first_over_runs_bucket`).
* **Outcome**: RAA per over over his remaining overs in that match
  (`dimension_filters = bowler_over_number:gte:2`), i.e. 6 × Σ RAA / metric balls.
* **Primary effect**: mean(10+) − mean(0-6) of per-match RAA per over. Claimed direction: negative.
  Meaningful effect: −0.5 RAA per over.
* **Tests**: Welch's t-test; bootstrap CI resampling matches within each bucket.
* **Control**: the same effect for five IPL spinners pooled: Yuzvendra Chahal, Rashid Khan,
  Kuldeep Yadav, Ravi Bishnoi, Axar Patel (same scope). Secondary effect: Varun's effect minus the
  peers' pooled effect (bootstrap of matches within player and bucket). Each peer's own effect is
  also reported.
* **Minimum**: 15 matches in each of the 0-6 and 10+ buckets for Varun, else Inconclusive.
* **Context**: economy for the rest of the match per bucket.

### H0b — entry point: powerplay vs middle overs

* **Unit**: a match he bowled in.
* **Exposure**: the over he first bowled (`bowler_entry_over`, 0-indexed): powerplay = 0-5,
  middle = 6-14. Entries at 15+ are reported but not tested.
* **Outcome**: RAA per over across all his overs in the match.
* **Primary effect**: mean(middle entry) − mean(powerplay entry). Claimed direction: positive.
  Meaningful effect: +0.5 RAA per over. Welch + bootstrap over matches. Peers as context.
* **Minimum**: 15 matches in each group, else Inconclusive.

### H0c — pressure from the other end

* **Unit**: one of his overs (bootstrap resamples matches, keeping each match's overs together).
* **Exposure**: runs off the previous over of the innings, bowled from the other end
  (`prev_over_runs_bucket` 0-6 / 7-9 / 10+). Overs with no previous over are excluded.
* **Outcome**: RAA per over of his over (bowling view).
* **Primary effect**: mean(10+) − mean(0-6). Claimed direction: negative. Meaningful: −0.5.
* **Placebo**: the same comparison using the runs off the *next* over (`next_over_runs_bucket`).
  What happens after his over cannot cause it, so a placebo effect of similar size means the
  previous-over pattern is confounding (pitch, batters, phase), not pressure.
* **Verdict**: Supported only if the primary effect is supported AND the placebo effect's CI
  includes zero; if both are significant in the same direction, Not supported (confounded).
* Context: raw economy per bucket; `prev_over_raa_bucket` reported as an exploratory split.
* **Minimum**: 30 overs in each of the 0-6 and 10+ buckets.

## What the numbers say

**Varun's rest-of-match RAA per over by runs off his first over, pooled over all those balls (bowling view; the test compares per-match averages)**

{{chart:first_over}}

**Five IPL spinners pooled: rest-of-match RAA per over by first-over runs (all their balls)**

{{chart:peers}}

**Varun's RAA per over by the over he came on (0 = first over of the innings)**

{{chart:entry}}

**Varun's RAA per over by runs off the previous over from the other end**

{{chart:pressure}}

| Effect | Estimate | 95% CI | p | Test | n |
|---|---|---|---|---|---|
| Varun: rest-of-match RAA/over, 10+ first over minus 0-6 (RAA per over) | -0.64 | -1.87 to +0.55 | 0.32 | Welch t-test | 10+: 34, 0-6: 69 |
| Five IPL spinners pooled: same effect (RAA per over) | -0.65 | -1.10 to -0.20 | < 0.01 | Welch t-test | 10+: 258, 0-6: 531 |
| Varun's effect minus the peers' effect (RAA per over) | +0.01 | -1.30 to +1.33 | 0.99 | bootstrap difference-in-differences | varun matches: 103, peer matches: 789 |
| Varun: match RAA/over, middle-overs entry minus powerplay entry (RAA per over) | -0.28 | -1.16 to +0.57 | 0.53 | Welch t-test | middle: 51, powerplay: 89 |
| Varun: RAA/over of his over, previous over 10+ minus 0-6 (RAA per over) | +0.44 | -0.44 to +1.35 | 0.35 | bootstrap over matches | overs 0-6: 214, overs 7-9: 116, overs 10+: 195 |
| Placebo: same split by the NEXT over's runs (RAA per over) | -0.74 | -1.55 to +0.07 | 0.08 | bootstrap over matches | overs 0-6: 210, overs 7-9: 125, overs 10+: 189 |

## Verdict: Partly

- a. 10+ first over hurts the rest of his match: **Inconclusive**
- b. better entering in the middle overs: **Inconclusive**
- c. hurt by a big over from the other end: **Not supported**

Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.

## Caveats and sample sizes

- Line/length is not used here. RAA is per six balls that carry metrics (wides carry none).
- Matches where he bowled one over have no rest of match and are excluded from part a.
- Peers are pooled by match, so bowlers with more matches weigh more.
- first over matches: 0-6: 69, 7-9: 37, 10+: 34
- Varun's RAA per over by the over he came on (0 = first over of the innings): small sample (<15 innings): 0 (3), 1 (7), 2 (2), 3 (14) +4 more
- Data through 2026-10-03.

## Reproduce this

- [Varun's rest-of-match RAA per over by runs off his first over, pooled over all those balls (bowling view; the test compares per-match averages)](https://hindsightcricket.com/query?bowlers=Varun+Chakaravarthy&leagues=IPL&include_international=true&start_date=2015-01-01&metrics_perspective=bowling&dimension_filters=bowler_over_number%3Agte%3A2&group_by=bowler_first_over_runs_bucket&fmt=mens-t20)
- [Five IPL spinners pooled: rest-of-match RAA per over by first-over runs (all their balls)](https://hindsightcricket.com/query?bowlers=Yuzvendra+Chahal&bowlers=Rashid+Khan&bowlers=Kuldeep+Yadav&bowlers=Ravi+Bishnoi&bowlers=Axar+Patel&leagues=IPL&include_international=true&start_date=2015-01-01&metrics_perspective=bowling&dimension_filters=bowler_over_number%3Agte%3A2&group_by=bowler_first_over_runs_bucket&fmt=mens-t20)
- [Varun's RAA per over by the over he came on (0 = first over of the innings)](https://hindsightcricket.com/query?bowlers=Varun+Chakaravarthy&leagues=IPL&include_international=true&start_date=2015-01-01&metrics_perspective=bowling&group_by=bowler_entry_over&fmt=mens-t20)
- [Varun's RAA per over by runs off the previous over from the other end](https://hindsightcricket.com/query?bowlers=Varun+Chakaravarthy&leagues=IPL&include_international=true&start_date=2015-01-01&metrics_perspective=bowling&group_by=prev_over_runs_bucket&fmt=mens-t20)
- [Placebo: Varun's RAA per over by runs off the NEXT over](https://hindsightcricket.com/query?bowlers=Varun+Chakaravarthy&leagues=IPL&include_international=true&start_date=2015-01-01&metrics_perspective=bowling&group_by=next_over_runs_bucket&fmt=mens-t20)
- Code: `analysis/hypotheses` in the Hindsight repository.

## Credits

- Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).
- Ball-by-ball data before 2015, and recent matches not yet in the main feed: [Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).
- Ball-by-ball data from 2015, including line, length and shot: [2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed].
- Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo](https://twitter.com/hganjoo_153), *T20 Metrics: A Primer*).
- Methodology: Welch t-test, bootstrap difference-in-differences, bootstrap over matches. Confidence intervals are 95% bootstrap percentile intervals (10,000 resamples of matches or innings). Definitions were registered before the analysis was run (analysis/hypotheses/preregistration).
