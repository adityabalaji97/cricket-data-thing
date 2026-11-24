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
  publish, Jan match -> next year). "Over" = start + 4h for a T20, + 9h for an ODI. A preview whose dek has no
  start (hand-written) stays: front end only, no API change.
- Fetches 8 and shows the first 3 left, so hiding previews doesn't empty the row.

Checked: unit tests (5) and App.test pass; local data's 2 Oct preview is hidden, the three notes left are dated.
Screenshot: `l3_notes_390.png` (cover images are broken only locally: the dev server doesn't serve /img).
Open: hand-written previews with a different dek format never expire; a `match_date` on the notes API would
make this exact (small backend change, not done).
