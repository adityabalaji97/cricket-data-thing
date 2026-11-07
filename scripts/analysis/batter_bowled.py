"""
Do some batters get bowled or LBW more than others, as a trait? (7 Nov 2026; the batter's side of stumps_attack.py)

Per batter, all men's T20s, 2023-24 v 2025-26: his dismissals bowled + LBW as a share of his dismissals, against a
typical batter dismissed in the same competitions and years by the same kind of bowler (weighted by his dismissals in
each). Tests: does it repeat (Spearman, period to period)? Is it tied to how well he bats (average, strike rate), now
or next period? Bowled and LBW alone too (LBW leans on DRS and umpiring).
"""
from __future__ import annotations

import logging
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)

MIN_OUTS = 20
HOW = {"bowled": "b", "leg before wicket": "l", "caught": "c", "caught and bowled": "c", "stumped": "s", "hit wicket": "s"}


def spearman(a, b):
    from scipy.stats import spearmanr

    return float(spearmanr(a, b).correlation) if len(a) > 2 else float("nan")


def main() -> int:
    from sqlalchemy import text

    from database import get_session

    db = next(get_session())
    rows = db.execute(text("""
        SELECT p_out, bowl_kind, competition, SUBSTRING(match_date, 1, 4) yr,
               CASE WHEN match_date < '2025-01-01' THEN 'early' ELSE 'late' END period, dismissal, COUNT(*)
        FROM delivery_details
        WHERE format = 'T20' AND gender = 'male' AND match_date >= '2023-01-01' AND p_out IS NOT NULL
          AND bowl_kind IN ('pace bowler', 'spin bowler')
          AND dismissal IN ('bowled', 'leg before wicket', 'caught', 'caught and bowled', 'stumped', 'hit wicket')
        GROUP BY 1, 2, 3, 4, 5, 6""")).fetchall()
    bat = db.execute(text("""
        SELECT p_bat, CASE WHEN match_date < '2025-01-01' THEN 'early' ELSE 'late' END period,
               SUM(CASE WHEN COALESCE(wide, 0) = 0 THEN 1 ELSE 0 END) balls, SUM(COALESCE(batruns, 0)) runs
        FROM delivery_details WHERE format = 'T20' AND gender = 'male' AND match_date >= '2023-01-01' AND p_bat IS NOT NULL
        GROUP BY 1, 2""")).fetchall()
    names = dict(db.execute(text("SELECT pid, display_name FROM player_identity")).fetchall())
    runs = {(p, per): (b, r) for p, per, b, r in bat}

    lg = defaultdict(lambda: defaultdict(int))
    for pid, kind, comp, yr, per, how, n in rows:
        lg[(comp, yr, kind)][HOW[how]] += n
    me = defaultdict(lambda: {"b": 0, "l": 0, "n": 0, "xb": 0.0, "xl": 0.0, "xbl": 0.0, "pace": 0})
    for pid, kind, comp, yr, per, how, n in rows:
        x, L = me[(pid, per)], lg[(comp, yr, kind)]
        tot = sum(L.values())
        x["n"] += n
        x["b"] += n if HOW[how] == "b" else 0
        x["l"] += n if HOW[how] == "l" else 0
        x["pace"] += n if kind == "pace bowler" else 0
        x["xb"] += n * L["b"] / tot
        x["xl"] += n * L["l"] / tot
        x["xbl"] += n * (L["b"] + L["l"]) / tot

    def m(pid, per):
        x = me[(pid, per)]
        b, r = runs.get((pid, per), (0, 0))
        return {"bl": (x["b"] + x["l"]) / x["xbl"] - 1, "b": x["b"] / x["xb"] - 1 if x["xb"] else 0,
                "l": x["l"] / x["xl"] - 1 if x["xl"] else 0, "raw": (x["b"] + x["l"]) / x["n"],
                "avg": r / x["n"], "sr": 100 * r / b if b else None, "n": x["n"], "pace": x["pace"] / x["n"]}

    pids = {p for p, per in list(me) if me.get((p, "early"), {}).get("n", 0) >= MIN_OUTS and me.get((p, "late"), {}).get("n", 0) >= MIN_OUTS}
    P = [(names.get(p, p), m(p, "early"), m(p, "late")) for p in pids]
    print(f"{len(P)} batters with {MIN_OUTS}+ dismissals (to pace or spin, not run-outs) in each period; "
          f"median dismissals {sorted(e['n'] for _, e, _ in P)[len(P) // 2]}")
    for k in ("bl", "b", "l", "raw", "avg", "sr", "pace"):
        print(f"  repeat {k:5s} rho {spearman([e[k] for _, e, _ in P], [l[k] for _, _, l in P]):+.2f}")
    for a, b in (("bl", "avg"), ("bl", "sr"), ("b", "avg"), ("bl", "pace")):
        print(f"  {a} v {b}: same {spearman([e[a] for _, e, _ in P], [e[b] for _, e, _ in P]):+.2f}, "
              f"next {spearman([e[a] for _, e, _ in P], [l[b] for _, _, l in P]):+.2f}")
    hi = sorted(P, key=lambda p: -(p[1]["bl"] + p[2]["bl"]))[:12]
    print("bowled/LBW more than typical, both periods:")
    for n, e, l in hi:
        print(f"   {n:24s} {e['bl']:+.0%} {l['bl']:+.0%}  (raw {e['raw']:.0%}/{l['raw']:.0%}, {e['n']}+{l['n']} outs, avg {e['avg']:.0f}/{l['avg']:.0f})")
    lo = sorted(P, key=lambda p: (p[1]["bl"] + p[2]["bl"]))[:8]
    print("least:", [(n, f"{e['bl']:+.0%}", f"{l['bl']:+.0%}") for n, e, l in lo])
    return 0


if __name__ == "__main__":
    sys.exit(main())
