# Query builder, rebuilt for the phone

The same treatment as the player, team and venue pages (PROFILE_SIMPLIFY_PLAN.md, TEAM_VENUE_PLAN.md), applied to
/query. Mobile first: a phone should go from a question to an answer it can read and share in one screen.

Status: **built** (5 Nov 2026, mockups signed off).

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
| Q0 | Mockups with real questions | [x] 5 Nov 2026: https://claude.ai/artifact/Ghw26ZwdmG6U5gkbxjjUC6, signed off |
| Q1 | Shell | [x] 5 Nov 2026: src/components/query2/QueryPage.jsx. Question bar first; T20/ODI pill (never "All formats"); suggestions from the next fixture; recent questions on the device; /query?nl= runs a question |
| Q2 | The answer | [x] 5 Nov 2026: answerShape.js picks the measure (rate by perspective, or the one the question names), the chart (line, pitch map, ranked list, bars, tiles) and the sentence; AnswerCard.jsx; "All columns" is the old results table |
| Q3 | Chips and filter sheet | [x] 5 Nov 2026: qbWords.js (chips in plain words, remove), FilterSheet.jsx (five groups, search, inline controls) |
| Q4 | Group-by chips and follow-up | [x] 5 Nov 2026: /nl2query/parse takes `context` (the query in words) and reads it with the follow-up as one question |
| Q5 | Share | [x] 5 Nov 2026: share menu (copy link, make a graphic with the old maker); /query?graphic=1 still opens it |
| Q6 | Cleanup and check | [x] 5 Nov 2026: QueryBuilder, QueryFilters, NLQueryInput and FormatSwitcher removed; checked at 390px (empty, by year, ranking, pitch map, filter sheet, plain English) |

## Decisions (user, 5 Nov 2026)

* **Results:** chart first, then the rows.
* **Filters:** behind "Add filter" everywhere, desktop included. The question bar and chips are the only entry.
* **Follow-up box:** built in this plan (Q4). The plain-English parser takes the current query as context.
