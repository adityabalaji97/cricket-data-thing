# H8 — Matchups are overrated

Common claim: bowling "matchups" — e.g. leg-spin to left-handers, left-arm pace to right-handers
in the powerplay — do not make bowlers more effective.

* **Scope**: men's T20, 2015-01-01 to 2026-10-03. Bowling view.
* **Matchup A**: leg-spinners (`bowl_style` LB, LBG) bowling to left-handed batters, vs the same
  bowlers to right-handers. All overs.
* **Matchup B**: left-arm pace (`bowl_style` LF, LFM, LMF, LM) bowling to right-handed batters in
  the powerplay (overs 1-6, 0-indexed 0-5), vs the same bowlers to left-handers in the powerplay.
* **Unit**: a bowler with at least 120 balls to each hand in the matchup's scope. Within-bowler
  difference in RAA per 100 balls (matchup hand − other hand), averaged across bowlers weighted by
  the bowler's smaller ball count. Bootstrap over bowlers.
* **Claim "overrated"**: each matchup's effect lies within an **equivalence band of ±3 RAA per
  100 balls** (about 0.18 runs per over, or 0.7 runs across a four-over spell).
* **Verdict per matchup**: Supported (overrated) if the CI lies within ±3; Not supported if the CI
  excludes zero in the matchup's favour (positive); "Not supported — the matchup backfires" if it
  excludes zero negatively; else Inconclusive. Overall: Partly if the two matchups differ.
* **Context**: raw economy by hand; WAA per 100 by hand.
* **Minimum**: 10 qualifying bowlers per matchup.
