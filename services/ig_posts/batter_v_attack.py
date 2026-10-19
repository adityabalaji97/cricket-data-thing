"""
A batter against the kind of bowling he's about to face, and against his side's other options for the job. From a
spec (services/ig_posts/spotlight.SPECS, type "batter_v_attack").

Slides: hook (written from the numbers: his strike rate against new-ball pace and how much of the opponent's bowling
is pace); the openers of both sides against new-ball pace (the lead chart: on a hero cover it moves onto slide 1);
the deeper cut (his runs by length against pace); his side's opening options in the powerplay; express against
fast-medium pace; his partnerships with the fixed opener; his record by competition; end. Every number from the
query builder, every men's T20 since `since` (leagues=[], include_international=False); code writes the titles.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.ig_posts.cards import card, fmt
from services.ig_posts.spotlight import heat, short_name

ALL_T20 = {"leagues": [], "include_international": False}
LENGTHS = [("FULL", "Full"), ("GOOD_LENGTH", "Good length"), ("SHORT_OF_A_GOOD_LENGTH", "Back of a length"),
           ("SHORT", "Short"), ("YORKER", "Yorker")]
PACE_TYPES = [("Express", ["RF", "LF"]), ("Fast-medium", ["RFM", "LFM", "LMF", "RMF"]),
              ("Medium", ["RM", "LM"])]  # row labels stay short: the scorecard's label column cuts long ones
MIN_BALLS = 25
SAME = 15        # Impact per 100 balls: closer than this, the types are no different


def _q(db, **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "T20", "gender": "male", "limit": 2000, "metrics_perspective": "batting", **ALL_T20}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


def _nm(spec, n: str) -> str:
    return spec.get("names", {}).get(n) or short_name(n)


def _plain(payload, scales: Dict[str, Optional[float]]):
    """Zero-centred shading (brighter above average, dark at or below), no rings: cells aren't ranked against each
    other. scales: {column: value that's brightest}; None leaves a column unshaded."""
    for r in payload["rows"]:
        r["short"] = r["name"]  # row labels are lengths and pace types, not names: no surname shortening
        r["leader"] = []
        for c, sc in scales.items():
            v = r["values"].get(c)
            r["pct"][c] = None if (sc is None or v is None) else max(0.0, min(100.0, 100 * v / sc))


def hook_text(db, spec, me_sr: float) -> str:
    rows = _q(db, bowling_teams=[spec["opponent"]], group_by=["bowl_kind"], start_date=spec["since"],
              include_international=True, metrics_perspective="bowling")
    total = sum(r.get("balls") or 0 for r in rows if r.get("bowl_kind") in ("pace bowler", "spin bowler"))
    pace = sum(r.get("balls") or 0 for r in rows if r.get("bowl_kind") == "pace bowler")
    pct = f" {spec['opponent']} bowl {100 * pace / total:.0f}% of their balls with pace." if total else ""
    return f"{spec['player']} scores at {me_sr:.0f} against new-ball pace.{pct}"


def openers_card(db, spec) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    rows = _q(db, batters=spec["openers"], group_by=["batter"], start_date=spec["since"], bowl_kind=["pace bowler"],
              over_max=5)
    rows = [r for r in rows if (r.get("balls") or 0) >= 100]
    if not any(r["batter"] == p for r in rows) or len(rows) < 4:
        return None
    rows.sort(key=lambda r: -(r.get("impact_per_100") or 0))
    me = next(r for r in rows if r["batter"] == p)
    out = [{"name": _nm(spec, r["batter"]), "value": r["impact_per_100"], "highlight": r["batter"] == p,
            "detail": f"SR {r['strike_rate']:.0f} · avg {r['average']:.0f} · {r['balls']} balls"} for r in rows]
    lead = rows[0]["batter"] == p
    title = (f"Against new-ball pace, {_nm(spec, p)} scores at {me['strike_rate']:.0f} and averages {me['average']:.0f}"
             + (": no opener in either squad adds more" if lead else ""))
    payload = {"metric": {"label": "Impact per 100 balls against new-ball pace", "format": "signed0", "signed": True},
               "rows": out, "label_width": 120}
    c = card("openers", "metric_bars", title, payload,
             f"{spec['sides']} openers · pace in overs 1-6 · every men's T20 since {spec['since']:%b %Y}",
             f"Impact per 100 balls: runs added to the team's projected total. {_nm(spec, p)}: {fmt(me['impact_per_100'], 'signed0')}")
    c["me_sr"] = me["strike_rate"]
    return c


def lengths_card(db, spec) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    rows = {r.get("length"): r for r in _q(db, batters=[p], group_by=["length"], start_date=spec["since"], bowl_kind=["pace bowler"])}
    table, order = {}, []
    for key, label in LENGTHS:
        r = rows.get(key)
        if not r or (r.get("balls") or 0) < MIN_BALLS:
            continue
        table[label] = {"Strike rate": r["strike_rate"], "Impact /100": r["impact_per_100"], "Balls": r["balls"]}
        order.append(label)
    if "Yorker" not in table or len(table) < 4:
        return None
    payload = heat(table, ["Strike rate", "Impact /100", "Balls"], "", order)
    _plain(payload, {"Strike rate": None, "Impact /100": 100, "Balls": None})
    for m in payload["metrics"]:
        m["format"] = {"Strike rate": "int", "Impact /100": "signed0", "Balls": "int"}[m["key"]]
    full, york = rows["FULL"], rows["YORKER"]
    title = (f"Pitch it up and {_nm(spec, p)} scores at {full['strike_rate']:.0f}. The yorker slows him: "
             f"{york['runs']} runs off {york['balls']} balls")
    payload["method"] = (f"Pace bowling, every men's T20 since {spec['since']:%b %Y}; tracked balls only; – under "
                         f"{MIN_BALLS} balls. Brighter: Impact above the average ball.")
    out = card("lengths", "scorecard", title, payload, f"{spec['player']} against pace, by length",
               f"Out {york['wickets']} times to {york['balls']} yorkers")
    out["kicker"] = "The deeper cut"
    return out


def options_card(db, spec) -> Optional[Dict[str, Any]]:
    """The side's opening options in the powerplay, against all bowling: strike rate, average, Impact, WPA."""
    rows = {r["batter"]: r for r in _q(db, batters=spec["options"], group_by=["batter"], start_date=spec["since"], over_max=5)
            if (r.get("balls") or 0) >= 100}
    if spec["player"] not in rows or len(rows) < 2:
        return None
    cols = ["Strike rate", "Average", "Impact /100", "WPA"]
    table = {_nm(spec, b): {"Strike rate": r["strike_rate"], "Average": r["average"], "Impact /100": r["impact_per_100"],
                            "WPA": r.get("wpa")} for b, r in rows.items()}
    order = sorted(table, key=lambda n: -(table[n]["Impact /100"] or -999))
    payload = heat(table, cols, _nm(spec, spec["player"]), order)
    leaders = {r["name"]: r["leader"] for r in payload["rows"]}
    for r in payload["rows"]:
        r["short"] = r["name"]
    for m in payload["metrics"]:
        m["format"] = {"Strike rate": "int", "Average": "dec1", "Impact /100": "signed0", "WPA": "signed2"}[m["key"]]
    me = _nm(spec, spec["player"])
    wins = len(leaders.get(me, []))
    others = [n for n in order if n != me]
    title = (f"In the powerplay, {me} beats {' and '.join(others)} on all {len(cols)} measures" if wins == len(cols)
             else f"In the powerplay, {me} leads {wins} of {len(cols)} measures against {' and '.join(others)}")
    payload["method"] = f"Overs 1-6, all bowling, every men's T20 since {spec['since']:%b %Y}. Ring: best in the column."
    return card("options", "scorecard", title, payload, f"{spec['team']}'s opening options · powerplay",
                f"{me} didn't open in the West Indies series; these are the candidates in the squad")


def pace_types_card(db, spec) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    table, order = {}, []
    for label, styles in PACE_TYPES:
        rs = _q(db, batters=[p], group_by=["batter"], start_date=spec["since"], bowl_style=styles)
        r = rs[0] if rs else None
        if not r or (r.get("balls") or 0) < MIN_BALLS:
            continue
        table[label] = {"Strike rate": r["strike_rate"], "Impact /100": r["impact_per_100"], "Balls": r["balls"]}
        order.append(label)
    if len(table) < 2:
        return None
    payload = heat(table, ["Strike rate", "Impact /100", "Balls"], "", order)
    _plain(payload, {"Strike rate": None, "Impact /100": 100, "Balls": None})
    for m in payload["metrics"]:
        m["format"] = {"Strike rate": "int", "Impact /100": "signed0", "Balls": "int"}[m["key"]]
    lo = min(order, key=lambda k: table[k]["Impact /100"])
    hi = max(order, key=lambda k: table[k]["Impact /100"])
    a, b = table[lo]["Impact /100"], table[hi]["Impact /100"]
    if b - a < SAME:  # a few runs apart is no difference: don't name a "best" type
        kinds = [k.lower() for k in order]
        said = kinds[0].capitalize() if len(kinds) == 1 else ", ".join(kinds[:-1]).capitalize() + " or " + kinds[-1]
        title = (f"{said}, it's all the same to {_nm(spec, p)}: {fmt(a, 'signed0')} to "
                 f"{fmt(b, 'signed0')} per 100 balls against each")
    else:
        title = (f"{_nm(spec, p)} is at his best against {hi.lower()} pace ({fmt(b, 'signed0')} per 100 balls) "
                 f"and least against {lo.lower()} ({fmt(a, 'signed0')})")
    payload["method"] = f"Every men's T20 since {spec['since']:%b %Y}; – under {MIN_BALLS} balls. Brighter: above average."
    return card("pace-types", "scorecard", title, payload, f"{spec['player']} by type of pace",
                "Express: RF/LF · fast-medium: RFM/LFM · medium: RM/LM. New Zealand's Ferguson and Milne are express; Henry, Duffy, Jamieson, Foulkes fast-medium")


def partner_card(db, spec) -> Optional[Dict[str, Any]]:
    """The fixed opener's powerplay partnerships, his with the subject highlighted: the doubt, said plainly."""
    rows = [r for r in _q(db, partnership_players=[spec["partner"]], group_by=["partnership"], start_date=spec["since"],
                          over_max=5, min_balls=60)]
    want = set(spec["options"])
    keep = []
    for r in rows:
        other = [n for n in r["partnership"].split(" & ") if n != spec["partner"]]
        if other and other[0] in want:
            keep.append((other[0], r))
    if not any(o == spec["player"] for o, _ in keep) or len(keep) < 2:
        return None
    keep.sort(key=lambda x: -x[1]["strike_rate"])
    out = [{"name": _nm(spec, o), "value": r["strike_rate"], "highlight": o == spec["player"],
            "detail": f"avg {r['average']:.0f} · {r['balls']} balls"} for o, r in keep]
    me = next(r for o, r in keep if o == spec["player"])
    slowest = keep[-1][0] == spec["player"]
    title = (f"With {_nm(spec, spec['partner'])}, {_nm(spec, spec['player'])}'s powerplay stands run at {me['strike_rate']:.0f}"
             + (", the slowest of his pairs" if slowest else "") + f", from just {me['balls']} balls")
    payload = {"metric": {"label": "partnership strike rate, overs 1-6", "format": "int", "signed": False}, "rows": out,
               "label_width": 120}
    c = card("partner", "metric_bars", title, payload,
             f"{_nm(spec, spec['partner'])}'s opening partnerships, overs 1-6 · every men's T20 since {spec['since']:%b %Y}",
             "A small sample: the pair has rarely batted together")
    c["small_sample"] = True
    return c


def comps_card(db, spec) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    rows = [r for r in _q(db, batters=[p], group_by=["competition"], start_date=spec["since"], bowl_kind=["pace bowler"])
            if (r.get("balls") or 0) >= 40]
    if len(rows) < 2:
        return None
    rows.sort(key=lambda r: -(r.get("balls") or 0))
    out = [{"name": r["competition"], "value": r["strike_rate"], "highlight": r["competition"] == "T20I",
            "detail": f"{r['runs']} off {r['balls']} · Impact {fmt(r['impact_per_100'], 'signed0')} per 100"} for r in rows]
    t = next((r for r in rows if r["competition"] == "T20I"), None)
    title = (f"It's not just the IPL: against pace in T20Is he scores at {t['strike_rate']:.0f}, from {t['balls']} balls"
             if t else f"{_nm(spec, p)} against pace, competition by competition")
    payload = {"metric": {"label": "strike rate against pace", "format": "int", "signed": False}, "rows": out, "label_width": 150}
    c = card("comps", "metric_bars", title, payload, f"{spec['player']} against pace · every men's T20 since {spec['since']:%b %Y}",
             "The T20I sample is small")
    c["small_sample"] = True
    return c


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    first, deep = openers_card(db, spec), lengths_card(db, spec)
    if not first or not deep:
        return None
    cards = [c for c in (first, deep, options_card(db, spec), pace_types_card(db, spec), partner_card(db, spec),
                         comps_card(db, spec)) if c]
    hook = hook_text(db, spec, first.pop("me_sr"))
    slides = ([{"type": "hook", "text": hook, "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [{"type": "end", "heading": "Every batter, free", "body": "Every batter against every length: hindsightcricket.com"}])
    told = [c for c in cards if c is not deep]
    return {"slides": slides, "cards": cards, "title": hook, "verdict": " ".join(f"{c['title']}." for c in told[:2]),
            "players": [spec["player"]],
            "deep_cut": {"probe": "lengths", "subject": spec["player"], "sentence": deep["title"], "by": "spotlight"}}
