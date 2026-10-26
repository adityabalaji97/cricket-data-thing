"""
Per team innings: legal balls with a left-right pair at the crease, against balls where both hands are known; and every
men's T20's result. Read-only. Writes data/lr_innings.csv and data/results.csv.

The 2015+ feed (delivery_details, keyed p_match / team_bat) wins where both tables have a match; the Cricsheet table (deliveries) fills the rest.

    python articles/gambhir/build_lr.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

MIXED = "('LHB_RHB', 'RHB_LHB', 'lhb_rhb', 'rhb_lhb')"
KNOWN = "('LHB_RHB', 'RHB_LHB', 'LHB_LHB', 'RHB_RHB', 'lhb_rhb', 'rhb_lhb', 'lhb_lhb', 'rhb_rhb')"
SQL = {
    "dd": f"""
        SELECT dd.p_match::text AS match_id, dd.team_bat AS batting_team,
               COUNT(*) FILTER (WHERE dd.crease_combo IN {MIXED}) AS mixed, COUNT(*) AS known
        FROM delivery_details dd JOIN matches m ON m.id = dd.p_match::text
        WHERE m.gender = 'male' AND m.format = 'T20' AND COALESCE(dd.wide, 0) = 0 AND dd.crease_combo IN {KNOWN}
        GROUP BY 1, 2""",
    "d": f"""
        SELECT d.match_id::text AS match_id, d.batting_team, COUNT(*) FILTER (WHERE d.crease_combo IN {MIXED}) AS mixed,
               COUNT(*) AS known
        FROM deliveries d JOIN matches m ON m.id = d.match_id::text
        WHERE m.gender = 'male' AND m.format = 'T20' AND COALESCE(d.wides, 0) = 0 AND d.crease_combo IN {KNOWN}
        GROUP BY 1, 2""",
    "results": """
        SELECT id AS match_id, date, competition, team1, team2, winner FROM matches
        WHERE gender = 'male' AND format = 'T20'""",
}

if __name__ == "__main__":
    from database import engine

    with engine.connect() as conn:
        d = {k: pd.read_sql(q, conn) for k, q in SQL.items()}
    print({k: len(v) for k, v in d.items()})
    lr = pd.concat([d["dd"], d["d"][~d["d"].match_id.isin(d["dd"].match_id)]], ignore_index=True)
    lr.to_csv(HERE / "data" / "lr_innings.csv", index=False)
    d["results"].to_csv(HERE / "data" / "results.csv", index=False)
    print(f"{len(lr):,} team innings; mixed share overall {lr.mixed.sum() / lr.known.sum():.1%}")
