"""
A match-day Instagram post from a fixture's preview story (services/ig_backlog.preview_post).

    python scripts/make_ig_preview.py --venue "Ekana Cricket Stadium" --team1 India --team2 "West Indies" \
        --t1 IND --t2 WI --label "1st T20I · Lucknow" --date 2026-10-06 \
        --cards par,head-to-head,key-battles,death-bowlers,suits-ground [--write]

Without --write it saves nothing (a read-only session; the cards are built but not stored) and prints the slides.
Card ids are the story's (GET /match-preview/{venue}/{t1}/{t2}/cards lists them).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--venue", required=True)
    parser.add_argument("--team1", required=True)
    parser.add_argument("--team2", required=True)
    parser.add_argument("--t1", help="short label for team 1, e.g. IND")
    parser.add_argument("--t2", help="short label for team 2")
    parser.add_argument("--format", default="T20", choices=["T20", "ODI"])
    parser.add_argument("--cards", required=True, help="comma-separated story card ids, in slide order")
    parser.add_argument("--label", required=True, help='the line above the hook, e.g. "1st T20I · Lucknow"')
    parser.add_argument("--date", required=True, help="the day it goes out (YYYY-MM-DD)")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    from services import ig_backlog

    day = date.fromisoformat(args.date)
    kwargs = dict(venue=args.venue, team1=args.team1, team2=args.team2, cards=[c.strip() for c in args.cards.split(",")],
                  day=day, label=args.label, team1_short=args.t1, team2_short=args.t2, fmt=args.format)
    if args.write:
        from database import engine, get_session

        db = next(get_session())
        post = ig_backlog.preview_post(db, **kwargs)
        if post["status"] == "resolved":
            with engine.begin() as conn:
                ig_backlog.upsert_pack(conn, post, day, source="ig-preview")
    else:
        import services.snapshots as snapshots
        from analysis.hypotheses.common import read_only_session

        def fake_create(db, kind, params, created_by="web"):
            data = snapshots._preview_card_data(db, snapshots._clean_preview_params(params))
            return {"id": f"dry-{params['card']}", "kind": kind, "title": data.get("title"), "data": data}

        snapshots.create_snapshot = fake_create
        snapshots.create_static_snapshot = lambda db, kind, data, title, key, created_by: {"id": "dry-carousel", "kind": kind,
                                                                                          "title": title, "data": data}
        with read_only_session() as db:
            post = ig_backlog.preview_post(db, **kwargs)

    # print, not log: importing database reconfigures logging.
    if post["status"] != "resolved":
        print("FAILED:", post.get("note"), post.get("warnings"))
        return 1
    print(f"\n{post['fact']['title']}  ({post['fact']['slides']} slides, carousel {post['snapshot_id']})")
    for t in post["fact"]["card_titles"]:
        print("  -", t)
    for w in post["warnings"]:
        print("  !!", w)
    print("\nCaption:\n" + post["caption"])
    print("\nwritten" if args.write else "\ndry run: nothing saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
