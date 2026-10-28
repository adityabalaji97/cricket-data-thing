"""
Build the statistical twins' feature table, player_vectors (migration 036; DOPPELGANGER_PLAN.md S1).

    python scripts/build_player_vectors.py                  # nightly: the current and previous season
    python scripts/build_player_vectors.py --season 2019    # one season
    python scripts/build_player_vectors.py --all            # every season from 2015 (Impact and tracking start)
    python scripts/build_player_vectors.py --window         # the profile's default window (careers)

Men's T20, strong-opposition scope (services/player_verdict.scope_params), both roles. Each period is replaced whole.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("USAGE_LOGGING", "0")
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("player_vectors")

FIRST_SEASON = 2015


def write(db, unit: str, period: str, role: str, scope: str, vectors) -> None:
    from sqlalchemy import text

    db.execute(text("DELETE FROM player_vectors WHERE unit = :u AND period = :p AND role = :r AND scope = :s"),
               {"u": unit, "p": period, "r": role, "s": scope})
    rows = [{"u": unit, "p": period, "r": role, "s": scope, "player": name, "balls": v["balls"], "inn": v["innings"],
             "q": v["qualified"], "floor": v["floor_balls"], "kind": v["kind"], "tracked": v["tracked_share"],
             "f": json.dumps(v["features"])} for name, v in vectors.items() if name]
    if rows:
        db.execute(text("""
            INSERT INTO player_vectors (unit, period, role, scope, player, balls, innings, qualified, floor_balls, kind,
                                        tracked_share, features)
            VALUES (:u, :p, :r, :s, :player, :balls, :inn, :q, :floor, :kind, :tracked, CAST(:f AS jsonb))
        """), rows)
    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--window", action="store_true")
    parser.add_argument("--scope", default="strong", choices=["strong", "all"])
    args = parser.parse_args()

    from database import get_session
    from services.player_verdict import default_window
    from services.twins_features import build_period

    db = next(get_session())
    today = date.today()
    jobs = []
    if args.window:
        start, end = default_window("T20", today)
        jobs.append(("window", f"{start.isoformat()}..{end.isoformat()}", start, end))
    else:
        seasons = ([args.season] if args.season else
                   list(range(FIRST_SEASON, today.year + 1)) if args.all else [today.year - 1, today.year])
        jobs += [("season", str(y), date(y, 1, 1), min(date(y, 12, 31), today)) for y in seasons]

    for unit, period, start, end in jobs:
        for role in ("bat", "bowl"):
            t = time.time()
            vectors, qual = build_period(db, role, start, end, scope=args.scope, unit=unit)
            write(db, unit, period, role, args.scope, vectors)
            log.info("%s %s %s: %d players, %d qualified (%s+ balls), %.0fs", unit, period, role, len(vectors),
                     len(qual["players"]), qual["floor"], time.time() - t)
        if unit == "window":  # one career window at a time: drop yesterday's
            from sqlalchemy import text
            gone = db.execute(text("DELETE FROM player_vectors WHERE unit = 'window' AND scope = :s AND period <> :p"),
                              {"s": args.scope, "p": period}).rowcount
            db.commit()
            log.info("dropped %d rows of older windows", gone)
    # How far players' nearest twins usually are (the "no close twin" line on the profile): per unit and role.
    from services.twins import store_gap_stats
    for unit in sorted({u for u, *_ in jobs}):
        t = time.time()
        stats = store_gap_stats(db, unit, args.scope)
        log.info("nearest-twin gaps %s: %s, %.0fs", unit, stats, time.time() - t)
        if unit == "window":  # the doppelgangers page
            from services.twins import store_board
            t = time.time()
            b = store_board(db, unit, args.scope)
            log.info("board: %s, %.0fs", {r: len(v["pairs"]) for r, v in b.items()}, time.time() - t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
