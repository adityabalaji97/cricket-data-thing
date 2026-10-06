"""
Line up the Instagram backlog (services/ig_backlog.py): make every curated idea, schedule ~30 days, queue the posts.

    python scripts/build_ig_backlog.py --start 2026-10-12              # dry run: print the calendar, save nothing
    python scripts/build_ig_backlog.py --start 2026-10-12 --write      # save the charts and queue the packs
    python scripts/build_ig_backlog.py --start 2026-10-12 --only odi-pull-sixes --only ipl-fastest-1000-balls

The dry run reads the database only (a read-only session) and stubs out chart saving, so it is safe on production.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=date.today().isoformat(), help="first day of the calendar (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--write", action="store_true", help="save chart snapshots and queue the packs")
    parser.add_argument("--only", action="append", help="build only these idea keys (debate posts: debate-<question key>)")
    parser.add_argument("--base", default=None, help="site that renders /ig/<id>/<n> (default: hindsightcricket.com)")
    parser.add_argument("--no-render", action="store_true", help="queue without rendering the debate carousels")
    parser.add_argument("--refresh", action="append", help="remake these queued posts in place (keeps their day)")
    parser.add_argument("--render-pending", action="store_true", help="render queued carousels missing slides, then stop")
    parser.add_argument("--reels-pending", action="store_true", help="make reels for queued carousels without one, then stop")
    parser.add_argument("--extras-pending", action="store_true", help="draft notes + YouTube copy for posts lacking them")
    args = parser.parse_args()

    from services import ig_backlog

    start = date.fromisoformat(args.start)
    if args.extras_pending:
        from database import get_session
        from services import ig_notes

        print(f"notes and YouTube copy: {ig_notes.extras_pending(next(get_session()))}")
        return 0
    if args.reels_pending:
        r = ig_backlog.reels_pending()
        print(f"reels made {r['made']}, still missing {r['missing']}")
        return 0
    if args.render_pending:
        r = ig_backlog.render_pending(args.base)
        print(f"rendered {r['rendered']}" + (f"; failed: {r['failed']}" if r["failed"] else ""))
        return 0
    if args.refresh:
        from database import get_session

        db = next(get_session())
        posts = ig_backlog.refresh(db, args.refresh)
        rendered = ig_backlog.render_carousels(posts, args.base)
        print(f"refreshed {[p['key'] for p in posts]}; rendered {rendered['rendered']}"
              + (f"; failed: {rendered['failed']}" if rendered["failed"] else ""))
        return 0
    if args.write:
        from database import get_session

        db = next(get_session())
        result = ig_backlog.build(db, start, args.days, write=True, only=args.only)
        from services import ig_notes

        print(f"notes and YouTube copy: {ig_notes.extras_pending(db)}")
        if not args.no_render:
            posts = [e["post"] for e in result["calendar"] if e["post"]] + result["bench"]
            rendered = ig_backlog.render_carousels(posts, args.base)
            print(f"rendered {rendered['rendered']} carousels" + (f"; failed: {rendered['failed']}" if rendered["failed"] else ""))
    else:
        import services.snapshots as snapshots
        from analysis.hypotheses.common import read_only_session

        stub = {}

        def fake_snapshot(db, kind, data, title, key, created_by):
            sid = f"dry{len(stub):06d}"
            stub[sid] = data
            return {"id": sid, "kind": kind, "title": title, "data": data}

        snapshots.create_static_snapshot = fake_snapshot
        with read_only_session() as db:
            result = ig_backlog.build(db, start, args.days, write=False, only=args.only)

    # print, not log: importing database reconfigures logging.
    print(f"\nCalendar from {start} ({args.days} days)\n")
    for e in result["calendar"]:
        post = e["post"]
        label = post["fact"]["title"] if post else ("(open: games)" if e["pillar"] == "play" else
                                                    "(open: on the day, bench if nothing trends)" if e["pillar"] == "reactive"
                                                    else "(open: nothing left that keeps the spread)")
        warn = f"  !! {'; '.join(post['warnings'])}" if post and post["warnings"] else ""
        print(f"{e['date']:%a %d %b}  {e['pillar']:<8} {label[:110]}{warn}")
    print(f"\nBench ({len(result['bench'])}):")
    for b in result["bench"]:
        print(f"  {b['pillar']:<7} {b['key']:<26} {b['fact']['title'][:90]}")
    if result["failed"]:
        print(f"\nFailed ({len(result['failed'])}):")
        for f in result["failed"]:
            print(f"  {f['key']:<26} {f['status']}: {(f['note'] or '')[:120]}")
    players = Counter(p for e in result["calendar"] if e["post"] for p in e["post"]["players"])
    print(f"\nPlayers in the calendar: {dict(players.most_common(8))}")
    print("written" if args.write else "dry run: nothing saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
