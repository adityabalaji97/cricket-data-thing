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

## Post ideas backlog (undated)

Ideas agreed in conversation but not yet scheduled. A pitch source for the morning brief (PITCH_BRIEF_PLAN.md P3).
Add the date each came up; strike one through when it posts.

| # | Idea | What it shows | Ready? | Came up |
|---|---|---|---|---|
| 1 | **The T20 standard field** | The field our model sets for the average batter, by phase × pace/spin × hand: nine fielders with coverage circles, as the broadcasts draw them. Labelled as a model built from where the ball goes, not real fielding positions. Optional extra: the few batters who stayed outliers in both periods (Suryakumar v middle-overs spin, Pollard v death pace, Johnson Charles v powerplay pace). Don't present the gap index as a ranking (it barely repeats). | Solver built: `services/field_model.py`, `articles/fields/prototype.py` (branch field-coverage, unmerged). Needs a card design. | 7 Nov 2026 |
| 2 | **Oddly specific outliers** (a series) | Players unusually good or bad at one narrow thing, each against the typical player where they played. Seeds: **Babar Azam** bowled or LBW on 39% of dismissals v 25% typical (LBW 21% v 7%), and 13 of his 26 dismissals to spin since 2024; Suryakumar 11% v 21% (out caught when out); Varun attacks the stumps less than the typical spinner (25% v 35%) but bowls batters 31% of the time v 20%. Find more by ranking the profile cards' "v typical" numbers that hold in both periods. | Numbers come from the profile cards (`services/wicket_style.py`) and `scripts/analysis/{batter_bowled,stumps_attack}.py`. Check each seed repeats across periods before posting. | 7 Nov 2026 |
| 3 | **Stump-hunters** | How bowlers take wickets: Thushara and Shaheen (bowled or LBW well above typical, attack the stumps most) v Hardik, Mustafizur and Muzarabani (cutters and the short ball, caught). Or wrist-spinners (Rashid, Tahir, Zampa, Noor) v finger-spinners. Style, not quality: it doesn't predict economy. | Same data as #2. | 7 Nov 2026 |
| 4 | **Profile showcases** (batter, bowler, all-rounder) | One player each, a carousel that walks through his profile cards (verdict, plays like, where he scores or bowls, pace map, shot mix, how he gets out or takes wickets) to show the breadth and depth of the data and visuals. Pick players in the news. | Profile cards are live; needs a carousel builder that renders the profile's cards as slides. | 7 Nov 2026 |
| 5 | **India's lower order (bat and ball, 5-8)** | Already agreed, held until the NZ v IND T20Is end (memory: india-lower-order-post). | Analysis done; branch post/india-lower-order. | Oct 2026 |
| 6 | **How to bowl to X / how to bat against X** | The scouting templates as posts (pitch map, wheel, shot mix, what works against him), news-led (Livingstone, Noor). | `articles/scouting/build.py` (branch scouting-templates, unmerged); swap "the fielder who matters" for descriptive wording first. | 7 Nov 2026 |
| 7 | **The winners' template** | What IPL playoff sides have that others don't: openers who last, powerplay average, boundary scoring at 5-7, middle-overs spin wickets, death economy, six regular bowlers, fewer players used. A one-off explainer (the retention posts use it per team). | `TEAM_TEMPLATE_IPL_FINDINGS.md`, `services/pinned/team_template_IPL.json`. | 6 Nov 2026 |
| 8 | **Tier lists** (a slow-news-day series, team by team) | A side's players in one role or phase since a set year (CSK's Indian pacers since 2018; India's openers; RCB's death bowlers), placed in tiers by wins added, runs above par and Impact, the fan format that already travels on X (@AbhiMSD__07's CSK pacer tiers, 13 Nov). Leagues and internationals. Tiers from the numbers, not taste: cut points stated (e.g. by runs above par per 100 balls), a sample floor, and a "too little to judge" row instead of a verdict. Career looks back, so the no-repeat caveat matters less; still no blame: rank the role's output, not the person. Visual: tier rows (the label states the cut, e.g. "+1.0 wins and up"), each player an Impact Pyramid card (https://claude.ai/artifact/LFpcAGFw7jRMFoeSUMkJQi): team-colour fill, small first name, big uppercase surname in the display face, the number in mono, one detail line (overs/balls, seasons); the top card gets the lime ring; on a one-team list the bottom accent strip carries the tier (brighter up top). No photos, no legend, one-line header and footer (post-design feedback). | Numbers: query builder grouped by player with team + phase/role filters; needs a `tier_board` post visual. | 13 Nov 2026 |
