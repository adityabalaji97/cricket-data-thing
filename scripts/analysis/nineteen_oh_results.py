#!/usr/bin/env python3
"""
19-0 results (the game_result events the game logs on lock-in, since 13 Nov 2026): how many drafts, by how many
browsers, the spread of records, and the most-drafted player-seasons. For tuning the game (is it too hard?) and for
posts ("the most-drafted season"). Reads app_events; the deal and picks in each row replay exactly in the app.

    python scripts/analysis/nineteen_oh_results.py [--days 30]
"""
import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)


def main() -> int:
    from sqlalchemy import text

    from database import get_session

    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()
    db = next(get_session())
    rows = db.execute(text("""
        SELECT anon_id, ts, props FROM app_events
        WHERE event = 'game_result' AND props->>'game' = '19-0' AND ts >= now() - make_interval(days => :days)
        ORDER BY ts"""), {"days": args.days}).fetchall()
    starts = db.execute(text("""
        SELECT COUNT(*), COUNT(DISTINCT anon_id) FROM app_events
        WHERE event = 'game_start' AND props->>'game' = '19-0' AND ts >= now() - make_interval(days => :days)"""),
        {"days": args.days}).fetchone()
    # One result per draft (deal + picks): the same lock-in can't count twice.
    seen, plays = set(), []
    for anon, ts, props in rows:
        key = (props.get("d"), props.get("p"))
        if key in seen:
            continue
        seen.add(key)
        plays.append((anon, props))
    print(f"last {args.days} days: {starts[0]} drafts started by {starts[1]} browsers; "
          f"{len(plays)} locked in by {len({a for a, _ in plays})} browsers")
    if not plays:
        return 0
    made = [p["made"] for _, p in plays]
    dist = Counter(made)
    print("records:", "  ".join(f"{m}-{19 - m}: {dist[m]}" for m in sorted(dist, reverse=True)))
    s = sorted(made)
    print(f"median {s[len(s) // 2]}-{19 - s[len(s) // 2]}, best {s[-1]}-{19 - s[-1]}, 19-0s: {dist[19]}")
    picks = Counter(name for _, p in plays for name in p.get("picks") or [])
    print("most drafted:", ", ".join(f"{n} ({c})" for n, c in picks.most_common(10)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
