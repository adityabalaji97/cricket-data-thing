"""
One-off (Oct 2026): rebuild the queued ODI posts for the new window, ODIs since the 2023 World Cup
(services/ig_posts/questions.ODI_SINCE), instead of since 2019.

    python scripts/odi_window_rebuild.py            # say what it would rebuild
    python scripts/odi_window_rebuild.py --write    # rebuild; then render where Chrome is (build_ig_backlog --render-pending)

- Ready ODI debate posts (debate-odi19-*) are remade as debate-odiwc-* on the same day; the old ones expire and
  their unpublished draft notes are marked rejected (new drafts come with the new posts).
- Ready ODI trend debates (on a day or the bench) are remade in place, in the ODI scope, keeping their headlines.
Each gets its deeper cut; X threads, YouTube copy and notes are remade by ig_notes.extras_pending.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine, get_session
    from services import ig_backlog, ig_captions, ig_carousel, ig_notes
    from services.ig_posts import post as P, trends

    db = next(get_session())
    debates = db.execute(text("""
        SELECT id, angle_key, planned_for, facts FROM content_packs
        WHERE channel = 'instagram' AND status = 'ready' AND angle_key LIKE 'ig:debate-odi19-%'
    """)).mappings().all()
    trend_rows = db.execute(text("""
        SELECT id, angle_key, planned_for, facts, title FROM content_packs
        WHERE channel = 'instagram' AND status = 'ready' AND source = 'ig-trend' AND title LIKE '%in ODIs since 2019%'
    """)).mappings().all()
    print(f"ODI debates: {[r['angle_key'] for r in debates]}\nODI trend debates: {[r['angle_key'] for r in trend_rows]}")
    if not args.write:
        print("dry run: nothing rebuilt")
        return 0

    # Debates: the same questions in the new scope, on the same days.
    day_of = {r["angle_key"].replace("ig:debate-odi19-", "odiwc-"): r for r in debates}
    for post in ig_backlog.debate_posts(db, only=list(day_of), limit=len(day_of) or 1):
        old = day_of.get(post["key"].removeprefix("debate-"))
        if not old:
            continue
        ig_backlog.add_deep_cut(db, post, old["planned_for"])
        with engine.begin() as conn:
            ig_backlog.upsert_pack(conn, post, old["planned_for"])
            conn.execute(text("UPDATE content_packs SET status = 'expired' WHERE id = :i"), {"i": old["id"]})
            note = (old["facts"] or {}).get("note_id")
            if note:
                conn.execute(text("UPDATE notes SET status = 'rejected' WHERE id = :n AND status = 'draft'"), {"n": note})
        print(f"  {old['angle_key']} -> ig:{post['key']} on {old['planned_for']}: {post['fact']['verdict']}")

    # Trend debates: the same player, the ODI scope, the same key and day (or bench).
    for r in trend_rows:
        old = dict(r["facts"] or {})
        name = old.get("subject")
        role = "bowler" if "bowlers" in (old.get("method") or "") else "batter"
        e = trends.entry_for(db, name, role, old.get("headlines") or [], scope_key="odiwc")
        if not e:
            print(f"  {r['angle_key']}: {name} doesn't qualify for the ODI field since the World Cup; left as is")
            continue
        e["appeal"], e["appeal_by"] = old.get("appeal") or 0, old.get("appeal_by") or "kept"
        built = P.build(e)
        if not built:
            print(f"  {r['angle_key']}: too few cards; left as is")
            continue
        q = e["question"]
        carousel = ig_carousel.save(db, built["slides"], q.text, {"trend": q.key, "rebuilt": "odiwc"}, "ig-trend")
        plan = e["plan"]
        fact = {"kind": "debate", "trending": True, "subject": name, "title": q.text, "verdict": built["verdict"],
                "headlines": old.get("headlines") or [], "leaders": built["leaders"], "angles": [a.id for a in plan["angles"]],
                "angle_scores": plan["scores"], "angles_by": plan["by"], "appeal": e["appeal"], "appeal_by": e["appeal_by"],
                "method": built["method"], "carousel_id": carousel["id"], "slides": len(built["slides"]), "render": True}
        post = {"key": r["angle_key"].removeprefix("ig:"), "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"],
                "warnings": [], "players": [name],
                "caption": ig_captions.build(q.text, built["verdict"], "debate", built["method"],
                                             [name, *built["players"]], q.kicker)}
        ig_backlog.add_deep_cut(db, post, r["planned_for"])
        with engine.begin() as conn:
            ig_backlog.upsert_pack(conn, post, r["planned_for"], source="ig-trend")
            conn.execute(text("UPDATE content_packs SET title = :t WHERE id = :i"), {"t": q.text, "i": r["id"]})
        print(f"  {r['angle_key']} ({r['planned_for'] or 'bench'}): {q.text} -> {built['verdict']}")
    print(f"X, YouTube and notes: {ig_notes.extras_pending(db)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
