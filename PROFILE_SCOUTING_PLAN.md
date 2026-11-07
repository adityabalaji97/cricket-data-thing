# Scouting on the player profile

"How to bowl to him" and "How to bat against him", folded into the profile's role cards (7 Nov 2026, agreed with the
user). It's the scouting templates (`services/scouting.py`, the Livingstone and Noor cards) brought to every profile,
upgrading cards we already have instead of duplicating them.

## Principles

- **Same window and scope as the verdict and its cards.** It's part of the same cached call (`/player/{name}/cards`,
  `services/player_cards.py`, `CARDS_VERSION` c2), so every number on the page agrees.
- **Against the player's own baseline, or the average player of his hand in the same window.** Never a bare number.
- **Our data has the bowler's type, not the variation (slower ball, googly) or speed.** The type card says so.
- **Each card hides itself below its sample floor and shows its balls**, as the profile cards already do.

## Batters: the "How to bowl to him" group

| # | Card | Status | What |
|---|---|---|---|
| 1 | Against each bowling type | **upgrade** | Each type's strike rate, plus % against his own ("−36% v his 145"). Retitled "Who to bowl to him". |
| 2 | Where to bowl (pace) | **new** | Pitch map against pace: his strike rate in each line and length against his strike rate v pace. 20+ balls a cell. |
| 3 | Where he scores | **upgrade** | The existing wheel, plus one line: against pace short of full, his share of boundary runs square on the leg side against the average batter of his hand, and **the fielder who matters**. |
| 4 | How he scores | **new** | His main scoring shots, share of runs against the average batter of his hand (the slog share). |

| 5 | How he gets out | **upgrade** (7 Nov 2026) | His dismissals bowled, LBW, caught and stumped against a typical batter out to the same kinds of bowling in the competitions and years he batted (run-outs left out). Repeats year to year (0.34) but isn't tied to his average or strike rate (`scripts/analysis/batter_bowled.py`): how he gets out, not how good he is. 30+ dismissals to compare. Filter: phase, bowling. `services/wicket_style.py` (role="bat"). |

His start stays as it is.

## Bowlers: the "How to bat against him" group

| # | Card | Status | What |
|---|---|---|---|
| 1 | Where he bowls | as is | Economy by line and length (already on the profile) |
| 2 | What works against him | **new** | Batters' strike rate with each shot against him, against their strike rate off him, with balls per wicket, so "it works" is honest |

| 3 | How he takes wickets | **upgrade** (7 Nov 2026) | His wickets bowled, LBW, caught and stumped against a typical bowler of his type in the competitions and years he bowled in (LBWs run 4-8.5% of wickets by competition), plus how often he attacks the stumps (on the stumps, full or good length or yorker) against typical. A style, not a rating: it repeats year to year but doesn't predict economy (`scripts/analysis/stumps_attack.py`). 20+ wickets to compare, 300+ tagged balls for the stumps line. Filter: phase, batter's hand. `services/wicket_style.py`. |

Phases and hands stay as they are.

## Cost

- **Batters:** 4 more grouped queries per player (hand, pace by line and length, boundary zones, shot families).
- **Bowlers:** 1 more.
- **Baselines:** the average batter of each hand, cached once per window and scope, shared by every profile.
- **Build:** the same one-build-at-a-time slot as today's cards.

## Later

- Per-card share images (an item still pending from earlier).
- The scouting post template stays separate: `articles/scouting/build.py`.
