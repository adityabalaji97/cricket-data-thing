"""
Rebuild batting/bowling stats and Primer metrics for matches whose ball-by-ball rows were corrected (migration 035,
services/delivery_fixes.py): their stats rows are rebuilt from the corrected balls, their player ids refilled, and
their ball_metrics scored again by the nightly incremental run's own code (the stored model; no refit).

    python scripts/rebuild_match_stats.py --ids-file matches.json            # what would be rebuilt
    python scripts/rebuild_match_stats.py --ids-file matches.json --write
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*", default=[])
    parser.add_argument("--ids-file")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    ids = list(args.ids) + (json.load(open(args.ids_file)) if args.ids_file else [])
    ids = sorted({str(i) for i in ids})
    print(f"{len(ids)} matches")
    if not args.write or not ids:
        return 0

    from sqlalchemy import text

    from database import engine, get_session
    from sync_stats_from_dd import StatsFromDeliveryDetails

    with engine.begin() as conn:
        b = conn.execute(text("DELETE FROM batting_stats WHERE match_id::text = ANY(:ids)"), {"ids": ids}).rowcount
        w = conn.execute(text("DELETE FROM bowling_stats WHERE match_id::text = ANY(:ids)"), {"ids": ids}).rowcount
    print(f"cleared {b} batting and {w} bowling rows")
    session = next(get_session())
    proc = StatsFromDeliveryDetails()
    made = {"batting": 0, "bowling": 0}
    for i, mid in enumerate(ids, 1):
        got = proc.process_match_stats(session, mid)
        made["batting"] += got["batting"]
        made["bowling"] += got["bowling"]
        if i % 25 == 0:
            session.commit()
    session.commit()
    print(f"rebuilt {made['batting']} batting and {made['bowling']} bowling rows")
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "backfill_stats_player_ids.py")], check=True, cwd=ROOT)
    with engine.begin() as conn:
        m = conn.execute(text("DELETE FROM ball_metrics WHERE p_match = ANY(:ids)"), {"ids": ids}).rowcount
    print(f"cleared {m} ball_metrics rows; scoring them again")
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "compute_primer_metrics.py"), "incremental", "--write"],
                   check=True, cwd=ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
