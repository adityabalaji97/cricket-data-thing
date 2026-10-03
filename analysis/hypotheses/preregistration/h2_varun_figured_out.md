# H2 — Has Varun Chakravarthy been figured out?

Common claim: batters have worked Varun Chakravarthy out; he is less effective than he was.

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
