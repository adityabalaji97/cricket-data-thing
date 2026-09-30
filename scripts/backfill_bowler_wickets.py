#!/usr/bin/env python3
"""Recount bowling_stats wickets for rows written from delivery_details, counting LBWs.

Why this exists
---------------
sync_stats_from_dd.py counted a bowler's wickets from a list of dismissal types that had "lbw",
but the ball-by-ball feed writes "leg before wicket". Every LBW was dropped: Rashid Khan's ODI
wickets read 142 against 226 in the deliveries themselves. Across the table ~6,000 ODI and
~9,500 T20 wickets were missing, in ~13,000 spells. The writer is fixed; this repairs rows
already written: wickets, the three phase wicket columns and the fantasy points derived from them.

Legacy rows (Cricsheet deliveries, "lbw") are unaffected and not touched.

Usage
-----
    python scripts/backfill_bowler_wickets.py --dry-run     # counts per year and a sample
    python scripts/backfill_bowler_wickets.py --confirm     # write, one year at a time

Take a database backup first (heroku pg:backups:capture).
"""
import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from database import engine  # noqa: E402

WICKET_TYPES = ("bowled", "caught", "lbw", "leg before wicket", "caught and bowled", "stumped", "hit wicket")
# Phase boundaries (end-exclusive over index) per format, as in format_config / the writer.
PHASE_SQL = """
    CASE WHEN dd.format = 'ODI' THEN CASE WHEN dd.over < 10 THEN 1 WHEN dd.over < 40 THEN 2 ELSE 3 END
         ELSE CASE WHEN dd.over < 6 THEN 1 WHEN dd.over < 15 THEN 2 ELSE 3 END END
"""
FRESH = f"""
WITH balls AS (
    SELECT dd.p_match, dd.inns, dd.bowl, {PHASE_SQL} AS phase,
           (LOWER(COALESCE(dd.out::text, '')) = 'true'
            AND LOWER(COALESCE(dd.dismissal, '')) = ANY(:types)) AS wicket
    FROM delivery_details dd
    WHERE dd.year = :year AND dd.format IN ('T20', 'ODI')
),
fresh AS (
    SELECT p_match, inns, bowl,
           SUM(CASE WHEN wicket THEN 1 ELSE 0 END) AS wickets,
           SUM(CASE WHEN wicket AND phase = 1 THEN 1 ELSE 0 END) AS pp_wickets,
           SUM(CASE WHEN wicket AND phase = 2 THEN 1 ELSE 0 END) AS middle_wickets,
           SUM(CASE WHEN wicket AND phase = 3 THEN 1 ELSE 0 END) AS death_wickets
    FROM balls GROUP BY 1, 2, 3
)
"""
CHANGED = FRESH + """
SELECT bs.*, f.wickets AS new_wickets, f.pp_wickets AS new_pp, f.middle_wickets AS new_middle,
       f.death_wickets AS new_death
FROM bowling_stats bs
JOIN fresh f ON bs.match_id = f.p_match AND bs.innings = f.inns AND bs.bowler = f.bowl
WHERE bs.wickets IS DISTINCT FROM f.wickets
   OR bs.pp_wickets IS DISTINCT FROM f.pp_wickets
   OR bs.middle_wickets IS DISTINCT FROM f.middle_wickets
   OR bs.death_wickets IS DISTINCT FROM f.death_wickets
"""
BATCH = 500


def _write(conn, updates):
    """One UPDATE ... FROM (VALUES ...) per BATCH rows: a round trip per row took ~45 min for the table."""
    for i in range(0, len(updates), BATCH):
        chunk = updates[i:i + BATCH]
        values, params = [], {}
        for j, u in enumerate(chunk):
            values.append(f"(:id{j}, :w{j}, :pp{j}, :mid{j}, :death{j}, CAST(:fp{j} AS double precision))")
            params.update({f"id{j}": u["id"], f"w{j}": u["w"], f"pp{j}": u["pp"], f"mid{j}": u["mid"],
                           f"death{j}": u["death"], f"fp{j}": u["fp"]})
        conn.execute(text(f"""
            UPDATE bowling_stats bs SET wickets = v.w, pp_wickets = v.pp, middle_wickets = v.mid,
                   death_wickets = v.death, fantasy_points = v.fp
            FROM (VALUES {", ".join(values)}) AS v(id, w, pp, mid, death, fp)
            WHERE bs.id = v.id
        """), params)


def _new_fantasy(row, calculators):
    """Bowling fantasy points with the corrected wicket count, by the row's own ruleset."""
    if row["fantasy_points"] is None:
        return None
    from fantasy_points_odi import get_calculator

    key = ((row["format"] or "T20").upper(), row["gender"] or "male")
    if key not in calculators:
        calculators[key] = get_calculator(*key)
    stats = SimpleNamespace(**{**dict(row), "wickets": row["new_wickets"], "pp_wickets": row["new_pp"],
                               "middle_wickets": row["new_middle"], "death_wickets": row["new_death"]})
    return calculators[key].calculate_bowling_points(stats)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--confirm", action="store_true")
    parser.add_argument("--years", default="2000-2026", help="Inclusive range, e.g. 2025-2026")
    args = parser.parse_args()
    first, last = (int(x) for x in args.years.split("-"))

    calculators = {}
    totals = {"rows": 0, "wickets_added": 0}
    sample = []
    for year in range(first, last + 1):
        with engine.begin() as conn:
            rows = conn.execute(text(CHANGED), {"year": year, "types": list(WICKET_TYPES)}).mappings().all()
            added = sum((r["new_wickets"] or 0) - (r["wickets"] or 0) for r in rows)
            if args.confirm:
                _write(conn, [{"id": r["id"], "w": r["new_wickets"], "pp": r["new_pp"], "mid": r["new_middle"],
                               "death": r["new_death"], "fp": _new_fantasy(r, calculators)} for r in rows])
        totals["rows"] += len(rows)
        totals["wickets_added"] += added
        sample += [(r["bowler"], r["format"], r["match_id"], r["wickets"], r["new_wickets"]) for r in rows[:2]]
        print(f"{year}: {len(rows)} spells, {added:+} wickets{' (written)' if args.confirm else ''}", flush=True)
    print(totals)
    print("sample (bowler, format, match, stored, recounted):", sample[:8])


if __name__ == "__main__":
    main()
