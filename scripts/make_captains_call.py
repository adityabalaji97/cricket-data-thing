"""
"The captain's call" (services/ig_posts/captains_call.py): the over that swung a chase, against the plan around it.

    python scripts/make_captains_call.py --match 1529231                    # print every slide, save nothing
    python scripts/make_captains_call.py --match 1529231 --over 17 --date 2026-10-11 --write [--no-render] [--base URL]

--over defaults to the over that moved the bowling side's win probability most. With --write: the carousel, the queued
pack (a spotlight, 6 pm), the slides rendered from --base (the live site by default) and the Reel; then the X thread and
YouTube copy. Rendering needs Chrome and ffmpeg.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match", required=True)
    parser.add_argument("--over", type=int)
    parser.add_argument("--date", default=str(date.today() + timedelta(days=1)))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--base", default="https://hindsightcricket.com")
    args = parser.parse_args()

    from scripts.make_spotlight import show
    from services.ig_posts import captains_call

    if not args.write:
        from analysis.hypotheses.common import read_only_session

        with read_only_session() as db:
            built = captains_call.post(db, args.match, args.over)
        if not built:
            print("no chase to read")
            return 1
        show(built)
        for s in built["slides"]:
            if s["type"] == "text":
                print(f"\n{s['heading']}\n{s['body']}")
        print("\ndry run: nothing saved")
        return 0

    from database import engine, get_session
    from services import ig_backlog, ig_notes, ig_slides

    db = next(get_session())
    built = captains_call.post(db, args.match, args.over)
    if not built:
        print("no chase to read")
        return 1
    show(built)
    day = date.fromisoformat(args.date)
    post = captains_call.make_post(db, args.match, args.over, built)
    fact = post["fact"]
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, day, source="ig-spotlight")
    print(f"\nqueued {post['key']} for {day}: carousel {fact['carousel_id']}, {fact['slides']} slides")
    if not args.no_render:
        r = ig_slides.render(fact["carousel_id"], fact["slides"], args.base)
        print(f"rendered {len(r['ok'])}/{fact['slides']}" + (f", failed {r['failed']}" if r["failed"] else ""))
        print(f"reel: {ig_slides.reel_from_stored(fact['carousel_id'], fact['slides'])}s")
    print(f"X and YouTube copy: {ig_notes.extras_pending(db)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
