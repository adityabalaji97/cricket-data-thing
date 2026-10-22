"""
Headlines for the next few days' big fixtures into fixture_news (services/preview_news.py, storylines chunk 1).

    python scripts/fetch_fixture_news.py --dry-run     # print each fixture's headlines, save nothing
    python scripts/fetch_fixture_news.py               # store them (DATABASE_URL decides which database)
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from services import preview_news as N

    fxs = N.fixtures(args.days)
    print(f"{len(fxs)} big fixtures in the next {args.days} days")
    general = N.general_feeds() if fxs else {}
    total = 0
    for fx in fxs:
        items = N.fetch(fx, general)
        print(f"\n{N.fixture_key(fx)} · {fx.get('series') or ''} · {len(items)} headlines")
        for it in items[:12]:
            when = it["published_at"].strftime("%d %b %H:%M") if it["published_at"] else "?"
            print(f"  [{when}] {it['title']} — {it['outlet'] or it['source']}")
        if not args.dry_run and items:
            from database import engine

            with engine.begin() as conn:
                new = N.store(conn, fx, items)
            total += new
            print(f"  stored ({new} new)")
    print("\ndry run: nothing saved" if args.dry_run else f"\n{total} new headlines stored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
