# Statistical Twins: doppelgänger search, rebuilt

Goal: "who is X's statistical twin?" answered with the T20 Primer metrics and ball tracking, for
the profile's "Similar players" section **and** a repeatable content series (post + Reel).
Prompted by a hoopers_stats Reel on Kobe's statistical twin (13 percentile inputs, nearest
neighbour, a radial "rings = distance" map). We borrow the method, which is standard
nearest-neighbour, and make our own look. We don't copy their frames.

## User's calls (2026-10-27)
* **Unit: both.** Player-seasons for content (twins across eras: "Abhishek 2025 ≈ Gayle 2015") and
  careers-in-a-window for the profile section.
* **Two separate twins:** a **"plays like"** twin (style) and a **"worth like"** twin (value). When
  they disagree, that's a story too.
* **Both together:** one engine feeding the profile section and the post/Reel template.
* **All three roles:** batters, bowlers, all-rounders (bat + ball matched together).

## Where it stands
`services/search.py:get_player_doppelgangers` measures Euclidean distance over z-scored
**outcome** stats (average, SR, dot %, boundary %, the same by phase; bowling economy/SR/dots by
phase) plus pace/spin split features, within one date window, men's T20 only. It has no context
metrics, no usage, no shot mix, no era adjustment, and no explanation of why two players match.

## Status tracker

| Chunk | Description | Status |
|---|---|---|
| S0 | Sign off feature lists + floors (below) | [ ] |
| S1 | Feature tables: player-season + career vectors (nightly, precomputed) | [ ] |
| S2 | Engine: percentiles, group weights, two distances, explanations | [ ] |
| S3 | Validation: sanity twins, stability, a review list for the user | [ ] |
| S4 | API: `/twins/{player}` (season or window, role, style/value) | [ ] |
| S5 | Profile "Similar players" section on the new engine | [ ] |
| S6 | Visuals: percentile strip (reuse V3 PeerStrip), distance star, twin map | [ ] |
| S7 | Post/Reel template + the first 5 twins | [ ] |

## Method (S1–S2)

**Pool.** Men's T20, 2015 onwards (when Impact/WPA and ball tracking start), strong-opposition
scope by default (major leagues + T20Is between top-12 sides; see VERDICT_SCREEN_PLAN D1).
**Floors are dynamic (the user, 2026-10-27).** No fixed ball counts across eras. Each period's floor
comes from who actually played in it, per role:
* Take the role's players in that period (a season for player-seasons, the window for careers)
  with at least 5 innings. Their median balls is that period's "regular" workload.
* The floor is **40% of that median**, so it rises and falls with how much T20 there was. 2015 has
  fewer leagues (no SA20, ILT20, MLC), so players face fewer balls than in 2025, and the floor
  follows.
* A **noise guard** sits underneath: never below 120 balls for batters or bowlers. Percentiles
  from a few dozen balls are luck.
* **All-rounders** must clear each role's floor (bat and ball) for the period.
* The floor used is stored with every vector and shown in the API ("qualified: 250+ balls, 40% of
  the 2025 median"). The 40% is checked in S3: if twins jump around when it moves to 30% or 50%,
  it's too tight.

**Era adjustment.** Every feature becomes a percentile **within its season** (and the same pool),
so a 2015 strike rate is compared with 2015 and a 2026 one with 2026. Runs above par and wins
added are already set against game state, and the percentile adds the era.

**Features.** Weights are per group, so a group with many features (shot mix) can't drown out a
group with one.

*Batting: "plays like" (style)*
* Usage: average entry over, share of balls in powerplay / middle / death, balls per innings
* Scoring shape: dot %, boundary %, sixes share of boundaries, SR by phase
* Shot mix (tracked): shares of the 11 shot families, control %
* Matchups: SR and dismissal rate v pace and v spin
* Not used: average, Impact, WPA (those are value)

*Batting: "worth like" (value)*
* Runs above par per 100 balls, overall and by phase
* Impact per innings, wins added per innings
* Balls per dismissal, average

*Bowling: style*
* Usage: share of overs by phase, typical over numbers, spell length
* Line and length mix (tracked), pace/spin kind, control % induced
* Dot %, boundary % conceded by phase; v LHB and v RHB

*Bowling: value*
* Economy and runs above par per over by phase, balls per wicket, wickets above average
* Wins added per innings (bowling Impact is noisy as a rating, so it's kept out)

*All-rounders:* the bat and ball vectors concatenated, each role weighted by its share of the
player's innings (the verdict screen's innings rule), and matched only against other all-rounders.

**Distance.** Euclidean over percentiles (0–1), group-weighted. Rings for the map: distance in
percentile-standard-deviation units, like "d = 3/6/9". Output per twin:
* the distance;
* the 3 closest and 3 furthest features ("same powerplay intent, different v spin");
* how much tracking data the vector rests on (tracked share), flagging thin vectors.

**Missing data.** Tracked features (shot mix, line/length, control) are patchy. With less than
70% of balls tracked, the tracked group is dropped for that pair and the remaining weights are
re-normalised; the twin carries a note.

## Validation (S3)
* Sanity twins should look right to a cricket eye: openers with openers, finishers with finishers.
  Produce the top-3 style and value twins for 40 players the user knows (India squad, IPL
  captains, overseas stars). The user reviews them before anything ships.
* Stability: split each season's balls in two halves; a player's twin from each half should
  overlap (an echo of the bowler-rating reliability check, split-half r ≈ 0 for bowling Impact).
* Check that one group doesn't dominate: drop each group in turn and count how many twins change.

## API (S4)
`GET /twins/{player}?unit=season|window&season=2025&start_date&end_date&role=bat|bowl|allround&kind=style|value&n=5`
→ twins with distance, closest/furthest features, both players' percentile rows, tracked share.
Precomputed nightly for player-seasons (one table), cached per window for careers.

## Profile (S5)
Replace "Similar players" with two short lists, **Plays like** and **Worth like**, each linking to a
side-by-side page (percentile strips, both players). Same section for all three roles.

## Visuals (S6)
* **Percentile strip** (the inputs): one row per feature, the player's dot on 0–100. The same
  component as the verdict screen's PeerStrip (V3), so building V3 first pays twice.
* **Distance star** (the method): the player at the centre, the nearest 15 on spokes labelled with
  distance.
* **Twin map:** all player-seasons placed by distance, rings at fixed distances, the twin labelled,
  brightness by closeness. Use an MDS or UMAP layout for angle; radius is the true distance.
* Hindsight's own look: dark surface, lime highlight, team colours for the twin's dot, card
  anatomy rules (claim title, one-line footer).

## Content (S7)
A Reel and carousel with four beats: the claim ("Abhishek's statistical twin is Gayle 2015"), the
inputs (percentile strip), the method (distance star, one line on the formula), the map (rings)
→ the twin side by side. The "plays like" v "worth like" split makes a second beat when they
differ. First five: Abhishek, Jansen (all-rounder), Bumrah, Sooryavanshi, Rinku. Also usable in
auction posts ("the pool's closest thing to X").

## Rough cost
S1–S3 are the heavy chunks (feature SQL + validation), each about V2-sized. S4–S5 are V2-sized
together. S6 shares components with V3. S7 is a content session.
Order: V3 (shared strip) → S1 → S2 → S3 (user review) → S4 → S5 → S6 → S7.
