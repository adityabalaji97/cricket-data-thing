# Multi-Format Expansion — ODIs, Women's T20s, Tests

> **Working log / handoff state: [MULTI_FORMAT_DEV_LOG.md](MULTI_FORMAT_DEV_LOG.md).**
> Read its CURRENT STATE block before starting any session, and update it before ending one.

Hindsight is men's-T20-only today. This project extends the three hero features — **query
builder**, **match preview**, **scorecard** — to men's ODIs, women's T20s and Tests, targeting the
**2027 ODI World Cup**, redesigns the match preview onto the new dark design system, and gates the
remaining pages behind a "T20 only" section. Mobile-first throughout.

Everything is developed and verified **locally first**; production DDL and data loads are separate,
explicit promotion steps.

---

## Status tracker

| Chunk | Description | Status |
|---|---|---|
| **0.1** | Local env + regression baseline | [x] 2026-07-25 |
| **0.2** | Schema migration: `format` / `gender` columns | [x] 2026-07-25 (local only) |
| **0.3** | `format_config.py` + `/formats` + phase helpers | [x] 2026-07-25 |
| **0.4** | Pipeline format-awareness | [ ] |
| **0.5** | `table_routing` replaces the 2015 date fork | [ ] |
| **0.6** | Query builder backend format param | [ ] |
| **0.7** | Frontend foundation: theme, FormatContext, API client | [ ] |
| **0.8** | Sunset gating + NavMenu consolidation | [ ] |
| **A1** | ODI backfill load | [ ] |
| **A2** | Workflow matrix (t20 + odi daily) | [ ] |
| **A3** | Query builder ODI (frontend) | [ ] |
| **A4** | nl2query + summarizer ODI | [ ] |
| **A5** | Scorecard ODI | [ ] |
| **A6** | Match preview redesign 1: shell | [ ] |
| **A7** | Match preview redesign 2: core blocks + format phases | [ ] |
| **A8** | Match preview redesign 3: children + mobile pass | [ ] |
| **A9** | Per-format ELO | [ ] |
| **A10** | ODI fantasy points | [ ] |
| **A11** | Landing page multi-format | [ ] |
| **B1** | WT20 load + player name collisions | [ ] |
| **B2** | WT20 pipeline leg + UI enable | [ ] |
| **C0** | Test data recon (read-only) | [ ] |
| **C1** | Test config + load | [ ] |
| **C2** | Query builder Tests | [ ] |
| **C3** | Scorecard Tests | [ ] |
| **C4** | Test match preview variant | [ ] |
| **C5** | Tests ELO + final sweep | [ ] |

---

## Local environment

### Prerequisites

* **Postgres 16 client binaries.** Production is PG16.13 and `pg_dump` 14 refuses to dump it.
  pgAdmin 4 already ships them at `/Applications/pgAdmin 4.app/Contents/SharedSupport/`, which is
  the scripts' default. Override with `PG16_BIN=/path/to/bin`. The **local server** can stay on
  PG14 (Postgres.app) — we restore a plain-SQL schema dump, which is version-tolerant.
* **Local Postgres server running** on `localhost:5432` (Postgres.app).
* Python deps already satisfied by the anaconda3 base env (`fastapi`, `sqlalchemy`, …).

### Build the local database

```bash
scripts/dev/setup_local_db.sh                # full subset build (drops hindsight_local first)
scripts/dev/setup_local_db.sh --schema-only  # schema only
```

The local DB is a **subset** of production, because this machine has limited free disk:

| Table | Local contents | Rows |
|---|---|---|
| `players`, `player_aliases`, `query_builder_metadata` | full copy | 6.9k / 3.7k / 16 |
| `matches` | 2024-01-01 onwards **+** 2013–2014 | 3,926 |
| `batting_stats`, `bowling_stats` | matches in the subset | 63.7k / 46.6k |
| `delivery_details` | `match_date >= 2024-01-01` (the modern path) | 770k |
| `deliveries` | 2013–2014 (keeps the **legacy pre-2015 path** testable) | 118k |

Total ≈ 644 MB. The two windows are deliberate: chunk 0.5 changes how the app routes between the
modern and legacy ball-by-ball tables, so both must have data locally.

Tune with env vars: `MODERN_FROM`, `LEGACY_FROM`, `LEGACY_TO`, `LOCAL_DB`.

### Run the app locally

```bash
scripts/dev/run_local_api.sh          # API on :8000 against hindsight_local
npm start                             # frontend on :3000, already points at localhost:8000
```

`database.py` calls `load_dotenv()` with `override=False`, so an **exported `DATABASE_URL` beats
`.env`**. That is how the API is pointed at the local DB without ever editing `.env` (which holds
the production URL). `run_local_api.sh` additionally refuses to start if `DATABASE_URL` looks like
production.

### Regression goldens

The repo has no test suite, so frozen golden responses stand in for one. Phase 0's whole promise is
that **men's T20 behaviour stays bit-identical** while formats are added, and this is what proves it.

```bash
python scripts/regression_snapshot.py discover   # rebuild endpoints.json from DB contents
python scripts/regression_snapshot.py capture    # freeze current responses
python scripts/regression_snapshot.py check      # diff current responses vs goldens
```

13 endpoints cover all three heroes plus both ball-by-ball code paths. Goldens live in
`scripts/goldens/local/` (subset DB) and `scripts/goldens/prod/` (`--env prod --base-url …`);
the two legitimately differ, because the local DB holds less data.

**Run `check` after every backend chunk.** Any diff must be explained before the chunk is done.

---

## Core design decisions

### D1 — Single `delivery_details` table, explicit `format` + `gender` columns

`'T20' | 'ODI' | 'TEST'` and `'male' | 'female'`, added to `matches`, `delivery_details`,
`batting_stats`, `bowling_stats`, plus `gender` on `players`. All default to `'T20'`/`'male'`, which
is correct for every existing row, so the backfill is a metadata-only operation.

One table rather than per-format tables: the query builder (`services/query_builder_v2.py`, 143 KB)
builds SQL against `delivery_details` directly, so per-format tables would mean dynamic table-name
plumbing everywhere. Columns are denormalized onto `delivery_details` rather than joined from
`matches` because the hot query paths don't join `matches`. Native partitioning is the documented
fallback if T20 latency regresses after the ODI load, not something to do up front.

`matches.match_type` (`'league'`/`'international'`) is **left alone** — despite the name it means
domestic-vs-international and is orthogonal to format.

The legacy `deliveries` table gets no new columns: it is (T20, male, pre-2015) by construction, and
D5's routing keeps other formats away from it.

### D2 — `format_config.py` is the single source of truth

Per `(format, gender)`: balls per innings, innings count, chase innings, over cap, 3-phase and
4-phase over splits, fantasy ruleset key, SR/economy benchmark bands, legacy-table cutoff.

Phase splits: T20 `0-5 / 6-14 / 15-19`; ODI `0-9 / 10-39 / 40-49`; Tests `new ball 0-19 / set
20-79 / old ball 80+`.

Served to the frontend by `GET /formats` and consumed through a `FormatContext`, so there is **no
hand-maintained JS mirror to drift**. `services/analytics_common.py` gains `phase_case_sql()`,
`phase_bounds()` and `table_routing()`.

**Literal-retirement strategy.** The 6/15 phase split appears as inline SQL in ~200 places. Only
hero-path call sites get migrated:

| Migrate | Leave frozen (T20-only, server-pinned) |
|---|---|
| `services/query_builder_v2.py:475,2990` | `main.py` (~46 literals) |
| `services/match_scorecard.py:646` | `services/visualizations.py` |
| `services/delivery_data_service.py:504-508,591-593` | `routers/players.py`, `services/wrapped/*` |
| `sync_stats_from_dd.py:95,170` | `statsProcessor.py` (legacy loader) |
| `routers/query_builder_v2.py:122-123` (over caps) | |

The frozen literals stay *correct* because those endpoints are pinned to `format='T20'`.

### D3 — Keep `pp_/middle_/death_` stat columns, reinterpret per format

They become semantic phase1/2/3; `format_config` supplies the display label ("Powerplay" vs
"Overs 1-10" vs "New ball"). `sync_stats_from_dd.py` swaps its hardcoded tuples for
`phase_bounds(format)`. Renaming or going long-format would touch every consumer for no
user-visible gain.

### D4 — Pipeline: matrix workflow, per-format cadence

`.github/workflows/refresh-delivery-details.yml` becomes a matrix over `{format, gender, secret}`:
t20 + odi daily, wt20 daily from Phase B, tests **weekly** from Phase C. Initial backfills run
locally, never in Actions.

The loader gains `--format`/`--gender`, stamps the columns on insert, and cross-checks `max_balls`
against the config (300↔ODI, 120↔T20) so a mis-set secret aborts instead of corrupting data.

**`cleanup_non_t20.py` must be retired** — it deletes any match with >260 deliveries, which would
destroy every ODI. Also fix `sync_from_delivery_details.py`: international inference when ODI
`competition` is empty (fall back to `tournament`), NULL-safe `max_balls // 6`, per-format
complete-match checks. Fantasy points are computed only for formats that have a ruleset. ELO
becomes per-`(format, gender)` streams.

### D5 — Kill the 2015 date fork

`query_builder_v2.py:23-24` and `match_scorecard.py:17` route pre-2015 requests to the legacy
`deliveries` table **by date alone**. ODI data goes back to 2005, so pre-2015 ODIs would silently
vanish. `table_routing(format, gender, dates)` sends everything except (T20, male, pre-2015) to
`delivery_details`.

### D6 — Frontend: one flat format switcher

Four flat entries — Men's T20, Men's ODI, Women's T20, Tests — not orthogonal format × gender
toggles, which would advertise combinations that don't exist. Persisted in `localStorage` + a
`?fmt=` URL param via `FormatContext`.

`src/utils/analyticsApi.js` grows into the real API client and appends format/gender automatically;
hero pages migrate to it. The 132 inline `config.API_URL` calls in sunset pages stay as they are —
their endpoints are server-pinned to T20.

Before any preview redesign, consolidate the **triplicated** dark theme
(`src/components/queryBuilderTheme.js`, `LandingPage.jsx:34-57`, `scorecard/matchScorecard.css`)
into `src/theme/hindsightDark.js`. Dedupe the four copies of the nav in `App.js` into one
`<NavMenu>` with a labelled "T20 (men) only" section; non-T20 formats render those entries disabled
with a tooltip rather than hiding them.

---

## Chunk briefs

Each chunk is one session's work: independently executable and independently verifiable.
Every chunk ends with `python scripts/regression_snapshot.py check` unless noted.

### Phase 0 — Foundations (T20 behaviour must stay bit-identical)

**0.1 Local env + regression baseline** ✅
Local subset DB, `scripts/dev/setup_local_db.sh`, `scripts/dev/run_local_api.sh`,
`scripts/regression_snapshot.py`, 13 goldens in `scripts/goldens/local/`.

**0.2 Schema migration**
Write `scripts/migrations/001_multi_format_columns.sql` per D1. Update `models.py` (`Match`,
`BattingStats`, `BowlingStats`, `Player`) and `scripts/recreate_delivery_details.sql`.
*Verify:* apply to `hindsight_local`; `SELECT format, gender, count(*) FROM delivery_details GROUP
BY 1,2` returns exactly one `(T20, male)` row equal to the prior total; goldens `check` passes.
*Do not* apply to production in this chunk.

**0.3 format_config + /formats + helpers**
Create `format_config.py`; add `GET /formats`; add `phase_case_sql()`, `phase_bounds()`,
`table_routing()` to `services/analytics_common.py`. No call sites migrated yet.
*Verify:* `phase_case_sql('T20','male',3)` output is character-identical to the existing inline
literal at `services/query_builder_v2.py:475`; `/formats` returns all four combinations.

**0.4 Pipeline format-awareness**
Per D4. Requires a local copy of `t20_bbb.csv` (Dropbox secret `DROPBOX_CSV_URL`) — generate small
slices into `data/slices/` for fast iteration.
*Verify:* reload a T20 slice → `batting_stats`/`bowling_stats` identical to a pre-change run; load a
100-match ODI slice → rows land with `format='ODI'`, `overs=50`, no fantasy points written, and
nothing deleted.

**0.5 table_routing replaces the 2015 fork** — per D5.
*Verify:* goldens pass (both `scorecard_legacy_pre2015` and `qb_legacy_pre2015_window` exist
precisely to guard this); `table_routing('ODI','male', 2005-2010)` resolves to `delivery_details`.

**0.6 Query builder backend format param**
`format`/`gender` params defaulting to T20/male; over caps and innings validation from config;
phase CASE and chase innings via helpers; `/query/deliveries/columns` scoped by format.
*Verify:* goldens pass on defaults; `over_max=49&format=ODI` accepted, same with `format=T20`
returns 422.

**0.7 Frontend foundation** — theme consolidation, `FormatContext`, API client, switcher with only
Men's T20 enabled. *Verify:* no visual drift on landing / query builder / scorecard; switcher choice
survives reload.

**0.8 Sunset gating + NavMenu** — pin sunset endpoints to `format='T20' AND gender='male'`; extract
one `<NavMenu>`. *Verify:* goldens pass; grep shows no un-pinned stats aggregate.

### Phase A — Men's ODIs

**A1 ODI backfill** — run locally, off-peak, against production. **Upgrade Heroku to essential-2
first** (see below). ~1.5M balls. *Verify:* spot-check the 2019 WC final and the 438 game against
ESPNcricinfo; audit empty-`competition` inference and DLS winners; T20 goldens on prod; `pg:info`.

**A2 Workflow matrix** — {t20, odi} daily. *Verify:* `workflow_dispatch` green for both legs; a
re-run inserts 0 duplicate rows.

**A3 Query builder ODI (frontend)** — `QueryFilters.jsx:262,275` over caps, `:243-251` innings
select, phase labels from context. *Verify:* cross-check one player-venue split against Statsguru.

**A4 nl2query + summarizer ODI** — `VALID_LEAGUES` per format (`services/nl2query.py:545`), prompt
over-ranges (`:116-121`), clamp (`:1073-1075`), benchmark bands (`services/query_summarizer.py:24-33`).
*Verify:* a 10-prompt eval sheet, 5 T20 regression + 5 ODI, with expected filter JSON.

**A5 Scorecard ODI** — result text and balls-left from config (`services/match_scorecard.py:1147-1165`,
the `120` literal at `:1163`); DLS note when `target` ≠ innings-1 score + 1.
*Verify:* render three ODI scorecards including a DLS game and a tie.

**A6 Preview redesign 1: shell** — extract the inline filter JSX at `App.js:794-980` into
`src/components/preview/PreviewFilters.jsx`; dark mobile-first shell following the scorecard's
`min(100%, 430px)` pattern; standardise the breakpoint. *Verify:* T20 preview functionally
identical, new skin only.

**A7 Preview redesign 2: core blocks** — 4-phase split from config
(`services/delivery_data_service.py:504-508,591-593`), chase logic (`:269-276,359-366`),
`VenueNotes.jsx:815-827` `PHASE_OVERS` and the `/20` literal.
*Verify:* T20 preview numbers match pre-redesign values exactly.

**A8 Preview redesign 3: children + mobile** — restyle the ~8 child components; fix phase copy
(`WicketDistribution.jsx:166`), `getPhase` in `InningsScatter.jsx` / `Comparison*`.

**A9 Per-format ELO** — ODI stream recomputed 2005→now. *Verify:* T20 ELO unchanged; ODI top 5
directionally matches ICC rankings.

**A10 ODI fantasy points** — `fantasy_points_odi.py`. **Confirm the current Dream11 ODI rulebook
first** — the constants have changed historically. *Verify:* hand-score two real ODI scorecards to
the point; T20 fantasy values untouched.

**A11 Landing multi-format** — recent-match tiles per selected format; unify the 759px breakpoint.

### Phase B — Women's T20

**B1 WT20 load + collisions** — audit cross-gender name collisions before loading; `UNIQUE(name,
gender)`; load `--format T20 --gender female`; women's ELO stream.
*Verify:* the cross-gender contamination query returns 0 rows; spot-check a WBBL and a Women's T20
World Cup scorecard.

**B2 Pipeline leg + UI enable** — daily wt20 matrix leg; women's SR/economy bands; women's
competitions in `VALID_LEAGUES`. *Verify:* all three heroes end-to-end on mobile for a WPL match;
men's goldens unchanged; a colliding player name resolves to the right person.

### Phase C — Tests

**C0 Data recon (read-only)** — inspect `tests_bbb.csv`: `max_balls` semantics (NULL? huge?), `inns`
range, declaration signal, follow-on detection, `target` semantics in innings 4, session/day fields.
Record answers as comments in `format_config.py`. **This gates C1.**

**C1 Test config + load** — 4 innings, chase innings 4, no fantasy; sync handles NULL `overs`,
draws and declarations; ~1.9M balls loaded locally; weekly workflow leg.
*Verify:* Headingley 2019 (4 innings, target 359, 1-wicket win); draws have `winner` NULL.

**C2 Query builder Tests** — innings 1-4, over cap, chase = innings 4 with a target,
new-ball/set/old-ball phases. *Verify:* cross-check a new-ball split against Statsguru.

**C3 Scorecard Tests** — 4-innings render, declarations (`487/5d`), result text for innings
victories, draws and follow-ons; drop balls-left framing.
*Verify:* four archetype matches, result strings matching ESPNcricinfo verbatim.

**C4 Test match preview** — replaces par-score framing with venue draw rate, average score by
innings number, pace-vs-spin split by innings, 4th-innings chase history, toss-decision outcomes.
*Verify:* Galle shows a spin bias and high result rate; a flat road shows a high draw rate.

**C5 Tests ELO + final sweep** — stray-literal grep across hero paths; enable Tests in the switcher;
full three-heroes × four-formats mobile QA; final golden diff.

---

## Promotion to production (per chunk)

1. Local verify passes and `regression_snapshot.py check` is clean.
2. Commit and push (Vercel builds a frontend preview).
3. Run the chunk's migration SQL on production via `heroku pg:psql -a cricket-data-thing`.
4. Deploy the backend to Heroku.
5. Re-run `regression_snapshot.py --env prod --base-url <prod>` and diff.

**Heroku upgrade.** Production is on **essential-1** (6.28 GB of 10 GB). The new formats add roughly
5 GB, so **essential-2** (32 GB, $20/mo) is required — but only from chunk **A1**, when the first
real data lands. Nothing in Phase 0 needs it, so the upgrade is deliberately deferred to keep the
extra cost off the clock until it buys something.

## Do not touch

* **Never run `cleanup_non_t20.py`** — it deletes any match with more than 260 deliveries. It must
  be retired in chunk 0.4 before any non-T20 data exists anywhere.
* **Never point `.env` at the local database**, and never point `DATABASE_URL` at production while
  developing. `.env` holds the production URL; local work exports `DATABASE_URL` instead.
* **`models.py:308-396` (`DeliveryDetails`) is stale** and does not describe the live table.
  `scripts/recreate_delivery_details.sql` is authoritative.
* **`delivery_details.date` is entirely NULL** — `match_date` (varchar, ISO `YYYY-MM-DD`) is the
  populated column. Filter and compare on `match_date`.
* The `/cricket-data-thing/` subdirectory is a stale vendored copy of the app. Ignore it; do not
  count its duplicate phase literals in any migration scope.

## Risks / open items

1. Test `max_balls` semantics are unknown → C0 gates C1; NULL-safety ships in 0.4 regardless.
2. `wprob` / `predscore` in the CSVs are T20-trained → hide win-probability UI for non-T20 formats.
3. Dream11 ODI constants must be confirmed against the current rulebook before A10.
4. Empty ODI `competition` values → `tournament`-based inference may misclassify some bilateral
   series; audit during A1.
5. Women's name collisions: the schema handles it, but any endpoint that looks players up by bare
   name needs the gender threaded through (grep during B1).
6. `query_builder_metadata` distinct-value lists must be partitioned by `(format, gender)` or ODI
   competitions will pollute the T20 dropdowns.
7. Monitor T20 p95 latency for 48h after A1; partitioning is the escape hatch.
