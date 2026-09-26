"""
Usage measurement endpoints (growth plan G0).

  POST /events          batched product events from the website (src/utils/analytics.js)
  GET  /admin/usage     weekly adoption report; needs the X-Admin-Token header to match the
                        ADMIN_TOKEN env var, and is 404 when ADMIN_TOKEN is unset

Events carry an anonymous per-browser id, never personal data, and are written off the request
path by services/usage_log.py.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_session
from services.usage_log import enqueue
from services.usage_report import build_usage_report

router = APIRouter(tags=["usage"])

EVENT_NAME = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
MAX_PROPS_BYTES = 2000
# Per client address: generous for real browsing (events are batched), tight for scripts.
RATE_LIMIT_EVENTS = 300
RATE_WINDOW_SECONDS = 60
_recent: Dict[str, Deque[float]] = defaultdict(deque)


class Event(BaseModel):
    event: str = Field(max_length=40)
    path: Optional[str] = Field(default=None, max_length=200)
    props: Optional[Dict[str, Any]] = None


class EventBatch(BaseModel):
    anon_id: str = Field(min_length=8, max_length=40)
    session_id: Optional[str] = Field(default=None, max_length=40)
    referrer: Optional[str] = Field(default=None, max_length=200)
    events: List[Event] = Field(min_length=1, max_length=50)


def _allowed(key: str, count: int) -> bool:
    now = time.monotonic()
    window = _recent[key]
    while window and now - window[0] > RATE_WINDOW_SECONDS:
        window.popleft()
    if len(window) + count > RATE_LIMIT_EVENTS:
        return False
    window.extend([now] * count)
    return True


@router.post("/events", status_code=204)
def post_events(batch: EventBatch, request: Request) -> Response:
    client_key = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0]
    if not _allowed(client_key, len(batch.events)):
        return Response(status_code=429)
    country = (request.headers.get("x-client-country") or "")[:4] or None
    for event in batch.events:
        if not EVENT_NAME.match(event.event):
            continue
        props = json.dumps(event.props or {}, default=str)
        if len(props) > MAX_PROPS_BYTES:
            props = "{}"
        enqueue("event", {
            "anon_id": batch.anon_id, "session_id": batch.session_id, "event": event.event,
            "path": event.path, "props": props, "referrer": batch.referrer, "country": country,
        })
    return Response(status_code=204)


def _require_admin(token: Optional[str]) -> None:
    expected = os.environ.get("ADMIN_TOKEN")
    if not expected:
        raise HTTPException(status_code=404, detail="Not Found")
    if token != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/admin/usage")
def usage_report(weeks: int = 8, x_admin_token: Optional[str] = Header(default=None), db: Session = Depends(get_session)):
    """Week-by-week adoption report (see services/usage_report.py)."""
    _require_admin(x_admin_token)
    return build_usage_report(db, weeks)
