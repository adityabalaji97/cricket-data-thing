"""
First-ball boundaries: how often a batter's first ball goes for four or six, and where Abhishek Sharma, Sanju Samson
and Vaibhav Sooryavanshi sit. Men's T20s; "first ball" = the first legal ball a batter faces in an innings
(batter_ball_number = 1). Numbers copied from the queries in LINKS; the field (since 2023, 60+ first balls) is
data/field_2023.json.

    DATABASE_URL=postgresql://localhost:5432/hindsight_local python articles/first-ball/cards.py [--reply]
"""
import json
import os
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
# Since 2023, first balls: (balls, boundaries, sixes, wickets). Sooryavanshi has 35, under the field's 60-ball floor.
MINE = {"Abhishek Sharma": (132, 18, 8, 7), "Sanju Samson": (107, 5, 3, 6), "Vaibhav Sooryavanshi": (35, 12, 4, 1)}


def card(cid, visual, title, payload, sample, help_=""):
    return {"id": cid, "visual": visual, "title": title, "help": help_, "sample": sample, "payload": payload}


def pct(a, b):
    return round(100 * a / b, 1)


# Ball of the innings 1-20, all men's T20s: (ball, balls, boundaries, sixes)
CURVE = [(1, 187902, 14834, 2236), (2, 174579, 18987, 3988), (3, 162202, 20449, 4657), (4, 150500, 20829, 5267),
         (5, 139706, 20665, 5503), (6, 129930, 20658, 5911), (7, 120664, 20108, 5865), (8, 112082, 19299, 5697),
         (9, 104104, 18187, 5567), (10, 96750, 17330, 5252), (11, 89966, 16182, 5043), (12, 83730, 15022, 4646),
         (13, 78058, 14102, 4560), (14, 72713, 13141, 4255), (15, 67781, 12169, 4008), (16, 63208, 11293, 3725),
         (17, 59091, 10309, 3461), (18, 55170, 9454, 3214), (19, 51396, 8728, 3075), (20, 47985, 8079, 2898)]
curve = card(
    "curve", "metric_lines", "A batter's first ball goes for four or six 7.9% of the time. By ball 13, 18%",
    {"x": {"label": "Ball of his innings", "ticks": [1, 5, 10, 15, 20]}, "y": {"label": "% of balls", "format": "pct1"},
     "series": [{"name": "Boundary %", "highlight": True, "points": [{"x": n, "y": pct(b4, b)} for n, b, b4, _ in CURVE]},
                {"name": "Six %", "points": [{"x": n, "y": pct(s6, b)} for n, b, _, s6 in CURVE]}],
     "callouts": [{"series": "Boundary %", "x": 1}]},
    f"{CREDIT}, 2005–2026 · 188k first balls")

# First balls by season, 2015-2026: (year, balls, boundaries, sixes)
ALL = [(2015, 8346, 624, 87), (2016, 8979, 698, 96), (2017, 7882, 634, 92), (2018, 9242, 759, 127),
       (2019, 13296, 1052, 146), (2020, 8881, 722, 104), (2021, 16876, 1271, 183), (2022, 19223, 1502, 240),
       (2023, 15459, 1278, 178), (2024, 21477, 1669, 274), (2025, 21304, 1711, 284), (2026, 19311, 1664, 284)]
IPL = [(2015, 878, 69, 8), (2016, 864, 74, 8), (2017, 894, 69, 7), (2018, 902, 82, 10), (2019, 871, 85, 7),
       (2020, 865, 71, 11), (2021, 907, 87, 12), (2022, 1155, 107, 20), (2023, 1163, 117, 23), (2024, 1109, 126, 22),
       (2025, 1117, 138, 29), (2026, 1126, 144, 32)]
trend = card(
    "trend", "metric_lines", "IPL first balls: 9.3% went for four or six in 2022, 12.8% in 2026",
    {"x": {"label": "Season", "ticks": [2015, 2018, 2021, 2024, 2026]}, "y": {"label": "First-ball boundary %", "format": "pct1"},
     "span": {"from": 2022.5, "to": 2026, "label": "Impact Player"},
     "series": [{"name": "IPL", "highlight": True, "points": [{"x": y, "y": pct(b4, b)} for y, b, b4, _ in IPL]},
                {"name": "All T20s", "dashed": True, "points": [{"x": y, "y": pct(b4, b)} for y, b, b4, _ in ALL]}],
     "callouts": [{"series": "IPL", "x": 2022, "place": "above-left"}]},
    f"{CREDIT}, 2015–2026 · IPL ~1,100 first balls a season")

field = json.loads((HERE / "data" / "field_2023.json").read_text())
names = {r["batter"] for r in field}
pts = [{"name": r["batter"], "x": pct(r["boundaries"], r["balls"]), "y": pct(r["wickets"], r["balls"])} for r in field
       if r["batter"] not in THREE]
pts += [{"name": n, "short": THREE[n], "x": pct(bd, b), "y": pct(w, b), "highlight": True} for n, (b, bd, s, w) in MINE.items()]
scatter = card(
    "scatter", "scatter_plus", "Sooryavanshi hits 34% of his first balls for four or six. Samson, 4.7%",
    {"x": {"label": "First-ball boundary %", "format": "pct0", "higher_better": True},
     "y": {"label": "Out on first ball %", "format": "pct0", "higher_better": False},
     "points": pts, "box": False},
    f"{CREDIT}, 2023–2026 · 248 batters with 60+ first balls; Sooryavanshi 35")


# The attackers: Jaiswal and Salt named in lime, the rest of the leaders numbered (named in the key under the chart).
LEAD = ["Yashasvi Jaiswal", "Phil Salt"]
SHORT = {"Suryakumar Yadav": "Suryakumar", "Karanbir Singh": "Karanbir"}
KEYED = ["Virat Kohli", "Suryakumar Yadav", "Travis Head", "Nicholas Pooran", "Sunil Narine", "Karanbir Singh"]
lead_pts = [{"name": r["batter"], "x": pct(r["boundaries"], r["balls"]), "y": pct(r["wickets"], r["balls"]),
             **({"highlight": True, "short": r["batter"].split()[-1]} if r["batter"] in LEAD else {}),
             **({"label": KEYED.index(r["batter"]) + 1, "short": SHORT.get(r["batter"])} if r["batter"] in KEYED else {})}
            for r in field]
attackers = card(
    "attackers", "scatter_plus", "Jaiswal and Salt both go at ball one. Salt's been out 14 times, Jaiswal never",
    {"x": {"label": "First-ball boundary %", "format": "pct0", "higher_better": True},
     "y": {"label": "Out on first ball %", "format": "pct0", "higher_better": False},
     "points": lead_pts, "box": False},
    f"{CREDIT}, 2023–2026 · 248 batters with 60+ first balls")


# Along the ground or over the top: first-ball four % against six %. Kohli and Narine named, the like and unlike numbered.
POLES = {"Virat Kohli": "Kohli", "Sunil Narine": "Narine"}
STYLE = ["Travis Head", "Shreyas Iyer", "Abhishek Sharma", "Shivam Dube", "Karanbir Singh"]  # Karanbir (Austria): the only one high on both
style_pts = [{"name": r["batter"], "x": pct(r["fours"], r["balls"]), "y": pct(r["sixes"], r["balls"]),
              **({"highlight": True, "short": POLES[r["batter"]]} if r["batter"] in POLES else {}),
              **({"label": STYLE.index(r["batter"]) + 1, "short": {"Abhishek Sharma": "Abhishek", "Karanbir Singh": "Karanbir (Austria)"}.get(r["batter"], r["batter"].split()[-1])}
                 if r["batter"] in STYLE else {})} for r in field]
kohli = card(
    "kohli", "scatter_plus", "Kohli hits more first balls for four than anyone: 16 in 70. Not one six",
    {"x": {"label": "First-ball four %", "format": "pct0", "higher_better": True},
     "y": {"label": "First-ball six %", "format": "pct0", "higher_better": True},
     "points": style_pts, "box": False},
    f"{CREDIT}, 2023–2026 · 248 batters with 60+ first balls")

SHARE = ["Sunil Narine", "Shivam Dube", "Abhishek Sharma", "Nicholas Pooran", "Yashasvi Jaiswal", "Phil Salt",
         "Virat Kohli", "Travis Head", "Shreyas Iyer"]
by = {r["batter"]: r for r in field}
share = card(
    "six-share", "metric_bars", "Half of Narine's and Dube's first-ball boundaries are sixes. None of Kohli's",
    {"metric": {"label": "Sixes as % of first-ball boundaries", "format": "pct0", "signed": False}, "label_width": 130,
     "rows": [{"name": n, "value": pct(by[n]["sixes"], by[n]["boundaries"]), "highlight": n in POLES,
               "detail": f"{by[n]['sixes']} of {by[n]['boundaries']}"} for n in SHARE]},
    f"{CREDIT}, 2023–2026 · 60+ first balls (field: 15%)")


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def bars(metric, key, top, extra_label):
    rows = sorted(field, key=lambda r: -r[key] / r["balls"])
    out = [{"name": r["batter"], "value": pct(r[key], r["balls"]), "detail": f"{r[key]} in {r['balls']}"} for r in rows[:top]]
    for n, (b, bd, s, w) in MINE.items():
        v = {"boundaries": bd, "sixes": s}[key]
        rank = 1 + sum(r[key] / r["balls"] > v / b for r in field)
        out.append({"name": n, "value": pct(v, b), "highlight": True,
                    "detail": f"{v} in {b}" + ("" if n in names else " · under 60") + (f" · {ordinal(rank)} of 248" if n in names else "")})
    out.sort(key=lambda r: -r["value"])
    return {"metric": {"label": metric, "format": "pct1", "signed": False}, "rows": out, "label_width": 130}


four_bars = card("boundary-bars", "metric_bars", "Abhishek is 43rd of 248 for first-ball boundaries. Samson, 225th",
                 bars("First-ball boundary %", "boundaries", 6, ""),
                 f"{CREDIT}, 2023–2026 · 60+ first balls (median 9.2%)")
six_bars = card("six-bars", "metric_bars", "Abhishek clears the rope off 6.1% of first balls, 6th of 248",
                bars("First-ball six %", "sixes", 5, ""),
                f"{CREDIT}, 2023–2026 · 60+ first balls (median 1.0%)")

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
