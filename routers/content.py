"""Admin "Social" queue: content packs (services/content_packs.py). All routes need the admin token."""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_session
from routers._auth import require_admin
from services import content_rules

router = APIRouter(prefix="/admin/content", tags=["admin"], dependencies=[Depends(require_admin)])

STATUSES = ("ready", "posted", "skipped", "expired")


@router.get("/packs")
def list_packs(status: str = "ready", limit: int = 60, db: Session = Depends(get_session)):
    where = "" if status == "all" else "WHERE p.status = :status"
    rows = db.execute(text(f"""
        SELECT p.id, p.match_id, p.snapshot_id, p.title, p.first_comment, p.subreddit, p.flair, p.facts,
               p.rule_warnings, p.status, p.post_by, p.posted_url, p.source, p.created_at,
               m.date AS match_date, m.team1, m.team2, m.competition, s.kind AS snapshot_kind
        FROM content_packs p
        LEFT JOIN matches m ON m.id = p.match_id
        LEFT JOIN chart_snapshots s ON s.id = p.snapshot_id
        {where}
        ORDER BY (p.status = 'ready') DESC, p.post_by ASC NULLS LAST, p.created_at DESC
        LIMIT :limit
    """), {"status": status, "limit": min(limit, 200)}).mappings()
    return {"packs": [dict(r) for r in rows]}


class PackUpdate(BaseModel):
    status: Optional[str] = None
    posted_url: Optional[str] = Field(default=None, max_length=500)
    title: Optional[str] = Field(default=None, max_length=300)


@router.patch("/packs/{pack_id}")
def update_pack(pack_id: int, body: PackUpdate, db: Session = Depends(get_session)):
    pack = db.execute(text("SELECT facts FROM content_packs WHERE id = :id"), {"id": pack_id}).mappings().first()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    sets, params = [], {"id": pack_id}
    if body.status is not None:
        if body.status not in STATUSES:
            raise HTTPException(status_code=400, detail=f"status must be one of {STATUSES}")
        sets.append("status = :status")
        params["status"] = body.status
    if body.posted_url is not None:
        sets.append("posted_url = :url")
        params["url"] = body.posted_url.strip() or None
    if body.title is not None:
        facts = pack["facts"] or {}
        known = [facts.get("numbers") or {}, {k: facts.get(k) for k in ("n", "since_year", "rank")}]
        errors, warnings = content_rules.check_title(body.title, known, facts.get("subject"))
        if errors:
            raise HTTPException(status_code=400, detail=" ".join(errors))
        sets += ["title = :title", "rule_warnings = CAST(:w AS jsonb)"]
        params.update(title=body.title.strip(), w=json.dumps(warnings))
    if not sets:
        return {"ok": True}
    from database import engine

    with engine.begin() as conn:
        conn.execute(text(f"UPDATE content_packs SET {', '.join(sets)} WHERE id = :id"), params)
    return {"ok": True}


class GenerateRequest(BaseModel):
    match_ids: List[str] = []
    days: int = Field(default=3, ge=1, le=30)


@router.post("/generate")
def generate_packs(body: GenerateRequest, db: Session = Depends(get_session)):
    """Scan recent (or the given) matches now instead of waiting for the nightly run."""
    from services.content_packs import generate

    summary = generate(db, days=body.days, match_ids=body.match_ids or None)
    return {
        "matches": summary["matches"],
        "created": [p["title"] for p in summary["packs"] if not p.get("duplicate")],
        "refused": [{"title": p["title"], "why": p["refused"]} for p in summary["refused"]],
        "expired": summary["expired"],
    }
