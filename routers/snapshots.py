"""Chart snapshots for notes, embeds and share images (services/snapshots.py)."""
import re
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_session
from services.snapshots import SnapshotError, create_snapshot, get_snapshot, params_from_query_string

router = APIRouter(prefix="/snapshots", tags=["snapshots"])

_ID = re.compile(r"^[A-Za-z0-9]{6,16}$")
# Public creation (the Embed / Download image buttons) runs a query, so it is rate-limited per
# client: 20 per 10 minutes. Identical requests are de-duplicated before this matters.
_WINDOW_SECONDS, _MAX_PER_WINDOW = 600, 20
_recent: Dict[str, deque] = defaultdict(deque)


def _client(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def _allow(client: str) -> bool:
    now = time.time()
    q = _recent[client]
    while q and now - q[0] > _WINDOW_SECONDS:
        q.popleft()
    if len(q) >= _MAX_PER_WINDOW:
        return False
    q.append(now)
    return True


class SnapshotRequest(BaseModel):
    kind: str
    params: Dict[str, Any] = {}
    # kind=query only: the site's own /query/deliveries query string, merged under params
    # (which then carry just the presentation options: title, sort_by, chart_metric...).
    query_string: Optional[str] = None


@router.post("")
def create(body: SnapshotRequest, request: Request, db: Session = Depends(get_session)):
    if not _allow(_client(request)):
        raise HTTPException(status_code=429, detail="Too many charts created; try again in a few minutes.")
    try:
        params = dict(body.params)
        if body.query_string and body.kind == "query":
            params = {**params_from_query_string(body.query_string[:4000]), **params}
        snap = create_snapshot(db, body.kind, params, created_by="web")
    except SnapshotError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": snap["id"], "kind": snap["kind"], "title": snap["title"]}


class GraphicRequest(BaseModel):
    # The site's own /query/deliveries query string (what the viewer is looking at).
    query_string: str
    metric: str
    highlight: Optional[str] = None
    # {type: 'scatter', x_axis, y_axis} when the viewer's question named two metrics.
    chart: Optional[Dict[str, Any]] = None


@router.post("/graphic")
def create_graphic(body: GraphicRequest, request: Request, db: Session = Depends(get_session)):
    """'Make a graphic' from a query-builder result: the idea-pack chart forms, without the LLM.

    The query is re-run here from the query string (the client never sends chart data, so a
    graphic under hindsightcricket.com always shows real numbers). Every chart form the result
    supports is saved as a snapshot; the response lists them, best first, for the picker.
    """
    from services.content_ideas import attempt

    if not _allow(_client(request)):
        raise HTTPException(status_code=429, detail="Too many graphics made; try again in a few minutes.")
    try:
        params = params_from_query_string(body.query_string[:4000])
        if "format" in params:
            params["fmt"] = params.pop("format")
        if not params.get("group_by"):
            raise SnapshotError("Group the query (by player, team, season...) to make a graphic.")
        for key in ("start_date", "end_date"):
            if params.get(key) is not None:
                params[key] = str(params[key])
        planned = {"params": params, "metric": body.metric,
                   "highlight": [body.highlight] if body.highlight else None,
                   "chart": body.chart if (body.chart or {}).get("type") == "scatter" else None}
        description = f"{body.metric.replace('_', ' ')} by {' and '.join(params['group_by'])}"
        result = attempt(db, description, planned, created_by="graphic")
    except SnapshotError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result.get("status") != "resolved":
        raise HTTPException(status_code=400, detail=result.get("note") or "Nothing to chart for this query.")
    fact = result["fact"]
    return {"options": fact.get("chart_options") or [], "picked_by": fact.get("chart_picked_by"),
            "title": fact.get("title")}


# Ideas cost a natural-language parse (OpenAI, under the monthly cap): a per-client daily allowance
# on top of the short-window chart limit. In memory per dyno, which is enough to stop casual abuse.
IDEA_DAILY_LIMIT = 20
_idea_days: Dict[str, deque] = defaultdict(deque)


def _allow_idea(client: str) -> bool:
    now = time.time()
    q = _idea_days[client]
    while q and now - q[0] > 86400:
        q.popleft()
    if len(q) >= IDEA_DAILY_LIMIT:
        return False
    q.append(now)
    return True


class IdeaGraphicRequest(BaseModel):
    text: str
    format: Optional[str] = None  # 'T20' | 'ODI' | None (auto)


@router.post("/idea")
def create_idea_graphic(body: IdeaGraphicRequest, request: Request, db: Session = Depends(get_session)):
    """'Make a graphic' from a plain-English idea: the admin idea box, for everyone.

    The idea is parsed into a query (nl2query), run, and every chart form it supports is saved;
    no content pack is made. Conditions the query cannot apply are refused with the reason
    (content_ideas.plan), so a graphic never silently drops part of the question.
    """
    from services.content_ideas import attempt, plan

    text = (body.text or "").strip()
    if len(text) < 6 or len(text) > 300:
        raise HTTPException(status_code=400, detail="Describe the stat in 6-300 characters.")
    client = _client(request)
    if not _allow(client) or not _allow_idea(client):
        raise HTTPException(status_code=429, detail=f"That's today's limit of {IDEA_DAILY_LIMIT} ideas; try again tomorrow, "
                                                    "or build it in the query builder.")
    fmt = body.format if body.format in ("T20", "ODI") else None
    try:
        planned = plan(text, fmt, db)
        result = attempt(db, text, planned, created_by="graphic")
    except SnapshotError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result.get("status") != "resolved":
        raise HTTPException(status_code=400, detail=result.get("note") or "Nothing to chart for this idea yet.")
    fact = result["fact"]
    snap = result["snapshot"]
    options = fact.get("chart_options") or [{"form": "bars", "snapshot_id": snap["id"], "title": fact.get("title"), "p": None}]
    return {
        "options": options,
        "picked_by": fact.get("chart_picked_by"),
        "title": fact.get("title"),
        "explanation": planned.get("explanation"),
        # Readable chips of what was run ("Batter: Virat Kohli", "2024-01-01 -> today", "T20").
        "chips": (snap.get("data") or {}).get("filter_chips") or [],
        "query_url": (snap.get("data") or {}).get("hindsight_url"),
    }


@router.get("/{snapshot_id}")
def read(snapshot_id: str, db: Session = Depends(get_session)):
    if not _ID.match(snapshot_id):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    snap = get_snapshot(db, snapshot_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snap
