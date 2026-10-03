# H7 — The toss doesn't matter at Indian venues

Common claim: at Indian grounds, winning the toss makes no real difference to the result.

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
