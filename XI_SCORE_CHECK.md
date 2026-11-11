# XI Builder X2: does a squad score predict the season? (11 Nov 2026)

`scripts/analysis/xi_score_check.py`. Every IPL season 2015-26 (106 side-seasons): each side's core (its 16 most-used
players) graded on their IPL numbers in the three seasons before, against the season's win rate and playoffs. The
winners' template was fitted on 2023-26, so 2015-22 is the out-of-sample test. Within each season (so eras don't mix):

| Score's top four: made the playoffs | 2015-22 (held out) | 2023-26 (fitted) |
|---|---|---|
| Template grade (weighted fit) | 13/32 (41%) | 10/16 (62%) |
| Roles at playoff level | 15/32 (47%) | 9/16 (56%) |
| Pre-season Elo (benchmark) | 18/32 (56%) | 5/16 (31%) |

Chance is about 50% (4 of 8; 4 of 10 from 2022). Rank correlation with win rate, within seasons: grade −0.16 / +0.05,
roles −0.26 / −0.01, Elo +0.23 / −0.12. Scoring everyone a side used made it worse (−0.21 to −0.30): losing sides
churn players, and more players fill more roles.

**Verdict:** the grade describes a squad; it does not predict its season (and nothing pre-season does much better: Elo
is near chance too). Decisions for XI_BUILDER_PLAN.md:
- No playoff predictions anywhere ("would make the playoffs", "squads like this made it N times in 10").
- The team page and builder show roles against what playoff sides had, as description, with no headline score.
- Season Draft's "N of 19" is a comparison, not a prediction: "out-ranks that season's playoff sides on the template
  in N of 19 seasons".
- The earlier squad_review backtest (projected runs) also failed to order a table (services/squad_review.py note).
