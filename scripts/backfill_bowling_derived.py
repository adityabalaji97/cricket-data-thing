#!/usr/bin/env python3
"""Recompute the bowling_stats columns derived from other bowlers' runs and from fantasy rules.

Why this exists
---------------
scripts/backfill_bowler_runs.py rewrote a row only when that bowler's *own* runs, dots, fours or
sixes changed. Two things escaped it:

* The team comparison (team_runs_excl_bowler, team_economy_excl_bowler, economy_diff) depends on
  the *other* bowlers' runs. A bowler who conceded no byes in an innings where a teammate did kept
  the old, inflated team figure (1549524, Ruben Trumpelmann: stored 123, correct 119).
* fantasy_points was never recomputed by it, so rows whose economy changed keep points scored on
  the old economy. (backfill_bowler_wickets.py recomputed them only for the rows it touched.)

This repairs both, for every row, by the writers' current rules: the team comparison from the same
per-year SQL as backfill_bowler_runs.py (delivery_details matches and legacy-only matches), and
bowling fantasy points from the row's own dots/wickets/overs/economy with its format's calculator.
Rows already right are not written, so a re-run is a no-op.

Usage
-----
    python scripts/backfill_bowling_derived.py --dry-run     # counts per year and a sample
    python scripts/backfill_bowling_derived.py --confirm     # backup table, then write year by year

--confirm first copies the affected columns to bowling_stats_backup_derived_20260930 (skipped if it
already exists), so the change can be reverted with one UPDATE ... FROM.
"""
import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text  # noqa: E402

from backfill_bowler_runs import DD_UPDATE, LEGACY  # noqa: E402
from database import engine  # noqa: E402

BACKUP_TABLE = "bowling_stats_backup_derived_20260930"
BATCH = 500

TEAM_SET = """
UPDATE bowling_stats bs SET
    team_runs_excl_bowler = f.team_runs,
    team_economy_excl_bowler = CASE WHEN bs.team_overs_excl_bowler > 0 THEN f.team_runs / bs.team_overs_excl_bowler END,
    economy_diff = CASE WHEN bs.overs > 0 AND bs.team_overs_excl_bowler > 0
                        THEN bs.runs_conceded / bs.overs - f.team_runs / bs.team_overs_excl_bowler END
FROM fresh f
WHERE {join}
  AND bs.team_runs_excl_bowler IS DISTINCT FROM f.team_runs
"""
TEAM_COUNT = """
SELECT COUNT(*) AS stale, COALESCE(SUM(bs.team_runs_excl_bowler - f.team_runs), 0) AS over_count
FROM fresh f JOIN bowling_stats bs ON {join}
WHERE bs.team_runs_excl_bowler IS DISTINCT FROM f.team_runs
"""
DD_JOIN = "bs.match_id = f.p_match AND bs.innings = f.inns AND bs.bowler = f.bowl"
LEGACY_JOIN = "bs.match_id = f.match_id AND bs.innings = f.innings AND bs.bowler = f.bowler"

FANTASY_ROWS = """
SELECT bs.id, bs.bowler, bs.match_id, bs.format, bs.gender, bs.dots, bs.wickets, bs.overs, bs.economy,
       bs.fantasy_points
FROM bowling_stats bs JOIN matches m ON m.id = bs.match_id
WHERE EXTRACT(YEAR FROM m.date) = :year AND bs.fantasy_points IS NOT NULL
"""


def _fantasy(row, calculators):
    from fantasy_points_odi import get_calculator

    key = ((row["format"] or "T20").upper(), row["gender"] or "male")
    if key not in calculators:
        calculators[key] = get_calculator(*key)
    stats = SimpleNamespace(**dict(row))
    stats.dots = stats.dots or 0
    stats.wickets = stats.wickets or 0
    stats.overs = stats.overs or 0
    return float(calculators[key].calculate_bowling_points(stats))


def _write_fantasy(conn, updates):
    for i in range(0, len(updates), BATCH):
        chunk = updates[i:i + BATCH]
        values = ", ".join(f"(:id{j}, CAST(:fp{j} AS double precision))" for j in range(len(chunk)))
        params = {}
        for j, (row_id, fp) in enumerate(chunk):
            params[f"id{j}"], params[f"fp{j}"] = row_id, fp
        conn.execute(text(f"""
            UPDATE bowling_stats bs SET fantasy_points = v.fp
            FROM (VALUES {values}) AS v(id, fp) WHERE bs.id = v.id
        """), params)


def _backup():
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT to_regclass(:t)"), {"t": BACKUP_TABLE}).scalar()
        if exists:
            print(f"backup {BACKUP_TABLE} already exists; keeping it")
            return
        conn.execute(text(f"""
            CREATE TABLE {BACKUP_TABLE} AS
            SELECT id, team_runs_excl_bowler, team_economy_excl_bowler, economy_diff, fantasy_points
            FROM bowling_stats
        """))
        n = conn.execute(text(f"SELECT COUNT(*) FROM {BACKUP_TABLE}")).scalar()
        print(f"backup {BACKUP_TABLE}: {n} rows")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--confirm", action="store_true")
    parser.add_argument("--years", default="2000-2026", help="Inclusive range, e.g. 2025-2026")
    args = parser.parse_args()
    first, last = (int(x) for x in args.years.split("-"))

    if args.confirm:
        _backup()

    calculators = {}
    totals = {"team_dd": 0, "team_legacy": 0, "fantasy": 0}
    sample = []
    for year in range(first, last + 1):
        with engine.begin() as conn:
            dd = conn.execute(text(DD_UPDATE.format(action=TEAM_COUNT.format(join=DD_JOIN))), {"year": year}).mappings().first()
            lg = conn.execute(text(LEGACY.format(action=TEAM_COUNT.format(join=LEGACY_JOIN))), {"year": year}).mappings().first()
            rows = conn.execute(text(FANTASY_ROWS), {"year": year}).mappings().all()
            changed = []
            for r in rows:
                fp = _fantasy(r, calculators)
                if abs(fp - float(r["fantasy_points"])) > 1e-9:
                    changed.append((r["id"], fp))
                    if len(sample) < 8:
                        sample.append((r["bowler"], r["format"], r["match_id"], r["fantasy_points"], fp))
            if args.confirm:
                conn.execute(text(DD_UPDATE.format(action=TEAM_SET.format(join=DD_JOIN))), {"year": year})
                conn.execute(text(LEGACY.format(action=TEAM_SET.format(join=LEGACY_JOIN))), {"year": year})
                _write_fantasy(conn, changed)
        totals["team_dd"] += dd["stale"]
        totals["team_legacy"] += lg["stale"]
        totals["fantasy"] += len(changed)
        print(f"{year}: team comparison stale dd {dd['stale']} ({dd['over_count']:+} runs), legacy {lg['stale']} "
              f"({lg['over_count']:+}) | fantasy {len(changed)} of {len(rows)}"
              f"{' (written)' if args.confirm else ''}", flush=True)
    print(totals)
    print("fantasy sample (bowler, format, match, stored, recomputed):", sample)


if __name__ == "__main__":
    main()
