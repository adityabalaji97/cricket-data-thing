# Query builder, rebuilt for the phone

The same treatment as the player, team and venue pages (PROFILE_SIMPLIFY_PLAN.md, TEAM_VENUE_PLAN.md), applied to
/query. Mobile first: a phone should go from a question to an answer it can read and share in one screen.

Status: **draft for the user's sign-off** (5 Nov 2026). Mockups with real queries come next.

## What it is today (captured 5 Nov 2026, 390px)

**How it's used (60 days):**
- **Plain-English questions:** 270, from 57 visitors. This is the main way in.
  - Examples: "Kusal Mendis middle overs"; "Hagley Oval 2nd innings over 7 to 15 bowler type stats"; "Rohit Sharma ODI
    powerplay strike rate by year since 2019".
- **Filter runs:** 64, from 15 people.
  - Most common group-bys: batter (18), partnership (7), year (5), length x country (4).
- **Shares and graphics:** 1 share and 5 graphics.

**The page on a phone:**
1. **Before any data:** two screens.
   - First a plain-English search card.
   - Then a collapsed "Filters & Grouping" panel and a disabled "Execute query" button.
   - Then "No results yet".
2. **The filters:** about 30 controls in one flat list. Labels are the database's ("Bowl Kind", "Is Chase", "Shot
   Control", "Group By Columns", "Show Summary Rows").
   - It also has six min/max thresholds, a row limit and a "top teams" slider.
3. **Format:** the default is **All formats**, which mixes T20s and ODIs. Kohli's numbers by phase looked wrong in the
   audit for exactly this reason.
4. **Results:**
   - A paragraph of metric definitions comes first.
   - Then a table five rows to a page, wider than the screen, with raw column names ("bowl_kind").
   - "Applied filters" comes after the table, collapsed.
   - The chart is last, about three screens down.
5. **Sharing a result:** done through a separate "Make a Graphic" page.

## The new page

1. **One question bar at the top**, the page's whole first screen:
   - "Ask anything" in plain English, with three suggestion chips about today: the current fixture's players and
     grounds, and recent posts.
   - A format pill (T20 / ODI) that defaults to the site's format, never "All formats".
2. **The answer, first:**
   - One sentence that reads the top of the result ("Kohli scores at 111 against spin this year, from 85").
   - Then **one chart picked to fit the result's shape**, reusing the post visuals:
     - year or season: a line;
     - line x length: a pitch map;
     - wagon zone: a scoring wheel;
     - phase or bowling type: bars;
     - batter or bowler rankings: a ranked list.
   - Then the rows.
3. **The rows, for a phone:**
   - A compact ranked list: each row shows its label, the measure the question asked for, and two context numbers.
   - Tap a row to expand all its columns.
   - Sort by tapping a measure chip.
   - The full table stays one tap away ("All columns"), with a sticky first column, for desktop and power use.
4. **What was asked, as chips:**
   - "Virat Kohli · since 2024 · v spin · by year". Each chip opens its filter, and an x removes it.
   - "Add filter" opens a bottom sheet with five plain groups:
     - **Who:** batters, bowlers, teams.
     - **Where and when:** dates, venue, competitions.
     - **Match situation:** innings, chasing, result, toss.
     - **The ball:** pace or spin, bowling type, line, length, shot, control, scoring zone.
     - **Show:** group by and sort, plus minimum balls.
   - Each group has a search box, and the labels are plain words.
5. **Group-by as quick chips**: by year, phase, bowling type, line and length, scoring zone, venue, batter, bowler.
6. **A follow-up box under the answer** ("…and in the powerplay?"). It refines the current query rather than
   starting over.
7. **One share button** that makes the graphic from the answer card (Make a Graphic folded in) and copies the link.
8. **Recent questions**, kept on the device, shown under the bar when it's empty.

**Not changing:**
- the query engine and its API (`/query/deliveries`);
- shareable URLs (old links keep working);
- the connector.

## Chunks

| # | Chunk | Status |
|---|---|---|
| Q0 | Mockups with real questions (Kohli v spin since 2023; IPL 2026 death bowlers by economy; Bumrah line and length) for sign-off | [ ] |
| Q1 | Shell: question bar first, format pill defaulting to the site's format, suggestion and recent chips; old filter panel behind "Add filter" | [ ] |
| Q2 | The answer: summary sentence from the result, chart chosen by group-by (post visuals), compact ranked rows, "All columns" table | [ ] |
| Q3 | Query chips and the filter bottom sheet (five groups, plain labels, search) | [ ] |
| Q4 | Group-by quick chips; follow-up box (plain-English refinement with the current query as context) | [ ] |
| Q5 | Share: graphic from the answer card plus link; /graphics kept for its gallery | [ ] |
| Q6 | Remove unused components; 390px one-line check on 6 queries; regression goldens for /query/deliveries unchanged | [ ] |

## Open questions

1. Should the results open on the **chart first** (proposed) or the rows first?
2. Should the plain-English bar be the only entry, with filters only behind "Add filter" (proposed), or should the
   filters stay visible on desktop?
3. Is the follow-up box (Q4) in scope now, or later? It needs a change to the plain-English parser (passing the
   current query as context).
