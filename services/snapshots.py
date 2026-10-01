"""
Chart snapshots: frozen chart data that notes, embeds and share images render (migration 009).

A snapshot is created once and never changes, so a note or an embed shows exactly the numbers it
was published with and never re-runs a heavy query per viewer. Kinds:

  query     a query-builder result, shaped for display by the connector's structure_query_result
  win_prob  a finished match's win-probability path and Impact by over (scorecard primer data)
  recap     a finished match's "how it was won" headline and bullets (services/match_recap)

Creation de-duplicates on (kind, hash of params + data version), so the same chart asked for twice
on the same data is one snapshot.
"""
import hashlib
import json
import secrets
import string
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.query_cache import data_version, normalize

KINDS = ("query", "win_prob", "recap")
_ALPHABET = string.ascii_letters + string.digits

# Query-builder parameters a snapshot may carry (run_deliveries_query's signature), and the
# presentation options on top.
QUERY_PARAMS = {
    "venue", "start_date", "end_date", "leagues", "teams", "batting_teams", "bowling_teams", "players",
    "batters", "bowlers", "bat_hand", "bowl_style", "bowl_kind", "crease_combo", "line", "length", "shot",
    "control", "wagon_zone", "dismissal", "innings", "over_min", "over_max", "match_outcome", "is_chase",
    "chase_outcome", "toss_decision", "day_or_night", "group_by", "ball_aggregation", "min_balls",
    "max_balls", "min_runs", "max_runs", "min_wickets", "max_wickets", "include_international",
    "top_teams", "query_mode", "fmt", "gender",
}
PRESENTATION = {"sort_by", "sort_descending", "limit", "chart", "chart_metric", "scatter_x", "scatter_y",
                "highlight", "title"}
LIST_PARAMS = {"leagues", "teams", "batting_teams", "bowling_teams", "players", "batters", "bowlers",
               "bowl_style", "bowl_kind", "crease_combo", "line", "length", "shot", "wagon_zone",
               "dismissal", "match_outcome", "chase_outcome", "toss_decision", "group_by"}


class SnapshotError(ValueError):
    pass


def _new_id() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(9))


def _clean_query_params(raw: Dict[str, Any]) -> Dict[str, Any]:
    unknown = set(raw) - QUERY_PARAMS - PRESENTATION - {"format"}
    if unknown:
        raise SnapshotError(f"Unknown query parameters: {sorted(unknown)}")
    params = dict(raw)
    if "format" in params:
        params["fmt"] = params.pop("format")
    for key in LIST_PARAMS:
        if key in params and isinstance(params[key], str):
            params[key] = [params[key]]
    if not params.get("group_by"):
        raise SnapshotError("A chart needs at least one group_by column.")
    for key in ("start_date", "end_date"):
        if isinstance(params.get(key), str):
            params[key] = date.fromisoformat(params[key])
    return params


_INT_PARAMS = {"control", "innings", "over_min", "over_max", "min_balls", "max_balls", "min_runs", "max_runs",
               "min_wickets", "max_wickets", "top_teams"}
_BOOL_PARAMS = {"is_chase", "include_international"}


def params_from_query_string(query_string: str) -> Dict[str, Any]:
    """Snapshot params from the exact query string the site sent to GET /query/deliveries.

    The Embed and Download image buttons pass it through unchanged, so a snapshot runs the query
    the viewer is looking at. Parsed like the route: repeated keys and comma lists both become
    lists; paging and display-only keys are dropped; unknown keys are rejected by the cleaner.
    """
    from urllib.parse import parse_qsl

    from routers.query_builder_v2 import preprocess_int_list_param, preprocess_list_param

    raw: Dict[str, list] = {}
    for key, value in parse_qsl(query_string.lstrip("?"), keep_blank_values=False):
        raw.setdefault(key, []).append(value)
    for key in ("limit", "offset", "show_summary_rows", "striker_batter_type", "non_striker_batter_type"):
        raw.pop(key, None)
    params: Dict[str, Any] = {}
    for key, values in raw.items():
        if key == "wagon_zone":
            params[key] = preprocess_int_list_param(values)
        elif key in LIST_PARAMS:
            params[key] = preprocess_list_param(values)
        elif key in _INT_PARAMS:
            try:
                params[key] = int(values[-1])
            except ValueError:
                raise SnapshotError(f"{key} must be a whole number")
        elif key in _BOOL_PARAMS:
            params[key] = values[-1].lower() in ("true", "1", "yes")
        else:
            params[key] = values[-1]
    return params


_METRIC_LABELS = {
    "control_percentage": "control %", "dot_percentage": "dot %", "boundary_percentage": "boundary %",
    "strike_rate": "strike rate", "average": "average", "economy": "economy", "impact": "Impact", "wpa": "WPA",
    "raa": "runs above average", "runs": "runs", "balls": "balls", "wickets": "wickets",
}
_FORMAT_LABELS = {"T20": "T20", "ODI": "ODI", "TEST": "Test"}


def _plural(word: str) -> str:
    word = word.replace("_", " ")
    return word if word.endswith("s") else word + "s"


def metric_label(metric: Optional[str]) -> str:
    if not metric:
        return ""
    return _METRIC_LABELS.get(metric, metric.replace("_percentage", " %").replace("_", " "))


def _and(values: List[str]) -> str:
    values = [v.replace("_", " ").lower() for v in values]
    return values[0] if len(values) == 1 else ", ".join(values[:-1]) + " and " + values[-1]


def _filter_phrase(params: Dict[str, Any]) -> str:
    """The filters that change what a chart means: " off pull and hook shots", " against spin"."""
    out = ""
    if params.get("shot"):
        out += f" off {_and(params['shot'])} shots"
    if params.get("bowl_kind"):
        kinds = [k.split()[0] for k in params["bowl_kind"]]  # "pace bowler" -> "pace"
        out += f" against {_and(kinds)}"
    if params.get("bowl_style"):
        out += f" against {', '.join(params['bowl_style'])}"
    if params.get("length"):
        out += f" to {_and(params['length'])} balls"
    if params.get("line"):
        out += f" on the {_and(params['line'])} line"
    if params.get("dismissal"):
        out += f" ({_and(params['dismissal'])})"
    return out


def title_parts(params: Dict[str, Any]) -> Dict[str, str]:
    """Pieces of a chart headline: who, scope ("ODI partnerships"), venue, window, minimum."""
    who = (params.get("batters") or params.get("bowlers") or params.get("players") or params.get("teams")
           or params.get("batting_teams") or params.get("bowling_teams") or [])
    scope = " ".join(filter(None, [
        ", ".join(params.get("leagues") or []) or _FORMAT_LABELS.get(str(params.get("fmt") or "").upper()),
        # match_id makes rows per-match; it is not what the chart is "of".
        " & ".join(_plural(g) for g in params.get("group_by") or [] if g != "match_id"),
    ]))
    start, end = params.get("start_date"), params.get("end_date")
    if start and end:
        window = f", {start.year}–{end.year}" if start.year != end.year else f", {start.year}"
    elif start:
        window = f", since {start.year}"
    elif end:
        window = f", up to {end.year}"
    else:
        window = ""
    overs = ""
    if params.get("over_min") is not None or params.get("over_max") is not None:
        lo, hi = params.get("over_min"), params.get("over_max")
        overs = (f" in overs {lo + 1}-{hi + 1}" if lo is not None and hi is not None
                 else f" from over {lo + 1}" if lo is not None else f" up to over {hi + 1}")
    return {
        "who": ", ".join(who[:2]),
        "overs": overs,
        "filters": _filter_phrase(params),
        "scope": scope,
        "venue": f" at {params['venue']}" if params.get("venue") else "",
        "window": window,
        "minimum": f" ({params['min_balls']:,}+ balls)" if params.get("min_balls") else "",
    }


def default_title(params: Dict[str, Any], metric: Optional[str]) -> str:
    """A self-contained headline for a share image: what, ranked by what, over which window.

    "ODI partnerships by control %, since 2019 (1,000+ balls)". Statement, not a question, and
    it carries its own numbers (the content rules for Reddit-style stat posts).
    """
    p = title_parts(params)
    scope = p["scope"]
    title = f"{p['who']}: {scope}" if p["who"] else scope[:1].upper() + scope[1:]
    title += p["filters"] + p["venue"] + p["overs"]
    if metric:
        title += f" by {metric_label(metric)}"
    return title + p["window"] + p["minimum"]


# Groupings whose natural order is the point of the chart (mcp_server.server._SEQUENTIAL_KEYS + phase).
_SEQUENCE_GROUPS = {"year", "over", "ball", "ball_in_over", "ball_in_spell", "innings", "batting_position", "phase"}
# Ranked ascending when a chart is "by" them.
_LOWER_IS_BETTER = {"economy", "bowling_average", "bowling_strike_rate"}


def _query_data(db: Session, params: Dict[str, Any]) -> Dict[str, Any]:
    from mcp_server.server import structure_query_result
    from services.query_builder_v2 import run_deliveries_query

    query = {k: v for k, v in params.items() if k in QUERY_PARAMS}
    view = {k: v for k, v in params.items() if k in PRESENTATION}
    limit = int(view.get("limit") or 12)
    query.setdefault("limit", max(limit, 200))
    result = run_deliveries_query(db, **query)
    display_params = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in query.items()
                      if k not in ("group_by", "fmt", "gender", "limit")}

    def structure(sort_by, sort_descending):
        return structure_query_result(
            result, display_params, query["group_by"], query_mode=query.get("query_mode") or "delivery",
            format=query.get("fmt") or "ALL", gender=query.get("gender") or "male",
            batters=query.get("batters"), bowlers=query.get("bowlers"), sort_by=sort_by,
            sort_descending=sort_descending, limit=limit, chart=view.get("chart") or "auto",
            chart_metric=view.get("chart_metric"), scatter_x=view.get("scatter_x"), scatter_y=view.get("scatter_y"),
        )

    structured = structure(view.get("sort_by"), view.get("sort_descending", True))
    metric = view.get("sort_by") or view.get("chart_metric") or (structured.get("chart") or {}).get("metric")
    # The title says "by <metric>", so the rows must be the top ones by it -- not the first N in
    # the API's default (balls) order. Sequences (years, overs, phases) keep their natural order.
    first = query["group_by"][0]
    if not view.get("sort_by") and metric and first not in _SEQUENCE_GROUPS:
        structured = structure(metric, metric not in _LOWER_IS_BETTER)
    structured["title"] = view.get("title") or default_title(query, metric)
    structured["highlight"] = view.get("highlight")
    return structured


def _match_meta(scorecard: Dict[str, Any]) -> Dict[str, Any]:
    match = scorecard.get("match") or {}
    summary = scorecard.get("summary") or {}
    return {
        "match_id": match.get("id"),
        "date": str(match.get("date")),
        "competition": match.get("competition") or match.get("event_name"),
        "venue": match.get("venue"),
        "result": match.get("result_text"),
        "teams": match.get("teams") or [],
        "scores": summary.get("innings_scores") or [],
    }


def _win_prob_data(db: Session, match_id: str) -> Dict[str, Any]:
    from services.match_scorecard import get_match_scorecard_service

    scorecard = get_match_scorecard_service(match_id=str(match_id), min_balls=6, db=db)
    primer = (scorecard.get("summary") or {}).get("primer")
    if not primer:
        raise SnapshotError("This match has no ball-by-ball win-probability data yet.")
    return {**_match_meta(scorecard), "primer": primer}


def _recap_data(db: Session, match_id: str) -> Dict[str, Any]:
    from services.match_recap import build_recap
    from services.match_scorecard import get_match_scorecard_service

    scorecard = get_match_scorecard_service(match_id=str(match_id), min_balls=6, db=db)
    if not (scorecard.get("summary") or {}).get("primer"):
        raise SnapshotError("This match has no ball-by-ball data for a recap yet.")
    recap = build_recap(scorecard, db)
    if not recap.get("available"):
        raise SnapshotError("No recap available for this match.")
    return {**_match_meta(scorecard), "recap": recap}


def create_snapshot(db: Session, kind: str, params: Dict[str, Any], created_by: Optional[str] = None) -> Dict[str, Any]:
    """Create (or return the existing identical) snapshot; returns {id, kind, title, data}."""
    if kind not in KINDS:
        raise SnapshotError(f"kind must be one of {KINDS}")
    if kind == "query":
        params = _clean_query_params(params)
    else:
        if not params.get("match_id"):
            raise SnapshotError("match_id is required")
        params = {"match_id": str(params["match_id"])}

    version = data_version(db)
    params_hash = hashlib.sha256(
        json.dumps({"p": normalize(params), "v": version}, sort_keys=True, default=str).encode()
    ).hexdigest()
    existing = db.execute(text(
        "SELECT id, kind, title, data FROM chart_snapshots WHERE kind = :k AND params_hash = :h"
    ), {"k": kind, "h": params_hash}).mappings().first()
    if existing:
        return dict(existing)

    if kind == "query":
        data = _query_data(db, params)
        title = data.get("title")
    elif kind == "win_prob":
        data = _win_prob_data(db, params["match_id"])
        title = f"Win probability · {data.get('result') or ''}".strip(" ·")
    else:
        data = _recap_data(db, params["match_id"])
        title = data["recap"].get("headline")

    snapshot_id = _new_id()
    stored_params = json.dumps(normalize(params), default=str)
    from database import engine

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO chart_snapshots (id, kind, params, params_hash, data, title, created_by)
            VALUES (:id, :kind, CAST(:params AS jsonb), :hash, CAST(:data AS json), :title, :by)
            ON CONFLICT (kind, params_hash) DO NOTHING
        """), {"id": snapshot_id, "kind": kind, "params": stored_params, "hash": params_hash,
               "data": json.dumps(data, default=str), "title": title, "by": created_by})
        row = conn.execute(text(
            "SELECT id, kind, title, data FROM chart_snapshots WHERE kind = :k AND params_hash = :h"
        ), {"k": kind, "h": params_hash}).mappings().first()
    return dict(row)


STATIC_KINDS = ("ranking",)


def create_static_snapshot(db: Session, kind: str, data: Dict[str, Any], title: str, key: Dict[str, Any],
                           created_by: str) -> Dict[str, Any]:
    """Store precomputed chart data (e.g. a records ranking for a content pack).

    Internal only: the public POST /snapshots never accepts data, only parameters. `key`
    identifies the chart for de-duplication; it is not versioned, because the data is frozen
    at the moment the fact was found.
    """
    if kind not in STATIC_KINDS:
        raise SnapshotError(f"kind must be one of {STATIC_KINDS}")
    params_hash = hashlib.sha256(json.dumps({"static": key}, sort_keys=True, default=str).encode()).hexdigest()
    from database import engine

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO chart_snapshots (id, kind, params, params_hash, data, title, created_by)
            VALUES (:id, :kind, CAST(:params AS jsonb), :hash, CAST(:data AS json), :title, :by)
            ON CONFLICT (kind, params_hash) DO NOTHING
        """), {"id": _new_id(), "kind": kind, "params": json.dumps(key, default=str), "hash": params_hash,
               "data": json.dumps(data, default=str), "title": title, "by": created_by})
        row = conn.execute(text(
            "SELECT id, kind, title, data FROM chart_snapshots WHERE kind = :k AND params_hash = :h"
        ), {"k": kind, "h": params_hash}).mappings().first()
    return dict(row)


def get_snapshot(db: Session, snapshot_id: str) -> Optional[Dict[str, Any]]:
    row = db.execute(text(
        "SELECT id, kind, title, params, data, created_at FROM chart_snapshots WHERE id = :id"
    ), {"id": snapshot_id}).mappings().first()
    return dict(row) if row else None
