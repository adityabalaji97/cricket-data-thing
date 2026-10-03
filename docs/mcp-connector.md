# Hindsight MCP connector

Hindsight's query builder, exposed as an [MCP](https://modelcontextprotocol.io) server so Claude,
ChatGPT and other MCP hosts can query the ball-by-ball data and show results as an interactive
table/chart. Code: `mcp_server/` (server + widget), mounted by `main.py`.

**Endpoint:** `https://cricket-data-thing-672dfbacf476.herokuapp.com/mcp` (streamable HTTP, no auth).

## Adding it

**Claude** (claude.ai web / desktop / mobile): Settings → Connectors → *Add custom connector* →
name `Hindsight`, URL above → Add. Then in a chat, enable it from the tools menu.

**ChatGPT**: Settings → Apps & Connectors → Advanced → enable *Developer mode*, then *Create* →
URL above, authentication *No authentication*. Enable it in a chat from the + menu.

Try: *"Kohli's strike rate against pace vs spin by year in T20s"*, *"top 10 IPL 2026 strike rates,
min 100 balls"*, *"Bumrah's economy by phase"*, *"preview South Africa v Australia at Kingsmead in
ODIs"*. The URL and these steps are also on the Home page ("Use Hindsight in Claude or ChatGPT").

## Tools

| Tool | Purpose |
|---|---|
| `match_recap`, `player_profile` | See the tool descriptions in `mcp_server/server.py`. |
| `find_entities` | Resolve "kohli" / "chinnaswamy" / "big bash" to exact names (players, teams, venues, competitions). |
| `get_query_options` | Valid values for line, length, shot, bowl style/kind, bat hand, competitions, group-by columns. |
| `query_cricket_data` | The query builder: filters + group_by (required) + sort, returns aggregated rows, a short text summary with the first 25 rows, **every row up to `limit` as CSV (or JSON, `result_format`)**, an interactive view (`ui://hindsight/query-result`) and an "Open in Hindsight" deep link to `/query`. `limit` up to 10,000 (same as the website) with `offset` paging (`next_offset` in the result). Men's T20 rows carry the T20 Primer metrics (impact, raa/waa incl. `*_per_100` and `*_per_over`, wpa, avg_leverage); `metrics_perspective` = `bowling` / `batting` pins their sign (default: bowling when grouped by bowler and not batter), and the perspective is printed in the text and in every signed column header, e.g. `raa (bowling view: + = good for bowler)`. Filters `match_ids`, `exclude_batters`, `exclude_bowlers`; match-context dimensions for group_by and `dimension_filters` (`name:op:value`): `bowler_over_number`, `bowler_entry_over`, `spell_number`, `bowler_first_over_runs(_bucket)`, `prev_over_runs(_bucket)`, `prev_over_raa(_bucket)`, `batter_balls_faced(_bucket)`, `impact_player_era`, `season` (`services/query_dimensions.py`). `query_mode='team_innings'` = one record per team innings (total, wickets, run rate, phase run rates, 160+/180+/200+/220+/250+ rates, win %), `services/team_innings.py`. Player names are canonical in every output. |
| `player_advanced` | The profile's Advanced Analytics for a bowler as JSON: previous-over pressure split, spell shape, entry point, first/last-ball boundary rates, state on entry, rolling form. Every bucket has raw economy (labelled unadjusted for game state) and bowling-view `raa_per_over` / `waa_per_over`. |
| `preview_match` | Fixture preview for two teams at a venue in T20 or ODI: venue record, leading run-scorers/wicket-takers there, head-to-head, recent form, standout batter-vs-bowler matchups, and a link to the site's preview. Format-specific throughout. History window defaults to 1 January 8 years back for ODIs and 4 years back for T20s (same as the website's preview). |

All are read-only (`readOnlyHint`). Results are **aggregated only** — `group_by` is required, so
raw ball-by-ball rows (line/length/shot from the licensed feed) are never redistributed.

## How it is built

* **MCP Python SDK 2.2** (`MCPServer` + the `Apps` extension for MCP Apps). The widget
  (`mcp_server/widget.html`) is one self-contained HTML file — hosts block external scripts by
  default — drawing tables and SVG charts, following the host's light/dark theme, and reporting its
  height with `ui/notifications/size-changed`.
* **Stateless streamable HTTP with JSON responses.** No SSE streams (main.py's `BaseHTTPMiddleware`
  breaks streaming responses) and nothing to keep between requests on a single dyno. The SDK route
  is added to FastAPI's router so the path is exactly `/mcp`; its session manager runs inside
  `main.py`'s `lifespan` (a mounted app's own lifespan never runs).
* **Same query path as the website.** `services.query_builder_v2.run_deliveries_query` is shared
  by `GET /query/deliveries` and the tool, including the per-format over/innings validation.
* **Guardrails:** every call runs in a `READ ONLY` transaction with `statement_timeout`
  (`MCP_STATEMENT_TIMEOUT_MS`, default 15s); rows capped at 10,000 (`offset` paging); a global budget of
  `MCP_CALLS_PER_MINUTE` (default 60) — global rather than per-IP because hosts call from shared
  servers. Driver errors are logged, not shown to users.
* **DNS-rebinding protection is off** on purpose: it protects localhost servers, and on a public
  credential-less endpoint it would only reject legitimate Host/Origin values.
* **Logging:** each call logs one `mcp_call` JSON line (tool, args, outcome, ms, client) —
  `heroku logs -a cricket-data-thing | grep mcp_call` shows what people ask.

## Testing locally

```bash
scripts/dev/run_local_api.sh            # or any uvicorn main:app
npx @modelcontextprotocol/inspector     # connect to http://localhost:8000/mcp (Streamable HTTP)
```

## Not yet

Auth (add OAuth before sharing widely) and wagon-wheel / pitch-map widgets. (The T20 Primer
metrics arrived with Phase 2 as query-builder columns, so the connector has them.)
