"""
Generate content packs for newly loaded matches (services/content_packs.py).

    python scripts/generate_content_packs.py                 # last 10 days, matches without packs
    python scripts/generate_content_packs.py --days 3 --dry-run
    python scripts/generate_content_packs.py --match 1525655 --match 1496589

Runs nightly after the load (refresh-delivery-details.yml). Also makes the season tallies for
leagues in progress (playoff race, Impact leaders). Packs land as 'ready' in the admin "Social" tab; ready packs past their post-by deadline are marked expired; parked ideas
(services/content_ideas.py) are retried against the new data.
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

    if not args.matches:
        # Season tallies (services/season_tallies.py): playoff race and Impact leaders for leagues in
        # progress. Needs ESPN; a failure here must not lose the packs above.
        try:
            from services.season_tallies import generate as generate_tallies

            tallies = generate_tallies(db, dry_run=args.dry_run)
            print(f"season tallies: leagues {tallies['leagues'] or '-'} | packs: {len(tallies['packs'])} | "
                  f"refused: {len(tallies['refused'])}")
            for p in tallies["packs"]:
                print(f"  + {p['title']}{' (already queued)' if p.get('duplicate') else ''}")
            for p in tallies["refused"]:
                print(f"  - refused: {p['title']} -- {'; '.join(p['refused'])}")
            for reason in tallies["skipped"]:
                print(f"  . {reason}")
        except Exception as exc:  # noqa: BLE001 -- reported, never fatal
            db.rollback()
            print(f"season tallies failed: {exc!r}")

    if not args.dry_run and not args.matches:
        from services.content_ideas import retry_parked

        counts = retry_parked(db)
        print(f"parked ideas: {counts['resolved']} resolved, {counts['parked']} still parked, {counts['failed']} given up")


if __name__ == "__main__":
    main()
