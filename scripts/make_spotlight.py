"""
A player spotlight post (services/ig_posts/spotlight.py) from a named spec.

    python scripts/make_spotlight.py --spec bhuvi                       # print every slide and table, save nothing
    python scripts/make_spotlight.py --spec bhuvi --date 2026-10-09 --write [--no-render]

With --write: the carousel, "The deeper cut" (slide 3), the queued pack, the slides rendered from the live site (--base)
and the Reel; then the X thread and YouTube copy (services/ig_notes.extras_pending). Rendering needs Chrome and ffmpeg.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def show(built) -> None:
    for i, s in enumerate(built["slides"], 1):
        c = s.get("card")
        print(f"\n{i}. [{s['type']}{' ' + c['visual'] if c else ''}] {c['title'] if c else s.get('text') or s.get('heading')}")
        if not c:
            continue
        print(f"   {c.get('help') or ''} | {c['sample']}")
        pl = c["payload"]
        if c["visual"] == "scorecard":
            cols = [m["key"] for m in pl["metrics"]]
            print("   " + " " * 14 + "".join(f"{k:>8}" for k in cols))
            for r in pl["rows"]:
                vals = "".join(f"{'-' if r['values'][k] is None else format(r['values'][k], '+.2f'):>8}" for k in cols)
                print(f"   {('*' if r['highlight'] else ' ') + r['short']:<14}{vals}")
        elif c["visual"] == "metric_bars":
            for r in pl["rows"]:
                print(f"   {'*' if r.get('highlight') else ' '}{r['name']:<14}{r['value']:6.2f}  {r.get('detail') or ''}")
        elif c["visual"] == "deep_compare":
            for r in pl["rows"]:
                print(f"   {'*' if r.get('highlight') else ' '}{r['label']:<14}{r['subject']:6.2f} v {r['field']:.2f}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--date", default=str(date.today() + timedelta(days=1)))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--base", default="https://hindsightcricket.com")
    args = parser.parse_args()

    from services.ig_posts import spotlight

    spec = spotlight.SPECS[args.spec]
    if not args.write:
        from analysis.hypotheses.common import read_only_session

        with read_only_session() as db:
            built = spotlight.build(db, spec)
        if not built:
            print("not enough data for a post")
            return 1
        show(built)
        print("\ndry run: nothing saved")
        return 0

    from database import engine, get_session
    from services import ig_backlog, ig_captions, ig_carousel, ig_notes, ig_slides

    db = next(get_session())
    built = spotlight.build(db, spec)
    if not built:
        print("not enough data for a post")
        return 1
    show(built)
    day = date.fromisoformat(args.date)
    carousel = ig_carousel.save(db, built["slides"], built["title"], {"spotlight": spec["key"]}, "ig-spotlight")
    fact = {"kind": "spotlight", "subject": spec["player"], "subject_role": spec["role"], "title": built["title"],
            "verdict": built["verdict"], "kicker": spec["kicker"], "carousel_id": carousel["id"],
            "slides": len(built["slides"]), "render": True}
    for k in ("deep_cut_scope", "deep_cut_exclude"):
        if spec.get(k):
            fact[k] = spec[k]
    caption = ig_captions.build(built["title"], built["verdict"], "debate",
                                spec.get("method") or "Impact and runs saved are computed ball by ball (T20 Primer method), on every T20 each bowler played.",
                                [spec["player"]], spec["kicker"], spec.get("tags", []))
    post = {"key": spec["key"], "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "caption": caption, "players": [spec["player"]]}
    if built.get("deep_cut"):  # the spotlight's own (slide 3): the generic one is skipped
        fact["deep_cut"] = built["deep_cut"]
        post["caption"] = ig_captions.with_deep_cut(post["caption"], built["deep_cut"]["sentence"])
        got = built["deep_cut"]
    else:
        got = ig_backlog.add_deep_cut(db, post, day)
    print(f"\ndeeper cut: {got['sentence'] if got else 'none'} (by {got['by'] if got else '-'})")
    with engine.begin() as conn:
        ig_backlog.upsert_pack(conn, post, day, source="ig-spotlight")
    print(f"queued {spec['key']} for {day}: carousel {fact['carousel_id']}, {fact['slides']} slides")
    if not args.no_render:
        r = ig_slides.render(fact["carousel_id"], fact["slides"], args.base)
        print(f"rendered {len(r['ok'])}/{fact['slides']}" + (f", failed {r['failed']}" if r["failed"] else ""))
        print(f"reel: {ig_slides.reel_from_stored(fact['carousel_id'], fact['slides'])}s")
    print(f"X and YouTube copy: {ig_notes.extras_pending(db)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
