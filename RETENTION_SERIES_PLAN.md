# IPL 2027 retention series

One IPL franchise a day, one consistent carousel each, until the retention deadline. Agreed with the user, 5 Nov 2026.

**Facts:**
- **Deadline:** Tuesday 17 Nov 2026 (moved from 15 Nov; the India v NZ ODIs end that day).
- **Retentions:** no cap on how many players a team keeps.
- **Auction:** 16 Dec, Goa.
- **Trades so far:**
  - Pant (LSG to DC) for Kuldeep (DC to LSG).
  - Natarajan (DC to SRH) for Zeeshan Ansari.
  - 5 Nov (CSK announcement): Liam Livingstone (₹6 cr) and Jack Edwards (₹3 cr) from SRH to CSK, for Khaleel Ahmed (₹4.8 cr) and Nathan Ellis (₹2 cr). The CSK post leads with it; the SRH post (10 Nov) gets it too (`NEWS` in the builder).

**Sources:** [Cricinfo](https://www.cricinfo.com/story/ipl-2027-retention-deadline-moved-to-november-17-1561149), [trade tracker](https://www.cricketnews.com/en/cricket/news/ipl-2027-trade-tracker-list-all-player-cash-deals-ipl-2027-mini-auction/6076978c3e37359b873c2e4a).

## Schedule (rescheduled 6 Nov: the big four go the weekend before the deadline)

| Date | Team | Why that day |
|---|---|---|
| Fri 6 Nov | SRH | The most settled squad after the window's trades (Natarajan in; Khaleel and Ellis for Livingstone and Edwards) |
| Sat 7 Nov | GT | Swapped in for DC: a settled squad (only a reported CSK interest in Sai Kishore) |
| Sun 8 Nov | LSG | The other side of the Pant–Kuldeep trade |
| Mon 9 Nov | RR | |
| Tue 10 Nov | PBKS | |
| Wed 11 Nov | Spare | |
| Thu 12 Nov | DC | Held: Axar (captain), Ashutosh and Rizvi in reported CSK talks (unconfirmed, 6 Nov). Axar is the big name |
| Fri 13 Nov | CSK | Big four |
| Sat 14 Nov | MI | Big four |
| Sun 15 Nov | RCB | Big four |
| Mon 16 Nov | KKR | Big four |
| Tue 17 Nov | Retention lists | What each team actually kept, against our cases |

**Before each post:** the user checks the template slide's role holders, since they check them by eye. Rebuild a
team's post the day before it goes out, so the latest trades are in.

The order of the six news-led days is re-checked each morning against the news (trades, reported releases).

## The format (every team, 8 slides, in the team's colours from src/utils/teamPalette.json)

**Window:** since the 2025 mega auction, meaning IPL 2025 and 2026.
- A player's numbers count from every IPL side he played for, so a traded player comes with his record.
- The squad is the 2026 squad (data/auction_raw/ipl/2026, 25 per team) adjusted for this window's trades.

**Measures (the user's choice):** Impact, runs above par (RAA) and wins added (WPA) lead every player's case.

**Voice:** the case for and against each player, not verdicts. Followers decide ("Who would you keep?").

| # | Slide | Content |
|---|---|---|
| 1 | Cover: squad board | Every player under his role (openers, middle order, finishers, pace, spin, all-rounders), with his wins added since the mega auction, shaded from the team colour (strong) to grey (below par). Hook: a player and a number. |
| 2 | Who carried them | Wins added and runs above par leaders, batting and bowling |
| 3 | Batting by role | Openers, middle order, finishers: runs above par per 100 balls and Impact per innings |
| 4 | Bowling by phase | Powerplay, middle, death: runs saved against par and wickets for each bowler |
| 5 | Value for money | Price paid (2026 squad price) against wins added, every player |
| 6 | The case for and against | Three players: one big name, one expensive underperformer, one bargain. Each gets his price, the number for him and the number against him. |
| 7 | Purse and gaps | Wage bill now, the money each of the three would free, and the side's weakest phases against the other IPL sides (the gaps to fill at the auction) |
| 8 | End | "Who would you keep?" |

**Every post also gets:**
- **A voiced Reel:** the cover chart under the hook, ending on "Who would you keep?".
- **An X thread:** hand-written, with #IPL2027 and the team's tag.

## Build

* `articles/ipl-retention/post.py --team CSK [--write]`: one builder, so all ten posts share the format; each team's
  news angle goes in as a line of copy.
* New post visuals: `squad_board` (the cover); `case_board` (slide 6), unless an existing visual fits.
* Pinned windows (end date 2026-10-31), so a rerun can't drift.
* Prices: 2026 squad prices from the auction file; traded players at their trade salary (web, the day before).

## Open checks

- **2027 purse and cap:** one report says a ₹157 crore total cap. Confirm from Cricinfo or IPL before the purse slide
  states it.
- **Each team's news:** check the morning of each post.
