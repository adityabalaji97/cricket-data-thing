# Landing build log

Builder log for LANDING_PLAN.md (the plan lives untracked in the main checkout). One entry per chunk.
Screenshots are in `docs/landing_review/build/` in this worktree (not committed: they are review aids).
Local setup: front end on :3001 against the local API on :8000 through a CORS shim on :8001 (the API only allows
:3000); headless Chrome via CDP at 390x844, 360x800 and 1440x900.

## L5: credits and small breakages

Files: `src/components/LandingPage.jsx`, `src/data/iplSchedule.js`, `src/App.test.js`.

- Credits: "Data sources" now leads with "Ball-by-ball tracking: Himanish Ganjoo & TechRadar" (links to
  x.com/himganj153), then Cricsheet and Cricmetric under "Scorecards and match data". Inspiration handle
  `@hganjoo_153` is now `@himganj153`.
- Duplicate "06": the kickers lost their numbers ("01 / Today" -> "Today" etc.). Sections are about to move
  (L1, L4, L7), and numbered kickers drift every time one does.
- "No match today" only once the fixtures are in: the subtitle is a blank line while loading (keeps the header's
  height), nothing on error or when there are no fixtures.
- Loading card at the real height: the fixture card is 280px (measured 279.7 at 390 and 1440), so the fixture
  loader and the card's `minHeight` share `FIXTURE_CARD_HEIGHT = 280`. No jump on arrival.
- Series chip: wraps to two lines (line clamp) instead of clipping at "INT..."; the status beside it wraps too and
  is capped at 58% so a long live status ("MI Emirates won toss & batted") can't squeeze the chip.
- Errors with retry: `fetchUpcomingMatches` now throws on a failed request (its only caller is the landing page)
  so "no fixtures" and "couldn't load" differ. Fixtures, recent matches, standout innings and ELO each show
  "Couldn't load ..." with a 44px "Try again" that refetches.
- Phone checks: every 11px label on the page is now 12px (the only sub-12px text left is the app's bottom nav,
  not this page); buttons, dropdowns, carousel arrows and the top icons went 42/38px -> 44px; "All notes" link
  44px tall; credit links and chips 36px.
- `src/App.test.js` was already failing on main (axios ESM, no FormatProvider, stale menu labels from the 5 Nov
  overhaul). Fixed: axios mocked, FormatProvider wrapper, useLocation in the router mock; asserts the new
  credits; new test: a 503 on fixtures shows the error, never "No match today", and "Try again" recovers.

Checked: 390 / 360 no horizontal scroll; error state with fixtures and innings blocked; `npm run build`;
`src/App.test.js` passes (2 tests). `FantasyPlanner.test.jsx` fails on main too, untouched.
Screenshots: `before_390.png`, `l5_390.png` (full page), `l5_360_top.png`, `l5_error_390.png`,
`l5_credits_390.png`.
Open: the team-code links inside fixture/recent cards stay 32px tall (inline in a dense card).

## L3: notes dated, played previews hidden

Files: `src/components/LandingPage.jsx`, new `src/utils/noteDates.js` + `src/utils/__tests__/noteDates.test.js`.

- Each note's kicker reads "MATCH RECAP · 1 OCT" (publish date in IST; the year appears outside the current year).
- A preview drops off once its match is over. The notes API has no match date, so the start is read from the dek
  that `services/note_drafts.py` writes ("Fri 2 Oct, 05:30 IST (00:00 GMT)"), the year from the publish date (Dec
  publish, Jan match -> next year). "Over" = start + 5h for a T20, + 10h for an ODI (raised from 4h/9h after review). A preview whose dek has no
  start (hand-written) stays: front end only, no API change.
- Fetches 8 and shows the first 3 left, so hiding previews doesn't empty the row.

Checked: unit tests (5) and App.test pass; local data's 2 Oct preview is hidden, the three notes left are dated.
Screenshot: `l3_notes_390.png` (cover images are broken only locally: the dev server doesn't serve /img).
Open: hand-written previews with a different dek format never expire; a `match_date` on the notes API would
make this exact (small backend change, not done).

## Review fixes (L5, L3)

- L5: the loading subtitle is now the explicit escape `' '` (it was already a literal NBSP byte, which read as
  a space in review; the escape makes it unambiguous). 44px: credit links and chips, the connector Copy button,
  the league counts "Show all", the top-bar logo link. Recent-match tiles: team-name and result links are 44px
  (tiles grow ~30px). Credit links now go to x.com (all of them, for one host).
- L3: a Dec match previewed in Jan gets the previous year (test added); the date label compares IST years;
  margins 5h (T20) / 10h (ODI).
- Still under 44px: the fixture card's team codes (32px, "GG"/"MIE"): raising them grows the 280px card.

## L4: two screens cut

Files: `src/components/LandingPage.jsx`, new `src/components/pages/ConnectPage.jsx`, `src/App.js`, `src/navItems.js`,
`vercel.json`, `src/components/CreditsPage.jsx`.

- League Match Counts: `showLeagueCounts` now defaults to false (LandingPage and the section); nothing in the app
  passes it, so it's off the public page. The component stays for a caller that wants it.
- Connector block: `ConnectorSection` is exported and rendered by a new `/connect` page (title "Connect" in the
  app header). Its hash-scroll effect is gone. The landing page keeps one 67px row, "Ask Hindsight from Claude or
  ChatGPT ›", linking to /connect. `/#connector` redirects to `/connect` (replace) on the client, and vercel.json's
  browser rule for `/mcp` now 302s to `/connect` instead of `/#connector`. (A config change, not an API one; the
  crawler rule for /mcp is unchanged.)
- Credits: labels fixed against CreditsPage: Himanish Ganjoo & TechRadar = ball-by-ball tracking, Cricsheet =
  scorecards, Cricmetric = player information. `/credits` (CreditsPage) also had `@hganjoo_153` twice and no
  Himanish/TechRadar data credit: both fixed there too.

Checked: /#connector lands on /connect; /connect at 390 has no horizontal scroll; landing at 390 went from 5,580px
to 4,597px tall; build; App.test + noteDates tests.
Screenshots: `l4_390.png` (full page), `l4_connect_390.png`, `l4_connectrow_390.png`, `l5fix_390.png`.

## Review follow-ups folded into L8's commit

- `/connect` share card: `api/_lib/share.mjs` `summarize()` has a `/connect` text card ("Ask Hindsight from Claude or
  ChatGPT"), and vercel.json's crawler route list includes `connect`.
- `CreditsPage.jsx`: all twitter.com links are x.com.
- Pending (with L6): move `ConnectorSection` + `SectionHeader` into `src/components/connect/ConnectorSection.jsx` so
  `/connect` stops importing the landing page.

## L8: `/` and `/links` as one idea

Files: `src/components/ig/IgLinks.jsx`, new `src/brand.js`, `src/components/pages/TeamSquad.jsx`.

- One tagline: `src/brand.js` exports `TAGLINE = 'Hindsight shows you why'` and the one-line promise; /links uses
  them now and L1 will on the home page. /links' old "Ball-by-ball data that settles cricket debates" is gone.
- One logo: /links now shows the site's logo and wordmark (`/cricket-icon.svg` + "Hindsight", as the home top bar,
  the app header, the favicon and the mockup do), linking home. **Assumed**: the bat-h mark
  (`/brand/hindsight-mark.svg`, the Instagram avatar) was the odd one out on the site, so /links joined the site
  rather than the site joining the avatar. If the owner wants the bat-h mark everywhere, that's a site-wide swap.
- Current posts: "Latest posts" (the carousels marked posted) now comes first, each with its date. It's still empty
  until posts are marked posted (OWNER_TODO; locally it's empty too). So the page is never stale without them, a
  "Latest notes" block follows (dated, played previews hidden, as on the home page). Order: header, posts, next match
  (India first), notes, then Explore: ask, 19-0, daily games (/games, not guess-innings), "Everything else" (home).
- The next-match preview link now carries `fmt=mens-odi` for ODIs (it opened ODIs in T20 before).
- utm tagging keeps a `#hash` at the end (a tagged `/team?team=MI#squad` stays an anchor).
- Tap targets: Instagram / YouTube links are 44px tall (were 13px text).
- `#squad`: the squad block on /team has `id="squad"`; since the squad loads after the page (TeamPage's own hash
  scroll runs too early), TeamSquad scrolls itself once its cards arrive. `/team?team=MI#squad` lands on the squad
  (checked: block at 72px from the top under the app bar). Nothing generates these links yet: the social builders
  don't link team pages, so it's for hand-written Reel/X copy.

Checked: /links at 390 (no horizontal scroll, only sub-12px text is the app's bottom nav); #squad; build; tests.
Screenshots: `l8_links_390.png`, `l8_squad_390.png`.
Open: the posts grid couldn't be checked with real posts locally (none marked posted).

## L1: promise and ask box above everything

Files: new `src/components/landing/AskHero.jsx` + `src/components/landing/__tests__/askExamples.test.js`,
`src/components/LandingPage.jsx`, `src/App.test.js`.

- Above Today's Matches: "Cricket, ball by ball. **Hindsight shows you why.**" (TAGLINE from `src/brand.js`, lime),
  the promise line under it, then the ask box: 54px, lime border, a 44px lime go button. Submitting goes to
  `/query?nl=<question>`, as the header search's fallback does (checked: "Kohli vs spin" ->
  `/query?nl=Kohli+vs+spin&fmt=mens-t20`). Tracks `landing_ask` / `landing_example`.
- Two example chips (44px) from real recent questions: `GET /query-recent` (already public: the query builder's
  "Recently asked"). A chip opens the stored parsed query (`/query?...`), so it costs no model call. Filter: 12-40
  characters, no "…" trails, starts with a capital, no lower-cased team names ("India vs australia" is quick
  typing), and no chip that's another with a year added. Fewer than two qualify -> the curated pair "Rinku Singh vs
  pace" / "Jurel vs Buttler, by phase" (the mockup's). Today's local picks: "Shubman Gill in ODIs since 2024 by
  phase", "Hnry Stadium: pace or spin since 2023".
- One lime action: the fixture card's "Match Preview" and the recent tiles' "Scorecard" are now outlined (lime text,
  faint lime border); the desktop Explore button is outlined too. (The header SearchBar's own "Search" button on
  desktop is still lime-ish; it's a shared component, untouched.)
- The home page sets `document.title` to "Hindsight · Hindsight shows you why" (pages set their own titles, and
  coming back home kept theirs).

Checked: 390, 360, 1440 (no horizontal scroll; at 390 the hero, ask box and chips fit above the first fixture card);
App.test asserts the tagline, the search box and the fallback chip; 3 unit tests for the chip picker; build.
Screenshots: `l1_390.png`, `l1_360.png`, `l1_1440.png`.
Open: the chips' "real recent questions" are whatever visitors typed last; the filter keeps out the obvious junk,
but an odd one can still show. A hand-kept list is the alternative.

## L8 review fixes

Files: `src/components/ig/IgLinks.jsx`, `public/index.html`, `api/_lib/share.mjs`.

- /links drops posts planned more than 14 days ago (client-side; the endpoint is unchanged). In prod the list ends
  21 Oct, so today "Latest notes" leads /links until posts are marked posted again.
- /links tab title is just TAGLINE ("Hindsight shows you why").
- The fallback head (`public/index.html`): title and og/twitter titles "Hindsight · Hindsight shows you why";
  description, og:description and twitter:description "Hindsight shows you why. Every ball of men's T20s and
  ODIs, answered in plain words." No more "T20 Cricket Analytics" / "2025 Wrapped". og/twitter image moved from
  the SVG (which most unfurlers ignore) to the absolute `/_og?path=%2F` card.
- `api/_lib/share.mjs` DEFAULT_TITLE / DEFAULT_DESCRIPTION carry the same tagline (the crawler head for every page
  without its own summary, and the home card's text). The share image headline "Who really won the match?" stays.
- Still assumed: the logo on /links is the site's `cricket-icon.svg`, not the bat-h mark.

## L1 review fixes

Files: `src/components/landing/AskHero.jsx`, `src/components/landing/__tests__/askExamples.test.js`, `src/App.test.js`.

- The chips no longer read `/query-recent` (visitor text on the most-viewed spot; and stored queries can be wrong:
  "Shubman Gill in ODIs since 2024 by phase" was stored grouped by wagon zone). `EXAMPLES` is a hand-kept list of six,
  each a label plus a stored `/query?...` (label as `q=`), two a day by IST date, cycling over three days. A tap never
  calls the model (no `nl=`; a unit test checks every entry).
- The six, each checked by rendering its URL in the local app (screenshots `l1fix_chip1..6.png`):
  1. Rinku Singh vs pace: by year, "strike rate 161 in 2026, from 157 in 2024".
  2. Jurel vs Buttler, by phase: batter x phase, six rows.
  3. Sanju Samson vs pace: by year.
  4. Tilak Varma at the death, by length: overs 16-20 by length.
  5. Shubman Gill since 2024, by phase: T20, three phases.
  6. New Zealand bowling at the death since 2024: overs 16-20 by bowler, Boult cheapest.
  Sources: 1-3 are the Fable review's picks (from the production log), 4-6 are questions in the query log
  (5 Nov), rewritten to the query they asked for. The ODI versions (Gill in ODIs, India v Australia in ODIs) were
  dropped: the local DB's ODIs are too thin to check them.
- **Owner: curate this list** (`EXAMPLES` in AskHero.jsx): swap in questions you want showcased; keep each URL
  checked.
- Placeholder: "Ask anything about a player, phase or matchup" (no longer repeats a chip).

## L2: one rating, the team page's

Files: new `src/components/landing/TeamRatings.jsx` + `src/components/landing/__tests__/teamRatings.test.js`,
`src/components/LandingPage.jsx` (old `EloSection`/`EloRow`, the range dropdown and `dateInput` removed),
`src/App.test.js`.

- Root cause of "Mumbai 6th at 1546 here, 9th at 1468 on the team page": the IPL is stored under two competition
  names, "Indian Premier League" to 2025 and "IPL" from 2026. `/teams/elo-rankings?league=Indian Premier League`
  never saw a 2026 match, so every side sat at its 2025 rating (locally: MI 4th at 1528 vs the team page's 9th at
  1456). Front-end fix: fetch both league names and keep each side at its latest match. Locally the list now has
  MI 9th at 1456, matching `/team-page?team=MI` exactly (rating.now 1456, rank 9 of 10). The order matches the
  mockup's (RCB, SRH/GT, ... LSG). **Backend note**: the endpoint itself still splits the IPL; anything else that
  calls it with one league name has the same bug (worth a small normalisation later; not done: front end only).
- Current franchises only: merged by code (Bangalore/Bengaluru, Kings XI/Punjab Kings, Daredevils/Capitals count
  once, at the latest), filtered to the ten current sides (Rising Pune, Kochi, Gujarat Lions, Pune Warriors gone).
  International: the top 12 (the team page's peers), with proper codes (IND, SA, NZ, WI...) and the country name
  for the team page link.
- One number a row: rank, code, a dot on one shared scale (lowest to highest rating, team colour), the rating.
  W-L and win % gone; "K-FACTOR 32 - TOP 10" gone; the range dropdown gone (a window only changed which "latest"
  was picked). An IPL / T20Is toggle (44px tabs) stays.
- Card anatomy: claim ("Royal Challengers Bengaluru are the top-rated IPL side. Lucknow Super Giants are 10th of
  10."), picture (the dot scale), scope ("Elo rating after each side's latest IPL match, to 31 May 2026. The same
  rating as each team page; tap a side for its page."), credit ("hindsightcricket.com · Data: Himanish Ganjoo &
  TechRadar, Cricsheet", as on the mockup). Each row is a 44px link to the team page.
- Loading and error states keep the card's height; error has Try again.
- Built as a card component so L7 can lift it into the lead slot.

Checked: 390, 360, 1440; T20Is view (12 sides); 3 unit tests (merge/rename/defunct, intl codes, claim); App.test;
build. Screenshots: `l2_390.png`, `l2_intl_360.png`, `l2_1440.png`.
Open: the dot scale runs from the lowest to the highest rating, so the last side always sits at the left end.

## L7: the lead card, the fixture row, games below

Files: new `src/components/landing/LeadCard.jsx` + `__tests__/leadCard.test.js`, `src/components/landing/TeamRatings.jsx`,
`src/components/landing/AskHero.jsx` (placeholder), `src/components/LandingPage.jsx`.

- Page order now: top bar, promise + ask box (L1), **lead card**, the fixture (a row), Play (19-0 + All games), latest
  notes, recent matches, standout innings, (ratings only when a post leads), connector row, credits.
- Lead card (decided: automatic with a hand-pick override): the override is the day's post, an IG carousel planned
  for today (IST) and marked posted (`/snapshots/ig/recent`): slide 1, its title, "All N slides ›", credit. Without
  one: the ten IPL sides' ratings (L2's card), tied to the calendar. Until 16 Dec the kicker is
  "IPL 2027 · auction 16 Dec" ("auction today" on the day) and the claim reads "Bengaluru go into the auction as the
  top-rated side. Lucknow are 10th of 10." (cities, as people say them); after it, "IPL team ratings" with the plain
  claim. "All squads ›" goes to /team. When a post leads, the ratings card still shows lower down; when the
  ratings lead, it isn't repeated.
- Fixtures (decided: shrink to a row unless India or a major league plays): `isHeadline` = India in the match, or
  the series matches the existing BIG_SERIES list (IPL, World Cup, Asia Cup, Champions Trophy, BBL, PSL, SA20, CPL,
  the Hundred, MLC). Otherwise one 56px row: start time (or LIVE in red), "GG v MIE", "T20, <place>", "Preview ›",
  the whole row a link to the preview; "N more fixtures ›" (44px) expands to the old cards. Headline days keep the
  cards. Loading shows a row-height loader (so a headline day grows; the usual day doesn't jump).
- Games (decided: below the lead card and fixture): one row for 19-0 ("Draft an IPL XI from 19 seasons", Play ›)
  and an "All games" link to /games. The daily four are on /games (unchanged, `TodaysGamesSection` still exported).
- The page at 390 went from 4,597px to 3,368px.
- **Deviation**: the ask placeholder is "Ask about a player, phase or matchup", not the requested "Ask anything about
  a player, phase or matchup": at 390 the longer one clipped ("...or mat") at 16px (16px is needed so iOS doesn't
  zoom on focus).
- Review fix folded in: the ratings credit is "hindsightcricket.com · Data: Cricsheet".

Checked: 390, 360, 1440 (no horizontal scroll); unit tests (today's post by IST date, the auction frame, the city
claim); App.test; build. Screenshots: `l7_390.png` (first screen), `l7_390_s2.png` (second), `l7_390_full.png`,
`l7_360.png`, `l7_1440.png`.
Not checked live: the post-led card (no post is marked posted locally) and a headline-day fixture (today's only
fixtures are ILT20); both paths are small and unit-tested where pure.

## Open items (for the owner / later)

- `routers/teams.py` `/teams/elo-rankings` treats "Indian Premier League" and "IPL" as two leagues (2026 matches are
  stored as "IPL"). The landing works around it by asking for both; the endpoint should normalise.
- `src/components/EloLeaderboard.jsx` is unused and could be deleted.
- Owner: curate the ask box's example chips (`EXAMPLES` in `src/components/landing/AskHero.jsx`).
- Owner: posts must be marked posted for /links and the lead card to show them (the coordinator is telling the owner).

## L7 review fixes

- The lead post: the newest marked-posted post planned for today **or yesterday** (IST), from `?limit=9` (was 3),
  so a post marked after midnight still leads. Test: "planned yesterday, after midnight" leads; two days on it doesn't.
- The kicker keeps "16 Dec" together (no-break space) when it wraps at 360.
- The post card's credit is "Data: Hindsight (hindsightcricket.com)" (the recent-posts data carries no credit).
- `isHeadline` is now the one helper (exported from LandingPage.jsx): India (men or women) always; otherwise a major
  league or event (BIG_SERIES), never a qualifier, never a women's match without India. It also orders the fixtures
  within a day (it replaced `isBig`; the old BIG_TEAMS list of ten Full Members is gone, so Australia v England no
  longer jumps the queue: India-first). Tests: `src/components/landing/__tests__/headline.test.js`.

## L6 step 1: ConnectorSection out of LandingPage

Files: new `src/components/connect/ConnectorSection.jsx`, new `src/components/landing/sectionKit.jsx`,
`src/components/LandingPage.jsx`, `src/components/pages/ConnectPage.jsx`.

- `ConnectorSection`, `CONNECTOR_URL` and `CONNECTOR_PROMPTS` live in `src/components/connect/ConnectorSection.jsx`.
- The section pieces both pages use (`Kicker`, `SectionHeader`, `sectionTitleSx`, `chipSx`, `monoSx`) live in
  `src/components/landing/sectionKit.jsx` (with the few tokens they need), so neither page imports the other.
  `/connect` no longer pulls in the landing page.
- Unused imports dropped from LandingPage (copy/check icons, `track`).
- Bundle baseline for L6 (`npm run build`, gzip): **main 976 kB** (`main.388dc930.js`), the largest other chunk
  15.6 kB. Every route except a few admin/notes pages is in main.

Checked: /connect renders the connector; / renders; tests; build.
