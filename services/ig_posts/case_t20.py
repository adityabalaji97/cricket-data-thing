"""
"The case for ..." in T20Is: a spotlight post on a batter fans want back in India's T20I side, from a spec
(services/ig_posts/spotlight.SPECS, type "case_t20"). Made in Impact (runs added to the team's projected total) and WPA
(win probability added), with strike rate only as context.

Slides: hook; the hole (India's no. 3 to 7 with him in the side and since his last game); the deeper cut (his Impact
per 100 balls against pace and spin, year by year); his arc (Impact an innings in T20Is and the IPL); the alternatives
(the batters India have used at 3 to 7 since, against pace, against spin and on WPA, over the last year); when it
mattered (WPA at the spec's big event); the case both ways; end.

Every number comes from the query builder and code writes every title. Windows run to today, so the morning check's
rebuild picks up the latest game.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from services.ig_posts.cards import card, fmt
from services.ig_posts.spotlight import _pct, heat, short_name

POSITIONS = [3, 4, 5, 6, 7]   # the middle order the post is about
MIN_YEAR_BALLS = 40           # a year (or a year against one bowler type) needs this many balls for a number
PEER_MIN_BALLS = 60           # T20I balls at 3 to 7 since the last game to be one of the alternatives
MAX_PEERS = 7
EVENT_MIN_BALLS = 30


def _q(db, **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "T20", "gender": "male", "limit": 2000, "metrics_perspective": "batting"}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


T20I = {"leagues": [], "include_international": True}          # internationals only
IPL = {"leagues": ["IPL"], "include_international": False}
T20I_IPL = {"leagues": ["IPL"], "include_international": True}


def _names(names: List[str]) -> str:
    return ", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else "".join(names)


def _name(spec, n: str) -> str:
    return spec["display"] if n == spec["player"] else spec.get("names", {}).get(n) or short_name(n)


def _team(spec, t: str) -> str:
    return spec.get("teams", {}).get(t, t)


def _per100(rows: List[Dict[str, Any]], min_balls: int = 1) -> Optional[float]:
    balls = sum(r.get("balls") or 0 for r in rows)
    if balls < min_balls:
        return None
    return 100 * sum(r.get("impact") or 0 for r in rows) / balls


def _wpa(rows: List[Dict[str, Any]]) -> float:
    return sum(r.get("wpa") or 0 for r in rows)


def _flat(payload, table, cols_by_measure: List[List[str]]):
    """One player (or one team) across columns: shade each measure's columns against each other, no rings."""
    order = [r["name"] for r in payload["rows"]]
    for cols in cols_by_measure:
        flat = _pct({f"{n}|{c}": table[n].get(c) for n in order for c in cols})
        for r in payload["rows"]:
            r["leader"] = []
            for c in cols:
                r["pct"][c] = flat[f"{r['name']}|{c}"]


def hole_card(db, spec) -> Optional[Dict[str, Any]]:
    """India's no. 3 to 7 in T20Is: from `with_from` to his last game, and since."""
    last = spec["last_game"]
    team = {"batting_teams": [spec["team"]], **T20I, "group_by": ["batting_position"]}
    before = [r for r in _q(db, **team, start_date=spec["with_from"], end_date=last) if r.get("batting_position") in POSITIONS]
    since = [r for r in _q(db, **team, start_date=last + timedelta(days=1)) if r.get("batting_position") in POSITIONS]
    if sum(r.get("balls") or 0 for r in since) < 300:
        return None
    by = lambda rows, p: [r for r in rows if r["batting_position"] == p]  # noqa: E731
    # Games in each period: every innings has a no. 3 (so does almost every game's); the openers' count is exact.
    games = lambda p: max((r.get("innings_count") or 0) for r in _q(db, batting_teams=[spec["team"]], **T20I,  # noqa: E731
                                                                    group_by=["batting_position"], **p) if r.get("batting_position") == 1)
    gw, gs = games({"start_date": spec["with_from"], "end_date": last}), games({"start_date": last + timedelta(days=1)})
    cols = ["Impact · with", "Impact · since", f"WPA · with ({gw} games)", f"WPA · since ({gs} games)"]
    table = {}
    for p in POSITIONS:
        table[f"No. {p}"] = {cols[0]: _per100(by(before, p), MIN_YEAR_BALLS), cols[1]: _per100(by(since, p), MIN_YEAR_BALLS),
                             cols[2]: _wpa(by(before, p)), cols[3]: _wpa(by(since, p))}
    table["3 to 7"] = {cols[0]: _per100(before), cols[1]: _per100(since), cols[2]: _wpa(before), cols[3]: _wpa(since)}
    order = list(table)
    payload = heat(table, cols, "3 to 7", order)
    for r in payload["rows"]:
        r["short"] = r["name"]
    for m in payload["metrics"]:
        m["format"] = "signed1" if m["key"].startswith("Impact") else "signed2"
    _flat(payload, table, [cols[:2], cols[2:]])
    a, b = table["3 to 7"][cols[0]], table["3 to 7"][cols[1]]
    worst = min(POSITIONS, key=lambda p: (table[f"No. {p}"][cols[1]] or 0) - (table[f"No. {p}"][cols[0]] or 0))
    word = "down from" if b < a else "up from"
    title = f"Since {spec['display']}'s last T20I, India's no. 3 to 7 add {fmt(b, 'signed1')} Impact per 100 balls, {word} {fmt(a, 'signed1')}"
    help_ = (f"Win probability added: {fmt(table['3 to 7'][cols[2]], 'signed2')} with him in the side, "
             f"{fmt(table['3 to 7'][cols[3]], 'signed2')} since. The biggest drop is at no. {worst}")
    payload["method"] = (f"With: T20Is {spec['with_from']:%b %Y} to {last:%-d %b %Y}, his own balls included. Since: every "
                         "T20I after. Impact per 100 balls; WPA in wins (+1.00 = one win). Brighter is better.")
    return card("hole", "scorecard", title, payload,
                f"India's batters at 3 to 7 in T20Is · {sum(r['balls'] for r in since):,} balls since", help_)


def pace_spin_card(db, spec) -> Optional[Dict[str, Any]]:
    p, years = spec["player"], [str(y) for y in spec["years"]]
    t = _q(db, batters=[p], **T20I, batting_teams=[spec["team"]], group_by=["year", "bowl_kind"], start_date=date(spec["years"][0], 1, 1))
    i = _q(db, batters=[p], **IPL, group_by=["year", "bowl_kind"], start_date=date(spec["years"][0], 1, 1))

    def row(rows, kind):
        return {y: _per100([r for r in rows if str(r["year"]) == y and r.get("bowl_kind") == kind], MIN_YEAR_BALLS) for y in years}
    table = {"T20Is v pace": row(t, "pace bowler"), "T20Is v spin": row(t, "spin bowler"),
             "IPL v pace": row(i, "pace bowler"), "IPL v spin": row(i, "spin bowler")}
    order = list(table)
    payload = heat(table, years, "", order)
    for r in payload["rows"]:
        r["short"] = r["name"]
    for m in payload["metrics"]:
        m["format"] = "signed0"
    _flat(payload, table, [years])
    nm = spec["display"]
    spin = [v for v in table["T20Is v spin"].values() if v is not None]
    pace = [v for v in table["T20Is v pace"].values() if v is not None]
    if spin and min(spin) > 0 and pace:
        title = (f"In T20Is, {nm} adds Impact against spin every year. Against pace he swings from "
                 f"{fmt(max(pace), 'signed0')} to {fmt(min(pace), 'signed0')}")
    else:
        title = f"{nm}'s Impact per 100 balls against pace and spin, year by year"
    worst = min(((k, y) for k in ("T20Is v pace", "IPL v pace") for y in years if table[k][y] is not None), key=lambda ky: table[ky[0]][ky[1]])
    wr = [r for r in (t if worst[0].startswith("T20I") else i) if str(r["year"]) == worst[1] and r.get("bowl_kind") == "pace bowler"]
    outs, balls = sum(r.get("wickets") or 0 for r in wr), sum(r.get("balls") or 0 for r in wr)
    help_ = (f"Impact per 100 balls. The low: {worst[0].split(' v ')[0]} {worst[1]}, out {outs} "
             f"times in {balls} balls of pace") if outs else ""
    payload["method"] = f"Impact per 100 balls, wickets included; – under {MIN_YEAR_BALLS} balls. Brighter is better."
    out = card("pace-spin", "scorecard", title, payload, f"{p} · T20Is for {spec['team']} and the IPL, by calendar year", help_)
    out["kicker"] = "The deeper cut"
    return out


def arc_card(db, spec) -> Optional[Dict[str, Any]]:
    p, years = spec["player"], [str(y) for y in spec["years"]]
    t = {str(r["year"]): r for r in _q(db, batters=[p], **T20I, batting_teams=[spec["team"]], group_by=["year"], start_date=date(spec["years"][0], 1, 1))}
    i = {str(r["year"]): r for r in _q(db, batters=[p], **IPL, group_by=["year"], start_date=date(spec["years"][0], 1, 1))}
    ipi = lambda r: (r["impact"] / r["innings_count"]) if r and r.get("innings_count") else None  # noqa: E731
    table = {"T20Is": {y: ipi(t.get(y)) for y in years}, "IPL": {y: ipi(i.get(y)) for y in years}}
    if sum(v is not None for v in table["T20Is"].values()) < 3:
        return None
    payload = heat(table, years, "", list(table))
    for r in payload["rows"]:
        r["short"] = r["name"]
    _flat(payload, table, [years])
    nm, last = spec["display"], years[-1]
    bits = []
    tl = table["T20Is"].get(last)
    if tl is not None:
        since = next((y for y in reversed(years[:-1]) if table["T20Is"][y] is not None and table["T20Is"][y] >= tl), None)
        bits.append(f"{nm}'s {last} T20Is: {fmt(tl, 'signed1')} Impact an innings" + (f", his best since {since}" if since else ""))
    il = table["IPL"].get(last)
    if il is not None and all(il <= v for v in table["IPL"].values() if v is not None):
        bits.append(f"IPL {last}: {fmt(il, 'signed1')}, his worst season")
    if not bits:
        return None
    wpa = lambda d, y: fmt(d[y]["wpa"], "signed2") if d.get(y) else "–"  # noqa: E731
    help_ = "WPA by year · T20Is " + ", ".join(f"{y} {wpa(t, y)}" for y in years[-3:]) + " · IPL " + \
        ", ".join(f"{y} {wpa(i, y)}" for y in years[-3:])
    payload["method"] = (f"Impact an innings, wickets included. {last} T20Is run to his last game "
                         f"({spec['last_game']:%-d %b}). Brighter is better.")
    return card("arc", "scorecard", ". ".join(bits), payload, f"{p} · T20Is for {spec['team']} and the IPL", help_)


def peers(db, spec) -> List[str]:
    rows = _q(db, batting_teams=[spec["team"]], **T20I, group_by=["batter", "batting_position"],
              start_date=spec["last_game"] + timedelta(days=1))
    balls: Dict[str, int] = {}
    for r in rows:
        if r.get("batting_position") in POSITIONS:
            balls[r["batter"]] = balls.get(r["batter"], 0) + (r.get("balls") or 0)
    ranked = sorted((b for b, n in balls.items() if n >= PEER_MIN_BALLS and b != spec["player"]), key=lambda b: -balls[b])
    return ranked[:MAX_PEERS]


def peers_card(db, spec, field: List[str]) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    start = date.today() - timedelta(days=365)
    who = [p] + field
    split = _q(db, batters=who, **T20I_IPL, group_by=["batter", "bowl_kind"], start_date=start)
    tot = {r["batter"]: r for r in _q(db, batters=who, **T20I_IPL, group_by=["batter"], start_date=start)}
    cols = ["v pace", "v spin", "WPA"]
    table = {}
    for b in who:
        if b not in tot:
            continue
        table[b] = {"v pace": _per100([r for r in split if r["batter"] == b and r.get("bowl_kind") == "pace bowler"], MIN_YEAR_BALLS),
                    "v spin": _per100([r for r in split if r["batter"] == b and r.get("bowl_kind") == "spin bowler"], MIN_YEAR_BALLS),
                    "WPA": tot[b].get("wpa") or 0}
    if p not in table or len(table) < 4:
        return None
    order = sorted(table, key=lambda b: -table[b]["WPA"])
    payload = heat(table, cols, p, order)
    for r in payload["rows"]:
        r["short"] = _name(spec, r["name"])
    for m in payload["metrics"]:
        m["format"] = "signed2" if m["key"] == "WPA" else "signed0"
        m["label"] = {"v pace": "Impact /100 v pace", "v spin": "Impact /100 v spin", "WPA": "WPA (total)"}[m["key"]]
    allpos = [b for b in order if all((table[b][c] or 0) > 0 for c in cols)]
    rank = order.index(p) + 1
    if len(allpos) == 1:
        title = f"Over the last year, only {_name(spec, allpos[0])} is positive against pace, against spin and on WPA"
    elif allpos:
        title = f"Over the last year, {_names([_name(spec, b) for b in allpos])} are positive against pace, against spin and on WPA"
    else:
        title = f"Over the last year, nobody here is positive against pace, against spin and on WPA"
    help_ = f"{spec['display']} ranks {rank} of {len(order)} for WPA ({fmt(table[p]['WPA'], 'signed2')})"
    payload["method"] = (f"T20Is and IPL since {start:%-d %b %Y}. Impact per 100 balls by bowler type; – under "
                         f"{MIN_YEAR_BALLS} balls. Ring: best in the column.")
    return card("alternatives", "scorecard", title, payload,
                f"The batters India have used at 3 to 7 since {spec['display']}'s last T20I, with him", help_)


def event_card(db, spec) -> Optional[Dict[str, Any]]:
    ev, p = spec["event"], spec["player"]
    rows = _q(db, batting_teams=[spec["team"]], **T20I, group_by=["batter"], start_date=ev["start"], end_date=ev["end"],
              min_balls=EVENT_MIN_BALLS)
    rows = sorted(rows, key=lambda r: -(r.get("wpa") or 0))
    if not any(r["batter"] == p for r in rows) or len(rows) < 4:
        return None
    out = [{"name": _name(spec, r["batter"]), "value": r.get("wpa") or 0, "highlight": r["batter"] == p,
            "detail": f"{r['innings_count']} inns · {r['runs']} ({r['balls']})"} for r in rows]
    mine = next(r for r in rows if r["batter"] == p)
    inns = sorted(_q(db, batters=[p], batting_teams=[spec["team"]], **T20I, group_by=["match_date", "bowling_team"],
                     start_date=ev["start"], end_date=ev["end"]), key=lambda r: -(r.get("wpa") or 0))
    rank = [r["batter"] for r in rows].index(p) + 1
    title = (f"At the {ev['label']}, {spec['display']} ranked {rank} of {len(rows)} India batters for win probability added "
             f"({fmt(mine['wpa'], 'signed2')})")
    top = inns[0] if inns else None
    rest = sum(r.get("wpa") or 0 for r in inns[1:])
    help_ = (f"{fmt(top['wpa'], 'signed2')} of it in one innings, {top['runs']} ({top['balls']}) v {_team(spec, top['bowling_team'])}; "
             f"his other {len(inns) - 1} came to {fmt(rest, 'signed2')}") if top else ""
    payload = {"metric": {"label": "win probability added", "format": "signed2", "signed": True}, "rows": out, "label_width": 120,
               "subject_wpa": fmt(mine["wpa"], "signed2"), "top_wpa": fmt(top["wpa"], "signed2") if top else "–"}
    return card("event", "metric_bars", title, payload,
                f"India batters with {EVENT_MIN_BALLS}+ balls · {ev['start']:%-d %b} to {ev['end']:%-d %b %Y}", help_)


def both_ways(db, spec, cards: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """The case for and against, one line each from the cards' own numbers."""
    p, nm = spec["player"], spec["display"]
    lines = ["For"]
    if "hole" in cards:
        lines.append("· " + cards["hole"]["title"].replace(f"Since {nm}'s last T20I, ", "Since he left, "))
    if "arc" in cards:
        lines.append("· " + cards["arc"]["title"].split(". ")[0])
    lines.append("Against")
    yr = spec["years"][-1]
    ipl = [r for r in _q(db, batters=[p], **IPL, group_by=["year", "bowl_kind"], start_date=date(yr, 1, 1))
           if r.get("bowl_kind") == "pace bowler"]
    if ipl and sum(r.get("wickets") or 0 for r in ipl):
        b, w = sum(r["balls"] for r in ipl), sum(r["wickets"] for r in ipl)
        lines.append(f"· IPL {yr}: out every {b / w:.1f} balls against pace")
    if "event" in cards:
        e = cards["event"]
        lines.append(f"· {spec['event']['label']}: {e['payload']['subject_wpa']} win probability added, "
                     f"{e['payload']['top_wpa']} of it in one innings")
    if "alternatives" in cards:
        lines.append("· " + cards["alternatives"]["title"])
    return {"type": "text", "heading": "The case, both ways", "body": "\n".join(lines)}


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    field = peers(db, spec)
    hole, deep = hole_card(db, spec), pace_spin_card(db, spec)
    rest = [c for c in (arc_card(db, spec), peers_card(db, spec, field), event_card(db, spec)) if c]
    if not hole or not deep or len(rest) < 2:
        return None
    cards = [hole, deep, *rest]
    by_id = {c["id"]: c for c in cards}
    slides = ([{"type": "hook", "text": spec["hook"], "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [both_ways(db, spec, by_id),
                 {"type": "end", "heading": "Make your own case",
                  "body": "Impact and win probability for every batter, free: hindsightcricket.com"}])
    told = [c for c in cards if c is not deep]
    verdict = " ".join(f"{c['title']}." for c in told[:2])
    return {"slides": slides, "cards": cards, "title": spec["hook"], "verdict": verdict, "players": [spec["player"], *field],
            "deep_cut": {"probe": "pace-spin", "subject": spec["player"], "sentence": deep["title"], "by": "spotlight"}}
