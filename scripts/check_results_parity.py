"""
Our men's T20I record by year against ESPNcricinfo's (services/results_parity.py). Prints every year that differs;
exits 1 if any does (a non-blocking step in the nightly run: a missing match, a wrong result, or a match still loading).

    python scripts/check_results_parity.py               # every team in the reference file
    python scripts/check_results_parity.py --team India
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LABELS = ("M", "W", "L", "T", "NR")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", action="append")
    args = parser.parse_args()

    from database import get_session
    from services import results_parity as P

    db = next(get_session())
    teams = args.team or [k for k in json.loads(P.REFERENCE.read_text()) if not k.startswith("_")]
    bad = 0
    for team in teams:
        diffs = P.check(db, team)
        print(f"{team}: {'matches the reference' if not diffs else f'{len(diffs)} years differ'}")
        for d in diffs:
            fmt = lambda r: " ".join(f"{l}{v}" for l, v in zip(LABELS, r))  # noqa: E731
            print(f"  {d['year']}: ours {fmt(d['ours'])} · reference {fmt(d['reference'])}")
        bad += len(diffs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
