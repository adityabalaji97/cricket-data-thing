*The three's Impact per innings is 1.36x as spread out as other India openers' (95% CI 1.12-1.63); India win 90% when they fire vs 69% when they fail.*

## The claim

A common claim is that India's T20I openers Sanju Samson, Abhishek Sharma and Ishan Kishan are all or nothing: they either win the game or fail cheaply.

## How we tested it

The definitions, thresholds and minimum samples below were written down and committed before the analysis was run ([pre-registration](https://github.com/adityabalaji97/cricket-data-thing/blob/main/analysis/hypotheses/preregistration/h4_india_openers.md)).

* **Scope**: men's T20Is for India, 2015-01-01 to 2026-10-03; innings where the player batted at
  position 1 or 2 (`batting_position`). Batting view.
* **Unit**: an opening innings. Impact per innings (runs added to the team's projected total).
* **Comparison group**: every other India T20I opener in the same scope with at least 15 opening
  innings.
* **Primary effect ("all or nothing")**: the standard deviation of Impact per innings for the three
  (pooled) divided by the comparison group's. Claimed direction: above 1. Meaningful: 1.2.
  Bootstrap over innings.
* **Also reported**: share of innings with Impact below −5 ("fail") and above +10 ("fire") for each
  player and the comparison group; the full distribution (chart).
* **Win rate when they fail vs fire**: India's result in matches where one of the three opened,
  classed by that player's Impact (fail < −5, fire > +10; ties/no results excluded). Effect:
  win % (fire) − win % (fail), Fisher's exact test, bootstrap CI over innings. Also the player's
  WPA per innings by class.
* **Verdict**: on the primary effect; the win-rate split is context.
* **Minimum**: 15 opening innings per named player to report them individually.

## What the numbers say

**India T20I innings: Impact per innings by batting position (named openers)**

{{chart:impact}}

**Impact per innings for the three, India wins vs losses**

{{chart:result}}

**Win probability added per innings, India T20Is (all positions)**

{{chart:wpa}}

| Effect | Estimate | 95% CI | p | Test | n |
|---|---|---|---|---|---|
| SD ratio (named three / other India openers) | +1.36 | +1.12 to +1.63 | < 0.01 | bootstrap over innings | named innings: 121, comparison innings: 310 |
| Spread of Impact per innings: SD(named) / SD(other openers), log scale (log SD ratio) | +0.31 | +0.11 to +0.49 | < 0.01 | bootstrap over innings |  |
| India win % when the opener fires minus when he fails (percentage points) | +21.6 | +4.7 to +37.5 | 0.03 | Fisher's exact test; bootstrap CI over innings | fire: 31, fail: 48 |

## Verdict: Supported

Verdicts are applied mechanically from the pre-registered rules: *Supported* when the 95% CI excludes zero in the claimed direction; *Not supported* when it excludes zero the other way or rules out an effect of meaningful size; *Inconclusive* otherwise or when a minimum sample is not met.

## Caveats and sample sizes

- Fail = Impact below -5, fire = above +10 runs added to the projected total.
- Batting position is the order of arrival at the crease; position 1-2 = opener.
- A spread measure says nothing about the average; both are shown.
- opening innings: Sanju Samson: 35, Abhishek Sharma: 51, Ishan Kishan: 35
- India T20I innings: Impact per innings by batting position (named openers): small sample (<15 innings): Sanju Samson / 4 (11), Sanju Samson / 5 (8), Sanju Samson / 2 (8), Abhishek Sharma / 3 (7) +2 more
- Impact per innings for the three, India wins vs losses: small sample (<15 innings): Abhishek Sharma / loss (13), Sanju Samson / loss (14), Abhishek Sharma / no_result (3), Sanju Samson / tie (3) +4 more
- Data through 2026-10-03.

## Reproduce this

- [India T20I innings: Impact per innings by batting position (named openers)](https://hindsightcricket.com/query?batters=Sanju+Samson&batters=Abhishek+Sharma&batters=Ishan+Kishan&batting_teams=India&include_international=true&start_date=2015-01-01&group_by=batter&group_by=batting_position&fmt=mens-t20)
- [Impact per innings for the three, India wins vs losses](https://hindsightcricket.com/query?batters=Sanju+Samson&batters=Abhishek+Sharma&batters=Ishan+Kishan&batting_teams=India&include_international=true&start_date=2015-01-01&group_by=batter&group_by=match_outcome&fmt=mens-t20)
- [Win probability added per innings, India T20Is (all positions)](https://hindsightcricket.com/query?batters=Sanju+Samson&batters=Abhishek+Sharma&batters=Ishan+Kishan&batters=Rohit+Sharma&batters=Shubman+Gill&batters=Shikhar+Dhawan&batters=Virat+Kohli&batters=Ruturaj+Gaikwad&batters=KL+Rahul&batting_teams=India&include_international=true&start_date=2015-01-01&group_by=batter&fmt=mens-t20)
- Code: `analysis/hypotheses` in the Hindsight repository.

## Credits

- Data: Hindsight ([hindsightcricket.com](https://hindsightcricket.com)).
- Ball-by-ball data before 2015, and recent matches not yet in the main feed: [Cricsheet](https://cricsheet.org) (Open Data Commons Attribution License, ODC-By 1.0).
- Ball-by-ball data from 2015, including line, length and shot: [2015+ ball-by-ball and line/length/shot feed: provider and licence to be confirmed].
- Advanced metrics: Impact, RAA, WAA, WPA and leverage are computed ball by ball using Himanish Ganjoo's T20 Primer method ([Himanish Ganjoo](https://twitter.com/hganjoo_153), *T20 Metrics: A Primer*).
- Methodology: Fisher's exact test; bootstrap CI over innings, bootstrap over innings. Confidence intervals are 95% bootstrap percentile intervals (10,000 resamples of matches or innings). Definitions were registered before the analysis was run (analysis/hypotheses/preregistration).
