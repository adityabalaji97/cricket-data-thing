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
min 100 balls"*, *"Bumrah's economy by phase"*.

## Tools

| Tool | Purpose |
|---|---|
| `find_entities` | Resolve "kohli" / "chinnaswamy" / "big bash" to exact names (players, teams, venues, competitions). |
| `get_query_options` | Valid values for line, length, shot, bowl style/kind, bat hand, competitions, group-by columns. |
| `query_cricket_data` | The query builder: filters + group_by + sort, returns rows, a text table for the model, an interactive view (`ui://hindsight/query-result`) and an "Open in Hindsight" deep link to `/query`. |

All three are read-only (`readOnlyHint`).

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
  (`MCP_STATEMENT_TIMEOUT_MS`, default 15s); rows capped at 500; a global budget of
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

Auth (add OAuth before sharing widely), wagon-wheel / pitch-map widgets, and the T20 Primer
metrics (RAA, Impact, WPA) — which will reach the connector for free once they are query-builder
columns.
