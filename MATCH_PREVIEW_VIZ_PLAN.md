# Match Preview: every visual where it earns its place (CARTA)

Plan written 2026-10-04, revised the same day with the decisions below. Chunks are sized so one
session (Claude Code or Codex) can take one.
Tick the tracker with the date when a chunk lands, as in `MOBILE_VIZ_SWEEP.md`.

## Goal

Use the full range of chart types Hindsight already has, and the full range of data in the DB, on
the match preview — **but only where a visual answers a real pre-match question for this fixture.**
Every module must pass CARTA (`MOBILE_VIZ_SWEEP.md`):

- **Complete:** shows its sample (matches, innings, balls) and filter context; has an empty state.
- **Accurate:** no mixed-scale overlays; small samples flagged or greyed; claims carry their
  uncertainty where it matters (toss, chase, matchup edges).
- **Relevant:** one question per module, a takeaway title that answers it; nothing generic.
- **Timely:** loads lazily, one fetch per module, cached; refetches only on GO.
- **Accessible:** 11px+ text, 32px+ targets, every detail reachable by tap, no rotated labels on
  phones, 3:1 contrast, no page overflow.

"Use every chart type" is a means, not a target: a type is used where it is the clearest answer
to a question below, and the plan says explicitly where a type is *not* used and why.

## Decisions (2026-10-04)

| Topic | Decision |
|---|---|
| Audience | The average cricket viewer who is curious about the game's nuances. Plain words first; the jargon stays behind the info icon. |
| Text on a card | A **title** (the takeaway, in plain words), and where it applies **one help line**: "Higher is better" / "Lower is better" / "Bars right of the line are above average". Everything else (definitions, method, intervals, full credits) goes behind an **info icon** that opens a sheet. |
| Always visible (CARTA Complete/Accurate) | Inside the card: footer line 1 = sample + context + small-sample flag ("34 matches · IPL 2023–26 · small sample"); footer line 2 = "Hindsight · hindsightcricket.com · Data: Cricsheet, [feed], Primer method". Outside the shareable area: Open in query builder, Share. |
| Navigation | **Story style, replacing the section pills.** Tap the right/left edge or swipe sideways for next/previous; progress segments at the top; no auto-advance. |
| Card shape | Full phone screen, with title + chart + footer inside a centred **4:5 core**, so a screenshot crops cleanly to the 1080×1350 feed format the share images use. |
| Grouping | **Chapters:** At a glance · The ground · The teams · The players · Fantasy, then one closing card (full preview, ask your own question). A floating logo button (bottom corner) opens the chapter index and the settings sheet. Top/bottom app bars auto-hide in the story. |
| Filters | Sensible defaults (T20: 4 years; ODI: 8 years; IPL era-aware), changed in a settings sheet from the logo menu; the footer context line shows what's applied. |
| Desktop | A **grid of the same cards** (2–3 per row), same info sheet and actions. |
| Formats | Men's T20 and **ODI ship together** with the same questions and visuals. The Primer metrics (Impact, RAA, WAA, WPA) exist for men's T20 only, so every module declares an ODI fallback on plain stats (strike rate, economy, average, dot %, boundary %). |
| Women's T20 | Skipped for now. |
| Ordering | **Automatic** (no admin overrides): chapters in a fixed order, cards inside a chapter ranked by how distinctive and well-sampled they are for this fixture. |
| Fantasy | On the preview, as its own chapter: projected points, captain/vice picks, value picks (IPL only, where credit prices exist), differentials. |
| Scope | Match preview only. The story shell is built as a reusable component; profiles decide later. |

### Does this fit CARTA? Yes, with these rules
- **Relevant:** one card = one question, and the title answers it. That's the story format's
  natural shape.
- **Complete / Accurate:** the sample-and-context footer and small-sample flags stay on the card,
  not behind the icon.
- **Accessible:**
  - Swiping is never the only way to move: there are edge tap zones, arrow keys on desktop,
    and the chapter index.
  - The middle of the card is reserved for chart taps (a bar opens its detail sheet), so it never
    collides with next/previous.
  - Text stays at 11px or more inside the 4:5 core, and the info and action targets are 32px or
    more.
  - The logo button never covers chart content.
- **No horizontal scroll inside a card.** Tables and the batter × bowler matrix become ranked
  lists of up to 8 rows that fit one screen, with the full detail in a bottom sheet.
- **Timely:** only the current card and its neighbours load; one fetch per module, cached;
  changing settings refetches.

## Copy rules for the average viewer

- **Titles state the finding in everyday words:** "Chasing sides win more here", "Spinners
  go for fewer here than anywhere in the IPL". They don't describe the chart ("Runs by phase").
- **Metric names on the card are plain:**

  | Metric | Plain name on the card |
  |---|---|
  | Impact | runs added |
  | RAA | runs saved vs an average bowler / runs above an average batter |
  | WPA | win chances added |
  | leverage | pressure |

  The info sheet gives the real name, the definition and the Primer credit.
- **Help line only when direction isn't obvious:** "Higher is better" for runs added; "Lower is
  better" for economy; none for a scatter whose axes are labelled.
- **Info sheet contents:** what the chart shows, how to read it, metric definitions, the sample
  and the filters in full, intervals and tests where used, data credits, and the "Open in query
  builder" link again.

---

## 1. The building blocks we already have

### Chart types

| Type | Where it lives now | Share-image layout (`api/img.mjs`) |
|---|---|---|
| Stat tile / takeaway card | `ui/StatCard`, `ui/TakeawayCard`, `ExpectStrip` | `stat` |
| Ranked bars | Recharts bars (`ScoresBarChart`, query results), connector widget | `bars` (default) |
| Diverging bars (± vs a baseline) | `charts/DivergingBars`, `charts/PhasePercentileBars` | `diverging` |
| Dumbbell (A vs B per category) | Make-a-graphic only | `dumbbell` |
| Stacked bars (composition) | Make-a-graphic only | `stacked` |
| Line (trend / innings shape) | query results, scorecard worm | `line` |
| Scatter (two metrics, or score vs result) | `InningsScatter`, `ScatterChart` in `VenueNotes` | `scatter` |
| Field / wagon zones | `MiniWagonWheel`, `ShotMapSection`, `venue_boundary_shape` | `field` |
| Pitch map (line × length) | `PitchMap/PitchMapVisualization`, `LineLengthProfile` | — (new layout, chunk 8) |
| Win-probability curve | scorecard win-prob card | `win_prob` snapshot kind |
| Match recap card | scorecard recap | `recap` snapshot kind |
| Ranked list (facts, battles) | `KeyBattles`, records facts | `list` |
| Matrix (batter × bowler) | `MatchupMatrix` in `Matchups.jsx` | — |
| Form strip | `playerProfile/RecentFormStrip` | — |
| Donut | `charts/DismissalDonutChart` | — |
| Catch-location map | `charts/CaughtDismissalScatterMap` | — |
| Radar | `TeamPhasePerformanceRadar`, `PhasePerformanceRadar` | — |
| Pie | `WinPercentagesPie` (preview Summary) | — |
| Table | `ui/ScrollTable`, Leaders | — |

### Data the preview can draw on

- **Ball by ball** (`delivery_details`): line, length, shot, control, wagon zone/x/y, bat hand,
  bowl style/kind, crease combo, phase, venue, competition, toss and result via `matches`.
- **Game-state metrics** (`ball_metrics`, men's T20 2015+): Impact, RAA, WAA, WPA, leverage,
  win probability; `match_par` (par per match).
- **Query-builder dimensions** (Phase 1): `season`, `impact_player_era`, `bowler_entry_over`,
  `spell_number`, `prev_over_runs`, `batter_balls_faced`, innings strike-rate bucket,
  `query_mode=team_innings` (totals, phase run rates, 160–250+ rates, toss-winner win %),
  leverage-weighted RAA.
- **Teams and players:** rosters (`team_roster`), batting/bowling orders, Elo (`elo.py`),
  rolling form, dismissal stats, player patterns, relative metrics, fantasy points.
- **Venue:** `venue_delivery_stats`, `venue_boundary_shape`, `venue_similarity` (similar grounds),
  day/night.
- **Forecast:** Foresight / `ml_predictions`, `ipl_prediction`, `preview_metrics`, typed preview
  facts (Jev-ranked).
- **Hypothesis findings** that must shape the claims we make (`analysis/hypotheses/results`):
  - **H1:** IPL scoring is +0.66 runs per over in the Impact Player era. Par and venue averages
    must be era-aware.
  - **H7:** the toss is noise at Indian venues overall. Toss/chase framing needs intervals.
  - **H8:** "leg-spin to left-handers" backfires. No generic handedness matchup advice.
  - **H6:** economy and leverage-weighted RAA disagree at the death. Rank death bowlers on the
    adjusted metric.
  - **H0c:** "pressure from the other end" isn't supported. Don't build that narrative.

### What the preview shows today (`VenueNotes.jsx`)

Summary (win % pie, scores bar chart, phase strategy) · What to expect (`ExpectStrip`) · Full
preview (`MatchPreviewCard`) · Teams (`MatchHistory`, `PostTossSetup`, `Matchups` / `KeyBattles`)
· Boundaries (`BoundaryAnalysis`) · Leaders (batting / bowling tables) · Explore (query prompts)
· Foresight (`ForesightCard`).

---

## 2. The preview as chapters of questions

Each row is one card: the question it answers, the visual that answers it best, and the data
behind it. The Data column names the T20 metric; ODI cards use the plain-stat fallback (section
3).

Status key: **K** keep · **C** change · **N** new · **R** remove/fold.

### A. At a glance
| # | Question | Visual | Data | Status |
|---|---|---|---|---|
| A1 | What should we expect, in one look? | Stat tiles: par band, chase win % **with interval**, forecast lean, last meeting | `expect` block, `match_par`, era-aware | C (`ExpectStrip`) |
| A2 | Who's favourite and by how much? | Stat tile + small win-probability bar | Foresight / `ml_predictions` | C (fold `ForesightCard` up here) |

### B. The ground
| # | Question | Visual | Data | Status |
|---|---|---|---|---|
| B1 | What total wins here? | Scatter: first-innings total vs result, coloured win/loss, par band shaded, current-era points highlighted | `team_innings` (venue, innings 1, `match_outcome`) | N (replaces scores bar chart) |
| B2 | How does an innings unfold here? | Line: average cumulative runs by over, this ground vs the competition (worm) | `group_by=over`, venue vs competition | N |
| B3 | Which phase is unusual here? | Diverging bars: runs per over and wickets per over by phase, vs the competition average | phase query, venue vs competition | C (replaces `PhaseWiseStrategy`) |
| B4 | Does batting first or chasing win, and is it real? | Stat tile with interval and "within noise" label; no pie | `team_innings` toss and results, binomial interval | C (removes `WinPercentagesPie`) |
| B5 | Pace or spin here? | Stacked bars: share of wickets and balls by pace / spin per phase; RAA per 100 for each | `group_by=phase,bowl_kind`, venue | C (from `BoundaryAnalysis`) |
| B6 | Where do the boundaries go? | Field / wagon zones: boundary share by zone, square vs straight | `venue_boundary_shape` | N |
| B7 | What length works here? | Pitch map: RAA per 100 by line × length, pace and spin tabs | `venue_delivery_stats` / query `group_by=line,length` | N |
| B8 | How do batters get out here? | Donut (≤4 slices: caught, bowled, lbw, other) | dismissal query at venue | N (donut kept only while ≤4 slices) |

### C. The two teams
| # | Question | Visual | Data | Status |
|---|---|---|---|---|
| C1 | Where will this game be won? | Dumbbell: team A vs team B, Impact per 100 batting and RAA per 100 bowling, per phase | query by team × phase, last 2 seasons | N |
| C2 | How strong is each side in each phase, vs the league? | Percentile bars (not radar) | `PhasePercentileBars` | C (replaces radar on phones) |
| C3 | Who's in form? | Line: Elo for both sides over the season; form chips | `elo.py`, results | N |
| C4 | What happened last time? | Recap card plus win-probability curve of the last meeting | scorecard `recap` / `win_prob` snapshots | N |
| C5 | Head to head | Compact table | `MatchHistory` | K |
| C6 | Likely XIs | Lists | `PostTossSetup` / rosters | K |

### D. The players
| # | Question | Visual | Data | Status |
|---|---|---|---|---|
| D1 | Which match-ups decide it? | Ranked list (6–8), each opening the matrix row in a sheet; evidence rule: within-player RAA vs baseline, min balls, no generic handedness framing | `/teams/{a}/{b}/matchups` | C (`KeyBattles`) |
| D2 | Who adds the most, by phase? | Ranked bars: Impact per 100 for each squad's batters and leverage-weighted RAA for bowlers, phase tabs | query builder, squad filter | C (replaces Leaders tables as the default view) |
| D3 | Who's hot? | Form strips (last 10 innings) for each side's top 3 | `rolling_form` | N |
| D4 | Who suits this ground? | Scatter: squad players' career record here vs elsewhere (Impact per 100), similar-venue fallback when thin | query by player × venue; `venue_similarity` | N |
| D5 | Records in play | Ranked list: milestones within reach this match | new `services/milestones.py` | N |
| D6 | How does the key bowler work? | Pitch map in the player's detail sheet | `LineLengthProfile` | N (in sheet, not on the page) |

### F. Fantasy
| # | Question | Visual | Data | Status |
|---|---|---|---|---|
| F1 | Who will score the most fantasy points? | Ranked bars, top 8 projected points across both sides, team colour per bar | `fantasy_planner` projections (matchup model), every format | N |
| F2 | Who should be captain and vice-captain? | Two stat tiles, each with a one-line reason ("Averages 52 points vs this attack") | F1 projections + matchup edges | N |
| F3 | Who's the best value? | Ranked bars: projected points per credit | IPL credit prices (`_load_player_prices`); **IPL only**, card hidden elsewhere | N |
| F4 | Who could surprise? | Dumbbell: usual points vs projected points here, biggest gaps first | projections vs each player's average fantasy points | N |

### Closing card (last card of the last chapter)
| # | Question | Visual | Data | Status |
|---|---|---|---|---|
| E1 | Want the whole story in words? | Link card → the preview note (same facts as the cards) | `MatchPreviewCard` text / preview note draft | C (moves off the main flow) |
| E2 | Ask your own question | Up to 4 one-tap query prompts built from this fixture's card queries | `ContextualQueryPrompts` | C |
| E3 | Full leaders tables | "See full tables" opens a sheet (tables can scroll there, not on a card) | Leaders | R (folded) |

### Not used on the preview, on purpose
- **Radar:** hard to read on phones and misleading with many axes. Replaced by percentile bars.
  Desktop may keep it behind a toggle.
- **Pie:** two-way splits read better as a stat with an interval.
- **Catch-location map:** too thin per ground. Revisit if a venue has 150+ caught dismissals.
- **Doppelganger radar, wrapped cards:** not pre-match questions.

---

## 3. Module contract

Every module is declared once, in `services/preview_modules/registry.py` (backend) and
`src/components/preview/modules.js` (frontend):

```python
Module(
    id="ground_total_vs_result",
    question="What total wins here?",
    visual="scatter",                      # one of the types in section 1
    data=QuerySpec(...) | ServiceSpec(...), # query-builder params, or a named service call
    sample=SampleRule(min_matches=15, below="flag" | "grey" | "fallback_similar_venues" | "hide"),
    takeaway=callable(rows) -> str,         # plain-words title generated from the numbers
    help_line="Higher is better" | None,   # the only other text on the card
    info=InfoSpec(...),                     # sheet: how to read, definitions, sample, method, credits
    odi=FallbackSpec(metric="strike_rate", help_line=...),  # plain-stat version (no Primer metrics)
    fits=FitRule(max_rows=8, no_horizontal_scroll=True),
    chapter="ground",
    relevance=callable(rows, sample) -> float,  # automatic order inside the chapter
    empty="No first-innings totals at this ground in the window.",
    formats=("T20", "ODI"),
    outputs=("screen", "snapshot", "graphic", "note"),
)
```

- **Query-backed modules** use the query builder, so they get "Open in query builder", result
  caching (`query_cache`), embeds and share images for free.
- **Service-backed modules** (Elo, recap, forecast) return the same row shape as a snapshot.
- **Sample rules** apply everywhere: flagged under 15 matches or innings, greyed under 5. Venue
  modules fall back to "grounds like this" (`venue_similarity`) when the venue itself is thin, and
  say so in the title.
- **Era-aware by default:** IPL modules use `impact_player_era=2023+` unless the module is about
  change over time.
- **Format-aware:** ODI previews use ODI phases (`format_config`) and each module's plain-stat
  fallback; the info sheet says the game-state metrics are T20-only.
- **Automatic ordering:** chapter order is fixed; inside a chapter, cards are ranked by a
  relevance score (how far this fixture departs from the norm, times a sample-strength factor).
  Cards that fail their sample rule and have no fallback are left out of the story, not shown
  empty.

---

## 4. Outputs: one computation, four surfaces

- **Screen:** the module renders on the preview.
- **Snapshot / embed:** "Embed" freezes the module (static snapshot, as the hypothesis notes do).
- **Graphic:** "Make a graphic" renders the card's 4:5 core at 1080×1350 with the existing
  `img.mjs` layouts, so it matches a screenshot. Pitch map, form strip and donut get new layouts.
- **Note:** the nightly preview draft (`services/note_drafts.py`) is built from the top-ranked
  modules' takeaways and snapshots, so the note and the screen never disagree.

---

## 5. Chunks

| # | Chunk | Status |
|---|---|---|
| 0 | Audit: CARTA scorecard and usage for every current module | [x] 2026-10-04 |
| 1 | Story shell: card frame (4:5 core), chapters, navigation, auto-hiding chrome, logo menu, settings sheet, deep links, desktop grid | [ ] |
| 2 | Module contract and registry; copy rules; ODI fallbacks; wrap existing modules as cards | [ ] |
| 3 | Mockups gate: real IPL, T20I and ODI fixtures, every card | [ ] |
| 4 | Correctness: era-aware par, toss/chase intervals, sample rules, similar-venue fallback | [ ] |
| 5 | At a glance and the ground: A1–A2, B1–B8 | [ ] |
| 6 | The teams: C1–C6 | [ ] |
| 7 | The players: D1–D6 (incl. milestones service) | [ ] |
| 8 | Fantasy: F1–F4 | [ ] |
| 9 | Outputs: Make a graphic = card core (new layouts), embeds, preview note from cards | [ ] |
| 10 | Switch-over: story becomes the default, pills removed, phone/desktop sweep, goldens, performance budget | [ ] |

### Story shell and card anatomy (applies to every chunk)

```
┌──────────────────────────────┐  progress segments (chapter)       ← outside the share crop
│                              │  chapter name · fixture            ← outside the share crop
│ ┌──────────────────────────┐ │
│ │ Title (the takeaway)   ⓘ │ │  ┐
│ │ Higher is better         │ │  │
│ │                          │ │  │ 4:5 core: what a screenshot
│ │        chart             │ │  │ or Make-a-graphic shares
│ │                          │ │  │
│ │ 34 matches · IPL 2023-26 │ │  │
│ │ Hindsight · hindsight... │ │  ┘
│ └──────────────────────────┘ │
│  [Open in query builder] [Share]                                  ← outside the share crop
│                         (logo)│  floating button: chapters + settings
└──────────────────────────────┘
tap left 20% = previous · tap right 20% = next · middle = chart taps · swipe sideways = next/previous
```

- **Deep links:** each card has its own URL (`/venue?...#ground-total-vs-result`), so a shared
  link opens on that card.
- **Same design as the share images:** the 4:5 core uses the `img.mjs` palette, fonts and
  legibility floors, so "Make a graphic" for a card produces the same picture as a cropped
  screenshot.
- **Desktop:** the same card component in a grid; clicking a card opens it in the story viewer.

### Chunk 0: Audit (read-only)
- Screenshot the current preview at 360/390/768 px (`scripts/dev/ui_sweep.mjs`, routes
  `venue_full`, `preview_odi`) for one IPL, one T20I and one ODI fixture.
- Score every current module against the CARTA checklist; record it in a table in this file.
- Pull usage per module from the usage log: section opens and expands, Make-a-graphic and embed
  counts.
- Check each current claim statistically: chase/toss edges and venue averages, with intervals
  and era splits.
- **Output:** the audit table, plus a confirmed keep/change/remove list (section 2 is the
  proposal).

### Chunk 0 results (2026-10-04)

**How it was audited:**
- the live site, after the v478 deploy;
- `ui_sweep.mjs` at 360, 390 and 768 px on Wankhede (IPL), Kingsmead (ODI) and Korogi (4 T20s,
  the thin-data case);
- `app_events` for the last 30 days;
- claims re-checked on the full-data copy.

**Automated checks.** No overflow, no low contrast, no rotated labels and no text under 11px at
any width. Tap targets under 32px: 7 on phones (filter inputs at 28px, the Credits link) and
81–86 at 768px (autocomplete Clear/Open buttons at 31px).

**Usage.**
- `/venue` had 415 views from 398 visitors in 30 days: about one view each, and **zero shares**.
  For comparison, `/player` had 2,121 views and 14 graphics were made site-wide.
- **No per-section events exist**, so module-level relevance can't be measured yet.
  Chunk 2 adds `card_view`, `card_share` and `card_info` events.

**Claims checked:**
- "Chasing sides have won 29 of 49 matches at Wankhede." On the full data it's 32 of 59, 54%
  (95% CI 42–66%, p = 0.60): **within noise, but stated as a venue trait.**
- Wankhede's average first innings was 167 before 2023 (21 innings) and 193 since (38 innings).
  The preview shows a blended **183, about 10 runs under the current era.**
- Several bullets rest on tiny samples:
  - "MI reached the average winning total in 0 of their last 2 innings" (n = 2);
  - "SKY 41 off 12 vs Foulkes" (12 balls);
  - Korogi's leaders, e.g. "Hasan Nawaz average 123" from 2 innings.

  None are flagged.
- The fantasy table shows "Confidence 90%" for every player, which tells the reader nothing.

**Module scorecard.** ✓ = passes; ✗ = fails; ~ = partly. Columns: C = Complete, A = Accurate,
R = Relevant, T = Timely, Ac = Accessible.

| Current module | C | A | R | T | Ac | Notes | Becomes |
|---|---|---|---|---|---|---|---|
| What to expect (par + toss cards) | ~ | ✗ | ✓ | ✓ | ✗ | par mixes eras; toss card cut off in a sideways scroller | A1 |
| How winning innings were built (stacked phase bars) | ✗ | ✓ | ✓ | ✓ | ✓ | good chart; no sample shown | **keep as B-card (stacked)**, add sample |
| Summary: results split bar | ✓ | ✗ | ~ | ✓ | ✓ | no interval; shows 2–2 at Korogi as if meaningful | B4 (stat + interval) |
| What total wins here (dot strip) | ✗ | ✗ | ✓ | ✓ | ✓ | no sample, era-mixed; still a clear visual | B1 (scatter), dot strip as thin-sample fallback |
| Phase-wise strategy ("55-1" blocks) | ✗ | ~ | ✗ | ✓ | ~ | no units or takeaway; hard for a casual reader | B3 (diverging) |
| Full preview (AI text) | ~ | ✗ | ~ | ✓ | ✓ | unqualified noise claims (above); long | closing card; facts pass sample rules |
| Head to head | ✓ | ~ | ✓ | ✓ | ✓ | 5 matches; flag | C5 |
| Recent at venue (list) | ✓ | ✓ | ✓ | ✓ | ✓ | fits a card already | **keep** (ground chapter) |
| Form chips | ✓ | ✓ | ✓ | ✓ | ✓ | | C3 (with Elo line) |
| Playing XIs and toss / Matchup matrix axes | — | — | — | — | ~ | controls, not charts | settings sheet |
| Fantasy top picks (table) | ~ | ✗ | ✓ | ✓ | ✓ | uniform "90% confidence" | F1–F2 |
| Key battles (diverging bars) | ✓ | ✗ | ✓ | ✓ | ✓ | 12-ball minimum; strike rate only | D1 (evidence rule) |
| Boundaries (cards + table) | ~ | ✓ | ~ | ✓ | ✗ | table scrolls sideways (cut at "BO…"); "bpb" jargon | B5 (stacked, plain words) |
| Leaders (tables) | ✓ | ✗ | ~ | ✓ | ✓ | no sample floor (avg 123 from 2 innings) | D2 lists + full tables in sheet |
| Explore | ✓ | ✓ | ~ | ✓ | ✓ | | closing card |

**Changes to section 2 from the audit:**
- "How winning innings were built" and "Recent at venue" are kept as ground cards (they were
  missing from the plan).
- The dot strip stays as the thin-sample fallback for B1.
- Fantasy and Key Battles are **changes**, not new: their components exist.
- Sample floors are the most urgent fix (chunk 4). Era-aware par goes with them.

### Chunk 1: Story shell
- `src/components/story/`: `StoryViewer` (chapters, progress segments, edge tap zones, sideways
  swipe, arrow keys, no auto-advance), `StoryCard` (full-screen frame with the 4:5 core, title
  row with info icon, help line, two-line footer, action strip), `LogoMenu` (floating button:
  chapter index, settings sheet), `InfoSheet` (built on `ui/DetailSheet`).
- Auto-hide the app's top and bottom bars inside the story; respect safe-area insets; the logo
  button never covers the core.
- Deep links per card; browser back leaves the story.
- Desktop: `StoryGrid` renders the same cards 2–3 per row; a click opens the viewer at that card.
- Behind a flag (`?story=1`) until chunk 10. **Acceptance:** phone screenshots at 360/390/768 px
  show title + chart + footer inside the core with no overflow; keyboard-only navigation works;
  tap zones don't trigger on chart taps.

### Chunk 2: Module contract and registry
- `services/preview_modules/` (registry, `QuerySpec`/`ServiceSpec`, sample rules, takeaway and
  help-line helpers, ODI fallbacks, relevance score); `GET /match-preview/cards` returns the
  ordered card manifest and light data; heavy cards fetch when they're within one card of view.
- Copy rules as code: a plain-name map for metrics (runs added, runs saved, win chances added,
  pressure) used by titles, help lines and info sheets.
- Wrap today's modules as cards where they already fit one screen (the expect strip, H2H, forecast).
  The rest are rebuilt in chunks 5–8. **Acceptance:** golden snapshots identical for the existing
  endpoints.

### Chunk 3: Mockups gate
- Build mockups of every card with real data, using the connector tools (`preview_match`,
  `query_cricket_data`) for an upcoming IPL fixture, a T20I and an ODI. Include a thin-sample
  ground to show the fallbacks.
- **You sign off before chunks 4–10.** Feedback is folded into this file.

### Chunk 4: Correctness first
- Era-aware par and venue averages (IPL `impact_player_era`); show both eras where they differ
  materially.
- Toss/chase: binomial interval, "within noise" label when the interval covers 50%.
- Sample rules wired into every card; similar-venue fallback.
- Key Battles evidence rule: within-player RAA vs baseline, min balls, no handedness templates.
- Death bowling leaders on leverage-weighted RAA, economy alongside.
- **Acceptance:** golden diffs limited to the intended fields; new tests per rule.

### Chunks 5–8: Cards by chapter
- One card = backend spec + renderer + ODI fallback + info sheet copy + empty state + test.
- Reuse the components named in section 1. New visual code only for: dumbbell and stacked on the
  site (they exist only as image layouts today), the worm line, and fantasy bars with team colours.
- New backend: `services/milestones.py` (D5); fantasy projections exposed per fixture for every
  format (F1, F2, F4), credit prices for IPL (F3).
- Tables and the matrix become lists of up to 8 rows with a detail sheet; nothing scrolls sideways
  inside a card.

### Chunk 9: Outputs
- "Make a graphic" renders the card core at 1080×1350; new `img.mjs` layouts for pitch map, form
  strip and donut, with legibility tests (`tests/js/share_images.test.mjs`).
- Embeds use static snapshots of the card data.
- The nightly preview note draft (`services/note_drafts.py`) is built from the top cards'
  takeaways and snapshots.

### Chunk 10: Switch-over
- The story becomes the default preview; section pills (`VenueSectionTabs`) are removed from the
  preview; the pie, scores bar chart and radar are retired there; Leaders are folded under D2.
- Phone screenshots at all three widths for T20 and ODI; desktop grid at 1280 px; goldens
  re-baselined with your sign-off.
- **Performance budget:** first card under 1.5 s warm; no module fetched twice; neighbours
  preloaded only.

## 6. Open questions

None outstanding; see Decisions. The 2015+ feed credit on every card is still a placeholder
(`analysis/hypotheses/credits.py`).
