# H6 — Jasprit Bumrah is the best death bowler

Common claim: Jasprit Bumrah is the best death-overs bowler in T20 cricket.

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
