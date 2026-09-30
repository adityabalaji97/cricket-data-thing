#!/usr/bin/env python3
"""Recompute the run-derived columns of bowling_stats with the corrected bowler-runs rule.

Why this exists
---------------
Bowler runs are the ball's total less byes and leg-byes. Both writers got it wrong:

* sync_stats_from_dd.py used `score + wide + noball`. `score` already includes wide and no-ball
  runs, so those were counted twice, and byes/leg-byes were charged to the bowler. It also
  counted "4 byes" as a four conceded (boundaries read `score`, not `batruns`) and did not give
  the bowler a dot for a leg-bye. (Bumrah, IPL 2025: stored 327 runs, correct 316.)
* statsProcessor.py (legacy `deliveries` rows) used `runs_off_bat + extras`, which includes
  byes, leg-byes and penalties.

Both writers are fixed; this repairs rows already written. Wickets, overs and balls are not
touched -- only runs, dots, fours/sixes/boundaries, economies and the team comparison.

Scope
-----
* Rows whose match has ball data in delivery_details (written by sync_stats_from_dd.py): every
  run-derived column, by the same phase boundaries that writer uses (format_config).
* Rows from the legacy table only: runs, economy and team comparison (their phase columns were
  written with T20 boundaries whatever the format, so T20 phase runs are recomputed too).

Usage
-----
    python scripts/backfill_bowler_runs.py --dry-run     # counts and a sample, no writes
    python scripts/backfill_bowler_runs.py --confirm     # write, one year at a time

Take a database backup first (heroku pg:backups:capture).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from database import engine  # noqa: E402

# Phase boundaries (end-exclusive over index) per format, as in format_config / the writer.
PHASE_SQL = """
    CASE WHEN dd.format = 'ODI' THEN CASE WHEN dd.over < 10 THEN 1 WHEN dd.over < 40 THEN 2 ELSE 3 END
         ELSE CASE WHEN dd.over < 6 THEN 1 WHEN dd.over < 15 THEN 2 ELSE 3 END END
"""

DD_UPDATE = f"""
WITH balls AS (
    SELECT dd.p_match, dd.inns, dd.bowl, {PHASE_SQL} AS phase,
           COALESCE(dd.score, 0) - COALESCE(dd.byes, 0) - COALESCE(dd.legbyes, 0) AS runs,
           (COALESCE(dd.batruns, 0) = 0 AND COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0) AS dot,
           COALESCE(dd.batruns, 0) AS batruns
    FROM delivery_details dd
    WHERE dd.year = :year AND dd.format IN ('T20', 'ODI')
),
per_bowler AS (
    SELECT p_match, inns, bowl,
           SUM(runs) AS runs,
           SUM(CASE WHEN phase = 1 THEN runs ELSE 0 END) AS pp_runs,
           SUM(CASE WHEN phase = 2 THEN runs ELSE 0 END) AS middle_runs,
           SUM(CASE WHEN phase = 3 THEN runs ELSE 0 END) AS death_runs,
           SUM(CASE WHEN dot THEN 1 ELSE 0 END) AS dots,
           SUM(CASE WHEN dot AND phase = 1 THEN 1 ELSE 0 END) AS pp_dots,
           SUM(CASE WHEN dot AND phase = 2 THEN 1 ELSE 0 END) AS middle_dots,
           SUM(CASE WHEN dot AND phase = 3 THEN 1 ELSE 0 END) AS death_dots,
           SUM(CASE WHEN batruns = 4 THEN 1 ELSE 0 END) AS fours,
           SUM(CASE WHEN batruns = 6 THEN 1 ELSE 0 END) AS sixes,
           SUM(CASE WHEN batruns IN (4, 6) AND phase = 1 THEN 1 ELSE 0 END) AS pp_boundaries,
           SUM(CASE WHEN batruns IN (4, 6) AND phase = 2 THEN 1 ELSE 0 END) AS middle_boundaries,
           SUM(CASE WHEN batruns IN (4, 6) AND phase = 3 THEN 1 ELSE 0 END) AS death_boundaries
    FROM balls GROUP BY 1, 2, 3
),
per_innings AS (
    SELECT p_match, inns, SUM(runs) AS runs FROM balls GROUP BY 1, 2
),
fresh AS (
    SELECT b.*, i.runs - b.runs AS team_runs
    FROM per_bowler b JOIN per_innings i ON i.p_match = b.p_match AND i.inns = b.inns
)
{{action}}
"""

DD_SET = """
UPDATE bowling_stats bs SET
    runs_conceded = f.runs,
    pp_runs = f.pp_runs, middle_runs = f.middle_runs, death_runs = f.death_runs,
    dots = f.dots, pp_dots = f.pp_dots, middle_dots = f.middle_dots, death_dots = f.death_dots,
    fours_conceded = f.fours, sixes_conceded = f.sixes,
    pp_boundaries = f.pp_boundaries, middle_boundaries = f.middle_boundaries, death_boundaries = f.death_boundaries,
    economy = CASE WHEN bs.overs > 0 THEN f.runs / bs.overs END,
    pp_economy = CASE WHEN bs.pp_overs > 0 THEN f.pp_runs / bs.pp_overs END,
    middle_economy = CASE WHEN bs.middle_overs > 0 THEN f.middle_runs / bs.middle_overs END,
    death_economy = CASE WHEN bs.death_overs > 0 THEN f.death_runs / bs.death_overs END,
    team_runs_excl_bowler = f.team_runs,
    team_economy_excl_bowler = CASE WHEN bs.team_overs_excl_bowler > 0 THEN f.team_runs / bs.team_overs_excl_bowler END,
    economy_diff = CASE WHEN bs.overs > 0 AND bs.team_overs_excl_bowler > 0
                        THEN f.runs / bs.overs - f.team_runs / bs.team_overs_excl_bowler END
FROM fresh f
WHERE bs.match_id = f.p_match AND bs.innings = f.inns AND bs.bowler = f.bowl
  AND (bs.runs_conceded IS DISTINCT FROM f.runs OR bs.dots IS DISTINCT FROM f.dots
       OR bs.fours_conceded IS DISTINCT FROM f.fours OR bs.sixes_conceded IS DISTINCT FROM f.sixes)
"""

DD_COUNT = """
SELECT COUNT(*) AS rows_matched,
       COUNT(*) FILTER (WHERE bs.runs_conceded IS DISTINCT FROM f.runs) AS runs_changed,
       COALESCE(SUM(bs.runs_conceded - f.runs), 0) AS runs_removed
FROM fresh f JOIN bowling_stats bs ON bs.match_id = f.p_match AND bs.innings = f.inns AND bs.bowler = f.bowl
"""

LEGACY = """
WITH balls AS (
    SELECT d.match_id, d.innings, d.bowler, d.over,
           COALESCE(d.runs_off_bat, 0) + COALESCE(d.wides, 0) + COALESCE(d.noballs, 0) AS runs
    FROM deliveries d
    JOIN matches m ON m.id = d.match_id
    WHERE EXTRACT(YEAR FROM m.date) = :year
      AND NOT EXISTS (SELECT 1 FROM delivery_details x WHERE x.p_match = d.match_id)
),
per_bowler AS (
    SELECT match_id, innings, bowler, SUM(runs) AS runs,
           SUM(CASE WHEN over < 6 THEN runs ELSE 0 END) AS pp_runs,
           SUM(CASE WHEN over >= 6 AND over < 15 THEN runs ELSE 0 END) AS middle_runs,
           SUM(CASE WHEN over >= 15 THEN runs ELSE 0 END) AS death_runs
    FROM balls GROUP BY 1, 2, 3
),
per_innings AS (SELECT match_id, innings, SUM(runs) AS runs FROM balls GROUP BY 1, 2),
fresh AS (
    SELECT b.*, i.runs - b.runs AS team_runs
    FROM per_bowler b JOIN per_innings i ON i.match_id = b.match_id AND i.innings = b.innings
)
{action}
"""

LEGACY_SET = """
UPDATE bowling_stats bs SET
    runs_conceded = f.runs,
    economy = CASE WHEN bs.overs > 0 THEN f.runs / bs.overs END,
    pp_runs = CASE WHEN bs.format = 'T20' THEN f.pp_runs ELSE bs.pp_runs END,
    middle_runs = CASE WHEN bs.format = 'T20' THEN f.middle_runs ELSE bs.middle_runs END,
    death_runs = CASE WHEN bs.format = 'T20' THEN f.death_runs ELSE bs.death_runs END,
    pp_economy = CASE WHEN bs.format = 'T20' AND bs.pp_overs > 0 THEN f.pp_runs / bs.pp_overs ELSE bs.pp_economy END,
    middle_economy = CASE WHEN bs.format = 'T20' AND bs.middle_overs > 0 THEN f.middle_runs / bs.middle_overs ELSE bs.middle_economy END,
    death_economy = CASE WHEN bs.format = 'T20' AND bs.death_overs > 0 THEN f.death_runs / bs.death_overs ELSE bs.death_economy END,
    team_runs_excl_bowler = f.team_runs,
    team_economy_excl_bowler = CASE WHEN bs.team_overs_excl_bowler > 0 THEN f.team_runs / bs.team_overs_excl_bowler END,
    economy_diff = CASE WHEN bs.overs > 0 AND bs.team_overs_excl_bowler > 0
                        THEN f.runs / bs.overs - f.team_runs / bs.team_overs_excl_bowler END
FROM fresh f
WHERE bs.match_id = f.match_id AND bs.innings = f.innings AND bs.bowler = f.bowler
  AND bs.runs_conceded IS DISTINCT FROM f.runs
"""

LEGACY_COUNT = """
SELECT COUNT(*) AS rows_matched,
       COUNT(*) FILTER (WHERE bs.runs_conceded IS DISTINCT FROM f.runs) AS runs_changed,
       COALESCE(SUM(bs.runs_conceded - f.runs), 0) AS runs_removed
FROM fresh f JOIN bowling_stats bs ON bs.match_id = f.match_id AND bs.innings = f.innings AND bs.bowler = f.bowler
"""


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--confirm", action="store_true")
    parser.add_argument("--years", default="2000-2026", help="Inclusive range, e.g. 2025-2026")
    args = parser.parse_args()
    first, last = (int(x) for x in args.years.split("-"))

    totals = {"dd_rows": 0, "dd_changed": 0, "dd_runs_removed": 0, "legacy_rows": 0, "legacy_changed": 0, "legacy_runs_removed": 0}
    for year in range(first, last + 1):
        with engine.begin() as conn:
            dd = conn.execute(text(DD_UPDATE.format(action=DD_COUNT)), {"year": year}).mappings().first()
            lg = conn.execute(text(LEGACY.format(action=LEGACY_COUNT)), {"year": year}).mappings().first()
            written = ""
            if args.confirm:
                a = conn.execute(text(DD_UPDATE.format(action=DD_SET)), {"year": year}).rowcount
                b = conn.execute(text(LEGACY.format(action=LEGACY_SET)), {"year": year}).rowcount
                written = f" | wrote dd {a}, legacy {b}"
        totals["dd_rows"] += dd["rows_matched"]; totals["dd_changed"] += dd["runs_changed"]; totals["dd_runs_removed"] += dd["runs_removed"]
        totals["legacy_rows"] += lg["rows_matched"]; totals["legacy_changed"] += lg["runs_changed"]; totals["legacy_runs_removed"] += lg["runs_removed"]
        print(f"{year}: dd {dd['rows_matched']} rows, {dd['runs_changed']} runs changed ({dd['runs_removed']:+} over-count) | "
              f"legacy {lg['rows_matched']} rows, {lg['runs_changed']} changed ({lg['runs_removed']:+}){written}", flush=True)
    print(totals)


if __name__ == "__main__":
    main()
