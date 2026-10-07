"""
Dry run of "The deeper cut" (services/ig_posts/deep_cut.py): every probe's finding for a player, best first.

    python scripts/deep_cut.py --player "Shreyas Iyer" --role batter [--since 2023-01-01] [--league IPL] [--format T20]
    python scripts/deep_cut.py --queued      # each ready Instagram post's pick and runner-up, in queue order
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--player")
    parser.add_argument("--role", choices=["batter", "bowler"])
    parser.add_argument("--queued", action="store_true")
    parser.add_argument("--since", default=f"{date.today().year - 3}-01-01")
    parser.add_argument("--league", action="append", default=[])
    parser.add_argument("--format", default="T20", choices=["T20", "ODI"])
    args = parser.parse_args()

    from analysis.hypotheses.common import read_only_session
    from services.ig_posts import deep_cut

    if args.queued:
        return queued(deep_cut, read_only_session)

    scope = {"fmt": args.format, "gender": "male", "start_date": date.fromisoformat(args.since),
             # No leagues and no internationals flag is every T20; leagues=[] with include_international=True would be
             # internationals only.
             "leagues": args.league, "include_international": False}
    label = f"{' '.join(args.league) or args.format + 's'} since {args.since[:4]}"
    if not (args.player and args.role):
        parser.error("--player and --role, or --queued")
    with read_only_session() as db:
        for c in deep_cut.candidates(db, args.role, args.player, scope, label):
            print(f"[{c.probe}] {c.surprise:.2f}  {c.sentence}\n    {c.sample}")
    return 0


def queued(deep_cut, read_only_session) -> int:
    """Each post on its own session, retried: a dropped connection costs a retry, not the run."""
    import time

    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    def retrying(work, tries=4):
        for attempt in range(1, tries + 1):
            try:
                with read_only_session() as db:
                    return work(db)
            except OperationalError:
                if attempt == tries:
                    raise
                time.sleep(10 * attempt)

    rows = retrying(lambda db: [dict(r) for r in db.execute(text("""
        SELECT angle_key, planned_for, facts FROM content_packs
        WHERE channel = 'instagram' AND status = 'ready' ORDER BY planned_for NULLS LAST, id
    """)).mappings().all()])
    recent: list = []
    for r in rows:
        fact = dict(r["facts"] or {})
        day = r["planned_for"] or "bench"
        try:
            people, _scope, label, got = retrying(lambda db: (*deep_cut.subjects_for(db, fact),
                                                              deep_cut.choose(db, fact, avoid=recent[-3:])))
        except OperationalError as exc:
            print(f"{day} {r['angle_key']}\n    ERROR: {str(exc).splitlines()[0][:120]}\n", flush=True)
            continue
        who = ", ".join(p[2] for p in people) or "-"
        if not got:
            print(f"{day} {r['angle_key']}\n    subjects: {who} ({label})\n    NO SLIDE: nothing clears the gates\n", flush=True)
            continue
        d = got["deep_cut"]
        recent.append(d["probe"])
        print(f"{day} {r['angle_key']}\n    subjects: {who} ({label})\n    [{d['probe']}] {d['sentence']}"
              f"\n    (by {d['by']}, jev {d['jev']}, surprise {d['surprise']})\n", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
