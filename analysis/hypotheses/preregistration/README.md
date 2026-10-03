# Pre-registration: shared rules

Written and committed **before** any of these analyses were run. The git history of this folder
is the record: definitions, thresholds and minimum samples are not changed after results are seen.
If a definition turns out to be unworkable (e.g. a value that does not exist in the data), the
change is made in a separate, dated commit that says why, and the note reports both versions.

## Data

* Hindsight database, men's T20, ball-by-ball `delivery_details` (2015 onward) with the T20 Primer
  metrics in `ball_metrics`. Snapshot date for every analysis: **data through 2026-10-03**.
* Queries go through the query-builder engine (`services.query_builder_v2.run_deliveries_query`),
  so every chart has a query-builder link that reproduces it.
* Player names are canonical (`player_alias_map`); any spelling resolves.

## Metrics

* **Primary**: game-state-adjusted metrics from the T20 Primer method: RAA and WAA (runs and
  wickets above average for the game state), Impact, WPA (win probability added); leverage-weighted
  RAA (`raa_lw_per_100` = 100 × Σ(RAA × leverage) / Σ leverage) where stakes matter.
* Signs: bowling questions use the bowling view (+ = good for the bowler), batting questions the
  batting view (+ = good for the batter). Every chart and table says which.
* **Context**: raw economy / strike rate / boundary % / dot % next to the adjusted numbers.
* "Per over" = per 6 balls that carry metrics (wides carry none, as in the Primer).

## Statistics

* Effect sizes with **95% confidence intervals from a bootstrap**: 10,000 resamples, seed
  20261003, resampling the unit of analysis named in each hypothesis (matches or innings, i.e.
  clustered, never individual balls), percentile intervals.
* **p-values**: Welch's t-test for differences in means; Fisher's exact test or a two-proportion
  z-test for rates (stated per hypothesis); bootstrap p for difference-in-differences.
* No multiple-comparison correction is applied across hypotheses; within a hypothesis, secondary
  splits are labelled exploratory.

## Verdicts (applied mechanically)

Each hypothesis states the claimed direction and a **meaningful effect** (the smallest effect worth
calling real). With the 95% CI of the primary effect:

* **Supported**: the CI excludes zero in the claimed direction, and minimum samples are met.
* **Not supported**: the CI excludes zero in the opposite direction, or the CI lies entirely
  short of the meaningful effect (evidence the effect is absent or small).
* **Inconclusive**: the CI includes zero and also includes the meaningful effect, or a minimum
  sample is not met.
* **Partly**: multi-part hypotheses where parts get different verdicts (each part is reported).

For claims that something does *not* matter (H7, H8), "Supported" means the CI lies inside the
stated equivalence band; "Not supported" means it excludes zero; otherwise "Inconclusive".

## Samples

* Any bucket with **fewer than 15 matches** (or innings, for innings-level units) is flagged on its
  chart as a small sample. Minimums below which a comparison is not tested are stated per
  hypothesis.

## Framing

Hypotheses are presented as "a common claim is…". No private individuals are named.
