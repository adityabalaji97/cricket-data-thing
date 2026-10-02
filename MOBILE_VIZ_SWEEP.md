# Mobile Viz Sweep — Status Tracker

| Chunk | Description | Status |
|---|---|---|
| 0 | Shared foundations (useIsMobile, touch tooltips, chartDefaults, CollapsibleSection, DetailSheet, TakeawayCard, ui_sweep 360/768) | [x] 2026-10-02 |
| 1 | Mockups artifact — user sign-off gate | [x] 2026-10-02 (signed off; defaults taken on all 5 calls) |
| 2 | Match preview fixes + mobile structure | [x] 2026-10-02 (preview-text-into-strip moves to chunk 3) |
| 3 | Match preview new vizs (What to expect, Key Battles, Foresight) | [x] 2026-10-02 (Foresight range/features deferred: match_predictions empty locally, cannot verify) |
| 4 | Player profile fixes + mobile structure | [ ] |
| 5 | Player profile chart rework + new vizs (At a glance, ShotMap, Impact/clutch) | [ ] |
| 6 | Rest-of-app sweep + dead code | [ ] |

## CARTA chart checklist
- **Complete**: sample size + filter context shown; explicit empty state.
- **Accurate**: no mixed-scale overlays; dual axes only when labelled; small samples flagged.
- **Relevant**: one question per chart; title states the takeaway.
- **Timely**: lazy, no duplicate fetches, refetch only on GO.
- **Accessible**: ≥11px text, ≥32px targets, tap-reachable detail, no rotated labels on mobile, ≥3:1 contrast, no page overflow.

---

# Mobile-First Visualization Sweep (CARTA)

## Context
Most Hindsight users, and the user themselves, use phones. Many charts were built desktop-first, especially the early ones. An audit (Oct 2 2026) found the main problems:
- **Charts hard-wired to desktop.** Some charts never receive `isMobile`, so phones get the desktop layout.
- **Overloaded charts.** A radar with 18 axes; a batter-vs-bowler matrix about 1000px wide.
- **Hover-only detail.** MUI Tooltips need a 700ms long-press on touch, and SVG `<title>` never shows.
- **Layout bugs.**
  - The Leaders tables can't scroll sideways.
  - Advanced Analytics goes blank once you scroll past it.
  - RecentFormStrip renders every innings in the date window.
  - InningsScatter traps page scroll.
- **Valuable data never shown:**
  - The `screen_story` context computed in `services/match_preview.py`.
  - Foresight `top_features`.
  - Wagon wheel and pitch-map endpoints.
  - Contextual metrics, shown only as a table.

Goal: make the **match preview** ("what to expect from this match") and **player profile** ("what this player has been like over a period") excellent on a 390px phone, then sweep every other chart in the app.

Decisions confirmed with the user:
- Story-first page layout with collapsible sections.
- All four proposed new or revived visualizations.
- Mockups first, then implementation.
- Scope covers the whole app.

**CARTA as concrete rules for every chart:**
- **Complete:** shows its sample size (balls, innings) and filter context, with a clear empty state.
- **Accurate:** no mixed-scale overlays on one axis; dual axes only when labelled. Small samples are flagged (greyed out when n below a threshold).
- **Relevant:** one question per chart, with a short title that answers it ("Scores faster vs spin in the middle overs"). Drop or fold away anything low-value.
- **Timely:** loads lazily, never fetches the same thing twice, and refetches only on GO.
- **Accessible:**
  - At least 11px text and 32px tap targets.
  - Every detail can be reached by tap.
  - No rotated labels on phones.
  - Contrast at least 3:1 using the `hindsightDark` tokens.
  - No horizontal page overflow; wide content gets a ScrollTable with a visible cue.

## Plan tracking
The first implementation step copies this plan into the repo as `MOBILE_VIZ_SWEEP.md` with a status-tracker table: one row per chunk, ticked `[x]` with the date when done, the same convention as `HINDSIGHT_FEATURE_PLAN.md`. Each chunk below is meant to be small enough to hand to another session (for example Codex).

---

## Chunk 0: Shared foundations (do first)
1. **`src/hooks/useIsMobile.js`:** one breakpoint helper (`isMobile` below `sm`, `isCompact` below `md`).
   - Replace the roughly 25 ad-hoc `useMediaQuery` calls and the `isMobile` props that default to `false`.
   - Components should call the hook directly instead of relying on a prop. This fixes the six charts that never receive it.
2. **Touch tooltips in the theme:** `theme/hindsightTheme.js` `MuiTooltip.defaultProps` set to `{ enterTouchDelay: 0, leaveTouchDelay: 4000 }`. This is a global fix for long-press-only detail.
3. **`src/theme/chartDefaults.js`:** Recharts presets built on `chartTheme.js` / `rechartsTooltipProps`.
   - Mobile margins and 11px ticks.
   - `angle=0`, with `interval="preserveStartEnd"` and short tick formatters.
   - A compact legend placed at the top.
   - A tooltip that opens on tap.
   - An `axisLabel()` helper that hides rotated Y labels on phones and puts the unit in the title.
4. **`ui/CollapsibleSection.jsx`:** wraps the existing `ui/Section.jsx` and `LazySection`.
   - Header shows a title plus a one-line takeaway; content mounts on expand.
   - Default open/closed state per section; open state stored in the URL hash.
   - Works with `VenueSectionTabs` (tapping a chip expands its section and scrolls to it).
5. **`ui/DetailSheet.jsx`:** a bottom-sheet pattern for "tap a cell, a dot or a chip to see full stats". It replaces hover-only cell detail.
6. **`ui/TakeawayCard.jsx`:** a compact headline-number card with a sparkline or mini bar, a caption and a sample-size footnote. Used by the story strips.
7. **Extend `scripts/dev/ui_sweep.mjs`:**
   - Add a 360px pass and a 768px tablet pass.
   - Add a check that flags rotated SVG text and elements wider than the viewport inside charts.

## Chunk 1: Mockups (approval gate)
- Load the `artifact-design` and `dataviz` skills.
- Pull real data through the Hindsight MCP tools: `preview_match` for a real upcoming fixture, `player_profile` for one batter and one bowler, and `query_cricket_data` for wagon zones, line/length and impact by phase.
- Publish **one private HTML artifact** with mobile (390px) mockups of:
  - **Match preview:** the "What to expect" strip and the Key Battles cards.
  - **Player profile:** the "Player at a glance" strip, the wagon wheel and pitch map, and the impact and clutch charts.
  - The collapsible section pattern.
  - **Before/after examples** for the matchup matrix and the doppelganger radar.
- **The user signs off before Chunks 2 to 6 begin.** Their feedback is folded into this plan.

## Chunk 2: Match preview bug fixes and phone layout
Files: `VenueNotes.jsx`, `Matchups.jsx`, `PostTossSetup.jsx`, `BoundaryAnalysis.jsx`, `MatchHistory.jsx`.
- **Leaders tables** (`VenueNotes.jsx` about 444-552): remove `overflowX:'hidden'`, and show the team as a short code under the player name instead of a `title` attribute.
- **MatchupMatrix:** fix the double-tab-open bug (the row `onClick` plus the inner `<a>`). Use a link only, and stop it opening on a sideways swipe.
- **FantasyAnalysisCard:** remove the nested `maxHeight:220` scroll. Show the top 5 with "show all".
- **PostTossSetup:** collapse into a summary row ("XI: 11 selected · Edit"). The roster chips open in the bottom sheet.
- **BoundaryAnalysis grid:**
  - On phones, use one card per phase with Pace/Spin as rows (or a segmented phase picker).
  - Switch to `hindsightDark` surface tokens instead of the light neutrals.
  - Use 11px or larger text.
- **ScoresBarChart:** replace the fixed pixel gutter and the percentage-placed labels with ECharts `grid.containLabel` and in-bar labels.
- **Section restructure with CollapsibleSection:**
  - Open by default: "What to expect" (new) and Teams.
  - Collapsed: Boundaries, Leaders, Explore.
  - Merge the Preview text card into the strip as a "Read full preview" expander.
  - Drop the duplicated Day/Night toggle.

## Chunk 3: Match preview new visualizations
1. **"What to expect" strip.** Backend: `routers/match_preview.py:338` adds an `expect` block built from the already-computed `screen_story` context in `services/match_preview.py` (around 1800).
   - Fields:
     - par score band (from `match_par` / `preview_metrics`)
     - toss-bias signal
     - phase templates (what a good powerplay, middle and death phase look like at this venue)
     - Elo for both teams and recent form
     - `expected_fantasy_points` (top 5)
     - `score_preview_lean`
   - Frontend: a horizontally swipeable row of `TakeawayCard`s, plus a phase-par bar (a bat-first vs chase par range per phase).
   - Add a regression snapshot for the endpoint.
2. **Key Battles** (`Matchups.jsx`):
   - On phones, by default, show a ranked list of the 6 to 8 most lopsided batter-vs-bowler matchups. Rank by SR delta and dismissal rate against each player's baseline, with a minimum-balls threshold.
   - Each card shows two names, a mini diverging bar (SR vs baseline), balls, dismissals, and an "edge" chip (batter or bowler).
   - "View full matrix" opens the existing matrix with a sticky batter column, tap-to-detail via DetailSheet, and the "Hover for more stats" copy removed.
   - Ranking runs on the client from the existing `/teams/{t1}/{t2}/matchups` payload. No backend change, unless baseline SRs are missing (then add them in `services/matchups.py`).
3. **Foresight:** `routers/ml_predictions.py` also selects the score low/high range, `top_features` and the phase predictions.
   - `ForesightCard` shows the predicted score range as an interval bar, plus the top 3 "why" features as plain-language chips.
   - Phase predictions are folded behind an expander.

## Chunk 4: Player profile bug fixes and phone layout
Files: `UnifiedPlayerProfile.jsx` and components under `playerProfile/`.
- **Advanced Analytics:** remove `enabled={activeSectionId===...}`. Gate on "has been visible once" instead, via LazySection. Also take `activeSectionId` out of the `sectionGroups` dependencies.
- **RecentFormStrip:** limit to the last 10 innings. Tapping a chip opens the DetailSheet (figures, SR, opponent, venue).
- **Non-core sections refetch on every edit:** Impact, LineLength, StrikeRateProgression, Boundaries, Dismissals and Advanced Bowling refetch on every filter change. Move them onto the applied filters that `usePlayerData` commits on GO, and reuse its `ball_stats` instead of refetching. Dedupe the doppelganger fetch.
- **Venue and competition filters:**
  - Pass `venue` through to `BoundaryAnalysis` and the doppelganger call.
  - Pass the competition filter to the global-rank call.
  - Where the backend can't filter, the UI says so.
- **InningsScatter:** pan only after a pinch or double-tap zoom (`panning.disabled` until scale > 1, `limitToBounds:true`).
- **Tablets (600-899px):** use the phone single-column layout until `md`, through `useIsMobile().isCompact`.
- **Restructure with CollapsibleSection:**
  - Open by default: a new "At a glance" strip, Overview, and Impact (now charts).
  - Collapsed: Performance, Shot map (new), Matchups, Dismissals, Visualizations, Explore.
  - DNA, Similar and Global Rank fold into "At a glance" cards that link to their full sections.
- **Filters:** the Venue Autocomplete is fixed at `width:250`; make it full width on phones.

## Chunk 5: Player profile chart rework and new visualizations
- **"At a glance" strip** (frontend only, from already-loaded data). `TakeawayCard`s for:
  - runs, SR and average vs the global baseline
  - best phase
  - weakest bowling type
  - impact/100 percentile
  - form trend sparkline
  - global rank

  Each card has a caption and its sample size.
- **Wagon wheel and pitch map revival:** port `WagonWheel.jsx`, `PlayerPitchMap.jsx`, `BowlerWagonWheel.jsx` and `BowlerPitchMap.jsx` into a single responsive `ShotMap` (viewBox-scaled, using the `fieldSvg` tokens).
  - Wagon wheel defaults to an aggregated **8-zone spoke view** (readable on a phone), with a toggle for a dot view. The pitch map is a line×length grid.
  - Both are filterable by phase and pace/spin, and tapping a zone opens a DetailSheet.
  - Endpoints: `/visualizations/{player|bowler}/{n}/wagon-wheel` and `/pitch-map` (`routers/visualizations.py`).
  - Merge `LineLengthProfile` into this "Shot map" section as the pitch-map tab: keep its comparison tabs and replace the tooltips with tap.
  - Also reuse it for `CaughtDismissalScatterMap`: move labels inside the circle, enlarge dots, and make details tappable.
- **Impact and clutch charts** (in `ImpactSection.jsx`; keep the table behind "Show table"). All from `/query/deliveries` with `group_by` year or phase (query builder v2):
  - (a) Impact per 100 balls by season, as a bar chart with a zero baseline.
  - (b) Impact by phase, as a diverging bar chart.
  - (c) Clutch: WPA per innings against average leverage, by season, as a dot chart. If that is too abstract, a "high vs low leverage SR" dumbbell instead.
- **Simplify overloaded charts:**
  - **Doppelganger radar:** on phones, replace it with a dumbbell list (player vs the most similar player on the top 8 dimensions). Keep the radar on desktop.
  - **Phase radar:** replace it with small multiples, one bar row per metric across PP / Middle / Death (one scale per metric).
  - **StrikeRateIntervals:** use a single series with intervals of 10 on phones; the other series go behind a toggle.
  - **WicketDistribution:** move Dot% off the wickets axis.
  - **OverCombinationsChart:** horizontal bars instead of rotated X labels, and use the chart defaults.
  - **TopInnings, BowlingInningsTable and FrequentOvers:** phones get 4 or 5 columns, and the remaining fields go into a DetailSheet on row tap. Wrap the BowlingInningsTable header row.
  - Add titles that state the takeaway to the charts that have none: ContributionGraph, WicketDistribution, OverEconomy and FrequentOvers.

## Chunk 6: Sweep of the rest of the app
Apply the Chunk 0 primitives and chart defaults. Fix whatever the 360/390/768px sweep flags.
- **Scorecard:** `WagonSpokes` is fixed at 240×240; make it scale with its viewBox. Check that the worm and win-probability SVG labels fit at 360px.
- **Comparison:** the tables in `BatterComparison` overflow, so use ScrollTable. Run `PhaseComparisonChart` and the comparison scatter and SR line through the chart defaults.
- **Team pages:** team radars become phase small multiples on phones. Check the `TeamComparisonVisualization` phase charts.
- **Matchups:** `MatchupsTab.jsx:419-550` has a fixed 400px three-column transfer list; turn it into a stacked phone picker using the bottom sheet.
- **Query builder:** in `ChartPanel.jsx`, change the `minWidth:200` selects to full width on phones, apply the chart defaults, and check that the pitch-map visualization scales.
- **Other pages:** rankings (`GlobalT20Rankings`), `IPLPredictions`, `DoppelgangerLeaderboard` and the landing-page `MiniWagonWheel` get the chart defaults and phone checks.
- **Wrapped cards** (`wrapped/cards/*`): replace the remaining light colour literals and check the Recharts bars at 360px.
- **Dead code:**
  - Stop computing `batting_scatter` in `main.py` (around 1500-1560).
  - Delete the now-ported `PlayerProfile.jsx`, `BowlerProfile.jsx` and `App.js.bak`.
  - Delete the other components nothing imports (list them in the PR before deleting).

---

## Verification
- **Run the app:** `scripts/dev/run_local_api.sh` (never repoint `.env`) and `npm start`.
- **Phone screenshots:** `BASE=http://localhost:3000 node scripts/dev/ui_sweep.mjs out` at 360, 390 and 768px, for the routes `venue_full`, `preview_odi`, `player`, the bowling player view, `query_res`, scorecard, comparison and team.
  - Before/after `report.json` must show zero horizontal overflow, zero text under 11px, zero rotated chart labels on phones, and no tap targets under 32px in charts.
  - Review the screenshots by eye.
- **Scripted phone sessions:** `scripts/dev/interact.mjs` covering:
  - opening and closing collapsible sections
  - tapping a matchup cell (DetailSheet opens; only one tab)
  - scrolling away from Advanced Analytics (content stays)
  - filter edits not refetching before GO (watch network calls)
  - InningsScatter not trapping scroll
- **Tests:** `npm test` (Jest/RTL), with new tests for `useIsMobile`, `CollapsibleSection`, Key Battles ranking and `ShotMap` zone aggregation.
- **Backend:** `pytest tests/` and `python scripts/regression_snapshot.py check` after the match-preview `expect` and `ml_predictions` changes. Add goldens for the new fields.
- **CARTA review:** for each hero page, check every chart against the five rules above, using a checklist in `MOBILE_VIZ_SWEEP.md`.
