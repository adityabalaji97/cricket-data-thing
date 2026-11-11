# XI Builder X4d: league-strength factors (12 Nov 2026)

`scripts/analysis/league_factor_check.py [fit_to_year]`. Factors per competition and measure from players who did the
same role elsewhere and then in the IPL; tested on IPL newcomers (under 120 balls in the role in the two IPL seasons
before) predicting their next IPL season, mean absolute error weighted by IPL balls, every prediction shrunk to the IPL
average the same way.

Fitted to 2022, tested 2023–26:

| Measure | n | IPL average | Raw record elsewhere | Adjusted |
|---|---|---|---|---|
| Batting strike rate | 46 | 24.3 | **22.2** | 24.9 |
| Batting average | 46 | **8.6** | 10.6 | 9.7 |
| Death pace economy | 20 | **1.06** | 1.20 | (no factor) |
| Powerplay pace economy | 22 | **1.15** | 1.40 | 1.18 |
| Powerplay pace wickets / 4 ov | 22 | 0.32 | 0.36 | 0.32 |
| Middle spin economy | 12 | **0.81** | 1.04 | 0.85 |
| Middle spin wickets / 4 ov | 12 | 0.32 | 0.31 | 0.29 |

Fitted to 2024 and tested on 2025–26 the samples are 4–18 and the picture is the same.

**Verdict:** for a player new to the IPL, the IPL average for his role predicts his season as well as or better than
his record elsewhere, raw or adjusted; batting strike rate is the one place the raw record helps. No "expected IPL"
numbers on the cards. The auction pool's records elsewhere stay as evidence, labelled, not as a forecast.

**Data issue found:** the Syed Mushtaq Ali Trophy is stored under four competition names in delivery_details ("SMAT",
"SMA TROPHY", "SMA TROPHY FINAL", "Syed Mushtaq Ali Trophy"), which split its pairs below the 15 a factor needs.
Worth canonicalising for the query builder and the profiles regardless.

**For X4e (style twins as potential):** given that a player's own record elsewhere doesn't beat the IPL average, a
style match is unlikely to; the test is still the right gate if we want "plays like" on the cards.
