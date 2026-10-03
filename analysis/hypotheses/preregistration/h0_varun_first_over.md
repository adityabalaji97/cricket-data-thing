# H0 — Varun Chakravarthy: first over, entry point, pressure from the other end

Common claim: when Varun Chakravarthy is hit in his first over he does not recover; he is better
used in the middle overs than the powerplay; and he suffers when the bowler at the other end
leaks runs.

Scope (all parts): men's T20, IPL + all T20Is, 2015-01-01 to 2026-10-03. Bowling view.

## H0a — a 10+ first over makes him worse for the rest of the match

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

## H0b — entry point: powerplay vs middle overs

* **Unit**: a match he bowled in.
* **Exposure**: the over he first bowled (`bowler_entry_over`, 0-indexed): powerplay = 0-5,
  middle = 6-14. Entries at 15+ are reported but not tested.
* **Outcome**: RAA per over across all his overs in the match.
* **Primary effect**: mean(middle entry) − mean(powerplay entry). Claimed direction: positive.
  Meaningful effect: +0.5 RAA per over. Welch + bootstrap over matches. Peers as context.
* **Minimum**: 15 matches in each group, else Inconclusive.

## H0c — pressure from the other end

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
