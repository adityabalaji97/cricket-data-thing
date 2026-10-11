"""
A one-off record post (services/ig_posts/records.py) with the deeper cut and the record holder's profile.

    python scripts/make_record_post.py --idea "Fastest to 2000 T20I runs" --expect "Abhishek Sharma"   # print, save nothing
    python scripts/make_record_post.py --idea "Fastest to 2000 T20I runs" --expect "Abhishek Sharma" \\
        --key spotlight-abhishek-2000-t20i --date 2026-10-12 --write [--no-render] [--base URL]

--expect: make the post only when that player leads the race by balls (exit 2 otherwise: the data hasn't caught up).
A key starting "spotlight-" goes out at 6 pm and is never moved by the nightly reorder. With --write: the carousel, the
queued pack, the slides rendered from --base (the live site by default) and the Reel; then the X thread and YouTube copy.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--idea", required=True)
    parser.add_argument("--expect")
    parser.add_argument("--key")
    parser.add_argument("--date", default=str(date.today() + timedelta(days=1)))
    parser.add_argument("--shallow", action="store_true", help="the plain record post, without the profile")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--base", default="https://hindsightcricket.com")
    args = parser.parse_args()

    from scripts.make_spotlight import show
    from services import ig_backlog

    from database import engine, get_session

    db = next(get_session())
    if not args.write:
        from services.ig_posts import records

        built = records.build(db, args.idea, deep=not args.shallow, expect=args.expect)
        if not built:
            print(f"no post: {args.expect or 'the race'} doesn't lead yet (or the race can't be built)")
            return 2
        print(built["hook"])
        show({"slides": [{"type": "card", "card": c} for c in built["cards"]]})
        print("\ndry run: nothing saved (the carousel is saved only with --write)")
        return 0

    if not args.key:
        print("--key is required with --write")
        return 1
    post = ig_backlog.record_post(db, args.key, args.idea, deep=not args.shallow, expect=args.expect)
    if not post:
        print(f"no post: {args.expect or 'the race'} doesn't lead yet (or the race can't be built)")
        return 2
    from services import ig_notes, ig_slides

    day = date.fromisoformat(args.date)
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, day, source="ig-record")
    fact = post["fact"]
    print(f"queued {args.key} for {day}: carousel {fact['carousel_id']}, {fact['slides']} slides")
    if not args.no_render:
        r = ig_slides.render(fact["carousel_id"], fact["slides"], args.base)
        print(f"rendered {len(r['ok'])}/{fact['slides']}" + (f", failed {r['failed']}" if r["failed"] else ""))
        print(f"reel: {ig_slides.reel_from_stored(fact['carousel_id'], fact['slides'])}s")
    print(f"X and YouTube copy: {ig_notes.extras_pending(db)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
