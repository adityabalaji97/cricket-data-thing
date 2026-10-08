"""Admin "Social" queue: content packs (services/content_packs.py). All routes need the admin token."""
import json
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_session
from routers._auth import require_admin
from services import content_rules

router = APIRouter(prefix="/admin/content", tags=["admin"], dependencies=[Depends(require_admin)])

STATUSES = ("ready", "posted", "skipped", "expired")


CHANNELS = ("reddit", "instagram")


@router.get("/packs")
def list_packs(status: str = "ready", channel: str = "reddit", limit: int = 60, db: Session = Depends(get_session)):
    """One channel's packs. Instagram packs (services/ig_backlog.py) come in calendar order, the bench last."""
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail=f"channel must be one of {CHANNELS}")
    if channel == "instagram":
        # Recaps stop being news at the sides' next meeting (services/ig_backlog.recap_post_by): expire them as soon as
        # the queue is read, not at the next nightly run.
        from services.content_packs import expire

        expire(db)
    where = "WHERE p.channel = :channel" + ("" if status == "all" else " AND p.status = :status")
    order = ("p.planned_for ASC NULLS LAST, p.created_at" if channel == "instagram"
             else "(p.status = 'ready') DESC, p.post_by ASC NULLS LAST, p.created_at DESC")
    rows = db.execute(text(f"""
        SELECT p.id, p.match_id, p.snapshot_id, p.title, p.first_comment, p.subreddit, p.flair, p.facts,
               p.rule_warnings, p.status, p.post_by, p.posted_url, p.source, p.created_at,
               p.channel, p.planned_for, p.pillar, p.caption, p.angle_key,
               m.date AS match_date, m.team1, m.team2, m.competition, m.data_source, s.kind AS snapshot_kind
        FROM content_packs p
        LEFT JOIN matches m ON m.id = p.match_id
        LEFT JOIN chart_snapshots s ON s.id = p.snapshot_id
        {where}
        ORDER BY {order}
        LIMIT :limit
    """), {"status": status, "channel": channel, "limit": min(limit, 200)}).mappings()
    packs = [dict(r) for r in rows]
    if channel == "instagram":
        # The admin's day list: what kind of post each is and when to post it (services/ig_plan.py).
        from services.ig_plan import TIMES, _kind
        from services.ig_season import post_format

        for p in packs:
            p["kind"] = _kind(p)
            p["time"] = (p["facts"] or {}).get("post_time") or TIMES.get(p["kind"], "1 pm")
            p["format"] = post_format(p["facts"] or {}, p["angle_key"])
    return {"packs": packs}


class PackUpdate(BaseModel):
    status: Optional[str] = None
    posted_url: Optional[str] = Field(default=None, max_length=500)
    title: Optional[str] = Field(default=None, max_length=300)
    # Switch the pack's image to another chart form it was built with (facts.chart_options).
    snapshot_id: Optional[str] = Field(default=None, max_length=32)
    # Instagram posts: where it has gone out so far (facts.posted_on), ticked per platform in the admin.
    posted_on: Optional[List[str]] = None
    # Instagram posts: put on a day (from the bench), or back on the bench (bench=true: no day, no deadline).
    planned_for: Optional[date] = None
    bench: Optional[bool] = None
    # An optional preview (facts.optional, a top-20 game beyond the day's one): false puts it in the feed.
    optional: Optional[bool] = None


PLATFORMS = ("instagram", "youtube", "x")


@router.patch("/packs/{pack_id}")
def update_pack(pack_id: int, body: PackUpdate, db: Session = Depends(get_session)):
    pack = db.execute(text("SELECT facts FROM content_packs WHERE id = :id"), {"id": pack_id}).mappings().first()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    sets, params = [], {"id": pack_id}
    fact_sets = []  # (facts key, bind name)
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
    if body.snapshot_id is not None:
        facts = pack["facts"] or {}
        option = next((o for o in facts.get("chart_options") or [] if o.get("snapshot_id") == body.snapshot_id), None)
        if not option:
            raise HTTPException(status_code=400, detail="That chart is not one of this pack's options")
        sets.append("snapshot_id = :snap")
        params["snap"] = body.snapshot_id
        if option.get("title") and body.title is None:
            known = [facts.get("numbers") or {}, {k: facts.get(k) for k in ("n", "since_year", "rank")}]
            _errors, warnings = content_rules.check_title(option["title"], known, facts.get("subject"))
            sets += ["title = :title", "rule_warnings = CAST(:w AS jsonb)"]
            params.update(title=option["title"], w=json.dumps(_errors + warnings))
    if body.posted_on is not None:
        unknown = set(body.posted_on) - set(PLATFORMS)
        if unknown:
            raise HTTPException(status_code=400, detail=f"posted_on takes {', '.join(PLATFORMS)}")
        fact_sets.append(("posted_on", "po"))
        params["po"] = json.dumps([p for p in PLATFORMS if p in body.posted_on])
    if body.bench:
        sets += ["planned_for = NULL", "post_by = NULL"]
    elif body.planned_for is not None:
        sets.append("planned_for = :day")
        params["day"] = body.planned_for
    if body.optional is not None:
        fact_sets.append(("optional", "opt"))
        params["opt"] = json.dumps(bool(body.optional))
    if fact_sets:  # one assignment to facts, however many keys change
        expr = "COALESCE(facts, '{}'::jsonb)"
        for key, param in fact_sets:
            expr = f"jsonb_set({expr}, '{{{key}}}', CAST(:{param} AS jsonb))"
        sets.append(f"facts = {expr}")
    if not sets:
        return {"ok": True}
    from database import engine

    with engine.begin() as conn:
        conn.execute(text(f"UPDATE content_packs SET {', '.join(sets)} WHERE id = :id"), params)
    return {"ok": True}


class GenerateRequest(BaseModel):
    match_ids: List[str] = []
    days: int = Field(default=3, ge=1, le=30)


def _generate_in_background(match_ids: List[str], days: int) -> None:
    from services.content_packs import generate

    db = next(get_session())
    try:
        generate(db, days=days, match_ids=match_ids or None)
    finally:
        db.close()


@router.post("/generate", status_code=202)
def generate_packs(body: GenerateRequest, background: BackgroundTasks):
    """Scan recent (or the given) matches now instead of waiting for the nightly run.

    Runs after the response: building the ball-by-ball comparison sets takes ~30 s per format on
    a cold process, past Heroku's 30 s request limit. New packs appear in the queue when done.
    """
    background.add_task(_generate_in_background, body.match_ids, body.days)
    return {"started": True}


class IdeaRequest(BaseModel):
    text: str = Field(min_length=8, max_length=500)
    format: Optional[str] = None  # T20 | ODI | ALL; guessed from the text when omitted


def _process_idea_in_background(idea_id: int, fmt: Optional[str]) -> None:
    from services.content_ideas import process_idea

    db = next(get_session())
    try:
        process_idea(db, idea_id, fmt)
    finally:
        db.close()


@router.post("/ideas", status_code=202)
def submit_idea(body: IdeaRequest, background: BackgroundTasks):
    """Idea -> pack (services/content_ideas.py). Parsing and a cold query can pass Heroku's 30 s
    limit, so it runs after the response; poll GET /ideas for the outcome."""
    from services.content_ideas import create_idea

    idea_id = create_idea(body.text)
    background.add_task(_process_idea_in_background, idea_id, body.format)
    return {"id": idea_id, "status": "pending"}


@router.get("/ideas")
def list_ideas(limit: int = 15, db: Session = Depends(get_session)):
    rows = db.execute(text("""
        SELECT i.id, i.text, i.status, i.note, i.pack_id, i.created_at, i.resolved_at, p.title AS pack_title
        FROM content_ideas i LEFT JOIN content_packs p ON p.id = i.pack_id
        ORDER BY i.created_at DESC LIMIT :limit
    """), {"limit": min(limit, 100)}).mappings()
    return {"ideas": [dict(r) for r in rows]}


@router.post("/packs/{pack_id}/note", status_code=201)
def pack_to_note(pack_id: int, db: Session = Depends(get_session)):
    """One tap from the Social queue: the pack becomes a draft note (or the one it already became)."""
    from services.note_drafts import note_from_pack
    from services.notes import NoteError

    try:
        return note_from_pack(db, pack_id)
    except NoteError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/plan")
def instagram_plan(start: Optional[str] = None, db: Session = Depends(get_session)):
    """This week's Instagram plan (services/ig_plan.py): each day's posts with a time, plus today's comment kit."""
    from datetime import date, datetime, timedelta, timezone

    from services import ig_plan

    day = date.fromisoformat(start) if start else datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
    return {"week": ig_plan.week(db, day), "comment_kit": ig_plan.comment_kit(db, day)}


# The morning digest, read by a scheduled routine that emails it: its own read-only token (IG_DIGEST_TOKEN), so the
# admin token never leaves Heroku.
digest_router = APIRouter(prefix="/digest", tags=["digest"])


@digest_router.get("/instagram")
def instagram_digest(token: str = "", db: Session = Depends(get_session)):
    import hmac
    import os
    from datetime import datetime, timedelta, timezone

    from services import ig_plan

    expected = os.environ.get("IG_DIGEST_TOKEN") or ""
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=404, detail="Not found")
    return ig_plan.digest(db, datetime.now(timezone(timedelta(hours=5, minutes=30))).date())
