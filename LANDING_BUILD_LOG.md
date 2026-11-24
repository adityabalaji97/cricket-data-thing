# Landing build log

Builder log for LANDING_PLAN.md (the plan lives untracked in the main checkout). One entry per chunk.
Screenshots are in `docs/landing_review/build/` in this worktree (not committed: they are review aids).
Local setup: front end on :3001 against the local API on :8000 through a CORS shim on :8001 (the API only allows
:3000); headless Chrome via CDP at 390x844, 360x800 and 1440x900.

## Summary (24 Nov 2026, night one)

Branch `worktree-agent-af285dfac6d456c80`. Nothing pushed, nothing deployed. All eight chunks are done and reviewed.

| Chunk | Commits |
|---|---|
| L5 credits, small breakages | 06dc50a, fixes in fbffcb9; 6baa8a6 (fixture team codes 44px) |
| L3 notes dated, played previews hidden | 101fc1a, fixes 15e9a58 |
| L4 two screens cut (/connect, league counts off) | fbffcb9 |
| L8 /links as the home page's twin, #squad | 8320269, fixes c5f942a |
| L1 promise + ask box | 64b1f80, fixes 0138c9f |
| L2 ratings = the team page's | e937851 |
| L7 lead card, fixture row, 19-0 row | 1fc599e, fixes c4f8b97 |
| L6 first paint: connector module, static shell, lazy routes | 72c135b, 29a1267, fixes 00fd8af, db06c31, fixes dad3539 |

Main bundle 976 kB -> 225 kB gzip. Phone page 5,580px -> ~3,400px tall at 390.

**Assumptions for the owner to check**
- Logo: /links uses the site's `cricket-icon.svg` + "Hindsight" (as the home page, app header and mockup do), not
  the bat-h mark from the Instagram avatar. Changing to bat-h would be a site-wide swap.
- Example chips: six hand-kept questions with checked stored queries (`EXAMPLES` in
  `src/components/landing/AskHero.jsx`), two a day. 1-3 are from the Fable review, 4-6 are from the Nov query log.
- India-first headline fixtures: full cards only when India (men or women) play or a major league/event runs
  (BIG_SERIES), never for qualifiers or women's matches without India. Otherwise one row.
- The old BIG_TEAMS list (ten Full Members) is gone, so Australia v England gets the row, not the cards.
- The ask placeholder is shorter than the review's wording ("Ask about a player, phase or matchup"), because the
  longer one clipped at 390.
- The chunk-reload flag clears when a chunk loads, not when the app mounts (clearing on mount looped).

**Owner to-dos**
- Mark posts as posted in the admin queue after publishing. /links (posts from the last 14 days) and the lead
  card (a post planned today or yesterday) only show posted ones. Prod's list currently ends 21 Oct.
- Curate `EXAMPLES` in AskHero.jsx, and keep each stored URL checked.

**Open items**
- `/teams/elo-rankings` (routers/teams.py) splits the IPL into "Indian Premier League" (to 2025) and "IPL" (2026). The
  landing works around this by asking for both. The endpoint should normalise them.
- `src/components/EloLeaderboard.jsx` is unused.
- Notes have no `match_date`, so preview expiry reads the dek. Hand-written deks never expire.
- Not checked live: a post-led lead card and a headline-day fixture (no local data for either); real slow-4G paint.
- `FantasyPlanner.test.jsx` fails on main too (untouched). `CompetitionFilter` is still an unused import in App.js.

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

## L6 step 2: static shell and fallback head

Files: `public/index.html`, `api/meta.mjs`.

- `public/index.html` draws the home page's first screen inside `#root` before the bundle loads: the top bar (logo +
  "Hindsight"), "Cricket, ball by ball. Hindsight shows you why.", the promise line and the ask box, with inline CSS
  (dark background from the first byte, no white flash). React's first render replaces it. Measured against the app:
  at 390 and 360 the heading (84px) and the ask box (184/205px) sit exactly where the app draws them; at 1440 the
  heading is at 116px, x 110 in both. So the swap doesn't move anything.
- The shell's ask box is a plain form (`GET /query?nl=...`), so a question typed before the JS arrives still works.
- Only `/` shows it: an inline script marks other paths `noshell` (they get the dark background alone, as before).
- Fonts: the Google Fonts stylesheet is now linked in the head (with preconnects), so it loads with the HTML, not
  after the bundle (index.css still imports it for the app).
- `api/meta.mjs` (crawler heads): the note/notes body now replaces `#root` including the shell (matched up to the
  `<!--/shell-->` marker; the old empty root still matches); on any crawler path other than `/` with no body, the shell
  is stripped so crawlers don't read the home heading as that page's. Checked the regex against the real file.
- The fallback head (title/description/og) was done in the L8 fixes.

Checked: JS blocked (`static/js/*`) at 390 and 1440 shows the shell (`l6_shell_390.png`, `l6_shell_1440.png`);
`/player` with JS blocked hides it; build output contains the shell and the new title.
Not measured: real slow-4G first paint (the CDP throttle in my script didn't take effect on the dev server); the
shell is plain HTML+CSS in the first response, so it paints with the document.

## L6 review fixes (blocker: the shell marker didn't survive the build)

Files: `public/index.html`, `api/meta.mjs`, new `api/_lib/shell.mjs` + `api/_lib/shell.test.mjs`,
`src/components/landing/AskHero.jsx`.

- The production build minifies index.html and strips comments, so `<!--/shell-->` was gone and the crawler root
  regex matched nothing (no note bodies for crawlers; every page kept the home heading). The shell now ends with a
  real element, `<template id="shell-end"></template>` (kept by the minifier: checked in `build/index.html`).
- The regex and the replace live in `api/_lib/shell.mjs` (`ROOT`, `rootFor(html, path, body)`); meta.mjs calls
  `rootFor`. `ROOT` still matches an empty `<div id="root"></div>`.
- `node --test api/_lib/shell.test.mjs` reads `build/index.html` when there is one (else public/index.html) and
  checks: the shell is in #root and ROOT matches; a note body replaces the whole root, shell included; other pages
  drop the shell and `/` keeps it; an empty root still works. 4/4 pass against the built file.
- AskHero starts from whatever was typed into the static box before the app loaded.
- Google Fonts load without blocking (`media="print" onload`), with a `<noscript>` fallback.

## L6 step 3: the heavy routes split with React.lazy

Files: `src/App.js`.

- Every page except the home page is `React.lazy`: player, team, venue (VenuePage, and VenueNotes on the old preview),
  query, compare, games (and the five game pages), connect, venues, IPL predictions, wrapped, search, credits,
  fantasy planner, scorecard, the two XI pages. (Admin, notes, /links, graphics were already lazy.) The home page
  stays in main: it's the most common first page and has the static shell in front of it.
- One `<React.Suspense>` around the main `<Routes>`, falling back to an empty `minHeight: 100vh` box (page background,
  `aria-busy`), so the footer can't flash up under the header and then drop when the page arrives. The existing
  per-route `fallback={null}` Suspense wrappers stay (nested; harmless).
- `SearchBar` is imported from its own file, not the search index (which pulled in GoogleSearchLanding eagerly).
- **Bundle (gzip, `npm run build`)**: main **976 kB -> 224.6 kB** (-751 kB). Biggest lazy chunks: 360.2 kB (a shared
  vendor chunk the profile/team/venue/query pages use: charts), 103.6 kB, 46.4 kB, 39.5 kB. Served from the built
  files (`python -m http.server` on build/), `/` downloads only `main.*.js` (688 kB raw, the 224.6 kB gzip) plus the
  small `auto-player-load.js`.
- Checked in the dev app (390): /player?name=V Kohli, /query, /team?team=MI, /games, /connect, /credits, /games/19-0,
  /venue?venue=Wankhede..., /compare, /search, /scorecard/1535464 all render. Full Jest suite: 169 pass; the only
  failure is `FantasyPlanner.test.jsx`, which fails on main too.
- Pre-existing eslint warning left alone: `CompetitionFilter` imported but unused in App.js.

## Follow-up: fixture card team codes at 44px

- The team codes on the fixture cards (headline days, or "N more fixtures") were 32px links: now 44px, with the
  "VS" line tightened. The card grew to 306px at 390 (two-line series chip), so `FIXTURE_CARD_HEIGHT` is 306 (cards and
  the error card share it). This closes the last tap-target item from L5. Screenshot: `fixture_cards_390.png`.

## L6 review fixes 2: stale chunks after a deploy

Files: new `src/utils/lazyWithRetry.js` + `src/utils/__tests__/lazyWithRetry.test.jsx`, new
`src/components/ui/ChunkErrorBoundary.jsx`, `src/App.js`.

- Every lazy page (the new ones and the older admin/notes/links ones) goes through `lazyWithRetry`. On an error
  matching `/Loading chunk|ChunkLoadError|dynamically imported module/i`, the first time in a session it sets
  `sessionStorage['chunk-reload']`, reloads, and returns a never-settling promise; otherwise it rethrows. Every
  sessionStorage access is in try/catch (if storage is blocked, it doesn't reload; the error shows).
- **Deviation from the review**: the flag is cleared when a page's chunk *loads*, not when the app mounts. The app
  mounts before the failing page's chunk is requested, so clearing on mount reloaded forever. I saw this in the
  browser: with TeamPage's chunk blocked, the first version kept reloading. Now: one reload, then the boundary.
- `ChunkErrorBoundary` wraps the main `<Suspense>`: "Couldn't load this page", "Check your connection, then reload.",
  and a 44px lime Reload button on the page background. It resets when the path changes.
- The redundant inner `<Suspense fallback={null}>` wrappers on /scorecards, /admin*, /notes*, /g, /links and
  /graphics are gone. The /ig Suspense stays: that branch renders outside the main one.
- Tests (4): a stale chunk reloads once, then the error goes through; a successful load clears the flag; other errors
  never reload; the boundary renders the message and button. Browser check: `/team?team=MI` with the TeamPage chunk
  blocked shows the boundary after one reload (`l6_chunk_error_390.png`). Unblocked, it renders normally.
- main bundle: 225.2 kB gzip (+0.5 kB).

## Round 2 (24 Nov, evening)

Builder: worktree `agent-afe273a40aee056dd`, branch `worktree-agent-afe273a40aee056dd`, from `2ece6b2` (PR #336).
Nothing pushed or deployed. Front end on :3002 against the :8000 API through a CORS shim on :8002 (scratchpad, not
committed). Screenshots in `docs/landing_review/build_r2/` (uncommitted).

### R2.1 The tagline on its own line

Files: `src/components/landing/AskHero.jsx`, `public/index.html`, `src/components/ig/IgLinks.jsx`.

- "Hindsight shows you why." is a block span under "Cricket, ball by ball.", still lime. The text keeps its space, so
  the heading reads the same to screen readers and crawlers.
- The static shell's `h1 em` is `display: block` too, so the swap to the app still doesn't move anything.
- Assumed: /links (IgLinks, the home page's twin) gets the same break, so the two stay alike.
- Checked at 390 and 360: two lines (h1 59px tall), no horizontal scroll (`hero.png`, `hero_360.png`).

### R2.2 "All squads" leads to a team list, not an empty dropdown

Files: new `src/components/pages/TeamList.jsx` + `src/components/pages/__tests__/teamList.test.js`,
`src/components/pages/TeamPage.jsx`, `src/components/landing/TeamRatings.jsx`, `src/components/landing/LeadCard.jsx`,
`src/components/landing/__tests__/teamRatings.test.js`.

- `/team` with no team (the menu's Teams, a bare link, "All squads") now shows two cards: the ten IPL sides and the
  12 T20I sides the landing card ranks. Each card: kicker, claim (who leads, who is last), one 44px row per side
  (rank, team-colour bar, full name, rating, ›), scope line (Elo after the latest match, to the date), credit.
  Each row goes to `/team?team=<code or name>&autoload=true`, the URL the landing rows use.
- Order: `?scope=t20i` puts T20Is first; `?league=IPL`, no param, or anything else IPL-ish puts the IPL first.
  "All squads" passes the tab that's open (`action` may now be a function of the scope).
- Ratings: the landing card's fetch moved into `fetchRankings`/`useSides` in TeamRatings.jsx, memoised per scope
  for the page load (2 calls for the IPL, 1 for T20Is; a failure is dropped so Try again re-asks). Home -> /team
  makes no new ratings calls. While loading, or if it fails, the sides still list (A-Z, no ratings) and are tappable.
- The old dropdown stays as "Search any team" under the cards; it fetches `/teams/` only when opened, not on load.
- Rows (here and on the landing card) scroll to the top on tap: the app keeps scroll position across routes, so a
  low row opened its team page half-way down.
- Assumed: the IPL claim now names sides by city outside the auction frame too ("Bengaluru are the top-rated IPL
  side. Lucknow are 10th of 10."); the full names ran to three lines at 390. Test updated.
- Assumed: with no param, the IPL leads (India-first).
- Desktop: the two cards sit side by side (max 1040px).
- Checked at 390 and 360: 22 rows, all 44px, no horizontal scroll; T20Is tab -> All squads -> `/team?scope=t20i`
  with T20Is first; tapping MI opens Mumbai Indians at the top (`teams_ipl.png`, `teams_t20i.png`,
  `teams_bottom_360.png`, `mi_page_390.png`).

### R2.3 Audit P1: fixture previews open with both teams

File: `src/components/LandingPage.jsx` (`routePreview`).

- The fixture row and the expanded card's Match preview passed short codes (GG, MIE), which the preview can't
  resolve, so the page opened venue-only. They now pass the full names (`team1`/`team2`, codes only as a fallback)
  plus `&story=1`, as /links does. Checked: GG v MIE (ILT20, live) opens "Gulf Giants v MI Emirates" with par,
  chasing and head to head (`fixture_preview_390.png`).

### R2.4 Audit P2: the lead card's kicker follows the tab; review fixes for R2.2

Files: `src/components/landing/LeadCard.jsx`, `src/components/landing/TeamRatings.jsx`, `src/components/pages/TeamList.jsx`,
`src/navItems.js`.

- The T20Is tab said "IPL 2027 · auction 16 Dec". `kicker` may now be a function of the tab: the IPL keeps the
  auction frame, T20Is read "T20I team ratings" (its claim never used the frame). `lead_t20i_390.png`.
- Review: the team list's fallback (ratings failed) is now really A-Z, as its scope line says.
- Review: the header for /team reads "Teams" (navItems title), matching the page heading.
