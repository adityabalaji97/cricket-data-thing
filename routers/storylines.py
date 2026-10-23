"""
Storylines review (MATCH_PREVIEW_STORYLINES_PLAN.md chunk 7): the user approves, edits or drops each fixture's
talking points (services/preview_storylines.py) before any preview or post uses them. Admin token only.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_session
from routers._auth import require_admin

router = APIRouter(prefix="/storylines", tags=["Storylines"], dependencies=[Depends(require_admin)])


@router.get("/admin")
def list_storylines(days: int = 4, db: Session = Depends(get_session)):
    """Upcoming fixtures' talking points, pending first, with their headlines."""
    rows = db.execute(text("""
        SELECT id, fixture_key, match_date, team1, team2, rank, claim, edited_claim, kind, players, team, sources,
               appeal, appeal_by, status, reviewed_at, test, tested_at
        FROM fixture_storylines WHERE match_date BETWEEN CURRENT_DATE - 1 AND CURRENT_DATE + :d
        ORDER BY match_date, fixture_key, CASE status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END, rank
    """), {"d": max(1, min(days, 14))}).mappings().all()
    news = dict(db.execute(text("""
        SELECT fixture_key, COUNT(*) FROM fixture_news WHERE match_date BETWEEN CURRENT_DATE - 1 AND CURRENT_DATE + :d
        GROUP BY 1
    """), {"d": max(1, min(days, 14))}).all())
    fixtures = {}
    for r in rows:
        f = fixtures.setdefault(r["fixture_key"], {"fixture_key": r["fixture_key"], "match_date": str(r["match_date"]),
                                                   "team1": r["team1"], "team2": r["team2"], "headlines": news.get(r["fixture_key"], 0),
                                                   "points": []})
        f["points"].append({**{k: r[k] for k in ("id", "rank", "claim", "edited_claim", "kind", "players", "team",
                                                  "sources", "appeal", "appeal_by", "status", "test")},
                            "reviewed_at": r["reviewed_at"].isoformat() if r["reviewed_at"] else None,
                            "tested_at": r["tested_at"].isoformat() if r["tested_at"] else None})
    for key, n in news.items():  # fixtures with headlines but no points yet
        if key not in fixtures:
            d, a, b = key.split("|")
            fixtures[key] = {"fixture_key": key, "match_date": d, "team1": a, "team2": b, "headlines": n, "points": []}
    try:
        ledes = dict(db.execute(text("SELECT fixture_key, lede FROM fixture_ledes WHERE fixture_key = ANY(:k)"),
                                {"k": list(fixtures)}).all())
    except Exception:  # before migration 031
        db.rollback()
        ledes = {}
    for key, f in fixtures.items():
        f["lede"] = ledes.get(key)
    return {"fixtures": sorted(fixtures.values(), key=lambda f: (f["match_date"], f["fixture_key"]))}


class Run(BaseModel):
    fixture_key: str


@router.post("/admin/run")
def run(body: Run, db: Session = Depends(get_session)):
    """Extract this fixture's talking points now (one model call); new ones arrive pending."""
    from database import engine
    from services import preview_storylines as S

    fx = next((f for f in S.fixtures_with_news(db, 14) if f["fixture_key"] == body.fixture_key), None)
    if not fx:
        raise HTTPException(status_code=404, detail="No headlines for that fixture")
    points = S.rank(fx, S.extract(db, fx))
    with engine.begin() as conn:
        new = S.store(conn, fx, points)
    return {"fixture_key": body.fixture_key, "points": len(points), "new": new}


@router.post("/admin/{point_id}/test")
def test(point_id: int, db: Session = Depends(get_session)):
    """Answer a talking point from the data now (services/storyline_testers.py)."""
    from services.preview_storylines import test_point

    result = test_point(db, point_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No such talking point")
    _rewrite_lede(db, point_id)
    return result


def _rewrite_lede(db: Session, point_id: int) -> None:
    """The fixture's lede follows its approved points (chunk 5); a failure never blocks the review."""
    from services.preview_storylines import write_lede

    key = db.execute(text("SELECT fixture_key FROM fixture_storylines WHERE id = :i"), {"i": point_id}).scalar()
    if key:
        try:
            write_lede(db, key)
        except Exception:  # pragma: no cover
            db.rollback()


class Review(BaseModel):
    action: Literal["approve", "drop", "pending", "edit"]
    claim: Optional[str] = None


@router.post("/admin/{point_id}")
def review(point_id: int, body: Review, db: Session = Depends(get_session)):
    if body.action == "edit":
        claim = (body.claim or "").strip()
        if not claim or len(claim) > 300:
            raise HTTPException(status_code=400, detail="claim must be 1-300 characters")
        sql, params = "edited_claim = :c, status = 'approved'", {"c": claim}  # an edit is an approval in your words
    else:
        status = {"approve": "approved", "drop": "dropped", "pending": "pending"}[body.action]
        sql, params = "status = :s", {"s": status}
    row = db.execute(text(f"""
        UPDATE fixture_storylines SET {sql}, reviewed_at = now() WHERE id = :i
        RETURNING id, status, COALESCE(edited_claim, claim) AS claim
    """), {**params, "i": point_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No such talking point")
    db.commit()
    out = dict(row)
    if row["status"] == "approved":  # what's approved is tested straight away (chunk 3)
        from services.preview_storylines import test_point

        out["test"] = test_point(db, point_id)
    _rewrite_lede(db, point_id)  # approved, edited, dropped or undone: the lede follows
    return out
