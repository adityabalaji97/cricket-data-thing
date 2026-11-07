"""
Is "attacking the stumps" a real, useful bowling trait? (7 Nov 2026)

Candidate measures, per bowler, all men's T20s, 2023-24 v 2025-26 (pace and spin separately):
  share     bowled + LBW as a share of his wickets (the user's idea)
  rate      bowled + LBW per 120 balls
  on_stumps share of his line-tagged balls on the stumps
  attack    share of tagged balls on the stumps AND full / good length / yorker (the ball that hits)
  convert   bowled + LBW per 100 tagged balls on the stumps
Tests: does it repeat (Spearman across bowlers, period to period)? Does the input (attack) explain the outcome
(share, rate)? Is it related to what matters (economy, balls per wicket), now and next period?
"""
from __future__ import annotations

import logging
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)



def spearman(a, b):
    from scipy.stats import spearmanr

    return float(spearmanr(a, b).correlation) if len(a) > 2 else float("nan")

MIN_BALLS, MIN_TAGGED, MIN_WKTS = 600, 300, 15


def main() -> int:
    from sqlalchemy import text

    from database import get_session

    db = next(get_session())
    rows = db.execute(text("""
        SELECT p_bowl, bowl_kind, CASE WHEN match_date < '2025-01-01' THEN 'early' ELSE 'late' END period,
               competition, SUBSTRING(match_date, 1, 4) yr,
               SUM(CASE WHEN dismissal = 'bowled' THEN 1 ELSE 0 END) bwd,
               SUM(CASE WHEN COALESCE(wide, 0) = 0 AND COALESCE(noball, 0) = 0 THEN 1 ELSE 0 END) balls,
               SUM(COALESCE(score, 0) - COALESCE(byes, 0) - COALESCE(legbyes, 0)) runs,
               SUM(CASE WHEN dismissal IN ('caught', 'bowled', 'leg before wicket', 'stumped', 'hit wicket') THEN 1 ELSE 0 END) wkts,
               SUM(CASE WHEN dismissal IN ('bowled', 'leg before wicket') THEN 1 ELSE 0 END) blw,
               SUM(CASE WHEN line IS NOT NULL THEN 1 ELSE 0 END) tagged,
               SUM(CASE WHEN line = 'ON_THE_STUMPS' THEN 1 ELSE 0 END) on_st,
               SUM(CASE WHEN line = 'ON_THE_STUMPS' AND length IN ('FULL', 'GOOD_LENGTH', 'YORKER') THEN 1 ELSE 0 END) attack,
               SUM(CASE WHEN line = 'ON_THE_STUMPS' AND dismissal IN ('bowled', 'leg before wicket') THEN 1 ELSE 0 END) blw_on
        FROM delivery_details
        WHERE format = 'T20' AND gender = 'male' AND match_date >= '2023-01-01' AND p_bowl IS NOT NULL
          AND bowl_kind IN ('pace bowler', 'spin bowler')
        GROUP BY 1, 2, 3, 4, 5""")).fetchall()
    names = dict(db.execute(text("SELECT pid, display_name FROM player_identity")).fetchall())
    # Against the average for where and when he bowled: each competition-year-kind's rates, applied to his own balls,
    # wickets and tagged balls (LBWs vary 4-9% of wickets by competition, with or without DRS, and associates' T20Is
    # give up bowleds and LBWs freely).
    KEYS = ("balls", "runs", "wkts", "blw", "tagged", "on_st", "attack", "blw_on", "bwd")
    lg = defaultdict(lambda: dict.fromkeys(KEYS, 0))
    for r in rows:
        pid, kind, period, comp, yr, bwd, balls, runs, wkts, blw, tagged, on_st, attack, blw_on = r
        x = lg[(comp, yr, kind)]
        for k, v in zip(KEYS, (balls, runs, wkts, blw, tagged, on_st, attack, blw_on, bwd)):
            x[k] += v or 0
    d = defaultdict(lambda: defaultdict(lambda: dict.fromkeys(KEYS + ("x_blw_w", "x_bwd_w", "x_attack", "x_blw_b"), 0.0)))
    for r in rows:
        pid, kind, period, comp, yr, bwd, balls, runs, wkts, blw, tagged, on_st, attack, blw_on = r
        x, L = d[(pid, kind)][period], lg[(comp, yr, kind)]
        for k, v in zip(KEYS, (balls, runs, wkts, blw, tagged, on_st, attack, blw_on, bwd)):
            x[k] += v or 0
        if L["wkts"]:
            x["x_blw_w"] += (wkts or 0) * L["blw"] / L["wkts"]
            x["x_bwd_w"] += (wkts or 0) * L["bwd"] / L["wkts"]
        if L["tagged"]:
            x["x_attack"] += (tagged or 0) * L["attack"] / L["tagged"]
        if L["balls"]:
            x["x_blw_b"] += (balls or 0) * L["blw"] / L["balls"]

    def m(r):
        return {"share": r["blw"] / r["wkts"] if r["wkts"] else None,
                "rate": 120 * r["blw"] / r["balls"],
                "on_stumps": r["on_st"] / r["tagged"] if r["tagged"] else None,
                "attack": r["attack"] / r["tagged"] if r["tagged"] else None,
                "convert": 100 * r["blw_on"] / r["on_st"] if r["on_st"] else None,
                # Against the average where he bowled: + is more than expected, as a share of what was expected.
                "share_adj": r["blw"] / r["x_blw_w"] - 1 if r["x_blw_w"] else None,
                "bowled_adj": r["bwd"] / r["x_bwd_w"] - 1 if r["x_bwd_w"] else None,
                "attack_adj": r["attack"] / r["x_attack"] - 1 if r["x_attack"] else None,
                "rate_adj": r["blw"] / r["x_blw_b"] - 1 if r["x_blw_b"] else None,
                "econ": 6 * r["runs"] / r["balls"], "bpw": r["balls"] / r["wkts"] if r["wkts"] else None,
                "blw_n": r["blw"], "wkts": r["wkts"]}

    for kind in ("pace bowler", "spin bowler"):
        pairs = []
        for (pid, k), per in d.items():
            if k != kind or "early" not in per or "late" not in per:
                continue
            e, l = per["early"], per["late"]
            if min(e["balls"], l["balls"]) < MIN_BALLS or min(e["tagged"], l["tagged"]) < MIN_TAGGED or min(e["wkts"], l["wkts"]) < MIN_WKTS:
                continue
            pairs.append((names.get(pid, pid), m(e), m(l)))
        print(f"\n== {kind}: {len(pairs)} bowlers ({MIN_BALLS}+ balls, {MIN_TAGGED}+ tagged, {MIN_WKTS}+ wickets in each period)")
        print("median blw/wkts in a period:", sorted(p[1]["blw_n"] for p in pairs)[len(pairs) // 2], "/",
              sorted(p[1]["wkts"] for p in pairs)[len(pairs) // 2])
        for k in ("share", "share_adj", "bowled_adj", "rate", "rate_adj", "on_stumps", "attack", "attack_adj", "convert", "econ", "bpw"):
            ok = [p for p in pairs if p[1][k] is not None and p[2][k] is not None]
            print(f"  repeat {k:10s} rho {spearman([p[1][k] for p in ok], [p[2][k] for p in ok]):+.2f}")
        for a, b in (("attack_adj", "share_adj"), ("attack_adj", "bowled_adj"), ("share_adj", "econ"), ("share_adj", "bpw"), ("attack_adj", "econ"), ("attack", "share"), ("attack", "rate"), ("on_stumps", "rate"), ("share", "econ"), ("share", "bpw"),
                     ("attack", "econ"), ("attack", "bpw"), ("rate", "bpw")):
            ok = [p for p in pairs if p[1][a] is not None and p[1][b] is not None]
            nxt = [p for p in pairs if p[1][a] is not None and p[2][b] is not None]
            print(f"  {a} v {b}: same period {spearman([p[1][a] for p in ok], [p[1][b] for p in ok]):+.2f}, "
                  f"next period {spearman([p[1][a] for p in nxt], [p[2][b] for p in nxt]):+.2f}")
        both = sorted(pairs, key=lambda p: -(p[1]["attack"] + p[2]["attack"]))[:6]
        print("  most stump-attacking (both periods):", [(n, round(e["attack"], 2), round(l["attack"], 2), f"{e['blw_n']}+{l['blw_n']} b/lbw") for n, e, l in both])
        hi = sorted(pairs, key=lambda p: -(p[1]["share"] + p[2]["share"]))[:6]
        print("  highest bowled+LBW share:", [(n, round(e["share"], 2), round(l["share"], 2)) for n, e, l in hi])
        hi = sorted(pairs, key=lambda p: -(p[1]["share_adj"] + p[2]["share_adj"]))[:8]
        print("  most above where they bowled (b+lbw share):", [(n, f"{e['share_adj']:+.0%}", f"{l['share_adj']:+.0%}") for n, e, l in hi])
        lo = sorted(pairs, key=lambda p: (p[1]["share_adj"] + p[2]["share_adj"]))[:5]
        print("  most below:", [(n, f"{e['share_adj']:+.0%}", f"{l['share_adj']:+.0%}") for n, e, l in lo])
    return 0


if __name__ == "__main__":
    sys.exit(main())
