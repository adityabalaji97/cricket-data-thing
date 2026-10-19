"""
A series preview: what works at each of a series' grounds, and how each side's batters fare against the other's
attack. From a spec (services/ig_posts/spotlight.SPECS, type "series_preview").

Slides: hook; the grounds (games, first-innings average, chases won, run rate); the deeper cut (pace v spin at each
ground); the phases by ground; boundaries by ground; side A's batters against side B's bowling styles; side B's
batters against side A's; what suits each side; end.

Grounds are matched on every name the data has used for them (a stadium renamed by sponsors is one ground; a second
field at the same address, like Eden Park's Outer Oval, is not). Ground numbers cover every men's T20 there
(leagues, domestic and T20Is: leagues=[], include_international=False). Every number comes from the query builder and
code writes every title.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from services.ig_posts.cards import card, fmt
from services.ig_posts.spotlight import _pct, heat, short_name

THIN = 15                # a ground with fewer games than this is flagged (Wellington: 11 T20Is, no Super Smash)
MIN_BALLS = 60           # a batter's balls against a bowling style for a number
PACE_LEFT = ["LF", "LFM", "LM", "LMF"]
WRIST = ["LB", "LBG", "LB/LBG", "LWS"]
STYLES = {
    "pace": {"bowl_kind": ["pace bowler"]},
    "left-arm spin": {"bowl_style": ["SLA"]},
    "off-spin": {"bowl_style": ["OB"]},
    "wrist spin": {"bowl_style": WRIST},
    "left-arm pace": {"bowl_style": PACE_LEFT},
    "right-arm pace": {"bowl_style": ["RF", "RFM", "RM", "RMF"]},
}
ALL_T20 = {"leagues": [], "include_international": False}


def _q(db, **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "T20", "gender": "male", "limit": 2000, "metrics_perspective": "batting"}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


def _ground(db, spec, names: List[str], **args) -> List[Dict[str, Any]]:
    """Rows at one ground: the same query run on each of its names, put together."""
    out: List[Dict[str, Any]] = []
    for n in names:
        out += _q(db, venue=n, start_date=spec["since"], **ALL_T20, **args)
    return out


def _sum(rows, k) -> float:
    return sum(r.get(k) or 0 for r in rows)


def _label(g: Dict[str, Any], games: Dict[str, int]) -> str:
    return g["label"] + ("*" if games.get(g["label"], 0) < THIN else "")


def ground_stats(db, spec) -> Dict[str, Dict[str, Any]]:
    """{label: {games, first, chased, rr, phases{}, pace{}, spin{}, bound, sixes}} for every ground."""
    out: Dict[str, Dict[str, Any]] = {}
    for g in spec["grounds"]:
        inns = _ground(db, spec, g["names"], query_mode="team_innings", group_by=["innings"])
        one = [r for r in inns if str(r.get("innings")) == "1"]
        two = [r for r in inns if str(r.get("innings")) == "2"]
        games = int(_sum(one, "innings_count"))
        first = (sum((r.get("avg_total") or 0) * (r.get("innings_count") or 0) for r in one) / games) if games else None
        w, l = _sum(two, "wins"), _sum(two, "losses")
        phases = _ground(db, spec, g["names"], group_by=["phase"])
        kinds = _ground(db, spec, g["names"], group_by=["bowl_kind"], metrics_perspective="bowling")
        balls, runs = _sum(phases, "balls"), _sum(phases, "runs")
        ph = {}
        for key in ("powerplay", "middle", "death"):
            rs = [r for r in phases if r.get("phase") == key]
            b = _sum(rs, "balls")
            ph[key] = 6 * _sum(rs, "runs") / b if b else None
        kind = {}
        for key in ("pace bowler", "spin bowler"):
            rs = [r for r in kinds if r.get("bowl_kind") == key]
            b, wk = _sum(rs, "balls"), _sum(rs, "wickets")
            kind[key] = {"econ": 6 * _sum(rs, "runs") / b if b else None, "bpw": b / wk if wk else None, "balls": b,
                         "impact": (_sum(rs, "impact") / b * 6) if b else None}
        out[g["label"]] = {"games": games, "first": first, "chased": 100 * w / (w + l) if w + l else None,
                           "rr": 6 * runs / balls if balls else None, "phases": ph, "kind": kind,
                           "bound": 100 * _sum(phases, "boundaries") / balls if balls else None,
                           "sixes": 6 * _sum(phases, "sixes") / balls if balls else None,
                           "comps": sorted({r.get("competition") for r in _ground(db, spec, g["names"], group_by=["competition"])
                                            if r.get("competition")})}
    return out


def _table_card(cid, title, help_, sample, rows: Dict[str, Dict[str, Optional[float]]], cols, fmts, method,
                lower_better=()):
    order = list(rows)
    payload = heat(rows, cols, "", order)
    for r in payload["rows"]:
        r["short"] = r["name"]
        r["leader"] = []
    for m in payload["metrics"]:
        m["format"] = fmts[m["key"]]
    for c in cols:
        if c in lower_better:
            flipped = _pct({n: (-rows[n][c] if rows[n].get(c) is not None else None) for n in order})
            for r in payload["rows"]:
                r["pct"][c] = flipped[r["name"]]
        if fmts[c] == "int" and c == "Games":
            for r in payload["rows"]:
                r["pct"][c] = None
    payload["method"] = method
    return card(cid, "scorecard", title, payload, sample, help_)


def grounds_card(spec, st) -> Optional[Dict[str, Any]]:
    games = {k: v["games"] for k, v in st.items()}
    rows = {_label(g, games): {"Games": st[g["label"]]["games"], "1st-inns avg": st[g["label"]]["first"],
                               "Chases won": st[g["label"]]["chased"], "Run rate": st[g["label"]]["rr"]}
            for g in spec["grounds"]}
    have = {k: v for k, v in st.items() if v["first"] and v["games"] >= THIN}  # thin grounds sit out the title
    if len(have) < 3:
        return None
    lo, hi = min(have, key=lambda k: have[k]["first"]), max(have, key=lambda k: have[k]["first"])
    title = (f"{lo} is the lowest-scoring of the four: {have[lo]['first']:.0f} batting first. "
             f"{hi}: {have[hi]['first']:.0f}")
    chase = max(have, key=lambda k: have[k]["chased"] or 0)
    help_ = f"Chasing sides won {have[chase]['chased']:.0f}% at {chase}"
    return _table_card("grounds", title, help_, _scope(spec, st), rows, ["Games", "1st-inns avg", "Chases won", "Run rate"],
                       {"Games": "int", "1st-inns avg": "int", "Chases won": "pct0", "Run rate": "dec1"},
                       f"Every men's T20 at each ground since {spec['since'].year}. * fewer than {THIN} games.")


def pace_spin_card(spec, st) -> Optional[Dict[str, Any]]:
    games = {k: v["games"] for k, v in st.items()}
    rows = {}
    for g in spec["grounds"]:
        k = st[g["label"]]["kind"]
        rows[_label(g, games)] = {"Pace econ": k["pace bowler"]["econ"], "Spin econ": k["spin bowler"]["econ"],
                                  "Pace balls/wkt": k["pace bowler"]["bpw"], "Spin balls/wkt": k["spin bowler"]["bpw"]}
    spin = {g["label"]: st[g["label"]]["kind"]["spin bowler"]["econ"] for g in spec["grounds"]
            if st[g["label"]]["kind"]["spin bowler"]["econ"] and games[g["label"]] >= THIN}
    if len(spin) < 2:
        return None
    lo, hi = min(spin, key=spin.get), max(spin, key=spin.get)
    title = f"Spin goes for {spin[lo]:.1f} an over at {lo}, and {spin[hi]:.1f} at {hi}"
    share = {k: v["kind"]["pace bowler"]["balls"] / ((v["kind"]["pace bowler"]["balls"] + v["kind"]["spin bowler"]["balls"]) or 1)
             for k, v in st.items()}
    help_ = f"Pace bowls {100 * min(share.values()):.0f}-{100 * max(share.values()):.0f}% of the balls at these grounds"
    out = _table_card("pace-spin", title, help_, _scope(spec, st), rows,
                      ["Pace econ", "Spin econ", "Pace balls/wkt", "Spin balls/wkt"],
                      {"Pace econ": "dec1", "Spin econ": "dec1", "Pace balls/wkt": "int", "Spin balls/wkt": "int"},
                      "Runs an over and balls a wicket; brighter is better for the bowler. * thin sample.",
                      lower_better=("Pace econ", "Spin econ", "Pace balls/wkt", "Spin balls/wkt"))
    out["kicker"] = "The deeper cut"
    return out


def phases_card(spec, st) -> Optional[Dict[str, Any]]:
    games = {k: v["games"] for k, v in st.items()}
    rows = {_label(g, games): {"Powerplay": st[g["label"]]["phases"]["powerplay"], "Middle": st[g["label"]]["phases"]["middle"],
                               "Death": st[g["label"]]["phases"]["death"]} for g in spec["grounds"]}
    pp = {g["label"]: st[g["label"]]["phases"]["powerplay"] for g in spec["grounds"]
          if st[g["label"]]["phases"]["powerplay"] and games[g["label"]] >= THIN}
    if len(pp) < 2:
        return None
    hi, lo = max(pp, key=pp.get), min(pp, key=pp.get)
    title = f"The powerplay goes fastest at {hi}: {pp[hi]:.1f} an over, against {pp[lo]:.1f} at {lo}"
    return _table_card("phases", title, "Runs an over in each phase", _scope(spec, st), rows, ["Powerplay", "Middle", "Death"],
                       {"Powerplay": "dec1", "Middle": "dec1", "Death": "dec1"},
                       "Overs 1-6, 7-15, 16-20; brighter is more runs. * thin sample.")


def boundaries_card(spec, st) -> Optional[Dict[str, Any]]:
    games = {k: v["games"] for k, v in st.items()}
    rows = {_label(g, games): {"Boundary %": st[g["label"]]["bound"], "Sixes an over": st[g["label"]]["sixes"]}
            for g in spec["grounds"]}
    six = {g["label"]: st[g["label"]]["sixes"] for g in spec["grounds"] if st[g["label"]]["sixes"] and games[g["label"]] >= THIN}
    if len(six) < 2:
        return None
    hi, lo = max(six, key=six.get), min(six, key=six.get)
    title = f"Sixes come most often at {hi}: {six[hi]:.2f} an over, {six[lo]:.2f} at {lo}"
    return _table_card("boundaries", title, "How often the ball reaches the rope", _scope(spec, st), rows,
                       ["Boundary %", "Sixes an over"], {"Boundary %": "pct1", "Sixes an over": "dec2"},
                       "Share of balls hit for four or six, and sixes an over. * thin sample.")


def _scope(spec, st) -> str:
    comps = sorted({c for v in st.values() for c in v["comps"]})
    return f"Men's T20s at the series grounds since {spec['since'].year} · {', '.join(comps)}"


def matchup_card(db, spec, side: Dict[str, Any], other: str) -> Optional[Dict[str, Any]]:
    """A side's batters (impact per 100) against the other side's bowling styles, every T20 since `form_since`."""
    cols = side["against"]
    table: Dict[str, Dict[str, Optional[float]]] = {}
    for col in cols:
        for r in _q(db, batters=side["batters"], group_by=["batter"], start_date=spec["form_since"], **ALL_T20, **STYLES[col]):
            if (r.get("balls") or 0) >= MIN_BALLS:
                table.setdefault(r["batter"], {})[col] = r.get("impact_per_100")
    table = {b: {c: table[b].get(c) for c in cols} for b in side["batters"] if b in table}
    if len(table) < 4:
        return None
    order = sorted(table, key=lambda b: -(table[b].get(cols[0]) or -999))
    payload = heat(table, cols, "", order)
    for r in payload["rows"]:
        r["short"] = spec.get("names", {}).get(r["name"]) or short_name(r["name"])
    for m in payload["metrics"]:
        m["format"] = "signed0"
        m["label"] = f"v {m['key']}"
    first = cols[0]
    have = [b for b in order if table[b].get(first) is not None]
    best, worst = have[0], have[-1]
    nm = lambda b: spec.get("names", {}).get(b) or short_name(b)  # noqa: E731
    title = (f"{side['team']}'s batters against {first}: {nm(best)} adds {fmt(table[best][first], 'signed0')} per 100 balls, "
             f"{nm(worst)} {fmt(table[worst][first], 'signed0')}")
    help_ = f"What {other} bowls: {side['attack']}"
    payload["method"] = (f"Impact per 100 balls in every T20 since {spec['form_since']:%b %Y}; – under {MIN_BALLS} balls. "
                         "Ring: best in the column.")
    return card(f"matchups-{side['team'].lower().replace(' ', '-')}", "scorecard", title, payload,
                f"{side['team']}'s squad batters · every men's T20 since {spec['form_since']:%b %Y}", help_)


def both_ways(spec, cards: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    lines = []
    for c in (cards.get("pace-spin"), cards.get("grounds"), cards.get("phases")):
        if c:
            lines.append("· " + c["title"])
    for side in spec["sides"]:
        c = cards.get(f"matchups-{side['team'].lower().replace(' ', '-')}")
        if c:
            lines.append("· " + c["title"])
    return {"type": "text", "heading": "What to watch", "body": "\n".join(lines[:5])}


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    st = ground_stats(db, spec)
    deep = pace_spin_card(spec, st)
    a, b = spec["sides"]
    cards = [c for c in (grounds_card(spec, st), deep, phases_card(spec, st), boundaries_card(spec, st),
                         matchup_card(db, spec, a, b["team"]), matchup_card(db, spec, b, a["team"])) if c]
    if not deep or len(cards) < 4 or cards[1] is not deep:
        return None
    by_id = {c["id"]: c for c in cards}
    slides = ([{"type": "hook", "text": spec["hook"], "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [both_ways(spec, by_id),
                 {"type": "end", "heading": "Every ground, free",
                  "body": "Par scores, pace v spin and match-ups for every ground: hindsightcricket.com"}])
    told = [c for c in cards if c is not deep]
    verdict = " ".join(f"{c['title']}." for c in told[:2])
    return {"slides": slides, "cards": cards, "title": spec["hook"], "verdict": verdict,
            "players": a["batters"][:2] + b["batters"][:2],
            "deep_cut": {"probe": "pace-spin-ground", "subject": spec["kicker"], "sentence": deep["title"], "by": "spotlight"}}
