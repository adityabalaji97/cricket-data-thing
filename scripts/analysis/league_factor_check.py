"""
XI_BUILDER_PLAN.md X4d: do league-strength factors turn a player's record elsewhere into a useful IPL expectation?

Per player-season, from delivery_details (men's T20s): batting strike rate and average; bowling economy and wickets per
four overs in each role (phase x pace/spin). A factor per competition and measure = how the measure changes for players
who did the same thing in that competition and then in the IPL (the IPL season after, or the same year), weighted by
the smaller sample. Factors are fitted on moves into IPL seasons up to 2024 and tested on 2025-26.

The test: players with little IPL record before (under 120 balls in the role in the two IPL seasons before) who then
had 60+ in an IPL season. Their IPL number predicted three ways, each shrunk the same way toward the IPL average:
  avg      the IPL average for the role (the baseline to beat)
  raw      their record elsewhere in the two seasons before, unadjusted
  adjusted that record times the competition's factor
Mean absolute error, weighted by IPL balls. A factor is worth using only if "adjusted" beats "avg".

    python scripts/analysis/league_factor_check.py
"""
from __future__ import annotations

import logging
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)

IPL = "IPL"
MIN_SRC, MIN_IPL, PRIOR_MAX, MIN_PAIRS = 120, 60, 120, 15
FIT_TO = int(sys.argv[1]) if len(sys.argv) > 1 else 2024   # factors from IPL seasons up to here; tested after
SHRINK = {"bat": 120, "bowl": 240}


def main() -> int:
    from sqlalchemy import text

    from database import get_session

    db = next(get_session())
    bat = db.execute(text("""
        SELECT p_bat, competition, SUBSTRING(match_date, 1, 4)::int y,
               SUM(CASE WHEN COALESCE(wide, 0) = 0 THEN 1 ELSE 0 END) balls, SUM(COALESCE(batruns, 0)) runs,
               SUM(CASE WHEN p_out = p_bat AND dismissal <> 'run out' THEN 1 ELSE 0 END) outs
        FROM delivery_details WHERE format = 'T20' AND gender = 'male' AND match_date >= '2019-01-01' AND p_bat IS NOT NULL
        GROUP BY 1, 2, 3""")).fetchall()
    bowl = db.execute(text("""
        SELECT p_bowl, competition, SUBSTRING(match_date, 1, 4)::int y,
               CASE WHEN over < 6 THEN 'powerplay' WHEN over < 15 THEN 'middle' ELSE 'death' END ph,
               CASE WHEN bowl_kind = 'spin bowler' THEN 'spin' ELSE 'pace' END k,
               SUM(CASE WHEN COALESCE(wide, 0) = 0 AND COALESCE(noball, 0) = 0 THEN 1 ELSE 0 END) balls,
               SUM(COALESCE(score, 0) - COALESCE(byes, 0) - COALESCE(legbyes, 0)) runs,
               SUM(CASE WHEN dismissal IN ('caught', 'bowled', 'leg before wicket', 'stumped', 'hit wicket',
                                           'caught and bowled') THEN 1 ELSE 0 END) wkts
        FROM delivery_details WHERE format = 'T20' AND gender = 'male' AND match_date >= '2019-01-01' AND p_bowl IS NOT NULL
          AND bowl_kind IN ('pace bowler', 'spin bowler')
        GROUP BY 1, 2, 3, 4, 5""")).fetchall()

    # rec[(measure_group, pid)][(comp, year)] = {balls, a, b}: measure = a / b (scaled)
    rec = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    for pid, comp, y, balls, runs, outs in bat:
        r = rec[("bat", pid)][(comp, y)]
        r["balls"] += balls
        r["runs"] += runs
        r["outs"] += outs
    for pid, comp, y, ph, k, balls, runs, wkts in bowl:
        if (ph, k) not in (("powerplay", "pace"), ("middle", "spin"), ("death", "pace")):
            continue
        r = rec[(f"{ph}|{k}", pid)][(comp, y)]
        r["balls"] += balls
        r["runs"] += runs
        r["wkts"] += wkts

    MEASURES = {"bat": [("strike_rate", lambda r: 100 * r["runs"] / r["balls"] if r["balls"] else None),
                        ("average", lambda r: r["runs"] / r["outs"] if r["outs"] else None)],
                "bowl": [("economy", lambda r: 6 * r["runs"] / r["balls"] if r["balls"] else None),
                         ("wickets_per_24", lambda r: 24 * r["wkts"] / r["balls"] if r["balls"] else None)]}

    def side(group):
        return "bat" if group == "bat" else "bowl"

    def pooled(recs):
        t = defaultdict(float)
        for r in recs:
            for k, v in r.items():
                t[k] += v
        return t

    groups = sorted({g for g, _ in rec})
    for group in groups:
        sd = side(group)
        players = {pid: v for (g, pid), v in rec.items() if g == group}
        # IPL average per season for the role (the baseline), as pooled totals.
        ipl_year = defaultdict(list)
        for pid, seasons in players.items():
            for (comp, y), r in seasons.items():
                if comp == IPL:
                    ipl_year[y].append(r)
        for mname, f in MEASURES[sd]:
            # 1. Factors from moves into IPL seasons <= 2024: elsewhere in Y-1 or Y, IPL in Y.
            pairs = defaultdict(list)  # comp -> [(ratio, weight)]
            for pid, seasons in players.items():
                for (comp, y), r in seasons.items():
                    if comp != IPL:
                        continue
                    if y > FIT_TO or r["balls"] < MIN_IPL:
                        continue
                    mi = f(r)
                    for (c2, y2), r2 in seasons.items():
                        if c2 == IPL or y2 not in (y - 1, y) or r2["balls"] < MIN_SRC:
                            continue
                        ms = f(r2)
                        if mi and ms:
                            pairs[c2].append((mi / ms, min(r["balls"], r2["balls"])))
            factors = {c: sum(a * w for a, w in v) / sum(w for _, w in v) for c, v in pairs.items() if len(v) >= MIN_PAIRS}
            # 2. Test on IPL seasons 2025-26: newcomers (thin IPL record the two seasons before).
            errs = defaultdict(lambda: [0.0, 0.0])  # method -> [sum |err| * w, sum w]
            n = 0
            for pid, seasons in players.items():
                for (comp, y), r in seasons.items():
                    if comp != IPL or y <= FIT_TO or r["balls"] < MIN_IPL:
                        continue
                    prior_ipl = sum(r2["balls"] for (c2, y2), r2 in seasons.items() if c2 == IPL and y2 in (y - 2, y - 1))
                    if prior_ipl >= PRIOR_MAX:
                        continue
                    src = [(c2, r2) for (c2, y2), r2 in seasons.items() if c2 != IPL and y2 in (y - 2, y - 1)]
                    src_bal = sum(r2["balls"] for _, r2 in src)
                    if src_bal < MIN_SRC:
                        continue
                    base = f(pooled([x for yy, xs in ipl_year.items() if yy in (y - 2, y - 1) for x in xs]))
                    actual = f(r)
                    raw = f(pooled([r2 for _, r2 in src]))
                    if None in (base, actual, raw):
                        continue
                    # Adjusted: each source competition's number times its factor (no factor: left out), weighted by balls.
                    adj_parts = [(f(r2) * factors[c2], r2["balls"]) for c2, r2 in src if c2 in factors and f(r2)]
                    adj = sum(a * w for a, w in adj_parts) / sum(w for _, w in adj_parts) if adj_parts else None
                    k = SHRINK[sd]
                    shrink = lambda v, b: (v * b + base * k) / (b + k)  # noqa: E731
                    w = r["balls"]
                    for name, pred in (("avg", base), ("raw", shrink(raw, src_bal)),
                                       ("adjusted", shrink(adj, sum(b for _, b in adj_parts)) if adj else None)):
                        if pred is None:
                            continue
                        errs[name][0] += abs(pred - actual) * w
                        errs[name][1] += w
                    n += 1
            if not n:
                continue
            res = {m: e[0] / e[1] for m, e in errs.items() if e[1]}
            top = sorted(factors.items(), key=lambda kv: -len(pairs[kv[0]]))[:6]
            print(f"{group:16s} {mname:15s} n={n:3d} | MAE avg {res.get('avg', 0):6.2f} raw {res.get('raw', 0):6.2f} "
                  f"adjusted {res.get('adjusted', 0):6.2f} | factors: " + ", ".join(f"{c} {v:.2f} ({len(pairs[c])})" for c, v in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
