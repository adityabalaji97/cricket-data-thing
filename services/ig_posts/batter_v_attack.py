"""
A batter against the kind of bowling he's about to face: the openers of both sides against new-ball pace, where his
runs come from by length, and his record by competition. From a spec (services/ig_posts/spotlight.SPECS, type
"batter_v_attack"). Every number from the query builder; code writes the titles. Every men's T20 since `since`
(leagues=[], include_international=False).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.ig_posts.cards import card, fmt
from services.ig_posts.spotlight import heat, short_name

ALL_T20 = {"leagues": [], "include_international": False}
LENGTHS = [("FULL", "Full"), ("GOOD_LENGTH", "Good length"), ("SHORT_OF_A_GOOD_LENGTH", "Back of a length"),
           ("SHORT", "Short"), ("YORKER", "Yorker")]
MIN_BALLS = 25


def _q(db, **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "T20", "gender": "male", "limit": 2000, "metrics_perspective": "batting", **ALL_T20}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


def _nm(spec, n: str) -> str:
    return spec.get("names", {}).get(n) or short_name(n)


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
    payload = {"metric": {"label": "Impact per 100 balls", "format": "signed0", "signed": True}, "rows": out, "label_width": 120}
    return card("openers", "metric_bars", title, payload,
                f"{spec['sides']} openers · pace in overs 1-6 · every men's T20 since {spec['since']:%b %Y}",
                f"Impact per 100 balls: runs added to the team's projected total. {_nm(spec, p)}: {fmt(me['impact_per_100'], 'signed0')}")


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
    for r in payload["rows"]:
        r["short"] = r["name"]
        r["leader"] = []
        r["pct"]["Balls"] = None
        imp = r["values"]["Impact /100"]
        r["pct"]["Impact /100"] = max(0.0, min(100.0, imp))  # brighter above the average ball, dark at or below
        r["pct"]["Strike rate"] = max(0.0, min(100.0, (r["values"]["Strike rate"] - 100) / 2))
    for m in payload["metrics"]:
        m["format"] = {"Strike rate": "int", "Impact /100": "signed0", "Balls": "int"}[m["key"]]
    full, york = rows["FULL"], rows["YORKER"]
    title = (f"Pitch it up and {_nm(spec, p)} scores at {full['strike_rate']:.0f}. The yorker slows him: "
             f"{york['runs']} runs off {york['balls']} balls")
    payload["method"] = f"Pace bowling, every men's T20 since {spec['since']:%b %Y}; tracked balls only; – under {MIN_BALLS} balls."
    out = card("lengths", "scorecard", title, payload, f"{spec['player']} against pace, by length",
               f"Out {york['wickets']} times to {york['balls']} yorkers")
    out["kicker"] = "The deeper cut"
    return out


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
    payload = {"metric": {"label": "strike rate", "format": "int", "signed": False}, "rows": out, "label_width": 150}
    c = card("comps", "metric_bars", title, payload, f"{spec['player']} against pace · every men's T20 since {spec['since']:%b %Y}",
             "The T20I sample is small")
    c["small_sample"] = True
    return c


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    first, deep = openers_card(db, spec), lengths_card(db, spec)
    cards = [c for c in (first, deep, comps_card(db, spec)) if c]
    if not first or not deep:
        return None
    nm = _nm(spec, spec["player"])
    watch = {"type": "text", "heading": "What to watch",
             "body": "\n".join([f"For India: {first['title'].split(':')[0]}", f"For New Zealand: the yorker. {deep['help']}",
                                spec["watch"]])}
    slides = ([{"type": "hook", "text": spec["hook"], "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [watch, {"type": "end", "heading": "Every batter, free", "body": "Every batter against every length: hindsightcricket.com"}])
    return {"slides": slides, "cards": cards, "title": spec["hook"], "verdict": " ".join(f"{c['title']}." for c in [first, cards[-1]]),
            "players": [spec["player"]],
            "deep_cut": {"probe": "lengths", "subject": spec["player"], "sentence": deep["title"], "by": "spotlight"}}
