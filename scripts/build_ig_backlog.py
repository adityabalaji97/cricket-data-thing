"""
Line up the Instagram backlog (services/ig_backlog.py): make every curated idea, schedule ~30 days, queue the posts.

    python scripts/build_ig_backlog.py --start 2026-10-12              # dry run: print the calendar, save nothing
    python scripts/build_ig_backlog.py --start 2026-10-12 --write      # save the charts and queue the packs
    python scripts/build_ig_backlog.py --start 2026-10-12 --only odi-pull-sixes --only ipl-fastest-1000-balls
    python scripts/build_ig_backlog.py --retitle-deep-cuts 3          # the next 3 days' deeper cuts: short claim

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
    parser.add_argument("--bench-unposted", action="store_true", help="unposted evergreen posts from past days to the bench")
    parser.add_argument("--reorder", action="store_true", help="re-date queued evergreen posts by the format that's on")
    parser.add_argument("--dry-run", action="store_true", help="with --bench-unposted / --reorder: say, don't move")
    parser.add_argument("--retitle-deep-cuts", type=int, metavar="DAYS", default=None,
                        help="give posts planned in the next DAYS days their deeper cut's short claim, and re-render")
    parser.add_argument("--retitle", action="append", help="the same for these queued posts (angle keys, any day)")
    parser.add_argument("--rebuild-breaking", type=int, metavar="DAYS", default=None,
                        help="rebuild posts planned in the next DAYS days (0: the bench) that break a rule their "
                             "builder now follows, and re-render")
    parser.add_argument("--rebuild", action="append", help="rebuild these queued posts (angle keys), and re-render")
    args = parser.parse_args()

    from services import ig_backlog

    start = date.fromisoformat(args.start)
    if args.bench_unposted or args.reorder:
        from datetime import datetime, timedelta as _td, timezone

        from database import get_session

        db = next(get_session())
        today = datetime.now(timezone(_td(hours=5, minutes=30))).date()  # the queue's days are India's
        if args.bench_unposted:
            moved = ig_backlog.bench_unposted(db, today, dry_run=args.dry_run)
            print(f"to the bench: {moved or 'none'}")
        if args.reorder:
            # From tomorrow: today's posts may already be out.
            for key, old, new in ig_backlog.reorder(db, today + _td(days=1), args.days, dry_run=args.dry_run):
                print(f"  {key}: {old} -> {new}")
        print("dry run: nothing moved" if args.dry_run else "done")
        return 0
    if args.rebuild_breaking is not None or args.rebuild:
        # A post built before its builder followed a rule (services/social_rules: lint, and the render's layout
        # findings) is remade through the builder as it is now, on the same day, and re-rendered with its Reel.
        from datetime import datetime, timedelta as _td, timezone

        from sqlalchemy import text

        from database import get_session
        from services import ig_slides
        from services.social_rules import findings

        db = next(get_session())
        keys = list(args.rebuild or [])
        if args.rebuild_breaking is not None:
            today = datetime.now(timezone(_td(hours=5, minutes=30))).date()
            where = ("p.planned_for IS NULL" if args.rebuild_breaking == 0
                     else "p.planned_for BETWEEN :a AND :b")
            for key, kind, layout, data in db.execute(text(f"""
                SELECT p.angle_key, p.facts->>'kind', p.facts->'layout', s.data FROM content_packs p
                JOIN chart_snapshots s ON s.id = p.facts->>'carousel_id'
                WHERE p.channel = 'instagram' AND p.status = 'ready' AND {where} ORDER BY p.planned_for, p.id
            """), {"a": today, "b": today + _td(days=args.rebuild_breaking)}).all():
                rules = {f["rule"] for f in findings(((data or {}).get("slides")) or [], kind)} | {
                    f["rule"] for f in layout or []}
                if rules & set(ig_backlog.REBUILD_RULES):
                    keys.append(key)
        for key in keys:
            got = ig_backlog.rebuild(db, key)
            line = f"  {key}: {got['status']}"
            if got["status"] == "rebuilt":
                r = ig_slides.render(got["carousel_id"], got["slides"], *([args.base] if args.base else []))
                line += f"; rendered {len(r['ok'])}/{got['slides']}" + (f", failed {r['failed']}" if r["failed"] else "")
                line += f"; Reel {r.get('reel')}s" if r.get("reel") else ""
            print(line, flush=True)
        return 0
    if args.retitle_deep_cuts is not None or args.retitle:
        # Posts made before the deeper cut wrote its own short claim (23 Oct 2026) still carry the sentence as the
        # card title; the nightly run fixes each as it comes up, re-rendered (its Reel remade with the slides).
        from datetime import datetime, timedelta as _td, timezone

        from sqlalchemy import text

        from database import get_session
        from services import ig_slides

        db = next(get_session())
        keys = list(args.retitle or [])
        if args.retitle_deep_cuts is not None:
            today = datetime.now(timezone(_td(hours=5, minutes=30))).date()
            keys += [r[0] for r in db.execute(text("""
                SELECT angle_key FROM content_packs
                WHERE channel = 'instagram' AND status = 'ready' AND facts->'deep_cut' IS NOT NULL
                  AND planned_for BETWEEN :a AND :b ORDER BY planned_for, id
            """), {"a": today, "b": today + _td(days=args.retitle_deep_cuts)}).all()]
        for key in keys:
            got = ig_backlog.retitle_deep_cut(db, key)
            line = f"  {key}: {got['status']}"
            if got["status"] == "retitled":
                r = ig_slides.render(got["carousel_id"], got["slides"], *([args.base] if args.base else []))
                line += f" ({got['title']}); rendered {len(r['ok'])}/{got['slides']}" + (f", failed {r['failed']}" if r["failed"] else "")
                line += f"; Reel {r.get('reel')}s" if r.get("reel") else ""  # render() makes the post's Reel
            print(line, flush=True)
        return 0
    if args.extras_pending:
        from database import get_session
        from services import ig_notes

        print(f"notes and YouTube copy: {ig_notes.extras_pending(next(get_session()))}")
        return 0
    if args.reels_pending:
        r = ig_backlog.reels_pending()
        print(f"reels made {r['made']}, still missing {r['missing']}; voiced in place of a slideshow {r['voiced']}"
              + (f", still unvoiced {r['unvoiced']}" if r["unvoiced"] else ""))
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
