# The winners' template

How playoff sides are built, role by role, and how each current squad measures up against that shape. It extends the
team page's phase ranks from "where a side ranks" to "what a winning side looks like, and what this one is missing".
Agreed with the user, 6 Nov 2026.

## Decisions

| Question | Answer |
|---|---|
| Which leagues | One template per league; a side is graded against its own league's winners |
| Successful | Playoff sides each season; champions flagged within them |
| Roles | Both: data-driven usage clusters for the analysis, mapped onto familiar phase × job labels for display |
| Outputs | Team pages (a new card), the post-retention/pre-auction post series, and role as a query builder dimension |

## What "structure" means here

A season's squad is a set of players with **jobs** and **value**:

- **Jobs** come from usage, not reputation: where he bats (position, the phase he's at the crease), when and what he
  bowls (phase, pace or spin), how much (share of the side's balls).
- **Value** is the T20 Primer's Impact, runs above par (RAA) and wins added (WPA), batting and bowling. Per my
  memory notes these barely repeat season to season for bowlers. So the template describes **skill** by stable rates
  (strike rate, economy, dot %, false shots) and **contribution** by Impact, RAA and WPA. Each card says which it shows.

The template for a league is then, for each role, across that league's playoff sides:

- **Share:** what share of the side's balls (batting or bowling) the role takes.
- **Quality:** the league percentile of the role's main players, on each measure.
- **Depth:** how many players fill it, and how far the second-choice player falls below the first.
- **Contribution:** what share of the side's runs above par and wins added the role produces.

Each is set against the non-playoff sides. Only the differences that hold across seasons count as "the shape".

## Roles

**Familiar labels (display):**
- **Batting:** openers (1–2), top order (3–4), middle and finishers (5–7), lower order (8+).
- **Bowling:**
  - powerplay pace, powerplay spin;
  - middle-overs spin, middle-overs pace;
  - death pace.
- **All-rounders:** both jobs above a usage floor.

**Clusters (analysis):** each player-season gets a usage vector:
- balls faced by position and phase;
- balls bowled by phase and pace or spin;
- share of team balls.

The vectors are clustered per league. Each cluster is labelled by its nearest familiar role, so a "floating
middle-order hitter" or a "death-only specialist" can surface without being forced into a box. The user approves the
labels.

## Data facts (checked 6 Nov 2026)

- **Playoff matches:** `matches.event_match_number` is set for league games and NULL for knockouts, so a season's
  playoff sides are the teams in its knockout games. The champion is the winner of the last one. To check per league
  and season: 2008–10 IPL semis, the BBL finals series, PSL eliminators.
- **Competition names:** these differ by source, e.g. "Indian Premier League" against "IPL" for 2026 feed matches.
  Use `competition_canonical_sql`.
- **Leagues with enough seasons:**
  - IPL (19 seasons), BBL, PSL, CPL, BPL, Vitality Blast;
  - SA20 (4 seasons), The Hundred (not T20: 100-ball, kept out at first), Super Smash, LPL.
  - Each league's template states its sample (seasons, playoff sides). A thin one is labelled, not hidden.
- **Measures:**
  - Impact, RAA and WPA exist from 2015, in men's T20 (`ball_metrics`).
  - Line and length, shot and control are patchier.
  - So the template uses 2015 onwards for value measures, and every season for usage and rates.

## Chunks

| # | Chunk | Output |
|---|---|---|
| T0 | **Season ledger.** Per league and season: teams, league-stage table, playoff sides, champion. Spot-check against the web for the IPL, BBL and PSL. | `services/season_ledger.py`, tests |
| T1 | **Player-season roles.** Usage vector per player, team and season; familiar label by rule; cached per league and season. | `services/team_roles.py` |
| T2 | **Clusters.** Per league, cluster the usage vectors; map clusters to familiar labels; report what doesn't fit. The user signs off the labels. | analysis notebook/script + a short findings note |
| T3 | **The template.** Per league and role: share, quality percentile, depth and contribution, playoff against the rest. Keep only differences stable across seasons (bootstrap by season). | `services/team_template.py`, a findings doc with the IPL template |
| T4 | **Grading a squad.** A squad (current, retained, or post-auction) is filled role by role with each player's recent role and rates. Each role is scored against the template: meets, short, or surplus. | `grade_squad(league, squad)` |
| T5 | **Team page card.** "Against the winners' template": role rows, the template band, this side's mark, the gaps. Mobile first. | TeamPage card |
| T6 | **Query builder.** `role` as a dimension (group by and filter), from T1. | QB dimension + docs |
| T7 | **Post series.** After the 17 Nov retention lists: each IPL squad against the template, and the gaps to fill at the 16 Dec auction. Builder in the retention post's format. | `articles/ipl-template/post.py` |

The order is T0 to T4 first, because the findings decide whether the template is real. The user sees the IPL
template (T3) before any page or post is built on it.

## Status

- [x] T0 season ledger: IPL verified for all 19 seasons, game by game (6 Nov 2026)
- [x] T1 player-season roles: IPL, 3,400 player-seasons
- [x] T2 clusters: batting and bowling separately, 6 each; they map onto the familiar labels, plus 2 splits
- [x] T3 template: IPL, all seasons and the Impact Player era; see `TEAM_TEMPLATE_IPL_FINDINGS.md`
- [x] T4 grading squads (6 Nov 2026), in the retention posts' slide 7 ("Against the winners' template"):
  - **Graded roles (7):** openers (average), 3-4 (strike rate, 3 holders), 5-7 (strike rate, 3), powerplay pace
    (wickets), middle-overs spin (wickets), death pace (economy), bowling depth (regular bowlers).
  - **Holders:** each player's IPL 2024-26 at any side. Recent seasons count more (2026 ×4, 2025 ×2, 2024 ×1). One
    batting role per player (Samson is an opener only). Bowlers can hold several slots.
  - **Benchmark:** IPL team-seasons 2023-26 worked out the same way. Pinned in `services/pinned/team_template_IPL.json`
    (`scripts/build_team_template.py`).
  - **Weights:** how consistently each role separated playoff sides across 19 seasons.
  - **User checks on CSK:** the 3-4 should include Mhatre and Urvil, so recency and one-role-per-batter were added;
    Hosein joins Noor in middle-overs spin.

## Open questions (for T3)

- Is "playoff sides" too generous in leagues where most teams make the playoffs (6 of 8)? If so, use the top half.
- Squads change mid-season (injuries, replacements). Use the XI that played, weighted by balls, not the auction squad.
- Impact Player rule (IPL 2023 onwards): an extra batter or bowler changes the shape. Template eras: pre-2023 and
  2023 onwards, compared.
