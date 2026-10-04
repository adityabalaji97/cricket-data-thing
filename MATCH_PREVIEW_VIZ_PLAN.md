# Match Preview: every visual where it earns its place (CARTA)

Plan written 2026-10-04. Chunks are sized so one session (Claude Code or Codex) can take one.
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

## 2. The preview as a sequence of questions

The screen reads top to bottom as a pre-match story. Each row is one module: the question it
answers, the visual that answers it best, and the data behind it.

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

### E. Go deeper
| # | Question | Visual | Data | Status |
|---|---|---|---|---|
| E1 | Read the full preview | Text with chart fences (same facts as the modules) | `MatchPreviewCard`, preview note draft | C |
| E2 | Ask your own question | Query prompts, now built from the module queries | `ContextualQueryPrompts` | C |
| E3 | Leaders tables | Behind "See full table" | Leaders | R (folded under D2) |

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
    takeaway=callable(rows) -> str,         # generated from the numbers, answers the question
    empty="No first-innings totals at this ground in the window.",
    formats=("T20", "ODI"),
    outputs=("screen", "snapshot", "graphic", "note"),
    weight=...,                             # default order; admin can override
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
- **Format-aware:** ODI previews use ODI phases (`format_config`); modules declare which formats
  they support.

---

## 4. Outputs: one computation, four surfaces

- **Screen:** the module renders on the preview.
- **Snapshot / embed:** "Embed" freezes the module (static snapshot, as the hypothesis notes do).
- **Graphic:** "Make a graphic" opens the 1080×1350 card for that module, using the existing
  `img.mjs` layouts. Pitch map gets a new `pitch` layout.
- **Note:** the nightly preview draft (`services/note_drafts.py`) is built from the top-ranked
  modules' takeaways and snapshots, so the note and the screen never disagree.
- **Admin:** `/admin` gets a per-fixture module panel to pin, hide and reorder modules (new
  table `preview_module_overrides`), next to the Social queue.

---

## 5. Chunks

| # | Chunk | Status |
|---|---|---|
| 0 | Audit: CARTA scorecard and usage for every current module | [ ] |
| 1 | Module contract and registry; wrap existing modules unchanged | [ ] |
| 2 | Mockups gate: real fixtures, every proposed module | [ ] |
| 3 | Correctness: era-aware par, toss/chase intervals, sample rules, similar-venue fallback | [ ] |
| 4 | The ground: B1–B8 | [ ] |
| 5 | The teams: C1–C4 | [ ] |
| 6 | The players: D1–D6 (incl. milestones service) | [ ] |
| 7 | At a glance and go deeper: A1–A2, E1–E3 | [ ] |
| 8 | Outputs: per-module snapshot, graphic (incl. `pitch` layout), embed | [ ] |
| 9 | Notes and admin: preview drafts from modules; per-fixture overrides | [ ] |
| 10 | Sweep and removals: phone screenshots, goldens, performance budget | [ ] |

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

### Chunk 1: Module contract and registry
- `services/preview_modules/` (registry, `QuerySpec`/`ServiceSpec`, sample rules, takeaway
  helpers); `GET /match-preview/modules` returns the ordered manifest and light data;
  heavy modules fetch on expand.
- `src/components/preview/`: `PreviewModule` shell (title from takeaway, sample chip, empty
  state, "Open in query builder", Share menu), rendered inside the existing `CollapsibleSection`
  and `VenueSectionTabs`.
- Wrap today's modules as-is. **Acceptance:** goldens identical; screenshots unchanged.

### Chunk 2: Mockups gate
- Build mockups for every proposed module with real data, using the connector tools
  (`preview_match`, `query_cricket_data`) for an upcoming IPL fixture, a T20I and an ODI. Use a
  thin-sample ground to show fallbacks.
- **You sign off before chunks 3–10.** Feedback is folded into this file.

### Chunk 3: Correctness first
- Era-aware par and venue averages (IPL `impact_player_era`); show both eras where they differ
  materially.
- Toss/chase: binomial interval, "within noise" label when the interval covers 50%.
- Sample rules wired into every module; similar-venue fallback.
- Key Battles evidence rule: within-player RAA vs baseline, min balls, no handedness templates.
- Death bowling leaders on leverage-weighted RAA, economy alongside.
- **Acceptance:** golden diffs limited to the intended fields; new tests per rule.

### Chunks 4–7: Modules
- One module = backend spec + frontend renderer + phone layout + empty state + test.
- Reuse the existing components named in section 1. New visual code only for: dumbbell and
  stacked on the site (they exist as image layouts only), the worm line, and the pitch-map share
  layout.
- New backend: `services/milestones.py` (D5). Everything else is query-builder specs or
  existing services.

### Chunk 8: Outputs
- Static snapshot per module; Share menu (Embed, Make a graphic); `pitch` layout in `img.mjs`
  plus legibility test (`tests/js/share_images.test.mjs`).

### Chunk 9: Notes and admin
- `note_drafts.py` preview drafts built from module takeaways and snapshots.
- Migration `016_preview_module_overrides.sql`; admin panel to pin, hide and reorder per fixture.

### Chunk 10: Sweep and removals
- Remove the pie, scores bar chart and radar from the preview; move Leaders behind D2.
- Phone screenshots at all three widths for all three formats; golden re-baseline with sign-off.
- **Performance budget:** first paint of the At a glance section under 1.5 s warm; no module
  fetches twice; lazy below the fold.

---

## 6. Open questions for you

1. **Fantasy:** `fantasy_planner` data exists. Should a "fantasy picks" module appear on the
   preview, or stay on its own page?
2. **ODI parity:** ship ODI previews with the same modules at once, or T20 first?
3. **Admin overrides:** worth a migration now, or rely on automatic ordering until usage data
   says otherwise?
4. **Women's T20:** no Primer metrics. Show the non-adjusted modules only, or hold the preview
   for women's fixtures until metrics exist?
