*IPL scoring rose from 8.31 to 9.50 runs per over; after netting out BBL, PSL and CPL over the same seasons the Impact Player era adds +0.66 (95% CI +0.37 to +0.96, p < 0.01) runs per over.*

## The claim

A common claim is that the Impact Player rule, introduced in IPL 2023, inflated IPL scoring.

## How we tested it

The definitions, thresholds and minimum samples below were written down and committed before the analysis was run ([pre-registration](https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration/h1_impact_player.md)).

* **Design**: difference-in-differences. Treated: IPL. Controls (no Impact Player rule): BBL, PSL,
  CPL. Periods by season start year: pre = 2020-2022 seasons, post = 2023-2026 seasons
  (BBL 2022/23 counts as pre). SA20 began in 2023 and has no pre period: shown descriptively,
  not in the DiD.
* **Unit**: a team innings (`query_mode=team_innings`), innings 1 and 2, scheduled at full length
  (`full_length:eq:1`). Bootstrap resamples matches (both innings together), within league-period.
* **Outcomes**:
  1. Runs per over (primary).
  2. Runs per over in the powerplay, middle and death overs.
  3. Boundary % and dot % of legal balls.
  4. Share of innings reaching 200+ and 250+ (first innings only for these two).
* **Primary effect**: (IPL post − IPL pre) − (controls post − controls pre) in runs per over, the
  controls pooled innings-weighted. Claimed direction: positive. Meaningful: +0.3 runs per over.
* **Game-state adjustment**: the outcome is raw scoring by design (the claim is about scoring
  levels); the control leagues absorb the global trend. RAA is not used here because its
  expectation is fit across leagues and seasons and would partly absorb the shift being measured.
* **Sensitivity** (reported, not used for the verdict): pre = 2022 only (the first full home IPL
  after two seasons partly in the UAE).
* **Caveat stated in advance**: other things changed in 2023 (e.g. bigger squads' batting depth,
  balls, playing conditions); DiD attributes to the rule any IPL-specific change in 2023.
* **Minimum**: 100 innings per league-period cell.

## What the numbers say

**IPL runs per over by season (full-length innings)**

{{chart:ipl_rr}}

**Runs per over before and after 2023: IPL vs leagues without the rule**

{{chart:leagues}}

**IPL first innings reaching 200, by season (%)**

{{chart:ipl_200}}

**Runs per over by phase, IPL and control leagues, before and after 2023**

{{chart:phases}}

| Effect | Estimate | 95% CI | p | Test | n |
|---|---|---|---|---|---|
| DiD: runs per over | +0.66 | +0.37 to +0.96 | < 0.01 | bootstrap difference-in-differences (matches) | IPL 2023-26 innings: 570, IPL 2020-22 innings: 388, BBL/PSL/CPL 2023-26 innings: 753, BBL/PSL/CPL 2020-22 innings: 707 |
| DiD: powerplay runs per over | +0.88 | +0.49 to +1.26 | < 0.01 | bootstrap difference-in-differences (matches) | IPL 2023-26 innings: 570, IPL 2020-22 innings: 388, BBL/PSL/CPL 2023-26 innings: 753, BBL/PSL/CPL 2020-22 innings: 707 |
| DiD: middle-overs runs per over | +0.70 | +0.35 to +1.05 | < 0.01 | bootstrap difference-in-differences (matches) | IPL 2023-26 innings: 570, IPL 2020-22 innings: 388, BBL/PSL/CPL 2023-26 innings: 753, BBL/PSL/CPL 2020-22 innings: 707 |
| DiD: death runs per over | +0.27 | -0.25 to +0.79 | 0.31 | bootstrap difference-in-differences (matches) | IPL 2023-26 innings: 570, IPL 2020-22 innings: 388, BBL/PSL/CPL 2023-26 innings: 753, BBL/PSL/CPL 2020-22 innings: 707 |
| DiD: boundary % of balls | +2.11 | +1.14 to +3.07 | < 0.01 | bootstrap difference-in-differences (matches) | IPL 2023-26 innings: 570, IPL 2020-22 innings: 388, BBL/PSL/CPL 2023-26 innings: 753, BBL/PSL/CPL 2020-22 innings: 707 |
| DiD: dot % of balls | -2.50 | -3.89 to -1.14 | < 0.01 | bootstrap difference-in-differences (matches) | IPL 2023-26 innings: 570, IPL 2020-22 innings: 388, BBL/PSL/CPL 2023-26 innings: 753, BBL/PSL/CPL 2020-22 innings: 707 |
| DiD: first innings 200+ (%) | +17.23 | +8.06 to +26.23 | < 0.01 | bootstrap difference-in-differences (matches) | IPL 2023-26 innings: 570, IPL 2020-22 innings: 388, BBL/PSL/CPL 2023-26 innings: 753, BBL/PSL/CPL 2020-22 innings: 707 |
| DiD: first innings 250+ (%) | +3.83 | +0.98 to +6.86 | < 0.01 | bootstrap difference-in-differences (matches) | IPL 2023-26 innings: 570, IPL 2020-22 innings: 388, BBL/PSL/CPL 2023-26 innings: 753, BBL/PSL/CPL 2020-22 innings: 707 |
| DiD: runs per over (pre = 2022 only) | +0.48 | +0.09 to +0.87 | 0.01 | bootstrap difference-in-differences (matches) | IPL 2023-26 innings: 570, IPL 2020-22 innings: 148, BBL/PSL/CPL 2023-26 innings: 753, BBL/PSL/CPL 2020-22 innings: 237 |

## Verdict: Supported

Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.

## Caveats and sample sizes

- Difference-in-differences attributes to the rule every IPL-specific change from 2023 (squads, conditions, balls, strategy), not only the extra batter.
- IPL 2020 and part of 2021 were played in the UAE; the 2022-only sensitivity check addresses that.
- SA20 started in 2023, so it has no before period and is shown for context only.
- innings: 2665
- Data through 2026-10-03.

## Reproduce this

- [IPL runs per over by season (full-length innings)](https://hindsightcricket.com/query?query_mode=team_innings&start_date=2019-07-01&dimension_filters=full_length%3Aeq%3A1&dimension_filters=season_start_year%3Agte%3A2020&leagues=IPL&group_by=season&fmt=mens-t20)
- [Runs per over before and after 2023: IPL vs leagues without the rule](https://hindsightcricket.com/query?query_mode=team_innings&start_date=2019-07-01&dimension_filters=full_length%3Aeq%3A1&dimension_filters=season_start_year%3Agte%3A2020&leagues=IPL&leagues=BBL&leagues=PSL&leagues=CPL&group_by=competition&group_by=impact_player_era&fmt=mens-t20)
- [IPL first innings reaching 200, by season (%)](https://hindsightcricket.com/query?query_mode=team_innings&start_date=2019-07-01&dimension_filters=full_length%3Aeq%3A1&dimension_filters=season_start_year%3Agte%3A2020&leagues=IPL&innings=1&group_by=season&fmt=mens-t20)
- [Runs per over by phase, IPL and control leagues, before and after 2023](https://hindsightcricket.com/query?query_mode=team_innings&start_date=2019-07-01&dimension_filters=full_length%3Aeq%3A1&dimension_filters=season_start_year%3Agte%3A2020&leagues=IPL&leagues=BBL&leagues=PSL&leagues=CPL&group_by=impact_player_era&group_by=competition&fmt=mens-t20)
- Code: `analysis/hypotheses` in the Hindsight repository.

## Credits

- Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).
- Ball-by-ball data before 2015, and recent matches not yet in the main feed: [Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).
- Ball-by-ball data from 2015, including line, length and shot: [2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed].
- Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo](https://twitter.com/hganjoo_153), *T20 Metrics: A Primer*).
- Methodology: bootstrap difference-in-differences (matches). Confidence intervals are 95% bootstrap percentile intervals (10,000 resamples of matches or innings). Definitions were registered before the analysis was run (analysis/hypotheses/preregistration).
