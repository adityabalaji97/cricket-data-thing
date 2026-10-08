"""
A player spotlight: one post on one player when the news is about them (a recall, a comeback, a debut), from a spec.

    build(db, spec)  ->  {slides, title, verdict, players, fact} or None

Slides: hook; their arc (a measure by phase and year); then the same measure against their team's peers, year by year
(Impact and runs saved, powerplay and death); their record in the series' country by ground; what the series grounds do
for their kind of bowler with the new ball; end. "The deeper cut" goes in as slide 3 when the post is queued
(services/ig_backlog.add_deep_cut).

Everyone is compared on all their T20s (leagues=[] with include_international=False; with True it would be
internationals only): a recalled player has no internationals in the window. Every number comes from the query builder;
code writes every title.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from services.ig_posts.cards import card, fmt

MIN_CELL_BALLS = 30   # a bowler's phase in a year needs this many balls to get a number
PEER_MIN_BALLS = 120  # international balls in the window to count as one of the team's pacers
PEER_MIN_PER_INNINGS = 15  # balls an innings: a frontline bowler, not a batter who bowls two overs
MAX_ROWS = 9          # what the heat table fits
PHASES = [("powerplay", "Powerplay"), ("middle", "Middle"), ("death", "Death")]
ARC_PHASES = [("powerplay", "Powerplay"), ("death", "Death")]  # a pacer's middle overs are too few to read by year
#: Surnames shared by too many players to name someone by (two Kumars in one table): their first name instead.
COMMON_SURNAMES = {"Kumar", "Singh", "Yadav", "Sharma", "Khan", "Patel", "Ahmed", "Reddy", "Pandya", "Chahar", "Malik",
                   "Iyer", "Ali", "Hasan", "Rahman"}

SPECS: Dict[str, Dict[str, Any]] = {
    "bhuvi": {
        "player": "Bhuvneshwar Kumar", "role": "bowler", "bowl_kind": "pace bowler", "team": "India",
        "years": [2023, 2024, 2025, 2026], "arc_from": 2022, "country": "New Zealand", "fmt": "T20",
        "venues": [("Hagley Oval", ["Hagley Oval, Christchurch"]),
                   ("Wellington", ["Westpac Stadium, Wellington", "Sky Stadium, Wellington", "WestpacTrust Stadium, Wellington"]),
                   ("Eden Park", ["Eden Park, Auckland"]),
                   ("Seddon Park", ["Seddon Park, Hamilton"])],
        "venues_since": 2018,
        "hook": "Bhuvneshwar Kumar is back for India after four years. Is he better than the pacers who replaced him?",
        "kicker": "India v New Zealand T20Is",
        "sub": "Impact and runs saved, phase by phase, year by year",
        "tags": ["#INDvNZ", "#TeamIndia", "#Bhuvi"],
        "key": "spotlight-bhuvneshwar-kumar-2026-10",
    },
}


def short_name(name: str) -> str:
    parts = str(name).split()
    if len(parts) < 2:
        return name
    return parts[0] if parts[-1] in COMMON_SURNAMES else parts[-1]


def per_over(row: Dict[str, Any], measure: str) -> Optional[float]:
    """Impact or runs above average per over (bowling view: + is good for the bowler)."""
    if (row.get("balls") or 0) < MIN_CELL_BALLS:
        return None
    v = row.get("impact_per_100" if measure == "impact" else "raa_per_100")
    return None if v is None else 6 * v / 100


def _q(db, **args) -> List[Dict[str, Any]]:
    from services.query_builder_v2 import run_deliveries_query

    base = {"fmt": "T20", "gender": "male", "limit": 2000, "metrics_perspective": "bowling"}
    return run_deliveries_query(db, **{**base, **args}).get("data") or []


def all_t20s(**args) -> Dict[str, Any]:
    """Every men's T20 (leagues, internationals, domestic)."""
    return {"leagues": [], "include_international": False, **args}


def peers(db, spec: Dict[str, Any]) -> List[str]:
    """The team's bowlers of this kind in internationals across the years, most used first (part-timers out)."""
    years = spec["years"]
    rows = _q(db, group_by=["bowler"], bowling_teams=[spec["team"]], bowl_kind=[spec["bowl_kind"]],
              include_international=True, leagues=[], start_date=date(years[0], 1, 1), min_balls=PEER_MIN_BALLS)
    rows = [r for r in rows if (r.get("balls") or 0) >= PEER_MIN_PER_INNINGS * (r.get("innings_count") or 1)]
    rows.sort(key=lambda r: -(r.get("balls") or 0))
    return [r["bowler"] for r in rows if r["bowler"] != spec["player"]][: MAX_ROWS - 1]


def phase_years(db, bowlers: List[str], start: int) -> Dict[Tuple[str, int, str], Dict[str, Any]]:
    """(bowler, year, phase) -> row, every T20 since `start`."""
    rows = _q(db, **all_t20s(), bowlers=bowlers, group_by=["bowler", "year", "phase"], start_date=date(start, 1, 1))
    return {(r["bowler"], int(r["year"]), r["phase"]): r for r in rows}


def _pct(values: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
    """Percentile of each value within its column (0..100, higher is better); None stays None."""
    have = sorted(v for v in values.values() if v is not None)
    if len(have) < 2:
        return {k: (None if v is None else 50.0) for k, v in values.items()}
    return {k: (None if v is None else 100 * sum(1 for x in have if x < v) / (len(have) - 1)) for k, v in values.items()}


def heat(table: Dict[str, Dict[str, Optional[float]]], cols: List[str], subject: str, order: List[str]) -> Dict[str, Any]:
    """The scorecard visual's payload: rows x columns, each cell shaded by its percentile in its column."""
    pcts = {c: _pct({name: table[name].get(c) for name in order}) for c in cols}
    leaders = {c: max((n for n in order if table[n].get(c) is not None), key=lambda n: table[n][c], default=None) for c in cols}
    return {
        "metrics": [{"key": c, "label": c, "format": "signed1"} for c in cols],
        "rows": [{"name": n, "short": short_name(n), "values": {c: table[n].get(c) for c in cols},
                  "pct": {c: pcts[c][n] for c in cols}, "leader": [c for c in cols if leaders[c] == n],
                  "highlight": n == subject} for n in order],
    }


def arc_card(spec, data, measure: str = "impact") -> Optional[Dict[str, Any]]:
    """Their measure by phase (rows) and year (columns), from the last year before the recall."""
    p = spec["player"]
    years = [str(y) for y in range(spec["arc_from"], spec["years"][-1] + 1)]
    table = {label: {y: per_over(data[(p, int(y), key)], measure) if (p, int(y), key) in data else None for y in years}
             for key, label in ARC_PHASES}
    order = [label for _, label in ARC_PHASES]
    payload = heat(table, years, "", order)
    # One player across years: shade every cell against the whole table, and no "best that year" rings.
    flat = _pct({f"{r}|{y}": table[r][y] for r in order for y in years})
    for r in payload["rows"]:
        r["short"] = r["name"]
        r["leader"] = []
        r["pct"] = {y: flat[f"{r['name']}|{y}"] for y in years}
    pp = table["Powerplay"]
    first, last = years[0], years[-1]
    who = short_name(p)
    earlier = [v for y, v in pp.items() if y != last and v is not None]
    if pp.get(last) is not None and earlier and pp[last] > max(earlier):
        title = f"{who}'s best new-ball year since {first}: {fmt(pp[last], 'signed1')} Impact an over in the {last} powerplay"
    elif pp.get(last) is not None and pp.get(first) is not None and pp[last] >= pp[first] * 0.6 and pp[last] > 0:
        title = f"{who} is back near his best with the new ball: {fmt(pp[last], 'signed1')} an over in {last}"
    elif pp.get(last) is not None:
        title = f"{who} in the powerplay: {fmt(pp[last], 'signed1')} an over in {last}"
    else:
        return None
    payload["method"] = ("Impact per over: runs taken off the batting side's projected total, wickets included "
                         "(+ is good for the bowler). Every T20 he played; – under 30 balls. Brighter is better.")
    return card("arc", "scorecard", title, payload, f"{p} · all T20s {first}-{last}",
                "His Impact per over, by phase and year")


def peer_card(spec, data, bowlers: List[str], phase: str, measure: str) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    cols = [str(y) for y in spec["years"]]
    table = {b: {y: per_over(data[(b, int(y), phase)], measure) if (b, int(y), phase) in data else None for y in cols}
             for b in bowlers}
    order = [b for b in bowlers if any(v is not None for v in table[b].values())]
    if p not in order or len(order) < 4:
        return None
    payload = heat(table, cols, p, order)
    last = cols[-1]
    ranked = sorted((b for b in order if table[b].get(last) is not None), key=lambda b: -table[b][last])
    phase_word = dict(PHASES)[phase].lower()
    what = "Impact" if measure == "impact" else "runs saved"
    unit = "per over"
    if p in ranked:
        rank = ranked.index(p) + 1
        ahead = [short_name(b) for b in ranked[: rank - 1]]
        if rank == 1:
            title = f"In {last}, no India pacer beat {short_name(p)}'s {phase_word} {what}: {fmt(table[p][last], 'signed1')} {unit}"
        elif rank <= 3:
            title = (f"In {last}, only {' and '.join(ahead)} beat {short_name(p)}'s {phase_word} {what} "
                     f"({fmt(table[p][last], 'signed1')} {unit})")
        else:
            title = f"In {last}, {short_name(p)} ranked {rank} of {len(ranked)} India pacers for {phase_word} {what}"
    else:
        title = f"{dict(PHASES)[phase]} {what} by year: {short_name(p)} against India's pacers"
    help_ = ("Impact per over (wickets included)" if measure == "impact" else "Runs saved per over against an average bowler") \
        + f", {phase_word}; brighter is better"
    payload["method"] = (f"Every T20 each bowler played (IPL, internationals, domestic); – under {MIN_CELL_BALLS} balls "
                         f"in the {phase_word} that year. Shade: rank within the year. Ring: best that year.")
    return card(f"peers-{phase}-{measure}", "scorecard", title, payload,
                f"India's pacers in T20Is since {cols[0]}, with {short_name(p)} · all T20s", help_)


def nz_record_card(db, spec) -> Optional[Dict[str, Any]]:
    p, country = spec["player"], spec["country"]
    rows = _q(db, group_by=["country", "venue", "year"], bowlers=[p], include_international=False, leagues=[])
    mine = [r for r in rows if r.get("country") == country and (r.get("balls") or 0)]
    if not mine:
        return None
    series = {v for _, names in spec["venues"] for v in names}
    label = {v: lab for lab, names in spec["venues"] for v in names}

    def figures(r):
        overs = f"{r['balls'] // 6}.{r['balls'] % 6}" if r["balls"] % 6 else str(r["balls"] // 6)
        return f"{r['wickets']}/{r['runs']} in {overs} overs ({r['year']})"
    out = [{"name": label.get(r["venue"], r["venue"].split(",")[0]), "value": 6 * r["runs"] / r["balls"],
            "detail": figures(r), "highlight": r["venue"] in series} for r in sorted(mine, key=lambda r: (r["venue"] not in series, r["year"]))]
    balls = sum(r["balls"] for r in mine)
    econ = 6 * sum(r["runs"] for r in mine) / balls
    wkts = sum(r["wickets"] for r in mine)
    played = {label[r["venue"]] for r in mine if r["venue"] in series}
    never = [lab for lab, _ in spec["venues"] if lab not in played]
    title = (f"{short_name(p)} has bowled {balls} balls of T20 cricket in {country}: {wkts} wickets at {econ:.1f} an over")
    payload = {"metric": {"label": "runs an over", "format": "dec1", "signed": False}, "rows": out[:7]}
    out_card = card("nz-record", "metric_bars", title, payload,
                    f"{p} · T20s in {country}" + (f" · never bowled at {', '.join(never)}" if never else ""),
                    "Economy by ground; lime: grounds in this series")
    out_card["small_sample"] = True
    return out_card


def grounds_card(db, spec) -> Optional[Dict[str, Any]]:
    """New-ball pace (powerplay) at each series ground against every men's T20 since `venues_since`."""
    since = date(spec["venues_since"], 1, 1)
    common = all_t20s(bowl_kind=[spec["bowl_kind"]], over_max=5, start_date=since, group_by=["innings"])

    def agg(rows):
        balls = sum(r.get("balls") or 0 for r in rows)
        runs = sum(r.get("runs") or 0 for r in rows)
        wkts = sum(r.get("wickets") or 0 for r in rows)
        return balls, runs, wkts
    fb, fr, fw = agg(_q(db, **common))
    if not fb:
        return None
    field_econ = 6 * fr / fb
    rows, notes = [], []
    for lab, names in spec["venues"]:
        b = r = w = 0
        for v in names:
            vb, vr, vw = agg(_q(db, **common, venue=v))
            b, r, w = b + vb, r + vr, w + vw
        if b < 120:
            continue
        rows.append({"label": lab, "subject": 6 * r / b, "field": field_econ, "highlight": False})
        notes.append((lab, 6 * r / b, b / w if w else None, b))
    if len(rows) < 2:
        return None
    best = min(notes, key=lambda n: n[1])
    for row in rows:
        row["highlight"] = row["label"] == best[0]
    title = (f"New-ball pace goes for {best[1]:.1f} an over at {best[0]}, {field_econ:.1f} across all T20s")
    bpw = ", ".join(f"{lab} {x:.0f}" for lab, _e, x, _b in notes if x)
    payload = {"metric": {"label": f"powerplay runs an over by pace bowlers · balls per wicket: {bpw}", "format": "dec1",
                          "signed": False},
               "series": ["This ground", "All men's T20s"], "rows": rows}
    return card("grounds", "deep_compare", title, payload,
                f"Pace bowlers, overs 1-6, every men's T20 since {spec['venues_since']} · {sum(n[3] for n in notes):,} balls at these grounds",
                f"The series grounds for {spec['bowl_kind'].replace(' bowler', '')} with the new ball")


ACCURACY_MIN_BALLS = 200  # tracked powerplay balls for a row (and 8 rows leave room for the definition line)


def accuracy_card(db, spec, bowlers: List[str]) -> Optional[Dict[str, Any]]:
    """The new ball, ball by ball: how often each pacer lands it on a good length, drops it short, and draws a false shot
    (a ball the batter didn't control), powerplays since the first year. Accuracy is a skill that holds from year to
    year; how many false shots become wickets mostly doesn't, so it isn't here."""
    from datetime import date as _date

    p = spec["player"]
    common = all_t20s(bowlers=bowlers, over_max=5, start_date=_date(spec["years"][0], 1, 1))
    lengths = _q(db, **common, group_by=["bowler", "length"])
    control = _q(db, **common, group_by=["bowler", "control"])
    table: Dict[str, Dict[str, Optional[float]]] = {}
    tracked: Dict[str, int] = {}
    for b in bowlers:
        lr = [r for r in lengths if r["bowler"] == b and r.get("length")]
        cr = [r for r in control if r["bowler"] == b and r.get("control") is not None]
        lt, ct = sum(r["balls"] for r in lr), sum(r["balls"] for r in cr)
        if lt < ACCURACY_MIN_BALLS or ct < ACCURACY_MIN_BALLS:
            continue
        tracked[b] = lt
        table[b] = {
            "Good length": 100 * sum(r["balls"] for r in lr if r["length"] == "GOOD_LENGTH") / lt,
            "Short": 100 * sum(r["balls"] for r in lr if r["length"] == "SHORT") / lt,
            "False shots": 100 * sum(r["balls"] for r in cr if r["control"] == 0) / ct,
        }
    if p not in table or len(table) < 4:
        return None
    order = sorted(table, key=lambda b: -table[b]["Good length"])
    cols = ["Good length", "Short", "False shots"]
    payload = heat(table, cols, p, order)
    # Short: fewer is better, so its shading and ring run the other way.
    flipped = _pct({b: -table[b]["Short"] for b in order})
    best_short = min(order, key=lambda b: table[b]["Short"])
    for r in payload["rows"]:
        r["pct"]["Short"] = flipped[r["name"]]
        r["leader"] = [c for c in r["leader"] if c != "Short"] + (["Short"] if r["name"] == best_short else [])
    for m in payload["metrics"]:
        m["format"] = "pct0"
    me = table[p]
    more_false = [short_name(b) for b in order if table[b]["False shots"] > me["False shots"] + 2]
    first = order[0] == p
    title = (f"{short_name(p)} lands {me['Good length']:.0f}% of his new balls on a good length"
             + (", more than any India pacer" if first else ""))
    named = more_false[:3]
    who = ", ".join(named[:-1]) + f" and {named[-1]}" if len(named) > 1 else "".join(named)
    help_ = (f"Accuracy, not menace: {who} draw{'s' if len(named) == 1 else ''} more false shots" if named
             else "Accuracy and menace: no India pacer draws more false shots")
    payload["method"] = "False shot: a ball the batter didn't control (a miss, an edge, a mis-hit). Ring: best."
    out = card("accuracy", "scorecard", title, payload,
               f"India's pacers, powerplays in every T20 since {spec['years'][0]} · {tracked[p]:,} of {short_name(p)}'s balls tracked",
               help_)
    out["kicker"] = "The deeper cut"
    return out


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    p = spec["player"]
    bowlers = [p] + peers(db, spec)
    data = phase_years(db, bowlers, min(spec["arc_from"], spec["years"][0]))
    deep = accuracy_card(db, spec, bowlers) if spec["role"] == "bowler" else None
    cards = [c for c in (
        arc_card(spec, data),
        deep,  # slide 3: the post's own deeper cut, so the generic one isn't added
        peer_card(spec, data, bowlers, "powerplay", "impact"),
        peer_card(spec, data, bowlers, "death", "impact"),
        peer_card(spec, data, bowlers, "powerplay", "raa"),
        peer_card(spec, data, bowlers, "death", "raa"),
        nz_record_card(db, spec),
        grounds_card(db, spec),
    ) if c]
    if len(cards) < 4:
        return None
    slides = ([{"type": "hook", "text": spec["hook"], "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [{"type": "end", "heading": "Every number, free",
                  "body": "Impact, runs saved and every phase of every bowler: hindsightcricket.com"}])
    told = [c for c in cards if c is not deep]  # the deeper cut has its own caption line
    verdict = told[0]["title"] + ". " + (told[1]["title"] + "." if len(told) > 1 else "")
    return {"slides": slides, "cards": cards, "title": spec["hook"], "verdict": verdict, "players": bowlers,
            "deep_cut": {"probe": "accuracy", "subject": p, "sentence": deep["title"], "by": "spotlight"} if deep else None}
