*Varun's RAA per over in 2025-26 vs earlier: -0.33 (95% CI -1.19 to +0.53, p = 0.45) (57 recent and 83 earlier matches).*

## The claim

A common claim is that batters have figured Varun Chakravarthy out.

## How we tested it

The definitions, thresholds and minimum samples below were written down and committed before the analysis was run ([pre-registration](https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration/h2_varun_figured_out.md)).

* **Scope**: men's T20, IPL + all T20Is, 2015-01-01 to 2026-10-03. Bowling view.
* **Unit**: a match he bowled in. Per-match RAA per over and WAA per over.
* **Primary effect**: mean per-match RAA per over in the 2025 and 2026 seasons minus the mean in
  all earlier seasons. Claimed direction: negative. Meaningful: −0.5 RAA per over.
  Welch + bootstrap over matches.
* **Secondary**: WAA per over, same comparison (meaningful −0.05 wickets per over).
* **Descriptive (charts)**:
  * RAA and WAA per over by season (`season`), and by half-season: within each IPL season, his
    matches split in date order into the first half (first ceil(n/2)) and second half.
  * Split by batter's hand (LHB / RHB).
  * By length and by the batter's shot, where the feed has them (2015+, partial coverage;
    coverage % reported).
  * Dismissal types by period (share of his wickets).
* Trend: OLS slope of per-match RAA per over on match date (per year), reported with bootstrap CI.
* **Minimum**: 15 matches in the recent window and 30 before, else Inconclusive. Half-season
  buckets under 15 matches are flagged on the chart.

## What the numbers say

**Varun's RAA per over by season (bowling view)**

{{chart:season}}

**Varun's RAA per over against left- and right-handers, by season**

{{chart:hand}}

**Varun's RAA per 100 balls by length (balls with length recorded)**

{{chart:length}}

**How Varun's wickets fall (all seasons)**

{{chart:dismissal}}

| Effect | Estimate | 95% CI | p | Test | n |
|---|---|---|---|---|---|
| Varun: per-match RAA/over, 2025-26 minus earlier seasons (RAA per over) | -0.33 | -1.19 to +0.53 | 0.45 | Welch t-test | 2025-26: 57, earlier: 83 |
| Varun: per-match WAA/over, 2025-26 minus earlier (WAA per over) | +0.103 | -0.001 to +0.210 | 0.06 | Welch t-test | 2025-26: 57, earlier: 83 |
| Trend: change in per-match RAA/over per year (RAA per over per year) | -0.14 | -0.34 to +0.07 | n/a | OLS slope, bootstrap over matches | matches: 140 |

## Verdict: Inconclusive

Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.

## Caveats and sample sizes

- Length and shot are recorded for part of the balls only (coverage in samples).
- Seasons mix IPL and T20Is; T20Is cluster around tournaments.
- matches: 140
- coverage percent: length: 99.8
- Varun's RAA per over by season (bowling view): small sample (<15): 2019 (1), 2020 (13), 2022 (11), 2023 (14)
- Varun's RAA per over against left- and right-handers, by season: small sample (<15 innings): 2019 / LHB (1), 2019 / RHB (1), 2020 / RHB (13), 2020 / LHB (13) +4 more
- How Varun's wickets fall (all seasons): small sample (<15 innings): leg before wicket (13), stumped (8), run out (5)
- Data through 2026-10-03.

## Reproduce this

- [Varun's RAA per over by season (bowling view)](https://hindsightcricket.com/query?bowlers=Varun+Chakaravarthy&leagues=IPL&include_international=true&start_date=2015-01-01&metrics_perspective=bowling&group_by=season&fmt=mens-t20)
- [Varun's RAA per over against left- and right-handers, by season](https://hindsightcricket.com/query?bowlers=Varun+Chakaravarthy&leagues=IPL&include_international=true&start_date=2015-01-01&metrics_perspective=bowling&group_by=season&group_by=bat_hand&fmt=mens-t20)
- [Varun's RAA per 100 balls by length (balls with length recorded)](https://hindsightcricket.com/query?bowlers=Varun+Chakaravarthy&leagues=IPL&include_international=true&start_date=2015-01-01&metrics_perspective=bowling&group_by=length&fmt=mens-t20)
- [How Varun's wickets fall (all seasons)](https://hindsightcricket.com/query?bowlers=Varun+Chakaravarthy&leagues=IPL&include_international=true&start_date=2015-01-01&metrics_perspective=bowling&group_by=dismissal&fmt=mens-t20)
- Code: `analysis/hypotheses` in the Hindsight repository.

## Credits

- Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).
- Ball-by-ball data before 2015, and recent matches not yet in the main feed: [Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).
- Ball-by-ball data from 2015, including line, length and shot: [2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed].
- Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo](https://twitter.com/hganjoo_153), *T20 Metrics: A Primer*).
- Methodology: OLS slope, bootstrap over matches, Welch t-test. Confidence intervals are 95% bootstrap percentile intervals (10,000 resamples of matches or innings). Definitions were registered before the analysis was run (analysis/hypotheses/preregistration).
