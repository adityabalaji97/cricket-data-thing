# Multi-Format Dev Log

Plan: [MULTI_FORMAT_PLAN.md](MULTI_FORMAT_PLAN.md) · Working dir: `/Users/adityabalaji/cdt/cricket-data-thing`

> **Every agent (Claude or Codex) reads the CURRENT STATE block below before doing anything else,
> and updates it before ending a session.** See "How to update this log" at the bottom.

---

## CURRENT STATE

> ### START HERE (2026-09-24) — U1 + Phase 0 live
>
> **Games v3 (2026-09-26):** four dailies, each with a practice mode (`?puzzle=<token>`, no streak):
> Higher or Lower = 10 independent pairs, tap the higher-Impact card; Call It = yes/no "did they win
> it?" with batters at the crease and the model %, ⭐ for a right upset call; Player Journeys = team
> colours + typed guesses (hangman dashes; `name_matches` forgives close spellings/aliases, the
> `/player-journey/names` endpoint is gone); Guess the Innings is now a daily
> (`/games/guess-innings/{daily,hint,check,reveal}`). Shared frontend: `games/daily/usePuzzle.js`,
> `NameGuessGame.jsx`, `NameGuessInput.jsx`. Progress keys moved to `day.v3.<date>` so v2 saves
> are ignored. `match_preview` prod golden drifts with rankings data; not a regression.
>
> **Latest:** Phase 2 T20 Primer metrics live (ball_metrics etc.; see newest entry). API on
> Python 3.12; U4 done. U3 colour sweep done (see newest entry; `ui_sweep.mjs` now reports contrast).
> Preview defaults to 1 Jan 8y (ODI) / 4y (T20) on site and connector; venue
> similarity is format-pinned with a shared pool cache (see newest log entry).
>
> **U1 (five UI bugs) is deployed**: commit ab453ab on main; Heroku v411/v412, Vercel `hindsight`
> Ready. **Phase 0 done**: Heroku Postgres is now **essential-1** ($9/mo, 10 GB, 20 connections;
> 3.73 GB used after the copy dropped bloat). The plan change moved the database, so
> **DATABASE_URL changed** — Heroku config, the GitHub secret and local `.env` all point at the
> new host (`c1rqglkbf2a14o…`). Pool is `DB_POOL_SIZE=4 / DB_MAX_OVERFLOW=2` (12 of 20
> connections). Backup `b004` taken before the change. Row counts verified identical.
>
> **U2 (global dark theme + mobile bottom nav) + first U3 pass is live** (2a3a18e on main,
> Vercel `hindsight` production Ready; live phone sweep clean). User validating on device.
> **Phase 1 (MCP connector) is live** at `/mcp` (Heroku v413; see its entry and
> `docs/mcp-connector.md`). Dyno now runs **one** uvicorn worker (`WEB_CONCURRENCY=1`,
> pool 8+4, v414) after R14 memory errors. Next: remaining U3 literals and U4, then Primer metrics.
>
> Plan of record for the wider work lives in `~/.claude/plans/can-you-look-at-iterative-plum.md`:
> U1+Phase 0 (done) → U2 global dark theme + mobile bottom nav → query-builder MCP → U3 →
> T20 Primer metrics → U4. **UI checks:** `node scripts/dev/ui_sweep.mjs <out>` (CDP phone
> emulation; see its header for why plain headless screenshots are wrong at 390px).
>
> **Known, not fixed:** `/rankings/player/{name}?snapshots=6` still exceeds 30s for long windows
> (Player page Global T20 Rank section). Golden check has 5 pre-existing diffs (see 2026-09-24
> entry) — re-capture goldens once confirmed intended.
>
> ### Previous state (2026-08-01)
>
> **ODIs are live end to end** — API, nightly refresh and UI. **A1, A2, A6, A7 and A8 are
> complete**, so all three hero features (query builder, scorecard, match preview) now work
> for ODIs, and the preview is on the dark design system. Heroku v391, Vercel current,
> `mens-odi` reports available. A1 and A2 are done; so are 0.7, A9, and the cross-format work
> below. Five live format-contamination bugs were found and fixed (see the sweep table further
> down); four files remain unchecked.
>
> **The query builder is cross-format by default now**, at the user's direction: the format
> control moved out of the site nav into Filters & Grouping, "All formats" is the default, and
> `group_by=format` works in delivery and both stats modes. `nl2query` knows `format` is a
> column distinct from `competition`. Kohli since 2023 returns ODI 2,430 @ SR 96.5 beside T20
> 2,892 @ SR 143.3 in one query.
>
> **Three traps this exposed, all worth knowing before touching format defaults again:**
>
> 1. **`get_format('ALL')` raises by design.** Any consumer resolving a FormatSpec must use
>    `pinnedFormatParams` from FormatContext, not `formatParams`. `/landing/featured-innings`
>    500s on `format=ALL` (verified) — it resolves a spec for strike-rate bands.
> 2. **Endpoint `Literal`s must list `"ALL"` explicitly** or FastAPI 422s. That is what produced
>    "Failed to load column metadata" with every filter dropdown empty.
> 3. **Pipeline steps silently drop the format.** Twice in one day: `step_backfill_advanced` and
>    `step_refresh_metadata` both called helpers that take `fmt`/`gender` without passing them,
>    so an ODI run refreshed the T20 cache. **`step_populate_columns` and `step_update_players`
>    still take no format at all** — check those next; `update_players` ignoring gender is
>    already the recorded women's-T20 blocker.
>
> **Vercel was not deploying for nine days** and nothing said so. `scripts/vercel-ignore-build.sh`
> skipped every build because Vercel clones shallowly: `git rev-parse --verify` passes on the
> previous SHA while the object is absent, so `git diff` fails with "fatal: bad object" and a
> `|| true` turned that into an empty diff, read as "nothing changed". It now builds when the
> diff *fails*, verified against a real `--depth 1` clone. Note the live project is **hindsight**,
> not `cricket-data-thing` — `.vercel/project.json` points at the wrong, stale project, so a
> bare `vercel` deploys somewhere nobody looks. Worth relinking.
>
> **Known slow, not fixed:** an unfiltered delivery aggregate takes ~23s for T20 alone and
> exceeds Heroku's 30s router timeout under `ALL`. Only reachable by executing with no filters,
> which is not a real user flow, but the 23s baseline is a genuine defect that will worsen as
> formats are added.
>
> **A1 detail.** Pipeline finished in 50m23s. Production now holds 3,053 ODI matches
> (2000-01-09 to 2026-07-25) with ELO, 1,647,737 ODI balls, and ODI batting/bowling stats.
> ELO ran as a separate `ODI/male` pass and reported "all matches already have ELO" for T20 —
> the per-format streams do not disturb each other.
>
> **Two live contamination bugs were found and fixed** (deployed v382, v383):
>
> * **`services/matchups.py` had no format handling at all.** It fed match preview's fantasy
>   projections. Mahmudullah's avg balls per innings went 16.81 → 24.23 (286 T20 innings →
>   478 mixed), pushing his projection from 63 to 71 expected points. Four pins added: the two
>   avg-balls lookups, the `recent_matches` CTE (which cascades to all six delivery reads that
>   join it), and the head-to-head `raw_stats` read.
> * **`services/global_t20_rankings.py` had no format handling.** 588,732 ODI balls — **39% of
>   the ranking pool** — were counting toward "global T20 rankings", via ODI, ICC World Cup,
>   Champions Trophy and Asia Cup.
>
> **Read this before trusting the old goldens.** The first `prod` baseline was captured *after*
> the ODI ball load, so it was only clean for paths that join `matches`. Anything reading
> `delivery_details` directly — the rankings, the head-to-head query — was **already
> contaminated in the baseline itself**. That is why the post-fix numbers moved *away* from the
> golden (372b → 356b was the pin removing 16 ODI balls, i.e. the fix, not a regression). The
> goldens have been re-captured post-fix and now pass 13/13. Judge future diffs on whether the
> pinned value is right, not on whether it matches a stored number.
>
> `/query/deliveries` was verified clean throughout: grouped by over it returns exactly one ball
> at over 20 (a genuine T20 super-over) and nothing at overs 21-50, where the database holds
> 36,155 ODI balls at over 20 alone.


- **Active chunk:** **Phase 0 complete, plus A3, A5, A9 and most of A11.** ODIs are usable in the query
  builder UI and render correct scorecards, all against local data. Next is **Phase A**, which opens with
  the Heroku essential-2 upgrade and the real ODI backfill (A1), then the workflow matrix (A2).
- **Before A1:** production still needs migration `002`, and the branch is **unpushed and
  undeployed** — production is running `main` with only migration 001 applied and its stats
  data repaired.
- **Both former blockers are now resolved in code, locally:**
  - The dropdown cache is partitioned by (format, gender); `/deliveries/columns` takes a format
    parameter. Fixing it exposed that the loader left `delivery_details.competition` raw while
    `matches.competition` was normalised, so `leagues=ODI` matched nothing — the league filter
    was simply broken for non-T20. The loader now normalises on load.
  - The corrupted stats are repaired by `scripts/backfill_recompute_stats.py`. Locally this took
    impossible wicket counts from 21,905 to 19 and batting averages from absurd (Sikandar Raza
    2.61) to correct (Kohli 57.58, top of the list).
- ✅ **Production backfill DONE** (2026-07-26). Corrupt rows 52,070 → 74 (0.04%, source-data
  anomalies); live batting averages verified correct. Backup `b002` predates the change.
- **Branch:** `multi-format` (branched from `main` @ `29b61c1`)
- **Local DB:** `hindsight_local` on localhost:5432 (PG14 server), 644 MB subset of prod, healthy.
  Rebuild any time with `scripts/dev/setup_local_db.sh`.
- **Prod DB:** Heroku `cricket-data-thing`, PG16.13, **essential-1** (6.28 GB / 10 GB).
  Upgrade to essential-2 is **NOT done yet** — deliberately deferred until just before the
  Phase A ODI backfill (chunk A1), since nothing before that needs the extra space.
- **Migrations applied — local:** `001_multi_format_columns.sql` ✅,
  `002_delivery_details_source_columns.sql` ✅
- **Migrations applied — prod:** `001_multi_format_columns.sql` ✅ (2026-07-26, 12s, all 2.33M
  rows stamped T20/male; live app verified healthy after). `002` still pending.
  Applied ahead of A1 because chunk 0.9's backfill needs those columns.
- **Dataset URLs:** all four are in `.env` (gitignored) as `DROPBOX_T20_URL`, `DROPBOX_ODI_URL`,
  `DROPBOX_WT20_URL`, `DROPBOX_TEST_URL`. **This repo is public — never commit these values**, and
  pull slices with `make_csv_slice.py --url-env NAME` so no link lands in shell history.
- **Slices in `data/slices/`** (gitignored, regenerate as needed): `t20_slice.csv` (2,874 matches,
  2015-2022), `odi_slice.csv` (349, 2000-2007), `test_slice.csv` (85, 2020-2025).
- **Goldens:** 13 endpoints in `scripts/goldens/local/`, `check` passes clean (re-captured in 0.2
  after a deterministic-ordering fix; see that entry).
- **Local data loaded:** men's T20 (3,926 matches / 770k balls) **and** men's ODI (257 matches /
  149,599 balls, 2000-2007), with derived batting and bowling stats for both.
- **Blocked on / next action:** nothing blocking. Start **0.7** (frontend foundation). Two known
  follow-ups are listed above: the `/columns` cache partition, and the stored-wickets backfill.

---

## Log entries (newest first)

### 2026-09-26 — Games v2: Higher or Lower plays all 10; Player Journeys daily across both tables — Claude

* **Higher or Lower**: a wrong call no longer ends the run -- all 10 are played, score N/10,
  share grid 🟩/🟥 per call.
* **Player Journeys v2** (daily like the others; answer never sent to the browser):
  - Careers from legacy `deliveries` (IPL < 2015) + `delivery_details` (IPL >= 2015) on
    canonical names (player_aliases). Pool: >= 4 seasons, >= 2 franchises, >= 500 runs or >= 25
    wickets, no lone-initial legacy names (216 players).
  - Team names shown as they were that season: delivery_details writes CURRENT names back to 2015,
    so `historical_team()` restores Delhi Daredevils (<=2018), Kings XI Punjab (<=2020), Royal
    Challengers Bangalore (<=2023). The old endpoint's map also no longer merges Deccan Chargers
    into SRH (different franchises).
  - Years shown up front; hints 🏏 style (role + hand + bowling style, labels not codes, feed
    fallback) / 🌍 country / 📊 IPL numbers / 🔤 initials, each -1; guesses from a name list
    (no spelling test), wrong guess -1, 6 guesses; score 5 - hints - misses (min 1 if solved).
  - Endpoints `/games/player-journey/{puzzle,hint,check,reveal,names}`; `puzzle=<ISO date>` is the
    daily, any other token is practice ("play a random one", no streak). Old `/player-journey`
    kept for compatibility.
* Home "Today's games" lists all three; warm-daily-games also builds the journey pool.

### 2026-09-26 — Growth G2: daily games "Call It" and "Higher or Lower" — Claude

* `services/daily_games.py`: deterministic puzzles per (game, IST date) via sha256 seed; #1 =
  2026-09-26; future dates clamp to today, pre-launch to launch. Pools cached 6h per process.
  - **Call It**: 5 decided chases from the last 3 years (slots weighted IPL 40% / top-10 T20I
    25% / other majors 35%); per match the max-leverage inns-2 ball with wp_before 0.15-0.85 and
    12-48 balls left. `/games/call-it/daily` (no answers) + `/games/call-it/reveal?index=`.
  - **Higher or Lower**: batter-seasons per competition (>= 150 balls, last 4 seasons, majors +
    top-10 T20I) of players with >= 600 balls in the window; 11-card chain alternating close
    (< 15) / clear (> 30) Impact gaps. `/games/higher-lower/daily` + `/reveal?index=`.
* Frontend: `games/daily/{dailyStorage.js, DailyGameShell.jsx}` (progress per day, streaks that
  survive only if yesterday was played, share, countdown to midnight IST), `CallItGame.jsx`
  (slider; score 100x(1-sq err); 🟩 right+beat model / 🟨 right / 🟥 wrong or 50%),
  `HigherLowerGame.jsx`. Routes in MensT20Scope, nav "Play" group, Home "Today's games" card.
* `.github/workflows/warm-daily-games.yml` requests both at 18:35 UTC (Call It builds in ~10s
  cold) and fails if either is down. Both daily endpoints are status-only goldens.

### 2026-09-26 — Growth G1: every shared link unfurls with its own title and image — Claude

* The site-wide og:image was an SVG, which WhatsApp/X/Facebook do not render: shared links had
  no image at all. Now `api/og.mjs` (@vercel/og, Node) draws 1200x630 PNGs at `/_og?path=...`:
  scorecards (result, scores, WP sparkline, Impact margin), players (latest-season Impact /
  per-100 / WPA tiles + Impact by season), everything else a branded text card.
* `api/meta.mjs` serves index.html with a page-specific head (title, description, OG/Twitter,
  canonical). `vercel.json` routes ONLY bot/unfurler user-agents there (explicit UA list, no
  `(?i)`), so people get the static app with no extra hop. Summaries live in `api/_lib/share.mjs`.
* `/sitemap.xml` (`api/sitemap.mjs` + API `GET /seo/sitemap-entries`, cached 1 day): last
  year's scorecards, top-500 men's T20 batters (3y), top-200 venues; robots.txt points at it.
* `src/components/ui/ShareButton.jsx` (native share sheet, else copy link; `share` event) on
  scorecard, player, match preview and query results.
* `SITE_URL` / `HINDSIGHT_API_BASE` env vars on Vercel override the defaults when the custom
  domain lands.

### 2026-09-26 — Growth G0: usage measurement, Player Journeys fix — Claude

Growth plan (`~/.claude/plans/can-you-look-at-iterative-plum.md`): G0 foundations → G1 shareable
links/OG → G2 daily games (Call It + Higher or Lower) → G3 AI "Hindsight Notes" → G4 MCP growth.
* **Player Journeys 500 fixed** — my U1 edit left `routers/games.py:278` as
  `WHERE mcompetition IN (...)'`. Both game endpoints are now status-only goldens
  (`status_only` support in regression_snapshot.py; prod/local goldens hold `{"status": 200}`),
  since the mocked-DB sanity tests can never catch SQL errors.
* **Migration 004** (applied to prod): `mcp_call_log`, `app_events`. `services/usage_log.py`
  writes them from one background thread (bounded queue, drop on failure, `USAGE_LOGGING=0` off).
  MCP `_log_call` persists every call with a salted caller hash (USAGE_HASH_SALT).
* **Web events**: `src/utils/analytics.js` (anon id in localStorage, 30-min session, DNT
  honoured, batched `fetch keepalive` to `POST /events`); tracked: page_view (App route change),
  query_run, nl_search, game_start/finish, share (games), connector_copy. The Vercel proxy now
  forwards `x-vercel-ip-country` as `X-Client-Country` (no IP).
* **Reports**: `GET /admin/usage` (X-Admin-Token = ADMIN_TOKEN config var; 404 if unset) and
  `scripts/usage_report.py` share `services/usage_report.build_usage_report` (whole weeks).
  Nightly workflow prunes raw rows older than 90 days.
* tests/conftest.py sets USAGE_LOGGING=0 -- .env is prod, tests must not write usage rows.

### 2026-09-25 — Connector didn't "see" the Primer metrics — Claude

A Claude chat using the connector answered that Hindsight has no Impact/RAA/WPA and approximated
them itself. The data was there, but (1) the text table the model reads stops at 10 columns and
the metrics came after, so only a `sort_by="impact"` query showed them, (2) neither the server
instructions nor get_query_options mentioned them. Fixed: instructions item 5 describes the
metrics and says to sort by them rather than approximate; get_query_options returns a `metrics`
block; the text table always appends impact/raa/waa/wpa when rows carry them. Chats opened before
this deploy may hold the old tool list -- reconnect the connector (or start a new chat).

### 2026-09-25 — Phase 2: T20 Primer metrics (par, Impact, RAA/WAA, WP/WPA, leverage) — Claude

Implements Himanish Ganjoo's *T20 Metrics: A Primer* (Aug 2026) for men's T20 (2015+, the
Hundred excluded). Library: `services/metrics/` (pure numpy/pandas, unit-tested in
`tests/test_primer_metrics.py`):
* `dl_curve.py` — DL Standard fit (weighted LSQ on runs-to-come cell means from 9,794 complete
  first innings; RMSE 0.73 runs; R_std(120,0) = 160.6 vs the Primer's ~170 on its narrower
  5-competition dataset), DL Pro with n0 = 1.04, vectorised lambda solver. F cubic with F(0)=1,
  beta cubic with free constant (8 params; the Primer says 7 without saying which).
* `par_scores.py` — nested shrinkage (global→league→year→ground; T20I global→year→country), eq. 3-4.
  Reproduces the Primer's fig. 1: Hyderabad IPL par 160.0 (2018) → 190.8 (2025), the same +31.
* `ball_metrics.py` — pre-ball state is the PREVIOUS ball's recorded state (feed has ~0.3% rows
  where score ≠ Δinns_runs, wickets without Δinns_wkts, mid-innings max_balls changes), so Impact
  telescopes exactly (verified 0.0 diff) and rain cuts are not charged to a ball. Impact (eq. 9),
  WP from the DL score ratio (eq. 11-12, n = 6 — also the best Brier on our data), WPA, leverage
  (p6 − pw).
* `raa_waa.py` — XGBoost regressor/classifier on (balls left, wickets down, par-or-target, innings),
  wides excluded; runs = what the ball added to the team total (extras included), same as Impact.

Validation (all against the Primer's own tables): IPL 2023-26 RAA leaders Abhishek 322.6 (Primer
309.4), SKY, Sooryavanshi, Salt, Klaasen in near-identical order; IPL 2026 Impact Sooryavanshi 243
(232), Bhuvneshwar 251 (243); WPA Sooryavanshi 1.75 (1.71), Kohli 1.02 (1.00), Kishan 0.75 (0.75);
WP Brier 0.1808 (Primer 0.182), and 0.1823 vs the feed's own 0.1826 on the 873k balls where it has one.

Storage (migration `003_primer_metrics.sql`, applied to prod after backup b005): `metric_models`
(versioned params + validation), `match_par`, `ball_metrics` (2,395,328 rows, 283 MB; DB now 4.1 GB).
Loaded by `scripts/compute_primer_metrics.py full --write`; models in `ml/models/primer/` (.ubj,
11 MB). Nightly: workflow step `compute_primer_metrics.py incremental --write` (never refits;
new matches only) + a DB-size warning over 8 GB.

Surfaces: query builder grouped delivery mode adds impact / impact_per_100 / impact_per_innings /
raa(_per_100) / waa(_per_100) / wpa / avg_leverage (+ metric_balls, metrics_perspective; bowling
side when grouped by bowler without batter; `QB_PRIMER_METRICS=0` kill switch; cumulative mode
returns nulls). Goldens: additions only. Results table shows Impact by default when present,
hides all-null columns, explains the metrics. NL layer knows them ("most impactful IPL 2026
batters" → impact/raa/wpa + bar). MCP: ordered, described, ranked column always in the text
table. Scorecard: player Impact/WPA, `summary.primer` (Impact by over, WP path) → "Win probability ·
Impact" card; desktop summary now a story column + full scorecard. Player page: Impact section
(per season, via the QB API). Credits: glossary.

**Open:** ODI / women's T20 metrics (need their own curves); leverage-weighted variants and
adjusted Impact (Primer 5.3, 7.2); `/analytics/matches/{id}/resource-benchmark` still depends on
the never-created `venue_resources` (unused by the UI) — repoint to dl_curve if it gets a consumer.

### 2026-09-25 — T20-only pages always reachable (MensT20Scope) — Claude

Opening an ODI preview sets the site format to men's ODI (persisted), and the nav then disabled
every `t20Only` page — most of the phone More sheet. Now `FormatContext.MensT20Scope` wraps those
routes in App.js: it re-provides the context as men's T20 for the page's subtree and points the
analytics API client at T20 while mounted (restoring the site format on unmount). Nav items are
never disabled; the More sheet shows a "Men's T20" note when another format is selected.
Verified with the site on mens-odi: all sheet items enabled, player page's boundary-analysis
requests format=T20, and returning to /query still shows Men's ODI. Value building moved to
`buildContextValue` so the provider and the scope share it; `supportsT20OnlyPages` is now unused
by the nav (kept in the context).

### 2026-09-25 — Track U4: phone UX (filter summaries, ScrollTable, sticky QB execute, rankings paging, desktop scorecard) — Claude

New shared pieces in `src/components/ui/`:
* **`ScrollTable`** — drop-in for TableContainer (`paper` replaces `component={Paper}`; margin
  keys in `sx` go outside, the rest incl. maxHeight on the scroller). Edge fades show which side
  has more to scroll; `stickyFirstColumn` pins the name column. Swapped into all ~20 live tables;
  sticky first column on Matchups, Fantasy, preview leaders, Boundary Analysis.
* **`FilterSummary`** (+ `summarizeDateRange` / `summarizeCompetitions` / `joinSummary`) — with
  `collapsed` (phones, once results show) the page's unchanged form becomes one summary line +
  Edit, opening it in a bottom sheet; `data-filter-submit` on the page's GO/Compare closes the
  sheet. Used on Player, Team, Matchups, Doppelgangers, Batter/Team Comparison. The form remounts
  when it moves, so CompetitionFilter now gets `value=` everywhere it is used this way.
* **`TryExamples`** — one-tap presets (URL-param links) on Batter/Team Comparison and Matchups
  start states.

Page changes: QB filters folded by default on phones, "Advanced match context" / "Delivery
analysis" collapse on phones unless set, **sticky Execute** above the bottom nav (needed
`overflow-x: clip` instead of `hidden` on the QB root and its html/body GlobalStyles — `hidden`
makes non-scrolling scroll containers that `position: sticky` attaches to). Rankings: one-line
cards on phones, 25 per list + "Show more". Doppelganger method banners → "How it works"
`<details>`. Home pipeline grid → top 10 + "Show all". Fantasy planner off-season message.
Player: rolling `PROFILE_START_DATE` (6y, was frozen "2020-01-01"), Top Innings context no
longer wraps (table-layout auto on desktop), Global rank distinguishes "failed to load" from
"not ranked" and states the 50-balls-per-length rule. Theme: clickable small chips 32px and
Autocomplete clear/open 38px on coarse pointers; MatchHistory W/L tiles 32px on phones; form
strip / phase labels >= 11px. Radar on Batter Comparison fits phones.

**Scorecard:** desktop (>= 1000px) summary is two columns (result across, story left, full
scorecard always open right). Backend: result text pluralises ("won by 1 wicket"), derives the
bat-first margin when the feed lacks `outcome.by` and the target was not revised (DLS); worm
lines share one scale (format overs x match-high runs, was each innings stretched to its own
length and top score) and `summary.worm_axis` ticks are format-aware (ODI 10-50). Goldens:
scorecard_modern/legacy differ only in worm points + worm_axis (intended).

Sweep: `ui_sweep.mjs` now also reports offender ancestry/position, small-text and tap-target
samples, skips visibility:hidden (closed drawers), and takes `LOAD_MS`.

### 2026-09-25 — API on Python 3.12 (3.10 EOL Oct 2026); MCP lifespan restartable — Claude

* `.python-version` 3.10 → **3.12** (Heroku heroku-24), nightly workflow 3.11 → 3.12. Not 3.13:
  numpy 1.26.4 has no 3.13 wheels and the ML pins stay put. Every pin has a cp312 wheel.
* `sqlalchemy>=2.0.9,<2.1`: an unpinned rebuild would have jumped to 2.1.0 (behaviour-changing
  minor; drops the implicit greenlet dep). Upgrade it on purpose later.
* **MCP session manager is now restartable.** A `StreamableHTTPSessionManager` can run() once,
  and every TestClient re-runs the lifespan, so since Phase 1 all 24 `tests/test_sanity.py`
  tests errored. `mount_mcp` now returns a `run_mcp()` context factory that rebuilds the SDK
  routes (fresh manager) and swaps their handlers into the registered /mcp routes. Prod unchanged.
* Verified on a local 3.12 venv: app imports (61 routes, same as 3.11); pytest 109 passed,
  2 failed — both stale tests that fail identically on 3.11 (`Indian Premier League (IPL)` alias
  added since; partnership fallback SQL no longer uses `LEFT JOIN player_aliases pa_bat`).
  Golden A/B vs live 3.10: only the known `match_preview` top_ranked_players diff. Latest joblib
  models give identical predictions on 3.12 vs 3.11 (none are loaded by the API itself —
  Foresight reads `match_predictions`). MCP initialize/tools/list/find_entities OK.
* Local macOS note: xgboost needs `llvm-openmp` in the conda base to import at all.
* `Tests.py` (root, old bokeh script) imports distutils (removed in 3.12); nothing uses it.

### 2026-09-24 — Track U3: colour/contrast sweep; preview drops Similar, Dismissals, Venue Twins — Claude

**Preview sections sunset** (user call, "unless we find a better use"): Similar, Venue Twins and
Dismissals (the caught-dismissal field designer = the field-position callouts) are gone from
`VenueNotes.jsx`. Components (`VenueSimilarity`, `VenueDismissalAnalytics`) and the backend
endpoints are kept, unimported, for revival; the field designer still serves the player page.

**Finding theme escapes by rendering, not grepping.** `scripts/dev/ui_sweep.mjs` now probes
colour after the full-height resize: light *neutral* surfaces (HTML background or SVG fill; lime
and team colours excluded) and leaf text under 3:1 against its composited background (disabled
controls and text over gradients skipped). report.json gains `lightIslands`/`islands` and
`lowContrast`/`low`. `LOAD_MS`/`SETTLE_MS` for the slow local API. Live baseline was 8 light
islands + 180 low-contrast texts across 23 routes.

Fixes, by root cause:
* **Theme bug:** MuiChip `colorPrimary`/`colorSuccess`/… applied to *outlined* chips too, so
  they got near-black "on accent" text on a transparent chip. Now `filledX` / `outlinedX` keys.
* `utils/teamColors.textOn(color)` picks near-black or white by actual contrast (replaces
  LandingPage's local gamma-space version). Used for ELO rank badges (home + EloLeaderboard),
  player form pills, comparison player chips, wagon-wheel/pitch-map chips, boundary badges.
* `hindsightDark.fieldSvg` tokens: CaughtDismissalScatterMap, VenueBoundaryShape and the wagon
  wheels drew a #fafafa ground with slate labels.
* White comparison cards (BatterComparison/TeamComparison selected items) → background.paper.
* designSystem `neutral[400]` was textGhost (2.5:1) but ~20 sites use it for real captions →
  #5f6672 (~3.2:1). QB footer → textFaint. Preview NR segment/axis labels, phase-strategy cells
  (white on #55ae6a) deepened, GlobalT20Rankings table borders, BallRunDistribution labels sit
  inside the bar only when they fit, LineLength heat-cell captions brighter.

**Verified:** build OK; `check_theme_literals.sh main` clean; local sweep: 0 light islands and 0
low-contrast texts on all routes except Wrapped's logo "H" (white on Spotify green, brand).

**Left:** GuessInningsShareCard is a white exported PNG by design (restyle is a product call);
comparison_full still overflows horizontally on phones (tables → U4 ScrollTable).

### 2026-09-24 — Preview default windows; venue similarity format-pinned and cached — Claude

**Preview window (site + connector):** the match preview's default start is now 1 January,
8 years back for ODIs and 4 for T20s (`src/utils/dateDefaults.js` `getPreviewStartDate`,
`mcp_server/server.py` `_default_window`). App.js follows the pinned format until the user
touches the date, and the day/night toggle no longer widens the window on its own.

**Venue similarity (`services/venue_similarity.py`) had no format at all.** With no competition
filter it scanned every format; with one it pinned T20 regardless; phases were T20 over literals
(so ODI grounds were profiled on overs 0-19); caches ignored format. Now:

* `format`/`gender` on `/visualizations/venue/{v}/similar` and `/tactical-edges` (and passed
  through the nested call); `_build_delivery_details_filters` always pins one format; phase
  overs come from `format_config` via `_phase_overs`. `VenueSimilarity.jsx` sends both.
* **Pool cache.** The seven pool-wide queries do not depend on the previewed venue, so they
  moved into `_load_venue_pool`, cached by (format, gender, dates, competition filters) for 6h,
  max 8 entries. Zone filters (bat hand / bowl kind / style) are *not* in that key — they run
  one extra query. An end date of today or later is treated as none so keys survive the
  browser/server date skew.
* Phase query rewritten as per-innings then per-ground (the three `COUNT(DISTINCT
  p_match||inns)` sorts were 8.4s); phase x pace/spin folded into it; the "output" zone query is
  skipped when there are no zone filters (it was a duplicate).
* Verified byte-identical responses before/after the refactor for 7 cases (T20/ODI similar,
  All Venues, LHB zone filter, tactical edges T20/ODI-death). From a laptop against prod:
  cold T20 4y pool ~22s (was 26-29s), every other venue ~1s, zone-filter change 21.5s → 4.6s.
* Kingsmead ODI "not enough data" is correct: 4 ODIs since 2018, pool minimum is 5.

**Open:** a cold T20 pool is still ~20s; if it H12s on Heroku, precompute venue features nightly.

### 2026-09-24 — ODI fixtures, preview_match MCP tool, Home connector card — Claude

* **Matchups are format-specific** (verified: Marsh v Maharaj 6 off 7 in T20, 53-54 off 80 in
  ODIs, matching raw delivery_details).
* **Today's AUS v SA ODI was missing from Home/preview because the fixture scraper only allowed
  T20Is and top T20 leagues.** `services/fixture_scraper.py`: `_is_odi_event` (ESPN
  internationalClassId 2 / card "ODI", both sides top-20) + fixtures carry `format`. Home cards
  link with `fmt=mens-odi|mens-t20` and label ODIs. App-level `?fmt=` sync (App.js) replaces the
  query-builder-only one; preview resets its fetch guard on format change so it refetches.
* **Leaders bug (pre-existing, all formats):** `/venues/{v}/stats` with "all leagues" + include
  internationals selected internationals ONLY (Wankhede leaders were Bethell/Hetmyer). Now league
  matches + internationals, matching venue notes. Wankhede T20 leaders: SKY 1069, Rohit 792, ...
* **MCP `preview_match`** (venue, team1, team2, format T20|ODI, window defaults 3y T20 / 8y ODI):
  venue record, leaders, H2H, form, recent at venue, standout batter-v-bowler edges, deep link to
  `/venue?...&fmt=`. Calls the preview's own endpoint functions (late `import main`).
* **MCP aggregates-only:** `query_cricket_data` requires `group_by` — raw ball-by-ball rows
  (licensed feed) are not redistributed.
* **Home "05 / Connect" card** with the connector URL (copy button), Claude/ChatGPT steps and
  example prompts; pipeline section renumbered 06.

**Verified:** preview_match for Kingsmead ODI and Wankhede MI v CSK T20 (10-12s each); A/B goldens
vs live: 12/13 identical (known local match_preview rankings diff); Home card at 390px, no page
overflow.

### 2026-09-24 — Match preview format leakage + query builder mobile layout — Claude

User report (phone): an ODI preview (Kingsmead, AUS v SA) showed T20 numbers; top-teams input
blanked itself; query builder cards overflowed and the column dropdown was unusable.

**Findings:** "0 ODIs since 2021" and "~13 ODIs since 2008" were *correct* (Kingsmead's last
ODI in the data is Feb 2020; 14 since 2008, one excluded by top-10). But most preview sections
were format-blind or hard-coded to men's T20:
* `/venues/{v}/stats` (Leaders): every query `format = 'T20'` literal, no format param.
* `/venues/{v}/teams/{t1}/{t2}/history` (Recent/H2H/Form): no format filter at all — this also
  leaked ODIs into **T20** previews.
* `/venues/{v}/dismissals`: legacy `deliveries` only (T20, stops 2025-11) — no ODI, no 2026 T20.
* `/visualizations/venue/{v}/wagon-wheel|pitch-map`: T20 pin + T20 phases, and the international
  filter was `LIKE '%International%'`, which matches nothing (labels are T20I/ODI) — so
  "include internationals" never added T20Is to the venue field map either.
* `/boundary-analysis`: T20 phases, format not plumbed.
* `/teams/{a}/{b}/matchups`: service supported fmt, route never passed it.

**Done:**
* All six endpoints take `format` (T20|ODI, default T20) + `gender`; per-format phases via
  format_config / `phase_case_sql`; international label via `_international_bucket`. Dismissals
  now split legacy (<2015, men's T20) + delivery_details (>=2015 and all other formats) with
  names normalised (`leg before wicket`→`lbw`).
* Frontend: Matchups, VenueDismissalAnalytics, DismissalFieldDesigner (venue), BoundaryAnalysis
  send `pinnedFormatParams`; post-toss + fantasy top picks + Foresight hidden for non-men's-T20
  (T20 scoring/models) with a note; Explore links carry `fmt=`; QueryBuilder applies `?fmt=` on
  in-app navigation; venue header says "ODIs"/"T20s" by format.
* CompetitionFilter top-teams: draft text state, commit only 1–20 (NaN was stored and echoed).
* Query builder mobile: root grid had no column template, so its implicit column sized to the
  widest child (~520px) → every card clipped at 390px and menus anchored off-screen. Now
  `minmax(0, 1fr)`; filters header wraps; columns menu capped at viewport width. Fantasy tabs
  scrollable.
* `scripts/dev/ui_sweep.mjs`: overflow detection no longer treats `overflow: hidden` ancestors as
  scrollers (body is overflow-x hidden, which masked all clipping); added `preview_odi` route.

**Verified:** Kingsmead ODI via API — leaders Miller/Amla/de Villiers, ODI-only recent results,
ODI dismissals + ODI-phase boundaries, ODI XI in matchups (Marsh/Carey/Green/Head). E2E phone run
of the ODI preview: every request carries format=ODI. A/B goldens vs live (T20 defaults): 12/13
identical, match_preview = known local-environment rankings diff. Phone sweep: no clipping
except Home's intentional carousel.

### 2026-09-24 — Phase 1: Hindsight MCP connector (query builder for Claude/ChatGPT) — Claude

**Done** (branch `phase1-mcp`; see `docs/mcp-connector.md`):
* `mcp_server/server.py`: MCP Python SDK 2.2 `MCPServer` + `Apps` extension. Tools
  `find_entities` (players/teams/venues via services/search.py + competitions incl. aliases),
  `get_query_options` (enum values from /query/deliveries/columns), `query_cricket_data`
  (filters, group_by, sort_by, chart hints; returns a markdown table for the model,
  structuredContent for the view, and a /query deep link). All read-only.
* `mcp_server/widget.html`: MCP Apps view `ui://hindsight/query-result` — self-contained
  table/bar/line/scatter (inline SVG, no CDN), host light/dark theme, size-changed reporting.
* Mounted at exactly `/mcp` (SDK route added to FastAPI's router), stateless + JSON responses
  (main.py's BaseHTTPMiddleware breaks SSE). `main.py` now uses a `lifespan` (replaces the
  deprecated `on_event("startup")`) that also runs the MCP session manager.
* Guardrails: READ ONLY transaction + `statement_timeout` per call, 500-row cap, global
  60 calls/min budget, generic user-facing errors (details logged), `mcp_call` JSON log lines.
* `services/query_builder_v2.py`: `run_deliveries_query()` keyword entry point +
  `validate_format_bounds()` / `QueryValidationError` (route maps to 422, unchanged) +
  `GROUP_BY_COLUMNS` (route + tool share it; **adds `format`** to the advertised group-by list).
* `requirements.txt`: `mcp==2.2.0`; numerical/ML stack pinned to production's pip freeze
  (pandas 2.3.3, numpy 1.26.4, scipy 1.15.3, statsmodels 0.15.0, scikit-learn 1.7.2,
  xgboost 3.2.0, joblib 1.6.0). The nightly GH Action (Python 3.11) was silently getting
  pandas 3 / sklearn 1.9 from the unbounded requirements; it now matches production.

**Verified:** JSON-RPC tests (initialize, tools/list, resources/read, tools/call x9) against a
local server on the prod DB (read-only). A/B golden check vs the live API: 11/13 identical;
`qb_columns` differs only by `+format`; `match_preview` top_ranked_players differ **identically
on unmodified main** in the same local env (macOS x86 numerics in the rankings mixed model) —
environmental, not this change. Widget rendered in a test host at 390px and 720px, dark + light.

**Decisions / surprises:** Postgres.app blocks new local binaries behind a GUI permission
prompt, so local MCP tests ran against prod with READ ONLY sessions. Rate limit is global, not
per-IP (hosts call from shared IPs).

**Deployed:** a32a7b6 → Heroku v413; `/mcp` verified in production (all tools + UI resource).
Build installed the pinned stack + mcp 2.2.0 on Python 3.10.21.

**Memory (R14) — found and fixed on deploy day:** the 512MB Basic dyno had been logging R14
"Memory quota exceeded" every ~20s since at least 08:51 UTC (before this deploy): two uvicorn
workers idle at ~230MB each, so any heavy page (IPL predictions, doppelgangers, rankings) pushed
it into swap. Now `WEB_CONCURRENCY=1` with `DB_POOL_SIZE=8 / DB_MAX_OVERFLOW=4` (v414) — same 12
DB connections, one worker. Post-change sweep of the heaviest pages + MCP suite: 0 R14, 103×200.

**Heroku warning:** Python 3.10 reaches end-of-life October 2026 and Heroku will drop it. Moving
to 3.12 re-resolves the numerical stack (pandas 3 etc. need 3.11+), which shifts rankings and may
break the joblib ML models — plan it as its own chunk with a golden A/B, not a drive-by.

**Next:** add the connector in Claude and ChatGPT and try it; OAuth before wider sharing; Primer
metrics become query-builder columns (and so connector columns).

### 2026-09-24 — Track U2 (+ first U3 pass): one dark theme, mobile bottom nav — Claude

**Done** (branch `u2-dark-theme-mobile-nav`):
* **One theme.** `src/theme/hindsightTheme.js` (palette/overrides from the former scoped
  `previewDark`, type scale/shape from designSystem) is the global MUI theme via
  `src/theme/index.js`. `previewDark.js` deleted, the `/venue` ThemeProvider removed, and every
  `isQueryRoute ? qbColors…` branch in the App.js nav dropped. CssBaseline + `src/index.css` set
  `color-scheme: dark` and the page colour on html/body (no white first paint, no light iOS
  overscroll, dark native date pickers); `index.html` theme-color + `manifest.json` dark.
* **designSystem.colors remapped to dark equivalents** (neutral 0-100 surfaces, 200-300
  hairlines, 400-950 text; primary = lime accent scale; semantic 50/100 tints, 600-900 readable
  hues). ~40 components index these directly in sx; remapping flipped them without per-site edits.
  Added the missing success/warning/error 100 and 900 keys.
* **Mobile nav.** Below md: sticky compact header (logo, page title, search) +
  `src/components/nav/MobileBottomNav.jsx` (Home · Search · Preview · Query · More; More is a
  grouped bottom sheet: Explore / Compare / Play + Wrapped, Credits). Grouping lives in
  `navItems.js` (`group`, `PRIMARY_NAV_PATHS`, `MORE_NAV_GROUPS`). Old hamburger popover removed.
  Home shows the bottom nav too and hides its own Explore button below md. Header hidden on
  /wrapped (full-screen story). Query builder's own "Hindsight / Query Builder + Explore" row
  removed (duplicate of the app header at every width).
* **Sticky offsets** in `src/theme/layout.js`: VenueSectionTabs sit under the 52px header
  (`STICKY_BELOW_HEADER`), sections use `SECTION_SCROLL_MARGIN`.
* **Charts.** `src/theme/chartTheme.js`: registered ECharts theme `hindsight` (passed in
  VenueNotes + VenueSimilarity); Recharts axes/grid/legend/tooltip restyled globally in index.css.
* **U3 literal pass:** tooltips, grey.50 fills, white gradients (VenueNotesCardShell — the Team
  header card; RecentMatchesSummaryCard), primary-fill + white text → contrastText,
  `primary.light` is now a soft tint (icon circles), Search page rebrand + SearchBar defaults to
  dark, MatchHistory loser text (was #0f172a) + `readableOnDark()` in utils/teamColors.js for
  team-coloured text, VenueSimilarity heat cells, PitchMap export background, ZoomableChart.
* **Guard:** `scripts/check_theme_literals.sh [base]` fails on light backgrounds / near-black
  text in lines added vs base (`// theme-literal-ok` to allow one).

**Verified:** `npm run build` (pre-existing warnings only); literal check clean vs main;
`scripts/dev/ui_sweep.mjs` against local dev: all 20 routes body `rgb(10,12,17)`, no overflow,
no light islands in first screens; desktop 1440 sweep of home/search/query/preview/player/
rankings consistent; More sheet opened via CDP (grouped, active item highlighted).

**Known / next (U4):** Top Innings and team phase tables overflow/overlap on phones (need a
ScrollTable); "Filters & Grouping" title wraps on phones; filter forms still take the first
screen (bottom-sheet editor); Rankings still ~33k px on mobile; ~140 older literals remain in
less-visited components (wrapped/cards, EloRacerChart, FantasyPlanner) — dark-safe but not audited.

### 2026-09-24 — Track U1 (UI bug fixes) — Claude

**Done** (branch `u1-ui-bugfixes`):
* **Nav disabled for every new visitor.** "All formats" is the default slug, and the nav keyed
  `t20Only` pages off `isDefaultFormat`, so Player/Team/Comparison/Matchups/Rankings/games/Fantasy
  were greyed out on first visit (11 of 15 items in the phone menu). New
  `FormatContext.supportsT20OnlyPages` (T20 or ALL, men's); App.js uses it for tabs and menu;
  disabled menu items now say "Men's T20 only". Those pages never read the format, so "all" was
  always safe for them.
* **Player page "Failed to fetch".** ~15 sections fetched on mount against a 6-connection pool
  (2+1 per worker); router logs showed bursts of simultaneous 30s 503s. New
  `src/components/ui/LazySection.jsx` mounts sections near the viewport (first two eager) in
  `UnifiedPlayerProfile.jsx`. Match preview already had lazy activation. Pool resize pending (Phase 0).
* **Doppelgangers broken for every post-2015 player.** batting_stats/bowling_stats use legacy
  names before the 2015 split and current names after; the target was resolved to the legacy
  name. `services/search.py`: `_merge_rows_by_canonical_name` folds rows under the current name
  via `player_aliases`, target resolved to the current name, and both doppelganger queries are
  pinned to men's T20 (`DOPPELGANGER_FORMAT_PIN`) — they were blending ODIs in.
* **2026 IPL season invisible to IPL-specific queries.** The feed labels it `IPL`; 13 queries
  filtered `competition = 'Indian Premier League'`, so IPL Predictions had no match rows (Win
  Rate/Elo/Situational/Venue all 50 for every team) and team roster/H2H/games missed 2026.
  New `competition_aliases.sql_in_list()`; `IPL_COMPETITIONS_SQL` used in
  `services/ipl_prediction.py`, `services/team_roster.py`, `services/team_h2h.py`, `routers/games.py`.
* **Match preview, venue with no matches:** Summary now renders `EmptyState` with reasons + Edit
  filters, and venue-history sections are dropped (team sections kept). Boundary analysis ignored
  `top_teams` (showed 327 balls beside "0 T20s"); now plumbed route → service → helper → prop.
  Venue "similar" 404 ("not found in qualified pool") renders a not-enough-data empty state.
  Invisible white header card (literal white gradient) and `grey.300` bar fixed.
* **"Total deliveries" under All formats showed the ODI count.** refresh script wrote the count
  to the bare key on every leg (ODI last); now `scoped_key()`. `/query/deliveries/columns` sums
  per-format counts under ALL. Nightly workflow: T20 leg no longer `--skip-metadata` (metadata
  is per-format; the T20 dropdown cache was never refreshed nightly).
* `src/components/ui/EmptyState.jsx` extended (reasons/action/icon; palette colours) —
  backward compatible with its 10 existing callers.

**Verified:** local API against hindsight_local — doppelgangers found for V Kohli / Virat Kohli /
JJ Bumrah; leaderboard OK; IPL predictions now differentiate (RCB 62.6 … MI 34.7, win-rate
8.7–91.5). `npm run build` OK (only pre-existing warnings). CDP iPhone-emulation sweep of local
dev server: empty-venue state, player lazy sections, all 15 menu items enabled.
Golden check: 5 endpoints differ (qb_columns, qb_batter_vs_pace_by_length,
qb_death_overs_venue, landing_featured_innings, qb_legacy_pre2015_window) — **identical set on
a clean checkout (changes stashed)**, so pre-existing drift, not this work; goldens need a
re-capture once someone confirms those drifts are intended.

**Decisions / surprises:** headless `chrome --screenshot` cannot go below 500px wide — it faked
right-edge clipping on every page at 390px; use CDP `Emulation.setDeviceMetricsOverride`
(mobile sweep script to be promoted to `scripts/dev/ui_sweep.mjs`). Essential-tier plan changes
move the DB and rewrite DATABASE_URL.

**Deployed + Phase 0 (same day):** merged to main (ab453ab), `git push heroku main` (v411),
Vercel `hindsight` production Ready. `pg:backups:capture` → b004 (5.15 GB → 349 MB). `heroku
addons:upgrade … heroku-postgresql:essential-1` (~20 min read-only; DATABASE_URL rewritten to a
new host). Row counts identical for matches, batting_stats, bowling_stats, players, nl_query_log,
delivery_details (4,164,765), deliveries (1,835,431); pg_trgm and guess_innings_pool present.
`DB_POOL_SIZE=4 DB_MAX_OVERFLOW=2` (v412). GH secret `DATABASE_URL` and local `.env` updated.
Post-deploy phone sweep of home/player/venue_full/iplpred on the live site: one 503 left
(`/rankings/player/V Kohli?snapshots=6`, a slow query), down from bursts of five.

**Next:** after tonight's run confirm keys `total_deliveries` + `total_deliveries:ODI:male` exist
and the nightly job succeeds on the new secret. Then U2 (global dark theme + mobile bottom nav).

### 2026-08-01 — Chunks A6, A7, A8 — Claude — match preview redesign complete

**Done** — the preview is dark-themed and format-aware end to end. T20 goldens stayed 13/13
throughout.

* **A6** — filters extracted from the `/venue` route in App.js into
  `components/preview/PreviewFilters.jsx`, restyled dark. Verbatim extraction, so T20 output
  was provably unchanged going into A7. App.js 947 → 807 lines.
* **A7** — the 4-phase split now comes from `format_config` via `phase_case_sql` instead of
  three inlined T20 literals. `fmt`/`gender` threaded through `gather_preview_context` to phase
  stats, venue stats, team form, H2H and matchups. **Format added to the preview cache key.**
* **A8** — `/venue_notes` accepts a format; the frontend sends one; `PhaseWiseStrategy` derives
  its bars from config; and the child components are dark-themed via a scoped MUI theme.

**Two gaps A7 left that only showed up by reading the ODI output**

Neither was in the chunk brief, and both would have passed a "does it deploy" check:

1. **Venue stats reported T20 numbers in an ODI preview** — "avg winning score 197" at Wankhede.
   Not contamination: `build_competition_filter_delivery_details` pins correctly but defaults to
   T20, and nothing passed a format.
2. **Then ODI venue stats were paired with T20 team form** — "India WWWLL; batting first scored
   192, 219, 233" against an ODI benchmark of 395. Five `matches` queries in the history and H2H
   path had no format predicate at all.

**And a gap A7 left overall:** the backend was format-aware but *unreachable* — the frontend sent
no format and `/venue_notes` did not accept one. Backend format-awareness is not done until a
caller can actually select it.

**On the restyle approach.** ~370 MUI surfaces across a dozen components versus ~14 hardcoded
light literals. A scoped `ThemeProvider` on the `/venue` route handles the 370; the literals were
fixed by hand. Global theming was rejected deliberately — it would restyle every page in one
untested step. White text on coloured backgrounds (W/L/NR badges, boundary chips, phase strip)
was left alone; it is already correct on dark.

**Open, not fixed:**
* An ODI phase response returned only two of four buckets at Wankhede. May be legitimate sparse
  data in the default window, may be real. **Check before trusting the ODI preview.**
* Avg winning score of 395 at Wankhede looks high even for ODIs, off a 9-match sample.
* `MULTI_FORMAT_PLAN.md` line references for A6-A8 were all stale. Verify before trusting others.


### 2026-07-27 — Chunk A1 — Claude — ODI load complete, pipeline running

**Done**
- **Full ODI load: 1,647,737 balls, 3,248 matches, 2000-01-09 to 2026-07-25.**
- Production golden baseline captured (`scripts/goldens/prod/`, 13 endpoints) while `matches`
  was still T20-only, so the match sync has a clean before-state to diff against.
- Verified the format pins hold against real post-2015 ODI data — see CURRENT STATE.

**Four failures on this load, four distinct bugs, all in ingest code**

Worth reading as a group, because they share one cause: **the ODI feed differs from the T20
feed in ways the 349-match dev slice did not contain.** The slice was too small and drawn from
too early in the file to hold any of them. Code was tested against data easier than reality.

1. **Over-cap guard aborted on any ball past the cap.** One 2005 West Indies innings runs to 51
   overs — 11 balls out of 1,647,737. Made proportional (`OVER_CAP_BREACH_LIMIT = 0.01`);
   confirmed a genuinely mislabelled file still aborts, at 56.7%.
2. **Same guard, second run.** Both attempts stopped at exactly 500,000 rows. I wrongly blamed
   the Mac sleeping; an identical stopping point should have ruled that out immediately.
3. **`load_delivery_details_full.py` — pandas re-inferred coerced integers back to float64**
   when nulls were present, so `"322.0"` was rejected for an INTEGER column 1.6M rows in. Fixed
   by building the Series with `dtype=object`.
4. **`backfill_advanced_data.py` — temp-table column types did not match the real table.**
   The bulk update does `COALESCE(dd.col, t.col)`; when a numeric column arrives as a decimal or
   uses `"-"` for a gap, pandas leaves it as object and `to_sql` creates TEXT. Postgres rejects
   the statement outright.

**On bug 4, note what fixing it column-by-column cost:** `control` was already handled, then the
run failed on the wagon trio, then on `pred_score`/`win_prob` — three round trips through a
multi-hour job. The fix now reads target types from `information_schema` and coerces to match,
which covers all nine advanced columns and any added later. Verified by round-tripping real ODI
rows through `to_sql` and running the actual `UPDATE ... COALESCE` against `delivery_details`.

**Trap for whoever picks this up:** judge that fix by whether the `COALESCE` type-checks, not by
whether the types match exactly. `text` vs `varchar` and `bigint` vs `integer` are both fine —
my first probe reported "STILL BROKEN" purely because it compared type names.

**Data note, not acted on:** the ODI feed uses `-1` as a sentinel in `pred_score` and `win_prob`
(first-innings early balls). Stored as-is, matching how T20 already behaves. Consistency with
T20 was judged more valuable than cleanliness; revisit if either column is ever surfaced in UI.

**Expected gap, not a bug: 195 ODI matches have balls but no `matches` row.**

`delivery_details` holds 3,248 distinct ODI `p_match`; `matches` got 3,053. The sync reported
`Errors: 0` because it skipped them deliberately. All 195 fail the `HAVING MIN(over) = 0` gate
on innings 1 — the feed's coverage starts partway through (over 3, 4, 8, in one case 49), and 16
have no innings 1 at all. 65,708 balls, spread 2000-2024 across every ODI competition, so it is
source incompleteness rather than a boundary artifact. The gate is right: building a match row
from partial ball-by-ball data would produce wrong totals. Leave it. If these are ever wanted,
they need a `partial_coverage` flag, not a relaxed gate.

**OPEN: the format-pin surface is far larger than chunk 0.4g assumed.**

A crude audit (`(FROM|JOIN) (delivery_details|batting_stats|bowling_stats)` vs any format
predicate) reports **46 of 53 service/router files with zero pins**. Do **not** read that as 46
bugs — it is a lead list, and most entries are safe for one of three reasons:

* **Keyed by `match_id`/`p_match`** — a single match is inherently one format. This is why both
  scorecard goldens stayed identical despite `match_scorecard.py` showing 5 unpinned reads.
* **Scoped by competition** — `team_roster.py` and all the `wrapped/*` cards filter to
  `competition = 'Indian Premier League'`, which is T20 by construction.
* **Pinned through a helper the regex cannot see** — `delivery_data_service.py` embeds
  `format_filter_sql("dd", ...)` inside `build_competition_filter_delivery_details`, so its
  reads are pinned via `{competition_filter}`.

**The real risk is cross-match aggregates that are neither competition-scoped nor match-keyed.**
All three bugs found so far were exactly that shape.

Sweep progress against that list:

| file | reads | verdict |
|---|---|---|
| `services/relative_metrics.py` | 8 | **FIXED** (v384) — see below |
| `services/resource_benchmark.py` | 3 | safe, match-keyed |
| `routers/player_line_length.py` | 7 | **FIXED** (v385) — was 68% wrong for Kohli, see below |
| `services/rolling_form.py` | 10 | **still to check** — 4 competition-scoped, 6 not |
| `services/search.py` | 10 | **still to check** — heavily competition-scoped, verify `:leagues` empty is not a no-op |
| `services/venue_similarity.py` | 9 | **still to check** |
| `services/bowling_context.py` | 3 | **still to check** |
| `services/venue_boundary_shape.py` | 2 | **still to check** |

**`relative_metrics.py` was the worst found so far**, because the contamination was in the
*comparison cohort*, not the player's own numbers. In the default last-50-matches window the
cohort held 89 ODI innings (avg 28.07 balls) beside 353 T20 innings (avg 13.67) — a ~21%
inflated baseline that depressed every T20 player's percentile. Eight aggregates pinned, plus
`_resolve_effective_start_date`, where "the last N matches" was being computed across formats
(observable: the window start moved 2026-07-14 → 2026-07-12 at the default window of 50).

**`player_line_length.py` was the most badly wrong endpoint found.** Virat Kohli's *T20* line
and length profile was built from 22,982 balls — 15,653 of them ODI, so **68% wrong format**.
Because the global baseline was equally contaminated, the error was invisible from the numbers
alone: his good-length strike rate read 98.0 against a benchmark of 91.4. Pinned, they read
123.2 against 107.4. Verified to the ball: 7,329 / 7,305 / 7,304 matches the T20-only counts.

**Two traps this file demonstrated, both worth checking for in the remaining files:**

1. **A pin inside a plain string does nothing but break the query.** Six of the seven sites were
   f-strings; the seventh was not, so it would have sent a literal `{FORMAT_PIN_SQL_BARE}` to
   Postgres and 500'd the endpoint. Always verify the placeholder is inside an f-string —
   `grep` for the constant is not enough.
2. **A contaminated metric and a contaminated baseline hide each other.** Both moved by roughly
   the same proportion here, so the *shape* of the profile looked plausible throughout. Do not
   sanity-check these by eye; compare against a format-pinned count from the database.

**Watch for this shape when checking the rest:** a filter parameter that is a no-op when empty.
`build_matches_filter_sql` with `leagues=[]` and `include_international=False` returns nothing at
all, so an endpoint can look competition-scoped while actually being unscoped for the default
call. That is why the crude audit's `comp_scope` count cannot be trusted on its own.

`services/ipl_prediction.py` (18 reads) and `services/wrapped_legacy.py` (38) are large but
IPL-scoped; check the scoping holds rather than pinning blindly.

**Method that worked, use it again:** grepping for unpinned SQL found nothing on its own — both
bugs were caught by *diffing live endpoint responses* against a captured baseline and then
tracing the moved number back to its query. Reading code missed `matchups.py` entirely.

### 2026-07-26 — Chunk A11 (partial) — Claude

**A9 introduced a bug that this fixed.** Making ELO per-format left the rankings query
partitioning by team alone, so a team's "latest" rating became whichever format it played most
recently and one table mixed T20 and ODI ratings. `services/elo.py` and `/teams/elo-rankings` are
now scoped, and the landing page sends the format and re-fetches on change. T20 now tops with
England 1716 over 112 teams; ODI with South Africa 1611 over 16.

Worth generalising from: **each chunk that makes something format-aware can leave a consumer
reading the now-ambiguous column.** After a change like A9, grep for readers of the affected
column rather than assuming the write side is the whole job.

Also unified the landing page's mobile breakpoint — it used a hand-picked `max-width:759px` while
`App.js` uses the theme's `sm`.

**`/landing/featured-innings` is now format-aware** — pinned on format, with the "standout"
strike-rate threshold taken from that format's benchmark band rather than a T20 constant of 130.

**⚠️ Caches keep being the trap.** Featured innings looked like it worked and did not: the
response cache was one global entry with no format in the key, so whichever format asked first was
served to every other. ODI was returning T20 innings at SR 207 and looking plausible. That is the
**third** instance — after `query_builder_metadata` (0.6) and the analytics response cache (0.7).
**When making anything format-aware, check its cache key before believing the result.**

**Still outstanding for A11: `/recent-matches/discover`.** I attempted it and **reverted**, so
the endpoint is untouched and working. Worth reading before the next attempt:

The format *pin* was easy and worked — ODI correctly narrowed to 3 matches against T20's 116.
What defeated it in the time available is that `'T20I'` is hardcoded as the international label
in at least four layers: three SQL `CASE` expressions and a `SELECT` literal
(`services/recent_matches.py` around lines 555, 607, 612, 717), the Python grouping key in
`_competition_stats_from_rows`, the group label in the grouping loop, and `_display_competition`
itself. Binding it as `:intl_label` fixed the labels but broke the endpoint with an empty-string
error I did not finish tracing — the first query in the chain still succeeds in isolation, so the
failure is further down, most likely a query whose params dict does not carry the new binding.

Suggested approach next time: add the binding to **one** query at a time and test after each,
rather than replacing all four literals at once. Also check the `priority` ordering expression,
which may reference the same literal.

### 2026-07-26 — Chunk A9 — Claude — per-format ELO

Done before A1 deliberately: ELO was computed chronologically over every match with ratings held
in a dict keyed by team name alone, so the moment real ODI data reached production a team's ODI
results would have moved its T20 rating. Each `(format, gender)` is now its own pass with a fresh
calculator, and all four selection points are scoped.

**Two leaks that only measurement caught.** The first run logged "T20: 0 matches missing" and yet
moved the T20 checksum — `get_matches_after_date` was still being called without a format, so the
ODI pass pulled in every format's matches. The missing-count check had the mirror-image flaw: it
counted all formats, so once one pass filled its own matches the next reported nothing to do.
Reading the code suggested it was fine; only comparing checksums before and after showed it was not.

**Verified by isolation, not absolute values:** nulling ODI ratings and recomputing leaves the T20
checksum byte-identical, and a second pass finds nothing to do. ODI ratings are era-plausible,
Australia top at 1683 in 2006.

⚠️ **Local ELO legitimately differs from production** and always will: ratings depend on the full
match history, and the local database is a 3,926-match subset of production's 11,500. My first
verification attempt compared a local recompute against a production-derived checksum and
"failed" for that reason alone. Do not treat that gap as a bug.

One golden moved — the match preview's ELO line — and was re-captured.

### 2026-07-26 — Chunks A3 and A5 — Claude

Both chosen deliberately as the Phase A work that needs no production load and no spend, so they
could be built and verified against the local ODI slice.

**A3 query builder UI.** Over inputs were capped at 19 and the innings dropdown hardcoded to two
entries, so the UI could not express an ODI query even though the backend has accepted one since
0.6. Both now come from the selected format, with the cap shown in the field label. All three
requests carry the format, including the columns lookup — its values are cached per format, so
without it an ODI query was offered the T20 competition list. That fetch re-runs on format change.

**A5 scorecard.** The phase breakdown used a hardcoded `over < 6 / over < 15` CASE with "1-6"
labels, so an ODI card split at T20 boundaries. Now from format_config: an ODI reads
Powerplay 1-10, Middle 11-40, Death 41-50. The chase note no longer subtracts from a literal 120
— it uses the format's innings length, prefers the innings' own allowance for rain-reduced games,
derives the target from the innings before the chase, and returns nothing for Tests. The
result-text wicket-margin fallback is guarded to two-innings matches.

Verified: T20 caps at over 19 with 38 competitions, ODI at 49 with 3; an overs 41-50 ODI filter
resolves to the death phase over 12,046 balls; a 2006 England v Ireland ODI renders with correct
phases and a Target 302 note. Goldens 13/13 throughout.

### 2026-07-26 — Chunk 0.8 — Claude — PHASE 0 COMPLETE

**Sunset endpoints pinned to men's T20.** `main.py`'s 23 raw-SQL queries are pinned by wrapping
the table in a filtered subquery rather than editing 23 different WHERE clauses — a subquery
cannot interact with existing filter logic, and Postgres pushes the predicate down.

**Grep was not sufficient, and only querying the endpoint revealed it.** `/players` is built with
the SQLAlchemy ORM rather than a SQL string, so the textual substitution missed it and the
endpoint still returned ODI-only players. Four ORM sites needed the filter added directly.
`/players` now returns 5,668 names instead of 6,146, and Andrew Strauss, Ed Joyce and Geraint
Jones — ODI-only in the local data — are correctly absent. **Lesson for later chunks: pinning by
pattern-matching SQL text leaves ORM queries untouched.**

**Navigation defined once.** `src/navItems.js` replaces the four hand-maintained copies in
`App.js` (tab-index map, title map, desktop Tabs, mobile Menu). Verified against the originals:
all 15 entries match on label, tab index and title.

Eleven entries carry `t20Only`. They stay reachable but are disabled in both navs when a non-T20
format is selected, because their endpoints are now T20-pinned and would otherwise render an empty
page that reads as broken rather than out of scope.

### 2026-07-26 — Chunk 0.7 — Claude — frontend foundation

**Done:** `src/theme/hindsightDark.js` is now the only definition of the dark design system;
`queryBuilderTheme.js` is a thin alias so its seven importers are untouched, `LandingPage` maps
its short names onto the shared tokens, and the tokens are published as CSS custom properties
(`--hs-*`) for stylesheets that cannot import JS. Added `src/context/FormatContext.jsx` (fed by
`GET /formats`, persisted to localStorage and `?fmt=`) and `src/components/FormatSwitcher.jsx`
in both the mobile and desktop headers.

**No visual drift, proven rather than eyeballed:** every token was compared against the previous
definitions. All 19 query-builder tokens are byte-identical. The only change anywhere is the
landing page's `hairline`, 0.06 → 0.07 alpha — the pre-existing drift between the two copies,
now reconciled.

**Notes for the next session**
- `analyticsApi.js` holds the active format at module level and `FormatProvider` pushes the
  selection into it, so anything already routed through that module becomes format-aware without
  touching the 132 inline `config.API_URL` fetches. Migrating a call site to `analyticsApi` is
  now how you make it format-aware.
- Switching format clears the analytics response cache, otherwise a switch can serve the previous
  format's numbers from cache.
- `matchScorecard.css` still contains its own hex literals. The CSS variables exist for it now,
  but the substitution has not been done — worth doing when the scorecard is next touched.
- Two stray `#0a0c11` literals remain in inline JSX styles (`search/SearchBar.jsx:237`,
  `scorecard/MatchScorecardPage.jsx:641`). Cosmetic, not duplicate palettes.
- There is no browser driver in this environment, so nothing was screenshotted. The token
  comparison above is the substitute; a human should still glance at the landing page and query
  builder before this ships.

### 2026-07-26 — Chunks 0.9 and 0.10 — Claude

**0.10 player-name canonicalisation — COMPLETE (local).** `ALIAS_MAP_CTE` and
`UNAMBIGUOUS_ALIASES` in `services/player_aliases.py`; applied to the batting and bowling
stats-mode grouping, and the six previously-bare `player_aliases` joins behind the
`non_striker`/`partnership` groupings now go through the deduplicated source.

* Kohli returns as **one** row (3,660 runs, average 46.92) where there were two.
* Grouped totals match the raw table exactly — 1,175,427 runs over 67,301 rows collapsing to
  5,456 groups — proving the join does not fan out.
* **39 ambiguous legacy names are deliberately excluded.** `scripts/report_ambiguous_aliases.py`
  classifies them: 25 are genuinely different players, including **`DJ Bravo` → Darren *and*
  Dwayne Bravo**, `MW Short` → D'Arcy and Matthew Short, `RK Singh` → Rinku and Rupesh Singh.
  Collapsing those would have merged real careers and shown it without any hint of a problem.
* Fixed an unstable sort found on the way: `ORDER BY innings_count DESC` had no tiebreaker, so
  merely adding a join reshuffled the leaderboard. Same class as the scorecard bug in 0.2.

**0.9 production backfill — COMPLETE.** Backup `b002` captured first (the only prior backup
was from 2025-05-24, 25 MB — not a usable rollback). Migration 001 applied to production as a
newly-discovered prerequisite. A 50-match batch behaved correctly (455 rows repaired), then the
full run completed over all 10,219 matches in about 2h20m at ~1.2 matches/sec (network-bound
against RDS, not CPU).

**Result on production:**

| | Before | After |
|---|---|---|
| Impossible wicket counts | 52,070 of 185,050 (28%) | **74 of 182,062 (0.04%)** |
| Average wickets per batting innings | 4.876 | **0.767** |
| Maximum | 80 | **3** |

The 74 survivors are source-data anomalies — the feed flags the same batter dismissed more than
once in one innings — not a code fault, and the same pattern seen locally. Integrity is clean:
zero orphans and zero half-written matches.

**Live endpoints confirmed fixed:** batting averages now read Pooran 38.17, de Kock 28.26,
Sikandar Raza 26.09 (was **2.61**); team phase averages read 32.44 and 20.26 (was **4.22**).

**Note for whoever picks this up:** the backfill is network-bound against RDS — roughly 1.5% CPU,
all round-trip latency — so it takes hours rather than minutes. Run it **detached** (`nohup`);
a first attempt was killed with the tool session that started it.

**What the interruption cost, and what it did not.** Corrupt rows had already dropped from
51,615 to 36,049 when it stopped, and that progress survived. An integrity sweep found **no
half-written matches** — every match has both batting and bowling stats or neither, which is what
the delete-and-rebuild-per-match design is meant to guarantee. One match (`1018875`, a CPL 2016
game with only its second innings recorded) was left with its stats deleted and not rebuilt;
recomputing it restored 4 rows and there are now zero orphans among matches that exist in the
`matches` table. Thirty other `delivery_details` matches have no stats, but they are not in the
`matches` table at all and predate this work.

The script now commits every 50 matches instead of 200, so an interruption loses less, and takes
`--match` for repairing a single game and `--resume-from` for continuing a partial run.

### 2026-07-26 — Chunk 0.6 — Claude — query builder is format-aware

**Done:** `format`/`gender` request parameters (default men's T20); over and innings bounds
validated against the format instead of fixed `le=19`; the phase grouping expression on the
delivery_details path now comes from `format_config`.

**Verified:** goldens 13/13 on defaults; an ODI query returns 149,599 balls with phase strike
rates of 70.3 (powerplay) / 75.5 (middle) / 106.8 (death) — the right shape for the format;
`over_max=45` gives 200 for ODI and 422 for T20; `innings=4` gives 200 for Tests and 422 for ODI.

**Left open:** `/columns` format scoping, see CURRENT STATE. The legacy `deliveries` grouping map
deliberately keeps its hardcoded phase literal — that table holds only men's T20 from before
2015, so the T20 split is correct there by construction.

### 2026-07-26 — Chunk 0.4d/0.4e/0.4f + 0.5 — Claude — 0.4 COMPLETE

**Done**
- **0.4d loader** — required `--format`/`--gender`, column stamping, nine new source columns in
  `COL_MAP`, and an over-vs-cap sanity check.
- **0.4e sync** — `overs` from play, normalizer wired into `competition`/`event_name`/
  `match_type`, `day_or_night` from the feed, format/gender stamped onto `matches`.
- **0.4f** — `phase_bounds()` in `sync_stats_from_dd`, fantasy gated on an implemented-ruleset
  registry.
- **0.5 (folded in)** — `table_routing()` replaces the 2015 date fork in both hero paths.

**Verified end-to-end on the local database**
- Mislabelling the ODI slice as T20 aborts (over 49 vs cap 19), exit 1.
- 149,599 ODI balls loaded; 257 ODI matches created; 4,201 batting and 2,985 bowling stat rows.
- `overs`: 184 matches at 50, rest 45-49 for shortened games, **never 20**.
- `competition`: ODI 228, ICC World Cup 15, ICC Champions Trophy 14. `match_type` international
  for all 257. `event_name` keeps the series name.
- ODI phase split 28k/77k/18k — middle-dominant, as ODI boundaries imply.
- ODI `fantasy_points` NULL; T20 untouched.
- A 2007 World Cup ODI scorecard renders (Scotland 136/10 in 34.1 overs) where date-based
  routing previously returned nothing.
- **Goldens 13/13 identical at every step**, including with two formats in both
  `delivery_details` and `matches`. That is the contamination canary — the single-table design
  and the 0.4g pins both hold.

**Proof the phase swap is a no-op for T20:** recomputing 493 batting innings with the old
hardcoded tuples and the new format-driven ones produced **zero** differences. (Comparing against
*stored* rows is not a valid test — see below.)

---

### ⚠️ 2026-07-26 — PRE-EXISTING DATA BUG FOUND — needs a backfill decision

**What is wrong.** `delivery_details.out` and `bat_out` are `VARCHAR` holding the strings
`'true'`/`'false'`, not booleans. `sync_stats_from_dd.py` tested them with plain truthiness, and
the string `'false'` is truthy in Python — so **every ball counted as a wicket**.

A second, subtler error sat on top: a wicket falling on a ball a batter faced is not necessarily
*that batter's* wicket, because the non-striker can be run out at the bowler's end. `bat_out`
distinguishes the two (3,738 striker dismissals vs 3,939 total wickets in the ODI slice).

**Two traps for anyone touching this code:**

1. **Do not switch to `p_out == p_bat`.** It looks equivalent and agrees with `bat_out` for ODIs
   (3,738) and Tests (2,802), but it is **broken in the T20 feed** — the two id columns never
   match on any of the 7,961 T20 wicket balls in the sample. Using it would credit every T20
   batter with zero dismissals. `bat_out` is the only signal that works across all three feeds.
2. **`bat_out` is not a dismissal flag on its own.** Outside wicket balls it is `'true'` on almost
   every delivery in the ODI and Test feeds (149,398 of 149,599 ODI rows). It only carries meaning
   in conjunction with `out`.

**Casing differs between the two sides of the pipeline:** the source CSVs write Python-style
`'True'`/`'False'`, the loaded table holds lowercase `'true'`/`'false'`. So a bare `== 'true'`
works against the database and silently matches nothing against a CSV — the comparison must be
case-insensitive.

**Blast radius in the stored data** (`batting_stats.wickets` can only ever be 0 or 1):

| Rows | Impossible (`wickets > 1`) | Share |
|---|---|---|
| All T20 (63,704) | 21,905 | **34.4%** |
| 2026 matches (12,176) | 11,309 | **93%** |
| 2025 matches (21,401) | 6,648 | 31% |
| 2024 matches (22,194) | 3,948 | 18% |
| 2013-14 matches (7,933) | 0 | 0% |

The clean pre-2015 rows come from the legacy `statsProcessor.py` path; the corruption is entirely
from the `delivery_details` sync, and it grows as more matches arrive through it. The maximum
stored value is **76 wickets for a single batter in a single innings**.

**Code is fixed** (`_truthy`, `_is_out`, `_batter_dismissed`), so anything synced from now on is
correct — ODI rows came out with wickets only ever 0 or 1. **The stored T20 data is still wrong.**

**Decision needed:** re-run the stats sync for affected T20 matches. It is a delete-and-recompute
of `batting_stats`/`bowling_stats` for matches from 2015 onward, which is why it wants an explicit
go-ahead and a backup rather than being folded in silently. Worth checking first which
user-visible features read `batting_stats.wickets` and phase wickets, to gauge how visible the
error currently is.

**Also noted:** recomputed `balls_faced`/`dots` differ from stored values by 1-3 on some innings.
That is a *separate*, pre-existing discrepancy between the legacy and delivery_details paths, not
caused by this work — the old-vs-new isolation test showed zero differences. Worth a look before
any backfill, since a backfill would move those numbers too.

---

### 2026-07-26 — Chunk 0.4a/0.4b — Claude — data sources, Test recon, migration 002

**Done**
- All four dataset URLs into `.env`; `make_csv_slice.py` gained `--url-env` (there is deliberately
  **no `--url` flag** — the links carry an access key and this repo is public).
- `scripts/migrations/002_delivery_details_source_columns.sql` applied locally: `tournament`,
  `season`, `daynight`, `trophy_name`, `rain`, plus Test-only `day`, `session`, `trail_by`,
  `lead_by`. `recreate_delivery_details.sql` updated to match.
- Slices built for all three formats.

**The big finding: the four CSVs do NOT share a schema.** My earlier claim that the ODI file has
"the exact same schema as t20_bbb.csv" was **wrong**. Actual differences:

| | extra columns | missing columns |
|---|---|---|
| `t20_bbb.csv` | `bowl_runs`, `bowl_wkt` | `rain`, `gmt_offset` |
| `odi_bbb.csv` | `rain`, `gmt_offset` | `bowl_runs`, `bowl_wkt` |
| `test_bbb.csv` | `trail_by`, `lead_by`, `day`, `session` | `max_balls`, `inns_runs_rem`, `inns_balls_rem`, `inns_rr`, `inns_rrr`, `rain`, `gmt_offset` |

**`test_bbb.csv` has no `max_balls` column at all.** Anything that reads it must tolerate absence,
not just a zero or NULL value. Good news: `scripts/load_delivery_details_full.py:124-125` already
keeps only mapped columns that exist, so a missing column is skipped rather than crashing.

**Test recon (front-loads chunk C0)** — from `test_slice.csv`, 85 matches, 2020-2025:
- `inns` spans **1-4** as expected: 69 matches have 4 innings, 15 have 3 (innings wins and draws),
  1 has 2.
- `over` **resets per innings**; the longest innings in the sample reached over 197. So
  `UNBOUNDED_OVER_MAX` was raised from 199 to 299 in `format_config.py` — 199 was uncomfortably
  close to real data.
- **`day` (1-5) and `session` (1-3) are real columns.** Sessions are how Tests are actually
  structured, so Phase C should revisit whether the over-based new-ball/old-ball buckets in
  `format_config.py` are the right phase model at all. Noted in a comment there.
- `winner` is `'-'` for draws (7 of 85). `target` is populated on every row, including first
  innings — do not treat "has a target" as "is a chase".
- ~1,683 balls per match on average.

**Verified, do not "fix" this:** the CSVs are **1-indexed** on `over` (ODI 1-50, Test 1-197) while
`delivery_details.over` is **0-indexed** (T20 rows run 0-19). `load_delivery_details_full.py:131-132`
already subtracts 1. Anyone comparing a CSV over number to a database one will otherwise be off by
one over, which silently shifts every phase boundary.

**Also fixed:** the URLs in `.env` had to be **quoted** — they contain `&`, so an unquoted value
breaks `source .env` (bash treats it as a background operator and truncates the URL).

**Next:** 0.4c competition normalizer, then 0.4d/0.4e loader and sync, then 0.4g (pin the
format-blind consumers) before any ODI data is loaded locally.

---

### 2026-07-26 — Chunk 0.4c/0.4g/0.4h — Claude

**Done**
- `services/competition_normalizer.py` — `normalize_competition()`, `resolve_event_name()`,
  `is_international()`, plus `unmapped_competitions()` for auditing.
- **Pinned the format-blind consumers** (0.4g): `format_filter_sql()` now scopes
  `delivery_data_service.build_competition_filter_delivery_details` (backs the match preview and
  six other services), `query_builder_v2.build_where_clause`, and all six condition lists in
  `services/visualizations.py` (via a `T20_MEN_PIN` constant — those pages are being sunset, not
  made format-aware). All default to men's T20, so nothing changes until 0.6 threads the format
  parameter through.
- **Retired `cleanup_non_t20.py`** (0.4h) — now prints why and exits 1.

**Why 0.4g could not wait for the 0.6/0.8 gating chunks**
Three separate places decided "this is domestic cricket" by *negating* a competition name
(`dd.competition != 'T20I'`), which an ODI or Test row satisfies just as well. The query
builder's `delivery_details` path was worse: with neither `leagues` nor `include_international`
set it emitted **no competition predicate at all**. Any of these would have started silently
mixing formats the moment ODI rows landed — which happens during this very chunk's verification.
The legacy `deliveries` table needs no pin; it is men's T20 pre-2015 by construction.

**Verified**
- Normalizer against all three slices: ODI (349) → `ODI` 298, `ICC Champions Trophy` 30,
  `ICC World Cup` 21; Test (85) → `ICC World Test Championship` 73, `Test` 12; no blank buckets,
  every match keeps a specific `event_name`.
- **T20 is a provable no-op**: across all 2,874 T20 matches in the slice, every normalized bucket
  equals the raw feed value verbatim, and `is_international()` agrees with the legacy substring
  rule on all 2,874. That was the requirement.
- Goldens **13/13 identical** after the pinning work.
- Landmine drill: `python cleanup_non_t20.py` exits 1 and leaves the database untouched.

**Decisions / surprises**
- `trophy_name` is the best normalization key — it collapses sponsor renames that `competition`
  splits apart: "VB Series", "Carlton & United Series", "Commonwealth Bank Series" and "Carlton
  Series" are all one tournament under the trophy "Australian Tri Series (CB Series)".
- Tests never leave `competition` empty, but the values are inconsistent per series ("Zimbabwe in
  BDESH Test" vs "Zimbabwe in Bangladesh Test"), with `WTC` for World Test Championship matches.
- `is_international` deliberately branches: ODIs and Tests are only played between countries, so
  team names settle it; T20 keeps the historical competition-substring rule so existing rows do
  not move.

**Next (the remaining half of 0.4)**
1. **0.4d loader** — `--format`/`--gender` flags on `scripts/load_delivery_details_pipeline.py`
   and `load_delivery_details_full.py`; stamp the columns; extend `COL_MAP` with the nine new
   source columns; add the single over-vs-`over_max` sanity check.
   *Note `load_delivery_details_full.py:124-125` already skips CSV columns that do not exist, and
   `:131-132` already converts 1-indexed CSV overs to 0-indexed — do not duplicate either.*
2. **0.4e sync** — in `sync_from_delivery_details.py`: derive `overs` from the highest over
   bowled (not `first_row.max_balls`, which Tests do not even have); `competition`/`event_name`/
   `match_type` from the normalizer; `day_or_night` from the new `daynight` column; stamp
   format/gender onto `matches` and the stats tables.
3. **0.4f** — `phase_bounds()` in `sync_stats_from_dd.py:95,170`; fantasy only when
   `format_config` declares a `fantasy_ruleset`.
4. **0.5 (folded in)** — swap `query_builder_v2.py:23-24` and `match_scorecard.py:17` to
   `table_routing()`. Required: the ODI slice is 100% pre-2015, so without this the loaded data
   returns nothing from either hero feature.
5. **Then load the ODI slice and re-run the goldens** — they must still be 13/13. That is the
   contamination canary and the first real test of the single-table design.

### 2026-07-25 — ODI data recon (unplanned, gates chunk 0.4) — Claude

Pulled a real ODI slice to de-risk 0.4 and found two things that change the plan.

**1. `max_balls` is NOT a reliable format signal — this breaks the planned approach.**
The plan (and `sync_from_delivery_details.py:172`) treats `max_balls` as the format signal via
`overs = (max_balls or 120) // 6`. In the slice:

- **111 of 349 matches (32%)** have `max_balls = 0` on their first row.
- `max_balls` **varies within a single match** in 115 of 349 matches, so reading it from
  `first_row` is arbitrary.
- Those same matches clearly *are* ODIs: their highest over is 45-50.

Because `0 or 120` evaluates to `120` in Python, the current code would assign **`overs = 20` to a
third of all ODI matches** — silently mislabelling them as T20-shaped. Legitimate rain-reduced
games also appear (`max_balls` of 282, 240 → 47, 40 overs), so a strict equality check against the
format's `balls_per_innings` would abort constantly.

*Revised approach for 0.4:* the explicit `--format` flag is authoritative for what gets stamped
into the `format` column. Derive `matches.overs` from the **maximum over actually observed in the
match** (or the max of `max_balls` across the match, ignoring zeros), not from `first_row`. Use
`max_balls` only as a soft sanity check — warn if the observed innings length *exceeds* the
format's `balls_per_innings`, rather than requiring equality.

**2. `competition` is empty far more often than expected — but `tournament` always covers it.**
- **197 of 349 matches (56%)** have an empty `competition` (86,604 of 149,599 rows).
- In **every single one**, `tournament` is populated ("Australia in South Africa ODI Series",
  "ICC World Cup", …).

`matches.competition` is `NOT NULL`, so the `tournament` fallback is **mandatory, not optional** —
without it more than half the ODI load fails to insert. Plan risk #4 was rated minor; it is not.

**Other observations**
- `inns` only ever takes values 1 and 2 in this window — no super overs to handle yet.
- The file is chronological and starts earlier than assumed: **2000**, not 2005. Combined with
  chunk 0.3's `table_routing`, those pre-2015 ODIs correctly route to `delivery_details`.
- The ODI CSV column is `date`; the `delivery_details` table has both `date` (NULL) and
  `match_date` (populated). Don't assume the CSV and table column names line up.
- `winner` can be `'-'` (no result), and `target` is empty even on second-innings rows for some
  matches — the sync's result handling needs to tolerate both.

**Tooling added:** `scripts/dev/make_csv_slice.py` streams only the leading bytes of the Dropbox
folder's zip and extracts whole matches, so nobody has to download 11 GB to test the loader.

### 2026-07-25 — Chunk 0.3 — Claude — COMPLETE

**Done**
- `format_config.py` — the single source of truth. Four specs: men's T20, women's T20, men's ODI,
  Tests. Each carries innings count, balls per innings, chase innings, over cap, a 3-phase and a
  4-phase model, fantasy ruleset key, and SR/economy benchmark bands.
- `services/analytics_common.py` — added `phase_bounds()`, `phase_case_sql()`, `table_routing()`
  and `format_filter_sql()`.
- `routers/formats.py` — `GET /formats`, wired into `main.py`.

**Verified**
- `phase_case_sql()` reproduces **both** existing inline literals character-for-character
  (`d.over` and `dd.over` variants from `services/query_builder_v2.py:475,2990`). This is the
  guarantee that migrating a T20 call site in chunk 0.6 changes nothing.
- T20 `display_overs` come out as `1-6 / 7-15 / 16-20`, matching the hand-written `PHASE_META`
  labels in `services/match_scorecard.py:19-23` — independent confirmation the bounds are right.
- `table_routing('ODI','male', 2005→2010)` → `delivery_details` only, which is the whole point:
  the old date-only fork would have sent those to the legacy table, which has never held ODIs.
- `/formats` reports `available: false` for the three unloaded formats and `3926` matches for
  men's T20.
- Goldens: **PASS 13/13**.

**Decisions / surprises**
- Phase *keys* are deliberately reused across formats (`powerplay`/`middle`/`death`, with Tests
  substituting `new_ball` for the first). That is what lets the existing `pp_*`/`middle_*`/`death_*`
  stat columns serve every format unchanged — decision D3. Only labels and over ranges vary.
- Tests declare `over_max = None`; the API cap comes from `UNBOUNDED_OVER_MAX = 199` via
  `effective_over_max()`, so an unbounded filter can't reach the query layer.
- `get_format()` raises on an unknown combination rather than falling back to T20 — a silent
  fallback would produce plausible-but-wrong numbers, which is the worst failure mode here.
- Format availability in `/formats` is **data-driven** (`COUNT(*) > 0` on `matches`), so no
  feature flag is needed to reveal a format — loading its data is what enables it. The count is
  cached for the process lifetime; call `reset_coverage_cache()` after a load.
- `.gitignore` also ignores `*.sql` wholesale, which silently excluded both the new migration and
  `scripts/recreate_delivery_details.sql` (the file the plan calls authoritative — it was never
  tracked). Added negations for `scripts/migrations/` and that file.

**Next**
- Chunk 0.4: pipeline format-awareness — `--format`/`--gender` flags on the loader, column
  stamping, `max_balls` cross-check, retire `cleanup_non_t20.py`, per-format phase bounds in
  `sync_stats_from_dd.py`, and fantasy gating on `fantasy_ruleset`.

### 2026-07-25 — Chunk 0.2 — Claude — COMPLETE (local only)

**Done**
- `scripts/migrations/001_multi_format_columns.sql`: adds `format`/`gender` to `matches`,
  `delivery_details`, `batting_stats`, `bowling_stats`, and `gender` to `players`; CHECK
  constraints on the allowed values; swaps `players` `UNIQUE(name)` → `UNIQUE(name, gender)`;
  adds a partial `idx_dd_format_gender` and `idx_matches_format_gender`. Idempotent.
- `models.py`: the four models above plus `Player` updated to match, with `UniqueConstraint`
  in `Player.__table_args__`.
- `scripts/recreate_delivery_details.sql` (the authoritative DDL) updated to include the new
  columns, checks and index, so a rebuild-from-scratch matches a migrated database.
- **Bug fix:** `services/match_scorecard.py` — `_bat_vs_bowler_sql` and `_bowl_vs_batter_sql`
  ordered by `balls DESC` with no tiebreaker. Added `bowler_name` / `batter_name` as the final
  sort key.

**Verified**
- Migration ran in **1.5 s** on the 770k-row local `delivery_details` — confirms the PG11+
  fast-default path, so production should be near-instant too.
- `SELECT format, gender, count(*)` → exactly one `(T20, male)` bucket per table, equal to the
  pre-migration totals (`delivery_details` 770,040 · `matches` 3,926 · `players` 6,887).
- Re-running the migration is clean (NOTICEs only).
- `models.py` imports and the ORM reflects all new columns.
- Goldens: **PASS, 13/13**, stable across repeated runs.

**Decisions / surprises**
- The golden check initially failed on `scorecard_legacy_pre2015` with 110 differences — which
  turned out to be **pure row reordering, not a data change**: an order-insensitive comparison of
  the whole payload was equal, and the re-captured golden is byte-identical in size (51,696) to
  the original. Root cause: the new `idx_matches_format_gender` changed the query plan, and the
  vs-bowler breakdown's `ORDER BY ... balls DESC` had no tiebreaker, so equally-faced bowlers came
  back in a different order. Fixed at source rather than papered over in the harness (an unstable
  sort means the scorecard could render rows differently between deploys on identical data).
  Goldens were then re-captured.
- Worth knowing for later chunks: **adding an index can flip golden diffs without any data
  changing.** If a check fails, compare order-insensitively before assuming a regression.

**Next**
- Chunk 0.3: `format_config.py` (phase splits, innings counts, balls per innings, benchmark bands),
  `GET /formats`, and `phase_case_sql()` / `phase_bounds()` / `table_routing()` in
  `services/analytics_common.py`. No call sites migrated in that chunk.

### 2026-07-25 — Chunk 0.1 — Claude — COMPLETE

**Done**
- Created branch `multi-format`.
- `scripts/dev/setup_local_db.sh` — builds `hindsight_local` from a **subset** of production.
- `scripts/dev/run_local_api.sh` — runs the API against the local DB, and refuses to start if
  `DATABASE_URL` looks like production.
- `scripts/regression_snapshot.py` — golden-response harness (`discover` / `capture` / `check`).
- `MULTI_FORMAT_PLAN.md` (status tracker + per-chunk briefs), this log, and `CLAUDE.md` pointing
  future sessions at both.
- `.gitignore` had a blanket `*.json` rule that would have silently excluded the goldens; added
  negations for `scripts/goldens/`.

**Verified**
- Local DB built: 3,926 matches · 770,040 `delivery_details` · 118,177 `deliveries` ·
  63,704 `batting_stats` · 46,551 `bowling_stats` · 6,887 players. Total **644 MB**.
- API starts against the local DB and serves all three hero features.
- `regression_snapshot.py discover` → 13 endpoints; `capture` → all 13 returned HTTP 200;
  `check` → **PASS, all 13 identical** (harness proven non-flaky).

**Environment findings (important for whoever picks this up)**
- Prod Postgres is **16.13**; the machine's Postgres.app server is **14.18**. `pg_dump` 14 refuses
  to dump a PG16 server. Fix: **pgAdmin 4 ships PG16.1 client binaries** at
  `/Applications/pgAdmin 4.app/Contents/SharedSupport/` — the setup script uses those by default
  (`PG16_BIN` env var overrides). No conda/Homebrew install needed. A plain-SQL schema dump from
  PG16 restores into the PG14 local server without complaint, so the local server stays on 14.
- **Disk is the binding constraint**: only ~19 GB free (volume at 90%). A full 6.3 GB prod restore
  plus later ODI test data would be uncomfortably tight, so the local DB is a **subset**:
  - all small tables in full (`players`, `player_aliases`, `query_builder_metadata`)
  - `matches` + `batting_stats` + `bowling_stats` for the subset window
  - `delivery_details` from **2024-01-01** (~769k rows) — the modern code path
  - `deliveries` from **2013–2014** (~118k rows) — keeps the legacy pre-2015 path testable,
    which chunk 0.5 (table routing) specifically needs
  - Expected local size ≈ 1.4 GB.
- `database.py` calls `load_dotenv()` with default `override=False`, so an **exported
  `DATABASE_URL` wins over `.env`**. That is how we point the API at the local DB without ever
  editing `.env` (which holds the production URL).

**Decisions / surprises**
- **`delivery_details.date` is 100% NULL in production** (all 2.33M rows); `match_date` (varchar,
  ISO `YYYY-MM-DD`) is the populated column. This silently produced a 0-row copy on the first run
  and will bite anything that filters `delivery_details` by date. Compare on `match_date`.
- `delivery_details` has **no** foreign key to `matches`, so it is sliced directly rather than
  through a join.
- The live `delivery_details` table has both `match_id` and `p_match` (both varchar). As the plan
  says, `models.py:308-396` is stale — `scripts/recreate_delivery_details.sql` is authoritative.
- `/query/deliveries/columns` reports `total_deliveries: 2326879` — the **production** count. It is
  served from the copied `query_builder_metadata` cache table, not counted live, so local responses
  quote prod totals. Harmless and stable, but don't be confused by it.
- Heroku plan upgrade deferred (see CURRENT STATE) rather than done up front as chunk 0.1
  originally implied — it costs money from the moment it runs and buys nothing until A1.
- Running the copy pipeline as a *backgrounded* shell task hung indefinitely on the first table;
  the identical command in the foreground finished in seconds. Run `setup_local_db.sh` in the
  foreground (the full build takes ~6 minutes, almost all of it `delivery_details`).

**Next**
- Chunk 0.2: write `scripts/migrations/001_multi_format_columns.sql`, apply to `hindsight_local`
  only, update `models.py` + `scripts/recreate_delivery_details.sql`, re-run the golden `check`.

---

## How to update this log

1. **Read the CURRENT STATE block first.** It is the single source of truth for what has been
   applied locally vs. on production.
2. **Append a new entry at the top of the log section** when you complete a chunk *or* when a
   session ends mid-chunk. Never leave work undescribed — the next session may be a different tool.
3. **Update CURRENT STATE in the same edit.**
4. **Record every schema change** with its migration filename and whether it has run locally and/or
   on prod. Migration drift between the two is the highest-risk failure mode in this project.
5. **Note deviations from the plan explicitly** under "Decisions / surprises" rather than silently
   changing course.

Entry template:

```markdown
### YYYY-MM-DD — Chunk X.Y — <Claude|Codex>

**Done:** what changed, which files
**Verified:** commands run and their results
**Decisions / surprises:** anything that contradicts or extends the plan
**Next:** the exact next step for whoever picks this up
```
