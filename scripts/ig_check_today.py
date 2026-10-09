"""
The morning check (services/ig_check.py): today's unposted Instagram posts rebuilt with this morning's data; a post
whose numbers changed is rebuilt in place, its slides and Reel re-rendered (needs Chrome and ffmpeg).

    python scripts/ig_check_today.py --dry-run      # compare only, change nothing
    python scripts/ig_check_today.py [--day YYYY-MM-DD] [--base https://hindsightcricket.com]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", help="default: today in India")
    parser.add_argument("--base", default="https://hindsightcricket.com")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from database import get_session
    from services.ig_check import check_today

    day = date.fromisoformat(args.day) if args.day else datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
    db = next(get_session())
    results = check_today(db, day, args.base, write=not args.dry_run)
    for r in results:
        print(f"{r['status']:8} {r['key']}" + (f"  [{r['compared']} slides compared]" if r.get("compared") else "")
              + (f"  ({r.get('error')})" if r.get("error") else ""))
        for d in r["diffs"]:
            print(f"           slide {d['slide']}: {d['was']}\n                 -> {d['now']}")
    print(f"{len(results)} posts checked for {day}" + (" (dry run: nothing changed)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
