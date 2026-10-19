"""
Who opens? A side's opening candidates for the top three, judged the way powerplay batting is played: go big or go
home. From a spec (services/ig_posts/spotlight.SPECS, type "openers_case").

Every powerplay innings (overs 1-6) is sorted by Impact (runs added to the team's projected total): big (+15 or
more), middling (0 to +15) or cost the team (below 0). The split was checked against WPA before use: big innings are
worth about +18 points of win probability, failures about -8 (19 Oct 2026, every T20I and IPL powerplay since 2023).

Slides: hook (the candidates' pooled failure rate, from the numbers); how often each goes big, is middling, or costs
the team (the lead chart: on a hero cover it moves onto slide 1); the deeper cut (every powerplay batter's failure and
big-innings rates, the candidates numbered among them); value per ball; against the opponent's bowling types; the
possible top threes (one keeper must play); the case for each; end. Every number from the query builder, every men's
T20 since `since` (leagues=[], include_international=False); code writes the titles.
"""
from __future__ import annotations

import statistics
from itertools import combinations
from typing import Any, Dict, List, Optional

from services.ig_posts.cards import batter_hand, card, fmt
from services.ig_posts.spotlight import heat, short_name

ALL_T20 = {"leagues": [], "include_international": False}
BIG, COST = 15.0, 0.0    # Impact in a powerplay innings: big at +15 or more; below 0 cost the team
FIELD_MIN = 30           # powerplay innings for a batter to join the field on the deeper cut
MIN_BALLS = 25
WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
GROUPS = [("big", "Big"), ("mid", "Middling"), ("cost", "Cost the team")]


def _q(db, **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "T20", "gender": "male", "limit": 10000, "metrics_perspective": "batting", **ALL_T20}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


def _nm(spec, n: str) -> str:
    return spec.get("names", {}).get(n) or short_name(n)


def group(impact: float) -> str:
    return "big" if impact >= BIG else ("cost" if impact < COST else "mid")


def innings(db, spec, batters: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """One row per batter per match: his balls in overs 1-6."""
    out, off = [], 0
    while True:
        args = {"batters": batters} if batters else {}
        rows = _q(db, group_by=["match_id", "batter"], start_date=spec["since"], over_max=5, offset=off, **args)
        out += [r for r in rows if r.get("impact") is not None]
        if len(rows) < 10000:
            return out
        off += 10000


def profile(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    share = {g: 100 * sum(group(r["impact"]) == g for r in rows) / n for g, _ in GROUPS}
    return {"n": n, **share, "impact": sum(r["impact"] for r in rows) / n,
            "wpa": 100 * sum(r.get("wpa") or 0 for r in rows) / n}


def typical(rows: List[Dict[str, Any]], g: str) -> str:
    s = [r for r in rows if group(r["impact"]) == g]
    return f"{statistics.median(r['runs'] for r in s):.0f} off {statistics.median(r['balls'] for r in s):.0f}" if s else "–"


def hook_text(spec, mine: List[Dict[str, Any]]) -> str:
    pooled = 100 * sum(group(r["impact"]) == "cost" for r in mine) / len(mine)
    return (f"{spec['side_word']} {WORDS.get(len(spec['candidates']), len(spec['candidates']))} openers fail in {pooled:.0f}% of their powerplay innings. "
            "What separates them is how often they go big.")


def groups_card(spec, by: Dict[str, List[Dict[str, Any]]], prof: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    order = sorted(spec["candidates"], key=lambda p: -prof[p]["big"])
    mine = [r for p in order for r in by[p]]
    hi, lo = order[0], order[-1]
    least_cost = min(prof[p]["cost"] for p in order)
    title = (f"{_nm(spec, hi)} goes big in {prof[hi]['big']:.0f}% of his powerplay innings, {_nm(spec, lo)} in "
             f"{prof[lo]['big']:.0f}%. All {WORDS.get(len(order), len(order))} fail at least {least_cost:.0f}% of the time")
    rows = [{"name": _nm(spec, p), "detail": f"{prof[p]['n']} innings",
             "segments": [{"key": g, "value": prof[p][g]} for g, _ in GROUPS]} for p in order]
    payload = {"groups": [{"key": g, "label": label} for g, label in GROUPS], "rows": rows, "format": "pct0"}
    help_ = (f"Big: Impact +{BIG:.0f} or more (typically {typical(mine, 'big')}). Cost the team: below 0 "
             f"(typically {typical(mine, 'cost')})")
    return card("groups", "share_bars", title, payload,
                f"Powerplay innings (overs 1-6) · every men's T20 since {spec['since']:%b %Y}", help_)


def field_card(spec, field: List[Dict[str, Any]], prof: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Every powerplay batter with FIELD_MIN innings: how often he fails (x, lower is better) and goes big (y)."""
    by: Dict[str, List[Dict[str, Any]]] = {}
    for r in field:
        by.setdefault(r["batter"], []).append(r)
    profs = {b: profile(rs) for b, rs in by.items() if len(rs) >= FIELD_MIN}
    for p in spec["candidates"]:
        profs[p] = prof[p]
    if len(profs) < 20:
        return None
    mid_cost = statistics.median(v["cost"] for v in profs.values())
    order = sorted(spec["candidates"], key=lambda p: -prof[p]["big"])
    points = [{"name": b, "x": v["cost"], "y": v["big"],
               **({"label": order.index(b) + 1, "short": _nm(spec, b)} if b in order else {})} for b, v in profs.items()]
    worse = [p for p in order if prof[p]["cost"] > mid_cost]
    k = WORDS.get(len(order), len(order))
    tail = (f"Only {_nm(spec, worse[0])} of {spec['side_poss']} {k} fails more" if len(worse) == 1 else
            f"{WORDS.get(len(order) - len(worse), len(order) - len(worse))} of {spec['side_poss']} {k} fail less often"
            if worse else f"All {k} of {spec['side_poss']} fail less often")
    title = f"The typical opener fails in {mid_cost:.0f}% of powerplay innings. {tail}"
    payload = {"points": points, "box": False,
               "x": {"label": "Fail %", "format": "pct0", "higher_better": False},
               "y": {"label": "Big innings %", "format": "pct0"}}
    out = card("field", "scatter_plus", title, payload,
               f"{len(profs)} batters with {FIELD_MIN}+ powerplay innings · every men's T20 since {spec['since']:%b %Y}",
               "Fail: cost the team runs. Up and right: better")
    out["kicker"] = "The deeper cut"
    return out


def cameo_line(field: List[Dict[str, Any]]) -> Optional[str]:
    """The caution on going fast: a quick cameo that ends early against a slow, long stay, in win probability."""
    cameo = [r for r in field if r.get("wickets") and r["balls"] <= 12 and 15 <= r["runs"] <= 24 and r.get("wpa") is not None]
    slow = [r for r in field if r["balls"] >= 20 and r["strike_rate"] < 120 and r.get("wpa") is not None]
    if len(cameo) < 50 or len(slow) < 50:
        return None
    cw, sw = (100 * statistics.mean(r["wpa"] for r in s) for s in (cameo, slow))
    md = lambda s, k: statistics.median(r[k] for r in s)  # noqa: E731
    return (f"Caution: {md(cameo, 'runs'):.0f} off {md(cameo, 'balls'):.0f} and out is worth {fmt(cw, 'signed1')} win points, "
            f"a slow {md(slow, 'runs'):.0f} off {md(slow, 'balls'):.0f} {fmt(sw, 'signed1')}. Going hard pays only when it goes big.")


def value_card(db, spec) -> Optional[Dict[str, Any]]:
    rows = {r["batter"]: r for r in _q(db, batters=spec["candidates"], group_by=["batter"], start_date=spec["since"],
                                       over_max=5)}
    order = [p for p in spec["candidates"] if p in rows]
    if len(order) < 2:
        return None
    cols = ["Impact /100", "WPA /inns", "Dot %", "Boundary %"]
    table = {_nm(spec, p): {"Impact /100": rows[p]["impact_per_100"], "WPA /inns": 100 * rows[p]["wpa"] / rows[p]["innings_count"],
                            "Dot %": rows[p]["dot_percentage"], "Boundary %": rows[p]["boundary_percentage"]} for p in order}
    names = sorted(table, key=lambda n: -table[n]["Impact /100"])
    payload = heat(table, cols, "", names)
    dot = {r["name"]: r for r in payload["rows"]}
    lo_dot = min(names, key=lambda n: table[n]["Dot %"])
    for r in payload["rows"]:  # fewer dots is better: re-rank that column
        r["short"] = r["name"]
        r["pct"]["Dot %"] = 100 - (r["pct"]["Dot %"] or 0)
        r["leader"] = [c for c in r["leader"] if c != "Dot %"] + (["Dot %"] if r["name"] == lo_dot else [])
    del dot
    for m in payload["metrics"]:
        m["format"] = {"Impact /100": "signed0", "WPA /inns": "signed1", "Dot %": "pct0", "Boundary %": "pct0"}[m["key"]]
    top, low = names[0], names[-1]
    title = (f"Per ball, {top} adds the most in the powerplay ({fmt(table[top]['Impact /100'], 'signed0')} per 100) and "
             f"{low} the least ({fmt(table[low]['Impact /100'], 'signed0')})")
    payload["method"] = "WPA /inns: win probability added an innings, in points. Ring: best in the column."
    return card("value", "scorecard", title, payload, f"Overs 1-6 · every men's T20 since {spec['since']:%b %Y}",
                "Fewer dots, more boundaries: the intent; Impact and WPA: the payoff")


def attack_card(db, spec) -> Optional[Dict[str, Any]]:
    """Each candidate against the opponent's main bowling types: new-ball pace in overs 1-6, the spinners in any over."""
    cols, table = [t["label"] for t in spec["attack"]], {}
    thin = set()
    for t in spec["attack"]:
        args = {"bowl_style": t["styles"]} if t.get("styles") else {"bowl_kind": t["kinds"]}
        if t.get("powerplay"):
            args["over_max"] = 5
        for r in _q(db, batters=spec["candidates"], group_by=["batter"], start_date=spec["since"], **args):
            name = _nm(spec, r["batter"])
            ok = (r.get("balls") or 0) >= MIN_BALLS
            table.setdefault(name, {})[t["label"]] = r["impact_per_100"] if ok else None
            if ok and r["balls"] < 60:
                thin.add(f"{name} v {t['label'].lower()} ({r['balls']} balls)")
    order = [_nm(spec, p) for p in spec["candidates"] if _nm(spec, p) in table]
    if len(order) < 2:
        return None
    payload = heat(table, cols, "", order)
    for r in payload["rows"]:
        r["short"] = r["name"]
        for c in cols:
            v = r["values"].get(c)
            r["pct"][c] = None if v is None else max(0.0, min(100.0, v))  # zero-centred: dark at or below average
    for m in payload["metrics"]:
        m["format"] = "signed0"
    best = {c: max((n for n in order if table[n].get(c) is not None), key=lambda n: table[n][c], default=None) for c in cols}
    a, b = cols[0], cols[1]
    title = f"Best against {a.lower()}: {best[a]}. Against {spec['attack'][1]['who']}'s {b.lower()}: {best[b]}"
    if len(cols) > 2 and best.get(cols[2]):
        title += f". Off-spin: {best[cols[2]]}" if cols[2].lower().startswith("off") else f". {cols[2]}: {best[cols[2]]}"
    payload["method"] = (f"Impact per 100 balls; – under {MIN_BALLS} balls. Brighter: above average."
                         + (f" Small: {', '.join(sorted(thin))}" if thin else ""))
    return card("attack", "scorecard", title, payload, f"Every men's T20 since {spec['since']:%b %Y}",
                " · ".join(t["help"] for t in spec["attack"]))


def lineups(db, spec, prof, value_rows) -> List[Dict[str, Any]]:
    """Every top three from the candidates with a keeper in it."""
    hands = {p: batter_hand(db, p) for p in spec["candidates"]}
    out = []
    for three in combinations(spec["candidates"], 3):
        if not any(p in spec["keepers"] for p in three):
            continue
        out_p = next(p for p in spec["candidates"] if p not in three)
        balls = sum(value_rows[p]["balls"] for p in three)
        out.append({"three": list(three), "out": out_p, "keeper": [p for p in three if p in spec["keepers"]],
                    "big": statistics.mean(prof[p]["big"] for p in three),
                    "cost": statistics.mean(prof[p]["cost"] for p in three),
                    "impact": 100 * sum(value_rows[p]["impact"] for p in three) / balls,
                    "lefties": sum(hands[p] == "LHB" for p in three), "inns": sum(prof[p]["n"] for p in three),
                    "right": [p for p in three if hands[p] == "RHB"]})
    return out


def lineups_card(spec, ups) -> Optional[Dict[str, Any]]:
    if len(ups) < 2:
        return None
    cols = ["Big %", "Cost %", "Impact /100", "Left-handers"]
    table = {f"Without {_nm(spec, u['out'])}": {"Big %": u["big"], "Cost %": u["cost"], "Impact /100": u["impact"],
                                                 "Left-handers": u["lefties"]} for u in ups}
    order = sorted(table, key=lambda k: -table[k]["Impact /100"])
    payload = heat(table, cols, "", order)
    for r in payload["rows"]:
        r["short"] = r["name"]
        r["pct"]["Cost %"] = 100 - (r["pct"]["Cost %"] or 0)
        r["pct"]["Left-handers"] = None
        lo = min(order, key=lambda k: table[k]["Cost %"])
        r["leader"] = [c for c in r["leader"] if c not in ("Cost %", "Left-handers")] + (["Cost %"] if r["name"] == lo else [])
    for m in payload["metrics"]:
        m["format"] = {"Big %": "pct0", "Cost %": "pct0", "Impact /100": "signed0", "Left-handers": "int"}[m["key"]]
    top = next(u for u in ups if f"Without {_nm(spec, u['out'])}" == order[0])
    title = (f"Leaving out {_nm(spec, top['out'])} gives the top three with the most Impact "
             f"({fmt(top['impact'], 'signed0')} per 100 balls)")
    if top["lefties"] == 3:
        title += ", and all three bat left-handed"
    payload["method"] = "The three's powerplay innings pooled. Ring: best in the column."
    payload["label_width"] = 140
    keepers = " or ".join(_nm(spec, k) for k in spec["keepers"])
    return card("lineups", "scorecard", title, payload, f"Overs 1-6 · every men's T20 since {spec['since']:%b %Y}",
                f"Each possible top three: {keepers} must play to keep wicket")


def case_slide(spec, ups, attack: Optional[Dict[str, Any]], caution: Optional[str] = None) -> Dict[str, Any]:
    """For and against each top three, every clause from the lineup and match-up numbers: a top three that leaves out
    the candidate best against one of the opponent's bowling types gives that up."""
    best = {}
    if attack:
        rows = attack["payload"]["rows"]
        for m in attack["payload"]["metrics"]:
            have = [r for r in rows if r["values"].get(m["key"]) is not None]
            if have:
                top = max(have, key=lambda r: r["values"][m["key"]])
                best[m["key"]] = (top["name"], top["values"][m["key"]])
    lefty_types = [t for t, (who, _v) in best.items() if t.lower().startswith("off")]
    rhb_names = {_nm(spec, p) for u in ups for p in u["right"]}
    extremes = {"imp": max(ups, key=lambda u: u["impact"]), "big": max(ups, key=lambda u: u["big"]),
                "cost": min(ups, key=lambda u: u["cost"]), "inns": max(ups, key=lambda u: u["inns"]),
                "low_imp": min(ups, key=lambda u: u["impact"]), "hi_cost": max(ups, key=lambda u: u["cost"])}
    lines = []
    for u in sorted(ups, key=lambda u: -u["impact"]):
        out = _nm(spec, u["out"])
        fors, againsts = [], []
        if u is extremes["imp"]:
            fors.append(f"most Impact ({fmt(u['impact'], 'signed0')})")
        if u is extremes["big"] and u is not extremes["imp"]:
            fors.append(f"most big innings ({u['big']:.0f}%)")
        if u is extremes["cost"]:
            fors.append(f"fails least ({u['cost']:.0f}%)")
        if u is extremes["inns"]:
            fors.append(f"most experience ({u['inns']} innings)")
        for t, (who, v) in best.items():
            if who == out:
                againsts.append(f"loses {who} v {t.lower()} ({fmt(v, 'signed0')})")
        if u is extremes["low_imp"]:
            againsts.append(f"least Impact ({fmt(u['impact'], 'signed0')})")
        if u is extremes["hi_cost"]:
            againsts.append(f"fails most ({u['cost']:.0f}%)")
        if u["lefties"] == 3 and lefty_types and best[lefty_types[0]][0] in rhb_names:
            againsts.append("all left-handed")
        keep = f" ({_nm(spec, u['keeper'][0])} keeps)" if len(u["keeper"]) == 1 else ""
        said = ", ".join(fors)
        if againsts:
            said = f"{said}. But {', '.join(againsts)}" if said else ", ".join(againsts)
        lines.append(f"Without {out}{keep}: {said}.")
    return {"type": "text", "heading": "The case, both ways", "body": "\n".join(lines + ([caution] if caution else []))}


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    mine = innings(db, spec, spec["candidates"])
    by = {p: [r for r in mine if r["batter"] == p] for p in spec["candidates"]}
    if any(len(v) < 15 for v in by.values()):
        return None
    prof = {p: profile(by[p]) for p in spec["candidates"]}
    first = groups_card(spec, by, prof)
    field = innings(db, spec)
    deep = field_card(spec, field, prof)
    if not deep:
        return None
    value_rows = {r["batter"]: r for r in _q(db, batters=spec["candidates"], group_by=["batter"], start_date=spec["since"],
                                             over_max=5)}
    ups = lineups(db, spec, prof, value_rows)
    attack = attack_card(db, spec)
    cards = [c for c in (first, deep, value_card(db, spec), attack, lineups_card(spec, ups)) if c]
    hook = hook_text(spec, mine)
    slides = ([{"type": "hook", "text": hook, "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [case_slide(spec, ups, attack, cameo_line(field)),
                 {"type": "end", "heading": "Every batter, free", "body": "Every batter, every phase: hindsightcricket.com"}])
    told = [c for c in cards if c is not deep]
    return {"slides": slides, "cards": cards, "title": hook, "verdict": " ".join(f"{c['title']}." for c in told[:2]),
            "players": spec["candidates"][:2],
            "deep_cut": {"probe": "boom-bust", "subject": spec["side"], "sentence": deep["title"], "by": "spotlight"}}
