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
| Q7 | Dates on phones | [x] 14 Nov 2026: presets (Any time, This year, Since 2025/2024/2023, Pick dates) in FilterSheet.jsx; cleanDates drops a range starting today or later and turns a backwards one round; empty answer with dates shows "Try any time"; a one-day range reads "9 Nov 2026". Tests in __tests__/qbFixes.test.js; checked at 390px |
| Q8 | The title follows the query | [x] 14 Nov 2026: qbWords.questionAfterEdit drops `q` when a chip removal or the sheet changes the filters (a new grouping keeps it); followLabel keeps the first question and the latest follow-up only. Checked at 390px: Samson + "Since 2024" from the sheet clears the bar |
| Q9 | "Average score" questions | [x] 14 Nov 2026: no parser or API change. Delivery rows already carry innings_count (GT IPL 2026 powerplay: 984 runs, 17 innings in both modes), so answerShape has a runs_per_innings measure ("Runs an innings", runs incl. extras / innings; lower is better from the bowling side), measureAsked() picks it from the words ("average score/total", "runs per innings"), and a follow-up keeps the measure in use. Also fixed: a query with no grouping (/query?batters=Sanju+Samson, where site search lands) showed "Nothing matched" because the API returns raw balls; the page now asks for group_by=format, one totals row, keeping the URL ungrouped. Checked at 390px |
| Q10 | Hamilton's old names | [x] 14 Nov 2026: both map to Seddon Park, Hamilton in venue_standardization.py; get_venue_aliases lists all four. Goldens: the venue list is one shorter (269 -> 268); the other diffs are the local data drift already seen before this change |
| Q11 | Bot questions out of the counts | [x] 14 Nov 2026: usage_report._URL_ASKER (no referrer, only /query?nl= or ?q= pages, no query run) leaves these ids out of people, and NL now counts nl_search events from people instead of every nl_query_log row (week of 2 Nov: 22 -> 17). The cache part was dropped: it's in memory and resets on deploy, and the bot costs ~5 model calls in three weeks |

## Fixes from the first week of use (14 Nov 2026)

Read from `app_events` (event `query_run`), `nl_query_log` and `mcp_call_log`, 2–14 Nov. Already fixed before
this review, so not chunks here: SMAT and the other leagues dropped by the parser, invented home grounds, conditions
it couldn't apply shown as "Couldn't apply: …" (#319, live 12 Nov). The Wellington names work: "Hnry Stadium" since
2023 returns pace 1,385 balls and spin 380 today.

**Q7: dates on phones.** On 9 and 11 Nov two sessions ended up with `start_date` = `end_date` = that day
(Gurjapneet Singh, Rovman Powell), so the answer covered one day and was empty. The cause is most likely the phone's
date picker: the From/To fields in `FilterSheet.jsx` are `type="date"`, and iOS fills in today when the picker is
opened and closed. Fix: presets first (Any time, This season, Since 2025, Since 2024, Since 2023, Pick dates), with the
two date fields only under "Pick dates"; and a range that ends today and starts today, or holds no matches, is shown
as "No matches between these dates" with a one-tap "Any time" instead of an empty card.
Check: at 390px, open and close each date field and confirm no filter is set.

**Q8: the title follows the query.** Chip removal, the group-by chips and the filter sheet's Apply all keep `q`
(`QueryPage.jsx`, the calls to `go(..., question, ...)`), so a card titled "Sanju Samson … Samson vs pace heavy sides"
went on to show Axar Patel, Dewald Brevis and Liam Livingstone. Follow-ups also add to the label each time
("A … B … C … D"). Fix: a filter or group-by changed by hand drops `q`, and the title falls back to the query in words
(`queryInWords`); a follow-up's label is the follow-up alone, with the earlier question kept only as parser context.
Check: ask, change the batter in the sheet, and confirm the title names the new batter.

**Q9: "average score" questions.** "Average scores in powerplay of all teams in IPL 2026" was asked three ways in two
minutes (13 Nov). The parser ran it as a delivery query grouped by batting team, which gives runs per wicket and strike
rate, not runs per innings. Fix: questions about a team's score per innings ("average score", "average total",
"how often do they pass 200") go to `query_mode='team_innings'`, which has the phase run rates and totals; add the case
to the parser's examples and to its tests. Check: the three phrasings return one row per IPL team with powerplay runs
per innings.

**Q10: Hamilton's old names.** `Westpac Park, Hamilton` and `WestpacTrust Park, Hamilton` (one ODI each, 2001 and
2003) are Seddon Park under its sponsors' names, but `venue_standardization.py` doesn't map them, so a Seddon Park
query misses those matches and the connector tried four names on 9 Nov. Fix: map both to `Seddon Park, Hamilton`.
(`National Stadium, Hamilton` is in Bermuda; leave it.) Check: `get_venue_aliases('Seddon Park, Hamilton')` lists
all four, and the regression goldens are unchanged.

**Q11: bot questions out of the counts.** `/query?nl=Grayscale` arrived five times since 27 Oct, each from a new id
with no referrer, from the US. It's a crawler, and it spends a model call each time. Fix: the usage report counts
plain-English questions from people only (the same rule as `people`), and the parse endpoint answers a repeat of a
question already in `nl_query_log` from the cache whatever the caller. Check: the week's NL count drops by the
Grayscale rows.

## Decisions (user, 5 Nov 2026)

* **Results:** chart first, then the rows.
* **Filters:** behind "Add filter" everywhere, desktop included. The question bar and chips are the only entry.
* **Follow-up box:** built in this plan (Q4). The plain-English parser takes the current query as context.
