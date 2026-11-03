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

Each card: its name as the title, one chart, a share button (link to the card's anchor, with its own preview image
later), and a short note only where it adds something ("15+ balls a cell", "run-outs not counted"). No site name,
link or data credit on cards, and no repeat of the page's window: the logo carries the brand and the data credit sits
once at the foot of the page (user, 3 Nov 2026).

## Decisions from the mockup review (user, 3 Nov 2026)

* The verdict is a list, one stat per line ("2nd of 339 for wins added", "2nd of 321 for boundary % v spin (33%)"),
  not a sentence. The backend keeps `verdict` for previews and adds the lines.
* Cards have no separate claim line: the card's name ("Plays like", "His start") is its title.
* Plays like: a lime chevron on each row opens that twin's comparison; no "tap for details" note.
* A gear beside the name opens the filters (format, period or custom dates, strong sides or every match,
  competitions), applied to the whole page.
* The start card is an interactive chart by ball of the innings: strike rate so far and on that ball; drag across to
  read each ball (strike rate, runs v par for the typical innings, innings still going).

* No sentence wraps at phone width (390px): the verdict is rank | short description rows ("2nd of 321 | Boundary %,
  v spin · 33%"); twins show two traits in short words; notes, legends and the page credit are one line each. P7 checks
  it with a text-line count at 390px, plus chart labels inside their charts.

## Chunks

| # | Chunk | Status |
|---|---|---|
| P0 | Remove the cut sections, the filter bar and their now-unused components and endpoints calls; the page reads the verdict's window | [ ] |
| P1 | Card shell: name as title, chart slot, scope/credit footer, share button; the gear's filters set one window/scope for the page; verdict as a list | [ ] |
| P2 | Backend: one `/player/{name}/cards` endpoint (role cards' numbers for the verdict window, cached with the summary, warmed nightly) | [ ] |
| P3 | Batter cards: start (interactive by-ball chart), shot map (slimmed ShotMapSection), bowling families, how he gets out | [ ] |
| P4 | Bowler cards: pitch map (fix the load failure), by phase, right v left, how he takes wickets | [ ] |
| P5 | All-rounder: both sets, main role first, a switch; Plays like slimmed | [ ] |
| P6 | Per-card share: anchor links and a per-card preview image (api/og.mjs) | [ ] |
| P7 | Mobile review at 390px for a batter, bowler, all-rounder and a career-only player; CARTA check of every card | [ ] |
