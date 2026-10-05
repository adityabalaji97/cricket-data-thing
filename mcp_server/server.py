"""
Hindsight MCP server: the query builder as tools for Claude, ChatGPT and other MCP hosts.

Read-only tools:
  * find_entities       - resolve "kohli", "chinnaswamy", "ipl" to the exact names the data uses
  * get_query_options   - valid values for the enum-like filters (line, length, shot, ...)
  * query_cricket_data  - the query builder itself; renders an interactive table/chart
                          (MCP Apps view ui://hindsight/query-result), returns every row up to
                          `limit` as CSV/JSON for the model, and links back to /query
  * preview_match, match_recap, player_profile, player_advanced - packaged views

Served over streamable HTTP at /mcp from the existing FastAPI app (see mount_mcp). Stateless with
plain JSON responses: every request stands alone (fits a single Heroku dyno and its 30s router
limit), and no SSE stream has to survive main.py's BaseHTTPMiddleware, which is known to break
streaming responses.

Guardrails: read-only SQL, a per-statement timeout, capped rows, and a global request budget so a
chatty assistant cannot starve the small DB pool the website shares.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import threading
import time
from collections import deque
from contextlib import asynccontextmanager, contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Callable, Dict, Iterator, List, Literal, Optional
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
from services.team_innings import GROUP_BY as TEAM_INNINGS_GROUP_BY

logger = logging.getLogger("hindsight.mcp")

WEB_URL = os.getenv("HINDSIGHT_WEB_URL", "https://hindsightcricket.com").rstrip("/")
UI_URI = "ui://hindsight/query-result"
STATEMENT_TIMEOUT_MS = int(os.getenv("MCP_STATEMENT_TIMEOUT_MS", "15000"))
DEFAULT_ROWS = 50
# Same cap as the website's query builder (routers/query_builder_v2.py), with offset paging.
MAX_ROWS = 10000
# Rows fetched before sorting/truncating, so "top 10 by strike rate" ranks the whole result
# rather than whichever 10 groups the service happened to return first.
SORT_FETCH_LIMIT = MAX_ROWS
# Rows shown in the human-readable markdown table; the full result rides along as CSV/JSON.
TEXT_TABLE_ROWS = 25

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

GroupByColumn = Literal[tuple(dict.fromkeys([*GROUP_BY_COLUMNS, *TEAM_INNINGS_GROUP_BY]))]  # type: ignore[valid-type]


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
    ms = int((time.monotonic() - started) * 1000)
    client = headers.get("user-agent", "")[:80]
    kept_args = {k: v for k, v in args.items() if v not in (None, [], "", False)}
    logger.info(json.dumps({
        "event": "mcp_call",
        "tool": tool,
        "outcome": outcome,
        "ms": ms,
        "client": client,
        "args": kept_args,
    }, default=str))
    # Persisted too (mcp_call_log), from a background thread, so weekly usage survives Heroku's
    # rolling log buffer. Never raises.
    try:
        from services.usage_log import log_mcp_call

        log_mcp_call(tool, outcome, ms, client, headers.get("x-forwarded-for"), kept_args)
    except Exception:  # pragma: no cover - logging must not affect the call
        pass


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
    # T20 Primer metrics (men's T20 only; null elsewhere).
    "impact", "impact_per_100", "impact_per_innings", "raa", "raa_per_100", "raa_per_over", "raa_lw_per_100", "waa",
    "waa_per_100", "waa_per_over", "wpa", "wpa_per_innings", "avg_leverage",
    # team_innings mode
    "avg_total", "avg_wickets", "run_rate", "powerplay_run_rate", "middle_run_rate",
    "death_run_rate", "pct_160_plus", "pct_180_plus", "pct_200_plus", "pct_220_plus", "pct_250_plus",
    "count_200_plus", "count_250_plus", "highest_total", "win_percentage",
]
# Primer columns whose sign depends on the perspective; labelled in the text table.
_SIGNED_METRICS = ("impact", "impact_per_100", "impact_per_innings", "raa", "raa_per_100", "raa_per_over", "raa_lw_per_100",
                   "waa", "waa_per_100", "waa_per_over", "wpa", "wpa_per_innings")
_PLAYER_COLUMNS = ("batter", "bowler", "non_striker", "player")
# Bookkeeping that rides along with the Primer metrics; reported once in metadata, not per row.
_ROW_INTERNAL = {"metric_balls", "metrics_perspective"}
_SEQUENTIAL_KEYS = {"year", "over", "ball", "ball_in_over", "ball_in_spell", "innings", "batting_position",
                    "bowler_over_number", "bowler_entry_over", "spell_number", "bowler_first_over_runs",
                    "prev_over_runs", "prev_over_raa", "next_over_runs", "batter_balls_faced", "season", "match_date"}
# Bucketed dimensions sort in their natural order, not alphabetically ('10+' after '7-9').
_BUCKET_ORDER = {
    "bowler_first_over_runs_bucket": ("0-6", "7-9", "10+"),
    "prev_over_runs_bucket": ("0-6", "7-9", "10+"),
    "next_over_runs_bucket": ("0-6", "7-9", "10+"),
    "prev_over_raa_bucket": ("below -2", "-2 to +2", "above +2"),
    "batter_balls_faced_bucket": ("1-9", "10-19", "20-29", "30-39", "40-49", "50+"),
    "batter_innings_strike_rate_bucket": ("under 110", "110-129", "130-149", "150+"),
    "impact_player_era": ("pre-2023", "2023+"),
    "total_bucket": ("<140", "140-159", "160-179", "180-199", "200-219", "220-249", "250+"),
}
# The first of these present is charted by default, per query mode.
_DEFAULT_CHART_METRIC = {
    "delivery": ["strike_rate", "runs", "balls"],
    "batting_stats": ["runs", "strike_rate", "average"],
    "bowling_stats": ["wickets", "economy", "runs_conceded"],
    "team_innings": ["avg_total", "pct_200_plus", "run_rate"],
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
    if column in _BUCKET_ORDER:
        order = _BUCKET_ORDER[column]
        return (0, order.index(value) if value in order else len(order), str(value))
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


def _hindsight_url(params: Dict[str, Any], group_by: List[str], fmt: str, gender: str,
                   limit: Optional[int] = None, offset: int = 0) -> str:
    """Deep link that reopens the same query on the website's /query page (it auto-runs).

    limit/offset ride along when they differ from the site's defaults (1,000 rows from 0), so a
    10,000-row pull opens as the same page of rows.
    """
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
    if limit and limit > 1000:
        pairs.append(("limit", str(limit)))
    if offset:
        pairs.append(("offset", str(offset)))
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
        "match_ids": "Matches", "exclude_batters": "Excluding batters", "exclude_bowlers": "Excluding bowlers",
        "dimension_filters": "Where",
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
    if params.get("metrics_perspective"):
        chips.append(f"{params['metrics_perspective'].capitalize()} view")
    chips.append("All formats" if fmt == "ALL" else fmt)
    return chips


def _title(params: Dict[str, Any], group_by: List[str]) -> str:
    who = params.get("batters") or params.get("bowlers") or params.get("players") or params.get("teams") \
        or params.get("batting_teams") or params.get("bowling_teams")
    subject = ", ".join(who[:3]) + (" +" if len(who) > 3 else "") if who else (params.get("venue") or "All matches")
    if group_by:
        return f"{subject} · by {', '.join(g.replace('_', ' ') for g in group_by)}"
    return subject


def perspective_label(perspective: Optional[str]) -> Optional[str]:
    """How to read the sign of Impact/RAA/WAA/WPA."""
    if perspective == "bowling":
        return "bowling view: + = good for bowler"
    if perspective == "batting":
        return "batting view: + = good for batter"
    return None


def _header(column: str, perspective: Optional[str]) -> str:
    label = perspective_label(perspective)
    return f"{column} ({label})" if label and column in _SIGNED_METRICS else column


def _markdown_table(columns: List[str], rows: List[Dict[str, Any]], max_rows: int = TEXT_TABLE_ROWS,
                    must_show: Optional[List[str]] = None, perspective: Optional[str] = None) -> str:
    # The first ten columns, plus whatever the rows were ranked or charted by -- otherwise a
    # "ranked by wpa" table could hide the very numbers it was ranked on.
    extra = []
    # The Primer metrics sit past the tenth column; show them whenever the rows carry them.
    if any(r.get("impact") is not None for r in rows[:max_rows]):
        must_show = list(must_show or []) + ["impact", "raa", "waa", "wpa"]
    for c in must_show or []:
        if c and c in columns and c not in columns[:10] and c not in extra:
            extra.append(c)
    shown = columns[:10] + extra
    lines = ["| " + " | ".join(_header(c, perspective) for c in shown) + " |", "|" + "---|" * len(shown)]
    for row in rows[:max_rows]:
        lines.append("| " + " | ".join("" if row.get(c) is None else str(row.get(c)) for c in shown) + " |")
    if len(rows) > max_rows:
        lines.append(f"| … {len(rows) - max_rows} more rows (all of them are in the full result below and in the widget) |")
    return "\n".join(lines)


def rows_as_csv(columns: List[str], rows: List[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow(["" if row.get(c) is None else row.get(c) for c in columns])
    return buf.getvalue()


# --------------------------------------------------------------------------------------------
# Canonical player names
# --------------------------------------------------------------------------------------------

_ADDITIVE = ("balls", "innings_count", "runs", "wickets", "dots", "boundaries", "fours", "sixes",
             "metric_balls", "impact", "raa", "waa", "wpa")


def _alias_map(db: Any) -> Dict[str, str]:
    """lower(spelling) -> canonical name (player_alias_map: unambiguous spellings only)."""
    try:
        return {k: v for k, v in db.execute(text("SELECT name_key, canonical_name FROM player_alias_map"))}
    except Exception as exc:  # pragma: no cover - the view exists in every environment
        logger.warning("alias map unavailable: %r", exc)
        return {}


def canonical_name(name: Any, alias_map: Dict[str, str]) -> Any:
    if not isinstance(name, str) or not name:
        return name
    return alias_map.get(name.lower(), name)


def canonicalize_rows(rows: List[Dict[str, Any]], group_by: List[str], alias_map: Dict[str, str]) -> tuple:
    """
    One name per player in every output row, whatever the grouping. The engine already groups on
    canonical names; this is the backstop for spellings it keys exactly (case variants, legacy
    rows). Rows that collapse onto one key are combined: counts and Primer totals add, rates are
    recomputed. Returns (rows, number of rows merged away).
    """
    if not alias_map or not rows:
        return rows, 0
    for row in rows:
        for col in _PLAYER_COLUMNS:
            if col in row:
                row[col] = canonical_name(row[col], alias_map)
        if row.get("partnership") and " & " in str(row["partnership"]):
            a, b = (canonical_name(x.strip(), alias_map) for x in str(row["partnership"]).split(" & ", 1))
            row["partnership"] = " & ".join(sorted([a, b]))
    keyed: Dict[tuple, Dict[str, Any]] = {}
    merged = 0
    for row in rows:
        key = tuple(str(row.get(g)) for g in group_by)
        if key not in keyed:
            keyed[key] = row
            continue
        merged += 1
        into = keyed[key]
        for f in _ADDITIVE:
            if isinstance(row.get(f), (int, float, Decimal)) or isinstance(into.get(f), (int, float, Decimal)):
                into[f] = float(into.get(f) or 0) + float(row.get(f) or 0)
        balls, runs, wkts = float(into.get("balls") or 0), float(into.get("runs") or 0), float(into.get("wickets") or 0)
        mb = float(into.get("metric_balls") or 0)
        if "strike_rate" in into:
            into["strike_rate"] = round(runs * 100 / balls, 2) if balls else 0
        if "average" in into:
            into["average"] = round(runs / wkts, 2) if wkts else None
        if "balls_per_dismissal" in into:
            into["balls_per_dismissal"] = round(balls / wkts, 2) if wkts else None
        for f, num in (("dot_percentage", "dots"), ("boundary_percentage", "boundaries")):
            if f in into:
                into[f] = round(float(into.get(num) or 0) * 100 / balls, 2) if balls else 0
        for f in ("impact", "raa", "waa"):
            if f"{f}_per_100" in into:
                into[f"{f}_per_100"] = round(float(into.get(f) or 0) * 100 / mb, 2) if mb else None
    return list(keyed.values()), merged


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
   The text shows the first 25 rows; every row up to `limit` (max 10,000, page with `offset`)
   follows as CSV (or JSON via result_format). Do arithmetic and statistics on that full block.
   Player names are canonical in every output (one name per player); any spelling works as input.
   Filters: match_ids, exclude_batters, exclude_bowlers. Match-context dimensions, usable in
   group_by and as dimension_filters 'name:op:value': bowler_over_number (his 1st/2nd/... over),
   bowler_entry_over, spell_number, bowler_first_over_runs(_bucket '0-6'/'7-9'/'10+'),
   prev_over_runs(_bucket), prev_over_raa(_bucket), next_over_runs(_bucket) (a placebo),
   batter_balls_faced(_bucket),
   impact_player_era ('pre-2023'/'2023+'), season ('2024' or '2024/25' for BBL-style seasons).
   Example, "does a bad first over hurt him for the rest of the match": bowlers=[X],
   group_by=['match_id','bowler_first_over_runs_bucket'], dimension_filters=['bowler_over_number:gte:2'],
   metrics_perspective='bowling'.
   query_mode='team_innings' gives one record per team innings (total, wickets, run rate, phase run
   rates, pct_200_plus/pct_250_plus, win %): "how often do IPL teams pass 200" = leagues=['IPL'],
   group_by=['season'], dimension_filters=['full_length:eq:1'].
Overs are 0-indexed (over_min=0, over_max=5 is the powerplay). Default format is ALL, which
mixes T20 and ODI: ALWAYS pin format="ODI" for ODI questions and format="T20" for T20 ones.
ODIs are all internationals -- for format="ODI" leave include_international, top_teams and
leagues unset (a T20 league filter on an ODI query returns nothing). The result renders as an interactive table/chart and
includes a link to open the same query on the Hindsight website — mention it to the user.
4. preview_match gives a fixture preview (venue record, leaders, head-to-head, form, standout
   batter-vs-bowler matchups) for two teams at a venue in T20 or ODI — use it for "preview X v Y
   at Z" questions, then drill in with query_cricket_data.
5. Contextual metrics ARE available (men's T20 from 2015, not The Hundred), computed ball by ball
   with Himanish Ganjoo's T20 Primer method and returned on every query_cricket_data row:
   impact (runs added to the team's projected total; impact_per_100, impact_per_innings),
   raa / waa (runs and wickets above average for the game state; *_per_100), wpa (win
   probability added, 1.0 = one match won) and avg_leverage. Their sign is the
   metrics_perspective: by default the batting side, or the bowling side when grouped by bowler
   (and not batter). For any bowler question grouped by something else (match, phase, bucket),
   pass metrics_perspective='bowling'. Every result states its perspective, e.g. "raa (bowling
   view: + = good for bowler)". For "most valuable / most impactful / match-winning" questions,
   pin format="T20" and sort_by="impact" or "wpa" -- do not approximate them.
6. preview_match also returns "Hindsight's take": the site's own preview facts (incl. par and
   each side's Impact leaders for T20), ranked by importance. Quote these rather than rederiving.
7. match_recap explains how a finished men's T20 was won (biggest Impact and WPA performances,
   the biggest win-probability swing, first innings vs par). Use it for "how did X beat Y" or
   "who won the game for X" questions.
8. player_profile gives what stands out about a player (Impact/RAA/WPA by season with rank,
   style, matchups) and Hindsight's fact-checked Player DNA. Use it for "tell me about X" or
   "how good has X been" questions before drilling in with query_cricket_data.
9. player_advanced returns a bowler's Advanced Analytics as JSON: pressure split by the previous
   over, spell shape, entry point, first/last-ball boundary rates, rolling form. Economy there is
   unadjusted for game state; prefer the raa_per_over / waa_per_over next to it.
"""

apps = Apps()


def structure_query_result(
    result: Dict[str, Any], params: Dict[str, Any], group_by: List[str], *, query_mode: str = "delivery",
    format: str = "ALL", gender: str = "male", batters: Optional[List[str]] = None,
    bowlers: Optional[List[str]] = None, sort_by: Optional[str] = None, sort_descending: bool = True,
    limit: int = 25, chart: str = "auto", chart_metric: Optional[str] = None,
    scatter_x: Optional[str] = None, scatter_y: Optional[str] = None, offset: int = 0,
    paged_by_engine: bool = False, min_coverage: Optional[float] = None,
) -> Dict[str, Any]:
    """Shape a query-builder result for display: ordered columns, chart spec, title, link.

    Shared by the connector (query_cricket_data) and chart snapshots/embeds, so the widget renders
    both the same way. Rows are sorted here when sort_by is given, then the page
    [offset, offset + limit) is kept -- unless the engine already applied the offset
    (paged_by_engine), in which case only `limit` applies.
    """
    raw_rows = result.get("data") or []
    # A bowling question: bowlers are filtered, or rows are split by bowler, and no batter is picked.
    bowler_centric = (bool(bowlers) or "bowler" in group_by) and not batters
    metrics_perspective = next((r.get("metrics_perspective") for r in raw_rows if r.get("metric_balls")), None)
    rows = []
    for raw in raw_rows:
        row = {k: _normalise_value(v) for k, v in raw.items() if k not in _ROW_INTERNAL}
        metric_balls = raw.get("metric_balls")
        if metric_balls:
            # Per over (six balls with metrics), the unit bowling questions are usually asked in.
            for f in ("raa", "waa"):
                if raw.get(f) is not None:
                    row[f"{f}_per_over"] = round(float(raw[f]) * 6.0 / float(metric_balls), 3)
            if raw.get("wpa") is not None and raw.get("innings_count"):
                row["wpa_per_innings"] = round(float(raw["wpa"]) / float(raw["innings_count"]), 4)
        rows.append(row)
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
    elif group_by and (group_by[0] in _SEQUENTIAL_KEYS or group_by[0] == "phase" or group_by[0] in _BUCKET_ORDER):
        rows.sort(key=lambda r: _sequence_key(group_by[0], r.get(group_by[0])))
    # Ranked by a tagged metric (control %): rows with too little tagged data rank last, out of the
    # count (services/coverage.py). Default floor 90%; min_coverage=0 turns it off.
    from services.coverage import DEFAULT_MIN_COVERAGE, rank_with_coverage
    rows, coverage = rank_with_coverage(rows, sort_by, DEFAULT_MIN_COVERAGE if min_coverage is None else min_coverage)
    total_rows = meta.get("total_groups") or meta.get("total_rows") or len(rows)
    start = 0 if paged_by_engine else offset
    rows = rows[start:start + limit]

    columns = _order_columns(rows, group_by)
    metric_columns = [
        c for c in columns
        if c not in group_by and any(isinstance(r.get(c), (int, float)) and not isinstance(r.get(c), bool) for r in rows)
    ]
    default_metric = chart_metric or sort_by or ("economy" if bowler_centric and "economy" in metric_columns else None)
    chart_spec = _choose_chart(chart, group_by, rows, metric_columns, query_mode, default_metric, scatter_x, scatter_y)
    url = _hindsight_url(params, group_by, format, gender, limit=limit, offset=offset)
    warnings = [w for w in (meta.get("warnings") or []) if w]
    next_offset = offset + len(rows) if offset + len(rows) < total_rows else None

    structured = {
        "title": _title(params, group_by),
        "subtitle": (f"{len(rows)} of {total_rows} rows" if not offset
                     else f"rows {offset + 1}–{offset + len(rows)} of {total_rows}")
                    + (f" · ranked by {sort_by}" if sort_by else ""),
        "filter_chips": _filter_chips(params, format),
        "group_by": group_by,
        "query_mode": query_mode,
        "columns": columns,
        "metric_columns": metric_columns,
        "rows": rows,
        "total_rows": total_rows,
        "offset": offset,
        "next_offset": next_offset,
        "chart": chart_spec,
        "hindsight_url": url,
        "warnings": warnings,
        "note": " ".join(warnings) if warnings else None,
        "metrics_perspective": metrics_perspective,
        "metrics_perspective_label": perspective_label(metrics_perspective),
        "coverage": coverage,
        "coverage_tags": (meta.get("coverage") or {}).get("tags") or [],
        "definitions": meta.get("definitions"),
    }

    return structured


@apps.tool(
    resource_uri=UI_URI,
    name="query_cricket_data",
    title="Query Hindsight cricket data",
    description=(
        "Run a Hindsight query-builder query over ball-by-ball cricket data and return aggregated "
        "rows (runs, balls, strike rate, average, dot %, boundary %, wickets, economy...) plus an "
        "interactive chart/table and a link to open it on the website. The text shows a short summary "
        "and the first 25 rows; EVERY row up to `limit` (max 10,000; page with `offset`) follows as "
        "CSV (or JSON with result_format='json') -- compute from that, not from the preview table. "
        "Use find_entities for exact names and get_query_options for filter values first. Men's T20 "
        "rows also carry contextual metrics from Ganjoo's T20 Primer: impact (runs added to the "
        "team's projected total), raa/waa (runs and wickets above average for the game state; "
        "*_per_100, *_per_over), wpa (win probability added) and avg_leverage. Their sign follows "
        "metrics_perspective: 'bowling' (+ = good for the bowler) or 'batting' (+ = good for the "
        "batter); by default bowling when grouped by bowler (and not batter), batting otherwise -- "
        "set it explicitly for bowler questions grouped by anything else. The perspective is printed "
        "with every result. Match-context dimensions (group_by and dimension_filters): "
        "bowler_over_number, bowler_entry_over, spell_number, bowler_first_over_runs(_bucket), "
        "prev_over_runs(_bucket), prev_over_raa(_bucket), next_over_runs(_bucket), batter_balls_faced(_bucket), match_date, "
        "impact_player_era, season. query_mode='team_innings' returns one record per team innings "
        "(total, wickets, run rate, phase run rates, 200+/250+ rates, result)."
    ),
    annotations=READ_ONLY,
)
def query_cricket_data(
    ctx: Context,
    group_by: Annotated[List[GroupByColumn], Field(min_length=1, description="Columns to aggregate by (required), e.g. ['batter'], ['bowl_kind','year'], ['phase'], ['match_id','bowler_first_over_runs_bucket']. team_innings mode: match_id, innings, competition, year, season, impact_player_era, venue, country, batting_team, bowling_team, match_outcome, toss_decision, format, full_length, total_bucket.")],
    batters: Annotated[List[str], Field(description="Batter names from find_entities, e.g. ['V Kohli']; any spelling resolves.")] = [],
    bowlers: Annotated[List[str], Field(description="Bowler names from find_entities; any spelling resolves.")] = [],
    players: Annotated[List[str], Field(description="Players matched as batter OR bowler.")] = [],
    exclude_batters: Annotated[List[str], Field(description="Drop balls faced by these batters (every spelling).")] = [],
    exclude_bowlers: Annotated[List[str], Field(description="Drop balls bowled by these bowlers (every spelling), e.g. the subject when comparing his team-mates.")] = [],
    match_ids: Annotated[List[str], Field(description="Only these matches (ids as returned when grouping by match_id).")] = [],
    batting_teams: Annotated[List[str], Field(description="Team batting, exact names.")] = [],
    bowling_teams: Annotated[List[str], Field(description="Team bowling, exact names.")] = [],
    teams: Annotated[List[str], Field(description="Team either batting or bowling.")] = [],
    venue: Annotated[Optional[str], Field(description="Exact venue name from find_entities.")] = None,
    leagues: Annotated[List[str], Field(description="T20 leagues, e.g. ['IPL','BBL'] (abbreviations work). Leave empty for ODIs, which are all internationals.")] = [],
    include_international: Annotated[bool, Field(description="T20 only: add T20Is (national sides) to league data. Not needed for ODIs -- every ODI is included automatically.")] = False,
    top_teams: Annotated[Optional[int], Field(ge=1, le=30, description="With include_international (T20), only T20Is between the top N national teams.")] = None,
    start_date: Annotated[Optional[date], Field(description="YYYY-MM-DD inclusive.")] = None,
    end_date: Annotated[Optional[date], Field(description="YYYY-MM-DD inclusive.")] = None,
    format: Annotated[Literal["T20", "ODI", "ALL"], Field(description="Cricket format. Set format='ODI' for any ODI question and format='T20' for T20 ones; ALL mixes T20 and ODI rows (add 'format' to group_by if you really want both).")] = "ALL",
    gender: Annotated[Literal["male", "female"], Field(description="Men's or women's cricket.")] = "male",
    query_mode: Annotated[Literal["delivery", "batting_stats", "bowling_stats", "team_innings"], Field(description="delivery = ball-by-ball aggregates (supports line/length/shot filters and the match-context dimensions); batting_stats / bowling_stats = per-innings scorecard aggregates; team_innings = one record per team innings (total, wickets, run rate, runs by phase, result) aggregated by group_by -- e.g. group_by=['season'] gives pct_200_plus / pct_250_plus per season.")] = "delivery",
    innings: Annotated[Optional[int], Field(ge=1, le=4, description="1 = batting first, 2 = chasing.")] = None,
    over_min: Annotated[Optional[int], Field(ge=0, description="First over, 0-indexed (0 = first over).")] = None,
    over_max: Annotated[Optional[int], Field(ge=0, description="Last over, 0-indexed (5 = end of the T20 powerplay, 19 = last T20 over).")] = None,
    bat_hand: Annotated[Optional[Literal["LHB", "RHB"]], Field(description="Batter's hand.")] = None,
    bowl_kind: Annotated[List[str], Field(description="Values from get_query_options, e.g. ['pace bowler'] or ['spin bowler'].")] = [],
    bowl_style: Annotated[List[str], Field(description="Values from get_query_options, e.g. ['LAO','SLA'] for left-arm spin.")] = [],
    line: Annotated[List[str], Field(description="Values from get_query_options.")] = [],
    length: Annotated[List[str], Field(description="Values from get_query_options.")] = [],
    shot: Annotated[List[str], Field(description="Values from get_query_options. The feed changed shot labels around 2018 (e.g. PULL_HOOK_ON_BACK_FOOT before, PULL/HOOK after): for career questions use shot_family.")] = [],
    shot_family: Annotated[List[str], Field(description="Shot families spanning both tagging schemes: PULL_HOOK, CUT, DRIVE, FLICK_GLANCE, SWEEP, REVERSE, RAMP_SCOOP, SLOG, WORK_PUSH, DEFENCE, LEAVE. Also a group_by column (shot_family).")] = [],
    partnership_players: Annotated[List[str], Field(description="With group_by=['partnership']: partnerships involving these players, counting both batters' balls. A batters filter is read this way too when grouping by partnership.")] = [],
    min_coverage: Annotated[Optional[float], Field(ge=0, le=100, description="When sort_by is a tagged metric (control_percentage): rows whose balls are less than this % tagged rank last and are flagged coverage_excluded. Default 90; 0 turns it off. Rows carry <tag>_coverage_pct.")] = None,
    control: Annotated[Optional[Literal[0, 1]], Field(description="1 = controlled shots, 0 = uncontrolled.")] = None,
    wagon_zone: Annotated[List[int], Field(description="Wagon-wheel zones 0-8.")] = [],
    dismissal: Annotated[List[str], Field(description="Dismissal types, e.g. ['caught','bowled','lbw'].")] = [],
    match_outcome: Annotated[List[Literal["win", "loss", "tie", "no_result"]], Field(description="Batting side's match result.")] = [],
    is_chase: Annotated[Optional[bool], Field(description="True = chasing innings only, False = setting only.")] = None,
    chase_outcome: Annotated[List[Literal["win", "loss", "tie", "no_result"]], Field(description="Result of the chase (chasing side's view).")] = [],
    toss_decision: Annotated[List[Literal["bat", "field"]], Field(description="Toss decision.")] = [],
    dimension_filters: Annotated[List[str], Field(description="Filters on match-context dimensions, each 'name:op:value' (op eq/ne/gt/gte/lt/lte/in; 'in' values separated by '|'). E.g. ['bowler_over_number:gte:2'] = the bowler's overs after his first; ['prev_over_runs_bucket:in:10+']; ['batter_balls_faced:gte:30']; ['impact_player_era:eq:2023+']. team_innings mode: total, wickets, balls, full_length, year, season, impact_player_era, match_outcome, total_bucket (e.g. ['full_length:eq:1']). Bucket labels: '0-6','7-9','10+'; RAA buckets 'below -2','-2 to +2','above +2'.")] = [],
    metrics_perspective: Annotated[Optional[Literal["bowling", "batting"]], Field(description="Sign of impact/raa/waa/wpa. 'bowling' = + is good for the bowler (and runs exclude byes/leg-byes); 'batting' = + is good for the batter. Omit to infer: bowling when grouped by bowler and not batter, batting otherwise. Set 'bowling' for any bowler question not grouped by bowler.")] = None,
    min_balls: Annotated[Optional[int], Field(ge=1, description="Drop groups with fewer balls (use for leaderboards, e.g. 120).")] = None,
    min_runs: Annotated[Optional[int], Field(ge=0, description="Drop groups with fewer runs.")] = None,
    min_wickets: Annotated[Optional[int], Field(ge=0, description="Drop groups with fewer wickets.")] = None,
    having: Annotated[List[str], Field(description="Thresholds on computed metrics, each 'metric:op:value' with op gte/lte/gt/lt; metrics average, strike_rate, balls_per_dismissal, dot_percentage, boundary_percentage, control_percentage, impact, impact_per_100, impact_per_innings, raa(_per_100), waa(_per_100), wpa, avg_leverage (Impact-family: men's T20 only). E.g. ['average:gte:50','strike_rate:gte:100'] for '50+ average, 100+ SR'. Applied before sorting and the row limit.")] = [],
    sort_by: Annotated[Optional[str], Field(description="Column to rank by, e.g. 'strike_rate', 'runs', 'economy', 'wickets', 'raa_per_over', 'pct_200_plus'.")] = None,
    sort_descending: Annotated[bool, Field(description="Highest first (set False for economy-style metrics where lower is better).")] = True,
    limit: Annotated[int, Field(ge=1, le=MAX_ROWS, description=f"Rows to return, all of them in the machine-readable result (max {MAX_ROWS:,}, same as the website).")] = DEFAULT_ROWS,
    offset: Annotated[int, Field(ge=0, description="Rows to skip, for paging; the result says next_offset when more rows exist.")] = 0,
    result_format: Annotated[Literal["csv", "json"], Field(description="Format of the full result block: csv (compact) or json (list of row objects).")] = "csv",
    chart: Annotated[Literal["auto", "table", "bar", "line", "scatter"], Field(description="Visual for the widget. auto picks line for year/over, bar for one categorical group.")] = "auto",
    chart_metric: Annotated[Optional[str], Field(description="Metric to plot for bar/line, e.g. 'strike_rate'.")] = None,
    scatter_x: Annotated[Optional[str], Field(description="Scatter x metric, e.g. 'strike_rate'.")] = None,
    scatter_y: Annotated[Optional[str], Field(description="Scatter y metric, e.g. 'average'.")] = None,
) -> CallToolResult:
    started = time.monotonic()
    if format == "ODI":
        # Every ODI is between national sides: the T20 "add internationals" switch and its
        # top-teams cut do not apply, and the website ignores them for ODIs too.
        include_international, top_teams = False, None
    params: Dict[str, Any] = {
        "venue": venue, "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None, "leagues": leagues, "teams": teams,
        "batting_teams": batting_teams, "bowling_teams": bowling_teams, "players": players,
        "batters": batters, "bowlers": bowlers, "bat_hand": bat_hand, "bowl_style": bowl_style,
        "bowl_kind": bowl_kind, "line": line, "length": length, "shot": shot, "shot_family": shot_family,
        "partnership_players": partnership_players, "control": control,
        "wagon_zone": wagon_zone, "dismissal": dismissal, "innings": innings, "over_min": over_min,
        "over_max": over_max, "match_outcome": match_outcome, "is_chase": is_chase,
        "chase_outcome": chase_outcome, "toss_decision": toss_decision, "min_balls": min_balls,
        "min_runs": min_runs, "min_wickets": min_wickets, "include_international": include_international,
        "top_teams": top_teams, "query_mode": query_mode, "having": having, "match_ids": match_ids,
        "exclude_batters": exclude_batters, "exclude_bowlers": exclude_bowlers,
        "dimension_filters": dimension_filters, "metrics_perspective": metrics_perspective,
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

    # With sort_by the connector ranks the whole result itself, so it fetches every group (up to
    # the cap) from row 0 and pages after sorting; otherwise the engine pages.
    sorting = bool(sort_by)
    fetch_limit, fetch_offset = (SORT_FETCH_LIMIT, 0) if sorting else (limit, offset)
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
                min_balls=min_balls, min_runs=min_runs, min_wickets=min_wickets, having=having, limit=fetch_limit,
                offset=fetch_offset, include_international=include_international, top_teams=top_teams,
                query_mode=query_mode, fmt=format, gender=gender, match_ids=match_ids,
                exclude_batters=exclude_batters, exclude_bowlers=exclude_bowlers,
                dimension_filters=dimension_filters, metrics_perspective=metrics_perspective,
                shot_family=shot_family, partnership_players=partnership_players,
            )
            alias_map = _alias_map(db)
    except QueryValidationError as exc:
        _log_call("query_cricket_data", ctx, params, started, "invalid")
        return _error(str(exc))
    except Exception as exc:
        _log_call("query_cricket_data", ctx, params, started, "error")
        logger.warning("mcp query failed: %r", exc)
        return _error(_user_message(exc, "That query could not be run."))

    # Titles, chips and the link name players canonically too, whatever spelling was asked for.
    for key in ("batters", "bowlers", "players", "exclude_batters", "exclude_bowlers"):
        if params.get(key):
            params[key] = list(dict.fromkeys(canonical_name(n, alias_map) for n in params[key]))
    result = dict(result)
    result["data"], merged = canonicalize_rows([dict(r) for r in result.get("data") or []], group_by, alias_map)
    structured = structure_query_result(
        result, params, group_by, query_mode=query_mode, format=format, gender=gender, batters=batters,
        bowlers=bowlers, sort_by=sort_by, sort_descending=sort_descending, limit=limit, chart=chart,
        chart_metric=chart_metric, scatter_x=scatter_x, scatter_y=scatter_y, offset=offset,
        paged_by_engine=not sorting, min_coverage=min_coverage,
    )
    rows, columns, url, warnings = structured["rows"], structured["columns"], structured["hindsight_url"], structured["warnings"]
    total_rows, chart_spec = structured["total_rows"], structured["chart"]
    perspective = structured["metrics_perspective"]
    if merged:
        warnings.append(f"{merged} rows under other spellings of the same player were combined into one name each.")
    if sorting and total_rows > SORT_FETCH_LIMIT:
        warnings.append(f"Ranked within the {SORT_FETCH_LIMIT:,} largest of {total_rows:,} groups; add filters for an exact ranking.")

    content = []
    if not rows:
        summary = "No rows match these filters. Check exact names with find_entities, or loosen filters (dates, min_balls, competitions)."
    else:
        span = (f"{len(rows)} of {total_rows} rows" if not offset
                else f"rows {offset + 1}–{offset + len(rows)} of {total_rows}")
        perspective_line = (
            f"Metric perspective: {perspective} view — impact/raa/waa/wpa are + when good for the "
            f"{'bowler' if perspective == 'bowling' else 'batter'}."
            if perspective else "Metric perspective: none (no T20 Primer metrics in these rows)."
        )
        summary = (
            f"{structured['title']} — {span}" + (f", ranked by {sort_by}" if sort_by else "") + ".\n"
            + perspective_line + "\n\n"
            + _markdown_table(columns, rows, must_show=[sort_by, chart_spec.get("metric")], perspective=perspective)
            + (f"\n\nMore rows: call again with offset={structured['next_offset']}." if structured["next_offset"] else "")
            + f"\n\nOpen this query on Hindsight: {url}"
        )
        if warnings:
            summary += "\n\nNotes: " + " ".join(warnings)
    content.append(TextContent(type="text", text=summary))
    if rows:
        if result_format == "json":
            body = json.dumps({"metrics_perspective": perspective, "columns": columns, "rows": rows}, default=str)
            content.append(TextContent(type="text", text=f"Full result as JSON ({len(rows)} rows):\n{body}"))
        else:
            header = f"Full result as CSV ({len(rows)} rows" + (
                f"; impact/raa/waa/wpa columns are the {perspective_label(perspective)}" if perspective else "") + "):"
            content.append(TextContent(type="text", text=f"{header}\n```csv\n{rows_as_csv(columns, rows)}```"))

    _log_call("query_cricket_data", ctx, params, started, "ok")
    return CallToolResult(content=content, structured_content=structured)


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
    description="Query ball-by-ball cricket data from Hindsight (hindsightcricket.com).",
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
        # Metric columns query_cricket_data returns, so a model knows they exist before asking.
        "metrics": {
            "basic": ["balls", "runs", "wickets", "average", "strike_rate", "economy", "dot_percentage",
                      "boundary_percentage", "control_percentage", "fours", "sixes", "percent_balls"],
            "contextual_t20": {
                "impact": "runs added to the team's projected total (DL-based), also impact_per_100 / impact_per_innings",
                "raa": "runs above average for the game state, also raa_per_100",
                "waa": "wickets above average for the game state, also waa_per_100",
                "wpa": "win probability added; 1.0 = one match won",
                "avg_leverage": "average stakes per ball (win-probability gap between a six and a wicket)",
                "coverage": "men's T20 from 2015, not The Hundred; batting side, or bowling side when grouped by bowler",
            },
        },
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
            # The site's preview narrative (code-written facts ranked by Jev), best-effort.
            try:
                from routers.match_preview import get_match_preview
                site_preview = get_match_preview(
                    venue=venue, team1_id=team1, team2_id=team2, start_date=start, end_date=end,
                    include_international=include_international, top_teams=top_teams, day_or_night=None,
                    format=format, gender="male", debug=False, db=db,
                )
            except Exception as preview_exc:
                logger.warning("mcp preview narrative failed: %r", preview_exc)
                site_preview = {}
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
        "hindsight_take": {
            "headline": (site_preview or {}).get("headline"),
            "sections": [{"title": sec.get("title"), "bullets": sec.get("bullets")} for sec in (site_preview or {}).get("sections") or []],
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
    take = structured["hindsight_take"]
    if take["sections"]:
        lines += ["", "**Hindsight's take** (facts from Hindsight's numbers, including T20 Impact/RAA/WPA; ranked by importance):"]
        if take["headline"]:
            lines.append(f"Headline: {take['headline']}")
        for sec in take["sections"]:
            lines.append(f"{sec['title']}: " + " ".join(sec["bullets"] or []))
    lines += ["", f"Full preview on Hindsight: {link}"]

    _log_call("preview_match", ctx, args, started, "ok")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))], structured_content=structured)


@mcp.tool(
    name="match_recap",
    title="Recap a finished match",
    description=(
        "How a finished men's T20 was won, from Hindsight's T20 Primer metrics: the performances that "
        "added or saved the most runs (Impact) and win probability (WPA), the biggest win-probability "
        "swing, the first innings against par, and comebacks. Give the two teams (exact names from "
        "find_entities) and optionally the date; without a date, their most recent meeting."
    ),
    annotations=READ_ONLY,
)
def match_recap(
    ctx: Context,
    team1: Annotated[str, Field(description="One team, exact name, e.g. 'India' or 'Mumbai Indians'.")],
    team2: Annotated[str, Field(description="The other team, exact name.")],
    match_date: Annotated[Optional[date], Field(description="Match date (YYYY-MM-DD); default: their latest T20 meeting.")] = None,
) -> CallToolResult:
    from sqlalchemy import text as sql_text
    from services.match_recap import build_recap
    from services.match_scorecard import get_match_scorecard_service
    from services.matchups import get_all_team_name_variations

    started = time.monotonic()
    args = {"team1": team1, "team2": team2, "match_date": str(match_date) if match_date else None}
    if not _budget.try_acquire():
        return _BUSY
    try:
        with _read_only_session() as db:
            row = db.execute(sql_text("""
                SELECT id, date FROM matches
                WHERE format = 'T20' AND gender = 'male'
                  AND ((team1 = ANY(:a) AND team2 = ANY(:b)) OR (team1 = ANY(:b) AND team2 = ANY(:a)))
                  AND (CAST(:d AS date) IS NULL OR date = :d)
                ORDER BY date DESC LIMIT 1
            """), {"a": get_all_team_name_variations(team1), "b": get_all_team_name_variations(team2), "d": match_date}).first()
            if not row:
                _log_call("match_recap", ctx, args, started, "not_found")
                return _error(f"No men's T20 between {team1} and {team2}" + (f" on {match_date}" if match_date else "") + " in Hindsight.")
            scorecard = get_match_scorecard_service(match_id=str(row[0]), min_balls=6, db=db)
            recap = build_recap(scorecard, db) if (scorecard.get("summary") or {}).get("primer") else {"available": False}
    except Exception as exc:
        _log_call("match_recap", ctx, args, started, "error")
        logger.warning("mcp recap failed: %r", exc)
        return _error(_user_message(exc, "That recap could not be built."))

    match = scorecard.get("match") or {}
    link = f"{WEB_URL}/scorecard/{match.get('id')}"
    structured = {"match_id": match.get("id"), "date": str(match.get("date")), "result": match.get("result_text"),
                  "recap": recap, "hindsight_url": link}
    lines = [f"**{match.get('team1')} v {match.get('team2')}**, {match.get('competition')} {match.get('date')}: {match.get('result_text')}", ""]
    if recap.get("available"):
        lines.append(recap["headline"])
        lines += [f"- {b}" for b in recap["bullets"]]
    else:
        lines.append("No ball-by-ball Impact/WPA for this match, so no recap; the scorecard is linked below.")
    lines += ["", f"Scorecard on Hindsight: {link}"]
    _log_call("match_recap", ctx, args, started, "ok")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))], structured_content=structured)


@mcp.tool(
    name="player_profile",
    title="What stands out about a player",
    description=(
        "A player's standout facts for men's T20: their Impact, RAA and WPA by season with rank "
        "among peers, style (strike rate / economy, phase), pace-v-spin and best/worst matchups, "
        "ranked by how distinctive they are, plus Hindsight's fact-checked 'Player DNA' summary. "
        "role is 'batter' or 'bowler'. Use find_entities for the exact player name."
    ),
    annotations=READ_ONLY,
)
def player_profile(
    ctx: Context,
    player: Annotated[str, Field(description="Exact player name from find_entities, e.g. 'V Kohli'.")],
    role: Annotated[Literal["batter", "bowler"], Field(description="Batting or bowling profile.")] = "batter",
    start_date: Annotated[Optional[date], Field(description="Window start for the style facts (default: 1 January, two years back).")] = None,
    end_date: Annotated[Optional[date], Field(description="Window end (default: today).")] = None,
) -> CallToolResult:
    from routers.player_summary import get_batter_summary, get_bowler_summary, player_standouts

    started = time.monotonic()
    args = {"player": player, "role": role}
    if not _budget.try_acquire():
        return _BUSY
    start = start_date or date(date.today().year - 2, 1, 1)
    filters = dict(start_date=start, end_date=end_date, leagues=[], include_international=True, top_teams=None, venue=None)
    try:
        with _read_only_session() as db:
            stand = player_standouts(role, player, db, **filters)
            summary_fn = get_batter_summary if role == "batter" else get_bowler_summary
            dna = summary_fn(player_name=player, include_patterns=False, db=db, **filters)
    except Exception as exc:
        _log_call("player_profile", ctx, args, started, "error")
        logger.warning("mcp player profile failed: %r", exc)
        return _error(_user_message(exc, "That player profile could not be built."))

    tab = "batting" if role == "batter" else "bowling"
    link = f"{WEB_URL}/player?" + urlencode([("name", player), ("tab", tab), ("autoload", "true")])
    structured = {"player": player, "role": role, "window": {"start_date": start.isoformat(), "end_date": str(end_date) if end_date else None},
                  "standouts": stand, "player_dna": getattr(dna, "summary", None), "hindsight_url": link}
    lines = [f"**{player}** ({tab}, men's T20)", ""]
    if stand.get("available"):
        lines += ["What stands out:", f"- {stand['headline']}"] + [f"- {b}" for b in stand["bullets"]]
    if structured["player_dna"]:
        lines += ["", f"Player DNA (since {start.isoformat()}, fact-checked):", structured["player_dna"]]
    if len(lines) == 2:
        lines.append("No T20 data for this player in the window.")
    lines += ["", f"Profile on Hindsight: {link}"]
    _log_call("player_profile", ctx, args, started, "ok")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))], structured_content=structured)


@mcp.tool(
    name="player_advanced",
    title="A bowler's advanced analytics",
    description=(
        "The player profile's Advanced Analytics as JSON (men's T20 bowling): pressure split (how the "
        "bowler does after a high- / neutral- / low-scoring previous over from the other end), spell "
        "shape (first spell vs later spells, spell lengths), entry-point stats (by the over he came "
        "on), first-/last-ball boundary rates, state on entry and rolling form. Each bucket carries "
        "economy (raw, unadjusted for game state) AND raa_per_over / waa_per_over (T20 Primer, "
        "game-state adjusted, bowling view: + = good for the bowler) -- prefer the RAA versions when "
        "comparing situations. Use find_entities for the name."
    ),
    annotations=READ_ONLY,
)
def player_advanced(
    ctx: Context,
    player: Annotated[str, Field(description="Player name from find_entities; any spelling resolves.")],
    start_date: Annotated[Optional[date], Field(description="Window start (default: all data).")] = None,
    end_date: Annotated[Optional[date], Field(description="Window end (default: today).")] = None,
    leagues: Annotated[List[str], Field(description="Competitions, e.g. ['IPL'] (empty = all).")] = [],
    include_international: Annotated[bool, Field(description="Add T20Is.")] = False,
    venue: Annotated[Optional[str], Field(description="Exact venue name.")] = None,
    pressure_threshold: Annotated[int, Field(ge=4, le=30, description="Previous-over runs at or above which an over counts as high pressure (low = threshold-4 or fewer). The profile uses 10.")] = 10,
    rolling_window: Annotated[int, Field(ge=1, le=30, description="Matches in the rolling-form window.")] = 10,
) -> CallToolResult:
    from services.bowling_context import get_bowling_context
    from services.rolling_form import get_player_rolling_form

    started = time.monotonic()
    args = {"player": player, "leagues": leagues, "include_international": include_international}
    if not _budget.try_acquire():
        return _BUSY
    try:
        with _read_only_session() as db:
            name = canonical_name(player, _alias_map(db))
            context = get_bowling_context(
                db=db, player_name=name, start_date=start_date, end_date=end_date, leagues=leagues,
                include_international=include_international, venue=venue, min_overs=10,
                pressure_threshold=pressure_threshold,
            )
            form = get_player_rolling_form(
                db=db, player_name=name, window=rolling_window, role="bowling", start_date=start_date,
                end_date=end_date, leagues=leagues, include_international=include_international, venue=venue,
            )
    except Exception as exc:
        _log_call("player_advanced", ctx, args, started, "error")
        logger.warning("mcp player advanced failed: %r", exc)
        return _error(_user_message(exc, "Those analytics could not be built."))

    link = f"{WEB_URL}/player?" + urlencode([("name", name), ("tab", "bowling"), ("autoload", "true")])
    structured = {
        "player": name, "role": "bowler", "metrics_perspective": "bowling",
        "metrics_perspective_label": perspective_label("bowling"),
        "bowling_context": json.loads(json.dumps(context, default=str)),
        "rolling_form": json.loads(json.dumps(form, default=str)),
        "hindsight_url": link,
    }
    lines = [f"**{name}** — advanced bowling analytics (men's T20). Metric perspective: bowling view, + = good for the bowler.",
             "Economy columns are raw (unadjusted for game state); raa_per_over / waa_per_over are game-state adjusted.", ""]
    total = context.get("total_overs_analyzed") or 0
    if not total:
        lines.append("No bowling in this window.")
    else:
        pressure = context.get("previous_over_pressure_stats") or {}
        lines.append(f"{total} overs analysed. Pressure (previous over ≥ {pressure.get('threshold_runs')} runs = high):")
        for key in ("high_pressure", "neutral_pressure", "low_pressure"):
            b = pressure.get(key) or {}
            lines.append(f"- {key.replace('_', ' ')}: {b.get('overs')} overs, economy {b.get('economy')} (unadjusted), "
                         f"RAA/over {b.get('raa_per_over')}, WAA/over {b.get('waa_per_over')}")
        spells = context.get("spell_stats") or {}
        for key in ("first_spell", "later_spells"):
            b = spells.get(key) or {}
            lines.append(f"- {key.replace('_', ' ')}: {b.get('overs')} overs, economy {b.get('economy')} (unadjusted), RAA/over {b.get('raa_per_over')}")
        fb = context.get("first_ball_last_ball_stats") or {}
        lines.append(f"- first-ball boundary rate {fb.get('first_ball_boundary_rate_pct')}%, last-ball {fb.get('last_ball_boundary_rate_pct')}%")
    lines += ["", "Full JSON:", json.dumps(structured["bowling_context"], default=str), "", f"Profile on Hindsight: {link}"]
    _log_call("player_advanced", ctx, args, started, "ok")
    return CallToolResult(content=[TextContent(type="text", text="\n".join(lines))], structured_content=structured)


# --------------------------------------------------------------------------------------------
# Mounting
# --------------------------------------------------------------------------------------------

def _build_mcp_routes() -> list:
    """The SDK's /mcp routes, backed by a new session manager (each can only run() once)."""
    starlette_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        # DNS-rebinding protection guards servers on localhost from hostile web pages. This is a
        # public, credential-less endpoint behind Heroku's router, so it would only reject
        # legitimate Host/Origin values (herokuapp.com, claude.ai, chatgpt.com, ...).
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    return list(starlette_app.routes)


def mount_mcp(app: Any) -> Callable[[], Any]:
    """
    Add POST/GET /mcp to a FastAPI app and return a context-manager factory that must wrap the
    app's lifespan (a mounted Starlette app's own lifespan never runs).

    The SDK's routes are added to the parent router rather than app.mount()-ed, so the endpoint is
    exactly /mcp (no /mcp/mcp, no slash redirect that some clients will not follow for POST).

    A session manager can only run() once, but an app's lifespan can run many times (every
    TestClient does). So each lifespan builds fresh routes and swaps their handlers into the
    registered ones -- in production the lifespan runs once and this is the same as before.
    """
    routes = _build_mcp_routes()
    app.router.routes.extend(routes)

    @asynccontextmanager
    async def run_mcp():
        for registered, fresh in zip(routes, _build_mcp_routes()):
            registered.app = fresh.app
        async with mcp.session_manager.run():
            yield

    return run_mcp
