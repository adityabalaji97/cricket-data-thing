"""
Rebuild player_identity (services/player_identity.py): every ESPNcricinfo id's display name.

    python scripts/build_player_identity.py             # rebuild
    python scripts/build_player_identity.py --review    # and print the namesakes with the most balls
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", action="store_true")
    args = parser.parse_args()
    from database import get_session
    from services import player_identity as P

    db = next(get_session())
    print(P.build(db))
    if args.review:
        last = None
        for r in P.namesakes(db, 80):
            if r["name"] != last:
                print(f"\n{r['name']}")
                last = r["name"]
            print(f"  {r['display_name']:<40} id {r['pid']:<9} {r['main_side'] or '':<28} {r['balls']:>7} balls "
                  f"{r['first_date']}..{r['last_date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
