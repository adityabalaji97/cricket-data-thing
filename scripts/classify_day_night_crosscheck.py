#!/usr/bin/env python3
"""
Cross-check the day/night classification heuristics before backfilling.

For every (date, competition='IPL') group with 2+ matches, computes:
  Heuristic A: lower event_match_number -> 'day', higher -> 'night'
  Heuristic B: lexicographic min of match_id -> 'day', max -> 'night'

Prints divergences for manual verification against Cricinfo.

Usage:
    python scripts/classify_day_night_crosscheck.py
"""

import sys
from pathlib import Path

# Make repo root importable when running as `python scripts/foo.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collections import defaultdict
from sqlalchemy import text
from database import get_database_connection
from services.day_night_classifier import classify_day_night_for_group, SUPPORTED_COMPETITIONS


def fetch_groups(session, competitions):
    """
    Returns dict: (date, competition) -> list of match dicts with id,
    event_match_number, venue, team1, team2, event_name.
    """
    query = text(
        """
        SELECT id, date, competition, event_match_number, venue, team1, team2, event_name
        FROM matches
        WHERE competition = ANY(:competitions)
        ORDER BY date, event_match_number NULLS LAST, id
        """
    )
    rows = session.execute(query, {"competitions": list(competitions)}).fetchall()
    cols = ["id", "date", "competition", "event_match_number", "venue", "team1", "team2", "event_name"]

    groups: dict = defaultdict(list)
    for r in rows:
        m = dict(zip(cols, r))
        groups[(m["date"], m["competition"])].append(m)
    return groups


def main():
    _, SessionLocal = get_database_connection()
    session = SessionLocal()
    try:
        comps = sorted(SUPPORTED_COMPETITIONS)
        # Pre-flight: how many matches lack event_match_number?
        rows = session.execute(
            text(
                """
                SELECT competition,
                       COUNT(*) total,
                       COUNT(*) - COUNT(event_match_number) null_emn
                FROM matches
                WHERE competition = ANY(:competitions)
                GROUP BY competition
                """
            ),
            {"competitions": comps},
        ).fetchall()
        for r in rows:
            print(f"{r[0]!r:30s} total={r[1]} null_emn={r[2]}")
        print()

        groups = fetch_groups(session, comps)
        multi = {k: v for k, v in groups.items() if len(v) >= 2}
        single = sum(1 for v in groups.values() if len(v) == 1)
        print(f"Date groups: {len(groups)} total, {len(multi)} multi-match, {single} single-match")
        print()

        if not multi:
            print("No multi-match days found — nothing to cross-check.")
            return 0

        divergences = []
        null_emn_groups = []
        agreement = 0

        for (date, comp), peers in multi.items():
            labels_a = classify_day_night_for_group(peers, method="event_match_number")
            labels_b = classify_day_night_for_group(peers, method="match_id")

            if any(p.get("event_match_number") is None for p in peers):
                null_emn_groups.append((date, comp, peers))

            if labels_a == labels_b:
                agreement += 1
            else:
                divergences.append((date, comp, peers, labels_a, labels_b))

        print(f"Agreement: {agreement}/{len(multi)} multi-match days")
        print(f"Divergences: {len(divergences)}")
        print(f"Groups with NULL event_match_number: {len(null_emn_groups)}")
        print()

        if divergences:
            print("=" * 80)
            print("DIVERGENCES (manually verify against Cricinfo before backfilling)")
            print("=" * 80)
            for date, comp, peers, a, b in divergences:
                print(f"\n{date} | {comp} | {len(peers)} matches")
                for p in peers:
                    label_a = a.get(p["id"], "?")
                    label_b = b.get(p["id"], "?")
                    flag = "" if label_a == label_b else "  <-- DIVERGES"
                    print(
                        f"  id={p['id']}  emn={p['event_match_number']}  "
                        f"{p['team1']} vs {p['team2']} @ {p['venue']}"
                    )
                    print(f"    A(event_match_number)={label_a}   B(match_id)={label_b}{flag}")
            print()

        if null_emn_groups:
            print("=" * 80)
            print("GROUPS WITH NULL event_match_number (heuristic A unreliable here)")
            print("=" * 80)
            for date, comp, peers in null_emn_groups[:20]:  # cap output
                print(f"\n{date} | {comp}")
                for p in peers:
                    print(
                        f"  id={p['id']}  emn={p['event_match_number']}  "
                        f"{p['team1']} vs {p['team2']} @ {p['venue']}"
                    )
            if len(null_emn_groups) > 20:
                print(f"\n... and {len(null_emn_groups) - 20} more groups with NULLs")
            print()

        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
