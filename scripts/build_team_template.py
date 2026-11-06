"""
Pin a league's winners' template (TEAM_TEMPLATE_PLAN.md) to services/pinned/team_template_<league>.json: per graded role, every
template-era team-season's value with playoff sides' and the rest's levels; and each role's weight, how consistently it
separated playoff sides across every season. Posts and pages read the file, so a squad is graded against the same
template until it's rebuilt (after a season ends).

    python scripts/build_team_template.py --league IPL --era 2023-2026
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", default="IPL")
    ap.add_argument("--era", default="2023-2026", help="seasons the levels come from, e.g. 2023-2026 (the Impact Player era)")
    args = ap.parse_args()
    logging.disable(logging.INFO)
    from database import get_session
    from services.squad_grade import ROLES, TEMPLATE_DIR, benchmarks
    from services.team_roles import league_roles
    from services.team_template import template

    db = next(get_session())
    data = league_roles(db, args.league)
    lo, hi = (int(x) for x in args.era.split("-"))
    era = [s["season"] for s in data["seasons"] if lo <= int(str(s["season"])[:4]) <= hi]
    ahead = {m["feature"]: m["seasons_ahead"] for m in template(data)["measures"]}
    out = {
        "league": args.league, "built": date.today().isoformat(), "era": era,
        "seasons": [s["season"] for s in data["seasons"]],
        "playoff_sides": {s["season"]: s["playoff"] for s in data["seasons"]},
        # How often (share of seasons) playoff sides beat the rest on the role's measure, turned into a weight.
        "weights": {r[7]: round(max(0.1, 2 * (ahead.get(r[7], 0.5) - 0.5)), 3) for r in ROLES},
        "seasons_ahead": {r[7]: ahead.get(r[7]) for r in ROLES},
        "benchmarks": benchmarks(data, era),
    }
    path = ROOT / TEMPLATE_DIR / f"team_template_{args.league}.json"
    path.write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote {path}: era {era}, weights {out['weights']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
