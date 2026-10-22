"""
First-ball boundaries: how often a batter's first ball goes for four or six, and where Abhishek Sharma, Sanju Samson
and Vaibhav Sooryavanshi sit. Men's T20s; "first ball" = the first legal ball a batter faces in an innings
(batter_ball_number = 1). Every number comes from data/first_ball.json (data.py, the queries in LINKS) and code writes
every title; a title's claim is checked before it's used, so a refresh that changes the story fails loudly.

    python articles/first-ball/data.py                                                           # refresh the numbers
    DATABASE_URL=postgresql://localhost:5432/hindsight_local python articles/first-ball/cards.py [--reply]
"""
import json
import os
import statistics
from datetime import date
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
Q = "https://hindsightcricket.com/query?metrics_perspective=batting&fmt=mens-t20&"
LINKS = {"curve": Q + "dimension_filters=batter_ball_number%3Alte%3A20&group_by=batter_ball_number",
         "trend": Q + "dimension_filters=batter_ball_number%3Aeq%3A1&group_by=year",
         "trend_ipl": Q + "leagues=IPL&dimension_filters=batter_ball_number%3Aeq%3A1&group_by=year",
         "field": Q + "start_date=2023-01-01&dimension_filters=batter_ball_number%3Aeq%3A1&group_by=batter&min_balls=60"}
CREDIT = "Men's T20s"
THREE = {"Abhishek Sharma": "Abhishek", "Sanju Samson": "Samson", "Vaibhav Sooryavanshi": "Sooryavanshi"}
D = json.loads((HERE / "data" / "first_ball.json").read_text())
YEAR = date.fromisoformat(D["as_of"]).year
# Since 2023, first balls: (balls, boundaries, sixes, wickets). Sooryavanshi is under the field's 60-ball floor.
MINE = {r["batter"]: (r["balls"], r["boundaries"], r["sixes"], r["wickets"]) for r in D["three"]}


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def pct(a, b):
    return round(100 * a / b, 1)


# Ball of the innings 1-20, all men's T20s: (ball, balls, boundaries, sixes)
CURVE = [(r["batter_ball_number"], r["balls"], r["boundaries"], r["sixes"]) for r in sorted(D["curve"], key=lambda r: r["batter_ball_number"])]
b1 = pct(CURVE[0][2], CURVE[0][1])
peak = max(CURVE, key=lambda c: c[2] / c[1])
curve = card(
    "curve", "metric_lines", f"A batter's first ball goes for four or six {b1}% of the time. By ball {peak[0]}, {pct(peak[2], peak[1]):.0f}%",
    {"x": {"label": "Ball of his innings", "ticks": [1, 5, 10, 15, 20]}, "y": {"label": "% of balls", "format": "pct1"},
     "series": [{"name": "Boundary %", "highlight": True, "points": [{"x": n, "y": pct(b4, b)} for n, b, b4, _ in CURVE]},
                {"name": "Six %", "points": [{"x": n, "y": pct(s6, b)} for n, b, _, s6 in CURVE]}],
     "callouts": [{"series": "Boundary %", "x": 1}]},
    f"{CREDIT}, 2005–{YEAR} · {round(CURVE[0][1] / 1000)}k first balls")

# First balls by season, 2015 on: (year, balls, boundaries, sixes)
ALL = [(r["year"], r["balls"], r["boundaries"], r["sixes"]) for r in sorted(D["trend_all"], key=lambda r: r["year"])]
IPL = [(r["year"], r["balls"], r["boundaries"], r["sixes"]) for r in sorted(D["trend_ipl"], key=lambda r: r["year"])]
ipl = {y: pct(b4, b) for y, b, b4, _ in IPL}
assert ipl[YEAR] > ipl[2022], "the IPL first ball isn't being hit more than in 2022 any more: rewrite the trend card"
trend = card(
    "trend", "metric_lines", f"IPL first balls: {ipl[2022]}% went for four or six in 2022, {ipl[YEAR]}% in {YEAR}",
    {"x": {"label": "Season", "ticks": [2015, 2018, 2021, 2024, YEAR]}, "y": {"label": "First-ball boundary %", "format": "pct1"},
     "span": {"from": 2022.5, "to": YEAR, "label": "Impact Player"},
     "series": [{"name": "IPL", "highlight": True, "points": [{"x": y, "y": pct(b4, b)} for y, b, b4, _ in IPL]},
                {"name": "All T20s", "dashed": True, "points": [{"x": y, "y": pct(b4, b)} for y, b, b4, _ in ALL]}],
     "callouts": [{"series": "IPL", "x": 2022, "place": "above-left"}]},
    f"{CREDIT}, 2015–{YEAR} · IPL ~{round(statistics.mean(b for _, b, _, _ in IPL[-4:]), -2):,.0f} first balls a season")

field = D["field"]
N = len(field)
names = {r["batter"] for r in field}
pts = [{"name": r["batter"], "x": pct(r["boundaries"], r["balls"]), "y": pct(r["wickets"], r["balls"])} for r in field
       if r["batter"] not in THREE]
pts += [{"name": n, "short": THREE[n], "x": pct(bd, b), "y": pct(w, b), "highlight": True} for n, (b, bd, s, w) in MINE.items()]
vs, ss = MINE["Vaibhav Sooryavanshi"], MINE["Sanju Samson"]
scatter = card(
    "scatter", "scatter_plus", f"Sooryavanshi hits {pct(vs[1], vs[0]):.0f}% of his first balls for four or six. Samson, {pct(ss[1], ss[0])}%",
    {"x": {"label": "First-ball boundary %", "format": "pct0", "higher_better": True},
     "y": {"label": "Out on first ball %", "format": "pct0", "higher_better": False},
     "points": pts, "box": False},
    f"{CREDIT}, 2023–{YEAR} · {N} batters with 60+ first balls; Sooryavanshi {vs[0]}")


# The attackers: Jaiswal and Salt named in lime, the rest of the leaders numbered (named in the key under the chart).
LEAD = ["Yashasvi Jaiswal", "Phil Salt"]
SHORT = {"Suryakumar Yadav": "Suryakumar", "Karanbir Singh": "Karanbir"}
KEYED = ["Virat Kohli", "Suryakumar Yadav", "Travis Head", "Nicholas Pooran", "Sunil Narine", "Karanbir Singh"]
lead_pts = [{"name": r["batter"], "x": pct(r["boundaries"], r["balls"]), "y": pct(r["wickets"], r["balls"]),
             **({"highlight": True, "short": r["batter"].split()[-1]} if r["batter"] in LEAD else {}),
             **({"label": KEYED.index(r["batter"]) + 1, "short": SHORT.get(r["batter"])} if r["batter"] in KEYED else {})}
            for r in field]
by = {r["batter"]: r for r in field}
jai, salt = by["Yashasvi Jaiswal"], by["Phil Salt"]
assert jai["wickets"] == 0, "Jaiswal has now been out on a first ball: rewrite the attackers card"
attackers = card(
    "attackers", "scatter_plus", f"Jaiswal and Salt both go at ball one. Salt's been out {salt['wickets']} times, Jaiswal never",
    {"x": {"label": "First-ball boundary %", "format": "pct0", "higher_better": True},
     "y": {"label": "Out on first ball %", "format": "pct0", "higher_better": False},
     "points": lead_pts, "box": False},
    f"{CREDIT}, 2023–{YEAR} · {N} batters with 60+ first balls")


# Along the ground or over the top: first-ball four % against six %. Kohli and Narine named, the like and unlike numbered.
POLES = {"Virat Kohli": "Kohli", "Sunil Narine": "Narine"}
STYLE = ["Travis Head", "Shreyas Iyer", "Abhishek Sharma", "Shivam Dube", "Karanbir Singh"]  # Karanbir (Austria): the only one high on both
style_pts = [{"name": r["batter"], "x": pct(r["fours"], r["balls"]), "y": pct(r["sixes"], r["balls"]),
              **({"highlight": True, "short": POLES[r["batter"]]} if r["batter"] in POLES else {}),
              **({"label": STYLE.index(r["batter"]) + 1, "short": {"Abhishek Sharma": "Abhishek", "Karanbir Singh": "Karanbir (Austria)"}.get(r["batter"], r["batter"].split()[-1])}
                 if r["batter"] in STYLE else {})} for r in field]
ko = by["Virat Kohli"]
assert ko["sixes"] == 0 and max(field, key=lambda r: r["fours"] / r["balls"])["batter"] == "Virat Kohli", \
    "Kohli is no longer top for first-ball fours with no sixes: rewrite the Kohli card"
kohli = card(
    "kohli", "scatter_plus", f"Kohli hits more first balls for four than anyone: {ko['fours']} in {ko['balls']}. Not one six",
    {"x": {"label": "First-ball four %", "format": "pct0", "higher_better": True},
     "y": {"label": "First-ball six %", "format": "pct0", "higher_better": True},
     "points": style_pts, "box": False},
    f"{CREDIT}, 2023–{YEAR} · {N} batters with 60+ first balls")

SHARE = ["Sunil Narine", "Shivam Dube", "Abhishek Sharma", "Nicholas Pooran", "Yashasvi Jaiswal", "Phil Salt",
         "Virat Kohli", "Travis Head", "Shreyas Iyer"]
half = [n for n in ("Sunil Narine", "Shivam Dube") if by[n]["sixes"] * 2 == by[n]["boundaries"]]
assert len(half) == 2, "Narine and Dube aren't both at half: rewrite the six-share card"
field_share = round(100 * sum(r["sixes"] for r in field) / sum(r["boundaries"] for r in field))
share = card(
    "six-share", "metric_bars", "Half of Narine's and Dube's first-ball boundaries are sixes. None of Kohli's",
    {"metric": {"label": "Sixes as % of first-ball boundaries", "format": "pct0", "signed": False}, "label_width": 130,
     "rows": [{"name": n, "value": pct(by[n]["sixes"], by[n]["boundaries"]), "highlight": n in POLES,
               "detail": f"{by[n]['sixes']} of {by[n]['boundaries']}"} for n in SHARE]},
    f"{CREDIT}, 2023–{YEAR} · 60+ first balls (field: {field_share}%)")


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def rank(key, v, b):
    return 1 + sum(r[key] / r["balls"] > v / b for r in field)


def bars(metric, key, top, extra_label):
    rows = sorted(field, key=lambda r: -r[key] / r["balls"])
    out = [{"name": r["batter"], "value": pct(r[key], r["balls"]), "detail": f"{r[key]} in {r['balls']}"} for r in rows[:top]]
    for n, (b, bd, s, w) in MINE.items():
        v = {"boundaries": bd, "sixes": s}[key]
        out.append({"name": n, "value": pct(v, b), "highlight": True,
                    "detail": f"{v} in {b}" + ("" if n in names else " · under 60") + (f" · {ordinal(rank(key, v, b))} of {N}" if n in names else "")})
    out.sort(key=lambda r: -r["value"])
    return {"metric": {"label": metric, "format": "pct1", "signed": False}, "rows": out, "label_width": 130}


ab, sa = MINE["Abhishek Sharma"], MINE["Sanju Samson"]
median = lambda key: statistics.median(pct(r[key], r["balls"]) for r in field)  # noqa: E731
four_bars = card("boundary-bars", "metric_bars",
                 f"Abhishek is {ordinal(rank('boundaries', ab[1], ab[0]))} of {N} for first-ball boundaries. "
                 f"Samson, {ordinal(rank('boundaries', sa[1], sa[0]))}",
                 bars("First-ball boundary %", "boundaries", 6, ""),
                 f"{CREDIT}, 2023–{YEAR} · 60+ first balls (median {median('boundaries'):.1f}%)")
six_bars = card("six-bars", "metric_bars",
                f"Abhishek clears the rope off {pct(ab[2], ab[0])}% of first balls, {ordinal(rank('sixes', ab[2], ab[0]))} of {N}",
                bars("First-ball six %", "sixes", 5, ""),
                f"{CREDIT}, 2023–{YEAR} · 60+ first balls (median {median('sixes'):.1f}%)")

# Player and number first (content rules), then the style split, then the general picture.
CARDS = [scatter, four_bars, six_bars, kohli, share, attackers, curve, trend]

if __name__ == "__main__":
    assert "localhost" in os.environ.get("DATABASE_URL", ""), "run against the local database"
    from services.snapshots import create_static_snapshot

    reply = "--reply" in sys.argv
    slides = [{"type": "card", "card": c, "teams": None} for c in CARDS]
    data = {"slides": slides, "title": "First ball"}
    if reply:
        data["counter"] = False
    snap = create_static_snapshot(None, "carousel", data, "First ball" + (" (reply)" if reply else ""),
                                  {"article": "first-ball", "slides": slides}, created_by="article")
    print(snap["id"], len(slides))
