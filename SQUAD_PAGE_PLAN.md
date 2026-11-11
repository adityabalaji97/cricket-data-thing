# Squad section on team pages

The daily IPL retention posts become a permanent, updating part of each team's page. Agreed with the user, 10 Nov 2026
(content strategy: every post points to a page that lasts). Time-critical: retention lists 17 Nov, auction 16 Dec.

## Why

- Each retention post is built once and goes stale with the next trade. The team page is where it should live.
- The last tweet of each thread already links to `/team?team=...`; the page should show what the post showed.
- The team page's "top players" covers the last three seasons, so players long gone appear (Boult for RR, Nov 2026).

## What the page gets (IPL sides first)

A **Squad** group on `/team`, below the existing cards, following the profile rules (title is the card's name, one
picture, one-line note, nothing wraps at 390px, labels inside the chart, share icon):

| Card | Picture | From |
|---|---|---|
| Squad | Every player under his role with wins added, shaded in the team colour; traded in / reported moves marked | the post's slide 1 |
| Against the winners' template | Seven role rows: this squad's place among IPL sides against where playoff sides sit | slide 7 (TEAM_TEMPLATE_PLAN T5) |
| Price v wins added | Scatter, every player | slide 5 |
| Three calls | Big name, big price, bargain: the number for and the number against each | slide 6 |

"As of" date and the status of each move ("confirmed", "agreed, awaiting BCCI ratification") in the note.

## Chunks

| # | Chunk | Output |
|---|---|---|
| Q0 | **Squads in the database.** Today they live in the post builder (auction CSV + a `TRADES` list). Move to data: 2026 squads from `auction_lots` (already loaded) plus a `squad_moves` table (player, from, to, price, status confirmed/reported, source, date). One function returns a team's squad as of a date. | `services/ipl_squads.py`, migration, tests |
| Q1 | **One build, two outputs.** Lift `build()` out of `articles/ipl-retention/post.py` into a service the post and the page both call, so their numbers can't differ. Includes the name matcher (`services/name_match.py`) and the small-sample flags. | `services/squad_view.py`; the post builder imports it |
| Q2 | **Endpoint.** `GET /team-squad?team=`: the four cards' data, cached per team and day; invalidated when `squad_moves` changes. | route + cache |
| Q3 | **Cards on the team page.** The four cards above; the existing slide components (`squad_board`, `template_board`, `scatter_plus`, `case_board`) reused where they fit 390px, redrawn where they don't. | `TeamPage.jsx` cards, phone screenshots |
| Q4 | **Current squad everywhere.** "Top players" on the team page and the link-preview card use the current squad's players (their numbers at any side), not the franchise's last three seasons. | `services/team_page.py`, `api/_lib/share.mjs` |
| Q5 | **17 Nov: retained and released.** Each player gets a state (retained, released). The page shows the retained squad, the purse left and "gaps to fill" (template roles short of playoff level). The post for that day links here. | state on `squad_moves`, cards updated |
| Q6 | **16 Dec: auction day.** New buys appear with their price and auction card; the template grade recomputes. | loader for 2027 lots |

## Order and size

Q0–Q3 before 17 Nov (the pages exist when the lists land); Q4 with them if small; Q5 on the day; Q6 in December.

## Open

- Non-IPL sides: internationals get the India XI plan (INDIA_XI_PLAN.md); other leagues later.
- The unmerged retention-builder fixes (branch `post/lsg-retention`: name matching, bargain rule, trade lead, title
  lengths) merge first; Q1 builds on them.
