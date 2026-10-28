# Verdict Screen: the player profile's first screen

Goal: one screenshot of a profile's first screen, plus its link, settles "is the hype fair?",
for all-rounders especially. It must load in under a second on a phone before the T20 season.

* Mockups (signed off in principle 2026-10-26): https://claude.ai/artifact/4o5QuXyvcB876Yqh4qsc5i
* Why: Marco Jansen's profile failed CARTA. It took about 4s to load, showed one role for an
  all-rounder, led with career totals that had no comparison, coloured form chips red/green by
  wickets, and clipped its cards on the right.
* Rules that apply: docs/social_rules.md (card anatomy, vocabulary). Mobile (375px) first. Don't
  copy Dan Weston's "translator" card (SD rating, translated SR, big ± number).

## Status tracker

| Chunk | Description | Status |
|---|---|---|
| V0 | Sign off decisions D1–D6 (below) | [ ] |
| V1 | Speed: remove the load waterfall (frontend only) | [x] 2026-10-26 (PR; ~3.3–4.9s → ~2.3–2.7s) |
| V2 | `GET /player/{name}/summary` endpoint + edge cache | [x] 2026-10-26 (PR; D1–D3 as proposed) |
| V2b | Dynamic peer floors (40% of the period's median, min 120) | [x] 2026-10-28 (services/qualification.py; floors per season, cleared in 2+ seasons) |
| V3 | Peer strips + season chart components | [x] 2026-10-28 (src/components/playerProfile/verdict/) |
| V4 | Verdict screen (T20) in UnifiedPlayerProfile | [x] 2026-10-28 (T20 + ODI switch; Test greyed) |
| V5 | Verdict line rules + 50-player review list | [~] 2026-10-28 rules v1 live (best rank + season swing); 50-player review list still to do |
| V6 | Form chips by runs above par | [x] 2026-10-28 (chips by runs above par, glyphs, dashed where no par) |
| V7 | Share image `/img/player/<id>.png` + OG tags | [x] 2026-10-28 (api/og.mjs verdict card + meta from /summary; PR) |
| V8 | ODI variant | [ ] |
| V9 | Pre-warm cache for upcoming fixtures' squads | [ ] |

**Deadline: V1–V7 live by 9 Dec 2026, a week before the IPL 2027 auction (16 Dec, Goa). See SOCIAL_CALENDAR.md.**
| T* | Tests: MULTI_FORMAT_PLAN chunks C0–C5, then a Test variant | [ ] |

## Decisions (V0)

Proposed answers are in **bold**. Confirm or change each before V2.

* **D1 Peer pool:** **T20 = major leagues (IPL, BBL, PSL, CPL, SA20, T20 Blast, ILT20, MLC, BPL,
  LPL, Super Smash) + T20Is between top-12 sides; ODI = ODIs between top-12 sides.** Against every
  side, the cheapest ODI bowlers since 2023 are associates (Namibia, Oman, Nepal, USA).
  Minimum balls: T20 600 bowling / 300 batting; ODI 500 / 400.
* **D2 Season metric:** **wins added (WPA) by season, split into bat and ball.** Bowling Impact is
  noise as a bowler rating (split-half r ≈ 0), so it moves below the fold.
* **D3 Form scope:** **the last 8 games whatever the scope, with neutral chips where there's no
  par** (The Hundred, ODIs). Otherwise Jansen's Hundred games disappear.
* **D4 Verdict line:** **written by rules, not an LLM**, at most 2 lines (~80 characters). The
  strongest rank is the claim; a season swing of more than one win, either way, is the second
  sentence.
* **D5 Share image:** **yes**, built on the summary endpoint.
* **D6 Visual identity:** **peer strips + season trend**, as in the mockups.

## Chunk briefs

### V1 Speed: remove the waterfall (frontend only, about one session)
Measured on production with Jansen's link: `/players` (162 KB, 0.8–1.3s) blocks everything, then a
500ms `setTimeout` (`UnifiedPlayerProfile.jsx:~308`), then `usePlayerData.fetchAllData` runs five
calls behind one `loading` flag. The slowest is batting `/players/{n}/dismissal_stats` (1.6–1.8s),
which the bowling screen never uses.
* If `?name=` is in the URL, start the player fetches at once and load `/players` + `/venues` in
  the background (they only feed the picker).
* Drop the 500ms timer.
* Show each section as its own data lands (per-fetch loading state, not one gate).
* Fetch dismissal stats lazily, when that section opens.
* Verify: Jansen's link renders the first card in under 1.5s (CDP phone emulation, throttled 4G).

### V2 Summary endpoint (backend)
`GET /player/{name}/summary?format=T20|ODI&start_date&end_date&scope=strong|all` returns, in a few KB:
identity (team, role, bowling style, usual batting position), and per role: season rows (balls,
runs, wickets, economy/SR, WPA, impact_per_innings), phase rows, the peer-strip metrics (value,
rank, n, and the peer distribution as ~50 quantiles, not every value), and the last 8 matches with
RAA. Precompute peer distributions per (format, scope, window) nightly. Set
`Cache-Control: s-maxage` keyed on `data_version` (see data-fix cache notes). Run
`regression_snapshot.py check` (should be unchanged).
Reference implementation of the numbers: `scripts/dev/verdict_mockup_data.py` (mockup page source: `scripts/dev/verdict_mockup.src.html`) (query API with
`format=T20`, `leagues=[...]`, `include_international=true`, `top_teams=12`).

### V2b Dynamic peer floors (fold into V3 or V4)
The peer pools in `services/player_verdict.py` use fixed floors (`MIN_BALLS`: T20 600 bowling /
300 batting; ODI 500 / 400). Switch them to the rule the statistical twins use
(DOPPELGANGER_PLAN.md, user 2026-10-27):
* For each role and **season** in the window, take the players with 5+ innings. That season's floor is **40% of
  their median balls**, never below 120; a player must clear it in **2+ seasons** (user, 2026-10-28: one floor
  over three seasons landed on 120 and let part-timers in).
* A player under the floor is still ranked against the pool (as now, `qualified: false`).
* Return the floor in `peers.min_balls`, and show it in the strip header ("v 213 bowlers, 380+
  balls").
* Bump `SUMMARY_VERSION` so cached summaries refresh. Share one helper with the twins engine
  (`services/qualification.py`) so both use the same rule.

### V3 Components
`PeerStrip` (faint tick per peer, median tick, player as a lime dot with a surface ring, better to the
right, "36th of 213" rank, top 10% in accent), `SeasonWinsChart` (thin diverging bars from 0, one per
role; bowl `#5b8def`, bat `#c4850f`, validated on surface `#101319`), `PhaseCells`. Use
`chartDefaults.js` + `useIsMobile`. Hover/tap tooltips.

### V4 Verdict screen
Replace the top of UnifiedPlayerProfile:
* identity row with a share button;
* T20 / ODI / Test switch (Test disabled until T*) and a one-line scope chip that opens the filter
  sheet;
* the verdict, the season chart, peer strips (all-rounders: 4 bowling + 2 batting (SR, average);
  specialists: 3–4 strips + phase cells), form, and the footer with URL + credit.

Existing sections stay below as collapsed rows. Default window: since Jan of 2 years back (T20),
3 years (ODI). The all-rounder layout must fit above a ~720px screenshot line at 375px.

### V5 Verdict rules
Templated sentences from ranks and season swings, in the user's vocabulary (wins added, runs above
par, balls per wicket, phases). Produce a review list of 50 players (India squad, top IPL names,
SA/AUS/ENG all-rounders) for the user to read before launch. No blame framing.

### V6 Form chips
Colour by summed RAA (bat + ball): > +2 up, < −2 down, else flat. Use the ▲ ▼ ● glyph as well as
colour; dashed outline where there's no par. Readable opponent codes. Tap opens the scorecard.

### V7 Share image
A Vercel function renders the verdict screen to PNG (like the existing `/img/:snapshotId.png`). The
profile route serves OG/Twitter tags pointing at it.

### V8 ODI variant
The season slot shows economy by year against the top-12 median until an ODI par model exists.
Phases 1–10 / 11–40 / 41–50. Neutral form chips.

### V9 Pre-warm
A nightly or match-day job hits `/summary` for every squad player in the next 3 days' fixtures.

## Mockup reference numbers (production, 26 Oct 2026; strong-opposition pool)
* Jansen T20 bowling since 2024: wins added 2.17 (36th of 213), dots 44.2% (21st), economy 8.65
  (129th), balls per wicket 18.4 (118th). WPA by season 0.60 / 1.99 / −0.41. Batting average
  20.0 (340th of 383).
* Jansen ODI since 2023 v top 12: balls per wicket 29.7 (32nd of 114), economy 6.65 (111th),
  SR 121 (4th of 114).
* Bumrah: wins added 6.5 (2nd of 213), economy 6.9 (4th). Abhishek: SR 196.6 (3rd of 383), wins
  added 4.12 (3rd).
