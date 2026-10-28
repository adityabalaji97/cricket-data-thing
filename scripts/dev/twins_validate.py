"""
Statistical twins, validation (DOPPELGANGER_PLAN.md S3). Read-only; prints a report.

    python scripts/dev/twins_validate.py --season 2025

1. Split-half stability: the season's matches split in two (by match id), each half built on its own, and each
   player's top-5 twins (within the season) found in both. The overlap is compared with chance (5 x 5 / pool).
2. Group drop-out: each group left out in turn; the share of players whose top twin changes. A group that changes
   almost everything is dominating; one that changes nothing isn't pulling its weight.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("USAGE_LOGGING", "0")
os.environ.setdefault("QUERY_CACHE", "0")

HALF_FLOOR = 60  # half a season's balls: half the full-season noise floor


def rows_from(vectors, period):
    rows = []
    for name, v in vectors.items():
        if v["qualified"]:
            rows.append({"period": period, "player": name, "balls": v["balls"], "innings": v["innings"],
                         "kind": v["kind"], "tracked_share": v["tracked_share"], "features": v["features"]})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    from database import get_session
    from services.player_verdict import scope_params
    from services.query_builder_v2 import run_deliveries_query
    from services.twins import GROUPS, find_in, percentiles
    from services.twins_features import build_period

    db = next(get_session())
    start, end = date(args.season, 1, 1), date(args.season, 12, 31)
    ids = sorted({str(r["match_id"]) for r in run_deliveries_query(
        db, fmt="T20", limit=100000, group_by=["match_id"], start_date=start, end_date=end,
        **scope_params("T20", "strong"))["data"]})
    halves = [ids[0::2], ids[1::2]]
    print(f"{args.season}: {len(ids)} matches, halves of {len(halves[0])} and {len(halves[1])}")

    for role in ("bat", "bowl"):
        built = []
        for i, half in enumerate(halves):
            vectors, _ = build_period(db, role, start, end, match_ids=half, floor=HALF_FLOOR)
            rows = rows_from(vectors, str(args.season))
            percentiles(rows)
            built.append(rows)
        both = {r["player"] for r in built[0]} & {r["player"] for r in built[1]}
        for kind in ("style", "value"):
            overlaps = []
            for name in both:
                a = {t["player"] for t in find_in(built[0], name, str(args.season), role, kind, args.n, True)["twins"]}
                b = {t["player"] for t in find_in(built[1], name, str(args.season), role, kind, args.n, True)["twins"]}
                if a and b:
                    overlaps.append(len(a & b) / args.n)
            # Fairer than exact overlap: where half A's top twins sit in half B's whole ordering (0% = nearest,
            # 50% = chance).
            ranks = []
            for name in both:
                a = [t["player"] for t in find_in(built[0], name, str(args.season), role, kind, args.n, True)["twins"]]
                order = [t["player"] for t in find_in(built[1], name, str(args.season), role, kind, 10000, True)["twins"]]
                pos = {p: i for i, p in enumerate(order)}
                ranks += [pos[p] / max(1, len(order) - 1) for p in a if p in pos]
            if ranks:
                ranks.sort()
                print(f"  {role} {kind}: half A's top-{args.n} sit at the {sum(ranks) / len(ranks):.0%} mark of half B's "
                      f"ordering on average (median {ranks[len(ranks) // 2]:.0%}; chance 50%)")
            chance = args.n / max(1, len(both) - 1)
            mean = sum(overlaps) / len(overlaps) if overlaps else 0
            print(f"  {role} {kind}: {len(overlaps)} players in both halves; top-{args.n} overlap {mean:.0%} "
                  f"(chance {chance:.1%}, {mean / chance if chance else 0:.0f}x)")

        # Group drop-out on the full season.
        vectors, _ = build_period(db, role, start, end)
        rows = rows_from(vectors, str(args.season))
        percentiles(rows)
        for kind in ("style", "value"):
            groups = [g for g, k in GROUPS[role].items() if k == kind]
            if len(groups) < 2:
                print(f"  {role} {kind}: one group ({groups[0]}), no drop-out test")
                continue
            base = {r["player"]: (find_in(rows, r["player"], str(args.season), role, kind, 1, True)["twins"] or [{}])[0].get("player")
                    for r in rows}
            for g in groups:
                changed = sum(1 for r in rows if base[r["player"]] != (find_in(
                    rows, r["player"], str(args.season), role, kind, 1, True, (g,))["twins"] or [{}])[0].get("player"))
                print(f"  {role} {kind} without {g}: top twin changes for {changed / len(rows):.0%} of {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
