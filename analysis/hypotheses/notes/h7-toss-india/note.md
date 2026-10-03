*Toss winners won 177 of 355 decided matches in India (49.9%); the 95% CI for the edge is -5.2 to +4.9 points.*

## The claim

A common claim is that the toss doesn't matter at Indian venues.

## How we tested it

The definitions, thresholds and minimum samples below were written down and committed before the analysis was run ([pre-registration](https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration/h7_toss_india.md)).

* **Scope**: men's T20, IPL and T20Is played in India (`country = India`), 2023-01-01 to
  2026-10-03. Matches with a result (ties and no results excluded).
* **Unit**: a match (team_innings rows, first innings, so each match counts once).
* **Primary effect**: toss winner's win % minus 50. Claim: no effect. **Equivalence band**: ±5
  percentage points. Two-sided exact binomial test; Wilson / bootstrap 95% CI.
* **By venue**: grounds with at least 15 decided matches: toss-winner win %, chase win %, and the
  share of toss winners who chose to field; others grouped as "other venues". Venue-level results
  are exploratory (many comparisons) and flagged as such.
* **Verdict**: Supported if the overall CI lies within 45-55%; Not supported if it excludes 50%;
  otherwise Inconclusive.

## What the numbers say

**Toss winner's win % by venue in India, IPL and T20Is 2023-26 (first-innings row per match)**

{{chart:venues}}

**Bat-first win % by toss decision (India, 2023-26)**

{{chart:decision}}

**Toss winner's win % by season (India)**

{{chart:season}}

| Effect | Estimate | 95% CI | p | Test | n |
|---|---|---|---|---|---|
| Toss winner's win % minus 50 (percentage points) | -0.1 | -5.2 to +4.9 | 1.00 | exact binomial test; bootstrap CI over matches | decided matches: 355 |

## Verdict: Inconclusive

Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.

## Caveats and sample sizes

- Venue-level results are exploratory: many grounds, few matches each.
- 'Doesn't matter' is tested as an equivalence band of +/-5 points around 50%.
- decided matches: 355
- Toss winner's win % by venue in India, IPL and T20Is 2023-26 (first-innings row per match): small sample (<15): Maharashtra Cricket Association Stadium (2), Saurashtra Cricket Association Stadium, Rajkot (2), JSCA International Stadium Complex, Ranchi (1), Punjab Cricket Association IS Bindra Stadium (6), Barsapara Cricket Stadium, Guwahati (10), Himachal Pradesh Cricket Association Stadium (10)
- Data through 2026-10-03.

## Reproduce this

- [Toss winner's win % by venue in India, IPL and T20Is 2023-26 (first-innings row per match)](https://hindsightcricket.com/query?query_mode=team_innings&leagues=IPL&include_international=true&start_date=2023-01-01&innings=1&dimension_filters=country%3Aeq%3AIndia&group_by=venue&fmt=mens-t20)
- [Bat-first win % by toss decision (India, 2023-26)](https://hindsightcricket.com/query?query_mode=team_innings&leagues=IPL&include_international=true&start_date=2023-01-01&innings=1&dimension_filters=country%3Aeq%3AIndia&group_by=toss_decision&fmt=mens-t20)
- [Toss winner's win % by season (India)](https://hindsightcricket.com/query?query_mode=team_innings&leagues=IPL&include_international=true&start_date=2023-01-01&innings=1&dimension_filters=country%3Aeq%3AIndia&group_by=season&fmt=mens-t20)
- Code: `analysis/hypotheses` in the Hindsight repository.

## Credits

- Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).
- Ball-by-ball data before 2015, and recent matches not yet in the main feed: [Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).
- Ball-by-ball data from 2015, including line, length and shot: [2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed].
- Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo](https://twitter.com/hganjoo_153), *T20 Metrics: A Primer*).
- Methodology: exact binomial test; bootstrap CI over matches. Confidence intervals are 95% bootstrap percentile intervals (10,000 resamples of matches or innings). Definitions were registered before the analysis was run (analysis/hypotheses/preregistration).
