"""
FIELD_COVERAGE_PLAN.md, F2: suggested fields for a few batters and cuts, drawn as SVG for the user's sense check.

    python articles/fields/prototype.py --out /tmp/fields [--since 2023-01-01]
"""
import argparse
import json
import logging
import math
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
logging.disable(logging.INFO)

from services import field_model as F  # noqa: E402

CASES = [("Rohit Sharma", "powerplay", "pace bowler"), ("Rohit Sharma", "middle", "spin bowler"), ("Rohit Sharma", "death", "pace bowler"),
         ("Liam Livingstone", "powerplay", "pace bowler"), ("Liam Livingstone", "middle", "spin bowler"), ("Liam Livingstone", "death", "pace bowler")]
OVERS = {"powerplay": (0, 5), "middle": (6, 14), "death": (15, 19)}


def average_profiles(db, since):
    """The average batter of each hand, per phase and bowler kind, in 5-degree bins (delivery_details, direct SQL)."""
    from sqlalchemy import text
    out = {}
    for hand in ("RHB", "LHB"):
        sx = "(wagon_x - 181)" if hand == "RHB" else "(181 - wagon_x)"
        rows = db.execute(text(f"""
            SELECT CASE WHEN over < 6 THEN 'powerplay' WHEN over < 15 THEN 'middle' ELSE 'death' END ph, bowl_kind,
                   (FLOOR(((DEGREES(ATAN2({sx}, -(wagon_y - 181))) + 360)::numeric % 360) / {F.BIN}))::int b,
                   SUM(CASE WHEN batruns = 4 THEN 1 ELSE 0 END) fours, SUM(CASE WHEN batruns = 6 THEN 1 ELSE 0 END) sixes,
                   SUM(CASE WHEN batruns BETWEEN 1 AND 3 THEN batruns ELSE 0 END) ran,
                   SUM(CASE WHEN LOWER(out) = 'true' AND LOWER(bat_out) = 'true' AND LOWER(dismissal) = 'caught'
                            AND SQRT(POWER(wagon_x - 181, 2) + POWER(wagon_y - 181, 2)) < 0.6 * 181 THEN 1 ELSE 0 END) cin,
                   SUM(CASE WHEN LOWER(out) = 'true' AND LOWER(bat_out) = 'true' AND LOWER(dismissal) = 'caught'
                            AND SQRT(POWER(wagon_x - 181, 2) + POWER(wagon_y - 181, 2)) >= 0.6 * 181 THEN 1 ELSE 0 END) cout,
                   COUNT(*) balls
            FROM delivery_details
            WHERE format = 'T20' AND gender = 'male' AND bat_hand = :h AND match_date >= :since
              AND wagon_x IS NOT NULL AND NOT (wagon_x = 0 AND wagon_y = 0)
            GROUP BY 1, 2, 3"""), {"h": hand, "since": since}).fetchall()
        for ph, kind, b, fours, sixes, ran, cin, cout, balls in rows:
            p = out.setdefault((hand, ph, kind), F.empty_profile())
            i = int(b) % F.NBINS
            for k, v in (("four", fours), ("six", sixes), ("ran", ran), ("catch_in", cin), ("catch_out", cout), ("balls", balls)):
                p[k][i] += float(v or 0)
    return out


def player_profile(db, name, phase, kind, since):
    from services.query_builder_v2 import run_deliveries_query
    base = dict(fmt="T20", include_international=False, leagues=[], start_date=date.fromisoformat(since), end_date=date.today(),
                metrics_perspective="batting", limit=10000, batters=[name], bowl_kind=[kind],
                over_min=OVERS[phase][0], over_max=OVERS[phase][1])
    hand = max(run_deliveries_query(db, group_by=["bat_hand"], **{k: v for k, v in base.items() if k not in ("bowl_kind", "over_min", "over_max")})["data"],
               key=lambda r: r["balls"])["bat_hand"]
    p = F.empty_profile()
    for r in run_deliveries_query(db, group_by=["wagon_x", "wagon_y"], **base)["data"]:
        if r.get("wagon_x") is None or (int(r["wagon_x"]) == 0 and int(r["wagon_y"]) == 0):
            continue
        a, _ = F.angle_of(r["wagon_x"], r["wagon_y"], hand)
        i = int(a // F.BIN) % F.NBINS
        f4, f6 = r.get("fours") or 0, r.get("sixes") or 0
        p["four"][i] += f4
        p["six"][i] += f6
        p["ran"][i] += max(0, (r.get("runs") or 0) - 4 * f4 - 6 * f6)
        p["balls"][i] += r.get("balls") or 0
    for r in run_deliveries_query(db, group_by=["wagon_x", "wagon_y"], dismissal=["caught"], **base)["data"]:
        if r.get("wagon_x") is None or (int(r["wagon_x"]) == 0 and int(r["wagon_y"]) == 0) or not r.get("wickets"):
            continue
        a, d = F.angle_of(r["wagon_x"], r["wagon_y"], hand)
        p["catch_in" if d < 0.6 else "catch_out"][int(a // F.BIN) % F.NBINS] += r["wickets"]
    return hand, p


def svg(title, sub, s, p_own, hand):
    """The ground: his scoring as faint wedges, the standard field as grey rings, his field in lime with its reach."""
    W, cx, cy, R = 380, 190, 205, 160
    ring = 0.45
    xy = lambda a, r: (cx + R * r * math.sin(math.radians(a)), cy - R * r * math.cos(math.radians(a)))  # noqa: E731
    runs = [p_own["four"][i] * 4 + p_own["six"][i] * 6 + p_own["ran"][i] for i in range(F.NBINS)]
    mx = max(runs) or 1
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 470" font-family="Helvetica, Arial, sans-serif">',
         '<rect width="100%" height="100%" fill="#0a0c11"/>',
         f'<text x="16" y="24" fill="#e8ecf2" font-size="15" font-weight="700">{title}</text>',
         f'<text x="16" y="42" fill="#9aa4b2" font-size="11">{sub}</text>',
         f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="#12301c" stroke="#3a4a3f"/>',
         f'<circle cx="{cx}" cy="{cy}" r="{R * ring}" fill="none" stroke="#3a4a3f" stroke-dasharray="4 4"/>']
    for i, v in enumerate(runs):
        if v <= 0:
            continue
        a0, a1 = i * F.BIN, (i + 1) * F.BIN
        r = 0.15 + 0.85 * (v / mx) ** 0.6
        (x0, y0), (x1, y1) = xy(a0, r), xy(a1, r)
        o.append(f'<path d="M{cx},{cy} L{x0:.1f},{y0:.1f} A{R * r:.1f},{R * r:.1f} 0 0 1 {x1:.1f},{y1:.1f} Z" fill="#5b9bf0" fill-opacity="0.28"/>')
    o.append(f'<rect x="{cx - 3}" y="{cy - 9}" width="6" height="18" rx="2" fill="#c9b27c"/>')
    for f in s["standard"]:
        x, y = xy(f["angle"], ring if f["ring"] == "in" else 0.96)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="none" stroke="#8a94a3" stroke-width="1.5"/>')
    for f in s["field"]:
        rr = ring if f["ring"] == "in" else 0.96
        reach = F.REACH_IN if f["ring"] == "in" else F.REACH_OUT
        (x0, y0), (x1, y1) = xy(f["angle"] - reach, rr), xy(f["angle"] + reach, rr)
        o.append(f'<path d="M{x0:.1f},{y0:.1f} A{R * rr:.1f},{R * rr:.1f} 0 0 1 {x1:.1f},{y1:.1f}" fill="none" stroke="#c6f432" stroke-opacity="0.55" stroke-width="7" stroke-linecap="round"/>')
        x, y = xy(f["angle"], rr)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="#c6f432" stroke="#0a0c11" stroke-width="1.5"/>')
    moved = ", ".join(sorted({m['name'] for m in s['moved']['to']})) or "none"
    gone = ", ".join(sorted({m['name'] for m in s['moved']['from']})) or "none"
    o.append(f'<text x="16" y="392" fill="#c6f432" font-size="12">In for him: {moved}</text>')
    o.append(f'<text x="16" y="410" fill="#9aa4b2" font-size="12">Out of the standard field: {gone}</text>')
    o.append(f'<text x="16" y="430" fill="#9aa4b2" font-size="11">Covers {round(100 * s["covered"])}% of the value of his balls; the standard field {round(100 * s["covered_by_standard"])}%</text>')
    o.append(f'<text x="16" y="450" fill="#6b7685" font-size="10">{s["own_balls"]} of his balls · a model of where he hits it, not his actual fields · {hand}, batter\'s view</text>')
    o.append('</svg>')
    return "".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/fields")
    ap.add_argument("--since", default="2023-01-01")
    args = ap.parse_args()
    from database import get_session
    db = next(get_session())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    avg = average_profiles(db, args.since)
    svgs, report = [], []
    for name, phase, kind in CASES:
        hand, own = player_profile(db, name, phase, kind, args.since)
        s = F.suggest(own, avg[(hand, phase, kind)], phase)
        k = kind.split()[0]
        title = f"{name} v {k}, {phase}"
        sub = "Lime: a field for him (with each fielder's reach) · grey rings: the standard field · blue: where he scores"
        svgs.append(svg(title, sub, s, own, hand))
        report.append({"case": title, **{k2: s[k2] for k2 in ("covered", "covered_by_standard", "gain", "own_balls")},
                       "in": [m["name"] for m in s["moved"]["to"]], "out": [m["name"] for m in s["moved"]["from"]],
                       "field": [f"{f['name']} ({f['ring']})" for f in s["field"]]})
        print(json.dumps(report[-1]))
    (out / "fields.html").write_text('<html><body style="margin:0;background:#0a0c11;display:grid;grid-template-columns:1fr 1fr 1fr;width:1140px">'
                                     + "".join(f'<div style="width:380px">{x}</div>' for x in svgs) + "</body></html>")
    (out / "fields.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
