"""
A bowler spotlight for one match: their record at the match's ground and how they line up against the opposition's
top order. For a recall or a return to a ground they know (Bhuvneshwar Kumar back for India at the Chinnaswamy, his
IPL home).

    build(db, spec)  ->  {slides, cards, title, verdict, players} or None

Cards: every spell at the ground since `since` (Impact, with figures); the same games' other pacers, and the same
comparison everywhere else; the team's new-ball pace in this series against the bowler's powerplays; the opposition's
top order (from this series' batting order) against new-ball pace; the bowler against each of them. Every number
comes from the query builder (all men's T20s unless said); code writes every title.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from services.ig_posts.cards import card
from services.ig_posts.spotlight import _pct, _q, all_t20s, heat, short_name

TOP_ORDER_MAX_POSITION = 5   # a batter who opened or batted 1-5 in this series counts as the top order
POWERPLAY_LAST_OVER = 5      # overs 1-6, 0-indexed
MIN_TOP_ORDER_BALLS = 40     # new balls from pacers for a top-order row
MIN_H2H_BALLS = 6            # balls from the bowler for a head-to-head row


def _sum(rows: List[Dict[str, Any]], key: str) -> float:
    return sum(r.get(key) or 0 for r in rows)


def _per_over(rows: List[Dict[str, Any]]) -> Optional[float]:
    """Impact per over (bowling view) over these rows; None without tracked balls."""
    mb = _sum(rows, "metric_balls")
    return 6 * _sum(rows, "impact") / mb if mb else None


def _economy(rows: List[Dict[str, Any]]) -> Optional[float]:
    b = _sum(rows, "balls")
    return 6 * _sum(rows, "runs") / b if b else None


def _overs(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}" if balls % 6 else str(balls // 6)


def _poss(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _date_label(d: str) -> str:
    return date.fromisoformat(str(d)[:10]).strftime("%-d %b %y")


def spells(db, spec) -> List[Dict[str, Any]]:
    return sorted(_q(db, **all_t20s(), bowlers=[spec["player"]], venue=spec["venue"], start_date=spec["since"],
                     group_by=["match_id", "match_date", "batting_team"]), key=lambda r: str(r["match_date"]))


def spells_card(spec, rows) -> Optional[Dict[str, Any]]:
    if len(rows) < 4:
        return None
    p = spec["player"]
    total = _sum(rows, "impact")
    wkts = int(_sum(rows, "wickets"))
    best = max(rows, key=lambda r: r.get("impact") or 0)
    # Figures on the name line, no detail line: ten spells fit the slide only one line each.
    out = [{"name": f"{_date_label(r['match_date'])} v {spec['short_names'].get(r['batting_team'], r['batting_team'])}"
                    f" · {int(r['wickets'])}/{int(r['runs'])}" + ("" if int(r["balls"]) == 24 else f" ({_overs(int(r['balls']))} ov)"),
            "value": r.get("impact") or 0, "highlight": r is best} for r in rows]
    title = (f"{short_name(p)} has {'added' if total >= 0 else 'cost'} {abs(total):.0f} runs of Impact in {len(rows)} games at the {spec['venue_short']} "
             f"since {spec['since'].year}, with {wkts} wickets")
    payload = {"metric": {"label": "Impact, runs (bowling)", "format": "signed1", "signed": True}, "rows": out,
               "label_width": 200}
    return card("venue-spells", "metric_bars", title, payload,
                f"{p} · every T20 at {spec['venue']} since {spec['since'].year}",
                f"Best: {int(best['wickets'])}/{int(best['runs'])} v {best['batting_team']}, {best.get('impact') or 0:+.1f}")


def venue_card(db, spec, rows) -> Optional[Dict[str, Any]]:
    """Impact an over: the bowler at the ground against the other pacers in the same games, and the same pair of
    numbers everywhere else since `since`."""
    p, since = spec["player"], spec["since"]
    match_ids = [str(r["match_id"]) for r in rows]
    others_here = _q(db, **all_t20s(), match_ids=match_ids, bowl_kind=[spec["bowl_kind"]], exclude_bowlers=[p],
                     group_by=["innings"])
    mine_all = _q(db, **all_t20s(), bowlers=[p], start_date=since, group_by=["venue"])
    mine_else = [r for r in mine_all if r.get("venue") != spec["venue"]]
    field_all = _q(db, **all_t20s(), bowl_kind=[spec["bowl_kind"]], exclude_bowlers=[p], start_date=since,
                   group_by=["innings"])
    here, field_here = _per_over(rows), _per_over(others_here)
    there = _per_over(mine_else)
    field_there = None
    if field_all:  # everywhere except the ground: all pacers less the other pacers in these games
        tot_i, tot_mb = _sum(field_all, "impact"), _sum(field_all, "metric_balls")
        here_i, here_mb = _sum(others_here, "impact"), _sum(others_here, "metric_balls")
        field_there = 6 * (tot_i - here_i) / (tot_mb - here_mb) if tot_mb > here_mb else None
    if None in (here, field_here, there, field_there):
        return None
    econ_here, econ_field = _economy(rows), _economy(others_here)
    payload = {"metric": {"label": "Impact an over (bowling)", "format": "signed2", "signed": True},
               "series": [short_name(p), "Other pacers"],
               "rows": [{"label": f"At the {spec['venue_short']}", "subject": here, "field": field_here, "highlight": True},
                        {"label": "Everywhere else", "subject": there, "field": field_there, "highlight": False}]}
    title = (f"Pacers go for {econ_field:.1f} an over at the {spec['venue_short']}. {short_name(p)} goes for "
             f"{econ_here:.1f}")
    return card("venue-vs-field", "deep_compare", title, payload,
                f"Same {len(rows)} games: {int(_sum(others_here, 'balls')):,} balls by other pacers · every men's T20 "
                f"since {since.year} for 'everywhere else'",
                f"Impact an over: {here:+.2f} for him there, {field_here:+.2f} for the rest")


def new_ball_card(db, spec) -> Optional[Dict[str, Any]]:
    """The team's pacers with the new ball in this series against the bowler's powerplays and all pacers'."""
    p, since = spec["player"], spec["since"]
    series = _q(db, include_international=True, leagues=[], bowling_teams=[spec["team"]],
                batting_teams=[spec["opponent"]], bowl_kind=[spec["bowl_kind"]], over_max=POWERPLAY_LAST_OVER,
                start_date=spec["series_start"], group_by=["innings"])
    mine = _q(db, **all_t20s(), bowlers=[p], over_max=POWERPLAY_LAST_OVER, start_date=since, group_by=["innings"])
    field = _q(db, **all_t20s(), bowl_kind=[spec["bowl_kind"]], over_max=POWERPLAY_LAST_OVER, start_date=since,
               group_by=["innings"])
    if not series or not mine or not field:
        return None
    s_econ, m_econ, f_econ = _economy(series), _economy(mine), _economy(field)

    def bpw(rows):
        w = _sum(rows, "wickets")
        return _sum(rows, "balls") / w if w else None
    rows = [{"label": f"{_poss(spec['team'])} pacers v {spec['opponent']}, this series", "subject": s_econ, "field": f_econ,
             "highlight": False},
            {"label": f"{short_name(p)}, every T20 since {since.year}", "subject": m_econ, "field": f_econ,
             "highlight": True}]
    payload = {"metric": {"label": "powerplay runs an over", "format": "dec1", "signed": False},
               "series": ["Runs an over", f"Every pacer, overs 1-6 since {since.year}"], "rows": rows}
    s_b, m_b = bpw(series), bpw(mine)
    title = (f"{_poss(spec['team'])} new-ball pace has gone for {s_econ:.1f} an over in this series. "
             f"{_poss(short_name(p))} powerplays since {since.year}: {m_econ:.1f}")
    help_ = (f"A wicket every {s_b:.0f} balls in this series, every {m_b:.0f} for {short_name(p)}"
             if s_b and m_b else "Overs 1-6")
    return card("new-ball", "deep_compare", title, payload,
                f"Overs 1-6 · {int(_sum(series, 'balls'))} balls this series, {int(_sum(mine, 'balls'))} of his", help_)


def top_order(db, spec) -> List[str]:
    rows = _q(db, include_international=True, leagues=[], batting_teams=[spec["opponent"]],
              bowling_teams=[spec["team"]], start_date=spec["series_start"], group_by=["batter", "batting_position"],
              metrics_perspective="batting")
    first: Dict[str, int] = {}
    for r in rows:
        pos = r.get("batting_position")
        if pos and pos <= TOP_ORDER_MAX_POSITION:
            first[r["batter"]] = min(first.get(r["batter"], 99), pos)
    return sorted(first, key=lambda b: (first[b], b))


def top_order_card(db, spec, batters: List[str]) -> Optional[Dict[str, Any]]:
    """The opposition's top order against new-ball pace since `since`: strike rate, balls a dismissal, false shots."""
    common = all_t20s(batters=batters, bowl_kind=[spec["bowl_kind"]], over_max=POWERPLAY_LAST_OVER,
                      start_date=spec["since"], metrics_perspective="batting")
    rows = {r["batter"]: r for r in _q(db, **common, group_by=["batter"]) if (r.get("balls") or 0) >= MIN_TOP_ORDER_BALLS}
    control = _q(db, **common, group_by=["batter", "control"])
    if len(rows) < 3:
        return None
    table: Dict[str, Dict[str, Optional[float]]] = {}
    for b, r in rows.items():
        cr = [c for c in control if c["batter"] == b and c.get("control") is not None]
        tracked = _sum(cr, "balls")
        table[b] = {"Strike rate": r.get("strike_rate"), "Balls an out": r.get("balls_per_dismissal"),
                    "False shots": (100 * _sum([c for c in cr if c["control"] == 0], "balls") / tracked) if tracked else None}
    order = sorted(table, key=lambda b: -rows[b]["balls"])
    cols = ["Strike rate", "Balls an out", "False shots"]
    payload = heat(table, cols, order[0], order)
    for m, f in zip(payload["metrics"], ["int", "int", "pct0"]):
        m["format"] = f
    # False shots: fewer is better for the batter, so the shade and ring run the other way.
    flipped = _pct({b: (-table[b]["False shots"] if table[b]["False shots"] is not None else None) for b in order})
    steadiest = min((b for b in order if table[b]["False shots"] is not None), key=lambda b: table[b]["False shots"])
    for r in payload["rows"]:
        r["pct"]["False shots"] = flipped[r["name"]]
        r["leader"] = [c for c in r["leader"] if c != "False shots"] + (["False shots"] if r["name"] == steadiest else [])
    payload["method"] = "False shot: a ball the batter didn't control (a miss, an edge, a mis-hit). Ring: best for the batter."
    lead = order[0]
    lr = rows[lead]
    title = (f"{short_name(lead)} has faced {int(lr['balls'])} new balls from pacers since {spec['since'].year} and "
             f"gets out once every {lr['balls_per_dismissal']:.0f}")
    loosest = max((b for b in order if table[b]["False shots"] is not None), key=lambda b: table[b]["False shots"])
    return card("top-order", "scorecard", title, payload,
                f"{_poss(spec['opponent'])} top order in this series · pace, overs 1-6, every T20 since {spec['since'].year}",
                f"{short_name(loosest)} plays the most false shots: {table[loosest]['False shots']:.0f}%")


def h2h_card(db, spec, batters: List[str]) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    rows = [r for r in _q(db, **all_t20s(), bowlers=[p], batters=batters, group_by=["batter"])
            if (r.get("balls") or 0) >= MIN_H2H_BALLS]
    if len(rows) < 2:
        return None
    rows.sort(key=lambda r: -r["balls"])

    def outs(n):
        return {0: "not out", 1: "out once", 2: "out twice"}.get(n, f"out {n} times")
    out = [{"name": short_name(r["batter"]), "value": r.get("impact") or 0,
            "detail": f"{int(r['runs'])} off {int(r['balls'])}, {outs(int(r['wickets']))}", "highlight": i == 0}
           for i, r in enumerate(rows)]
    top = rows[0]
    never = [short_name(b) for b in batters if b not in {r["batter"] for r in rows}]
    title = (f"{short_name(top['batter'])} has faced {short_name(p)} the most: {int(top['runs'])} off "
             f"{int(top['balls'])} balls, {outs(int(top['wickets']))}")
    payload = {"metric": {"label": f"{_poss(short_name(p))} Impact, runs (bowling)", "format": "signed1", "signed": True},
               "rows": out}
    c = card("h2h", "metric_bars", title, payload, f"{p} v {_poss(spec['opponent'])} top order · every T20",
             (f"Never bowled to {', '.join(never)}" if never else "Small samples: a few overs each"))
    c["small_sample"] = True
    return c


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    rows = spells(db, spec)
    batters = top_order(db, spec)
    cards = [c for c in (
        spells_card(spec, rows),
        venue_card(db, spec, rows),
        new_ball_card(db, spec),
        top_order_card(db, spec, batters) if batters else None,
        h2h_card(db, spec, batters) if batters else None,
    ) if c]
    if len(cards) < 4:
        return None
    slides = ([{"type": "hook", "text": spec["hook"], "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [{"type": "end", "heading": "Every number, free",
                  "body": "Impact, every spell and every matchup: hindsightcricket.com"}])
    verdict = cards[0]["title"] + ". " + cards[1]["title"] + "."
    return {"slides": slides, "cards": cards, "title": spec["hook"], "verdict": verdict, "players": [p] + batters}
