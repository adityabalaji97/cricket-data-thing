*A sub-110 30-ball innings vs a 150+ one: the WPA gap changed by +0.044 (95% CI +0.014 to +0.076, p < 0.01) per innings between 2015-19 and 2023-26.*

## The claim

A common claim is that the anchor is dead: a long, slow innings used to be useful in T20 and now loses games.

## How we tested it

The definitions, thresholds and minimum samples below were written down and committed before the analysis was run ([pre-registration](https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration/h5_anchor_dead.md)).

* **Scope**: men's T20, IPL and T20Is between the top 10 teams. Periods: 2015-01-01 to 2019-12-31
  and 2023-01-01 to 2026-10-03.
* **Unit**: a batting innings of 30+ balls faced (`batter_balls_faced:gte:30`), counting the whole
  innings.
* **Strike-rate buckets** (innings strike rate): under 110, 110-129.99, 130-149.99, 150+.
* **Outcomes**: the batting team's result (win % among decided matches) and the batter's WPA
  per innings (batting view).
* **Primary effect**: change between periods in the WPA per innings of the under-110 bucket
  relative to the 150+ bucket: (slow − fast) in 2023-26 minus (slow − fast) in 2015-19. Claimed
  direction: negative. Meaningful: −0.03 WPA per innings. Bootstrap over innings.
* **Secondary**: the same contrast in team win %.
* Context: share of 30+ ball innings that fall under 110 in each period.
* **Minimum**: 30 innings per bucket-period cell; cells under 15 are flagged.

## What the numbers say

**Innings of 30+ balls by strike rate, 2015-19: team result and WPA (batting view)**

{{chart:result_2015-19}}

**Innings of 30+ balls by strike rate, 2023-26: team result and WPA (batting view)**

{{chart:result_2023-26}}

**Innings of 30+ balls, 2023-26: Impact per 100 balls by strike-rate band**

{{chart:impact_2023}}

| Effect | Estimate | 95% CI | p | Test | n |
|---|---|---|---|---|---|
| Slow (<110) minus fast (150+) 30-ball innings, WPA per innings: 2023-26 minus 2015-19 | +0.044 | +0.014 to +0.076 | < 0.01 | bootstrap difference-in-differences (innings) | 2023-26 under 110: 98, 2023-26 150+: 639, 2015-19 under 110: 184, 2015-19 150+: 440 |
| Same contrast in team win % (percentage points) | -0.4 | -14.0 to +13.5 | 0.96 | bootstrap difference-in-differences (innings) | 2023-26 under 110: 98, 2023-26 150+: 639, 2015-19 under 110: 184, 2015-19 150+: 440 |

## Verdict: Not supported

Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.

## Caveats and sample sizes

- A slow innings is often a response to early wickets; WPA credits the batter only for what happened on his balls, but team result also reflects the collapse around him.
- T20Is restricted to matches between the top 10 teams.
- innings: 2015-19 under 110: 184, 2015-19 110-129: 253, 2015-19 130-149: 290, 2015-19 150+: 440, 2023-26 under 110: 98, 2023-26 110-129: 170, 2023-26 130-149: 237, 2023-26 150+: 639
- Innings of 30+ balls by strike rate, 2015-19: team result and WPA (batting view): small sample (<15 innings): under 110 / no_result (2), under 110 / tie (1), 110-129 / tie (3), 110-129 / no_result (1) +1 more
- Innings of 30+ balls by strike rate, 2023-26: team result and WPA (batting view): small sample (<15 innings): under 110 / tie (2), under 110 / no_result (1), 110-129 / no_result (3), 110-129 / tie (3) +2 more
- Data through 2026-10-03.

## Reproduce this

- [Innings of 30+ balls by strike rate, 2015-19: team result and WPA (batting view)](https://hindsightcricket.com/query?dimension_filters=batter_balls_faced%3Agte%3A30&start_date=2015-01-01&end_date=2019-12-31&leagues=IPL&include_international=true&top_teams=10&group_by=batter_innings_strike_rate_bucket&group_by=match_outcome&fmt=mens-t20)
- [Innings of 30+ balls by strike rate, 2023-26: team result and WPA (batting view)](https://hindsightcricket.com/query?dimension_filters=batter_balls_faced%3Agte%3A30&start_date=2023-01-01&end_date=2026-10-03&leagues=IPL&include_international=true&top_teams=10&group_by=batter_innings_strike_rate_bucket&group_by=match_outcome&fmt=mens-t20)
- [Innings of 30+ balls, 2023-26: Impact per 100 balls by strike-rate band](https://hindsightcricket.com/query?dimension_filters=batter_balls_faced%3Agte%3A30&start_date=2023-01-01&end_date=2026-10-03&leagues=IPL&include_international=true&top_teams=10&group_by=batter_innings_strike_rate_bucket&fmt=mens-t20)
- Code: `analysis/hypotheses` in the Hindsight repository.

## Credits

- Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).
- Ball-by-ball data before 2015, and recent matches not yet in the main feed: [Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).
- Ball-by-ball data from 2015, including line, length and shot: [2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed].
- Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo](https://twitter.com/hganjoo_153), *T20 Metrics: A Primer*).
- Methodology: bootstrap difference-in-differences (innings). Confidence intervals are 95% bootstrap percentile intervals (10,000 resamples of matches or innings). Definitions were registered before the analysis was run (analysis/hypotheses/preregistration).
