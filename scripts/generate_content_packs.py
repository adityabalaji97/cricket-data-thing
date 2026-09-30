"""
Generate content packs for newly loaded matches (services/content_packs.py).

    python scripts/generate_content_packs.py                 # last 10 days, matches without packs
    python scripts/generate_content_packs.py --days 3 --dry-run
    python scripts/generate_content_packs.py --match 1525655 --match 1496589

Runs nightly after the load (refresh-delivery-details.yml). Packs land as 'ready' in the admin
"Social" tab; ready packs past their post-by deadline are marked expired.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_session  # noqa: E402
from services.content_packs import generate  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--match", action="append", dest="matches")
    parser.add_argument("--per-match", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = next(get_session())
    summary = generate(db, days=args.days, match_ids=args.matches, per_match=args.per_match, dry_run=args.dry_run)
    print(f"matches scanned: {summary['matches']} | packs: {len(summary['packs'])} | "
          f"refused: {len(summary['refused'])} | expired: {summary['expired']}")
    for p in summary["packs"]:
        flag = " (already queued)" if p.get("duplicate") else ""
        print(f"  + {p['title']}{flag}")
        for w in p.get("rule_warnings") or []:
            print(f"      warning: {w}")
    for p in summary["refused"]:
        print(f"  - refused: {p['title']} -- {'; '.join(p['refused'])}")


if __name__ == "__main__":
    main()
