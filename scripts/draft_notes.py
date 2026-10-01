"""
Hindsight Bot drafts Notes (services/note_drafts.py): recaps of newly loaded matches, previews of
fixtures in the next 36 hours. Everything lands as a draft in /admin/notes.

    python scripts/draft_notes.py                      # recaps (last 10 days) + previews
    python scripts/draft_notes.py --recaps-only --days 3 --dry-run
    python scripts/draft_notes.py --match 1525655      # recap one match

Runs nightly after the content packs (refresh-delivery-details.yml), so recaps reuse the packs'
facts and charts. Re-runs are no-ops: one recap and one preview per match.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_session  # noqa: E402
from services.note_drafts import run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--match", action="append", dest="matches")
    parser.add_argument("--recaps-only", action="store_true")
    parser.add_argument("--previews-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="compose drafts and print them; write nothing")
    args = parser.parse_args()

    db = next(get_session())
    summary = run(db, days=args.days, match_ids=args.matches, recaps=not args.previews_only,
                  previews=not args.recaps_only, dry_run=args.dry_run)
    for kind in ("recaps", "previews"):
        print(f"{kind}: {len(summary[kind])}")
        for item in summary[kind]:
            print(f"  + {item if isinstance(item, str) else item.get('title')}")
            if args.dry_run and isinstance(item, dict):
                print("    " + item["body_md"].replace("\n", "\n    "))
    for item in summary["skipped"]:
        print(f"  - nothing to draft: {item}")
    print(f"stale preview drafts rejected: {summary['retired']}")
    for err in summary["errors"]:
        print(f"  ! {err}")
    return 1 if summary["errors"] and not (summary["recaps"] or summary["previews"]) else 0


if __name__ == "__main__":
    sys.exit(main())
