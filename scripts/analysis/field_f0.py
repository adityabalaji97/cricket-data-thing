"""
FIELD_COVERAGE_PLAN.md, F0: is a batter's shot DIRECTION a usable signal for suggesting a field?

For a few batters (all men's T20s since 2023), from the query builder grouped by the feed's ball coordinates:
  1. coverage: the share of his balls with a position;
  2. distance by outcome: do ground balls' distances just record where fielders stood (the reason to use direction)?
  3. direction profiles: share of runs by 30-degree sector, in the batter's view (a left-hander mirrored);
  4. separation: do players differ from each other more than a player differs from himself (2023-24 v 2025-26)?
  5. cuts: how much phase and pace/spin move the profile, and how many balls each cut has.
Writes field_f0.json and an SVG rose per player next to this script's output folder.

    python scripts/analysis/field_f0.py [--since 2023-01-01] [--out /tmp/f0]
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)

PLAYERS = ["Rohit Sharma", "Liam Livingstone", "Nicholas Pooran", "Virat Kohli"]
C = 181.0          # the grid's middle; the boundary is about 181 out
SECTORS = 12       # 30 degrees each
SECTOR_NAMES = ["behind", "fine leg", "backward square leg", "square leg", "midwicket", "wide long on", "straight",
                "wide long off", "extra cover", "cover-point", "point", "third man"]


def polar(x: float, y: float, hand: str):
    """Angle (0 = behind the batter, 90 = square on his leg side, 180 = straight, 270 = square off) and distance
    (1 = the rope), in the batter's view: the grid is a fixed view of the ground with a right-hander's leg side on the
    right, so a left-hander is mirrored."""
    dx, dy = (x - C), (y - C)
    if hand == "LHB":
        dx = -dx
    return (math.degrees(math.atan2(dx, -dy)) % 360), math.hypot(dx, dy) / C


def sector(a: float) -> int:
    return int(((a + 15) % 360) // 30)


def js(p, q) -> float:
    """Jensen-Shannon distance between two sector distributions (0 same, 1 disjoint)."""
    m = [(a + b) / 2 for a, b in zip(p, q)]

    def kl(a, b):
        return sum(x * math.log2(x / y) for x, y in zip(a, b) if x > 0 and y > 0)
    return math.sqrt(max(0.0, (kl(p, m) + kl(q, m)) / 2))


def normalise(v):
    t = sum(v)
    return [x / t for x in v] if t else v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2023-01-01")
    ap.add_argument("--out", default="/tmp/f0")
    args = ap.parse_args()
    from database import get_session
    from services.query_builder_v2 import run_deliveries_query

    db = next(get_session())
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = dict(fmt="T20", include_international=False, leagues=[], start_date=date.fromisoformat(args.since),
                end_date=date.today(), metrics_perspective="batting", limit=10000)
    report = {"since": args.since, "players": {}}
    for name in PLAYERS:
        hand = max(run_deliveries_query(db, batters=[name], group_by=["bat_hand"], **base)["data"], key=lambda r: r["balls"])["bat_hand"]
        total = run_deliveries_query(db, batters=[name], group_by=["batter"], **base)["data"][0]
        rows = []
        for yr in sorted({int(args.since[:4]) + i for i in range(date.today().year - int(args.since[:4]) + 1)}):
            rows += [{**r, "season": yr} for r in run_deliveries_query(
                db, batters=[name], group_by=["wagon_x", "wagon_y", "phase", "bowl_kind"],
                start_date=date(yr, 1, 1), end_date=date(yr, 12, 31),
                **{k: v for k, v in base.items() if k not in ("start_date", "end_date")})["data"]]
        pts = [r for r in rows if r.get("wagon_x") is not None and not (int(r["wagon_x"]) == 0 and int(r["wagon_y"]) == 0)]
        catches = run_deliveries_query(db, batters=[name], group_by=["wagon_x", "wagon_y"], dismissal=["caught"], **base)["data"]
        with_pos = sum(r["balls"] for r in pts)

        # 2. distance by outcome
        dist = defaultdict(list)
        for r in pts:
            a, d = polar(r["wagon_x"], r["wagon_y"], hand)
            b4, b6 = r.get("fours") or 0, r.get("sixes") or 0
            other = (r["balls"] or 0) - b4 - b6 - (r.get("dots") or 0)
            dist["six"] += [d] * b6
            dist["four"] += [d] * b4
            dist["ran (1-3)"] += [d] * max(other, 0)
        for r in catches:
            if r.get("wagon_x") is not None and not (int(r["wagon_x"]) == 0 and int(r["wagon_y"]) == 0) and (r.get("wickets") or 0):
                dist["caught"] += [polar(r["wagon_x"], r["wagon_y"], hand)[1]] * int(r["wickets"])
        med = {k: round(sorted(v)[len(v) // 2], 2) for k, v in dist.items() if v}

        # 3-5. direction profiles (share of runs by sector), by cut
        def profile(filt):
            v = [0.0] * SECTORS
            n = 0
            for r in pts:
                if not filt(r):
                    continue
                v[sector(polar(r["wagon_x"], r["wagon_y"], hand)[0])] += r.get("runs") or 0
                n += r["balls"] or 0
            return normalise(v), n

        overall, n_all = profile(lambda r: True)
        early, n_e = profile(lambda r: r["season"] <= 2024)
        late, n_l = profile(lambda r: r["season"] >= 2025)
        cuts = {}
        for ph in ("powerplay", "middle", "death"):
            for k in ("pace bowler", "spin bowler"):
                p, n = profile(lambda r, ph=ph, k=k: r.get("phase") == ph and r.get("bowl_kind") == k)
                cuts[f"{ph}|{k.split()[0]}"] = {"balls": n, "profile": [round(x, 3) for x in p],
                                                 "js_v_overall": round(js(p, overall), 3) if n else None}
        import random
        rnd = random.Random(7)
        floor = []
        for _ in range(40):
            a_, b_ = [0.0] * SECTORS, [0.0] * SECTORS
            for r in pts:
                (a_ if rnd.random() < 0.5 else b_)[sector(polar(r["wagon_x"], r["wagon_y"], hand)[0])] += r.get("runs") or 0
            floor.append(js(normalise(a_), normalise(b_)))
        noise = round(sum(floor) / len(floor), 3)
        report["players"][name] = {
            "hand": hand, "balls": total["balls"], "with_position": with_pos,
            "coverage": round(with_pos / total["balls"], 3) if total["balls"] else None,
            "median_distance": med, "overall": [round(x, 3) for x in overall],
            "self_split": {"2023-24": n_e, "2025-26": n_l, "js": round(js(early, late), 3)}, "noise_floor": noise, "cuts": cuts,
        }
        write_rose(out_dir / f"{name.replace(' ', '_')}.svg", name, overall, hand)
        print(f"{name}: {hand}, {total['balls']} balls, {round(100 * with_pos / total['balls'])}% with a position; "
              f"median distance {med}; self-split JS {report['players'][name]['self_split']['js']}")

    # The average batter of each hand, per cut (direct SQL on delivery_details: sectors of the batter's-view angle).
    from sqlalchemy import text
    pop = {}
    for hand in ("RHB", "LHB"):
        sx = "(wagon_x - 181)" if hand == "RHB" else "(181 - wagon_x)"
        rows = db.execute(text(f"""
            SELECT phase_, bowl_kind, sec, SUM(COALESCE(batruns, 0)) AS runs, COUNT(*) AS balls FROM (
              SELECT CASE WHEN over < 6 THEN 'powerplay' WHEN over < 15 THEN 'middle' ELSE 'death' END AS phase_, bowl_kind,
                     (FLOOR(((DEGREES(ATAN2({sx}, -(wagon_y - 181))) + 360 + 15)::numeric % 360) / 30))::int AS sec, batruns
              FROM delivery_details
              WHERE format = 'T20' AND gender = 'male' AND bat_hand = :h AND match_date >= :since
                AND wagon_x IS NOT NULL AND NOT (wagon_x = 0 AND wagon_y = 0)) t
            GROUP BY 1, 2, 3"""), {"h": hand, "since": args.since}).fetchall()
        agg = defaultdict(lambda: [0.0] * SECTORS)
        balls = defaultdict(int)
        for ph, k, sec, runs, n in rows:
            for key in ("all", f"{ph}|{(k or '').split()[0]}"):
                agg[key][int(sec) % SECTORS] += float(runs)
                balls[key] += int(n)
        pop[hand] = {k: {"profile": normalise(v), "balls": balls[k]} for k, v in agg.items()}
    report["population"] = {h: {k: {"balls": v["balls"], "profile": [round(x, 3) for x in v["profile"]]} for k, v in d.items()} for h, d in pop.items()}
    for name, rep in report["players"].items():
        h = rep["hand"]
        rep["js_v_average"] = round(js(rep["overall"], pop[h]["all"]["profile"]), 3)
        for cut, c in rep["cuts"].items():
            if c["balls"] and cut in pop[h]:
                c["js_v_average"] = round(js(c["profile"], pop[h][cut]["profile"]), 3)

    names = list(report["players"])
    report["between"] = {f"{a} v {b}": round(js(report["players"][a]["overall"], report["players"][b]["overall"]), 3)
                         for i, a in enumerate(names) for b in names[i + 1:]}
    (out_dir / "field_f0.json").write_text(json.dumps(report, indent=1))
    print("between players:", report["between"])
    for name in names:
        c = report["players"][name]["cuts"]
        print(name, "noise", report["players"][name]["noise_floor"], "v average", report["players"][name].get("js_v_average"),
              {k: (v["balls"], v["js_v_overall"], v.get("js_v_average")) for k, v in c.items()})
    print("wrote", out_dir)
    return 0


def write_rose(path: Path, name: str, prof, hand: str) -> None:
    """A rose of share of runs by sector, behind at the top, leg side on the right (batter's view)."""
    W, cx, cy, R = 360, 180, 190, 140
    mx = max(prof) or 1
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 380" font-family="sans-serif">',
             '<rect width="100%" height="100%" fill="#0a0c11"/>',
             f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="#12301c" stroke="#3a4a3f"/>',
             f'<text x="{cx}" y="22" fill="#e8ecf2" font-size="15" text-anchor="middle">{name} ({hand}, batter\'s view)</text>']
    for i, v in enumerate(prof):
        a0, a1 = math.radians(i * 30 - 15 - 90), math.radians(i * 30 + 15 - 90)
        r = R * (v / mx) ** 0.5
        parts.append(f'<path d="M{cx},{cy} L{cx + r * math.cos(a0):.1f},{cy + r * math.sin(a0):.1f} '
                     f'A{r:.1f},{r:.1f} 0 0 1 {cx + r * math.cos(a1):.1f},{cy + r * math.sin(a1):.1f} Z" fill="#c6f432" fill-opacity="0.75"/>')
        am = math.radians(i * 30 - 90)
        parts.append(f'<text x="{cx + (R + 14) * math.cos(am):.1f}" y="{cy + (R + 14) * math.sin(am) + 4:.1f}" fill="#9aa4b2" '
                     f'font-size="10" text-anchor="middle">{round(100 * v)}%</text>')
    parts.append(f'<text x="{cx}" y="{cy - R - 22}" fill="#6b7685" font-size="10" text-anchor="middle">behind</text>')
    parts.append('</svg>')
    path.write_text("".join(parts))


if __name__ == "__main__":
    sys.exit(main())
