"""Chart snapshots for notes, embeds and share images (services/snapshots.py)."""
import re
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_session
from services.snapshots import SnapshotError, create_snapshot, get_snapshot

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
    params: Dict[str, Any]


@router.post("")
def create(body: SnapshotRequest, request: Request, db: Session = Depends(get_session)):
    if not _allow(_client(request)):
        raise HTTPException(status_code=429, detail="Too many charts created; try again in a few minutes.")
    try:
        snap = create_snapshot(db, body.kind, body.params, created_by="web")
    except SnapshotError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": snap["id"], "kind": snap["kind"], "title": snap["title"]}


@router.get("/{snapshot_id}")
def read(snapshot_id: str, db: Session = Depends(get_session)):
    if not _ID.match(snapshot_id):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    snap = get_snapshot(db, snapshot_id)
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snap
