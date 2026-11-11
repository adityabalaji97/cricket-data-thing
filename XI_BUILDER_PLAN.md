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

### Stage 1b: realistic fits (agreed 12 Nov 2026, before stage 2)

The first "who fits" cards were right but unrealistic: the best options were stars at other sides (Bumrah, Rabada) no
one can sign. The builder's pool has to be players a side could actually get, judged on all the evidence we hold.

| # | Chunk | Output |
|---|---|---|
| X4a | **The profile, not the stars.** Each gap card opens with what fits: playoff sides' level on the role's measure plus two style markers (death pace: economy, dot %, yorker share; powerplay pace: wickets, dot %, swing lengths; middle spin: wickets, economy, false shots), "like Bumrah, Harshit Rana". The "at other sides" list goes; the names become examples in the profile line. | card change |
| X4c | **The available pool.** Unsold at the 2026 auction, released on 17 Nov (squad_moves), and the auction register when published (early Dec; a loader like the auction files'). Each candidate's role numbers from **every** T20 we hold (IPL, SMAT, other leagues, T20Is), not only the IPL. | `services/fit.py` pool |
| X4d | **Expected IPL numbers.** League factors from players who played the same role in both a league and the IPL within two seasons (SMAT → IPL, SA20 → IPL, ...): the typical change in economy, strike rate, wickets per 4 overs. A candidate's expected IPL number = his record there × the factor, shrunk by sample, with a range. **Backtest** on 2023–26 debuts/returns: does the expected number beat "the league average for the role" at predicting the next IPL season? Only factors that pass are used. | `services/league_factors.py`, `scripts/analysis/league_factor_check.py`, findings |
| X4e | **Style twins as potential (gated).** For a candidate with under 150 IPL balls in the role: his nearest style twins (services/twins.py, style kind) among proven role holders; their numbers as a "plays like" signal. **Test first:** for players with small IPL samples, do their style twins' numbers predict their next IPL season better than their own small sample (and better than X4d)? Shown only if it passes, labelled "unproven, bowls like ...". | `scripts/analysis/style_potential_check.py`, findings; card list if it passes |
| X4f | **The cards again.** Per gap: the profile line; "In the auction pool" ranked by expected IPL number (IPL record where it's enough, else the league-adjusted one, its source and range shown: "SMAT 2025: 7.4 an over, ~8.5 expected in the IPL"); "plays like" if X4e passed. Phone screenshots. The same pool feeds stage 2. | `TeamSquad.jsx` |

### Stage 2: the builder, 17 Nov – 16 Dec

| # | Chunk | Output |
|---|---|---|
| X5 | **Engine.** Slots per league, a pool with role values per player, limits (purse, overseas, squad size), score, best-possible XI, "plays most like" (nearest real squad by role profile). Pure functions, mirrored in JS from one spec with shared test vectors. | `services/xi_engine.py`, `src/utils/xiEngine.js` |
| X6 | **Fix my team.** On the team page: tap a slot, see who fits, swap, the score and template rows move; purse and overseas counters; over-purse state blocks Save / Share (rule 1). | builder screen, phone screenshots |
| X7 | **Save and share.** A short link and an image: the XI, the score, roles at playoff level, "plays most like KKR 2024". | share card, `/xi/<id>` |
| X8 | **Retention and auction days.** 17 Nov: retained / released states, purse left, the pool becomes real. 16 Dec: buys appear with prices; "how close was your XI to what they built". | loaders, a results post |

### Stage 2b: the XI tab (agreed 12 Nov 2026)

The squad view grades each role by the squad's busiest holders, and a batter counts in one batting role only (his usual
slot), so adding Will Jacks to MI didn't move the 5-7 row. The XI tab scores an actual team instead:

- **Twelve players:** a batting order 1-11 and an impact sub who comes in for a named player (he bats and the other
  bowls, or the reverse), as the real rule works; the batting and bowling elevens follow from that.
- **Batting roles from the order:** openers = slots 1-2, top order = 3-4, middle and finishers = 5-7. Each player's
  number in a role is his record at those slots if he has 60+ balls there, else his overall batting, flagged "out of
  his usual role".
- **Bowling from history:** the 20 overs (6 powerplay, 9 middle, 5 death; 4 a bowler) go to the bowling eleven by
  where each has bowled most; shown on screen, tap a bowler to change his phase. Each phase's role (powerplay pace,
  middle-overs spin, death pace) is the overs-weighted record of whoever bowls it (his phase record if 60+ balls there,
  else his overall bowling, flagged); no spinner in the middle overs is a gap.
- **Depth:** regular bowlers in the bowling eleven.
- **Overseas:** at most four in the twelve (warned, and Save off, as with the purse).
- **Two tabs:** Squad (the 25 and the purse, as now) and XI (twelve from that squad). The Season Draft (X10) scores its
  XI with the same function.

| # | Chunk | Output |
|---|---|---|
| X6b | Payload: each player's batting by slot group and bowling by phase and kind (not just his main role) | `services/xi_engine.py` |
| X6c | `scoreXI()` in the browser (order, sub, auto overs, flags) with tests; the Python mirror when an XI is shared | `src/utils/xiEngine.js` |
| X6d | The XI tab: the default XI from the squad, reorder, sub, bowling allocation, the template rows live | `XIBuilderPage.jsx` |

### Stage 3: the other modes

| # | Chunk | Output |
|---|---|---|
| X9 | **Pick your India XI.** Slots from India's recent XIs (who played each role), contenders from data (caps in 24 months + the top few by role in the IPL and domestic T20s, on measures that repeat), the case for and against each (the retention posts' `case()`), a "what moved" log after each match (feeds PITCH_BRIEF_PLAN.md P3c). Needs an international template (top-10 sides). User signs off contenders, measures and wording on a one-slot mockup first. | `services/india_xi.py`, page group on `/team?team=India` |
| X10 | **Season Draft: "made the playoffs in N of 19".** Three player-season cards dealt per slot (the deal is the constraint; a salary cap was ruled out on 11 Nov 2026: before 2018 only 8–55 of a season's 130–170 players have an auction price). Every player-season rated as a percentile within its own season on its slot's measures, so eras compare. The XI is placed among each of the 19 seasons' real sides on the same percentiles: the reveal is a strip of all 19 seasons (made the playoffs / missed / would have topped the table), the best XI from the same deal, and where each pick's real team finished. Wording (user, 11 Nov 2026): the game's score may say "made the playoffs in N of 19" as a game rule, with a one-line "how scoring works" (out-ranking that season's playoff sides on the template). X2 found no predictive power, so the wording stays in the game; analysis pages and posts never present it as a prediction. Same deal for everyone each day; share card "14/19". | `/games/season-draft` |
| X11 | **Other leagues.** A template per league (season ledger → roles → benchmarks, as for the IPL), then the same modes. | per-league pinned templates |

## Risks

- **The score fails X2.** Then the builder shows template rows only, with no headline number, until a better score
  exists. X2 comes before any builder work for this reason.
- **Numbers at one side don't transfer to another.** Stated on the screen: "on his IPL 2024–26, at any side".
- **Thin samples surface flukes** (Akash Singh's 109 balls): floors and shrinkage in X4, small-sample flags kept.
- **Scope.** Stage 1 is useful alone and feeds posts; stages 2 and 3 only start if stage 1 gets used.
