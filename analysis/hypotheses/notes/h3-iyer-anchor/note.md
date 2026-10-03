*In the middle overs Iyer adds +19.0 Impact per 100 balls vs +7.1 for the comparison group: +11.8 (95% CI -7.6 to +29.5, p = 0.22).*

## The claim

A common claim is that Shreyas Iyer anchors rather than accelerates in the middle overs, and struggles against the short ball.

## How we tested it

The definitions, thresholds and minimum samples below were written down and committed before the analysis was run ([pre-registration](https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration/h3_iyer_anchor.md)).

* **Scope**: men's T20, all competitions, 2024-01-01 to 2026-10-03. Batting view.
* **Players**: Shreyas Iyer; comparison group Suryakumar Yadav, Tilak Varma, Rinku Singh.
* **Middle overs**: overs 7-15 (0-indexed 6-14).
* **Unit**: a batting innings (balls in the middle overs of one innings). Bootstrap resamples
  innings.
* **Primary effect**: Iyer's middle-overs Impact per 100 balls minus the comparison group's pooled
  middle-overs Impact per 100 balls. Claimed direction: negative. Meaningful: −5 Impact per 100.
* **Secondary**: the same for strike rate (meaningful −10), separately against pace and against
  spin (exploratory).
* **Short balls**: lengths SHORT and SHORT_OF_A_GOOD_LENGTH (the feed's labels), all overs:
  Iyer's Impact per 100 and strike rate and dismissal rate vs the comparison group. Exploratory,
  as length is recorded for part of the balls only (coverage reported).
* **Verdict**: on the primary effect.
* **Minimum**: 300 middle-overs balls for Iyer and for each comparison player, else that player is
  dropped from the pooled group and the note says so.

## What the numbers say

**Middle overs (7-15), 2024-26: Impact per 100 balls (batting view)**

{{chart:middle_impact}}

**Middle overs (7-15), 2024-26: strike rate**

{{chart:middle_sr}}

**Middle overs vs pace and spin, 2024-26**

{{chart:kind}}

**Against short and short-of-a-length balls, 2024-26 (balls with length recorded)**

{{chart:short}}

| Effect | Estimate | 95% CI | p | Test | n |
|---|---|---|---|---|---|
| Iyer minus peers: middle-overs Impact per 100 balls | +11.8 | -7.6 to +29.5 | 0.22 | bootstrap over innings (ratio estimator) | iyer innings: 45, peer innings: 181 |
| Iyer minus peers: middle-overs strike rate | +13.0 | -1.5 to +27.3 | 0.08 | bootstrap over innings (ratio estimator) | iyer innings: 45, peer innings: 181 |
| Iyer minus peers vs pace: Impact per 100 (exploratory) (Impact per 100 balls) | +12.6 | -15.8 to +37.6 | 0.36 | bootstrap over innings (ratio estimator) | iyer innings: 41, peer innings: 147 |
| Iyer minus peers vs spin: Impact per 100 (exploratory) (Impact per 100 balls) | +12.0 | -10.8 to +34.7 | 0.31 | bootstrap over innings (ratio estimator) | iyer innings: 40, peer innings: 160 |

## Verdict: Inconclusive

Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.

## Caveats and sample sizes

- All men's T20 competitions in the window, so opposition strength differs between players.
- Length is recorded for part of the balls only; short-ball numbers are exploratory.
- middle balls: Shreyas Iyer: 729, Suryakumar Yadav: 1060, Tilak Varma: 1075, Rinku Singh: 385
- Data through 2026-10-03.

## Reproduce this

- [Middle overs (7-15), 2024-26: Impact per 100 balls (batting view)](https://hindsightcricket.com/query?batters=Shreyas+Iyer&batters=Suryakumar+Yadav&batters=Tilak+Varma&batters=Rinku+Singh&start_date=2024-01-01&over_min=6&over_max=14&group_by=batter&fmt=mens-t20)
- [Middle overs (7-15), 2024-26: strike rate](https://hindsightcricket.com/query?batters=Shreyas+Iyer&batters=Suryakumar+Yadav&batters=Tilak+Varma&batters=Rinku+Singh&start_date=2024-01-01&over_min=6&over_max=14&group_by=batter&fmt=mens-t20)
- [Middle overs vs pace and spin, 2024-26](https://hindsightcricket.com/query?batters=Shreyas+Iyer&batters=Suryakumar+Yadav&batters=Tilak+Varma&batters=Rinku+Singh&start_date=2024-01-01&over_min=6&over_max=14&group_by=batter&group_by=bowl_kind&fmt=mens-t20)
- [Against short and short-of-a-length balls, 2024-26 (balls with length recorded)](https://hindsightcricket.com/query?batters=Shreyas+Iyer&batters=Suryakumar+Yadav&batters=Tilak+Varma&batters=Rinku+Singh&start_date=2024-01-01&length=SHORT&length=SHORT_OF_A_GOOD_LENGTH&group_by=batter&fmt=mens-t20)
- Code: `analysis/hypotheses` in the Hindsight repository.

## Credits

- Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).
- Ball-by-ball data before 2015, and recent matches not yet in the main feed: [Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).
- Ball-by-ball data from 2015, including line, length and shot: [2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed].
- Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo](https://twitter.com/hganjoo_153), *T20 Metrics: A Primer*).
- Methodology: bootstrap over innings (ratio estimator). Confidence intervals are 95% bootstrap percentile intervals (10,000 resamples of matches or innings). Definitions were registered before the analysis was run (analysis/hypotheses/preregistration).
