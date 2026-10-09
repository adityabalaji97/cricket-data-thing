"""
The morning check: today's unposted Instagram posts, rebuilt with this morning's data and compared with what's queued.
Posts are built days ahead; a match loaded since can move a number. A post whose numbers changed is rebuilt in place
(same key, same day, same time); posted, skipped and expired posts are never touched.

    check_today(db, today, base, write)  ->  [{key, status: ok|rebuilt|changed|static|skipped|failed, diffs}]

Each post is rebuilt by the code that made it (preview, recap, spotlight, debate, trend, record), with saves stubbed
for the comparison. Debates and trends are rebuilt with their stored measures, so only the data can differ, not a
model's choice. The deeper cut is re-run for the same player and the same stat. The outcome goes on the post as
facts.check, which the admin shows.
"""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

KEEP = ("optional", "post_time", "pinned", "headlines", "appeal", "appeal_by", "note_id", "note_slug", "posted_on",
        "deep_cut_scope", "deep_cut_exclude", "spec")  # carried from the old fact onto a rebuilt one


@contextmanager
def _no_saves():
    """Carousel snapshots commit on their own connection: the comparison build saves none, and hands back the slides
    of the carousel it would have saved (captured["slides"])."""
    import services.snapshots as snapshots

    captured: Dict[str, Any] = {"slides": []}

    def stub(db, kind, data, title, key, created_by):
        if kind == "carousel":
            captured["slides"] = list((data or {}).get("slides") or [])
        return {"id": "check", "kind": kind}
    real = snapshots.create_static_snapshot
    snapshots.create_static_snapshot = stub
    try:
        yield captured
    finally:
        snapshots.create_static_snapshot = real


def _round(v: Any) -> Any:
    """Compared as stored: JSON round-trip (tuples become lists), floats to one decimal."""
    if isinstance(v, tuple):
        v = list(v)
    if isinstance(v, float):
        return round(v, 1)
    if isinstance(v, dict):
        return {k: _round(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_round(x) for x in v]
    return v


def _is_deep(slide: Dict[str, Any]) -> bool:
    from services.ig_posts.deep_cut import KICKER

    return (slide.get("card") or {}).get("kicker") == KICKER


def _label(slide: Dict[str, Any]) -> str:
    if slide.get("type") == "card":
        return (slide.get("card") or {}).get("title") or ""
    return slide.get("text") or slide.get("heading") or slide.get("type") or ""


def compare(old: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """What changed between two slide lists (the deeper cut compared on its own): a title or a chart's values."""
    old = [s for s in old if not _is_deep(s)]
    new = [s for s in new if not _is_deep(s)]
    diffs = []
    for i, (o, n) in enumerate(zip(old, new), start=1):
        if _label(o) != _label(n):
            diffs.append({"slide": i, "was": _label(o), "now": _label(n)})
        elif o.get("type") == "card" and _round((o.get("card") or {}).get("payload")) != _round((n.get("card") or {}).get("payload")):
            diffs.append({"slide": i, "was": _label(o), "now": "same title, chart values changed"})
        elif o.get("type") == "text" and o.get("body") != n.get("body"):
            diffs.append({"slide": i, "was": o.get("body") or "", "now": n.get("body") or ""})
    if len(old) != len(new):
        diffs.append({"slide": 0, "was": f"{len(old)} slides", "now": f"{len(new)} slides"})
    return diffs


def deep_cut_now(db: Session, fact: Dict[str, Any]) -> Optional[str]:
    """The same stat for the same player with today's data: its sentence, or None if it no longer clears the bar."""
    from services.ig_posts import deep_cut as D

    dc = fact.get("deep_cut") or {}
    probe = next((p for p in D.PROBES if p.id == dc.get("probe")), None)
    if not probe:
        return None
    people, scope, label = D.subjects_for(db, fact)
    for role, name, display in people:
        if dc.get("subject") not in (name, display):
            continue
        for r in ([role] if role else ["batter", "bowler"]):
            for c in D.candidates(db, r, name, scope, label, probes=[probe], display=display):
                return c.sentence
    return None


def rebuild(db: Session, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The post as its builder makes it today, or None if this kind isn't rebuilt (a play-along's puzzle is history)."""
    from services import ig_backlog
    from services.ig_plan import _kind

    fact, key, day = dict(row["facts"] or {}), row["angle_key"].removeprefix("ig:"), row["planned_for"]
    kind = _kind(row)
    post = None
    if kind == "preview":
        from services.ig_posts.match import series_label

        f = fact.get("fixture") or {}
        label = series_label(db, f["team1"], f["team2"], f.get("format") or "T20", day, f["venue"])
        built = ig_backlog.preview_post(db, f["venue"], f["team1"], f["team2"], None, day, label,
                                        f.get("team1_short"), f.get("team2_short"), f.get("format") or "T20")
        post = built if built.get("status") == "resolved" else None
    elif kind == "recap" and fact.get("match_id"):
        post = ig_backlog.recap_pack(db, fact["match_id"])
    elif kind == "spotlight":
        from services.ig_posts import spotlight

        spec = spotlight.SPECS.get(fact.get("spec") or "") or next(
            (s for s in spotlight.SPECS.values() if s.get("key") == key), None)
        post = spotlight.make_post(db, spec) if spec else None
    elif fact.get("trending") or (kind == "trend"):
        post = _trend(db, fact, key)
    elif fact.get("question"):
        post = _debate(db, fact)
    elif any(i["key"] == key for i in ig_backlog.IDEAS):
        item = next(i for i in ig_backlog.IDEAS if i["key"] == key)
        result = ig_backlog.make(db, item)
        if result.get("status") == "resolved":
            post = {"pillar": item["pillar"], "fact": result["fact"], "snapshot_id": (result.get("snapshot") or {}).get("id"),
                    "warnings": result.get("warnings") or [], "players": ig_backlog._players_of(item, result["fact"]),
                    "caption": result.get("caption")}
    else:
        return None
    if post:
        post["key"] = key
    return post


def _entry(db, question, angle_ids, fact):
    from services.ig_posts import angles as A
    from services.ig_posts.context import QuestionContext
    from services.ig_posts.questions import contested

    ctx = QuestionContext(db=db, role=question.role, fmt=question.fmt, params=question.params,
                          min_balls=question.min_balls, subject=question.subject)
    angles = [A.by_id(question.role, a) for a in angle_ids]
    return {"question": question, "ctx": ctx, "contest": contested(ctx, angles), "appeal": fact.get("appeal"),
            "appeal_by": fact.get("appeal_by"),
            "plan": {"angles": angles, "scores": fact.get("angle_scores") or {}, "by": fact.get("angles_by") or "stored"}}


def _debate(db, fact):
    from services import ig_backlog
    from services.ig_posts.questions import candidates

    q = next((c for c in candidates() if c.key == fact["question"]), None)
    return ig_backlog.debate_post(db, _entry(db, q, fact.get("angles") or [], fact)) if q else None


def _trend(db, fact, key):
    from services import ig_backlog
    from services.ig_posts import trends

    title = fact.get("title") or ""
    scope = "odiwc" if "ODIs" in title else "t20i23" if "T20Is" in title else "ipl23" if "IPL" in title else None
    role = "bowler" if "bowlers" in (fact.get("method") or "") else "batter"
    e = trends.entry_for(db, fact.get("subject"), role, fact.get("headlines") or [], scope_key=scope, log=lambda m: None)
    if not e:
        return None
    e = {**e, **_entry(db, e["question"], fact.get("angles") or [], fact)}
    return ig_backlog.trend_post(db, e, key, fact.get("headlines") or [])


def _stamp(db, pack_id: int, check: Dict[str, Any]) -> None:
    from database import engine

    with engine.begin() as conn:
        conn.execute(text("UPDATE content_packs SET facts = jsonb_set(COALESCE(facts, '{}'::jsonb), '{check}', CAST(:c AS jsonb)) WHERE id = :i"),
                     {"c": json.dumps(check, default=str), "i": pack_id})


def check_today(db: Session, today: date, base: Optional[str] = None, write: bool = True) -> List[Dict[str, Any]]:
    from database import engine
    from services import ig_backlog, ig_notes, ig_slides

    rows = [dict(r) for r in db.execute(text("""
        SELECT id, angle_key, source, pillar, title, status, planned_for, post_by, caption, facts FROM content_packs
        WHERE channel = 'instagram' AND status = 'ready' AND planned_for = :d ORDER BY id
    """), {"d": today}).mappings()]
    out = []
    for row in rows:
        fact = dict(row["facts"] or {})
        at = datetime.now(timezone.utc).isoformat(timespec="minutes")
        try:
            with _no_saves() as captured:
                fresh = rebuild(db, row)
            if fresh is None:
                result = {"status": "static", "diffs": []}
            else:
                old = db.execute(text("SELECT data FROM chart_snapshots WHERE id = :i"), {"i": fact.get("carousel_id")}).scalar() or {}
                diffs = compare(old.get("slides") or [], captured["slides"])
                dc = fact.get("deep_cut") or {}
                if dc and dc.get("by") != "spotlight":
                    now = deep_cut_now(db, fact)
                    if now != dc.get("sentence"):
                        diffs.append({"slide": 0, "was": f"The deeper cut: {dc.get('sentence')}",
                                      "now": f"The deeper cut: {now}" if now else "the deeper cut no longer clears the bar"})
                result = {"status": "changed" if diffs else "ok", "diffs": diffs, "compared": len(captured["slides"])}
                if not captured["slides"]:  # nothing to compare against: say so rather than call it fine
                    result = {"status": "failed", "diffs": [], "error": "the rebuild made no carousel to compare"}
            if result["status"] == "changed" and write:
                post = rebuild(db, row)  # for real this time
                if post:
                    for k in KEEP:
                        if k in fact and k not in post["fact"]:
                            post["fact"][k] = fact[k]
                    if not post["fact"].get("deep_cut"):  # a spotlight brings its own
                        ig_backlog.add_deep_cut(db, post, today)
                    post["fact"]["check"] = {"at": at, "status": "rebuilt", "diffs": result["diffs"]}
                    with engine.begin() as conn:
                        ig_backlog.upsert_pack(conn, post, today, source=row["source"], post_by=row["post_by"])
                    f = post["fact"]
                    ig_slides.render(f["carousel_id"], f["slides"], *([base] if base else []))
                    ig_slides.reel_from_stored(f["carousel_id"], f["slides"])
                    result["status"] = "rebuilt"
            if result["status"] != "rebuilt" and write:
                _stamp(db, row["id"], {"at": at, **result})
        except Exception as exc:  # pragma: no cover - one post never stops the others
            logger.exception("check of %s failed", row["angle_key"])
            db.rollback()
            result = {"status": "failed", "diffs": [], "error": str(exc)[:200]}
            if write:
                _stamp(db, row["id"], {"at": at, **result})
        out.append({"key": row["angle_key"], **result})
    if write and any(r["status"] == "rebuilt" for r in out):
        ig_notes.extras_pending(db)  # X thread and YouTube copy for the rebuilt posts
    return out

