# On this day + finding past scorecards

Two linked features: a daily "On this day" post (Instagram, X, Reels) that recaps a past match played on today's
date, and making every past scorecard easy to find on the site. Each post sends people to a scorecard, so the second
feature is what the first one links to.

## What the data supports (checked 15 Oct 2026)

- **Impact and win probability only exist from 2015** (`delivery_details` / `ball_metrics`). The 2005–2014 matches
  have scorecards but no Impact, so the Impact-led format covers 2015 to now. An older match can still be a plain
  scorecard recap, but not the headline format.
- **There's plenty to choose from.** 9,618 men's T20s from 2015 to 2025, of which 9,591 have ball-by-ball data. Every
  calendar date has at least 2 matches; the median is 25, and the median of IPL/T20I matches is 8. Only 5 dates
  have no IPL or international match.
- **Discovery today:**
  - The landing page's recent-matches card only filters by competition (`/recent-matches/discover` also takes
    `team`, `window`, `date_from` and `date_to`, but the UI doesn't expose them).
  - Search (`/search/suggestions`) finds players, teams and venues, not matches.
  - The sitemap lists 1,556 scorecards out of roughly 10k.

## Status

| # | Chunk | Status |
|---|-------|--------|
| 1 | `on_this_day` picker | [x] 2026-10-15 |
| 2 | On-this-day post (carousel + caption + X + Reel) | [x] 2026-10-15 (Reel via nightly --reels-pending) |
| 3 | Schedule it daily | [x] 2026-10-15 (nightly workflow step) |
| 4 | `/scorecards` browse page | [x] 2026-10-15 (PR open) |
| 5 | Matches in search | [ ] |
| 6 | Every scorecard in the sitemap; links from player, team and venue pages | [~] 2026-10-15: sitemap + scorecard-page links done; player/team/venue match lists to do |
| 7 | `/on-this-day` page | [ ] |

## Chunk 1: the picker (`services/on_this_day.py`)

`candidates(db, day) -> [match]`: men's T20s on today's month and day, from 2015 until last year, that have
`ball_metrics`. Rank them by how strong the story is, using only numbers the match has:

- **The swing:** the loser's peak win probability (comebacks) and the biggest single-over swing (the recap's WP card).
- **The best performance:** the top Impact in the match (batting or bowling), and how it ranks against every Impact
  in that competition (a percentile, so "top 1% of IPL innings" is a real claim).
- **Stakes:** a final, playoff or knockout (from `matches.event_*`), a record (reuse `recap_special`'s
  record cards), and a big rivalry (two full members, or a well-known IPL pairing).
- **Anniversaries:** 5, 10 years ago get a small bonus. Prefer IPL and T20Is between the top 12; the other leagues
  only win when their story clearly beats both.
- **Variety:** don't repeat a competition or team on consecutive days (the same pattern as `deep_cut.py`'s 14-day
  no-repeat).

Jev ranks the top 5 (as in `deep_cut.py`), and code writes every number. Return the winner along with why it
was chosen.

## Chunk 2: the post (`services/ig_posts/on_this_day.py`)

Reuse the series recap's cards (`recap_series.py`): `how_it_was_won`, `wp_swings`, `score_race`, plus the Impact
scorecards. Two new cards:

- **Then and now:** where the match's stars are now (their Impact per innings since, and whether they're still
  playing) from the query builder. Said neutrally: no blame on players who faded.
- **Where it ranks:** the top performance against the competition's history (`metric_bars`, highlighted).

- **Hook:** "On this day in 2016: …" with a number (the user's rule: question hooks only with a number).
- **Kicker:** `On this day · IPL 2016 · Final`.
- **Caption:** the series-recap pattern (findings, a question, tags). Tags: `#OnThisDay`, the fixture, two players,
  the competition.
- **X:** the last tweet links to the scorecard (already how recap posts work after PR #126). Add `#OnThisDay` beside
  `#CricketTwitter`.
- **Reel:** hand-scripted or v2, payoff first.

## Chunk 3: scheduling

- Add an `on_this_day` slot in `services/ig_plan.py` (one a day, morning IST, before match-day posts).
- Add a build step to `scripts/ig_match_day.py`, or a new `scripts/ig_on_this_day.py`, run by the nightly workflow
  for tomorrow's date so it's in the morning digest.
- Render locally or on GitHub Actions (Chrome + ffmpeg), as the other posts are.
- Bench rule: if no candidate clears the story bar, the slot borrows from the bench (as myth slots do).

## Chunk 4: `/scorecards` browse page

A page over `/recent-matches/discover` with the filters the API already has, plus a date picker:

- competition, team (either side), season/year, and a date or date range
- "On this day" as a preset (today's month and day, every year)
- Results as cards: teams, result, top Impact performer, and a link to the scorecard
- Mobile-first (it's the main interface); URL params so every filtered view can be shared
  (`/scorecards?team=India&year=2016`)
- Linked from the nav ("Scorecards" under More) and from the landing card's "see all"

**Backend:** `/recent-matches/discover` needs `year`/`season` and `month_day` filters, and the top Impact
performer per match (one query over `ball_metrics`, cached per match: finished matches don't change).

## Chunk 5: matches in search

`/search/suggestions` returns `type: "match"` for queries like "India v West Indies 2016", "IPL 2016 final" or
"RCB KKR 2008":

- Parse the teams (the existing team aliases), a year or season, and a stage word (final, qualifier, eliminator).
- Rank the matching scorecards by date, finals first.
- The search bar shows them under "Matches" and opens `/scorecard/:id`.
- `/search/route` sends match-like queries to `/scorecards` with the filters filled in when there's more than one hit.

## Chunk 6: SEO and links

- **Sitemap:** every scorecard, split into sitemap files by year, with a sitemap index (Google's limit is 50k URLs
  per file).
- **Scorecard page:**
  - links to the previous and next meeting of the same sides
  - "more from this season"
  - the same date in other years
- **Player, team and venue pages:** a "matches" list linking to scorecards (best Impact first).
- **Share cards:** the existing scorecard OG card already works for old matches; add the season and stage to its
  kicker.

## Chunk 7: `/on-this-day`

The site's own version of the daily post: every men's T20 on today's date since 2015, the picked story at the top
and the rest below by Impact.

- Each card links to its scorecard.
- The share card shows the picked match.
- The Instagram bio link and the X post link here on days with an On this day post.

## Order

Chunks 4 and 6 first: people arriving from a post need somewhere to go, and old scorecards should be indexed.
Then 1–3, the daily post. Then 5 and 7.

