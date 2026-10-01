# Hindsight codebase audit — 2026-10-01

Read-only audit of live code (`main.py`, `routers/`, `services/`, `ml/`, `mcp_server/`, fantasy files)
plus the local DB `hindsight_local` (a subset of prod: `delivery_details` 920k rows vs ~4.16M in prod).
Nothing in prod was touched.

**How to read this**
- **✅ verified** means I reproduced the finding myself, by query, request or test, or read the exact code.
- **📖 code-read** means an audit agent traced it in code and I spot-checked the snippet.
- **Goldens?** says whether fixing it changes men's T20 output covered by `regression_snapshot.py`. Those fixes are
  *correct but visible*, so each one needs your sign-off before it ships.

Branch for fixes: `audit-fixes` (not merged or deployed). **Fixed:** F0 `62a272d`, C4 `68c4023`, A7 `f26f058`, A9 `d6f9a5d`,
A4 (wicket casing only) `3200f45`, B1 `2ba20f5`, A16a `2355562`, C9 `2e19fcc`. All goldens identical after each.
Batch 2: cache LOGIC_VERSION `bba7529`, A1 `718d74e`, A2 `5b8e6b9`, A3 via shared `services/metrics/sql_defs.py` `49e561c`,
A6 + legacy-scorecard part of A18 `d00c0fa`; 8 goldens re-baselined with sign-off `40d9fc5`.
Batch 3: A14 rolling form/bowling context `0d76ce9`, venue leaders `fd5421b`, player stats vs types `d0591ba`,
player bowling breakdowns `33df9bd`, pitch maps `57d9284`; A11 matchups + innings filter `114eabc`;
A15 rankings `bb33be3`; A8 dismissal stats `08c1d6d`. **match_preview golden refresh awaiting sign-off.**

**New findings from fixing:** A19 — `/player/{name}/stats` bowling-type matrix reads only the legacy
table, which after 2025 holds only cricsheet-loaded matches (72 locally since mid-2025), so the profile
matrix misses most recent cricket. A20 — local `bowling_stats` was written by older sync rules (wide runs
double-counted, 'leg before wicket' not a wicket, `score = 0` dots): 26k/3.2k/12k innings differ from
current rules; check prod (read-only) before regenerating. A21 — `matchups.py` filtered innings on
`dd.innings` (never populated), so any innings-position filter dropped all post-2015 data (fixed).

Batch 4 (Wrapped + perf): Wrapped cards `58a37ef` (+ Venue Vibes crash: A22). C3 alias views `b4ddcb2`
(migration 011), preview metrics `c6254ac`, alias chains `4252679` (013, A23), matchups/scorecard alias +
pre-filter `e2da664` (012), refresh/ANALYZE `488525d`, QB pre-counts `f2b653e`. Measured locally, warm:
match preview 4.05 s → 0.79 s, scorecard 414 → 62 ms, matchup x6 18.0 → 1.8 s.
**Deploy order: migrations 011, 012, 013 on production before this branch.**
A22 — Wrapped "Venue Vibes" raised on every request and grouped on unpopulated columns (fixed).
A23 — two alias chains split players (Mitch/Mitchell Owen, Raj Bawa); `audit_roster_names --fix` created
them and now resolves chains (fixed). Open: "MW Short" aliases to both Matthew and D'Arcy Short.

---

## A. Correctness — wrong numbers shown to users

| # | Sev | Where | What's wrong | Evidence | Goldens? |
|---|---|---|---|---|---|
| A1 | HIGH | `services/query_builder_v2.py:2538-2544` | Date filter on `delivery_details` is truncated to **year**. A June 2025 window returns all of 2025. The legacy path filters exact dates, so the same request means different windows depending on the table. | ✅ June-2025 query → 300,249 balls; real June count 44,983 | Only if goldens use partial-year windows |
| A2 | HIGH | `services/query_builder_v2.py` ~2380-2427, 3433-3441 | When delivery_details and legacy `deliveries` results are **merged** (`format=ALL` + start < 2015), the new side applies `HAVING min_balls` and `LIMIT/OFFSET` in SQL *before* the merge. The merged list is then sliced by `offset` again. `min/max_wickets` are never re-applied; legacy-only path gets no min/limit at all. Result: page 2+ is wrong, `min_balls` drops or undercounts players, totals are partial. | ✅ batter leaderboard from 2010, page 2 = Finch 1604, Gayle 1507… (legacy-only rows) instead of the next-ranked batters | No (T20 goldens are post-2015) — verify |
| A3 | HIGH | `services/query_builder_v2.py:3317-3319` (+ legacy `:822-865`) | Grouped mode: `balls = COUNT(*)` includes **wides** (batter) and wides+no-balls (bowler); bowler runs = `score` include **byes/leg-byes**; wickets = any non-empty `dismissal`, so they include **run outs, retired hurt, "not out"** (10 rows locally), and a non-striker run-out is charged to the striker. `query_mode=batting_stats/bowling_stats` in the same file does it right, so the same player shows two different SRs. | ✅ Kohli T20: 1545 balls counted vs 1491 legal (SR understated ~3.5%) | **Yes** — every query-builder SR/avg/econ |
| A4 | HIGH | `services/visualizations.py:408-415, 745` | Pitch maps: `dd.out = 'True'` — DB holds `'true'`/`'False'` (mixed case), so **every pitch-map cell shows 0 wickets / NULL average**. Same queries count 4 byes as a "four" (`score=4`) and charge byes to bowler. | ✅ `select out,count(*)` → `False` 872,491 / `true` 48,000 | Only if pitch maps are in goldens |
| A5 | HIGH | `services/relative_metrics.py:188,289,547,648`; `services/ipl_prediction.py:644, 1035-1058, 1208-1241` | `bowling_stats.overs` is stored **decimal** (25 balls = `4.1667`). These read it as cricket notation (`4.1` → 4 overs 1 ball): 25 balls → 26, 21 balls (3.5) → 23. Economy and ball weights are skewed in relative metrics and IPL predictions. | ✅ `overs` values `4.1666…`, `3.3333…` in DB | Yes for those endpoints |
| A6 | HIGH | `services/match_scorecard.py:379, 454-457` vs legacy `:417, 485-490` | Scorecard's delivery_details path: batting balls = `COUNT(*)` (wides counted), bowler runs include byes/leg-byes, bowler wickets include retired-out / obstructing. The legacy path gets all three right. | ✅ code side by side | **Yes** (scorecard is a hero endpoint) |
| A7 | HIGH | `services/match_preview.py:149-150` | `WHERE team1=:team OR team2=:team AND (date <= :end_date)` — AND binds first, so the **end_date cutoff is ignored when the team is team1**. Historical previews and backtests leak future matches. Also no format/gender filter: an ODI preview shows T20/women's form, and `_get_latest_elo` shows T20 Elo. | ✅ code | Only with `end_date` |
| A8 | MED | `routers/players.py:83-150` (`/players/{name}/dismissal_stats`) | Ignores every page filter (dates, leagues, venue). Phase split `over < 16` puts over 15 in middle (rest of app: `< 15`). Keys on striker, so a non-striker run out is charged to the striker. Bowler dismissals include run outs. Reads legacy table only. | 📖 | Maybe |
| A9 | MED | `main.py:2254, 2674, 3661, 4277` | `"top_teams": top_teams is not None` → binds `False`, and SQL checks `:top_teams IS NULL`. With `include_international=true` and no `top_teams`, **internationals are excluded**. On some paths a catch-all OR hides it. | ✅ code (4 sites) | Possibly |
| A10 | MED | `services/match_preview.py:93-136`, 1721 | H2H headline uses exact team names; the history bundle uses name variants. Renamed franchises show two different H2H records on the same page. | 📖 | Possibly |
| A11 | MED | `services/matchups.py:824-855, 469-472` | The two tables use different wicket rules (`'run out'` exact vs `out::boolean`, which includes run outs). Batter runs include extras on both sides; balls include wides. In "Overall" rows 0 wickets is treated as 1 (avg = runs), but per-pair rows give NULL. | 📖 | Yes (matchups in preview) |
| A12 | MED | `services/matchups.py:120-140, 363-410`; `fantasy_points_odi.py` | Matchup fantasy projection is hard-coded to T20 (4-over cap, T20 bands) even for `format=ODI`. The ODI calculator inherits the **T20 SR and economy bands**. **Needs your call** on the intended ODI ruleset. | ✅ no band overrides in ODI class | No |
| A13 | MED | `sync_stats_from_dd.py:163,323`, `statsProcessor.py:254` | Stored `fantasy_points` includes only batting + bowling points: no LBW/bowled bonus, maidens or fielding. The bonus checks `'lbw'`, but the data says `'leg before wicket'`. Maidens count byes as conceded. | 📖 | Fantasy endpoints |
| A14 | MED | many | Bowler runs = `SUM(dd.score)` (byes charged to bowler) in `rolling_form.py:598`, `bowling_context.py:107,193`, `main.py:1176`, wrapped cards; player bowling breakdowns in `main.py:2348-2420, 3828-3880` read the legacy table only (missing everything after 2025-11), with wides counted as balls faced. | 📖 | Yes, scattered |
| A15 | MED | `services/global_t20_rankings.py:334-386` | Picks `dd.date` (100% NULL) and falls back to `dd.year`, so rolling windows widen to whole years; batting runs use `score` (extras credited to batters). | 📖 | Rankings |
| A16 | MED | `services/nl2query.py` | (a) Cache hits re-log the original OpenAI cost, which inflates monthly spend and **trips the 4o→4o-mini fallback early** (`:1640-1661`). (b) Overs clamped to 0-19 and no `format` filter, so ODI questions break (`:1097-1105`). (c) Any "N+ runs" is forced to per-innings, so "500+ runs in IPL 2024" returns 0 rows (`:1217`). | 📖 | No |
| A17 | MED | `routers/match_preview.py:56, 370, 444` | Preview cache is a plain dict: no TTL, no data version, unbounded growth. `debug` isn't in the key. A transient Jev failure caches the fallback narrative until restart. | 📖 | No |
| A18 | LOW | various | Dot-ball definition differs: `batruns=0 & legal` vs `score=0` (a leg-bye isn't a dot) vs `runs_off_bat=0 & extras=0`. Venue phase split `over < 11` for Mid1 vs `format_config` 6-9 (`venue_delivery_stats.py:132`). `is_chase` = innings 2 is wrong for Tests. Legacy scorecard counts "retired hurt" as a wicket. | 📖 | Some |

**Root cause of most of section A:** no shared definition of *legal ball / bowler runs / bowler wicket / dot*.
`sync_stats_from_dd.py:254-262` already has the right rules. **Recommendation:** add one small
`services/metrics/sql_defs.py` with those expressions and point every query at it. This is one change, not 15 one-off patches.

## B. Crashes / dead code

| # | Sev | Where | What | Evidence |
|---|---|---|---|---|
| F0 | HIGH | `src/components/BattingScatterChart.jsx` | Hook after early return. Crashes when data loads after an empty render. | ✅ **fixed** `62a272d` + regression test |
| B1 | MED | `ml/train_model.py:960` | `text` not imported. `--train-all-leagues` crashes when the league cache is empty. | ✅ ruff F821 |
| B2 | LOW | `statsProcessor.py:372` | `for d inbowler_deliveries` is a SyntaxError, so the legacy stats writer can't run. | 📖 (agent ran py_compile) |
| B3 | LOW | `main.py:553` `get_phase_stats` (unused, also wrong maths); `main.py:1706` duplicate matchups route shadowed by the router; `teams_percentiles.py:356` unreachable code; `query_cache.prune(keep_versions)` ignores its argument; `wrapped_legacy.py:47/206` function defined twice | ✅ ruff/vulture |
| B4 | LOW | repo root | 72 `debug_*`/`test_*`/`check_*` scripts, stale `cricket-data-thing/` copy (10 tracked files), empty `*.db` files, `wpa_engine_broken*.py` (no live code imports any `wpa_engine*`) | ✅ |
| B5 | LOW | frontend | 33 `exhaustive-deps` warnings. Most are intentional "fetch on trigger" effects; none confirmed as user-visible bugs yet. | eslint |

## C. Performance (measured locally; prod is ~4.5× bigger and colder)

| # | Sev | Where | Finding | Fix |
|---|---|---|---|---|
| C1 | CRIT | `/rankings/player/{name}` (`global_t20_rankings.py`) | ✅ **26.5 s** locally, 45 queries; each monthly snapshot reruns league-wide aggregations, sorts spill to disk, and filters on `COALESCE(TRIM(dd.batter)…)` (column 100% NULL), which blocks index use. Prod already 503s here. | Precompute snapshots nightly into a table; meanwhile use `dd.bat` / `dd.match_date` |
| C2 | HIGH | Match preview | ✅ **2.4 s**, 128 queries. (a) Matchup query does a full seq scan of all T20 rows because of `COALESCE(alias, dd.bat) = ANY(...)` (1.28 s). (b) `preview_metrics._team_rows` 300-760 ms each; rewriting to start from `matches` gave **674 → 2.8 ms**, same result. (c) N+1 alias lookups (50× `get_player_names`). | Expand name variants in Python and filter on raw `dd.bat`; `(team_bat, match_date)` / `(team_bowl, match_date)` indexes; batched alias lookup |
| C3 | HIGH | ~15 services | The `alias_map` CTE (DISTINCT ON over a UNION) is rebuilt **in every query**: 41 ms each (4.9 ms with `COLLATE "C"`), badly misestimated (200 vs 7,256 rows), and causes a 1.7M-row hash-join blowup in the query builder. A scorecard spends ~380 of its 396 ms DB time on it. | Materialized view `player_alias_map(name_key PK)`, refreshed nightly |
| C4 | HIGH | `routers/player_summary.py:368, 481` | `async def` endpoints call sync SQLAlchemy **and the sync OpenAI client** on the event loop. Prod runs 1 worker, so **one summary request freezes the whole API** for the length of the LLM call. | Make them plain `def` (FastAPI threadpools them) |
| C5 | HIGH | `delivery_details` heap | One match's 233 rows sit on 112 pages (should be ~14); `p_match` correlation 0.27. Cold IPL count reads ~91 MB. Caused by whole-table backfill UPDATEs. | `CLUSTER`/`pg_repack` by `(p_match,inns,over,ball)` when disk allows, or `ORDER BY` on the next reload |
| C6 | MED | query builder | The same WHERE is scanned 4-5× per grouped request (2 counts, main, per-level summaries): 1.5 s cold. | One count statement / window totals / `GROUPING SETS` |
| C7 | MED | 37 sites | `match_date::date` casts defeat `idx_dd_match_date` and wreck estimates (27 est vs 5,914 actual). | Compare ISO strings, or backfill the `date` column and index it |
| C8 | MED | indexes | 147 indexes, many duplicate or prefix-redundant (e.g. `idx_dd_match` = `idx_dd_p_match`); ~60 MB locally, est. 300-500 MB prod (disk is 6.3/10 GB). Index scripts have drifted from the live schema. | Confirm with prod `pg_stat_user_indexes`, then `DROP INDEX CONCURRENTLY`; add an index-baseline migration |
| C9 | MED | `database.py` | No `statement_timeout` on the web engine, so a 27 s query holds 1 of 12 pool slots and other requests queue for 20 s. The `databases.Database` object is created but never connected (dead dependency). | `connect_args={"options": "-c statement_timeout=15000"}` |
| C10 | LOW | schema | 7 dead all-NULL columns in `delivery_details` (`date`, `batter`, `bowler`, `match_id`…); `out`/`target`/`inns_rrr` are varchar; ~212 bytes/row of repeated match-level data; no FK `p_match → matches` (23,885 orphan rows locally — check prod). | Longer-term cleanup |
| C11 | LOW | search / `/players/all` | `LIKE '%x%'` over the stats tables per keystroke; `SELECT DISTINCT batter FROM deliveries` full scan. | Small teams/players lookup + trigram index; cache |

---

## Suggested order
1. **Quick, safe, no golden change:** C4 (async → def), A7 (parentheses), A9 (`None` not `False`), A4 (pitch-map `LOWER(out)`), B1, A16a (nl2query cost re-logging), C9 (statement timeout).
2. **Query builder correctness:** A1 (dates), A2 (merge/pagination). Then **A3 + A6 + A14 via one shared metric-definitions module**. These change T20 goldens and need your sign-off and a golden refresh.
3. **Perf:** C3 (alias materialized view), C2, C1 (rankings precompute), C6, C7, then index cleanup C8 against prod stats.
4. **Decisions for you:** ODI fantasy rules (A12/A13), dead-file cleanup (B4).
