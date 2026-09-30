"""
Stat shapes the query builder cannot express, for "Idea -> pack" (services/content_ideas.py).

  count within   "3 batter centuries (vs India) in an ODI innings": every qualifying
                 player-innings from the scorecard stats tables, counted per innings or match.
  race           "fastest to 100 in ODIs (balls)", "slowest team to 300", "fastest to 10,000 ODI
                 runs by innings": the first ball / innings at which a running total reaches X.

Both are parsed in code, not by the language model: the words that matter (a number, a
milestone, "vs X", "since 2015") are few and fixed, and the parser misread "vs India" as India
batting. Counts read batting_stats/bowling_stats, so matches loaded from any source (ball-by-ball
CSV or Cricsheet) count; balls-based races need delivery_details' running totals.
"""
import math
import re
from datetime import date, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.competition_aliases import canonical_competition, variants_for
from services.content_rules import MAIN_LEAGUES
from services.player_aliases import ALIAS_MAP_CTE
from services.records import _superlative, ordinal

NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
WITHIN = re.compile(r"\bin\s+(?:a|an|one|the same|a single|single)\s+(?:[\w-]+\s+){0,2}?(innings|match|game)\b", re.I)
MILESTONES = [  # (pattern, member dimension, threshold, plural noun)
    (r"half[- ]centur|fift|\b50s\b", "batter", 50, "fifty-plus scores"),
    (r"centur|hundreds|\b100s\b|\btons\b", "batter", 100, "centuries"),
    (r"five[- ]?(?:wicket|fers?)|5[- ]?(?:wicket|fers?|wkt)", "bowler", 5, "five-wicket hauls"),
    (r"four[- ]?(?:wicket|fers?)|4[- ]?(?:wicket|fers?|wkt)", "bowler", 4, "four-wicket hauls"),
    (r"three[- ]?(?:wicket|fers?)|3[- ]?(?:wicket|fers?|wkt)", "bowler", 3, "three-wicket hauls"),
]
TEAM_SHORT = {"wi": "West Indies", "sa": "South Africa", "nz": "New Zealand", "aus": "Australia", "eng": "England",
              "ind": "India", "pak": "Pakistan", "sl": "Sri Lanka", "ban": "Bangladesh", "afg": "Afghanistan",
              "ire": "Ireland", "zim": "Zimbabwe"}
RACE = re.compile(r"\b(fastest|quickest|slowest)\b", re.I)
NAMED_SCORES = [(r"double[- ]?(?:century|hundred|ton)", 200), (r"\b150\b", 150), (r"century|hundred|\bton\b", 100),
                (r"half[- ]?century|fifty", 50)]


# ---------------------------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------------------------

def _teams(db: Session) -> List[str]:
    return [r[0] for r in db.execute(text(
        "SELECT DISTINCT team1 FROM matches WHERE date >= now() - interval '6 years' "
        "UNION SELECT DISTINCT team2 FROM matches WHERE date >= now() - interval '6 years'")) if r[0]]


def _team_after(pattern: str, idea: str, teams: List[str]) -> Optional[str]:
    m = re.search(pattern + r"\s+(?:the\s+)?([A-Za-z][A-Za-z .'-]{1,40})", idea, re.I)
    if not m:
        return None
    phrase = m.group(1).strip().lower()
    if phrase.split()[0] in TEAM_SHORT:
        return TEAM_SHORT[phrase.split()[0]]
    hits = [t for t in teams if phrase.startswith(t.lower())]
    return max(hits, key=len) if hits else None


def parse_scope(idea: str, db: Session, fmt_choice: Optional[str] = None) -> Dict[str, Any]:
    """Format, competition, opponent, own team and date window, read from the idea's words."""
    teams = _teams(db)
    fmt = (fmt_choice or "").upper()
    if fmt not in ("T20", "ODI"):
        fmt = "ODI" if re.search(r"\bODIs?\b|one[- ]day", idea, re.I) else "T20" if re.search(
            r"\bT20I?s?\b|\bIPL\b|\bBBL\b|\bPSL\b|\bCPL\b|\bSA20\b|Hundred|Blast", idea, re.I) else "ODI"
    league = next((lg for lg in MAIN_LEAGUES if re.search(rf"\b{re.escape(lg)}\b", idea, re.I)), None)
    if re.search(r"\bT20Is?\b", idea, re.I):
        league = "T20I"
    since = re.search(r"\b(?:since|from|after)\s+((?:19|20)\d{2})\b", idea, re.I)
    in_year = re.search(r"\bin\s+((?:19|20)\d{2})\b", idea, re.I)
    return {
        "fmt": fmt, "league": league,
        "opponent": _team_after(r"\b(?:v|vs\.?|versus|against)", idea, teams),
        "team": _team_after(r"\b(?:by|for)", idea, teams),
        "start": f"{since.group(1)}-01-01" if since else f"{in_year.group(1)}-01-01" if in_year else None,
        "end": f"{in_year.group(1)}-12-31" if in_year and not since else None,
    }


def parse_count_within(idea: str) -> Optional[Dict[str, Any]]:
    m = WITHIN.search(idea)
    if not m:
        return None
    before = idea[:m.start()]
    counts = [int(t) if t.isdigit() else NUMBER_WORDS[t.lower()]
              for t in re.findall(r"\b(\d{1,2}|" + "|".join(NUMBER_WORDS) + r")\b(?![- ]?(?:wicket|fer|wkt))", before, re.I)]
    counts = [c for c in counts if 2 <= c <= 11]
    milestone = next(((dim, thr, noun) for pat, dim, thr, noun in MILESTONES if re.search(pat, idea, re.I)), None)
    if not counts or not milestone:
        return None
    return {"type": "rollup", "n": counts[0], "unit": "innings" if m.group(1).lower() == "innings" else "match",
            "member": milestone[0], "threshold": milestone[1], "noun": milestone[2]}


def parse_race(idea: str) -> Optional[Dict[str, Any]]:
    m = RACE.search(idea)
    if not m:
        return None
    direction = "slowest" if m.group(1).lower() == "slowest" else "fastest"
    after = idea[m.end():]
    target, measure = None, None
    # "to 100", "to 10k runs", "to 100 ODI wickets": a word or two may sit before the measure, so
    # look for the measure first and fall back to a bare number.
    num = (re.search(r"\bto\s+(\d[\d,]*)\s*(k)?\b(?:\s+[A-Za-z0-9]+){0,2}?\s+(runs?|wickets?|wkts?)\b", after, re.I)
           or re.search(r"\bto\s+(\d[\d,]*)\s*(k)?()", after, re.I))
    if num:
        target = int(num.group(1).replace(",", "")) * (1000 if num.group(2) else 1)
        measure = "wickets" if num.group(3) and num.group(3).lower().startswith("w") else "runs"
    else:
        for pattern, value in NAMED_SCORES:
            if re.search(pattern, after, re.I):
                target, measure = value, "runs"
                break
    if not target:
        return None
    unit_m = re.search(r"\b(?:in|by)\s+(?:terms of\s+)?(balls|deliveries|innings|matches|games)\b", idea, re.I)
    subject = "team" if re.search(r"\bteams?\b|\btotal\b", idea, re.I) else ("bowler" if measure == "wickets" else "batter")
    if unit_m:
        unit = "balls" if unit_m.group(1).lower() in ("balls", "deliveries") else "innings"
    else:  # a career milestone is counted in innings; an innings milestone in balls
        unit = "innings" if (measure == "runs" and target >= 500) or (measure == "wickets" and target >= 20) else "balls"
    if subject == "team":
        unit = "balls"
    return {"type": "race", "direction": direction, "target": target, "measure": measure, "unit": unit, "subject": subject}


# ---------------------------------------------------------------------------------------------
# Shared SQL scope
# ---------------------------------------------------------------------------------------------

def _where(scope: Dict[str, Any], team_col: str, opp_expr: str) -> Tuple[str, Dict[str, Any]]:
    clauses = ["m.format = :fmt", "m.gender = 'male'"]
    params: Dict[str, Any] = {"fmt": scope["fmt"]}
    if scope.get("league") == "T20I":
        clauses.append("m.match_type = 'international'")
    elif scope.get("league"):
        clauses.append("m.competition = ANY(:comps)")
        params["comps"] = variants_for(canonical_competition(scope["league"]))
    if scope.get("team"):
        clauses.append(f"{team_col} = :team")
        params["team"] = scope["team"]
    if scope.get("opponent"):
        clauses.append(f"{opp_expr} = :opp")
        params["opp"] = scope["opponent"]
    if scope.get("start"):
        clauses.append("m.date >= :start")
        params["start"] = date.fromisoformat(scope["start"])
    if scope.get("end"):
        clauses.append("m.date <= :end")
        params["end"] = date.fromisoformat(scope["end"])
    return " AND ".join(clauses), params


def scope_label(scope: Dict[str, Any]) -> str:
    return scope.get("league") or scope["fmt"]


def window_text(db: Session, scope: Dict[str, Any]) -> Tuple[int, str]:
    """(first year, " since 2000") for the comparison window actually covered by the data."""
    if scope.get("start") and scope.get("end") and scope["start"][:4] == scope["end"][:4]:
        return int(scope["start"][:4]), f" in {scope['start'][:4]}"
    first = db.execute(text("SELECT MIN(date) FROM matches WHERE format = :fmt AND gender = 'male'"),
                       {"fmt": scope["fmt"]}).scalar()
    year = max(first.year if first else 2000, int(scope["start"][:4]) if scope.get("start") else 0)
    return year, f" since {year}"


def _opp(team_col: str) -> str:
    return f"CASE WHEN m.team1 = {team_col} THEN m.team2 ELSE m.team1 END"


# ---------------------------------------------------------------------------------------------
# Count within an innings / match
# ---------------------------------------------------------------------------------------------

def count_within(db: Session, spec: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Groups (innings or matches) with spec['n']+ qualifying performances, latest first."""
    batter = spec["member"] == "batter"
    team_col = "s.batting_team" if batter else "s.bowling_team"
    where, params = _where(scope, team_col, _opp(team_col))
    table, name_col, cols, qualifies = (
        ("batting_stats", "striker", "s.runs, s.balls_faced AS balls", "s.runs >= :thr") if batter else
        ("bowling_stats", "bowler", "s.wickets, s.runs_conceded AS runs, s.overs", "s.wickets >= :thr"))
    rows = db.execute(text(f"""
        WITH {ALIAS_MAP_CTE}
        SELECT s.match_id, s.innings, COALESCE(am.canonical_name, s.{name_col}) AS name, {team_col} AS team,
               {_opp(team_col)} AS opp, m.date, {cols}
        FROM {table} s JOIN matches m ON m.id = s.match_id
        LEFT JOIN alias_map am ON LOWER(s.{name_col}) = am.name_key
        WHERE {where} AND {qualifies}
    """), {**params, "thr": spec["threshold"]}).mappings()
    groups: Dict[tuple, Dict[str, Any]] = {}
    seen = set()
    for r in rows:
        key = (r["match_id"], r["innings"]) if spec["unit"] == "innings" else (r["match_id"],)
        if (key, r["name"]) in seen:  # the two ingest paths can both hold an innings
            continue
        seen.add((key, r["name"]))
        g = groups.setdefault(key, {"team": r["team"], "opp": r["opp"], "date": r["date"], "members": []})
        g["members"].append(dict(r))
    hits = [g for g in groups.values() if len(g["members"]) >= spec["n"]]
    for g in hits:
        g["members"].sort(key=lambda r: r["runs" if batter else "wickets"], reverse=True)
        g["details"] = [f"{r['name']} {r['runs']} ({r['balls']})" if batter else f"{r['name']} {r['wickets']}/{r['runs']}"
                        for r in g["members"]]
    return sorted(hits, key=lambda g: g["date"], reverse=True)


# ---------------------------------------------------------------------------------------------
# Races: fastest / slowest to X
# ---------------------------------------------------------------------------------------------

def race(db: Session, spec: Dict[str, Any], scope: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Every innings/player that reached the target, best first, with {name, value, ...}; plus a caveat."""
    target, asc = spec["target"], spec["direction"] == "fastest"
    order = "ASC" if asc else "DESC"
    caveat = None
    if spec["unit"] == "balls":
        if spec["subject"] == "team":
            where, params = _where(scope, "dd.team_bat", "dd.team_bowl")
            sql = f"""
                SELECT dd.p_match AS match_id, dd.inns, dd.team_bat AS name, dd.team_bat AS team, dd.team_bowl AS opp,
                       m.date, MIN(dd.inns_balls) FILTER (WHERE dd.inns_runs >= :target) AS value,
                       MAX(dd.inns_runs) AS final
                FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
                WHERE {where} GROUP BY 1, 2, 3, 4, 5, 6
            """
        elif spec["subject"] == "batter":
            where, params = _where(scope, "dd.team_bat", "dd.team_bowl")
            sql = f"""
                WITH {ALIAS_MAP_CTE}
                SELECT dd.p_match AS match_id, dd.inns, COALESCE(am.canonical_name, dd.bat) AS name, dd.team_bat AS team,
                       dd.team_bowl AS opp, m.date,
                       MIN(dd.cur_bat_bf) FILTER (WHERE dd.cur_bat_runs >= :target) AS value, MAX(dd.cur_bat_runs) AS final
                FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
                LEFT JOIN alias_map am ON LOWER(dd.bat) = am.name_key
                WHERE {where} GROUP BY 1, 2, 3, 4, 5, 6
            """
        else:  # bowler: legal balls bowled when the Nth wicket fell (cur_bowl_ovr is overs.balls)
            where, params = _where(scope, "dd.team_bowl", "dd.team_bat")
            balls = "(FLOOR(dd.cur_bowl_ovr) * 6 + ROUND((dd.cur_bowl_ovr - FLOOR(dd.cur_bowl_ovr)) * 10))"
            sql = f"""
                WITH {ALIAS_MAP_CTE}
                SELECT dd.p_match AS match_id, dd.inns, COALESCE(am.canonical_name, dd.bowl) AS name, dd.team_bowl AS team,
                       dd.team_bat AS opp, m.date,
                       MIN({balls}) FILTER (WHERE dd.cur_bowl_wkts >= :target) AS value, MAX(dd.cur_bowl_wkts) AS final
                FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
                LEFT JOIN alias_map am ON LOWER(dd.bowl) = am.name_key
                WHERE {where} GROUP BY 1, 2, 3, 4, 5, 6
            """
        rows = [dict(r) for r in db.execute(text(f"SELECT * FROM ({sql}) q WHERE value IS NOT NULL ORDER BY value {order}, date"),
                                            {**params, "target": target}).mappings()]
        for r in rows:
            r["value"] = int(r["value"])
        return _dedupe(rows, lambda r: (r["match_id"], r["inns"], r["name"])), caveat

    # Career: the innings number at which a running total first reached the target. Only players
    # whose first innings in the data is a year after it starts, so a career that began before
    # our data is never counted from the middle.
    batter = spec["subject"] == "batter"
    team_col = "s.batting_team" if batter else "s.bowling_team"
    where, params = _where({**scope, "start": None, "end": None}, team_col, _opp(team_col))
    table, name_col, measure = ("batting_stats", "striker", "s.runs") if batter else ("bowling_stats", "bowler", "s.wickets")
    first = db.execute(text("SELECT MIN(date) FROM matches WHERE format = :fmt AND gender = 'male'"), {"fmt": scope["fmt"]}).scalar()
    debut_floor = (first or date(2000, 1, 1)) + timedelta(days=365)
    rows = [dict(r) for r in db.execute(text(f"""
        WITH {ALIAS_MAP_CTE},
        inns AS (
            SELECT DISTINCT ON (COALESCE(am.canonical_name, s.{name_col}), s.match_id, s.innings)
                   COALESCE(am.canonical_name, s.{name_col}) AS name, {team_col} AS team, m.date, s.match_id, s.innings,
                   {measure} AS amount
            FROM {table} s JOIN matches m ON m.id = s.match_id
            LEFT JOIN alias_map am ON LOWER(s.{name_col}) = am.name_key
            WHERE {where}
            ORDER BY COALESCE(am.canonical_name, s.{name_col}), s.match_id, s.innings
        ),
        running AS (
            SELECT *, SUM(amount) OVER w AS total, ROW_NUMBER() OVER w AS inn_no, MIN(date) OVER (PARTITION BY name) AS debut
            FROM inns WINDOW w AS (PARTITION BY name ORDER BY date, match_id, innings)
        )
        SELECT DISTINCT ON (name) name, team, date, inn_no AS value, total AS final, debut
        FROM running WHERE total >= :target AND debut >= :floor
        ORDER BY name, inn_no
    """), {**params, "target": target, "floor": debut_floor}).mappings()]
    rows.sort(key=lambda r: (r["value"] if asc else -r["value"], r["date"]))
    caveat = f"Players who debuted from {debut_floor.year} (Hindsight's {scope['fmt']} data starts in {(first or date(2000,1,1)).year})."
    return rows, caveat


def _dedupe(rows: List[Dict[str, Any]], key: Callable) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for r in rows:
        k = key(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def race_words(spec: Dict[str, Any], scope: Dict[str, Any]) -> Dict[str, str]:
    """Nouns for titles: {what: "100", unit: "balls", plural: "ODI hundreds" ...}."""
    fmt = scope_label(scope)
    t = spec["target"]
    if spec["measure"] == "wickets":
        what = f"{t} wickets" if spec["unit"] == "innings" else f"{t} wickets in an innings"
    elif spec["unit"] == "innings":
        what = f"{t:,} {fmt} runs"
    else:
        what = str(t)
    if spec["subject"] == "team":
        noun = f"{fmt} innings to reach {t}"
    elif spec["unit"] == "innings":
        noun = f"{'batters' if spec['subject'] == 'batter' else 'bowlers'} to reach {what}"
    elif spec["measure"] == "runs" and t == 100:
        noun = f"{fmt} hundreds"
    elif spec["measure"] == "runs" and t == 50:
        noun = f"{fmt} fifties"
    else:
        noun = f"{fmt} innings reaching {what}"
    return {"what": what, "noun": noun, "unit": spec["unit"]}


def sup_word(rank: int, direction: str, tied: bool = False) -> str:
    """"the fastest", "the 3rd-slowest", "the joint-fastest", "the joint 3rd-fastest"."""
    if not tied:
        return _superlative(rank, direction)
    return f"the joint-{direction}" if rank == 1 else f"the joint {ordinal(rank)}-{direction}"
