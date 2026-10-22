"""
Record radar (services/record_radar.py, RECORD_RADAR_PLAN.md): the day's best record moves as drafts on the bench.

    python scripts/record_radar.py --dry-run            # the latest match day: every event, the 3 picked, nothing saved
    python scripts/record_radar.py                       # queue the 3 picked on the bench (no day) and render them
    python scripts/record_radar.py --day 2026-10-22      # a given day

At most 3 a day (decision 2), on the bench, so nothing is planned until the user picks it in the admin. Runs after the
nightly load (.github/workflows/record-radar.yml); a day already done is skipped.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, time, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", help="match day (default: the latest men's T20 day loaded)")
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--base", default="https://hindsightcricket.com")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from sqlalchemy import text

    from database import engine, get_session
    from services import ig_backlog, ig_slides
    from services import record_radar as R

    db = next(get_session())
    day = date.fromisoformat(args.day) if args.day else db.execute(text(
        "SELECT MAX(date) FROM matches WHERE format = 'T20' AND gender = 'male'")).scalar()
    done = db.execute(text("""
        SELECT COUNT(*) FROM content_packs WHERE source = 'record-radar' AND facts->'event'->>'day' = :d
    """), {"d": day.isoformat()}).scalar()
    if done and not args.dry_run:
        print(f"{day}: already done ({done} drafts)")
        return 0
    picked, cubes = R.drafts_for_day(db, day, args.top)
    print(f"{day}: {len(picked)} picked")
    for e in picked:
        print(f"  [{e['score']:.2f}] {R.headline(e)}")
    if args.dry_run:
        print("dry run: nothing saved")
        return 0
    ist = timezone(timedelta(hours=5, minutes=30))
    post_by = datetime.combine(day + timedelta(days=3), time.max, tzinfo=ist)  # a record is news for a few days
    for e in picked:
        post = R.post_for(db, e, cubes["batter" if e["template"] not in ("wickets", "pp-wickets", "death-wickets") else "bowler"])
        with engine.begin() as conn:
            ig_backlog.upsert_pack(conn, post, None, source="record-radar", post_by=post_by)
        result = ig_slides.render(post["fact"]["carousel_id"], post["fact"]["slides"], args.base)
        print(f"  benched {post['key']}: rendered {len(result['ok'])}/{post['fact']['slides']}")
    if picked:
        from services import ig_notes

        print(f"YouTube / X copy: {ig_notes.extras_pending(db)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
