# H1 — The Impact Player rule inflated IPL scoring

Common claim: the Impact Player rule (IPL, from the 2023 season) made IPL scoring jump.

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
