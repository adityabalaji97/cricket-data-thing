# The IPL winners' template: first findings (T0–T3)

6 Nov 2026. 19 seasons (2008–2026), 166 team-seasons, 76 playoff sides. Code: `services/season_ledger.py`,
`services/team_roles.py`, `services/role_clusters.py`, `services/team_template.py`.

**How to read it:**
- **Place in season:** every measure is a side's place in its own season, 0 (worst) to 1 (best). That keeps 2008 and 2026
  comparable.
- **Ahead:** the share of seasons in which the playoff sides, on average, beat the rest on that measure. 50% means it
  doesn't separate them; 85%+ means it nearly always does.
- **Values** are the raw averages (playoff sides against the rest) across all seasons.
- **Measures:**
  - Wins added and runs above par exist from 2015 only (12 seasons).
  - Averages count every dismissal, run-outs at the non-striker's end included (#271).

## 1. The ledger (T0)

**Playoff sides and champions:**
- **2008–2025:** taken from Cricsheet's own knockout markings.
- **2026:** inferred as the last four games (our feed doesn't mark stages).
- **Checking:** all 19 were checked game by game. 2026 is confirmed by Olympics.com, Outlook India and Wikipedia: Q1 RCB
  beat GT, Eliminator RR beat SRH, Q2 GT beat RR, Final RCB beat GT.
- **Pinned:** they're in `VERIFIED`, and `ledger()` flags any season that drifts.

## 2. Roles, as the data sees them (T2)

Batting and bowling were clustered separately, over player-seasons with 60+ balls of each.

**Batting**, 6 clusters (silhouette 0.33). On playoff sides 46% of the time on average.

| Cluster | n | On playoff sides | Share of side's balls | Examples |
|---|---|---|---|---|
| Opener, high volume | 197 | **52%** | 20% | Kohli 2016, Buttler 2022, Gill 2023 |
| Opener, low volume | 237 | 39% | 9% | Parthiv 2017, Saha 2023 |
| Top order (3–4) | 365 | 48% | 13% | Williamson 2018, Suryakumar 2025 |
| Finisher (5–7, mostly death overs) | 210 | **51%** | 7% | Rinku 2023, Dhoni 2019, Pollard 2013 |
| Middle order (5–7, mostly middle overs) | 266 | 38% | 9% | Karthik 2018, Miller 2022 |
| Lower order (8+) | 44 | 36% | 5% | |

**Bowling**, 6 clusters (silhouette 0.32):
- **Pace:**
  - Lead pace, powerplay + death: n 291, on playoff sides 48%, 17% of the side's balls (Steyn, Bhuvneshwar, Prasidh).
  - Powerplay-only pace: 43%.
  - All-phase pace: 45% (Bravo, Harshal).
  - Middle-overs pace: 44%.
- **Spin:**
  - Lead middle-overs spinner, 16% of the side's balls: 46% (Harbhajan, Ashwin, Rashid, Varun).
  - Support spinner, 6%: 46%.

**What this says about roles:**
- **The phase × job labels hold up.** The data adds two splits worth keeping: opener volume (an anchor who bats long
  against a short-stay opener), and whether a 5–7 bats in the middle overs or at the death.
- **Bowling clusters barely differ** in how often they're on playoff sides. Bowling quality matters (below), but which
  kind of bowler you have, less so.

## 3. The template (T3)

### What playoff sides have, nearly every season

| Role | Measure | Ahead | Playoff v rest | Champions' place |
|---|---|---|---|---|
| **Openers** | wins added | 92% of 12 | +0.47 v −0.13 | 0.70 |
| | average | 74% | 34.2 v 30.2 | 0.70 |
| | dot % | 79% | 39.0 v 41.2 | 0.62 |
| | share of the side's balls | 79% | 39% v 35% | 0.71 |
| **Powerplay batting** | average | 89% | 37.3 v 30.4 | 0.69 |
| **Middle & finishers (5–7)** | average | 84% | 31.9 v 28.3 | 0.64 |
| | boundary % | 84% | 16.7 v 15.8 | 0.75 |
| | strike rate | 74% | 128 v 125 | 0.68 |
| **Middle-overs spin** | wickets per 4 overs | 79% | 1.02 v 0.91 | 0.59 |
| **Middle overs (all bowling)** | wickets per 4 overs | 74% | 1.03 v 0.93 | 0.60 |
| **Death bowling** | economy | 79% | 9.64 v 10.14 | 0.73 |
| **Death pace** | dot % | 74% | 31.3 v 29.3 | 0.65 |
| **Squad build** | regular bowlers (120+ balls) | 84% | 6.1 v 5.5 | 0.68 |
| | top 5 bowlers' share of overs | 89% | 74% v 71% | 0.71 |
| | players used | 89% fewer | 19.3 v 20.8 | 0.28 (fewest) |

### In the Impact Player era (2023–26: 4 seasons, 40 team-seasons; small, so read as direction)

Every row below had playoff sides ahead in all 4 seasons:

| Role | Measure | Playoff v rest |
|---|---|---|
| Openers | average | 38.3 v 32.1 |
| | wins added | +0.53 v −0.18 |
| | share of balls | 39% v 34% |
| Powerplay batting | average | 44.8 v 33.6 |
| Top order (3–4) | strike rate | 155 v 147 |
| | dot % | 32.0 v 34.4 |
| Middle & finishers (5–7) | strike rate | 147 v 139 |
| Middle overs (all bowling) | wickets per 4 overs | 1.17 v 1.02 |
| Middle-overs spin | wickets per 4 overs | 1.15 v 0.98 |
| Middle-overs pace | economy | 9.05 v 9.62 |
| Death pace | economy | 10.56 v 11.20 |
| | dot % | 31.6 v 28.9 |

The shape is the same as the whole history. Batting depth now matters at a higher tempo: the 3–4 and 5–7 strike rates
separate sides more than before.

### What doesn't separate them (about 50–65% of seasons)

- **How much spin a side bowls:** 35% v 36% of overs, ahead 37%. Whether spin takes wickets in the middle overs is what
  counts.
- **How many all-rounders:** 0.95 v 0.76, ahead 53%. Champions do have more (place 0.72), but it doesn't hold year to year.
- **Powerplay and middle-overs economy:** ahead 63%. Wickets in those phases separate sides more than economy does.
- **Raw strike rates of openers and the powerplay:** ahead 58–63%. It's the openers' *average*, and how long they last,
  that separates.

### Consequences, not ingredients (shown, not used to grade)

Playoff sides give the lower order fewer balls (ahead 0%, so always fewer), and the 5–7s too (5%). Their top three take
55% of the balls against 50%. That's what a good top order produces, not something to build towards.

## The template in one paragraph

A playoff IPL side has:
- **Openers** who last: they average about 4 more and take a bigger share of the balls.
- **A 5–7** that scores boundaries rather than just surviving.
- **Middle-overs spin** that takes wickets, not just saves runs.
- **Pace at the death** that concedes about half a run an over less.
- **The overs in a settled group:** six regular bowlers, the top five bowling about three-quarters of them, and about
  1.5 fewer players used across a season.

## For the user to decide before T4 (grading squads)

1. **Labels:** keep the two splits the data found (opener volume; 5–7 middle against death)? I'd keep both.
2. **Measures to grade on:** the "nearly every season" table, all-history and Impact-era together, weighted by how
   consistently each separates. Leave out the consequences row.
3. **Thin leagues:** with 6 of 8 sides reaching the playoffs, the BBL needs "top half" as its benchmark. The IPL doesn't.
