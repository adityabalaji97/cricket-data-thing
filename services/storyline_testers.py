"""
Storyline testers (MATCH_PREVIEW_STORYLINES_PLAN.md chunk 3): each approved talking point answered from the data.

A tester is a fixed query-builder recipe per kind of point. It returns
    {verdict, finding, card, query_url, direction}
verdict: supported | not supported | partly | too little data | context. The finding is one sentence with the numbers
(player and number first); the card is a story card the preview's storylines chapter shows (chunk 4). Every number
comes from the query builder; the model only says which way a claim points (up / down / neither), never a number.

Kinds without a fixed test (injury, record, milestone, a selection call) are 'context': the point can lead a preview
as what's being said, with the player's relevant numbers where there's a player, but no verdict.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

YEARS = 2
RECENT = 10               # innings / spells for "form"
MIN_RECENT_BALLS = 60
MIN_BASE_BALLS = 200
FORM_GAP = 10             # runs above par per 100 balls between recent and usual that counts as a change
MATCHUP_MIN_BALLS = 18
SHRINK = 120              # as players.battles: shrink a head-to-head edge toward zero by n / (n + SHRINK)


def _q(db, fmt: str = "T20", **kw) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": fmt, "gender": "male", "leagues": [], "include_international": False, "limit": 10000}
    return run_deliveries_query(db, **{**base, **kw})["data"]


def _since(days: int = 365 * YEARS) -> date:
    return date.today() - timedelta(days=days)


def _url(**params) -> str:
    from services.ig_links import query_path

    group_by = params.pop("group_by")
    return "https://hindsightcricket.com" + query_path(params, group_by)


def direction(claim: str, about: str) -> Dict[str, str]:
    """Which way the claim points for `about` ('up': doing well / in form / on top; 'down'; 'neither') and what it's
    about ('batting', 'bowling' or 'both'). One light call; never a number."""
    from services import llm
    from services.ig_reel_v2 import _client

    prompt = (f'Claim: "{claim}"\nAbout: {about}\n1. Does the claim say {about} is doing well / in good form / on top '
              '("up"), doing badly / out of form / struggling ("down"), or neither?\n2. Is it about batting, bowling, or '
              'both?\nReply JSON {"direction": "up|down|neither", "aspect": "batting|bowling|both"}.')
    try:
        resp = _client().chat.completions.create(model=llm.MODEL_LIGHT, response_format={"type": "json_object"},
                                                 messages=[{"role": "user", "content": prompt}],
                                                 **llm.chat_kwargs(llm.MODEL_LIGHT, 60, temperature=0))
        d = json.loads(resp.choices[0].message.content or "{}")
        return {"direction": d.get("direction") if d.get("direction") in ("up", "down", "neither") else "neither",
                "aspect": d.get("aspect") if d.get("aspect") in ("batting", "bowling", "both") else "both"}
    except Exception as exc:  # a test without a direction is still a finding
        logger.warning("storyline direction failed: %r", exc)
        return {"direction": "neither", "aspect": "both"}


def _verdict(direction_: str, gap: float, enough: bool) -> str:
    if not enough:
        return "too little data"
    moved = "up" if gap >= FORM_GAP else "down" if gap <= -FORM_GAP else "steady"
    if direction_ == "neither":
        return "context"
    if moved == "steady":
        return "partly"
    return "supported" if moved == direction_ else "not supported"


def _role(db, player: str, fmt: str = "T20", aspect: str = "both") -> str:
    """'bat' or 'bowl': what the claim is about if it says, else where most of his last two years' balls are."""
    if aspect in ("batting", "bowling"):
        return "bat" if aspect == "batting" else "bowl"
    bat = sum(r["balls"] for r in _q(db, fmt, batters=[player], group_by=["batter"], start_date=_since(),
                                     metrics_perspective="batting"))
    bowl = sum(r["balls"] for r in _q(db, fmt, bowlers=[player], group_by=["bowler"], start_date=_since(),
                                      metrics_perspective="bowling"))
    return "bat" if bat >= bowl else "bowl"


# --------------------------------------------------------------------------------------------
# form: the last RECENT innings / spells against the two years before them
# --------------------------------------------------------------------------------------------

FORM_GAP_SR = 15          # ODIs (no Primer metrics): strike-rate points
FORM_GAP_ECON = 0.6       # ODIs: runs an over


def form(db, point: Dict[str, Any], fmt: str = "T20") -> Optional[Dict[str, Any]]:
    if not point.get("players"):
        return None
    player = point["players"][0]
    dd = direction(point["claim"], player)
    role = _role(db, player, fmt, dd["aspect"])
    who, persp = ("batters", "batting") if role == "bat" else ("bowlers", "bowling")
    rows = _q(db, fmt, **{who: [player]}, group_by=["match_id", "match_date"], start_date=_since(),
              metrics_perspective=persp)
    rows = sorted((r for r in rows if r.get("balls")), key=lambda r: str(r["match_date"]), reverse=True)
    recent, before = rows[:RECENT], rows[RECENT:]

    def agg(rs):
        balls = sum(r["balls"] for r in rs)
        raa = [r.get("raa_per_100") for r in rs]
        per100 = (100 * sum((r.get("raa_per_100") or 0) * r["balls"] / 100 for r in rs) / balls
                  if balls and all(v is not None for v in raa) else None)
        rate = 100 * sum(r["runs"] for r in rs) / balls if balls else None
        return balls, per100, rate

    rb, rr, rsr = agg(recent)
    bb, br, bsr = agg(before)
    enough = rb >= MIN_RECENT_BALLS and bb >= MIN_BASE_BALLS and rsr is not None and bsr is not None
    what = "innings" if role == "bat" else "spells"
    primer = rr is not None and br is not None
    if not enough:
        return {"verdict": "too little data", "finding": f"{player}: too few balls to compare his last {RECENT} {what}",
                "card": None, "direction": dd["direction"], "query_url": None}
    if primer:
        gap, scale = rr - br, 1.0
        lead = f"{player}: {rr:+.0f} runs above par per 100 balls in his last {len(recent)} {what}, {br:+.0f} in the two years before"
        metric, rows_ = ({"label": "Runs above par per 100 balls", "format": "signed0", "signed": True},
                         [round(rr), round(br)])
    elif role == "bat":  # an ODI: strike rate
        gap, scale = (rsr - bsr) * FORM_GAP / FORM_GAP_SR, 1.0
        lead = f"{player}: strike rate {rsr:.0f} in his last {len(recent)} innings, {bsr:.0f} in the two years before"
        metric, rows_ = {"label": "Strike rate", "format": "int", "signed": False}, [round(rsr), round(bsr)]
    else:  # an ODI: economy (lower is better, so the gap is turned round)
        re_, be = 6 * rsr / 100, 6 * bsr / 100
        gap, scale = (be - re_) * FORM_GAP / FORM_GAP_ECON, 1.0
        lead = f"{player}: {re_:.1f} an over in his last {len(recent)} spells, {be:.1f} in the two years before"
        metric, rows_ = {"label": "Runs per over", "format": "dec1", "signed": False}, [round(re_, 1), round(be, 1)]
    extra = (f"; strike rate {rsr:.0f} (usually {bsr:.0f})" if role == "bat" else
             f"; economy {6 * rsr / 100:.1f} (usually {6 * bsr / 100:.1f})") if primer else ""
    card = {"id": f"storyline-{point['id']}", "visual": "metric_bars", "title": lead, "help": "",
            "sample": f"{player} · men's {fmt}s, {YEARS} years · last {len(recent)} {what} v the rest",
            "payload": {"metric": metric,
                        "rows": [{"name": f"Last {len(recent)} {what}", "value": rows_[0], "highlight": True, "detail": f"{rb} balls"},
                                 {"name": "The two years before", "value": rows_[1], "detail": f"{bb} balls"}]}}
    return {"verdict": _verdict(dd["direction"], gap * scale, True), "finding": lead + extra, "card": card,
            "direction": dd["direction"],
            "query_url": _url(**{who: [player]}, start_date=_since(), metrics_perspective=persp, group_by=["match_id"])}


# --------------------------------------------------------------------------------------------
# matchup: batter v bowler (two players), or a batter v pace and spin
# --------------------------------------------------------------------------------------------

def matchup(db, point: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    players = point.get("players") or []
    if not players:
        return None
    if len(players) >= 2:
        roles = {p: _role(db, p) for p in players[:2]}
        bat = next((p for p in players[:2] if roles[p] == "bat"), players[0])
        bowl = next((p for p in players[:2] if p != bat), players[1])
        h2h = _q(db, batters=[bat], bowlers=[bowl], group_by=["batter"], metrics_perspective="batting")
        base = _q(db, batters=[bat], group_by=["batter"], start_date=_since(365 * 4), metrics_perspective="batting")
        if not h2h or (h2h[0]["balls"] or 0) < MATCHUP_MIN_BALLS:
            n = h2h[0]["balls"] if h2h else 0
            return {"verdict": "too little data", "finding": f"{bat} v {bowl}: {n} balls, too few to say", "card": None,
                    "direction": "neither", "query_url": _url(batters=[bat], bowlers=[bowl], group_by=["batter"])}
        r = h2h[0]
        n = r["balls"]
        edge = ((r.get("raa_per_100") or 0) - ((base[0].get("raa_per_100") or 0) if base else 0)) * n / (n + SHRINK)
        d = direction(point["claim"], bat)["direction"]
        finding = (f"{bat} v {bowl}: {r['runs']} off {n} balls, out {r['wickets']} times; {edge:+.0f} runs per 100 balls "
                   f"against what {bat} usually does")
        card = {"id": f"storyline-{point['id']}", "visual": "metric_bars", "title": finding.split(";")[0], "help": "",
                "sample": f"{bat} v {bowl} · every men's T20 · edge shrunk for {n} balls",
                "payload": {"metric": {"label": "Strike rate", "format": "int", "signed": False},
                            "rows": [{"name": f"v {bowl}", "value": round(r["strike_rate"] or 0), "highlight": True,
                                      "detail": f"{n} balls · {r['wickets']} out"},
                                     {"name": "v everyone (4 years)", "value": round((base[0]["strike_rate"] or 0) if base else 0),
                                      "detail": f"{base[0]['balls'] if base else 0} balls"}]}}
        return {"verdict": _verdict(d, edge, True), "finding": finding, "card": card, "direction": d,
                "query_url": _url(batters=[bat], bowlers=[bowl], group_by=["batter"])}
    player = players[0]
    rows = {r["bowl_kind"]: r for r in _q(db, batters=[player], group_by=["bowl_kind"], start_date=_since(),
                                          metrics_perspective="batting") if r.get("bowl_kind") in ("pace bowler", "spin bowler")}
    if len(rows) < 2:
        return {"verdict": "too little data", "finding": f"{player}: not enough balls against pace and spin",
                "card": None, "direction": "neither", "query_url": None}
    p, s = rows["pace bowler"], rows["spin bowler"]
    finding = (f"{player}: {p['raa_per_100'] or 0:+.0f} runs above par per 100 balls v pace, {s['raa_per_100'] or 0:+.0f} "
               f"v spin (two years)")
    card = {"id": f"storyline-{point['id']}", "visual": "metric_bars", "title": finding, "help": "",
            "sample": f"{player} · every men's T20, {YEARS} years",
            "payload": {"metric": {"label": "Runs above par per 100 balls", "format": "signed0", "signed": True},
                        "rows": [{"name": "v pace", "value": round(p["raa_per_100"] or 0), "detail": f"{p['balls']} balls"},
                                 {"name": "v spin", "value": round(s["raa_per_100"] or 0), "detail": f"{s['balls']} balls"}]}}
    return {"verdict": "context", "finding": finding, "card": card, "direction": "neither",
            "query_url": _url(batters=[player], start_date=_since(), metrics_perspective="batting", group_by=["bowl_kind"])}


# --------------------------------------------------------------------------------------------
# tactics: the side's batting by phase against par (last 12 months, its main competition)
# --------------------------------------------------------------------------------------------

def tactics(db, point: Dict[str, Any], fixture: Dict[str, Any], fmt: str = "T20") -> Optional[Dict[str, Any]]:
    """The side's batting or bowling by phase against par, last 12 months (T20s; ODIs: runs per over)."""
    team = point.get("team") if point.get("team") in (fixture["team1"], fixture["team2"]) else None
    if not team:
        return None
    aspect = direction(point["claim"], team)["aspect"]
    bowling = aspect == "bowling"
    kw = ({"bowling_teams": [team], "metrics_perspective": "bowling"} if bowling else
          {"batting_teams": [team], "metrics_perspective": "batting"})
    rows = {r["phase"]: r for r in _q(db, fmt, **kw, group_by=["phase"], start_date=_since(365), include_international=True)}
    phases = [p for p in ("powerplay", "middle", "death") if p in rows]
    if len(phases) < 3:
        return None
    primer = all(rows[p].get("raa_per_100") is not None for p in phases)
    if primer:
        vals = {p: rows[p]["raa_per_100"] for p in phases}  # bowling perspective: + = runs saved
        label, fmt_ = ("Runs saved per 100 balls" if bowling else "Runs above par per 100 balls"), "signed0"
    else:
        vals = {p: 6 * rows[p]["runs"] / rows[p]["balls"] for p in phases}
        label, fmt_ = "Runs per over", "dec1"
    better = (min if (bowling and not primer) else max)
    best = better(vals, key=vals.get)
    worst = (max if better is min else min)(vals, key=vals.get)
    words = {"powerplay": "the powerplay", "middle": "the middle overs", "death": "the death"}
    verb = "bowl" if bowling else "bat"
    if primer:
        unit = "runs saved per 100 balls" if bowling else "runs above par per 100 balls"
        finding = f"{team} {verb} {vals[best]:+.0f} {unit} in {words[best]}, {vals[worst]:+.0f} in {words[worst]} (12 months)"
    else:
        finding = f"{team} {verb}: {vals[best]:.1f} an over in {words[best]}, {vals[worst]:.1f} in {words[worst]} (12 months)"
    card = {"id": f"storyline-{point['id']}", "visual": "metric_bars", "title": finding, "help": "",
            "sample": f"{team} {'bowling' if bowling else 'batting'} · men's {fmt}s, 12 months",
            "payload": {"metric": {"label": label, "format": fmt_, "signed": primer},
                        "rows": [{"name": words[p].capitalize(), "value": round(vals[p], 1 if not primer else 0),
                                  "highlight": p in (best, worst), "detail": f"{rows[p]['balls']} balls"} for p in phases]}}
    return {"verdict": "context", "finding": finding, "card": card, "direction": "neither",
            "query_url": _url(**kw, start_date=_since(365), include_international=True, group_by=["phase"])}


# --------------------------------------------------------------------------------------------
# conditions: the ground's pace and spin, against its country's grounds
# --------------------------------------------------------------------------------------------

def conditions(db, point: Dict[str, Any], fixture: Dict[str, Any], fmt: str = "T20") -> Optional[Dict[str, Any]]:
    venue = fixture.get("venue")
    if not venue:
        return None
    rows = {r["bowl_kind"]: r for r in _q(db, fmt, venue=venue, group_by=["bowl_kind"], start_date=_since(365 * 5),
                                          metrics_perspective="bowling") if r.get("bowl_kind") in ("pace bowler", "spin bowler")}
    if len(rows) < 2 or sum(r["balls"] for r in rows.values()) < 1200:
        return {"verdict": "too little data", "finding": f"Too few matches at {venue} to say", "card": None,
                "direction": "neither", "query_url": None}
    econ = {k: 6 * r["runs"] / r["balls"] for k, r in rows.items()}
    share = 100 * rows["spin bowler"]["balls"] / sum(r["balls"] for r in rows.values())
    finding = (f"At {venue.split(',')[0]}, seamers go at {econ['pace bowler']:.1f} an over and spinners at "
               f"{econ['spin bowler']:.1f}; spin bowls {share:.0f}% of the overs (5 years)")
    card = {"id": f"storyline-{point['id']}", "visual": "metric_bars", "title": finding.split(";")[0], "help": "",
            "sample": f"{venue} · every men's T20, 5 years",
            "payload": {"metric": {"label": "Runs per over", "format": "dec1", "signed": False},
                        "rows": [{"name": "Pace", "value": round(econ["pace bowler"], 1), "detail": f"{rows['pace bowler']['balls']} balls"},
                                 {"name": "Spin", "value": round(econ["spin bowler"], 1), "detail": f"{rows['spin bowler']['balls']} balls"}]}}
    return {"verdict": "context", "finding": finding, "card": card, "direction": "neither",
            "query_url": _url(venue=venue, start_date=_since(365 * 5), metrics_perspective="bowling", group_by=["bowl_kind"])}


def run(db, point: Dict[str, Any], fixture: Dict[str, Any]) -> Dict[str, Any]:
    """The point's test in the fixture's format; 'context' with no numbers when nothing fits."""
    fmt = "ODI" if str(fixture.get("format") or "").upper().startswith("ODI") else "T20"
    kind = point["kind"]
    try:
        if kind == "form":
            out = form(db, point, fmt) if point.get("players") else tactics(db, point, fixture, fmt)
        elif kind == "matchup":
            out = matchup(db, point)
        elif kind == "tactics":
            out = tactics(db, point, fixture, fmt) or (form(db, point, fmt) if point.get("players") else None)
        elif kind == "conditions":
            out = conditions(db, point, fixture, fmt)
        elif kind == "selection" and point.get("players"):
            out = form(db, point, fmt)
            if out and out["verdict"] != "too little data":
                out["verdict"] = "context"  # his numbers, not a verdict on a selection call
        else:
            out = None
    except Exception as exc:
        logger.warning("storyline tester %s failed: %r", kind, exc)
        out = None
    return out or {"verdict": "context", "finding": None, "card": None, "direction": "neither", "query_url": None}
