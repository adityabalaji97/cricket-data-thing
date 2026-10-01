"""
Record ties, Super Over winners and no-results the ball-by-ball feed left out (services/match_results.py).

    python scripts/resolve_match_results.py --all --dry-run     # every unresolved match: what would change
    python scripts/resolve_match_results.py --all               # write matches.outcome
    python scripts/resolve_match_results.py --days 30           # what the nightly sync does
    python scripts/resolve_match_results.py --match 1529281

Writes only matches.outcome, only where winner IS NULL; re-runs are no-ops.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_session  # noqa: E402
from services.match_results import resolve  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int)
    parser.add_argument("--all", action="store_true", help="every unresolved ball-by-ball match")
    parser.add_argument("--match", action="append", dest="matches")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not (args.days or args.all or args.matches):
        parser.error("pass --days N, --all or --match ID")
    out = resolve(next(get_session()), days=args.days, match_ids=args.matches, dry_run=args.dry_run)
    print(f"checked {out['checked']} | {'would update' if args.dry_run else 'updated'} "
          f"{len(out['tie_eliminator']) + len(out['tie']) + len(out['no_result'])}")
    for key, label in (("tie_eliminator", "Super Over"), ("tie", "tied"), ("no_result", "no result"),
                       ("won", "ESPN has a winner (left for review)"), ("unclear", "unclear / ESPN unavailable")):
        for line in out[key]:
            print(f"  [{label}] {line}")


if __name__ == "__main__":
    main()
