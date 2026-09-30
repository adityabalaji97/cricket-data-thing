"""
Records, firsts and career-bests for one match: "the 3rd-highest ODI score since 2015".

For a newly loaded match, each template ranks that match's innings or spells against every
comparable one in Hindsight's data (same format and gender; same competition for leagues) since
2015 and keeps the ones near the top. Every fact carries the numbers its sentence uses, the
comparison window and sample size, and the ranking rows for its chart, so a content pack can
show the proof and the title can be number-checked (services/content_rules.py).

Works from batting_stats / bowling_stats, so it covers every format and needs no ball-by-ball
metrics; Impact- and control-based angles come from the recap and the standout scanner.
"""
import math
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.competition_aliases import canonical_competition, variants_for
from services.match_recap import _poss
from services.player_aliases import ALIAS_MAP_CTE

SINCE = date(2015, 1, 1)
RANK_MAX = 5            # "5th-highest" is still a post; "9th-highest" is not
MIN_POPULATION = 200    # a record among 40 innings is not a record
CHART_ROWS = 8
QUOTA_OVERS = {"T20": 4, "ODI": 10}
MIN_SR_BALLS = {"T20": 20, "ODI": 50}
MIN_PRIOR = 10          # career-bests need this many earlier innings/spells to mean anything
CAREER_BEST_RUNS = {"T20": 70, "ODI": 100}
CAREER_BEST_WICKETS = 4


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _superlative(rank: int, word: str) -> str:
    """rank 1 -> "the highest", 3 -> "the 3rd-highest"."""
    return f"the {word}" if rank == 1 else f"the {ordinal(rank)}-{word}"


def _overs_text(overs: Any) -> str:
    """Stored overs are decimal (9.333 = 9.2 overs); show cricket notation."""
    o = float(overs or 0)
    whole, balls = int(o), round((o - int(o)) * 6)
    if balls == 6:
        whole, balls = whole + 1, 0
    return f"{whole}" if balls == 0 else f"{whole}.{balls}"


def _scope(match: Dict[str, Any]) -> Dict[str, Any]:
    """The comparison set: internationals by format, leagues by competition."""
    fmt = match.get("format") or "T20"
    competition = canonical_competition(match.get("competition"))
    international = match.get("match_type") == "international" or competition in ("ODI", "T20I")
    if international:
        label = "ODI" if fmt == "ODI" else "T20I"
        where, params = "m.format = :fmt AND m.match_type = 'international'", {}
    else:
        label = competition
        where, params = "m.competition = ANY(:comps)", {"comps": variants_for(competition)}
    return {"fmt": fmt, "label": label, "where": where, "params": params, "international": international}


def _opponent(match: Dict[str, Any], team: str) -> str:
    return match["team2"] if team == match["team1"] else match["team1"]


def _ranked(db: Session, match: Dict[str, Any], scope: Dict[str, Any], select: str, table: str,
            team_col: str, name_col: str, order: str, extra_where: str = "") -> List[Dict[str, Any]]:
    """Every row of the population ranked by `order`; returns the top CHART_ROWS plus this match's rows."""
    sql = f"""
        WITH {ALIAS_MAP_CTE},
        pop AS (
            SELECT s.match_id, COALESCE(am.canonical_name, s.{name_col}) AS name, s.{team_col} AS team,
                   m.date, m.team1, m.team2, {select},
                   RANK() OVER (ORDER BY {order}) AS rk,
                   COUNT(*) OVER () AS n,
                   MIN(m.date) OVER () AS first_date
            FROM {table} s
            JOIN matches m ON m.id = s.match_id
            LEFT JOIN alias_map am ON LOWER(s.{name_col}) = am.name_key
            WHERE {scope['where']} AND m.gender = :gender AND m.date >= :since AND m.date <= :upto {extra_where}
        )
        SELECT * FROM pop WHERE rk <= :top OR match_id = :mid ORDER BY rk, date
    """
    params = {**scope["params"], "fmt": scope["fmt"], "gender": match.get("gender") or "male", "since": SINCE,
              "upto": match["date"], "top": CHART_ROWS, "mid": str(match["id"])}
    return [dict(r) for r in db.execute(text(sql), params).mappings()]


def _chart(rows: List[Dict[str, Any]], match: Dict[str, Any], hit: Dict[str, Any], display, metric: str) -> List[Dict[str, Any]]:
    """Top rows for the chart, with this match's entry swapped in at its rank if it is not there."""
    top = [r for r in rows if r["rk"] <= CHART_ROWS][:CHART_ROWS]
    if not any(r["match_id"] == hit["match_id"] and r["name"] == hit["name"] for r in top):
        top = top[:CHART_ROWS - 1] + [hit]
    out = []
    for r in top:
        # Name and year only: long franchise names would wrap every row on a phone-sized image.
        label = f"{r['name']}, {r['date'].year}"
        out.append({"rank": int(r["rk"]), "label": label, metric: float(r[metric]) if r[metric] is not None else None,
                    "display": display(r), "highlight": r["match_id"] == hit["match_id"] and r["name"] == hit["name"]})
    return out


def _rank_facts(db, match, scope, template: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = _ranked(db, match, scope, template["select"], template["table"], template["team_col"],
                   template["name_col"], template["order"], template.get("where", ""))
    if not rows or rows[0]["n"] < MIN_POPULATION:
        return []
    facts = []
    for hit in (r for r in rows if r["match_id"] == str(match["id"]) and r["rk"] <= RANK_MAX):
        rank, n = int(hit["rk"]), int(hit["n"])
        tied = sum(1 for r in rows if r["rk"] == hit["rk"]) > 1
        since_year = max(SINCE.year, hit["first_date"].year)
        numbers = template["numbers"](hit)
        sup = ("joint " if tied else "") + _superlative(rank, template["word"])
        title = template["title"].format(name=hit["name"], poss=_poss(hit["name"]), opp=_opponent(match, hit["team"]), sup=sup,
                                         comp=scope["label"], since=since_year, n=n, **numbers)
        facts.append({
            "kind": template["kind"], "team": hit["team"], "subject": hit["name"], "title": title,
            "rank": rank, "n": n, "since_year": since_year, "numbers": numbers,
            "weight": (RANK_MAX + 1 - rank) * math.log10(n),
            "method": template["method"].format(comp=scope["label"], since=since_year, n=n),
            "chart": {
                "metric": template["metric"], "group": template["group"],
                "rows": _chart(rows, match, hit, template["display"], template["metric"]),
            },
        })
    return facts


def _templates(fmt: str) -> List[Dict[str, Any]]:
    quota, min_balls = QUOTA_OVERS.get(fmt, 4), MIN_SR_BALLS.get(fmt, 20)
    bat = {"table": "batting_stats", "team_col": "batting_team", "name_col": "striker", "group": "innings",
           "display": lambda r: f"{r['runs']} ({r['balls']})"}
    bowl = {"table": "bowling_stats", "team_col": "bowling_team", "name_col": "bowler", "group": "spells"}
    return [
        {**bat, "kind": "bat_runs", "metric": "runs", "word": "highest",
         "select": "s.runs, s.balls_faced AS balls", "order": "s.runs DESC", "where": "AND s.balls_faced > 0",
         "numbers": lambda r: {"runs": r["runs"], "balls": r["balls"]},
         "title": "{poss} {runs} off {balls} v {opp} is {sup} {comp} score since {since}",
         "method": "Ranked against all {n:,} {comp} innings in Hindsight's data since {since}."},
        {**bat, "kind": "bat_sr", "metric": "strike_rate", "word": "fastest",
         "select": "s.runs, s.balls_faced AS balls, s.runs * 100.0 / NULLIF(s.balls_faced, 0) AS strike_rate",
         "order": "s.runs * 100.0 / NULLIF(s.balls_faced, 0) DESC", "where": f"AND s.balls_faced >= {min_balls}",
         "numbers": lambda r: {"runs": r["runs"], "balls": r["balls"], "sr": round(float(r["strike_rate"]), 1)},
         "title": "{poss} {runs} off {balls} v {opp} (strike rate {sr}) is {sup} {comp} innings of "
                  + f"{min_balls}+ balls since {{since}}",
         "method": f"Strike rate ranked against all {{n:,}} {{comp}} innings of {min_balls}+ balls in Hindsight's data since {{since}}."},
        {**bowl, "kind": "bowl_figures", "metric": "wickets", "word": "best",
         "select": "s.wickets, s.runs_conceded AS runs, s.overs",
         "order": "s.wickets DESC, s.runs_conceded ASC", "where": "AND s.wickets >= 3",
         "display": lambda r: f"{r['wickets']}/{r['runs']}",
         "numbers": lambda r: {"wickets": r["wickets"], "runs": r["runs"], "overs": _overs_text(r["overs"])},
         "title": "{poss} {wickets}/{runs} in {overs} overs v {opp} are {sup} {comp} figures since {since}",
         "method": "Figures (wickets, then runs) ranked against all {n:,} {comp} spells of 3+ wickets in Hindsight's data since {since}."},
        {**bowl, "kind": "bowl_economy", "metric": "economy", "word": "most economical",
         "select": "s.wickets, s.runs_conceded AS runs, s.overs, s.runs_conceded / NULLIF(s.overs, 0) AS economy",
         "order": "s.runs_conceded / NULLIF(s.overs, 0) ASC", "where": f"AND s.overs >= {quota}",
         "display": lambda r: f"{r['wickets']}/{r['runs']} ({_overs_text(r['overs'])})",
         "numbers": lambda r: {"wickets": r["wickets"], "runs": r["runs"], "overs": _overs_text(r["overs"]),
                               "econ": round(float(r["economy"]), 2)},
         "title": "{name} conceded {runs} in {overs} overs v {opp} (economy {econ}), {sup} full {comp} spell since {since}",
         "method": f"Economy ranked against all {{n:,}} {{comp}} spells of {quota} overs in Hindsight's data since {{since}}."},
    ]


def _career_bests(db: Session, match: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A batter's new best score (50+) or a bowler's new best figures (3+ wickets) in this scope."""
    sql = f"""
        WITH {ALIAS_MAP_CTE},
        rows_ AS (
            SELECT s.match_id, COALESCE(am.canonical_name, s.{{name}}) AS name, s.{{team}} AS team, m.date, {{cols}}
            FROM {{table}} s JOIN matches m ON m.id = s.match_id
            LEFT JOIN alias_map am ON LOWER(s.{{name}}) = am.name_key
            WHERE {scope['where']} AND m.gender = :gender AND m.date >= :since AND m.date <= :upto
        ),
        this AS (SELECT * FROM rows_ WHERE match_id = :mid AND {{qualifies}})
        SELECT t.*, p.prev_n, p.prev_first, b.*
        FROM this t
        JOIN LATERAL (SELECT COUNT(*) AS prev_n, MIN(date) AS prev_first FROM rows_ r
                      WHERE r.name = t.name AND r.match_id <> t.match_id AND r.date <= t.date) p ON TRUE
        JOIN LATERAL (SELECT {{prev_cols}} FROM rows_ r
                      WHERE r.name = t.name AND r.match_id <> t.match_id AND r.date <= t.date
                      ORDER BY {{order}} LIMIT 1) b ON TRUE
    """
    params = {**scope["params"], "fmt": scope["fmt"], "gender": match.get("gender") or "male", "since": SINCE,
              "upto": match["date"], "mid": str(match["id"])}
    facts = []
    bat = sql.format(name="striker", team="batting_team", table="batting_stats", cols="s.runs, s.balls_faced AS balls",
                     qualifies=f"runs >= {CAREER_BEST_RUNS.get(scope['fmt'], 70)}", prev_cols="r.runs AS prev_runs, r.date AS prev_date", order="r.runs DESC")
    for r in db.execute(text(bat), params).mappings():
        if r["prev_n"] < MIN_PRIOR or r["runs"] <= r["prev_runs"]:
            continue
        career = r["prev_first"] and r["prev_first"].year > SINCE.year  # debut inside our window
        label = f"new {scope['label']} career-best" if career else f"best {scope['label']} score since {SINCE.year}"
        numbers = {"runs": r["runs"], "balls": r["balls"], "prev": r["prev_runs"], "prev_year": r["prev_date"].year}
        facts.append({
            "kind": "career_best_bat", "team": r["team"], "subject": r["name"], "numbers": numbers,
            "title": f"{_poss(r['name'])} {r['runs']} off {r['balls']} v {_opponent(match, r['team'])} is a {label}, "
                     f"passing {r['prev_runs']} ({r['prev_date'].year})",
            "weight": 2 + r["runs"] / 50, "since_year": SINCE.year, "n": int(r["prev_n"]) + 1,
            "method": f"Compared with {r['prev_n']} earlier {scope['label']} innings by {r['name']} in Hindsight's data since {SINCE.year}.",
        })
    bowl = sql.format(name="bowler", team="bowling_team", table="bowling_stats",
                      cols="s.wickets, s.runs_conceded AS runs, s.overs", qualifies=f"wickets >= {CAREER_BEST_WICKETS}",
                      prev_cols="r.wickets AS prev_w, r.runs AS prev_r, r.date AS prev_date",
                      order="r.wickets DESC, r.runs ASC")
    for r in db.execute(text(bowl), params).mappings():
        if r["prev_n"] < MIN_PRIOR or (r["wickets"], -r["runs"]) <= (r["prev_w"], -r["prev_r"]):
            continue
        career = r["prev_first"] and r["prev_first"].year > SINCE.year
        label = f"new {scope['label']} career-best" if career else f"best {scope['label']} figures since {SINCE.year}"
        numbers = {"wickets": r["wickets"], "runs": r["runs"], "prev_w": r["prev_w"], "prev_r": r["prev_r"],
                   "prev_year": r["prev_date"].year}
        facts.append({
            "kind": "career_best_bowl", "team": r["team"], "subject": r["name"], "numbers": numbers,
            "title": f"{_poss(r['name'])} {r['wickets']}/{r['runs']} v {_opponent(match, r['team'])} "
                     f"{'is a' if career else 'are the'} {label}, passing {r['prev_w']}/{r['prev_r']} ({r['prev_date'].year})",
            "weight": 2 + r["wickets"], "since_year": SINCE.year, "n": int(r["prev_n"]) + 1,
            "method": f"Compared with {r['prev_n']} earlier {scope['label']} spells by {r['name']} in Hindsight's data since {SINCE.year}.",
        })
    return facts


def _player_chart(db: Session, match: Dict[str, Any], scope: Dict[str, Any], fact: Dict[str, Any]) -> Dict[str, Any]:
    """The player's own best innings (or spells) in this scope, this one highlighted."""
    bat = fact["kind"] == "career_best_bat"
    table, name_col, team_col = ("batting_stats", "striker", "batting_team") if bat else ("bowling_stats", "bowler", "bowling_team")
    cols = "s.runs, s.balls_faced AS balls" if bat else "s.wickets, s.runs_conceded AS runs"
    order = "s.runs DESC" if bat else "s.wickets DESC, s.runs_conceded ASC"
    rows = db.execute(text(f"""
        WITH {ALIAS_MAP_CTE}
        SELECT s.match_id, m.date, m.team1, m.team2, s.{team_col} AS team, {cols},
               RANK() OVER (ORDER BY {order}) AS rk
        FROM {table} s JOIN matches m ON m.id = s.match_id
        LEFT JOIN alias_map am ON LOWER(s.{name_col}) = am.name_key
        WHERE {scope['where']} AND m.gender = :gender AND m.date >= :since AND m.date <= :upto
          AND COALESCE(am.canonical_name, s.{name_col}) = :name
        ORDER BY {order}, m.date LIMIT {CHART_ROWS}
    """), {**scope["params"], "fmt": scope["fmt"], "gender": match.get("gender") or "male", "since": SINCE,
           "upto": match["date"], "name": fact["subject"]}).mappings()
    out = []
    for r in rows:
        out.append({"rank": int(r["rk"]), "label": f"v {_opponent(r, r['team'])}, {r['date'].year}",
                    ("runs" if bat else "wickets"): r["runs"] if bat else r["wickets"],
                    "display": f"{r['runs']} ({r['balls']})" if bat else f"{r['wickets']}/{r['runs']}",
                    "highlight": r["match_id"] == str(match["id"])})
    return {"metric": "runs" if bat else "wickets", "group": "innings" if bat else "spells", "rows": out,
            "title_prefix": f"{_poss(fact['subject'])} best {scope['label']} {'scores' if bat else 'figures'}"}


def match_records(db: Session, match: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Record facts for one match (a `matches` row as a dict), strongest first."""
    scope = _scope(match)
    facts: List[Dict[str, Any]] = []
    for template in _templates(scope["fmt"]):
        facts += _rank_facts(db, match, scope, template)
    facts += _career_bests(db, match, scope)
    # One angle per player: keep the strongest (a record score is also a career-best).
    best: Dict[str, Dict[str, Any]] = {}
    for f in sorted(facts, key=lambda f: f["weight"], reverse=True):
        best.setdefault(f"{f['subject']}|{'bat' if 'bat' in f['kind'] else 'bowl'}", f)
    for f in best.values():
        f["scope"] = scope["label"]
        if "chart" not in f:
            f["chart"] = _player_chart(db, match, scope, f)
    return sorted(best.values(), key=lambda f: f["weight"], reverse=True)
