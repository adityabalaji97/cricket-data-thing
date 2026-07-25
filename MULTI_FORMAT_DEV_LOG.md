# Multi-Format Dev Log

Plan: [MULTI_FORMAT_PLAN.md](MULTI_FORMAT_PLAN.md) · Working dir: `/Users/adityabalaji/cdt/cricket-data-thing`

> **Every agent (Claude or Codex) reads the CURRENT STATE block below before doing anything else,
> and updates it before ending a session.** See "How to update this log" at the bottom.

---

## CURRENT STATE

- **Active chunk:** 0.3 complete → next is **0.4 pipeline format-awareness**
- **Branch:** `multi-format` (branched from `main` @ `29b61c1`)
- **Local DB:** `hindsight_local` on localhost:5432 (PG14 server), 644 MB subset of prod, healthy.
  Rebuild any time with `scripts/dev/setup_local_db.sh`.
- **Prod DB:** Heroku `cricket-data-thing`, PG16.13, **essential-1** (6.28 GB / 10 GB).
  Upgrade to essential-2 is **NOT done yet** — deliberately deferred until just before the
  Phase A ODI backfill (chunk A1), since nothing before that needs the extra space.
- **Migrations applied — local:** `001_multi_format_columns.sql` ✅
- **Migrations applied — prod:** **none** — `001` is still pending on production
- **Goldens:** 13 endpoints in `scripts/goldens/local/`, `check` passes clean (re-captured in 0.2
  after a deterministic-ordering fix; see that entry).
- **Blocked on / next action:** chunk 0.4 — pipeline format-awareness. **Needs a local copy of
  `t20_bbb.csv`** (GitHub secret `DROPBOX_CSV_URL`) plus an ODI slice to test against; neither is
  on this machine yet.

---

## Log entries (newest first)

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
