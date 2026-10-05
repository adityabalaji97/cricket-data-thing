"""
Record posts ("fastest to 1,000 IPL runs"): the race by balls and by innings, then what each got there with.

    1. race_lines by balls: cumulative runs (or wickets) against balls for the five fastest, the milestone dashed
    2. race_lines by innings: the same race counted in innings; the leader often changes, which is the talking point
    3. scorecard: balls and innings to the milestone, plus strike rate (or economy) and, in men's T20, RAA and WPA per
       100 balls over their career up to the milestone; a split verdict ("fewest balls: X; fewest innings: Y")

Who reached the milestone, and when, comes from services/idea_stats.race (the same counting as the record ideas, so
careers that start before the data are left out, and the sample line says so). The lines are each career's running
total at the end of every innings, from the same tables race() reads: delivery_details for balls, batting_stats /
bowling_stats for innings. Rates at the milestone come from the query builder with end_date = the milestone's date.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from services import idea_stats as S
from services.ig_posts.cards import card, fmt, short
from services.player_aliases import ALIAS_MAP_CTE

TOP = 5


def _qb_scope(scope: Dict[str, Any]) -> Dict[str, Any]:
    """idea_stats scope -> query-builder filters."""
    league = scope.get("league")
    if league == "T20I":
        return {"include_international": True}
    return {"leagues": [league]} if league else {}


def _series_balls(db: Session, spec: Dict[str, Any], scope: Dict[str, Any], names: List[str]) -> Dict[str, List[Tuple[int, int]]]:
    """Each name's running (balls, runs|wickets) at the end of every innings, from delivery_details (as race())."""
    batter = spec["subject"] == "batter"
    team_col = "dd.team_bat" if batter else "dd.team_bowl"
    where, params = S._where({**scope, "start": None, "end": None}, team_col, "dd.team_bowl" if batter else "dd.team_bat")
    name = "COALESCE(am.canonical_name, dd.bat)" if batter else "COALESCE(am.canonical_name, dd.bowl)"
    join = "LEFT JOIN alias_map am ON LOWER(dd.bat) = am.name_key" if batter else "LEFT JOIN alias_map am ON LOWER(dd.bowl) = am.name_key"
    amount = ("COALESCE(dd.batruns, 0)" if batter else
              "CASE WHEN LOWER(COALESCE(dd.out::text, '')) = 'true' AND LOWER(COALESCE(dd.dismissal, '')) = ANY(:wk) THEN 1 ELSE 0 END")
    ball = ("COALESCE(dd.ballfaced, CASE WHEN COALESCE(dd.wide, 0) = 0 THEN 1 ELSE 0 END)" if batter else
            "CASE WHEN COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END")
    rows = db.execute(text(f"""
        WITH {ALIAS_MAP_CTE},
        inns AS (
            SELECT {name} AS name, m.date, dd.p_match, dd.inns, SUM({amount}) AS amount, SUM({ball}) AS faced
            FROM delivery_details dd JOIN matches m ON m.id = dd.p_match {join}
            WHERE {where} AND {name} = ANY(:names)
            GROUP BY 1, 2, 3, 4
        )
        SELECT name, SUM(faced) OVER w AS x, SUM(amount) OVER w AS y
        FROM inns WINDOW w AS (PARTITION BY name ORDER BY date, p_match, inns ROWS UNBOUNDED PRECEDING)
        ORDER BY name, x
    """), {**params, "names": names, "wk": list(S.BOWLER_WICKETS)}).all()
    return _cut(rows, spec["target"])


def _series_innings(db: Session, spec: Dict[str, Any], scope: Dict[str, Any], names: List[str]) -> Dict[str, List[Tuple[int, int]]]:
    """Each name's running (innings, runs|wickets), from batting_stats / bowling_stats (as race())."""
    batter = spec["subject"] == "batter"
    team_col = "s.batting_team" if batter else "s.bowling_team"
    where, params = S._where({**scope, "start": None, "end": None}, team_col, S._opp(team_col))
    table, name_col, measure = ("batting_stats", "striker", "s.runs") if batter else ("bowling_stats", "bowler", "s.wickets")
    rows = db.execute(text(f"""
        WITH {ALIAS_MAP_CTE},
        inns AS (
            SELECT DISTINCT ON (COALESCE(am.canonical_name, s.{name_col}), s.match_id, s.innings)
                   COALESCE(am.canonical_name, s.{name_col}) AS name, m.date, s.match_id, s.innings, {measure} AS amount
            FROM {table} s JOIN matches m ON m.id = s.match_id
            LEFT JOIN alias_map am ON LOWER(s.{name_col}) = am.name_key
            WHERE {where} AND COALESCE(am.canonical_name, s.{name_col}) = ANY(:names)
            ORDER BY COALESCE(am.canonical_name, s.{name_col}), s.match_id, s.innings
        )
        SELECT name, ROW_NUMBER() OVER w AS x, SUM(amount) OVER w AS y
        FROM inns WINDOW w AS (PARTITION BY name ORDER BY date, match_id, innings)
        ORDER BY name, x
    """), {**params, "names": names}).all()
    return _cut(rows, spec["target"])


def _cut(rows, target: int) -> Dict[str, List[Tuple[int, int]]]:
    """Points from (0, 0) up to and including the innings that reached the target."""
    out: Dict[str, List[Tuple[int, int]]] = {}
    done = set()
    for name, x, y in rows:
        if name in done:
            continue
        out.setdefault(name, [(0, 0)]).append((int(x), int(y or 0)))
        if (y or 0) >= target:
            done.add(name)
    return out


def _race_card(db, spec, scope, unit: str, words: Dict[str, str]) -> Optional[Dict[str, Any]]:
    rows, _ = S.race(db, {**spec, "unit": unit, "span": "career"}, scope)
    # Balls come from ball-by-ball data, which can start later than the scorecards innings are counted from: each
    # race says whose careers it covers.
    caveat = S.debut_floor(db, scope, ball_by_ball=unit == "balls")[1].strip(" ()")
    top = rows[:TOP]
    if len(top) < 2:
        return None
    series_fn = _series_balls if unit == "balls" else _series_innings
    series = series_fn(db, spec, scope, [r["name"] for r in top])
    lead, second = top[0], top[1]
    gap = second["value"] - lead["value"]
    title = (f"{lead['name']} got to {words['what']} in {lead['value']:,} {unit}"
             + (f", {gap:,} fewer than {short(second['name'])}" if gap > 0 else f", level with {short(second['name'])}"))
    payload = {"unit": unit, "target": spec["target"], "measure": "runs" if spec["measure"] == "runs" else "wickets",
               "series": [{"name": r["name"], "points": series.get(r["name"], []), "reached_at": r["value"]} for r in top
                          if series.get(r["name"])]}
    return card(f"race-{unit}", "race_lines", title, payload,
                f"{len(rows)} reached {words['what']} · {caveat}", f"Running total, the {TOP} fastest by {unit}"), rows


def _at_milestone(db, spec, scope, names_dates: List[Tuple[str, date]]) -> Dict[str, Dict[str, Any]]:
    """Rates over each career up to the milestone date (query builder)."""
    from services.query_builder_v2 import run_deliveries_query

    batter = spec["subject"] == "batter"
    out = {}
    for name, when in names_dates:
        args = {"fmt": scope["fmt"], "gender": "male", "group_by": ["batter" if batter else "bowler"], "limit": 5,
                "end_date": when, **_qb_scope(scope), ("batters" if batter else "bowlers"): [name]}
        if not batter:
            args["metrics_perspective"] = "bowling"
        rows = run_deliveries_query(db, **args).get("data") or []
        if rows:
            r = rows[0]
            mb = r.get("metric_balls") or 0
            out[name] = {"sr": r.get("strike_rate"), "economy": round(r["strike_rate"] * 6 / 100, 2) if r.get("strike_rate") and not batter else None,
                         "raa": r.get("raa_per_100"), "wpa": round(r["wpa"] * 100 / mb, 3) if r.get("wpa") is not None and mb else None}
    return out


def build(db: Session, idea: str) -> Optional[Dict[str, Any]]:
    """A record post for a career race idea ("Fastest to 1000 IPL runs"), or None if it isn't one / lacks data."""
    spec = S.parse_race(idea)
    if not spec or S.span_of(spec) != "career" or spec["subject"] == "team":
        return None
    scope = S.parse_scope(idea, db, None)
    words = S.race_words({**spec, "unit": "balls"}, scope)
    caveat = S.debut_floor(db, scope, ball_by_ball=True)[1].strip(" ()")
    made = _race_card(db, spec, scope, "balls", words)
    if not made:
        return None
    balls_card, balls_rows = made
    cards = [balls_card]
    inns = _race_card(db, spec, scope, "innings", words)
    inns_rows = []
    if inns:
        cards.append(inns[0])
        inns_rows = inns[1]
    # The milestone table: the six fastest by balls (careers with ball-by-ball data, so every column is comparable),
    # with their innings count from the innings race.
    by_inn = {r["name"]: r["value"] for r in inns_rows}
    pool = balls_rows[:6]
    rates = _at_milestone(db, spec, scope, [(r["name"], r["date"]) for r in pool])
    batter = spec["subject"] == "batter"
    t20 = scope["fmt"] == "T20" and scope.get("league") != "Men's Hundred"
    metrics = [("balls", "Balls", False, "int"), ("innings", "Innings", False, "int"),
               ("sr" if batter else "economy", "SR" if batter else "Econ", batter, "dec1" if batter else "dec2")]
    if t20:
        metrics += [("raa", "RAA/100", True, "signed1"), ("wpa", "WPA/100", True, "signed2")]
    table = []
    for r in pool:
        vals = {"balls": r["value"], "innings": by_inn.get(r["name"])}
        vals.update({k: (rates.get(r["name"]) or {}).get(k) for k, *_ in metrics[2:]})
        table.append({"name": r["name"], "values": vals})
    for key, _, higher, _ in metrics:
        have = [t for t in table if t["values"].get(key) is not None]
        for t in have:
            v = t["values"][key]
            better = sum(1 for o in have if (o["values"][key] < v if higher else o["values"][key] > v))
            t.setdefault("pct", {})[key] = round(100 * better / max(1, len(have) - 1), 1)
        if have:
            best = (max if higher else min)(have, key=lambda t: t["values"][key])
            best.setdefault("leader", []).append(key)
    phrases = {"balls": "fewest balls", "innings": "fewest innings", "sr": "fastest scoring", "economy": "cheapest",
               "raa": "most runs above average", "wpa": "most win probability added"}
    leaders: Dict[str, List[str]] = {}
    for t in table:
        for k in t.get("leader", []):
            leaders.setdefault(t["name"], []).append(phrases[k])
    verdict = "; ".join(f"{short(n)}: {', '.join(v)}" for n, v in leaders.items()) + "."
    if inns_rows and inns_rows[0]["name"] not in {t["name"] for t in table}:
        # The innings race reaches back further than ball-by-ball data: its winner isn't in the table, so say so.
        first = inns_rows[0]
        verdict += (f" By innings, {first['name']} ({first['date'].year if hasattr(first.get('date'), 'year') else ''}) "
                    f"was quicker still: {first['value']}.").replace(" () ", " ")
    score = card("scorecard", "scorecard", f"How they got to {words['what']}", {
        "metrics": [{"key": k, "label": lbl, "format": f} for k, lbl, _, f in metrics],
        "rows": [{"name": t["name"], "short": short(t["name"]), "values": t["values"], "pct": t.get("pct", {}),
                  "leader": t.get("leader", [])} for t in table],
        "verdict": verdict,
        "method": "Rates are over each career up to the day of the milestone. Shade: rank among these players "
                  "(brighter is better). Ring: best of them.",
    }, f"The fastest to {words['what']} · {caveat}")
    cards.append(score)
    hook = f"Who is the fastest to {words['what']}?"
    return {"hook": hook, "kicker": S.scope_label(scope), "cards": cards, "verdict": verdict,
            "players": list(leaders), "title": balls_card["title"]}
