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


REGULAR_BALLS = 200   # balls at 3 to 7 since the last game to count as one of the regulars there


def win_rate(db, spec, **dates) -> Optional[Dict[str, int]]:
    rows = _q(db, query_mode="team_innings", batting_teams=[spec["team"]], **T20I, group_by=["match_outcome"], **dates)
    won = sum(r.get("wins") or 0 for r in rows)
    lost = sum(r.get("losses") or 0 for r in rows)
    return {"won": won, "lost": lost, "pct": round(100 * won / (won + lost))} if won + lost else None


def hole_card(db, spec) -> Optional[Dict[str, Any]]:
    """India's no. 3 to 7 in T20Is, from `with_from` to his last game and since, split three ways: him, the regulars there
    since (REGULAR_BALLS), everyone else. Shows whose numbers moved, not just that the total did."""
    p, nm, last = spec["player"], spec["display"], spec["last_game"]
    team = {"batting_teams": [spec["team"]], **T20I, "group_by": ["batter", "batting_position"]}
    before = [r for r in _q(db, **team, start_date=spec["with_from"], end_date=last) if r.get("batting_position") in POSITIONS]
    since = [r for r in _q(db, **team, start_date=last + timedelta(days=1)) if r.get("batting_position") in POSITIONS]
    if sum(r.get("balls") or 0 for r in since) < 300:
        return None
    balls: Dict[str, int] = {}
    for r in since:
        balls[r["batter"]] = balls.get(r["batter"], 0) + (r.get("balls") or 0)
    regulars = sorted((b for b, n in balls.items() if n >= REGULAR_BALLS), key=lambda b: -balls[b])
    if not regulars:
        return None
    games = lambda **d: max((r.get("innings_count") or 0) for r in _q(db, batting_teams=[spec["team"]], **T20I,  # noqa: E731
                                                                      group_by=["batting_position"], **d) if r.get("batting_position") == 1)
    gw, gs = games(start_date=spec["with_from"], end_date=last), games(start_date=last + timedelta(days=1))
    cols = ["Impact · before", "Impact · since", f"WPA · before ({gw} games)", f"WPA · since ({gs} games)"]
    groups = {nm: lambda b: b == p,
              _names([_name(spec, b) for b in regulars]): lambda b: b in regulars,
              "Everyone else": lambda b: b != p and b not in regulars,
              "All 3 to 7": lambda b: True}
    table = {}
    for label, keep in groups.items():
        b_rows = [r for r in before if keep(r["batter"])]
        s_rows = [r for r in since if keep(r["batter"])]
        table[label] = {cols[0]: _per100(b_rows, MIN_YEAR_BALLS), cols[1]: _per100(s_rows, MIN_YEAR_BALLS),
                        cols[2]: _wpa(b_rows) if b_rows else None, cols[3]: _wpa(s_rows) if s_rows else None}
    order = list(table)
    payload = heat(table, cols, nm, order)
    for r in payload["rows"]:
        r["short"] = r["name"] if r["name"] != order[1] else "The regulars"
    for m in payload["metrics"]:
        m["format"] = "signed1" if m["key"].startswith("Impact") else "signed2"
    _flat(payload, table, [cols[:2], cols[2:]])
    me, reg, rest = table[nm][cols[0]], table[order[1]][cols[1]], table["Everyone else"][cols[1]]
    if me is not None and reg is not None and rest is not None and reg > me and rest < reg:
        title = (f"India's regulars at 3 to 7 add {fmt(reg, 'signed1')} Impact per 100 balls, more than {nm} did "
                 f"({fmt(me, 'signed1')}). The drop is elsewhere")
    else:
        title = (f"Since {nm}'s last T20I, India's no. 3 to 7 add {fmt(table['All 3 to 7'][cols[1]], 'signed1')} Impact per "
                 f"100 balls, {fmt(table['All 3 to 7'][cols[0]], 'signed1')} before")
    wb, ws = win_rate(db, spec, start_date=spec["with_from"], end_date=last), win_rate(db, spec, start_date=last + timedelta(days=1))
    rest_balls = sum(r["balls"] for r in since if groups["Everyone else"](r["batter"]))
    help_ = (f"India won {wb['pct']}% of T20Is before his last game, {ws['pct']}% since. " if wb and ws else "") + \
        (f"Everyone else at 3 to 7: {fmt(rest, 'signed1')} per 100 over {rest_balls} balls" if rest is not None else "")
    payload["method"] = (f"Before: T20Is {spec['with_from']:%b %Y} to {last:%-d %b %Y}. Regulars: {REGULAR_BALLS}+ balls "
                         f"at 3 to 7 since ({_names(regulars)}). Impact per 100 balls; WPA in wins (+1.00 = one win).")
    return card("hole", "scorecard", title, payload,
                f"India's batters at 3 to 7 in T20Is · {sum(r['balls'] for r in since):,} balls since {nm}'s last game", help_)


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
    spin_ok = bool(spin) and min(spin) > 0
    ty = [y for y in years if table["T20Is v pace"][y] is not None]
    low = min(ty, key=lambda y: table["T20Is v pace"][y]) if ty else None
    wr = [r for r in t if str(r["year"]) == low and r.get("bowl_kind") == "pace bowler"]
    outs, balls = sum(r.get("wickets") or 0 for r in wr), sum(r.get("balls") or 0 for r in wr)
    if low and table["T20Is v pace"][low] < 0 and outs:
        title = (f"The {low} slump was against pace: {fmt(table['T20Is v pace'][low], 'signed0')} Impact per 100 balls, "
                 f"out {outs} times in {balls}" + (". Spin stayed positive" if spin_ok else ""))
    else:
        title = f"{nm}'s Impact per 100 balls against pace and spin, year by year"
    help_ = "Impact per 100 balls" + (f". Against pace in T20Is he swings from {fmt(max(pace), 'signed0')} to "
                                      f"{fmt(min(pace), 'signed0')}" if pace else "")
    payload["method"] = f"Impact per 100 balls, wickets included; – under {MIN_YEAR_BALLS} balls. Brighter is better."
    out = card("pace-spin", "scorecard", title, payload, f"{p} · T20Is for {spec['team']} and the IPL, by calendar year", help_)
    out["kicker"] = "The deeper cut"
    if spin_ok:
        out["line"] = f"In T20Is he adds Impact against spin every year"
    return out


def arc_card(db, spec) -> Optional[Dict[str, Any]]:
    """His T20I career so far, Impact an innings by year (the IPL alongside): the peak, the slump, where he left off."""
    first = spec.get("career_from", spec["years"][0])
    p, years = spec["player"], [str(y) for y in range(first, spec["years"][-1] + 1)]
    t = {str(r["year"]): r for r in _q(db, batters=[p], **T20I, batting_teams=[spec["team"]], group_by=["year"], start_date=date(first, 1, 1))}
    i = {str(r["year"]): r for r in _q(db, batters=[p], **IPL, group_by=["year"], start_date=date(first, 1, 1))}
    ipi = lambda r: (r["impact"] / r["innings_count"]) if r and r.get("innings_count") else None  # noqa: E731
    table = {"T20Is": {y: ipi(t.get(y)) for y in years}, "IPL": {y: ipi(i.get(y)) for y in years}}
    if sum(v is not None for v in table["T20Is"].values()) < 3:
        return None
    payload = heat(table, years, "", list(table))
    for r in payload["rows"]:
        r["short"] = r["name"]
    _flat(payload, table, [years])
    nm, last = spec["display"], years[-1]
    tr = {y: v for y, v in table["T20Is"].items() if v is not None}
    peak, slump, tl = max(tr, key=tr.get), min(tr, key=tr.get), tr.get(last)
    if slump > peak and tl is not None and slump != last and tr[slump] < 0 < tl:
        title = (f"{nm}'s T20I career: a peak in {peak} ({fmt(tr[peak], 'signed1')} Impact an innings), a slump in {slump} "
                 f"({fmt(tr[slump], 'signed1')}), back up in {last} ({fmt(tl, 'signed1')})")
    else:
        title = f"{nm}'s T20I career, Impact an innings by year: best {peak} ({fmt(tr[peak], 'signed1')})"
    since = next((y for y in reversed(years[:-1]) if tl is not None and table["T20Is"][y] is not None and table["T20Is"][y] >= tl), None)
    wpa = lambda d, y: fmt(d[y]["wpa"], "signed2") if d.get(y) else "–"  # noqa: E731
    help_ = "WPA by year · T20Is " + ", ".join(f"{y} {wpa(t, y)}" for y in years[-3:]) + " · IPL " + \
        ", ".join(f"{y} {wpa(i, y)}" for y in years[-3:])
    payload["method"] = (f"Impact an innings, wickets included. {last} T20Is run to his last game "
                         f"({spec['last_game']:%-d %b}). Brighter is better.")
    out = card("arc", "scorecard", title, payload, f"{p} · T20Is for {spec['team']} and the IPL", help_)
    if tl is not None and tl > 0:
        out["line"] = f"His {last} T20Is: {fmt(tl, 'signed1')} Impact an innings" + (f", his best since {since}" if since else "")
    il = table["IPL"].get(last)
    if il is not None and all(il <= v for v in table["IPL"].values() if v is not None):
        out["against"] = f"IPL {last}: {fmt(il, 'signed1')} Impact an innings, his worst season"
    return out


def rise_card(db, spec) -> Optional[Dict[str, Any]]:
    """The batter who took his place, over the same years: WPA in the T20Is and IPL seasons since his slump began."""
    p, r_name, slump = spec["player"], spec["rival"], spec["slump_year"]
    rows = _q(db, batters=[p, r_name], **T20I_IPL, group_by=["batter", "competition", "year"], start_date=date(slump, 1, 1))
    cols = []
    for y in range(slump, spec["years"][-1] + 1):
        cols += [f"T20Is {y}", f"IPL {y}"]
    get = lambda b, c: next((r for r in rows if r["batter"] == b and f"{'T20Is' if r['competition'] == 'T20I' else r['competition']} {r['year']}" == c), None)  # noqa: E731
    table = {b: {c: (get(b, c) or {}).get("wpa") if get(b, c) else None for c in cols} for b in (p, r_name)}
    cols = [c for c in cols if any(table[b][c] is not None for b in table)]
    table = {b: {c: table[b][c] for c in cols} for b in table}
    payload = heat(table, cols, p, [p, r_name])
    for r in payload["rows"]:
        r["short"] = _name(spec, r["name"])
    for m in payload["metrics"]:
        m["format"] = "signed2"
    leaders = {r["name"]: [c for c in r["leader"] if all(table[b][c] is not None for b in table)] for r in payload["rows"]}
    _flat(payload, table, [cols])  # one measure throughout: shade the whole table on one scale
    for r in payload["rows"]:  # a ring means best of the two: none where only one of them played
        r["leader"] = leaders[r["name"]]
    nm, rn = spec["display"], _name(spec, r_name)
    me_slump = table[p].get(f"T20Is {slump}")
    ipls = [c for c in cols if c.startswith("IPL") and table[r_name].get(c) is not None]
    if me_slump is None or not ipls:
        return None
    title = (f"While {nm}'s T20Is slumped in {slump} ({fmt(me_slump, 'signed2')} WPA), {rn} added "
             + " and ".join(f"{fmt(table[r_name][c], 'signed2')} in {c}" for c in ipls[:2]))
    tdates = sorted(r["match_date"] for r in _q(db, batters=[r_name], **T20I, batting_teams=[spec["team"]], group_by=["match_date"]))
    back = next((d for a, d in reversed(list(zip(tdates, tdates[1:])))  # his latest return after a year or more out
                 if (date.fromisoformat(str(d)) - date.fromisoformat(str(a))).days > 365), None)
    help_ = f"{rn} came back into India's T20I side on {date.fromisoformat(str(back)):%-d %B %Y}" if back else ""
    payload["method"] = "Win probability added, total for the season (+1.00 = one win). – didn't play. Brighter is better."
    return card("rise", "scorecard", title, payload, f"{p} and {r_name} · T20Is for {spec['team']} and the IPL", help_)


def role_card(db, spec) -> Optional[Dict[str, Any]]:
    """His slot (the position he batted most in `with_from`..last game) before, and the batters there since."""
    p, nm, last = spec["player"], spec["display"], spec["last_game"]
    team = {"batting_teams": [spec["team"]], **T20I, "group_by": ["batter", "batting_position"]}
    before = [r for r in _q(db, **team, start_date=spec["with_from"], end_date=last) if r["batter"] == p]
    if not before:
        return None
    slot = max(before, key=lambda r: r.get("innings_count") or 0)["batting_position"]
    since = [r for r in _q(db, **team, start_date=last + timedelta(days=1)) if r.get("batting_position") == slot]
    mine = [r for r in before if r["batting_position"] == slot]
    cols = ["Impact /100", "WPA", "Strike rate", "Innings"]

    def row(rs):
        b = sum(r["balls"] for r in rs)
        return {"Impact /100": _per100(rs), "WPA": _wpa(rs), "Strike rate": 100 * sum(r["runs"] for r in rs) / b if b else None,
                "Innings": sum(r.get("innings_count") or 0 for r in rs)}
    table = {f"{nm} (before)": row(mine)}
    main = [r for r in since if (r.get("balls") or 0) >= PEER_MIN_BALLS]
    for r in sorted(main, key=lambda r: -r["balls"]):
        table[f"{_name(spec, r['batter'])} (since)"] = row([r])
    table[f"All no. {slot}s since"] = row(since)
    if len(table) < 2:
        return None
    order = list(table)
    payload = heat(table, cols, order[0], order)
    for r in payload["rows"]:
        r["short"] = r["name"]
        r["leader"] = []
    fm = {"Impact /100": "signed1", "WPA": "signed2", "Strike rate": "int", "Innings": "int"}
    for m in payload["metrics"]:
        m["format"] = fm[m["key"]]
    for r in payload["rows"]:
        r["pct"]["Innings"] = None
    me = table[order[0]]["Impact /100"]
    if len(order) > 2:
        them, who = table[order[1]]["Impact /100"], order[1].replace(" (since)", "")
        verb = "matched" if abs(them - me) <= 2 else "beaten" if them > me else "fallen short of"
        title = (f"At no. {slot}, {nm}'s main spot, {who} has {verb} him: {fmt(them, 'signed1')} Impact per 100 balls since, "
                 f"{nm} {fmt(me, 'signed1')} there before")
    else:
        title = f"India's no. {slot}s since {nm}'s last game: {fmt(table[order[-1]]['Impact /100'], 'signed1')} Impact per 100 balls"
    payload["method"] = (f"Before: his T20Is at no. {slot}, {spec['with_from']:%b %Y} to {last:%-d %b %Y}. Since: every India "
                         f"no. {slot} after (named with {PEER_MIN_BALLS}+ balls).")
    return card("role", "scorecard", title, payload, f"India's no. {slot} in T20Is · {sum(r['balls'] for r in since):,} balls since",
                f"The role he'd come back to")


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
    lines = ["For"] + [f"· {c['line']}" for c in (cards.get("arc"), cards.get("pace-spin")) if c and c.get("line")]
    lines.append("Against")
    yr = spec["years"][-1]
    ipl = [r for r in _q(db, batters=[p], **IPL, group_by=["year", "bowl_kind"], start_date=date(yr, 1, 1))
           if r.get("bowl_kind") == "pace bowler"]
    if ipl and sum(r.get("wickets") or 0 for r in ipl):
        b, w = sum(r["balls"] for r in ipl), sum(r["wickets"] for r in ipl)
        lines.append(f"· IPL {yr}: {b / w:.1f} balls per wicket against pace")
    if "event" in cards:
        e = cards["event"]
        lines.append(f"· {spec['event']['label']}: {e['payload']['subject_wpa']} win probability added, "
                     f"{e['payload']['top_wpa']} of it in one innings")
    role = (cards.get("role") or {}).get("title", "")
    if " has matched him" in role or " has beaten him" in role:
        lines.append("· " + cards["role"]["title"].split(": ")[0].replace(f", {spec['display']}'s main spot", ""))
    elif "alternatives" in cards:
        lines.append("· " + cards["alternatives"]["title"])
    return {"type": "text", "heading": "The case, both ways", "body": "\n".join(lines)}


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    field = peers(db, spec)
    arc, deep = arc_card(db, spec), pace_spin_card(db, spec)
    if not arc or not deep:
        return None
    # The story: his career, the slump (slide 3, the deeper cut), the rival's rise, his old role now, the rest of the case.
    cards = [arc, deep] + [c for c in (rise_card(db, spec), role_card(db, spec), hole_card(db, spec),
                                       peers_card(db, spec, field), event_card(db, spec)) if c]
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
