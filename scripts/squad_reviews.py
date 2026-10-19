"""
Squad reviews for a league's squads file (data/squads/<league>_<season>.json): each team's likely XI (last season's
regulars, gaps filled by new buys), each player's value by phase with its sample, the team's phases, pace and spin
overs against its home ground, new buys, unproven players, and names that may be two players. Descriptive only: no
team total, no ranking (scripts/squad_backtest.py showed the total doesn't order a table).

    python scripts/squad_reviews.py data/squads/sa20_2027.json [--team "Paarl Royals"]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def f(v, d=1):
    return "   –" if v is None else f"{v:+.{d}f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("squads")
    ap.add_argument("--team")
    args = ap.parse_args()
    doc = json.load(open(args.squads))
    as_of = date.fromisoformat(doc["as_of"])
    last = (date.fromisoformat(doc["last_season"][0]), date.fromisoformat(doc["last_season"][1]))

    from analysis.hypotheses.common import read_only_session
    from services import squad_review as S

    teams = [t for t in doc["teams"] if not args.team or t["team"] == args.team]
    dn = lambda p: p.get("data_name") or p["name"]  # noqa: E731  the ball-by-ball spelling
    everyone = sorted({dn(p) for t in teams for p in t["players"]})
    home = S.LEAGUES[doc["league"]]["home"]
    with read_only_session() as db:
        values = S.player_values(db, everyone, as_of)
        slots = S.slot_balls(db, doc["league"], as_of)
        over_all = {dn(p) for t in teams for p in t["players"] if p["overseas"]}
        flags = S.identity_flags(db, everyone, as_of, home, over_all)
        print(f"{doc['league']} {doc['season']} · values: every men's T20 in the two years to {as_of} · likely XI from "
              f"{last[0]} to {last[1]} · {'confirmed' if doc.get('confirmed') else 'squads not fully confirmed'}")
        print("Maybe two players under one name: " + ("; ".join(f"{n} ({', '.join(ts)})" for n, ts in flags.items()) or "-"))
        for t in teams:
            squad = [dn(p) for p in t["players"]]
            over = [dn(p) for p in t["players"] if p["overseas"]]
            bought = {dn(p) for p in t["players"] if p["how"] in ("auction", "wildcard")}
            d = S.describe(db, doc["league"], t["team"], squad, over, as_of, last, values, slots)
            g = S.ground_profile(db, t["home"], date(2021, 1, 1))
            print(f"\n== {t['team']}  (home: {t['home'][0]})")
            print(f"  {'player':<24}{'role':<12}{'apps':>4} {'bat balls':>9} {'PP':>6}{'Mid':>6}{'Death':>6}  {'bowl balls':>10}"
                  f" {'PP':>6}{'Mid':>6}{'Death':>6}")
            for p in d["players"]:
                b = p["bowl"] or {}
                tag = (" new" if p["name"] in bought else "") + (" *" if p["overseas"] else "") + (" ?" if p["name"] in flags else "")
                print(f"  {(p['name'] + tag)[:24]:<24}{p['role']:<12}{p['apps_last']:>4} {p['bat_balls']:>9} "
                      f"{f(p['bat']['powerplay']):>6}{f(p['bat']['middle']):>6}{f(p['bat']['death']):>6}  {p['bowl_balls']:>10} "
                      f"{f(b.get('powerplay'), 2):>6}{f(b.get('middle'), 2):>6}{f(b.get('death'), 2):>6}")
            print("  Overs: " + "; ".join(f"{p} " + "/".join(f"{ph[0].upper()}{n}" for ph, n in by.items())
                                         for p, by in d["overs"].items()))
            ph = d["phases"]
            print("  Runs above average a game, batting: " + "  ".join(f"{k} {v:+.1f}" for k, v in ph["bat"].items())
                  + " | bowling: " + "  ".join(f"{k} {v:+.1f}" for k, v in ph["bowl"].items()))
            k = d["kinds"]
            print(f"  Pace {k['pace']['overs']} overs, spin {k['spin']['overs']}  | home: pace {g['pace']['econ']:.2f} an over, "
                  f"spin {g['spin']['econ']:.2f}, spin {100 * (g['spin']['share'] or 0):.0f}% of balls")
            print(f"  New buys in the XI: {', '.join(p for p in d['xi'] if p in bought) or '-'} · unproven in squad: "
                  + (", ".join(d["unproven"]) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
