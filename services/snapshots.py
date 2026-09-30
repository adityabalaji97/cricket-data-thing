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
from typing import Any, Dict, Optional

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
    structured = structure_query_result(
        result, display_params, query["group_by"], query_mode=query.get("query_mode") or "delivery",
        format=query.get("fmt") or "ALL", gender=query.get("gender") or "male",
        batters=query.get("batters"), bowlers=query.get("bowlers"), sort_by=view.get("sort_by"),
        sort_descending=view.get("sort_descending", True), limit=limit, chart=view.get("chart") or "auto",
        chart_metric=view.get("chart_metric"), scatter_x=view.get("scatter_x"), scatter_y=view.get("scatter_y"),
    )
    if view.get("title"):
        structured["title"] = view["title"]
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


def get_snapshot(db: Session, snapshot_id: str) -> Optional[Dict[str, Any]]:
    row = db.execute(text(
        "SELECT id, kind, title, params, data, created_at FROM chart_snapshots WHERE id = :id"
    ), {"id": snapshot_id}).mappings().first()
    return dict(row) if row else None
