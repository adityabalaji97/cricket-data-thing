# Season Draft (game)

Build an XI from random player-seasons ("Kohli 2016", "Iyer 2025"), graded against what IPL playoff sides actually
had. Agreed with the user, 10 Nov 2026. It teaches the winners' template by playing it, and gives a shareable result.

## How a game goes

1. **Eleven picks, one per slot:** 2 openers, 2 top order (3–4), 3 middle and finishers (5–7, one a keeper), 2 pace,
   2 spin. At most 4 overseas.
2. **Each pick: three cards dealt for that slot.** A card is a player-season: name, year, team colour and the two
   numbers that matter for the slot (average and strike rate; wickets per four overs and economy). Pick one; the
   other two are gone.
3. **The reveal.** The XI is graded role by role against the template (`services/squad_grade.py`): a score out of
   100 and "5 of 7 roles at playoff level". Then the hindsight twist: the best XI you could have built from the same
   deal, and where each of your picks' real team finished that season.
4. **Share.** A card with the XI, the score and the day's number; same deal for everyone that day, so scores compare
   ("better than 62% of today's drafts").

## Why it should work

- The grading already exists and is data-backed (TEAM_TEMPLATE_PLAN.md, T4).
- Player-season roles already exist per league and season (`services/team_roles.py`, T1).
- The daily-puzzle framework exists (`services/daily_games.py`, `/games`).
- Every card links to the player's profile for that season: the game is a door into the site.

## Chunks

| # | Chunk | Output |
|---|---|---|
| D0 | **Does the grade mean anything?** Grade every real IPL squad 2008–26 with the same scoring and compare with where they finished (seasons the template wasn't fitted on held out). If the score doesn't separate playoff sides from the rest, fix the scoring before building. | `scripts/analysis/draft_grade_check.py`, a findings note |
| D1 | **The card pool.** IPL player-seasons with enough balls for a slot (floors per slot), their slot, overseas flag, the two display numbers; famous seasons weighted up so deals feel recognisable; no player twice in a deal. | `services/season_draft.py` pool + tests |
| D2 | **Deal and grade.** A seeded deal per day (11 slots × 3 cards); grade an XI; the best possible XI from a deal (33 cards: exhaustive per slot is cheap); overseas cap enforced. | deal(), grade(), best() + tests |
| D3 | **Endpoints.** `/games/season-draft/daily`, `/grade` (stores anonymous scores for the percentile). | routes |
| D4 | **The game screen.** Phone first: one slot at a time, three cards, tap to pick, the XI filling in as a team sheet; the reveal; the share card image. | `SeasonDraftGame.jsx`, phone screenshots |
| D5 | **Launch content.** A Reel of one draft; the daily "best XI from today's deal" as a post; link from player profiles ("this season is in today's draft"). | |

## Open

- All-rounders: a player-season could fill a batting and a bowling slot; v1 keeps one slot per card.
- Before 2015 there is no Impact, but the template's measures (average, strike rate, wickets, economy) exist for
  every season, so the full IPL history is playable.
- Other pools later: T20Is ("India 2007–26"), a single franchise's history.
