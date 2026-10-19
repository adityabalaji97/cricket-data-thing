"""
A squad review post for one team (services/squad_review.py), from a spec built off a league squads file
(data/squads/<league>_<season>.json). Descriptive: where the likely XI is strong or thin, never a ranking (the
squad total didn't order past tables; scripts/squad_backtest.py).

Slides: hook; the likely top seven's batting by phase; the deeper cut (the bowling plan by phase); the home ground
against the league's grounds and the XI's spin overs; strengths and gaps by phase; new and unproven; end.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.ig_posts.cards import card, fmt
from services.ig_posts.spotlight import heat, short_name

ROOT = Path(__file__).resolve().parents[2]
PHASE_LABEL = {"powerplay": "Powerplay", "middle": "Middle", "death": "Death"}
WORD = {"powerplay": "the powerplay", "middle": "the middle overs", "death": "the death"}
WHERE = {"powerplay": "in the powerplay", "middle": "in the middle overs", "death": "at the death"}


def poss(name: str) -> str:
    """Paarl Royals' / MI Cape Town's."""
    return name + ("'" if name.endswith("s") else "'s")


def spec_for(squads_file: str, team: str, key: str) -> Dict[str, Any]:
    doc = json.load(open(ROOT / squads_file))
    t = next(x for x in doc["teams"] if x["team"] == team)
    return {"type": "squad_review", "squads": squads_file, "team": team, "league": doc["league"], "season": doc["season"],
            "hook": f"{poss(team)} {doc['league']} squad: where it's strong, where it's thin",
            "kicker": f"{doc['league']} {doc['season']} squad reviews", "sub": "The likely XI, phase by phase, and the home ground",
            "short": t.get("short") or team, "key": key, "prompt": "Where is your team strongest?", "tags": [f"#{doc['league']}", "#" + team.replace(" ", "").replace("'", "")],
            "method": ("Values are Impact (runs added to the team's projected total) above the average ball, from every men's "
                       "T20 in the two years before; thin records are pulled toward below average.")}


def _name(n: str) -> str:
    return short_name(n)


def _scorecard(cid, title, help_, sample, table, cols, fmts, method, order, scale: Optional[float] = None):
    """scale: shade around zero (the average ball) instead of by rank in the column: brighter above average, darker
    below (at or below average is dark); +scale is the brightest. A squad's cells aren't a ranking of each other."""
    payload = heat(table, cols, "", order)
    for r in payload["rows"]:
        r["short"] = r["name"]
        r["leader"] = []
        if scale:
            r["pct"] = {c: (None if r["values"].get(c) is None else max(0.0, min(100.0, 100 * r["values"][c] / scale)))
                        for c in cols}  # at or below average: dark; brighter the further above
    for m in payload["metrics"]:
        m["format"] = fmts.get(m["key"], "signed1")
    payload["method"] = method
    return card(cid, "scorecard", title, payload, sample, help_)


def batting_card(spec, d) -> Optional[Dict[str, Any]]:
    top = d["players"][:7]
    table = {_name(p["name"]): {PHASE_LABEL[ph]: p["bat"][ph] for ph in PHASE_LABEL} for p in top}
    order = list(table)
    best_ph = max(d["phases"]["bat"], key=d["phases"]["bat"].get)
    lead = max(top, key=lambda p: p["bat"][best_ph])
    title = (f"{poss(spec['short'])} likely top seven bat best {WHERE[best_ph]}: {_name(lead['name'])} adds "
             f"{fmt(lead['bat'][best_ph], 'signed0')} per 100 balls there")
    thin = [_name(p["name"]) for p in top if p["bat_balls"] < 500]
    help_ = "Impact per 100 balls above the average ball" + (f" · under 500 balls: {', '.join(thin)}" if thin else "")
    return _scorecard("xi-batting", title, help_, f"{spec['team']} · likely top seven · every men's T20 in the last two years",
                      table, list(PHASE_LABEL.values()), {}, "Brighter: above the average ball; darker: below. Batting order "
                      "from where each usually bats.", order, scale=25)


def bowling_card(spec, d) -> Optional[Dict[str, Any]]:
    plan = d["overs"]
    by = {p["name"]: p for p in d["players"]}
    table, order = {}, []
    for name, overs in sorted(plan.items(), key=lambda kv: -sum(kv[1].values())):
        label = f"{_name(name)} ({sum(overs.values())})"
        order.append(label)
        table[label] = {PHASE_LABEL[ph]: (by[name]["bowl"] or {}).get(ph) if overs.get(ph) else None for ph in PHASE_LABEL}
    bowl = d["phases"]["bowl"]
    lo, hi = min(bowl, key=bowl.get), max(bowl, key=bowl.get)
    title = (f"{poss(spec['short'])} bowling plan is strongest {WHERE[hi]} ({fmt(bowl[hi], 'signed1')} runs a game) and "
             f"thinnest {WHERE[lo]} ({fmt(bowl[lo], 'signed1')})")
    out = _scorecard("bowling-plan", title, "Impact an over above the average ball, in the phases each bowls · (overs a game)",
                     f"{spec['team']} · the XI's 20 overs, shared as each bowler is used",
                     table, list(PHASE_LABEL.values()), {k: "signed2" for k in PHASE_LABEL.values()},
                     "Brighter: better than the average ball for the bowling side. – doesn't bowl in that phase.", order, scale=1.0)
    out["kicker"] = "The deeper cut"
    return out


def ground_card(spec, d, home: Dict[str, Any], league: Dict[str, Any], ground: str) -> Optional[Dict[str, Any]]:
    if not home["spin"]["econ"] or not league["spin"]["econ"]:
        return None
    table = {ground: {"Pace econ": home["pace"]["econ"], "Spin econ": home["spin"]["econ"], "Spin share": 100 * home["spin"]["share"]},
             "All grounds": {"Pace econ": league["pace"]["econ"], "Spin econ": league["spin"]["econ"],
                             "Spin share": 100 * league["spin"]["share"]}}
    spin_overs = d["kinds"]["spin"]["overs"]
    title = (f"Spin bowls {100 * home['spin']['share']:.0f}% of the balls at {ground} and goes for {home['spin']['econ']:.1f} "
             f"an over. {poss(spec['short'])} XI has {spin_overs} spin overs")
    out = _scorecard("ground", title, f"The likely XI: {d['kinds']['pace']['overs']} pace overs, {spin_overs} spin",
                     f"Every men's T20 since 2021 at {ground} and at the league's six grounds",
                     table, ["Pace econ", "Spin econ", "Spin share"], {"Pace econ": "dec2", "Spin econ": "dec2", "Spin share": "pct0"},
                     "Runs an over by pace and spin, and spin's share of the balls.", list(table))
    for r in out["payload"]["rows"]:  # two rows aren't a ranking: plain cells
        r["pct"] = {k: None for k in r["pct"]}
    return out


def phases_card(spec, d) -> Optional[Dict[str, Any]]:
    ph = d["phases"]
    table = {"Batting": {PHASE_LABEL[k]: ph["bat"][k] for k in PHASE_LABEL},
             "Bowling": {PHASE_LABEL[k]: ph["bowl"][k] for k in PHASE_LABEL}}
    cells = [(side, k, ph[s][k]) for side, s in (("batting", "bat"), ("bowling", "bowl")) for k in PHASE_LABEL]
    best, worst = max(cells, key=lambda c: c[2]), min(cells, key=lambda c: c[2])
    title = (f"Strongest: {best[0]} {WHERE[best[1]]} ({fmt(best[2], 'signed1')} runs a game). "
             f"Thinnest: {worst[0]} {WHERE[worst[1]]} ({fmt(worst[2], 'signed1')})")
    return _scorecard("phases", title, "Projected runs a game above the average ball, the likely XI",
                      f"{spec['team']} · every men's T20 in the last two years", table, list(PHASE_LABEL.values()), {},
                      "Batting: the top order's balls by phase. Bowling: the 20-over plan. Brighter: above average.", list(table), scale=5)


def new_slide(spec, d, bought: List[str], flags: Dict[str, List[str]]) -> Dict[str, Any]:
    by = {p["name"]: p for p in d["players"]}
    new_in = [f"{_name(n)} ({by[n]['role']})" for n in d["xi"] if n in bought]
    lines = ["New in the likely XI: " + (", ".join(new_in) if new_in else "none, it's last season's core"),
             "Unproven (under 150 balls of T20 in two years): " + (", ".join(_name(n) for n in d["unproven"]) or "none")]
    if flags:
        lines.append("Check: " + ", ".join(flags))
    return {"type": "text", "heading": "New and unproven", "body": "\n".join(lines)}


def build(db, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from services import squad_review as S

    doc = json.load(open(ROOT / spec["squads"]))
    t = next(x for x in doc["teams"] if x["team"] == spec["team"])
    dn = lambda p: p.get("data_name") or p["name"]  # noqa: E731
    squad = [dn(p) for p in t["players"]]
    over = [dn(p) for p in t["players"] if p["overseas"]]
    bought = [dn(p) for p in t["players"] if p["how"] in ("auction", "wildcard")]
    as_of = date.fromisoformat(doc["as_of"])
    last = (date.fromisoformat(doc["last_season"][0]), date.fromisoformat(doc["last_season"][1]))
    values = S.player_values(db, squad, as_of)
    slots = S.slot_balls(db, doc["league"], as_of)
    d = S.describe(db, doc["league"], t["team"], squad, over, as_of, last, values, slots)
    home = S.ground_profile(db, t["home"], date(2021, 1, 1))
    league = S.ground_profile(db, [n for x in doc["teams"] for n in x["home"]], date(2021, 1, 1))
    flags = S.identity_flags(db, d["xi"], as_of, S.LEAGUES[doc["league"]]["home"], over)
    ground = t["home"][0].split(",")[0]
    bat, deep = batting_card(spec, d), bowling_card(spec, d)
    cards = [c for c in (bat, deep, ground_card(spec, d, home, league, ground), phases_card(spec, d)) if c]
    if not deep or cards[1] is not deep:
        return None
    slides = ([{"type": "hook", "text": spec["hook"], "kicker": spec["kicker"], "sub": spec.get("sub", "")}]
              + [{"type": "card", "card": c, "teams": None} for c in cards]
              + [new_slide(spec, d, bought, flags),
                 {"type": "end", "heading": "Every player, free", "body": "Impact by phase for every T20 player: hindsightcricket.com"}])
    told = [c for c in cards if c is not deep]
    return {"slides": slides, "cards": cards, "title": spec["hook"], "verdict": " ".join(f"{c['title']}." for c in told[:2]),
            "players": d["xi"][:2], "review": d,
            "deep_cut": {"probe": "squad-bowling", "subject": spec["team"], "sentence": deep["title"], "by": "spotlight"}}
