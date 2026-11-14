"""
Two batters compared, each over his own window and competitions ("Kohli 2023-26 or Warner 2015-19 in the IPL?"). From a
spec (services/ig_posts/spotlight.SPECS, type "player_compare"): players [{name, label, start, end, leagues,
include_international}].

The numbers people quote (runs, average, strike rate) first, then what they leave out: the era (strike rate against
the league in the same seasons; Impact, runs added to the team's projected total, and WPA, win probability added,
both judged against the conditions of the day), the phases (where the balls were faced and what each added there),
season by season, batting first against chasing, and the bowling faced.

Bowling faced: each bowler rated on his own season in the same competitions, by bowling Impact per 100 balls above
that season's average, leaving out the balls he bowled to the batter being judged (else a batter who dominates a
bowler makes his own opposition look weak) and pulled toward average when the season is thin (K balls). Impact, not
WPA: a bowler's WPA follows when he bowls more than how well. The batter's figure is the ball-weighted mean.

Slides: hook; the raw line; the deeper cut (against the era); phases; seasons; batting first v chasing; bowling faced;
end. Every number from the query builder; code writes the titles.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from services.ig_posts.cards import card, fmt
from services.ig_posts.spotlight import heat

K = 120                 # bowler-season balls: a season this long counts half its own rate, half average
PHASES = [("powerplay", "Powerplay"), ("middle", "Middle"), ("death", "Death")]
MIN_CONTROL_COVERAGE = 70.0  # % of balls with shot data before false shots are shown
TWINS_AVG, TWINS_SR = 5.0, 6.0   # closer than this on average and strike rate, the raw lines "look like twins"
# The hook carries the raw line, so the raw card sits out under the 8-slide cap; seasons (a bar chart) can lead the
# cover, and the era is the deeper cut on slide 3.
CARDS = ["seasons", "era", "phases", "chase", "team", "bowling"]
SAME_BOWLING = 0.1   # runs an over: closer than this, the bowling faced was the same


def _q(db, pl: Dict[str, Any], **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "T20", "gender": "male", "limit": 5000, "metrics_perspective": "batting",
            "leagues": pl.get("leagues", []), "include_international": pl.get("include_international", False),
            "start_date": pl["start"], "end_date": pl["end"]}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


def _one(db, pl, **args) -> Optional[Dict[str, Any]]:
    rows = _q(db, pl, batters=[pl["name"]], group_by=["batter"], **args)
    return rows[0] if rows else None


def _plain(payload, scales: Optional[Dict[str, Optional[float]]] = None, rings: bool = True):
    """Zero-centred shading where a column has a scale (brighter above average), none elsewhere; rings stay on the
    better of the two only where `rings`."""
    for r in payload["rows"]:
        r["short"] = r["name"]
        if not rings:
            r["leader"] = []
        for c in list(r["pct"]):
            sc = (scales or {}).get(c)
            v = r["values"].get(c)
            r["pct"][c] = None if (sc is None or v is None) else max(0.0, min(100.0, 100 * v / sc))


def names_of(table) -> List[str]:
    return list(table)


def _formats(payload, fmts: Dict[str, str]):
    for m in payload["metrics"]:
        m["format"] = fmts.get(m["key"], "signed0")


def _sample(spec) -> str:
    return " · ".join(f"{p['label']}: {p['window']}" for p in spec["players"]) + f" · {spec['scope']}"


# ---- the data ----------------------------------------------------------------------------------------------------

def gather(db, spec) -> Dict[str, Any]:
    out = {}
    for pl in spec["players"]:
        me = _one(db, pl)
        if not me:
            return {}
        years = {r["year"]: r for r in _q(db, pl, batters=[pl["name"]], group_by=["year"])}
        league = {r["year"]: r for r in _q(db, pl, group_by=["year"])}
        out[pl["label"]] = {
            "me": me, "years": years, "league": league,
            "phases": {r["phase"]: r for r in _q(db, pl, batters=[pl["name"]], group_by=["phase"])},
            "innings": {r["innings"]: r for r in _q(db, pl, batters=[pl["name"]], group_by=["innings"])},
            "bowling": bowling_faced(db, pl, league),
            "team": team_context(db, pl, me),
        }
    return out


def team_context(db, pl, me) -> Dict[str, Any]:
    """The rest of his side in the same seasons, him left out: the other batters' and the bowlers' Impact per 100 balls
    against the league's that season (above 0: better than an average side's), the side's win %, and his share of the
    side's runs. A low "rest" with a high share: he carried it; a strong rest: he played inside a good side."""
    teams = {}
    for r in _q(db, pl, batters=[pl["name"]], group_by=["year", "batting_team"]):
        if r["balls"] > teams.get(r["year"], (None, 0))[1]:
            teams[r["year"]] = (r["batting_team"], r["balls"])
    lg_bat = {r["year"]: r for r in _q(db, pl, group_by=["year"])}
    acc = {"rb": 0, "ri": 0.0, "rl": 0.0, "bb": 0, "bi": 0.0, "bl": 0.0, "runs": 0, "won": 0, "played": 0}
    for y, (team, _b) in teams.items():
        yr = {"start_date": pl["start"].replace(year=int(y), month=1, day=1), "end_date": pl["start"].replace(year=int(y), month=12, day=31)}
        rest = next(iter(_q(db, pl, batting_teams=[team], exclude_batters=[pl["name"]], group_by=["batting_team"], **yr)), None)
        bowl = next(iter(_q(db, pl, bowling_teams=[team], group_by=["bowling_team"], metrics_perspective="bowling", **yr)), None)
        lg = lg_bat.get(y)
        if not rest or not bowl or not lg:
            continue
        lg_per = (lg["impact"] or 0) / lg["balls"]  # the league's batting Impact a ball; bowling is its mirror
        acc["rb"] += rest["balls"]; acc["ri"] += rest["impact"] or 0; acc["rl"] += lg_per * rest["balls"]
        acc["bb"] += bowl["balls"]; acc["bi"] += bowl["impact"] or 0; acc["bl"] += -lg_per * bowl["balls"]
        acc["runs"] += rest["runs"]
        for m in _q(db, pl, batting_teams=[team], group_by=["match_id", "match_outcome"], **yr):
            if m.get("match_outcome") in ("win", "loss"):
                acc["played"] += 1
                acc["won"] += m["match_outcome"] == "win"
    if not acc["rb"] or not acc["bb"]:
        return {}
    return {"teams": sorted({t for t, _ in teams.values()}),
            "rest_bat": 100 * (acc["ri"] - acc["rl"]) / acc["rb"], "bowl": 100 * (acc["bi"] - acc["bl"]) / acc["bb"],
            "win": 100 * acc["won"] / acc["played"] if acc["played"] else None,
            "share": 100 * me["runs"] / (me["runs"] + acc["runs"])}


def sr_index(d) -> Optional[float]:
    """Strike rate against the league's in the same seasons, 100 = the league: runs over the runs the league's
    scoring rate would have made from the same balls, season by season."""
    par = sum(r["balls"] * d["league"][y]["strike_rate"] / 100 for y, r in d["years"].items() if y in d["league"])
    return 100 * sum(r["runs"] for y, r in d["years"].items() if y in d["league"]) / par if par else None


def bowling_faced(db, pl, league_bat: Dict[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """The batter's balls by bowler-season, each bowler-season rated on the rest of his season (see module doc) by
    economy: runs an over better than the season's average. Economy, not bowling Impact: split each IPL bowler's season
    into odd and even matches and Impact doesn't predict itself (r 0.03; 0.09 from one two-season spell to the next),
    economy does (0.36 within a season, 0.59 season to season; checked 20 Oct 2026). Returns {"quality": the
    ball-weighted rating, "top": batter's Impact /100 v the season's top third, "rest": v the others, "top_share": % of
    his balls v the top third}."""
    seasons = _q(db, pl, group_by=["bowler", "year"], metrics_perspective="bowling", limit=10000)
    league = {}
    for r in seasons:
        b, runs = league.get(r["year"], (0, 0))
        league[r["year"]] = (b + (r["balls"] or 0), runs + (r["runs"] or 0))
    vs_me = {(r["bowler"], r["year"]): r for r in _q(db, pl, batters=[pl["name"]], group_by=["bowler", "year"],
                                                      metrics_perspective="bowling", limit=10000)}
    me_bat = {(r["bowler"], r["year"]): r for r in _q(db, pl, batters=[pl["name"]], group_by=["bowler", "year"], limit=10000)}
    rating, size = {}, {}
    for r in seasons:
        key = (r["bowler"], r["year"])
        mine = vs_me.get(key) or {}
        balls = (r["balls"] or 0) - (mine.get("balls") or 0)
        runs = (r["runs"] or 0) - (mine.get("runs") or 0)
        lb, lr = league[r["year"]]
        rating[key] = 6 * (lr / lb * balls - runs) / (balls + K) if balls > 0 and lb else 0.0  # runs an over saved, shrunk
        size[key] = balls
    top = set()
    by_year: Dict[Any, List[Tuple[float, Tuple]]] = {}
    for key, v in rating.items():
        if size[key] >= 60:
            by_year.setdefault(key[1], []).append((v, key))
    for xs in by_year.values():
        xs.sort(reverse=True)
        top |= {k for _, k in xs[: max(1, len(xs) // 3)]}
    faced = [(key, r) for key, r in me_bat.items() if r.get("balls")]
    balls = sum(r["balls"] for _, r in faced)
    if not balls:
        return {}

    def per100(rows):
        b = sum(r["balls"] for r in rows)
        return (100 * sum(r["impact"] or 0 for r in rows) / b, b) if b else (None, 0)

    t, tb = per100([r for k, r in faced if k in top])
    o, _ = per100([r for k, r in faced if k not in top])
    return {"quality": sum(rating.get(k, 0.0) * r["balls"] for k, r in faced) / balls, "top": t, "rest": o,
            "top_share": 100 * tb / balls}


# ---- the cards ---------------------------------------------------------------------------------------------------

def raw_card(spec, d) -> Dict[str, Any]:
    (a, da), (b, db_) = list(d.items())
    cols = ["Innings", "Runs", "Average", "Strike rate"]
    table = {n: {"Innings": x["me"]["innings_count"], "Runs": x["me"]["runs"], "Average": x["me"]["average"],
                 "Strike rate": x["me"]["strike_rate"]} for n, x in d.items()}
    payload = heat(table, cols, "", list(table))
    _plain(payload, rings=False)
    _formats(payload, {"Innings": "int", "Runs": "int", "Average": "dec1", "Strike rate": "int"})
    ma, mb = da["me"], db_["me"]
    if abs((ma["average"] or 0) - (mb["average"] or 0)) < TWINS_AVG and abs(ma["strike_rate"] - mb["strike_rate"]) < TWINS_SR:
        title = (f"On the numbers people quote, they're twins: average {ma['average']:.1f} v {mb['average']:.1f}, "
                 f"strike rate {ma['strike_rate']:.0f} v {mb['strike_rate']:.0f}")
    else:
        title = (f"{a} averages {ma['average']:.1f} at a strike rate of {ma['strike_rate']:.0f}; {b} {mb['average']:.1f} "
                 f"at {mb['strike_rate']:.0f}")
    payload["method"] = "The raw line: no allowance for when or where."
    return card("raw", "scorecard", title, payload, _sample(spec), "Runs, average and strike rate, as quoted")


def era_card(spec, d) -> Dict[str, Any]:
    cols = ["SR v league", "Impact /100", "WPA", "False shot %"]
    table, thin = {}, []
    for n, x in d.items():
        m = x["me"]
        ok = (m.get("control_coverage_pct") or 0) >= MIN_CONTROL_COVERAGE
        if not ok:
            thin.append(n)
        table[n] = {"SR v league": sr_index(x), "Impact /100": m["impact_per_100"], "WPA": m["wpa"],
                    "False shot %": (100 - m["control_percentage"]) if ok and m.get("control_percentage") is not None else None}
    names = list(table)
    payload = heat(table, cols, "", names)
    _plain(payload, {"Impact /100": 30, "WPA": 5})
    for r in payload["rows"]:  # 100 is the league: shade the distance above it
        v = r["values"]["SR v league"]
        r["pct"]["SR v league"] = None if v is None else max(0.0, min(100.0, 10 * (v - 100)))
    _formats(payload, {"SR v league": "int", "Impact /100": "signed0", "WPA": "signed1", "False shot %": "pct0"})
    fs = [n for n in names_of(table) if table[n]["False shot %"] is not None]
    if len(fs) == 2:  # fewer false shots is better: ring the lower
        lo = min(fs, key=lambda n: table[n]["False shot %"])
        for r in payload["rows"]:
            r["leader"] = [c for c in r["leader"] if c != "False shot %"] + (["False shot %"] if r["name"] == lo else [])
    a, b = names
    idx = {n: table[n]["SR v league"] for n in names}

    def faster(n):
        v = idx[n] - 100
        return f"{abs(v):.0f}% {'faster' if v >= 0 else 'slower'}"
    title = (f"{a} scored {faster(a)} than his league, {b} {faster(b)}. Impact per 100: {a} "
             f"{fmt(table[a]['Impact /100'], 'signed0')}, {b} {fmt(table[b]['Impact /100'], 'signed0')}")
    payload["method"] = ("SR v league: 100 = the league's strike rate in the same seasons. WPA: win probability added, "
                         "in wins. False shot: played and missed or edged, of the balls with shot data. Ring: better of the two."
                         + (f" – too little shot data ({', '.join(thin)})." if thin else ""))
    lsr = {n: (min(x["league"][y]["strike_rate"] for y in x["years"] if y in x["league"]),
               max(x["league"][y]["strike_rate"] for y in x["years"] if y in x["league"])) for n, x in d.items()}
    help_ = " · ".join(f"League SR in {n}'s seasons: {lo:.0f}-{hi:.0f}" for n, (lo, hi) in lsr.items())
    out = card("era", "scorecard", title, payload, _sample(spec), help_)
    out["kicker"] = "The deeper cut"
    return out


def phases_card(spec, d) -> Dict[str, Any]:
    names = list(d)
    cols = [f"{n} balls %" for n in names] + [f"{n} Impact" for n in names]
    table, gaps = {}, {}
    for key, label in PHASES:
        row = {}
        for n in names:
            ph, tot = d[n]["phases"].get(key), d[n]["me"]["balls"]
            row[f"{n} balls %"] = 100 * ph["balls"] / tot if ph else None
            row[f"{n} Impact"] = ph["impact_per_100"] if ph else None
        table[label] = row
        if all(row[f"{n} Impact"] is not None for n in names) and min(d[n]["phases"][key]["balls"] for n in names) >= 60:
            gaps[label] = row[f"{names[0]} Impact"] - row[f"{names[1]} Impact"]
    payload = heat(table, cols, "", [l for _, l in PHASES])
    _plain(payload, {f"{n} Impact": 30 for n in names}, rings=False)
    _formats(payload, {**{f"{n} balls %": "pct0" for n in names}, **{f"{n} Impact": "signed0" for n in names}})
    big = max(gaps, key=lambda k: abs(gaps[k]))
    lead, trail = (names[0], names[1]) if gaps[big] > 0 else (names[1], names[0])
    where = {"Powerplay": "in the powerplay", "Middle": "in the middle overs", "Death": "at the death"}[big]
    title = (f"The biggest gap is {where}: {lead} {fmt(table[big][f'{lead} Impact'], 'signed0')} per 100 balls, "
             f"{trail} {fmt(table[big][f'{trail} Impact'], 'signed0')}")
    payload["method"] = "Balls %: share of each batter's balls in that phase. Impact per 100 balls; brighter: higher."
    return card("phases", "scorecard", title, payload, _sample(spec), "Where each faced his balls, and what he added there")


def seasons_card(spec, d) -> Dict[str, Any]:
    names = list(d)
    rows = []
    for i, n in enumerate(names):
        for y in sorted(d[n]["years"]):
            r = d[n]["years"][y]
            rows.append({"name": f"{n} {y}", "value": r["impact_per_100"], "highlight": i == 0,
                         "detail": f"{r['runs']} runs · SR {r['strike_rate']:.0f}"})
    pos = {n: sum(1 for r in d[n]["years"].values() if (r["impact_per_100"] or 0) > 0) for n in names}
    tot = {n: len(d[n]["years"]) for n in names}

    def said(n):
        return f"all {tot[n]} seasons" if pos[n] == tot[n] else f"{pos[n]} of {tot[n]} seasons"
    best = {n: max(d[n]["years"].items(), key=lambda kv: kv[1]["impact_per_100"] or -999) for n in names}
    title = f"{names[0]} added runs in {said(names[0])}, {names[1]} in {said(names[1])}"
    a_lo = min(d[names[0]]["years"].items(), key=lambda kv: kv[1]["impact_per_100"] or 0)
    if pos[names[0]] < tot[names[0]]:
        title += f" ({names[0]} from {fmt(a_lo[1]['impact_per_100'], 'signed0')} in {a_lo[0]} to {fmt(best[names[0]][1]['impact_per_100'], 'signed0')} in {best[names[0]][0]})"
    elif pos[names[1]] < tot[names[1]]:
        b_lo = min(d[names[1]]["years"].items(), key=lambda kv: kv[1]["impact_per_100"] or 0)
        title += f" ({names[1]} {fmt(b_lo[1]['impact_per_100'], 'signed0')} in {b_lo[0]})"
    payload = {"metric": {"label": "Impact per 100 balls", "format": "signed0", "signed": True}, "rows": rows,
               "label_width": 120}
    return card("seasons", "metric_bars", title, payload, _sample(spec), "Impact per 100 balls, season by season")


def chase_card(spec, d) -> Optional[Dict[str, Any]]:
    cols = ["Batting first", "Chasing", "WPA first /inns", "WPA chasing /inns"]
    table = {}
    for n, x in d.items():
        f, c = x["innings"].get(1), x["innings"].get(2)
        if not f or not c:
            return None
        table[n] = {"Batting first": f["impact_per_100"], "Chasing": c["impact_per_100"],
                    "WPA first /inns": 100 * f["wpa"] / f["innings_count"], "WPA chasing /inns": 100 * c["wpa"] / c["innings_count"]}
    names = list(table)
    payload = heat(table, cols, "", names)
    _plain(payload, {"Batting first": 30, "Chasing": 30, "WPA first /inns": 8, "WPA chasing /inns": 8})
    _formats(payload, {"Batting first": "signed0", "Chasing": "signed0", "WPA first /inns": "signed1",
                       "WPA chasing /inns": "signed1"})
    lead = {k: max(names, key=lambda n: table[n][k]) for k in ("Batting first", "Chasing")}
    if lead["Batting first"] == lead["Chasing"]:
        n = lead["Chasing"]
        o = next(m for m in names if m != n)
        title = (f"{n} adds more batting first ({fmt(table[n]['Batting first'], 'signed0')} v "
                 f"{fmt(table[o]['Batting first'], 'signed0')}) and chasing ({fmt(table[n]['Chasing'], 'signed0')} v "
                 f"{fmt(table[o]['Chasing'], 'signed0')})")
    else:
        c, f = lead["Chasing"], lead["Batting first"]
        title = (f"Chasing, {c} adds more ({fmt(table[c]['Chasing'], 'signed0')} per 100); batting first, {f} "
                 f"({fmt(table[f]['Batting first'], 'signed0')})")
    payload["method"] = "Impact per 100 balls; WPA an innings, in points of win probability. Ring: better of the two."
    return card("chase", "scorecard", title, payload, _sample(spec), "Setting a total against chasing one")


def bowling_card(spec, d) -> Optional[Dict[str, Any]]:
    if not all(x["bowling"] for x in d.values()):
        return None
    cols = ["Bowling faced", "v top third", "v the rest", "Balls v top third"]
    table = {n: {"Bowling faced": x["bowling"]["quality"], "v top third": x["bowling"]["top"], "v the rest": x["bowling"]["rest"],
                 "Balls v top third": x["bowling"]["top_share"]} for n, x in d.items()}
    names = list(table)
    payload = heat(table, cols, "", names)
    _plain(payload, {"v top third": 30, "v the rest": 30}, rings=False)
    _formats(payload, {"Bowling faced": "signed2", "v top third": "signed0", "v the rest": "signed0", "Balls v top third": "pct0"})
    tough = max(names, key=lambda n: table[n]["Bowling faced"])
    easy = next(n for n in names if n != tough)
    gap = table[tough]["Bowling faced"] - table[easy]["Bowling faced"]
    first = (f"They faced bowling of much the same quality" if gap < SAME_BOWLING else
             f"{tough} faced tighter bowling ({fmt(table[tough]['Bowling faced'], 'signed2')} v "
             f"{fmt(table[easy]['Bowling faced'], 'signed2')} runs an over)")
    best = max(names, key=lambda n: table[n]["v top third"] or -999)
    other = next(n for n in names if n != best)
    title = (f"{first}. Against the best third, {best} {fmt(table[best]['v top third'], 'signed0')}, {other} "
             f"{fmt(table[other]['v top third'], 'signed0')}")
    payload["method"] = ("Bowling faced: the bowlers' economy against their season's average, in runs an over, from the "
                         "rest of their season (balls to this batter left out), thin seasons pulled to average. Higher: "
                         "tighter. Top third: the season's most economical with 60+ balls. v: his Impact per 100 balls.")
    return card("bowling", "scorecard", title, payload, _sample(spec), "The quality of the bowling each faced, and how he fared")


def team_card(spec, d) -> Optional[Dict[str, Any]]:
    if not all(x["team"] for x in d.values()):
        return None
    cols = ["Rest of batting", "Bowling", "Win %", "His run share"]
    table = {n: {"Rest of batting": x["team"]["rest_bat"], "Bowling": x["team"]["bowl"], "Win %": x["team"]["win"],
                 "His run share": x["team"]["share"]} for n, x in d.items()}
    names = list(table)
    payload = heat(table, cols, "", names)
    _plain(payload, {"Rest of batting": 15, "Bowling": 15}, rings=False)
    _formats(payload, {"Rest of batting": "signed1", "Bowling": "signed1", "Win %": "pct0", "His run share": "pct0"})
    carry = min(names, key=lambda n: table[n]["Rest of batting"])
    other = next(n for n in names if n != carry)
    title = (f"{carry}'s batting-mates added {fmt(table[carry]['Rest of batting'], 'signed1')} per 100 balls, {other}'s "
             f"{fmt(table[other]['Rest of batting'], 'signed1')}. {carry} made {table[carry]['His run share']:.0f}% of his "
             f"side's runs")
    payload["method"] = ("Rest of batting and bowling: Impact per 100 balls against the league's that season, him left "
                         "out (above 0: better than an average side). Win %: his side's, in those seasons.")
    sides = " · ".join(f"{n}: {', '.join(d[n]['team']['teams'])}" for n in names)
    return card("team", "scorecard", title, payload, _sample(spec), f"The rest of his side · {sides}")


BUILDERS = {"raw": raw_card, "era": era_card, "phases": phases_card, "seasons": seasons_card, "chase": chase_card,
            "bowling": bowling_card, "team": team_card}


def hook_text(spec, d) -> str:
    (a, da), (b, db_) = list(d.items())
    ma, mb = da["me"], db_["me"]
    return (f"{a}: average {ma['average']:.1f}, strike rate {ma['strike_rate']:.0f}. {b}: {mb['average']:.1f} and "
            f"{mb['strike_rate']:.0f}. Then you allow for the era.")


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for pl in spec["players"]:
        pl.setdefault("window", f"{pl['start']:%Y}-{pl['end']:%y}")
    d = gather(db, spec)
    if len(d) != 2:
        return None
    built = {k: BUILDERS[k](spec, d) for k in spec.get("cards", CARDS)}
    cards = [c for c in built.values() if c]
    deep = built.get("era")
    if not deep or cards.index(deep) != 1:  # the deeper cut on slide 3
        return None
    hook = spec.get("hook") or hook_text(spec, d)
    slides = ([{"type": "hook", "text": hook, "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [{"type": "end", "heading": "Compare any two", "body": "Every batter, every season: hindsightcricket.com"}])
    told = [c for c in cards if c is not deep]
    return {"slides": slides, "cards": cards, "title": hook, "verdict": " ".join(f"{c['title']}." for c in told[:2]),
            "players": [p["name"] for p in spec["players"]], "data": d,
            "deep_cut": {"probe": "era", "subject": " v ".join(d), "sentence": deep["title"], "by": "spotlight"}}
