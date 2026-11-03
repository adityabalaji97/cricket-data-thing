# Player profile, simplified

Agreed direction (user, 3 Nov 2026): the profile is the verdict and "plays like", then a few role-specific cards; every
other section is removed outright (the query builder and the connector still reach the data). Mobile first, each card
screenshot-ready (one claim, one picture, scope and credit, one phone screen) and shareable on its own.
Mockups with real data: the "Player profile, simplified" artifact (scratchpad build_mock.py).

## What the page is today (captured 3 Nov 2026, 390px, every section open)

* 18-23 phone screens; 13 sections under the verdict (At a glance, Overview, Impact, Global T20 Rank, DNA & Similar,
  Shot map, Performance, Matchups, Advanced Analytics, Boundaries, Dismissals/Wickets, Visualizations, Explore) plus a
  filter bar.
* Phase strike rates appear four times, pace v spin four times.
* Two windows on one page: the verdict is "since Jan 2024, strong sides", the sections below "Jan 2020 to today, all
  leagues".
* Bugs: Bumrah's line & length "Failed to load"; the DNA text calls leg-spin (LB) "left-arm bowling"; Global T20 Rank's
  6-month line is flat; bowling Advanced Analytics shows fantasy points and "Form: COLD".

## The new page

1. **Verdict** (exists): headline + standouts, wins added by season, peer ranks, phases, last 8. Its Format and
   Recent/Career switches set the window for the whole page.
2. **Plays like** (exists, slimmed): the four closest twins, comparisons one tap away.
3. **Role cards** (four each; an all-rounder gets both sets, the main role first, with a switch):
   * Batters: his start (typical runs after 10 balls), where he scores (shot map), against each bowling type (six
     plain families), how he gets out.
   * Bowlers: where he bowls (pitch map), by phase (economy, dots, false shots), right- v left-handers, how he takes
     wickets.
4. **Footer**: one "dig deeper in the query builder" link, credits.

Each card: kicker, claim title written from the numbers, one chart, a one-line scope + credit footer, a share button
(link to the card's anchor, with its own preview image later).

## Chunks

| # | Chunk | Status |
|---|---|---|
| P0 | Remove the cut sections, the filter bar and their now-unused components and endpoints calls; the page reads the verdict's window | [ ] |
| P1 | Card shell: kicker, claim title, chart slot, scope/credit footer, share button; one window/scope from the verdict switches | [ ] |
| P2 | Backend: one `/player/{name}/cards` endpoint (role cards' numbers for the verdict window, cached with the summary, warmed nightly) | [ ] |
| P3 | Batter cards: start, shot map (slimmed ShotMapSection), bowling families, how he gets out | [ ] |
| P4 | Bowler cards: pitch map (fix the load failure), by phase, right v left, how he takes wickets | [ ] |
| P5 | All-rounder: both sets, main role first, a switch; Plays like slimmed | [ ] |
| P6 | Per-card share: anchor links and a per-card preview image (api/og.mjs) | [ ] |
| P7 | Mobile review at 390px for a batter, bowler, all-rounder and a career-only player; CARTA check of every card | [ ] |
