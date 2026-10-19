"""
Squad reviews for a league's squads file (data/squads/<league>_<season>.json): each team's best XI, where it's
strong or thin by phase, its pace and spin overs against its home ground, depth, and the players the data hasn't
seen enough of. Descriptive only: the squad total doesn't rank teams (scripts/squad_backtest.py), so it isn't shown
as one.

    python scripts/squad_reviews.py data/squads/sa20_2027.json [--team "Paarl Royals"]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("squads")
    ap.add_argument("--team")
    args = ap.parse_args()
    doc = json.load(open(args.squads))
    as_of = date.fromisoformat(doc["as_of"])

    from analysis.hypotheses.common import read_only_session
    from services import squad_review as S

    teams = [t for t in doc["teams"] if not args.team or t["team"] == args.team]
    dn = lambda p: p.get("data_name") or p["name"]  # noqa: E731  the ball-by-ball spelling
    everyone = sorted({dn(p) for t in teams for p in t["players"]})
    with read_only_session() as db:
        values = S.player_values(db, everyone, as_of)
        slots = S.slot_balls(db, doc["league"], as_of)
        unseen = [p for p in everyone if not values[p]["bat_balls"] and not values[p]["bowl_balls"]]
        print(f"{doc['league']} {doc['season']} · values from every men's T20 in the two years to {as_of}"
              f" · {'confirmed' if doc.get('confirmed') else 'UNCONFIRMED squads'}")
        print(f"Not in the data at all ({len(unseen)}): {', '.join(unseen) or '-'}")
        for t in teams:
            squad = [dn(p) for p in t["players"]]
            over = [dn(p) for p in t["players"] if p["overseas"]]
            r = S.review(db, doc["league"], squad, as_of, overseas=over, values=values, slots=slots)
            g = S.ground_profile(db, t["home"], date(2021, 1, 1))
            bought = {dn(p) for p in t["players"] if p["how"] in ("auction", "wildcard")}
            print(f"\n== {t['team']}  (home: {t['home'][0]})")
            print("  XI: " + ", ".join(f"{p}{' (new)' if p in bought else ''}{' *' if p in over else ''}" for p in r["xi"]))
            print("  Overs: " + "; ".join(f"{p} " + "/".join(f"{ph[0].upper()}{n}" for ph, n in by.items())
                                         for p, by in r["overs"].items()))
            ph = r["phases"]
            print("  Batting by phase:  " + "  ".join(f"{k} {v:+.1f}" for k, v in ph["bat"].items()))
            print("  Bowling by phase:  " + "  ".join(f"{k} {v:+.1f}" for k, v in ph["bowl"].items()))
            k = r["kinds"]
            print(f"  Pace {k['pace']['overs']} overs ({k['pace']['runs']:+.1f}), spin {k['spin']['overs']} overs ({k['spin']['runs']:+.1f})"
                  f"  | home: pace {g['pace']['econ']:.2f} an over, spin {g['spin']['econ']:.2f}, spin share {100 * (g['spin']['share'] or 0):.0f}%")
            print("  Depth (runs lost without): " + ", ".join(f"{p} {v:+.1f}" for p, v in r["depth"]))
            print(f"  New buys in the XI: {sum(1 for p in r['xi'] if p in bought)} of 11 · unproven in squad: "
                  + (", ".join(r["unproven"]) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
