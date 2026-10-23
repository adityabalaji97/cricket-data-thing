"""
Talking points for the next few days' fixtures (services/preview_storylines.py, storylines chunk 2): one model call
per fixture, ranked, the top 5 stored 'pending' for review in the admin (/admin/storylines).

    python scripts/build_storylines.py --dry-run     # print each fixture's points, store nothing (still one model call)
    python scripts/build_storylines.py               # store them
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--fixture", help="only this fixture_key")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from database import engine, get_session
    from services import preview_storylines as S

    db = next(get_session())
    fxs = [f for f in S.fixtures_with_news(db, args.days) if not args.fixture or f["fixture_key"] == args.fixture]
    print(f"{len(fxs)} fixtures with headlines")
    for fx in fxs:
        points = S.rank(fx, S.extract(db, fx))
        print(f"\n{fx['fixture_key']} · {fx['n']} headlines · {len(points)} talking points")
        for p in points[: S.TOP]:
            print(f"  [{p['appeal']:.1f} {p['appeal_by']}] ({p['kind']}) {p['claim']}  — {', '.join(p['players'])} "
                  f"· {len(p['sources'])} headlines")
        if not args.dry_run and points:
            with engine.begin() as conn:
                print(f"  stored ({S.store(conn, fx, points)} new, pending review)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
