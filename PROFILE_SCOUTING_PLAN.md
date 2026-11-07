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

His start and how he gets out stay as they are.

## Bowlers: the "How to bat against him" group

| # | Card | Status | What |
|---|---|---|---|
| 1 | Where he bowls | as is | Economy by line and length (already on the profile) |
| 2 | What works against him | **new** | Batters' strike rate with each shot against him, against their strike rate off him, with balls per wicket, so "it works" is honest |

Phases, hands and wickets stay as they are.

## Cost

- **Batters:** 4 more grouped queries per player (hand, pace by line and length, boundary zones, shot families).
- **Bowlers:** 1 more.
- **Baselines:** the average batter of each hand, cached once per window and scope, shared by every profile.
- **Build:** the same one-build-at-a-time slot as today's cards.

## Later

- Per-card share images (an item still pending from earlier).
- The scouting post template stays separate: `articles/scouting/build.py`.
