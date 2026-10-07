"""
Trend radar (services/ig_posts/trends.py): this morning's most-talked-about players as 'Trending today' debate posts.

    python scripts/trend_radar.py              # queue the top 3 for today, render their slides
    python scripts/trend_radar.py --dry-run    # print the headlines' players and the questions, save nothing

Runs each morning (.github/workflows/ig-trend-radar.yml). A trending post is planned for today and dropped from the
queue at the end of tomorrow (post_by): yesterday's news isn't news.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, time, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=3, help="how many trending posts to queue")
    parser.add_argument("--base", default="https://hindsightcricket.com")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from database import engine, get_session
    from services import ig_backlog, ig_captions, ig_carousel, ig_slides
    from services.ig_posts import post as P, trends

    db = next(get_session())
    entries = trends.rank(trends.candidates(db, top=args.top * 2))
    # The queue's days are India's (the audience, and when the posts go out), not UTC's.
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    post_by = datetime.combine(today + timedelta(days=1), time.max, tzinfo=ist)
    queued = 0
    for e in entries[: args.top]:
        q = e["question"]
        news = "; ".join(f"{h['source']}: {h['title']}" for h in e["headlines"][:2])
        print(f"[{e['appeal']:.1f} {e['appeal_by']}] {q.text}\n    in the news: {news}")
        if args.dry_run:
            continue
        built = P.build(e)
        if not built:
            print("    not made: too few cards")
            continue
        carousel = ig_carousel.save(db, built["slides"], q.text, {"trend": q.key, "day": str(today)}, "ig-trend")
        plan = e["plan"]
        fact = {"kind": "debate", "trending": True, "subject": q.subject, "title": q.text, "verdict": built["verdict"],
                "headlines": e["headlines"], "leaders": built["leaders"], "angles": [a.id for a in plan["angles"]],
                "angle_scores": plan["scores"], "angles_by": plan["by"], "appeal": e["appeal"], "appeal_by": e["appeal_by"],
                "method": built["method"], "carousel_id": carousel["id"], "slides": len(built["slides"]), "render": True}
        post = {"key": f"{q.key}-{today}", "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"],
                "warnings": [], "players": [q.subject],
                "caption": ig_captions.build(q.text, built["verdict"], "debate", built["method"],
                                             [q.subject, *built["players"]], q.kicker)}
        ig_backlog.add_deep_cut(db, post, today)
        with engine.begin() as conn:
            ig_backlog.upsert_pack(conn, post, today, source="ig-trend", post_by=post_by)
        result = ig_slides.render(post["fact"]["carousel_id"], post["fact"]["slides"], args.base)
        print(f"    queued for today, rendered {len(result['ok'])}/{post['fact']['slides']}"
              + (f", failed {result['failed']}" if result["failed"] else ""))
        queued += 1
    if queued:
        # A render that failed (a slow browser start) gets one more go before the run ends.
        retry = ig_backlog.render_pending(args.base)
        if retry["failed"]:
            print(f"still unrendered: {retry['failed']}")
    if queued:
        from services import ig_notes

        print(f"YouTube copy: {ig_notes.extras_pending(db)}")
    print("dry run: nothing saved" if args.dry_run else f"{queued} trending posts queued")
    return 0


if __name__ == "__main__":
    sys.exit(main())
