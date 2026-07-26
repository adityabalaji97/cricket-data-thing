# Multi-Format Dev Log

Plan: [MULTI_FORMAT_PLAN.md](MULTI_FORMAT_PLAN.md) · Working dir: `/Users/adityabalaji/cdt/cricket-data-thing`

> **Every agent (Claude or Codex) reads the CURRENT STATE block below before doing anything else,
> and updates it before ending a session.** See "How to update this log" at the bottom.

---

## CURRENT STATE

- **Active chunk:** 0.4 in progress (0.4a data sources + recon done, 0.4b migration 002 done;
  next is 0.4c competition normalizer)
- **Branch:** `multi-format` (branched from `main` @ `29b61c1`)
- **Local DB:** `hindsight_local` on localhost:5432 (PG14 server), 644 MB subset of prod, healthy.
  Rebuild any time with `scripts/dev/setup_local_db.sh`.
- **Prod DB:** Heroku `cricket-data-thing`, PG16.13, **essential-1** (6.28 GB / 10 GB).
  Upgrade to essential-2 is **NOT done yet** — deliberately deferred until just before the
  Phase A ODI backfill (chunk A1), since nothing before that needs the extra space.
- **Migrations applied — local:** `001_multi_format_columns.sql` ✅,
  `002_delivery_details_source_columns.sql` ✅
- **Migrations applied — prod:** **none** — `001` and `002` are both still pending on production
- **Dataset URLs:** all four are in `.env` (gitignored) as `DROPBOX_T20_URL`, `DROPBOX_ODI_URL`,
  `DROPBOX_WT20_URL`, `DROPBOX_TEST_URL`. **This repo is public — never commit these values**, and
  pull slices with `make_csv_slice.py --url-env NAME` so no link lands in shell history.
- **Slices in `data/slices/`** (gitignored, regenerate as needed): `t20_slice.csv` (2,874 matches,
  2015-2022), `odi_slice.csv` (349, 2000-2007), `test_slice.csv` (85, 2020-2025).
- **Goldens:** 13 endpoints in `scripts/goldens/local/`, `check` passes clean (re-captured in 0.2
  after a deterministic-ordering fix; see that entry).
- **Test data:** `data/slices/odi_slice.csv` — 349 complete ODI matches, 149,599 balls, 2000-01-09
  to 2007-03-23 (gitignored; regenerate with `scripts/dev/make_csv_slice.py`).
  **`t20_bbb.csv` is still not on this machine** — chunk 0.4's T20 no-regression check needs it
  (GitHub secret `DROPBOX_CSV_URL`), or export one from `hindsight_local` instead.
- **Blocked on / next action:** chunk 0.4 — pipeline format-awareness. Read the ODI recon entry
  below first: two of its findings change what 0.4 has to do.

---

## Log entries (newest first)

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
