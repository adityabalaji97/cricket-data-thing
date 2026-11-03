# Team and venue pages, simplified

The same treatment as the player profile (PROFILE_SIMPLIFY_PLAN.md, live 3 Nov 2026), applied to /team and /venue:

* A summary at the top, written as one stat per line ("3rd of 10 IPL sides | rating 1,812").
* A few cards below it. Each card has one claim, one picture and a share button, and fits one phone screen.
* One window for the whole page, set from a filters icon and kept in the URL.
* The data credit appears once, at the foot.
* No text wraps at 390px.

Anything else is removed. The query builder and the connector still reach that data.

Status: **draft for the user's sign-off** (3 Nov 2026). The next step after sign-off is mockups with real teams and
grounds.

## What the pages are today (captured 3 Nov 2026, 390px, every section open)

**Team (India, Jan 2025 to today): 10 phone screens, 9 sections.**

* **Overview:** six stat tiles (matches, W/L, success rate, won batting first, won fielding first, toss), the ELO
  card and a recent-form strip.
* **Phases:** percentile bars, followed by a runs/balls table for batting and another for bowling.
* **Batting and Bowling:** batting-order and bowling-order cards, one long card per player.
* **Four sections show nothing:**
  * Squad: "No players found for this team."
  * Relative Metrics: "unavailable".
  * Head-to-Head: "not available yet".
  * Title Odds: "will populate in Phase 3".
* **Bugs:**
  * India's batting order lists Rohit Sharma as No. 1 since 2025, with 1,254 runs and 25 wickets. That looks like a
    team-name match pulling in another side.
  * The name shows as "India (India)".
  * The toss tile uses emoji.

**Venue (Wankhede): 5 phone screens, 4 sections.**

* **Summary:** results split, "what total wins here" and a phase table.
* **Boundaries:** balls per boundary by pace/spin and phase, plus a bowl-style table.
* **Leaders:** most runs and most wickets tables.
* **Explore:** query prompts.

The page is titled "Match Preview" and is the preview screen with no teams picked. The new story-style preview is
built only once both teams are chosen.

## The key reuse: the preview's ground chapter

The match preview's "The ground" chapter (services/preview_cards/ground.py, existing.py) is already a set of cards
about the ground alone. None of them reads the two teams:

* par
* what total wins
* how an innings unfolds
* which phase is unusual (against every ground in its main competition)
* pace or spin
* where the boundaries go
* how batters get out
* how winning innings are built
* bat first or chase
* recent results

So **the venue page is the preview with no teams**. It runs the same cards, with the same visuals and titles, from
`PreviewContext` with team1/team2 left empty. Picking two teams on it opens the full preview.

The team chapter's sources already work for one side. Both team pages build on them:

* `team_window`
* `team_phases` (against the competition)
* `elo_series`
* `last_xis`
* `form`

## The new venue page

1. **Summary:**
   * Ground and city, then the window ("Since Jan 2024 · 31 IPL matches").
   * Rank | description rows against the grounds of its main competition, for example:
     * "2nd of 12 IPL grounds | par first innings · 196"
     * "1st of 12 | chases won · 64%"
     * "11th of 12 | spin overs · 22%"
   * Its next fixture, if one is scheduled, linking to that match's preview.
2. **Ground cards:** the ground chapter, in its fixed order.
   * Boundary zones and dismissals appear only where the ground really differs from the rest, as in the preview.
3. **Who does well here:** one card for the leading run-scorers and wicket-takers at this ground in the window, ranked
   by Impact and showing runs/strike rate or wickets/economy. This replaces the two long tables.
4. **Footer:** a query builder link and the credit.

Removed: the "Match Preview" title and the classic filters panel (replaced by the filters icon), the Boundaries tables
(their content sits in pace or spin and the boundary zones), and Explore.

## The new team page

1. **Summary:**
   * Name, competition and window.
   * Rank | description rows among the sides in its competition, for example:
     * "3rd of 10 IPL sides | rating · 1,812"
     * "1st of 10 | death batting, runs above par · +9 /100"
     * "9th of 10 | powerplay bowling, economy · 9.4"
   * Won-lost in the window.
   * The last 8 results, coloured by margin (like the player's last 8).
2. **Cards:**
   * **Rating over time:** the ELO line, with the competition median.
   * **By phase:** batting and bowling against the competition, one picture showing both (the preview's
     phase-strength card for one side).
   * **Who bats where:** the usual top eight by position, with each batter's share of innings there and his
     Impact. This replaces the per-player batting-order cards.
   * **Who bowls when:** an overs grid (1-20 across, bowlers down) showing who bowls which overs. This replaces the
     per-player bowling-order cards.
   * **Top players:** the side's biggest contributors in the window, by Impact, for batting and bowling.
   * **Where they win:** home and away, and batting first and chasing, as one card.
   * **Against each side:** won-lost against each opponent in the window. This only appears where there are
     meetings, and it replaces the empty Head-to-Head section.
3. **Footer:** a query builder link and the credit.

Removed:

* the stat tiles (they go into the summary)
* Squad
* Relative Metrics
* Title Odds
* the per-player order cards
* the two phase tables

## Shared

* **One page shell:** the profile's card shell (`ProfileCard`), filters drawer (`ProfileFilters`) and URL-held window,
  lifted into a shared component that all three pages use.
* **Filters:** format, period (recent, career or custom dates) and competition.
* **Cache:** every page's numbers come from one cached endpoint, warmed nightly, with the same 503 retry and
  semaphore pattern as /player/{name}/cards.

## Chunks

| # | Chunk | Status |
|---|---|---|
| S0 | Mockups with real teams and grounds (India, Chennai Super Kings; Wankhede, Chinnaswamy) for sign-off | [x] 3 Nov 2026: signed off ("looks good, go forth and build") |
| S1 | Shared page shell | [x] 3 Nov 2026: src/components/pageKit/pageKit.jsx (header, pills, summary rows, URL window, retrying fetch, footer); ProfileCard and ProfileFilters (showScope) reused. The player profile keeps its own VerdictScreen header for now |
| G1 | Backend: venue page | [x] 3 Nov 2026: services/venue_page.py, GET /venue-page; the preview's ground cards with no teams, ranks against the main competition's grounds, leaders; built in the background (services/page_builds.py: 503 + retry), warmed nightly (scripts/warm_pages.py) |
| G2 | Venue page | [x] 3 Nov 2026: src/components/pages/VenuePage.jsx; /venue with a ground and no teams; "Add two teams" opens the preview; next fixture here; the picker sends a ground-only pick here |
| T0 | Team data bugs | [x] 3 Nov 2026: moot, the old batting-order service and "India (India)" header went with the old page; the new page counts by ball-by-ball team names |
| T1 | Backend: team page | [x] 3 Nov 2026: services/team_page.py, GET /team-page; league or top-12 peers; ODIs rank batting by strike rate (no par yet) |
| T2 | Team cards | [x] 3 Nov 2026: rating, by phase, who bats where (a line-up: each batter at his most-used spot), who bowls when, top players, where they win, against each side |
| T3 | Team page | [x] 3 Nov 2026: src/components/pages/TeamPage.jsx at /team; TeamProfile and 12 components only it used removed |
| Z  | Check at 390px; per-card share images | [~] 3 Nov 2026: checked Wankhede, CSK, India at 390px; per-card share images (as profile P6) still to do |

## Decisions (user, 3 Nov 2026)

* **Peers:** a franchise is ranked against the sides in its league, and an international side against the top-12 T20I
  sides.
* **Window:** since Jan 2024 by default, the same as the player verdict.
* **IPL team pages:** they take the retention and auction data after the 16 Dec auction.

Mockups (S0, real data): https://claude.ai/artifact/JzAUEhHBqCi8Mw2JVGCG49.

* **Phones:** Wankhede and Chinnaswamy, built from the preview's real ground cards, and CSK and India.
* **Builder:** scratchpad build_tv_mock.py, which reads tv_data.py's numbers.
* **Venue summary:** it will use the preview's par (the T20 Primer method), so it agrees with the par card. The mockup
  shows the plain average first innings.
