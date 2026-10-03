*Bumrah ranks 3 of 170 death bowlers on leverage-weighted RAA (+26.5 per 100 balls); he ranks first in 7% of bootstrap resamples.*

## The claim

A common claim is that Jasprit Bumrah is the best death bowler in T20 cricket.

## How we tested it

The definitions, thresholds and minimum samples below were written down and committed before the analysis was run ([pre-registration](https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration/h6_bumrah_death.md)).

* **Scope**: men's T20, all competitions with Primer metrics, 2015-01-01 to 2026-10-03; death overs
  = overs 16-20 (0-indexed 15-19). Bowling view.
* **Population**: every bowler with at least 600 death-over balls (100 overs).
* **Primary metric**: leverage-weighted RAA per 100 balls (`raa_lw_per_100`). Secondary: WPA per
  100 balls, RAA per 100, WAA per 100; raw economy as context.
* **Primary effect**: Bumrah's `raa_lw_per_100` minus the next-best bowler's. Claimed direction:
  positive (Bumrah ranked first).
* **Uncertainty**: bootstrap over matches for every bowler in the population (resampling each
  bowler's matches); report the CI of the gap and the share of resamples in which Bumrah ranks
  first.
* **Verdict**: Supported if Bumrah ranks first and the gap CI excludes zero; Partly if he ranks
  first but the gap CI includes zero, or ranks 2nd-3rd with overlapping CIs; Not supported if he
  ranks below 3rd or the leader's gap CI over him excludes zero.

## What the numbers say

**Death overs (16-20) since 2015, 600+ balls: leverage-weighted RAA per 100 balls (bowling view)**

{{chart:lw_raa}}

**Death overs since 2015, 600+ balls: win probability added (total)**

{{chart:wpa}}

**Bumrah at the death by year: leverage-weighted RAA per 100 balls**

{{chart:bumrah_year}}

| Effect | Estimate | 95% CI | p | Test | n |
|---|---|---|---|---|---|
| Bumrah's leverage-weighted death RAA per 100 minus the best other bowler's (RAA per 100 balls (leverage-weighted)) | -4.2 | -30.5 to +3.6 | n/a | bootstrap over each bowler's matches (gap to the best other bowler in each replicate) | bowlers: 170, bumrah matches: 209 |

## Verdict: Partly

Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.

## Caveats and sample sizes

- All men's T20 competitions with Primer metrics since 2015 (The Hundred excluded by the metrics).
- Leverage-weighted RAA weights each ball by how much was at stake on it.
- qualifying bowlers: 170
- Bumrah at the death by year: leverage-weighted RAA per 100 balls: small sample (<15 innings): 2015 (4), 2023 (2)
- Data through 2026-10-03.

## Reproduce this

- [Death overs (16-20) since 2015, 600+ balls: leverage-weighted RAA per 100 balls (bowling view)](https://hindsightcricket.com/query?min_balls=600&over_min=15&over_max=19&start_date=2015-01-01&group_by=bowler&fmt=mens-t20)
- [Death overs since 2015, 600+ balls: win probability added (total)](https://hindsightcricket.com/query?min_balls=600&over_min=15&over_max=19&start_date=2015-01-01&group_by=bowler&fmt=mens-t20)
- [Bumrah at the death by year: leverage-weighted RAA per 100 balls](https://hindsightcricket.com/query?bowlers=Jasprit+Bumrah&over_min=15&over_max=19&start_date=2015-01-01&group_by=year&fmt=mens-t20)
- Code: `analysis/hypotheses` in the Hindsight repository.

## Credits

- Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).
- Ball-by-ball data before 2015, and recent matches not yet in the main feed: [Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).
- Ball-by-ball data from 2015, including line, length and shot: [2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed].
- Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo](https://twitter.com/hganjoo_153), *T20 Metrics: A Primer*).
- Methodology: bootstrap over each bowler's matches (gap to the best other bowler in each replicate). Confidence intervals are 95% bootstrap percentile intervals (10,000 resamples of matches or innings). Definitions were registered before the analysis was run (analysis/hypotheses/preregistration).
