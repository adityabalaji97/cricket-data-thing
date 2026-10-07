"""
Add "The deeper cut" (services/ig_posts/deep_cut.py) to every ready Instagram post that doesn't have one, in queue
order (so the variety and no-repeat rules see the posts before it). Posted, skipped and expired posts are left alone.

    python scripts/deep_cut_backfill.py            # say what it would do, change nothing
    python scripts/deep_cut_backfill.py --write    # new carousels, facts and captions; X and YouTube copy remade

Slides and reels are rendered separately, where Chrome and ffmpeg are (python scripts/build_ig_backlog.py
--render-pending, then --reels-pending): the new carousels have none yet.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine, get_session
    from services import ig_backlog, ig_notes

    if not args.write:  # carousels commit on their own connection: a dry run saves none
        import services.snapshots as snapshots

        snapshots.create_static_snapshot = lambda db, kind, data, title, key, created_by: {"id": "dry-run", "kind": kind}
    db = next(get_session())
    rows = db.execute(text("""
        SELECT id, angle_key, planned_for, pillar, snapshot_id, caption, rule_warnings, facts FROM content_packs
        WHERE channel = 'instagram' AND status = 'ready' AND facts->>'carousel_id' IS NOT NULL
        ORDER BY planned_for NULLS LAST, id
    """)).mappings().all()
    done = db.execute(text("""
        SELECT facts->'deep_cut'->>'subject', facts->'deep_cut'->>'probe' FROM content_packs
        WHERE channel = 'instagram' AND facts->'deep_cut' IS NOT NULL
    """)).all()
    recent, used = [r[1] for r in done][-3:], {(r[0], r[1]) for r in done}
    added = skipped = 0
    for r in rows:
        fact = dict(r["facts"] or {})
        if fact.get("deep_cut"):
            continue
        post = {"key": r["angle_key"][len("ig:"):], "pillar": r["pillar"], "fact": fact, "snapshot_id": r["snapshot_id"],
                "caption": r["caption"], "warnings": r["rule_warnings"] or []}
        got = ig_backlog.add_deep_cut(db, post, r["planned_for"], recent, used)
        day = r["planned_for"] or "bench"
        if not got:
            skipped += 1
            print(f"{day} {r['angle_key']}: no deeper cut", flush=True)
            continue
        added += 1
        recent.append(got["probe"])
        used.add((got["subject"], got["probe"]))
        print(f"{day} {r['angle_key']}: [{got['probe']}] {got['sentence']} (by {got['by']}, jev {got['jev']})", flush=True)
        if args.write:
            fact.pop("x", None)
            fact.pop("youtube", None)  # remade below from the new slides and caption
            with engine.begin() as conn:
                conn.execute(text("UPDATE content_packs SET snapshot_id = :s, facts = CAST(:f AS jsonb), caption = :c WHERE id = :i"),
                             {"s": post["snapshot_id"], "f": json.dumps(fact, default=str), "c": post["caption"], "i": r["id"]})
    if args.write:
        print(f"X and YouTube copy: {ig_notes.extras_pending(db)}")
    print(f"{added} posts got a deeper cut, {skipped} none" + ("" if args.write else " (dry run: nothing saved)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
