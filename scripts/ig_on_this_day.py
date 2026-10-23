"""
Queue the On this day post (services/on_this_day.py) for the next days: the best past match on each calendar day,
as a carousel planned for that day (9 am IST, services/ig_plan.TIMES), with its slides rendered.

    python scripts/ig_on_this_day.py                    # tomorrow (IST), queued and rendered
    python scripts/ig_on_this_day.py --date 2026-10-16 --dry-run
    python scripts/ig_on_this_day.py --days 3 --base http://localhost:3000

A day already queued is left alone (--force remakes it, unless posted). The best story on the day goes out, whatever
ran the day before. The post is news only on its day: post_by is the end of that day in IST.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, time, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

IST = timezone(timedelta(hours=5, minutes=30))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="first day (YYYY-MM-DD); default tomorrow in IST")
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--base", default=None, help="site to render the slides from (default: the live site)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine, get_session
    from services import ig_backlog, ig_slides

    db = next(get_session())
    start = date.fromisoformat(args.date) if args.date else datetime.now(IST).date() + timedelta(days=1)
    made = 0
    for i in range(args.days):
        day = start + timedelta(days=i)
        key = f"ig:otd-{day.isoformat()}"
        row = db.execute(text("SELECT status FROM content_packs WHERE angle_key = :k"), {"k": key}).first()
        if row and (not args.force or row[0] == "posted"):
            print(f"{key}: already queued ({row[0]})")
            continue
        if args.dry_run:
            from services.on_this_day import candidates

            for c in candidates(db, day)[:5]:
                print(f"  {c['score']:.2f} {c['date']} {c['key']} {c['team1']} v {c['team2']} "
                      f"({c['angle']} {c['signals']}; world cup {c['world_cup']}, rivalry {c['rivalry']})")
            continue
        post = ig_backlog.otd_pack(db, day)
        if not post:
            print(f"{key}: no match with Impact on this day")
            continue
        post_by = datetime.combine(day, time(23, 59), IST).astimezone(timezone.utc)
        with engine.begin() as conn:
            ig_backlog.upsert_pack(conn, post, day, source="ig-otd", post_by=post_by)
        result = ig_slides.render(post["fact"]["carousel_id"], post["fact"]["slides"], *([args.base] if args.base else []))
        print(f"queued {key}: {post['fact']['title']} ({post['fact']['competition']}); rendered "
              f"{len(result['ok'])}/{post['fact']['slides']}" + (f", failed {result['failed']}" if result["failed"] else ""))
        made += 1
    if made:
        from services import ig_notes

        print(f"notes and YouTube copy: {ig_notes.extras_pending(db)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
