"""
Hindsight MCP server: the query builder as tools for Claude, ChatGPT and other MCP hosts.

Three read-only tools:
  * find_entities       - resolve "kohli", "chinnaswamy", "ipl" to the exact names the data uses
  * get_query_options   - valid values for the enum-like filters (line, length, shot, ...)
  * query_cricket_data  - the query builder itself; renders an interactive table/chart
                          (MCP Apps view ui://hindsight/query-result) and links back to /query

Served over streamable HTTP at /mcp from the existing FastAPI app (see mount_mcp). Stateless with
plain JSON responses: every request stands alone (fits a single Heroku dyno and its 30s router
limit), and no SSE stream has to survive main.py's BaseHTTPMiddleware, which is known to break
streaming responses.

Guardrails: read-only SQL, a per-statement timeout, capped rows, and a global request budget so a
chatty assistant cannot starve the small DB pool the website shares.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Dict, Iterator, List, Literal, Optional
from urllib.parse import urlencode

from pydantic import Field
from sqlalchemy.sql import text

from mcp.server import MCPServer
from mcp.server.apps import Apps
from mcp.server.mcpserver import Context
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from database import SessionLocal
from services.query_builder_v2 import GROUP_BY_COLUMNS, QueryValidationError, run_deliveries_query

logger = logging.getLogger("hindsight.mcp")

WEB_URL = os.getenv("HINDSIGHT_WEB_URL", "https://hindsight2020.vercel.app").rstrip("/")
UI_URI = "ui://hindsight/query-result"
STATEMENT_TIMEOUT_MS = int(os.getenv("MCP_STATEMENT_TIMEOUT_MS", "15000"))
DEFAULT_ROWS = 50
MAX_ROWS = 500
# Rows fetched before sorting/truncating, so "top 10 by strike rate" ranks the whole result
# rather than whichever 10 groups the service happened to return first.
SORT_FETCH_LIMIT = 2000

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

GroupByColumn = Literal[GROUP_BY_COLUMNS]  # type: ignore[valid-type]


# --------------------------------------------------------------------------------------------
# Guardrails
# --------------------------------------------------------------------------------------------

class _RequestBudget:
    """
    Sliding-window cap on tool calls across all clients.

    Hosts call from their own servers, so every friend using Claude arrives from a few shared
    IPs; a per-IP limit would throttle them all together. What needs protecting is the database
    pool the website also uses, so the budget is global.
    """

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._calls: deque = deque()
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._calls and now - self._calls[0] > 60:
                self._calls.popleft()
            if len(self._calls) >= self.per_minute:
                return False
            self._calls.append(now)
            return True


_budget = _RequestBudget(int(os.getenv("MCP_CALLS_PER_MINUTE", "60")))

_BUSY = CallToolResult(
    content=[TextContent(type="text", text="Hindsight is busy right now (too many queries in the last minute). Please try again shortly.")],
    is_error=True,
)


@contextmanager
def _read_only_session() -> Iterator[Any]:
    """A DB session whose statements are capped and can never write."""
    db = SessionLocal()
    try:
        # SET LOCAL lasts for the surrounding transaction, which is the whole tool call because
        # the query paths never commit. READ ONLY makes accidental writes impossible.
        db.execute(text("SET TRANSACTION READ ONLY"))
        db.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
        yield db
    finally:
        db.rollback()
        db.close()


def _log_call(tool: str, ctx: Optional[Context], args: Dict[str, Any], started: float, outcome: str) -> None:
    headers = {}
    try:
        headers = dict(ctx.headers or {}) if ctx is not None else {}
    except Exception:  # pragma: no cover - headers are best-effort
        pass
    logger.info(json.dumps({
        "event": "mcp_call",
        "tool": tool,
        "outcome": outcome,
        "ms": int((time.monotonic() - started) * 1000),
        "client": headers.get("user-agent", "")[:80],
        "args": {k: v for k, v in args.items() if v not in (None, [], "", False)},
    }, default=str))


def _error(message: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=message)], is_error=True)


def _user_message(exc: Exception, fallback: str) -> str:
    """
    What the assistant (and so the user) is told when a call fails.

    The service rejects bad filter combinations with an HTTPException whose detail is written for
    users, so that is passed through. Anything else -- driver errors, connection failures --
    carries hostnames and internals, so it is logged server-side and replaced with a plain message.
    """
    text_ = str(exc).lower()
    if "statement timeout" in text_ or "canceling statement" in text_:
        return "That query took too long. Narrow it (a player, team, season or competition) and try again."
    detail = getattr(exc, "detail", None)
    status = getattr(exc, "status_code", None)
    if isinstance(detail, str) and detail and status is not None and 400 <= status < 500:
        return detail
    return fallback + " Please try again in a moment."


# --------------------------------------------------------------------------------------------
# Result shaping
# --------------------------------------------------------------------------------------------

# Metric columns in the order people usually want them; unknown columns follow.
_METRIC_ORDER = [
    "balls", "balls_faced", "runs", "wickets", "dismissals", "innings_count", "matches",
    "average", "strike_rate", "economy", "bowling_strike_rate", "balls_per_dismissal",
    "dot_percentage", "boundary_percentage", "control_percentage", "fours", "sixes", "dots",
    "boundaries", "percent_balls",
]
_SEQUENTIAL_KEYS = {"year", "over", "ball", "ball_in_over", "ball_in_spell", "innings", "batting_position"}
# The first of these present is charted by default, per query mode.
_DEFAULT_CHART_METRIC = {
    "delivery": ["strike_rate", "runs", "balls"],
    "batting_stats": ["runs", "strike_rate", "average"],
    "bowling_stats": ["wickets", "economy", "runs_conceded"],
}


def _normalise_value(value: Any) -> Any:
    """
    Make numbers JSON numbers. The merged sources return some values as Decimal (Postgres
    numeric, e.g. EXTRACT(year) from the legacy table), which serialises as a string -- so 2013
    arrived as "2013" beside 2024 and sorted after it -- and a few as numeric strings.
    """
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else round(float(value), 2)
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return int(stripped)
        except ValueError:
            try:
                return round(float(stripped), 2)
            except ValueError:
                return value
    if isinstance(value, float):
        return round(value, 2)
    return value


_PHASE_ORDER = {"powerplay": 0, "middle": 1, "middle1": 1, "middle2": 2, "death": 3}


def _sequence_key(column: str, value: Any) -> tuple:
    """Sort key for ordered groupings; tolerates mixed ints/strings and missing values."""
    if value is None:
        return (2, 0, "")
    if column == "phase":
        return (0, _PHASE_ORDER.get(str(value).lower(), 99), str(value))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, value, "")
    return (1, 0, str(value))


def _with_economy(row: Dict[str, Any], query_mode: str) -> Dict[str, Any]:
    """
    Delivery-mode rows are batter-perspective (runs, strike_rate). For bowling questions the number
    people use is economy (runs per over), so derive it wherever runs and balls are present.
    """
    if query_mode == "delivery" and "economy" not in row:
        runs, balls = row.get("runs"), row.get("balls")
        if isinstance(runs, (int, float)) and isinstance(balls, (int, float)) and balls:
            row["economy"] = round(runs * 6 / balls, 2)
    return row


def _order_columns(rows: List[Dict[str, Any]], group_by: List[str]) -> List[str]:
    seen: List[str] = []
    for row in rows:
        for key in row:
            if key not in seen:
                seen.append(key)
    keys = [g for g in group_by if g in seen]
    metrics = [m for m in _METRIC_ORDER if m in seen and m not in keys]
    rest = [c for c in seen if c not in keys and c not in metrics]
    return keys + metrics + rest


def _choose_chart(
    requested: str,
    group_by: List[str],
    rows: List[Dict[str, Any]],
    metric_columns: List[str],
    query_mode: str,
    chart_metric: Optional[str],
    scatter_x: Optional[str],
    scatter_y: Optional[str],
) -> Dict[str, Any]:
    if not group_by or not rows or requested == "table":
        return {"type": "table"}
    label_key = group_by[0]
    metric = chart_metric if chart_metric in metric_columns else next(
        (m for m in _DEFAULT_CHART_METRIC.get(query_mode, []) if m in metric_columns),
        metric_columns[0] if metric_columns else None,
    )
    if requested == "scatter" or (requested == "auto" and scatter_x and scatter_y):
        x = scatter_x if scatter_x in metric_columns else ("strike_rate" if "strike_rate" in metric_columns else None)
        y = scatter_y if scatter_y in metric_columns else ("average" if "average" in metric_columns else None)
        if x and y:
            return {"type": "scatter", "label_key": label_key, "x": x, "y": y}
    if requested == "line" or (requested == "auto" and len(group_by) == 1 and label_key in _SEQUENTIAL_KEYS):
        return {"type": "line", "label_key": label_key, "metric": metric}
    if requested in ("bar", "auto") and len(group_by) == 1:
        return {"type": "bar", "label_key": label_key, "metric": metric}
    return {"type": "table"}


def _format_slug(fmt: str, gender: str) -> str:
    if fmt == "ALL":
        return "all"
    return f"{'mens' if gender == 'male' else 'womens'}-{fmt.lower()}"


def _hindsight_url(params: Dict[str, Any], group_by: List[str], fmt: str, gender: str) -> str:
    """Deep link that reopens the same query on the website's /query page (it auto-runs)."""
    pairs: List[tuple] = []
    for key, value in params.items():
        if value is None or value == [] or value == "" or value is False:
            continue
        if key == "query_mode" and value == "delivery":
            continue
        if isinstance(value, list):
            pairs.extend((key, str(v)) for v in value)
        elif isinstance(value, bool):
            pairs.append((key, "true"))
        else:
            pairs.append((key, str(value)))
    pairs.extend(("group_by", g) for g in group_by)
    pairs.append(("fmt", _format_slug(fmt, gender)))
    return f"{WEB_URL}/query?{urlencode(pairs)}"


def _filter_chips(params: Dict[str, Any], fmt: str) -> List[str]:
    chips = []
    labels = {
        "batters": "Batter", "bowlers": "Bowler", "players": "Player", "teams": "Team",
        "batting_teams": "Batting", "bowling_teams": "Bowling", "venue": "Venue", "leagues": "League",
        "bowl_kind": "Bowl kind", "bowl_style": "Bowl style", "bat_hand": "Bat hand", "line": "Line",
        "length": "Length", "shot": "Shot", "dismissal": "Dismissal", "innings": "Innings",
        "match_outcome": "Result", "chase_outcome": "Chase result", "toss_decision": "Toss",
    }
    for key, label in labels.items():
        value = params.get(key)
        if value in (None, [], ""):
            continue
        shown = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
        chips.append(f"{label}: {shown}")
    if params.get("start_date") or params.get("end_date"):
        chips.append(f"{params.get('start_date') or '…'} → {params.get('end_date') or 'today'}")
    if params.get("over_min") is not None or params.get("over_max") is not None:
        # Overs are 0-indexed in the data; show them as people count them.
        lo = (params.get("over_min") or 0) + 1
        hi = params.get("over_max")
        chips.append(f"Overs {lo}–{hi + 1 if hi is not None else 'end'}")
    if params.get("is_chase") is not None:
        chips.append("Chasing" if params["is_chase"] else "Setting")
    if params.get("include_international"):
        chips.append("Incl. internationals" + (f" (top {params['top_teams']})" if params.get("top_teams") else ""))
    chips.append("All formats" if fmt == "ALL" else fmt)
    return chips


def _title(params: Dict[str, Any], group_by: List[str]) -> str:
    who = params.get("batters") or params.get("bowlers") or params.get("players") or params.get("teams") \
        or params.get("batting_teams") or params.get("bowling_teams")
    subject = ", ".join(who[:3]) + (" +" if len(who) > 3 else "") if who else (params.get("venue") or "All matches")
    if group_by:
        return f"{subject} · by {', '.join(g.replace('_', ' ') for g in group_by)}"
    return subject


def _markdown_table(columns: List[str], rows: List[Dict[str, Any]], max_rows: int = 25) -> str:
    shown = columns[:10]
    lines = ["| " + " | ".join(shown) + " |", "|" + "---|" * len(shown)]
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join("" if row.get(c) is None else str(row.get(c)) for c in shown) + " |")
    if len(rows) > max_rows:
        lines.append(f"| … {len(rows) - max_rows} more rows (shown in the widget) |")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------
# Server
# --------------------------------------------------------------------------------------------

INSTRUCTIONS = """\
Hindsight is a ball-by-ball cricket database (men's T20 since 2005 incl. IPL, BBL, PSL, CPL,
SA20, T20 Blast, The Hundred, T20Is; men's ODIs since 2000). Line/length/shot data exists from
2015 and is patchier than the rest.

How to use the tools:
1. Resolve names first with find_entities — player, team and venue names must match the data
   exactly (e.g. "V Kohli", "M Chinnaswamy Stadium, Bengaluru").
2. For enum-like filters (line, length, shot, bowl_style, bowl_kind, dismissal, competitions)
   call get_query_options once and use its values verbatim.
3. query_cricket_data answers the question. group_by is required (results are aggregated).
   For leaderboards, group by batter or bowler, set
   min_balls (e.g. 120) to drop small samples, and sort_by the metric. Group by "phase" for
   powerplay/middle/death, "year" for trends, "format" when mixing T20 and ODI.
Overs are 0-indexed (over_min=0, over_max=5 is the powerplay). Default format is ALL; pin
format="T20" for T20-only questions. The result renders as an interactive table/chart and
includes a link to open the same query on the Hindsight website — mention it to the user.
4. preview_match gives a fixture preview (venue record, leaders, head-to-head, form, standout
   batter-vs-bowler matchups) for two teams at a venue in T20 or ODI — use it for "preview X v Y
   at Z" questions, then drill in with query_cricket_data.
"""

apps = Apps()


@apps.tool(
    resource_uri=UI_URI,
    name="query_cricket_data",
    title="Query Hindsight cricket data",
    description=(
        "Run a Hindsight query-builder query over ball-by-ball cricket data and return aggregated "
        "rows (runs, balls, strike rate, average, dot %, boundary %, wickets, economy...) plus an "
        "interactive chart/table and a link to open it on the website. Use find_entities for "
        "exact names and get_query_options for filter values first."
    ),
    annotations=READ_ONLY,
)
def query_cricket_data(
    ctx: Context,
    group_by: Annotated[List[GroupByColumn], Field(min_length=1, description="Columns to aggregate by (required), e.g. ['batter'], ['bowl_kind','year'], ['phase'].")],
    batters: Annotated[List[str], Field(description="Exact batter names from find_entities, e.g. ['V Kohli'].")] = [],
    bowlers: Annotated[List[str], Field(description="Exact bowler names from find_entities.")] = [],
    players: Annotated[List[str], Field(description="Players matched as batter OR bowler.")] = [],
    batting_teams: Annotated[List[str], Field(description="Team batting, exact names.")] = [],
    bowling_teams: Annotated[List[str], Field(description="Team bowling, exact names.")] = [],
    teams: Annotated[List[str], Field(description="Team either batting or bowling.")] = [],
    venue: Annotated[Optional[str], Field(description="Exact venue name from find_entities.")] = None,
    leagues: Annotated[List[str], Field(description="Competitions, e.g. ['IPL','BBL'] (abbreviations work).")] = [],
    include_international: Annotated[bool, Field(description="Include T20Is/ODIs between national sides.")] = False,
    top_teams: Annotated[Optional[int], Field(ge=1, le=30, description="With include_international, only matches between the top N national teams.")] = None,
    start_date: Annotated[Optional[date], Field(description="YYYY-MM-DD inclusive.")] = None,
    end_date: Annotated[Optional[date], Field(description="YYYY-MM-DD inclusive.")] = None,
    format: Annotated[Literal["T20", "ODI", "ALL"], Field(description="Cricket format. ALL mixes formats; add 'format' to group_by to keep rows comparable.")] = "ALL",
    gender: Annotated[Literal["male", "female"], Field(description="Men's or women's cricket.")] = "male",
    query_mode: Annotated[Literal["delivery", "batting_stats", "bowling_stats"], Field(description="delivery = ball-by-ball aggregates (supports line/length/shot filters); batting_stats / bowling_stats = per-innings scorecard aggregates (faster for career totals, 50s/100s-style questions).")] = "delivery",
    innings: Annotated[Optional[int], Field(ge=1, le=4, description="1 = batting first, 2 = chasing.")] = None,
    over_min: Annotated[Optional[int], Field(ge=0, description="First over, 0-indexed (0 = first over).")] = None,
    over_max: Annotated[Optional[int], Field(ge=0, description="Last over, 0-indexed (5 = end of the T20 powerplay, 19 = last T20 over).")] = None,
    bat_hand: Annotated[Optional[Literal["LHB", "RHB"]], Field(description="Batter's hand.")] = None,
    bowl_kind: Annotated[List[str], Field(description="Values from get_query_options, e.g. ['pace bowler'] or ['spin bowler'].")] = [],
    bowl_style: Annotated[List[str], Field(description="Values from get_query_options, e.g. ['LAO','SLA'] for left-arm spin.")] = [],
    line: Annotated[List[str], Field(description="Values from get_query_options.")] = [],
    length: Annotated[List[str], Field(description="Values from get_query_options.")] = [],
    shot: Annotated[List[str], Field(description="Values from get_query_options.")] = [],
    control: Annotated[Optional[Literal[0, 1]], Field(description="1 = controlled shots, 0 = uncontrolled.")] = None,
    wagon_zone: Annotated[List[int], Field(description="Wagon-wheel zones 0-8.")] = [],
    dismissal: Annotated[List[str], Field(description="Dismissal types, e.g. ['caught','bowled','lbw'].")] = [],
    match_outcome: Annotated[List[Literal["win", "loss", "tie", "no_result"]], Field(description="Batting side's match result.")] = [],
    is_chase: Annotated[Optional[bool], Field(description="True = chasing innings only, False = setting only.")] = None,
    chase_outcome: Annotated[List[Literal["win", "loss", "tie", "no_result"]], Field(description="Result of the chase (chasing side's view).")] = [],
    toss_decision: Annotated[List[Literal["bat", "field"]], Field(description="Toss decision.")] = [],
    min_balls: Annotated[Optional[int], Field(ge=1, description="Drop groups with fewer balls (use for leaderboards, e.g. 120).")] = None,
    min_runs: Annotated[Optional[int], Field(ge=0, description="Drop groups with fewer runs.")] = None,
    min_wickets: Annotated[Optional[int], Field(ge=0, description="Drop groups with fewer wickets.")] = None,
    sort_by: Annotated[Optional[str], Field(description="Column to rank by, e.g. 'strike_rate', 'runs', 'economy', 'wickets'.")] = None,
    sort_descending: Annotated[bool, Field(description="Highest first (set False for economy-style metrics where lower is better).")] = True,
    limit: Annotated[int, Field(ge=1, le=MAX_ROWS, description=f"Rows to return (max {MAX_ROWS}).")] = DEFAULT_ROWS,
    chart: Annotated[Literal["auto", "table", "bar", "line", "scatter"], Field(description="Visual for the widget. auto picks line for year/over, bar for one categorical group.")] = "auto",
    chart_metric: Annotated[Optional[str], Field(description="Metric to plot for bar/line, e.g. 'strike_rate'.")] = None,
    scatter_x: Annotated[Optional[str], Field(description="Scatter x metric, e.g. 'strike_rate'.")] = None,
    scatter_y: Annotated[Optional[str], Field(description="Scatter y metric, e.g. 'average'.")] = None,
) -> CallToolResult:
    started = time.monotonic()
    params: Dict[str, Any] = {
        "venue": venue, "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None, "leagues": leagues, "teams": teams,
        "batting_teams": batting_teams, "bowling_teams": bowling_teams, "players": players,
        "batters": batters, "bowlers": bowlers, "bat_hand": bat_hand, "bowl_style": bowl_style,
        "bowl_kind": bowl_kind, "line": line, "length": length, "shot": shot, "control": control,
        "wagon_zone": wagon_zone, "dismissal": dismissal, "innings": innings, "over_min": over_min,
        "over_max": over_max, "match_outcome": match_outcome, "is_chase": is_chase,
        "chase_outcome": chase_outcome, "toss_decision": toss_decision, "min_balls": min_balls,
        "min_runs": min_runs, "min_wickets": min_wickets, "include_international": include_international,
        "top_teams": top_teams, "query_mode": query_mode,
    }
    group_by = list(dict.fromkeys(group_by))
    if not group_by:
        # Aggregates only: raw ball-by-ball rows (with line/length/shot from the licensed feed)
        # are not redistributed through the public connector.
        return _error("query_cricket_data returns aggregated results only. Pass group_by, e.g. "
                      "['batter'], ['year'], ['phase'] or ['bowl_kind'].")
    if not _budget.try_acquire():
        _log_call("query_cricket_data", ctx, params, started, "busy")
        return _BUSY

    fetch_limit = SORT_FETCH_LIMIT if (sort_by and group_by) else limit
    try:
        with _read_only_session() as db:
            result = run_deliveries_query(
                db,
                venue=venue, start_date=start_date, end_date=end_date, leagues=leagues, teams=teams,
                batting_teams=batting_teams, bowling_teams=bowling_teams, players=players,
                batters=batters, bowlers=bowlers, bat_hand=bat_hand, bowl_style=bowl_style,
                bowl_kind=bowl_kind, line=line, length=length, shot=shot, control=control,
                wagon_zone=wagon_zone, dismissal=dismissal, innings=innings, over_min=over_min,
                over_max=over_max, match_outcome=match_outcome, is_chase=is_chase,
                chase_outcome=chase_outcome, toss_decision=toss_decision, group_by=group_by,
                min_balls=min_balls, min_runs=min_runs, min_wickets=min_wickets, limit=fetch_limit,
                offset=0, include_international=include_international, top_teams=top_teams,
                query_mode=query_mode, fmt=format, gender=gender,
            )
    except QueryValidationError as exc:
        _log_call("query_cricket_data", ctx, params, started, "invalid")
        return _error(str(exc))
    except Exception as exc:
        _log_call("query_cricket_data", ctx, params, started, "error")
        logger.warning("mcp query failed: %r", exc)
        return _error(_user_message(exc, "That query could not be run."))

    raw_rows = result.get("data") or []
    # A bowling question: bowlers are filtered, or rows are split by bowler, and no batter is picked.
    bowler_centric = (bool(bowlers) or "bowler" in group_by) and not batters
    rows = [{k: _normalise_value(v) for k, v in row.items()} for row in raw_rows]
    if bowler_centric:
        rows = [_with_economy(row, query_mode) for row in rows]
    meta = result.get("metadata") or {}

    def _num(value: Any) -> Optional[float]:
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    if sort_by and rows and any(_num(r.get(sort_by)) is not None for r in rows):
        # Missing values sort last whichever direction is asked for.
        rows.sort(key=lambda r: (
            _num(r.get(sort_by)) is None,
            -(_num(r.get(sort_by)) or 0.0) if sort_descending else (_num(r.get(sort_by)) or 0.0),
        ))
    elif group_by and (group_by[0] in _SEQUENTIAL_KEYS or group_by[0] == "phase"):
        rows.sort(key=lambda r: _sequence_key(group_by[0], r.get(group_by[0])))
    total_rows = meta.get("total_groups") or meta.get("total_rows") or len(rows)
    rows = rows[:limit]

    columns = _order_columns(rows, group_by)
    metric_columns = [
        c for c in columns
        if c not in group_by and any(isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool) for r in rows)
    ]
    default_metric = chart_metric or sort_by or ("economy" if bowler_centric and "economy" in metric_columns else None)
    chart_spec = _choose_chart(chart, group_by, rows, metric_columns, query_mode, default_metric, scatter_x, scatter_y)
    url = _hindsight_url(params, group_by, format, gender)
    warnings = [w for w in (meta.get("warnings") or []) if w]

    structured = {
        "title": _title(params, group_by),
        "subtitle": f"{len(rows)} of {total_rows} rows" + (f" · ranked by {sort_by}" if sort_by else ""),
        "filter_chips": _filter_chips(params, format),
        "group_by": group_by,
        "query_mode": query_mode,
        "columns": columns,
        "metric_columns": metric_columns,
        "rows": rows,
        "total_rows": total_rows,
        "chart": chart_spec,
        "hindsight_url": url,
        "warnings": warnings,
        "note": " ".join(warnings) if warnings else None,
    }

    if not rows:
        summary = "No rows match these filters. Check exact names with find_entities, or loosen filters (dates, min_balls, competitions)."
    else:
        summary = (
            f"{structured['title']} — {len(rows)} of {total_rows} rows"
            + (f", ranked by {sort_by}" if sort_by else "") + ".\n\n"
            + _markdown_table(columns, rows)
            + f"\n\nOpen this query on Hindsight: {url}"
        )
        if warnings:
            summary += "\n\nNotes: " + " ".join(warnings)

    _log_call("query_cricket_data", ctx, params, started, "ok")
    return CallToolResult(content=[TextContent(type="text", text=summary)], structured_content=structured)


apps.add_html_resource(
    UI_URI,
    (Path(__file__).parent / "widget.html").read_text(encoding="utf-8"),
    name="Hindsight query result",
    description="Interactive table and chart for a Hindsight query-builder result.",
    prefers_border=False,
)


mcp = MCPServer(
    name="hindsight",
    title="Hindsight cricket data",
    description="Query ball-by-ball cricket data from Hindsight (hindsight2020.vercel.app).",
    instructions=INSTRUCTIONS,
    website_url=WEB_URL,
    version="1.0.0",
    extensions=[apps],
)


@mcp.tool(
    name="find_entities",
    title="Find players, teams, venues or competitions",
    description=(
        "Resolve a partial or informal name ('kohli', 'chinnaswamy', 'rcb', 'big bash') to the "
        "exact names Hindsight uses. Call this before filtering query_cricket_data by name."
    ),
    annotations=READ_ONLY,
)
def find_entities(
    ctx: Context,
    query: Annotated[str, Field(min_length=2, description="Name or part of a name.")],
    kind: Annotated[Optional[Literal["player", "team", "venue", "competition"]], Field(description="Restrict to one kind.")] = None,
    limit: Annotated[int, Field(ge=1, le=25, description="Maximum matches.")] = 8,
) -> CallToolResult:
    from services.search import search_entities

    started = time.monotonic()
    args = {"query": query, "kind": kind, "limit": limit}
    if not _budget.try_acquire():
        return _BUSY
    matches: List[Dict[str, Any]] = []
    try:
        with _read_only_session() as db:
            if kind != "competition":
                for item in search_entities(query, db, limit=limit * 2):
                    if kind and item.get("type") != kind:
                        continue
                    entry = {"type": item.get("type"), "name": item.get("name")}
                    display = item.get("display_name")
                    if display and display != entry["name"]:
                        entry["also_known_as"] = display
                    matches.append(entry)
            if kind in (None, "competition"):
                matches.extend(_match_competitions(db, query))
    except Exception as exc:
        _log_call("find_entities", ctx, args, started, "error")
        logger.warning("mcp search failed: %r", exc)
        return _error(_user_message(exc, "Search is unavailable right now."))
    matches = matches[:limit]
    _log_call("find_entities", ctx, args, started, "ok")
    if not matches:
        return CallToolResult(content=[TextContent(type="text", text=f"No players, teams, venues or competitions match '{query}'.")],
                              structured_content={"matches": []})
    lines = [f"- {m['type']}: {m['name']}" + (f" (a.k.a. {m['also_known_as']})" if m.get("also_known_as") else "") for m in matches]
    return CallToolResult(
        content=[TextContent(type="text", text="Use these exact names in query_cricket_data:\n" + "\n".join(lines))],
        structured_content={"matches": matches},
    )


def _match_competitions(db: Any, query: str) -> List[Dict[str, Any]]:
    from services.competition_aliases import canonical_competition, variants_for

    row = db.execute(text("SELECT values FROM query_builder_metadata WHERE key = 'competitions'")).fetchone()
    values = row[0] if row and isinstance(row[0], list) else []
    needle = query.strip().lower()
    out, seen = [], set()
    for value in values:
        name = str(value)
        canonical = canonical_competition(name) or name
        # Match every registered spelling, so "big bash" finds BBL and "indian premier" finds IPL.
        spellings = [name, canonical, *variants_for(canonical)]
        if any(needle in spelling.lower() for spelling in spellings):
            if canonical not in seen:
                seen.add(canonical)
                out.append({"type": "competition", "name": canonical})
    return out


@mcp.tool(
    name="get_query_options",
    title="List valid filter values",
    description=(
        "Valid values for query_cricket_data's enum-like filters (line, length, shot, bowl_style, "
        "bowl_kind, bat_hand, competitions) and the group_by columns, with data-coverage notes."
    ),
    annotations=READ_ONLY,
)
def get_query_options(
    ctx: Context,
    format: Annotated[Literal["T20", "ODI", "ALL"], Field(description="Format to list values for.")] = "ALL",
    gender: Annotated[Literal["male", "female"], Field(description="Men's or women's.")] = "male",
) -> CallToolResult:
    from routers.query_builder_v2 import get_available_columns

    started = time.monotonic()
    if not _budget.try_acquire():
        return _BUSY
    try:
        with _read_only_session() as db:
            cols = get_available_columns(format=format, gender=gender, db=db)
    except Exception as exc:
        _log_call("get_query_options", ctx, {"format": format}, started, "error")
        logger.warning("mcp options failed: %r", exc)
        return _error(_user_message(exc, "Filter options are unavailable right now."))

    keys = ["line", "length", "shot", "bowl_style", "bowl_kind", "bat_hand", "wagon_zone", "control"]
    options = {k: cols.get(f"{k}_options") for k in keys}
    options["competitions"] = cols.get("competitions")
    options["group_by"] = cols.get("group_by_columns")
    options["match_outcome"] = cols.get("match_outcome_options")
    options["toss_decision"] = cols.get("toss_decision_options")
    coverage = {k: cols.get(f"{k}_coverage") for k in keys if cols.get(f"{k}_coverage") is not None}
    structured = {
        "format": format,
        "gender": gender,
        "options": options,
        "coverage_percent": coverage,
        "notes": "line/length/shot/control exist from 2015 and cover a minority of balls; filtering on "
                 "them narrows results to balls that have the data.",
    }
    _log_call("get_query_options", ctx, {"format": format}, started, "ok")
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(structured, default=str))],
        structured_content=structured,
    )


PREVIEW_WINDOW_YEARS = {"ODI": 8, "T20": 4}


def _default_window(fmt: str) -> tuple:
    """
    History window ending today, starting 1 January 8 years back for ODIs (they are sparse) and
    4 years back for T20s -- sized for a meaningful number of matches, not an exact span. Same
    rule as the website's preview (src/utils/dateDefaults.js getPreviewStartDate).
    """
    today = date.today()
    return date(today.year - PREVIEW_WINDOW_YEARS.get(fmt, 4), 1, 1), today


def _matchup_edges(team_block: Dict[str, Any], min_balls: int) -> Dict[str, List[Dict[str, Any]]]:
    """Standout batter-vs-bowler pairs from a matchups block, both directions."""
    pairs = []
    for batter, cells in (team_block.get("batting_matchups") or {}).items():
        for bowler, cell in (cells or {}).items():
            if bowler == "Overall" or not isinstance(cell, dict):
                continue
            balls = cell.get("balls") or 0
            if balls < min_balls:
                continue
            pairs.append({
                "batter": batter, "bowler": bowler, "balls": balls, "runs": cell.get("runs"),
                "wickets": cell.get("wickets"), "strike_rate": _normalise_value(cell.get("strike_rate")),
            })
    batter_edges = sorted(
        (p for p in pairs if (p["wickets"] or 0) <= 1), key=lambda p: -(p["strike_rate"] or 0)
    )[:4]
    bowler_edges = sorted(
        pairs, key=lambda p: (-(p["wickets"] or 0), p["strike_rate"] or 0)
    )[:4]
    return {"batter_edges": batter_edges, "bowler_edges": [p for p in bowler_edges if (p["wickets"] or 0) >= 1]}


@mcp.tool(
    name="preview_match",
    title="Preview a match",
    description=(
        "Pre-match preview for two teams at a venue in T20 or ODI: the venue's record (bat-first "
        "wins, average and winning scores), leading run-scorers and wicket-takers there, recent "
        "head-to-head and form, and standout batter-vs-bowler matchups from recent XIs. All numbers "
        "are for the chosen format only. Use find_entities for exact venue and team names."
    ),
    annotations=READ_ONLY,
)
def preview_match(
    ctx: Context,
    venue: Annotated[str, Field(description="Exact venue name from find_entities, e.g. 'Kingsmead, Durban'.")],
    team1: Annotated[str, Field(description="First team, exact name, e.g. 'Australia' or 'Mumbai Indians'.")],
    team2: Annotated[str, Field(description="Second team, exact name.")],
    format: Annotated[Literal["T20", "ODI"], Field(description="Format of the match being previewed.")] = "T20",
    start_date: Annotated[Optional[date], Field(description="History window start (default: 1 January, 4 years back for T20 and 8 for ODI).")] = None,
    end_date: Annotated[Optional[date], Field(description="History window end (default: today).")] = None,
    include_international: Annotated[bool, Field(description="Include internationals in the venue record.")] = True,
    top_teams: Annotated[int, Field(ge=1, le=20, description="Internationals only between the top N sides.")] = 20,
    leagues: Annotated[List[str], Field(description="Competitions for the venue record (empty = all leagues).")] = [],
) -> CallToolResult:
    import main as app  # late import: main.py imports this module at startup
    from services.matchups import get_team_matchups_service

    started = time.monotonic()
    args = {"venue": venue, "team1": team1, "team2": team2, "format": format}
    if not _budget.try_acquire():
        return _BUSY
    default_start, default_end = _default_window(format)
    start, end = start_date or default_start, end_date or default_end
    try:
        with _read_only_session() as db:
            notes = app.get_venue_notes(
                venue=venue, start_date=start, end_date=end, leagues=leagues,
                include_international=include_international, top_teams=top_teams,
                day_or_night=None, format=format, gender="male", db=db,
            )
            stats = app.get_venue_stats(
                venue=venue, start_date=start, end_date=end, leagues=leagues,
                include_international=include_international, top_teams=top_teams,
                day_or_night=None, format=format, gender="male", db=db,
            )
            history = app.get_match_history(
                venue=venue, team1=team1, team2=team2, start_date=start, end_date=end,
                day_or_night=None, format=format, gender="male", db=db,
            )
            matchups = get_team_matchups_service(
                team1=team1, team2=team2, start_date=start, end_date=end, team1_players=[],
                team2_players=[], db=db, use_current_roster=False, innings_position=None,
                venue_filter=None, min_balls=6, day_or_night=None, fmt=format, gender="male",
            )
    except Exception as exc:
        _log_call("preview_match", ctx, args, started, "error")
        logger.warning("mcp preview failed: %r", exc)
        return _error(_user_message(exc, "That preview could not be built."))

    min_balls = 18 if format == "ODI" else 10
    t1_edges = _matchup_edges((matchups or {}).get("team1") or {}, min_balls)
    t2_edges = _matchup_edges((matchups or {}).get("team2") or {}, min_balls)
    h2h = (history or {}).get("h2h_stats") or {}
    link = f"{WEB_URL}/venue?" + urlencode([
        ("venue", venue), ("team1", team1), ("team2", team2), ("includeInternational", "true"),
        ("topTeams", str(top_teams)), ("autoload", "true"), ("fmt", _format_slug(format, "male")),
    ])
    venue_record = {k: _normalise_value(v) for k, v in (notes or {}).items() if not isinstance(v, (dict, list))}
    structured = {
        "venue": venue, "team1": team1, "team2": team2, "format": format,
        "window": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "venue_record": venue_record,
        "top_batters": [{k: _normalise_value(v) for k, v in row.items()} for row in (stats or {}).get("batting_leaders", [])[:5]],
        "top_bowlers": [{k: _normalise_value(v) for k, v in row.items()} for row in (stats or {}).get("bowling_leaders", [])[:5]],
        "head_to_head": {"team1_wins": h2h.get("team1_wins"), "team2_wins": h2h.get("team2_wins"),
                         "no_result": h2h.get("draws"), "recent": h2h.get("recent_matches", [])},
        "recent_form": {"team1": (history or {}).get("team1_results", []), "team2": (history or {}).get("team2_results", [])},
        "recent_at_venue": (history or {}).get("venue_results", []),
        "matchups": {
            f"{team1} batting": t1_edges,
            f"{team2} batting": t2_edges,
        },
        "hindsight_url": link,
    }

    def _pair(p: Dict[str, Any]) -> str:
        return f"{p['batter']} v {p['bowler']}: {p['runs']} off {p['balls']}, {p['wickets']} out (SR {p['strike_rate']})"

    noun = "ODIs" if format == "ODI" else "T20s"
    lines = [f"**{team1} v {team2} at {venue}** ({format}, {start.isoformat()} to {end.isoformat()})", ""]
    total = venue_record.get("total_matches") or 0
    if total:
        lines += [
            f"Venue: {total} {noun} — batting first won {venue_record.get('batting_first_wins')}, chasing won "
            f"{venue_record.get('batting_second_wins')}. Avg 1st innings {venue_record.get('average_first_innings')}, "
            f"avg winning score {venue_record.get('average_winning_score')}, highest chased {venue_record.get('highest_total_chased')}.",
        ]
    else:
        lines.append(f"Venue: no {noun} at this ground in the window (try an earlier start_date).")
    if structured["top_batters"]:
        lines.append("Top run-scorers here: " + "; ".join(
            f"{b.get('name')} {b.get('batRuns')} ({b.get('batInns')} inns, SR {b.get('batSR')})" for b in structured["top_batters"][:3]))
    if structured["top_bowlers"]:
        lines.append("Top wicket-takers here: " + "; ".join(
            f"{b.get('name')} {b.get('bowlWickets')} ({b.get('bowlInns')} inns, econ {b.get('bowlER')})" for b in structured["top_bowlers"][:3]))
    lines.append(f"Head-to-head (last {len(h2h.get('recent_matches') or [])}): {team1} {h2h.get('team1_wins')}, {team2} {h2h.get('team2_wins')}.")
    for side, edges in structured["matchups"].items():
        if edges["batter_edges"]:
            lines.append(f"{side} — batter edges: " + "; ".join(_pair(p) for p in edges["batter_edges"][:3]))
        if edges["bowler_edges"]:
            lines.append(f"{side} — bowler edges: " + "; ".join(_pair(p) for p in edges["bowler_edges"][:3]))
    lines += ["", f"Full preview on Hindsight: {link}"]

    _log_call("preview_match", ctx, args, started, "ok")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))], structured_content=structured)


# --------------------------------------------------------------------------------------------
# Mounting
# --------------------------------------------------------------------------------------------

def mount_mcp(app: Any) -> Any:
    """
    Add POST/GET /mcp to a FastAPI app and return the session manager, whose run() context must
    wrap the app's lifespan (a mounted Starlette app's own lifespan never runs).

    The SDK's routes are added to the parent router rather than app.mount()-ed, so the endpoint is
    exactly /mcp (no /mcp/mcp, no slash redirect that some clients will not follow for POST).
    """
    starlette_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        # DNS-rebinding protection guards servers on localhost from hostile web pages. This is a
        # public, credential-less endpoint behind Heroku's router, so it would only reject
        # legitimate Host/Origin values (herokuapp.com, claude.ai, chatgpt.com, ...).
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    for route in starlette_app.routes:
        app.router.routes.append(route)
    return mcp.session_manager
