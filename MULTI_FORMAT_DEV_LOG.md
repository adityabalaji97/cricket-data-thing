# Multi-Format Dev Log

Plan: [MULTI_FORMAT_PLAN.md](MULTI_FORMAT_PLAN.md) · Working dir: `/Users/adityabalaji/cdt/cricket-data-thing`

> **Every agent (Claude or Codex) reads the CURRENT STATE block below before doing anything else,
> and updates it before ending a session.** See "How to update this log" at the bottom.

---

## CURRENT STATE

- **Active chunk:** **0.4, 0.5 and 0.6 COMPLETE.** ODIs are queryable end to end locally.
  Next is **0.7** (frontend foundation: theme consolidation, FormatContext, API client) and
  **0.8** (sunset gating + NavMenu).
- **Both former blockers are now resolved in code, locally:**
  - The dropdown cache is partitioned by (format, gender); `/deliveries/columns` takes a format
    parameter. Fixing it exposed that the loader left `delivery_details.competition` raw while
    `matches.competition` was normalised, so `leagues=ODI` matched nothing — the league filter
    was simply broken for non-T20. The loader now normalises on load.
  - The corrupted stats are repaired by `scripts/backfill_recompute_stats.py`. Locally this took
    impossible wicket counts from 21,905 to 19 and batting averages from absurd (Sikandar Raza
    2.61) to correct (Kohli 57.58, top of the list).
- ⚠️ **Still to do on PRODUCTION:** the backfill has only been run against `hindsight_local`.
  Production still holds the corrupt rows, and its batting averages in the query builder's
  `batting_stats` mode are visibly wrong today. Run `scripts/backfill_recompute_stats.py`
  there — after a `heroku pg:backups:capture` — as part of the deploy.
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

**0.9 production backfill — IN PROGRESS.** Backup `b002` captured first (the only prior backup
was from 2025-05-24, 25 MB — not a usable rollback). Migration 001 applied to production as a
newly-discovered prerequisite. A 50-match batch behaved correctly (455 rows repaired), then the
full run over 10,218 matches started.

**Note for whoever picks this up:** the backfill is network-bound against RDS — roughly 1.5% CPU,
all round-trip latency — so it takes hours rather than minutes. It commits every 200 matches and
is safely resumable: re-running simply recomputes matches again, since it deletes and rebuilds
per match rather than appending.

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
