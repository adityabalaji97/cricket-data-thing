#!/usr/bin/env python3
"""
Build each IPL side's Squad group (GET /team-squad, services/squad_view.team_squad) into the query cache, one side at a
time: a cold build is ~40 s, so the nightly run pays it rather than the first visitor (XI_BUILDER_PLAN.md X3).

    python scripts/warm_team_squads.py
"""
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.disable(logging.INFO)


def main() -> int:
    from database import get_session
    from services.squad_view import TEAMS, team_squad
    from services.xi_engine import payload

    db = next(get_session())
    for code in TEAMS:
        t = time.time()
        try:
            team_squad(db, code)
            payload(db, code)  # the builder's data (XI_BUILDER_PLAN.md X5)
            print(f"{code}: {time.time() - t:.0f}s")
        except Exception as exc:  # one side failing doesn't stop the rest
            db.rollback()
            print(f"{code}: failed ({exc})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
