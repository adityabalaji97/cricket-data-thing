# Notes pipeline: orientation (Phase 0)

What exists before the connector/hypothesis/notes work, and where the data comes from.
Written read-only on 2026-10-03 from the code at `main` 40f3946.

## MCP connector

`mcp_server/server.py`, mounted at `/mcp` by `main.py` (stateless streamable HTTP, JSON responses,
READ ONLY transaction + `MCP_STATEMENT_TIMEOUT_MS` per call, global `MCP_CALLS_PER_MINUTE` budget).
User docs: `docs/mcp-connector.md`.

| Tool | Backed by |
|---|---|
| `query_cricket_data` | `services.query_builder_v2.run_deliveries_query` (same path as `GET /query/deliveries`), shaped by `structure_query_result`; rows capped at 500; the text result is a markdown table of the first 25 rows; MCP Apps widget `mcp_server/widget.html` |
| `find_entities` | `services.search.search_entities` + competition aliases |
| `get_query_options` | `routers.query_builder_v2.get_available_columns` |
| `preview_match` | `main.get_venue_notes/get_venue_stats/get_match_history`, `services.matchups`, `routers.match_preview` |
| `match_recap` | `services.match_scorecard` + `services.match_recap.build_recap` |
| `player_profile` | `routers.player_summary.player_standouts` + batter/bowler summary (Player DNA) |

Tests: none exercise the MCP tools directly (`tests/` has query-builder contract tests with a
mocked session).

## Query engine

`services/query_builder_v2.py` (website query builder, connector, snapshots, embeds).

* Three modes: `delivery` (ball-by-ball aggregates), `batting_stats`, `bowling_stats` (per-innings
  scorecard tables).
* Table routing: `delivery_details` (2015+ men's T20, every other format at every date) and the
  legacy `deliveries` table (men's T20 before 2015); grouped results are merged with alias
  normalisation (`merge_grouped_results`).
* Grouped plan (`handle_grouped_query`): stage 1 per (group, innings) totals for HAVING/paging,
  stage 2 rich aggregates for the surviving groups. Computed group-by columns
  (`ball_in_over`, `ball`, `ball_in_spell`) are window CTEs joined by `dd.id`
  (`COMPUTED_GROUP_BY_COLUMNS`).
* Primer metrics: `LEFT JOIN ball_metrics bm ON bm.delivery_id = dd.id`; sign flipped to the
  bowling side when grouped by bowler and not batter (`metrics_perspective`), wides excluded.
* Shared ball definitions (bowler runs, wickets, dots): `services/metrics/sql_defs.py`.
* Result cache: `services/query_cache.py`, keyed on params + `app_meta.data_version` +
  `LOGIC_VERSION` (bump it with any semantic change).
* Router: `routers/query_builder_v2.py`, `limit` up to 10,000 with `offset`. Frontend:
  `src/components/QueryBuilder.jsx`, URL parsing in `src/utils/urlParamParser.js` (already reads
  `limit`/`offset`).

## Player profile "Advanced Analytics"

Bowling only. `src/components/playerProfile/AdvancedBowlingAnalyticsSection.jsx` calls:

* `/player/{name}/bowling-context` → `services/bowling_context.get_bowling_context`: entry-point
  stats (entry over), spell shape (first vs later spells, spell-length distribution; spells split
  by a gap > 2 overs), first-/last-ball boundary rates, previous-over pressure buckets
  (threshold N: high ≥ N, low ≤ N−4), state on entry. All economy-based, no game-state adjustment.
* `/player/{name}/rolling-form` → `services/rolling_form.get_player_rolling_form`.
* `/relative-metrics/player/{name}` → `services/relative_metrics.py`.
* `/leaderboards/first-ball-boundaries` → `bowling_context.get_first_ball_boundary_leaderboard`.

## Notes system

* Storage: Postgres tables `notes`, `note_authors`, `chart_snapshots` (migrations 009/010).
  `services/notes.py`, `routers/notes.py`. Everything is created as a `draft`; only the admin
  publishes (`/admin/notes`, token auth in `routers/_auth.py`).
* Authoring: markdown body. A chart is a fenced block naming a snapshot:
  ```` ```hindsight\nchart: <snapshot id>\n``` ````. `POST /admin/notes/charts` turns a pasted
  `/query?...` (or `/scorecard`, `/embed`, `/img`) URL into a snapshot and returns the fence.
* Snapshots (`services/snapshots.py`): frozen query-builder results (kinds `query`, `ranking`,
  `win_prob`, `recap`), shaped by the connector's `structure_query_result`, so a published note
  never changes.
* Rendering: `src/components/notes/` (`NotePage`, `NoteBody` renders fences as `/embed/*` iframes,
  `noteMarkdown.mjs` = `marked` with raw HTML escaped); crawlers get `api/meta.mjs` +
  `api/_lib/note_html.mjs` (each chart as a table). Share images: `api/img.mjs`
  (`@vercel/og`, portrait 1080×1350, dark palette, Barlow fonts).
* Bot drafts: `services/note_drafts.py` + `scripts/draft_notes.py` (nightly recaps/previews).

## Data pipeline

Nightly GitHub Action `.github/workflows/refresh-delivery-details.yml`:
download CSVs → `scripts/load_delivery_details_pipeline.py` (load, advanced-column backfill,
crease combo, players, stats sync, ELO, query-builder metadata) → `scripts/load_cricsheet.py`
fallback → `scripts/compute_primer_metrics.py incremental` (ball_metrics) → alias view refresh →
query-cache invalidation → content packs and note drafts.

## Data provenance (what the repo says, not assumptions)

| Data | Source found | Licence evidence |
|---|---|---|
| Ball-by-ball 2015+ (`delivery_details`, all formats), incl. **line, length, shot, control, wagon zone**, and the feed's own `pred_score`/`win_prob` | Four CSVs (`t20_bbb.csv`, `odi_bbb.csv`, `womens_t20_bbb.csv`, `test_bbb.csv`) pulled from private Dropbox URLs held in secrets (`DROPBOX_*_URL`; MULTI_FORMAT_PLAN.md "Dataset sources"). Keyed on ESPNcricinfo match ids (`p_match`) and player ids (`p_bat`/`p_bowl`). **The upstream provider is not named anywhere in the repo.** | None in the repo. Code and docs call it "the licensed feed" and keep it aggregate-only (`docs/mcp-connector.md`, HINDSIGHT_FEATURE_PLAN.md) — i.e. raw rows are not redistributed. **Needs the owner to supply the provider name and its attribution terms.** |
| Men's T20 before 2015 (`deliveries`) and the nightly fallback for recent matches the CSVs lack | Cricsheet.org (README "Data Credits", `loadMatches.py`, `scripts/load_cricsheet.py`) | Cricsheet's people register is published under the Open Data Commons Attribution License (ODC-By 1.0) per cricsheet.org/register. The match-data pages checked (home, matches, downloads, about) carry no licence text. Credited as Cricsheet regardless. |
| Player register ids (Cricsheet → ESPNcricinfo id mapping) | Cricsheet people register | ODC-By 1.0 (attribute, state the licence) |
| Player information (bat hand, bowl style) | Credits page lists Cricmetric; the feed also carries `bat_hand`/`bowl_style` | None in the repo |
| Advanced metrics (Impact, RAA, WAA, WPA, leverage, par) | Computed in-house (`services/metrics/`, `scripts/compute_primer_metrics.py`, models in `ml/models/primer/`) following Himanish Ganjoo's *T20 Metrics: A Primer* (August 2026) | Credits page links only his X profile (twitter.com/hganjoo_153); **no link to the primer document exists in the repo.** |

Credits used on notes and cards therefore read: Hindsight (hindsightcricket.com); Cricsheet
(cricsheet.org, ODC-By) for pre-2015 and fallback ball-by-ball; the 2015+ ball-by-ball and
line/length/shot feed as a placeholder (`analysis/hypotheses/credits.py`) until the owner names
it; the Primer line with the X profile link.
