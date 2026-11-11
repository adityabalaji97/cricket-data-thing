# XI Builder: one team-construction engine, three modes

Agreed with the user, 11 Nov 2026. It folds three earlier plans (the squad section on team pages, the living India
XI, the Season Draft game) into one: they are the same thing with different player pools. A T20 team-construction
game that starts with the IPL and is built to apply to any league.

## The idea

A team page shows a squad, its gaps against what winning sides have, and **who would fill them**. From there the
reader can swap players in and out, slot by slot, and watch the score move. Three modes share one engine:

| Mode | Starts from | Pool | Limits | When |
|---|---|---|---|---|
| **Fix my team** | A real IPL squad (retained players) | Released players, then the auction list | Purse left, overseas cap, squad size | 17 Nov – 16 Dec, then each season |
| **Pick your India XI** | India's current XI, slot by slot | Capped players + contenders by role | Eleven slots, one keeper | After every India match |
| **Season Draft** | Empty XI | Random player-seasons ("Kohli 2016"), three dealt per slot | Overseas cap; same deal for everyone that day | Daily |

## Rules agreed

1. **The purse is a hard limit only to save and share** (as in Fantasy Premier League): build anything, the screen
   shows how far over you are, and Save / Share stay off until it fits.
2. **Slot-based, not squad-based.** A player goes in *instead of* someone in a role ("at the death, instead of
   Avesh"), so every move changes the score. Adding a name to a 25-man list would often change nothing.
3. **No playoff predictions.** X2 (XI_SCORE_CHECK.md, 11 Nov 2026) found the grade doesn't predict a season (no
   better than chance out of sample; Elo barely better). The wording is "roles at playoff level", as description.
4. **No headline score.** Neither candidate predicts (X2), so the seven template rows are the picture: where the squad
   sits on each role against playoff sides. Single
   measures alone (openers on average, spin on wickets) are gameable and noisy: suggestions never rank on one raw
   number.
5. **Suggestions are fit, not verdicts.** "Fills the gap at the death: 8.4 an over across 310 balls" with the sample
   shown; no-blame wording throughout (never "drop X").
6. **Prices are stand-ins until the auction:** last auction price, else base price, labelled as such.
7. **Runs in the browser.** The pool's per-player role values are sent once; scoring is client-side, so play costs
   the two-worker server nothing.
8. **Profile rules** for every card: the title is the name, one picture, one-line note, nothing wraps at 390px.

## Chunks

### Stage 1: the page (read-only), before 17 Nov

| # | Chunk | Output |
|---|---|---|
| X0 | **Squads in the database.** Today they live in the retention post builder (auction CSV + a `TRADES` list). 2026 squads from `auction_lots` plus a `squad_moves` table (player, from, to, price, state: confirmed / reported / retained / released, source, date). One function: a team's squad as of a date. Merge `post/lsg-retention` first. | `services/ipl_squads.py`, migration, tests |
| X1 | **One build, two outputs.** Lift `build()` out of `articles/ipl-retention/post.py` into a service the post and the page both call. | `services/squad_view.py` |
| X2 | **Does the score mean anything?** Score every real IPL squad 2008–26 two ways (the template grade, `services/squad_grade.py`; projected runs, `services/squad_review.py`) and compare with where they finished, holding out seasons the template was fitted on. Pick the headline score; decide whether rule 3's sentence is allowed. | `scripts/analysis/xi_score_check.py`, findings note |
| X3 | **Squad cards on the team page.** Squad board, against the winners' template, price v wins added, three calls; "as of" and each move's status in the note. Fixes "top players" to the current squad (Boult for RR). | `GET /team-squad`, `TeamPage.jsx` |
| X4 | **Who fits.** For each role short of playoff level: the best available players for it, ranked on shrunk, repeatable measures, with samples; before 17 Nov the pool is "players at other sides" (labelled), after it the released list. Each list is also a post. | `services/fit.py`, a card per gap |

### Stage 2: the builder, 17 Nov – 16 Dec

| # | Chunk | Output |
|---|---|---|
| X5 | **Engine.** Slots per league, a pool with role values per player, limits (purse, overseas, squad size), score, best-possible XI, "plays most like" (nearest real squad by role profile). Pure functions, mirrored in JS from one spec with shared test vectors. | `services/xi_engine.py`, `src/utils/xiEngine.js` |
| X6 | **Fix my team.** On the team page: tap a slot, see who fits, swap, the score and template rows move; purse and overseas counters; over-purse state blocks Save / Share (rule 1). | builder screen, phone screenshots |
| X7 | **Save and share.** A short link and an image: the XI, the score, roles at playoff level, "plays most like KKR 2024". | share card, `/xi/<id>` |
| X8 | **Retention and auction days.** 17 Nov: retained / released states, purse left, the pool becomes real. 16 Dec: buys appear with prices; "how close was your XI to what they built". | loaders, a results post |

### Stage 3: the other modes

| # | Chunk | Output |
|---|---|---|
| X9 | **Pick your India XI.** Slots from India's recent XIs (who played each role), contenders from data (caps in 24 months + the top few by role in the IPL and domestic T20s, on measures that repeat), the case for and against each (the retention posts' `case()`), a "what moved" log after each match (feeds PITCH_BRIEF_PLAN.md P3c). Needs an international template (top-10 sides). User signs off contenders, measures and wording on a one-slot mockup first. | `services/india_xi.py`, page group on `/team?team=India` |
| X10 | **Season Draft.** A card pool of IPL player-seasons (floors per slot, famous seasons weighted up), a seeded daily deal (11 slots × 3 cards), the reveal (best XI from the same deal, where each pick's real team finished), percentile against the day's drafts. | `/games/season-draft` |
| X11 | **Other leagues.** A template per league (season ledger → roles → benchmarks, as for the IPL), then the same modes. | per-league pinned templates |

## Risks

- **The score fails X2.** Then the builder shows template rows only, with no headline number, until a better score
  exists. X2 comes before any builder work for this reason.
- **Numbers at one side don't transfer to another.** Stated on the screen: "on his IPL 2024–26, at any side".
- **Thin samples surface flukes** (Akash Singh's 109 balls): floors and shrinkage in X4, small-sample flags kept.
- **Scope.** Stage 1 is useful alone and feeds posts; stages 2 and 3 only start if stage 1 gets used.
