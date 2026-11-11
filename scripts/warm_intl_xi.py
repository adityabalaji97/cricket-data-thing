#!/usr/bin/env python3
"""
Build Pick your XI for the top 10 T20I sides into the query cache, one side at a time (a cold build is 30-50 s), so
visitors never wait (XI_BUILDER_PLAN.md stage 3a, I3). Run nightly after the feed, sequentially (2 web workers).

    python scripts/warm_intl_xi.py
"""
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.disable(logging.INFO)


def main() -> int:
    from database import get_session
    from services.intl_xi import TEAMS, get_page

    db = next(get_session())
    bad = 0
    for team in TEAMS:
        t = time.time()
        try:
            get_page(db, team, wait=True)
            print(f"{team}: {time.time() - t:.0f}s")
        except Exception as e:  # one side failing shouldn't stop the rest
            bad += 1
            db.rollback()
            print(f"{team}: FAILED {e!r}"[:300])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
