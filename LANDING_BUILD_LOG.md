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
