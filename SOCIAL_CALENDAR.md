# Social calendar: fixed dates

The daily queue (previews, recaps, On this day, trend radar) runs itself; see the admin page. This
file holds the dated moments that need planning ahead. Add a date only once it's confirmed, with
its source.

| Date | Event | Source | Status |
|---|---|---|---|
| 16 Dec 2026 | IPL 2027 auction, Goa | Cricinfo on X, seen 26 Oct 2026 | planning |
| Early 2027 | India v Australia Tests | user, 26 Oct 2026 (dates TBC) | needs Tests in the DB (MULTI_FORMAT_PLAN C0–C5) |

## IPL 2027 auction (16 Dec, Goa)

The auction is the strongest reason to have the verdict screen (VERDICT_SCREEN_PLAN.md) live
first. "Is he worth it?" is exactly the question it answers, and every pick becomes a link to a
profile.

* **Target:** V1–V7 of the verdict screen live by **9 Dec** (one week before), including share
  images, so links unfurl with the verdict.
* **Before (from retention day to 15 Dec):**
  * Each franchise's gaps, by phase and role, from its 2026 season (Impact / runs above par
    by phase).
  * "Best value in the pool": released players ranked by wins added since 2024 (strong-opposition
    pool).
  * Overseas all-rounders compared (the Jansen question, at scale).
* **On the day:** a verdict-screen card for each big buy within minutes, in a
  one-tweet + cards reply format (see tweet-reply-format).
* **After:** each squad's projected XI with phase coverage; "who overpaid" only with numbers,
  never blame framing.
* **Data gaps to close first:**
  * Past prices and retentions are covered (IPL 2018–2026, see "Auction data" below). Still needed:
    the 2027 retention lists and the live sold list on 16 Dec.
  * Confirm the retention deadline date before scheduling anything against it.

### Team-by-team arc (the user's plan, 26 Oct 2026)

Two series of 10 posts, one per franchise. Each post is a carousel plus a short X thread linking to
the team's page.

**Series 1: pre-auction previews.** Starts once the retention and release lists and the auction
pool are public. One team a day; the order follows purse size or the news cycle.
* What's kept: the retained core's verdict cards and the cost of each retention.
* What's missing: phase coverage for the retained squad, batting (powerplay / middle overs / death)
  and bowling, against a title-winning squad's profile. Also left/right balance, pace/spin, and
  overseas slots left.
* Purse left and slots to fill. The purse can be derived from retention prices and the IPL purse
  rules for the year (confirm the cap from the official announcement; don't guess).
* Who in the pool fits: the top 5 players for each gap, by wins added and runs above par in that
  phase (strong-opposition pool, verdict-screen numbers), with their last auction price.

**Series 2: post-auction squad evaluations.** In the 10 days after 16 Dec, one team a day.
* The squad's construction: the projected XI + impact player, phase coverage before and after the
  auction, depth (who covers if the first choice is out), overseas mix.
* What they paid for what: wins added since 2024 per crore spent, against the other 9 teams.
* Did they fill the gaps named in Series 1? Score it on the same chart as the preview, for
  continuity. Use numbers and fit, not blame.

**Builds needed:** a squad-level "phase coverage" visual (one chart reused in both series), the
auction tables (A1–A2 below), the IPL 2027 squad lists (retentions + buys), and the verdict screen's
numbers by player id. These need to be in place by the retention announcement date (TBC).

## Auction data (inventory, 26 Oct 2026)

Local copy: `data/auction_raw/` (gitignored, 2.8 MB). Source: the user's Dropbox `auction_data`
folder, scraped from Cricbuzz's auction pages.

| Set | Years | Rows | Notes |
|---|---|---|---|
| IPL | 2018–2026 | 250–400 per year | sold / unsold / retained / RTM / traded, with base and final price |
| IPL | 2008–2017 | 20 per year | **truncated**; looks like a top-20 only, so don't use for history |
| The Hundred, men + women | 2026 | 140 / 132 | sold / unsold / drafted / retained |
| WPL | 2023–2026 | 135–150 per year | we hold no women's ball-by-ball, so this is prices only |

* `completed_all_players.csv`: Cricbuzz `playerId`, name, country, role, capped/uncapped,
  overseas, base price, final price ("2.00 Cr" / "30.00 L" strings), team, status. `season`
  `ipl-2026` is the auction held in Dec 2025.
* `completed_trail.csv`: the **bid-by-bid trail** (team, price per bid). For example, Cameron Green
  2026 had 117 bids across KKR, CSK, RR and MI. Check the `seq` order before using it, because the
  last row shows 2.00 Cr.
* The ids are Cricbuzz's, not the ESPNcricinfo ids we use, so a name/id mapping table is needed
  (see PLAYER_IDS_PLAN.md).
* Use the facts (prices, teams, statuses). Don't republish Cricbuzz's `playerIntro` text or images.

### Uses
1. **Wins added per crore:** each 2026 buy's wins added in IPL 2026 against its price; a scatter of
   price v wins added by team ("who got value"), and the same for retentions.
2. **Did the price predict the season?** 2018–2025: price against next-season wins added and
   Impact, by role. A good long-form piece.
3. **Bidding wars:** the trail as a step chart of price against bid number, coloured by team,
   for the biggest fights (Green 2026). This is new visual material for Reels.
4. **Verdict screen:** an "IPL auction history" row (year, team, price, status) below the fold;
   on auction day, the verdict card for each buy carries its price.
5. **Before the 16 Dec auction:** released players' verdicts ranked by wins added, with their last
   price, as a "value in the pool" list.

### Work needed (fold into VERDICT_SCREEN_PLAN or its own chunk)
* A1: parse prices to lakhs, verify trail order, load into an `auction_lots` + `auction_bids`
  table (local first).
* A2: map Cricbuzz ids to our player ids (names + country + role; a manual list for the misses).
* A3: `/player/{name}/auctions` endpoint, plus the price v wins-added query for posts.
* A4: scrape or enter the 2027 auction live on 16 Dec (the same scraper the user already has?).
