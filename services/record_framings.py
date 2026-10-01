"""
Record, first and streak framings for one match (Notes plan §C.2; docs/content_guidelines.md:
"record, first or streak framing about the player everyone is watching" is what lands on Reddit).

services/records.py ranks this match's innings and spells and spots career-bests. This adds:

  streaks       a team's current winning/losing run, a batter's consecutive fifties, a bowler's run
                of matches with a wicket -- ranked against every such run in the scope since 2015,
                or "their longest since <year>" when it is not an all-time one
  firsts        a head-to-head win after a run of defeats, a first win at a ground in years, a
                star batter's fifty after a long drought
  fastest       balls to a fifty / hundred (/ 150 in ODIs), ranked within the scope (ball-by-ball)
  venue         the highest total, highest successful chase and lowest total defended at the ground

Every fact has the records.py shape: title (a statement with its numbers), numbers, rank / n /
since_year, method, weight and a ranked chart with this match highlighted, so content packs,
recap notes and the number check use it unchanged. Heavy populations are cached per scope and
data version, like the standout scanner's.
"""
import math
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.match_recap import _poss
from services.player_aliases import ALIAS_MAP_CTE
from services.query_cache import data_version
from services.records import CHART_ROWS, SINCE, _superlative, ordinal

RANK_MAX = 5
MIN_RUNS_POPULATION = 50        # runs (streaks) of this kind in the scope before a rank means anything
MIN_STREAK = {"team_W": 5, "team_L": 5, "bat_50": 3, "bowl_wkt": 10}
LONGEST_SINCE_GAP = 2           # "their longest since 2019" only when that is 2+ years back
DROUGHT_DEFEATS = 4             # a head-to-head / ground "first since" needs this many straight defeats
DROUGHT_INNINGS = {"T20": 12, "ODI": 10}
DROUGHT_PRIOR_FIFTIES = 5       # only for established batters
MILESTONES = {"T20": (50, 100), "ODI": (50, 100, 150)}
MILESTONE_MIN_POPULATION = {50: 200, 100: 40, 150: 20}
MILESTONE_WORD = {50: "fifty", 100: "hundred", 150: "150"}
# Ground records: only the top of each list is a post ("the 3rd-highest total at X" is not).
VENUE_RANK_MAX = {"total": 1, "chase": 2, "defended": 1}
VENUE_MIN = {"total": 40, "chase": 15, "defended": 15}
FULL_BALLS = {"T20": 120, "ODI": 300}

_CACHE: Dict[Tuple, Any] = {}


def _cached(db: Session, key: Tuple, build):
    full = (*key, data_version(db))
    if full not in _CACHE:
        if len(_CACHE) > 64:
            _CACHE.clear()
        _CACHE[full] = build()
    return _CACHE[full]


def clear_cache() -> None:
    _CACHE.clear()


def _short_team(name: Optional[str]) -> str:
    """'Sunrisers Hyderabad' -> 'SH'; short names pass through (same rule as api/_lib/share.mjs)."""
    words = (name or "").split()
    return "".join(w[0] for w in words).upper() if len(name or "") > 12 and len(words) > 1 else (name or "")


def _ground(venue: Optional[str]) -> str:
    return (venue or "").split(",")[0].strip()


def _matches_word(scope: Dict[str, Any], n: int = 2) -> str:
    """'ODIs' / 'T20Is' / 'IPL matches' (singular when n == 1)."""
    if scope["international"]:
        return scope["label"] + ("s" if n != 1 else "")
    return f"{scope['label']} match" + ("es" if n != 1 else "")


def _in_the(scope: Dict[str, Any]) -> str:
    """'in an ODI' / 'in a T20I' / 'in the IPL'."""
    if scope["international"]:
        return "in an ODI" if scope["label"] == "ODI" else "in a T20I"
    return f"in the {scope['label']}"


def _params(scope: Dict[str, Any], gender: str) -> Dict[str, Any]:
    return {**scope["params"], "fmt": scope["fmt"], "gender": gender, "since": SINCE}


def _rank_desc(values: List[float], value: float) -> Tuple[int, bool]:
    better = sum(1 for v in values if v > value)
    return better + 1, sum(1 for v in values if v == value) > 1


def _fact(kind: str, subject: str, team: str, title: str, numbers: Dict[str, Any], weight: float, method: str,
          chart: Dict[str, Any], rank: Optional[int] = None, n: Optional[int] = None, since_year: int = SINCE.year):
    return {"kind": kind, "subject": subject, "team": team, "title": title, "numbers": numbers, "weight": weight,
            "method": method, "chart": chart, "rank": rank, "n": n, "since_year": since_year}


# ------------------------------------------------------------------------------------- results

def _team_results(db: Session, scope: Dict[str, Any], gender: str) -> Dict[str, List[Dict[str, Any]]]:
    """Each team's results in the scope since 2015, in order: {team: [{match_id, date, opp, venue, r}]}.

    r is W when the team is the recorded winner, L when the opponent is, otherwise N (no result,
    tie, or a winner name that matches neither side) -- N breaks a streak rather than guess.
    """
    def build():
        rows = db.execute(text(f"""
            SELECT m.id, m.date, m.team1, m.team2, m.winner, m.venue FROM matches m
            WHERE {scope['where']} AND m.gender = :gender AND m.date >= :since
            ORDER BY m.date, m.id
        """), _params(scope, gender)).mappings()
        out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for m in rows:
            for team, opp in ((m["team1"], m["team2"]), (m["team2"], m["team1"])):
                r = "W" if m["winner"] == team else "L" if m["winner"] == opp else "N"
                out[team].append({"match_id": str(m["id"]), "date": m["date"], "opp": opp, "venue": m["venue"], "r": r})
        return dict(out)
    return _cached(db, ("results", scope["label"], scope["fmt"], gender), build)


def _runs(seq: List[Dict[str, Any]], hit) -> List[Dict[str, Any]]:
    """Maximal runs of consecutive entries where hit(entry); each {length, first, last}."""
    runs, cur = [], None
    for e in seq:
        if hit(e):
            if cur:
                cur["length"] += 1
                cur["last"] = e
            else:
                cur = {"length": 1, "first": e, "last": e}
        else:
            if cur:
                runs.append(cur)
            cur = None
    if cur:
        runs.append(cur)
    return runs


def _years(run: Dict[str, Any]) -> str:
    a, b = run["first"]["date"].year, run["last"]["date"].year
    return str(a) if a == b else f"{a}-{str(b)[2:]}"


def _streak_fact(kind: str, who: str, team: str, length: int, current: Dict[str, Any], history: List[Tuple[str, Dict[str, Any]]],
                 own_before: List[Dict[str, Any]], scope: Dict[str, Any], match: Dict[str, Any], text_now: str,
                 run_word: str, unit: str, ranked_only: bool = False) -> Optional[Dict[str, Any]]:
    """Rank a current run against every run of its kind; else "longest since <year>" for the subject.

    "Since <year>" is when the history actually starts (a league founded in 2023 has no 2015)."""
    lengths = [r["length"] for _, r in history]
    since = max(SINCE.year, min((r["first"]["date"].year for _, r in history), default=SINCE.year))
    own_since = max(SINCE.year, min((r["first"]["date"].year for r in own_before + [current])))
    n = len(lengths)
    rank, tied = _rank_desc(lengths, length)
    rows = sorted(history, key=lambda x: (-x[1]["length"], x[1]["last"]["date"]))
    chart_rows, seen_current = [], False
    for i, (name, r) in enumerate(rows[:CHART_ROWS]):
        is_current = r is current
        seen_current |= is_current
        chart_rows.append({"rank": _rank_desc(lengths, r["length"])[0], "label": f"{name}, {_years(r)}", "length": r["length"],
                           "display": str(r["length"]), "highlight": is_current})
    if not seen_current:
        chart_rows = chart_rows[:CHART_ROWS - 1] + [{"rank": rank, "label": f"{who}, {_years(current)}", "length": length,
                                                     "display": str(length), "highlight": True}]
    chart = {"metric": "length", "group": unit, "rows": chart_rows, "metric_label": f"{run_word} length"}
    numbers = {"length": length}
    if n >= MIN_RUNS_POPULATION and rank <= RANK_MAX:
        sup = ("joint " if tied else "") + _superlative(rank, "longest")
        title = f"{text_now}, {sup} {scope['label']} {run_word} since {since}"
        return _fact(kind, who, team, title, {**numbers, "n": n, "since": since}, (RANK_MAX + 1 - rank) * math.log10(n),
                     f"Ranked against all {n:,} {scope['label']} {run_word}s in Hindsight's data since {since}.",
                     chart, rank, n, since_year=since)
    if ranked_only:
        return None
    longer = [r for r in own_before if r["length"] >= length]
    if not longer:
        if len(own_before) < 3:
            return None  # a short history makes "their longest" trivia
        title = f"{text_now}, {_poss(who)} longest {scope['label']} {run_word} since {own_since}"
        return _fact(kind, who, team, title, {**numbers, "since": own_since}, 4.0,
                     f"Compared with {_poss(who)} earlier {scope['label']} {run_word}s in Hindsight's data since {own_since}.",
                     chart, since_year=own_since)
    last_year = max(r["last"]["date"].year for r in longer)
    if match["date"].year - last_year >= LONGEST_SINCE_GAP:
        title = f"{text_now}, {_poss(who)} longest {scope['label']} {run_word} since {last_year}"
        return _fact(kind, who, team, title, {**numbers, "year": last_year}, 3.0 + (match["date"].year - last_year) / 2,
                     f"{_poss(who)} last {scope['label']} {run_word} this long ended in {last_year}.", chart, since_year=last_year)
    return None


def team_streaks(db: Session, match: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    gender = match.get("gender") or "male"
    results = _team_results(db, scope, gender)
    mid, facts = str(match["id"]), []
    for team in (match["team1"], match["team2"]):
        seq = results.get(team) or []
        upto = next((i for i, e in enumerate(seq) if e["match_id"] == mid), None)
        if upto is None or seq[upto]["r"] == "N":
            continue
        r = seq[upto]["r"]
        kind = f"team_{r}"
        own = _runs(seq[:upto + 1], lambda e, r=r: e["r"] == r)
        current = own[-1] if own and own[-1]["last"]["match_id"] == mid else None
        if not current or current["length"] < MIN_STREAK[kind]:
            continue
        history: List[Tuple[str, Dict[str, Any]]] = []
        for other, oseq in results.items():
            cut = [e for e in oseq if e["date"] <= match["date"]]
            for run in _runs(cut, lambda e, r=r: e["r"] == r):
                history.append((other, current if other == team and run["last"]["match_id"] == mid else run))
        verb = "won" if r == "W" else "lost"
        text_now = f"{team} have {verb} {current['length']} {_matches_word(scope)} in a row"
        fact = _streak_fact(f"team_streak_{r}", team, team, current["length"], current, history, own[:-1], scope, match,
                            text_now, "winning run" if r == "W" else "losing run", "runs")
        if fact:
            facts.append(fact)
    return facts


def _won_at(scope: Dict[str, Any]) -> str:
    """'won an ODI' / 'won a T20I' / 'won an IPL match' (not "won the IPL")."""
    if scope["international"]:
        return "won an ODI" if scope["label"] == "ODI" else "won a T20I"
    return f"won {_article(scope['label'])} {scope['label']} match"


def _article(word: str) -> str:
    """'an' before a vowel sound; acronyms are read letter by letter ("an MLC", "a BBL", "an SA20")."""
    acronym = word.isupper() or any(c.isdigit() for c in word)
    return "an" if word[:1].upper() in ("AEFHILMNORSX" if acronym else "AEIOU") else "a"


def _history(db: Session, match: Dict[str, Any], scope: Dict[str, Any], team: str, extra: str, params: Dict[str, Any]):
    """The team's earlier results in the scope (all of Hindsight's history, not only since 2015)."""
    rows = db.execute(text(f"""
        SELECT m.id, m.date, m.team1, m.team2, m.winner FROM matches m
        WHERE {scope['where']} AND m.gender = :gender AND (m.team1 = :team OR m.team2 = :team) {extra}
          AND (m.date < :d OR (m.date = :d AND m.id < :mid))
        ORDER BY m.date, m.id
    """), {**scope["params"], "fmt": scope["fmt"], "gender": match.get("gender") or "male", "team": team,
           "d": match["date"], "mid": str(match["id"]), **params}).mappings()
    out = []
    for m in rows:
        opp = m["team2"] if m["team1"] == team else m["team1"]
        r = "W" if m["winner"] == team else "L" if m["winner"] == opp else "N"
        if r != "N":
            out.append({"date": m["date"], "r": r})
    return out


def team_firsts(db: Session, match: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The winner beat this opponent (or won at this ground) after a run of defeats."""
    winner = match.get("winner")
    if winner not in (match["team1"], match["team2"]):
        return []
    opp = match["team2"] if winner == match["team1"] else match["team1"]
    ground = _ground(match.get("venue"))
    facts = []
    for kind, extra, params, where_text, what in (
        ("h2h_first_since", "AND (m.team1 = :opp OR m.team2 = :opp)", {"opp": opp}, f"beat {opp} {_in_the(scope)}", f"v {opp}"),
        ("venue_first_since", "AND m.venue = :venue", {"venue": match.get("venue")}, f"{_won_at(scope)} at {ground}", f"at {ground}"),
    ):
        before = _history(db, match, scope, winner, extra, params)
        defeats = 0
        for e in reversed(before):
            if e["r"] != "L":
                break
            defeats += 1
        if defeats < DROUGHT_DEFEATS:
            continue
        last_win = next((e for e in reversed(before) if e["r"] == "W"), None)
        if last_win:
            title = f"{winner} {where_text} for the first time since {last_win['date'].year}, ending a run of {defeats} defeats"
            numbers = {"defeats": defeats, "year": last_win["date"].year}
        else:
            # Every earlier meeting in the data was a defeat: a first win, as far back as the data goes.
            title = f"{winner} {where_text} for the first time, at the {defeats + 1}th attempt"
            title = title.replace(f"{defeats + 1}th", ordinal(defeats + 1))
            numbers = {"defeats": defeats, "attempt": defeats + 1}
        # Chart: the winner's record in these meetings by year, this year highlighted.
        by_year: Dict[int, List[int]] = defaultdict(lambda: [0, 0])
        for e in before + [{"date": match["date"], "r": "W"}]:
            by_year[e["date"].year][0 if e["r"] == "W" else 1] += 1
        years = sorted(by_year)[-CHART_ROWS:]
        rows = [{"rank": i + 1, "label": str(y), "wins": by_year[y][0], "display": f"{by_year[y][0]}-{by_year[y][1]}",
                 "highlight": y == match["date"].year} for i, y in enumerate(reversed(years))]
        first_year = before[0]["date"].year if before else match["date"].year
        facts.append(_fact(kind, winner, winner, title, numbers, 3.0 + min(defeats, 12) / 2,
                           f"{_poss(winner)} {scope['label']} results {what} in Hindsight's data since {first_year} (won-lost by year).",
                           {"metric": "wins", "group": "seasons", "rows": rows, "metric_label": f"{winner} wins"},
                           since_year=first_year))
    return facts


# ------------------------------------------------------------------------------------- players

def _innings(db: Session, scope: Dict[str, Any], gender: str, bowling: bool) -> Dict[str, List[Dict[str, Any]]]:
    """Each player's innings (or spells) in the scope since 2015, in order."""
    table, name_col, team_col, measure = (("bowling_stats", "bowler", "bowling_team", "s.wickets") if bowling
                                          else ("batting_stats", "striker", "batting_team", "s.runs"))

    def build():
        rows = db.execute(text(f"""
            WITH {ALIAS_MAP_CTE}
            SELECT COALESCE(am.canonical_name, s.{name_col}) AS name, s.{team_col} AS team, s.match_id, s.innings,
                   m.date, {measure} AS value, m.team1, m.team2
            FROM {table} s JOIN matches m ON m.id = s.match_id
            LEFT JOIN alias_map am ON LOWER(s.{name_col}) = am.name_key
            WHERE {scope['where']} AND m.gender = :gender AND m.date >= :since
            ORDER BY m.date, s.match_id, s.innings
        """), _params(scope, gender)).mappings()
        out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in rows:
            out[r["name"]].append({**dict(r), "match_id": str(r["match_id"])})
        return dict(out)
    return _cached(db, ("innings", "bowl" if bowling else "bat", scope["label"], scope["fmt"], gender), build)


def player_streaks(db: Session, match: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    gender, mid, facts = match.get("gender") or "male", str(match["id"]), []
    for bowling, kind, hit, run_word, unit in (
        (False, "bat_50", lambda e: (e["value"] or 0) >= 50, "run of fifties", "innings"),
        (True, "bowl_wkt", lambda e: (e["value"] or 0) >= 1, "run of matches with a wicket", "matches"),
    ):
        players = _innings(db, scope, gender, bowling)
        in_match = {name for name, seq in players.items() if any(e["match_id"] == mid for e in seq)}
        history = None
        for name in sorted(in_match):
            seq = players[name]
            upto = max(i for i, e in enumerate(seq) if e["match_id"] == mid)
            own = _runs(seq[:upto + 1], hit)
            current = own[-1] if own and own[-1]["last"]["match_id"] == mid else None
            if not current or current["length"] < MIN_STREAK[kind]:
                continue
            if history is None:
                history = []
                for other, oseq in players.items():
                    for run in _runs([e for e in oseq if e["date"] <= match["date"]], hit):
                        history.append((other, run))
            hist = [(o, current if o == name and r["last"]["match_id"] == mid else r) for o, r in history]
            last = seq[upto]
            if bowling:
                text_now = f"{name} has taken a wicket in {current['length']} {_matches_word(scope)} in a row"
            else:
                text_now = f"{name} has made {current['length']} {scope['label']} fifties in a row"
            # A bowler's "longest run of matches with a wicket" is only a post when it is a record.
            fact = _streak_fact(f"{'bowl' if bowling else 'bat'}_streak", name, last["team"], current["length"], current, hist,
                                own[:-1], scope, match, text_now, run_word, unit, ranked_only=bowling)
            if fact:
                fact["numbers"]["latest"] = last["value"]
                facts.append(fact)
    return facts


def batter_droughts(db: Session, match: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """An established batter's fifty after a long run without one."""
    players = _innings(db, scope, match.get("gender") or "male", bowling=False)
    mid, need, facts = str(match["id"]), DROUGHT_INNINGS.get(scope["fmt"], 12), []
    for name, seq in players.items():
        idx = [i for i, e in enumerate(seq) if e["match_id"] == mid and (e["value"] or 0) >= 50]
        if not idx:
            continue
        i = idx[0]
        before = seq[:i]
        gap = 0
        for e in reversed(before):
            if (e["value"] or 0) >= 50:
                break
            gap += 1
        prior_fifties = sum(1 for e in before if (e["value"] or 0) >= 50)
        if gap < need or prior_fifties < DROUGHT_PRIOR_FIFTIES:
            continue
        hit = seq[i]
        opp = hit["team2"] if hit["team"] == hit["team1"] else hit["team1"]
        recent = seq[max(0, i - CHART_ROWS + 1):i + 1]
        rows = [{"rank": k + 1, "label": f"v {e['team2'] if e['team'] == e['team1'] else e['team1']}, {e['date']:%b %Y}",
                 "runs": e["value"], "display": str(e["value"]), "highlight": e is hit} for k, e in enumerate(reversed(recent))]
        title = f"{_poss(name)} {hit['value']} v {opp} ends a run of {gap} {scope['label']} innings without a fifty"
        facts.append(_fact("bat_drought", name, hit["team"], title, {"runs": hit["value"], "gap": gap}, 3.0 + gap / 6,
                           f"{_poss(name)} last {len(recent)} {scope['label']} innings in Hindsight's data, most recent first.",
                           {"metric": "runs", "group": "innings", "rows": rows, "metric_label": "runs"}))
    return facts


def fastest_milestones(db: Session, match: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Balls to a fifty / hundred, ranked in the scope (ball-by-ball matches only)."""
    if match.get("data_source") not in (None, "bbb"):
        return []
    gender, targets = match.get("gender") or "male", MILESTONES.get(scope["fmt"], (50, 100))
    cols = ", ".join(f"MIN(dd.cur_bat_bf) FILTER (WHERE dd.cur_bat_runs >= {t}) AS b{t}" for t in targets)

    def build():
        rows = db.execute(text(f"""
            WITH {ALIAS_MAP_CTE}
            SELECT dd.p_match AS match_id, dd.inns, COALESCE(am.canonical_name, dd.bat) AS name, dd.team_bat AS team,
                   dd.team_bowl AS opp, m.date, {cols}
            FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
            LEFT JOIN alias_map am ON LOWER(dd.bat) = am.name_key
            WHERE {scope['where']} AND m.gender = :gender AND m.date >= :since AND dd.cur_bat_runs >= {min(targets)}
            GROUP BY 1, 2, 3, 4, 5, 6
        """), _params(scope, gender)).mappings()
        return [{**dict(r), "match_id": str(r["match_id"])} for r in rows]
    pop = _cached(db, ("milestones", scope["label"], scope["fmt"], gender), build)
    pop = [r for r in pop if r["date"] <= match["date"]]
    mid, facts = str(match["id"]), []
    for t in targets:
        reached = sorted((r for r in pop if r[f"b{t}"] is not None), key=lambda r: (r[f"b{t}"], r["date"]))
        n = len(reached)
        if n < MILESTONE_MIN_POPULATION[t]:
            continue
        balls = [r[f"b{t}"] for r in reached]
        since = max(SINCE.year, min(r["date"].year for r in reached))
        for hit in (r for r in reached if r["match_id"] == mid):
            b = hit[f"b{t}"]
            rank = sum(1 for x in balls if x < b) + 1
            tied = balls.count(b) > 1
            if rank > RANK_MAX:
                continue
            word = MILESTONE_WORD[t]
            sup = ("joint " if tied else "") + _superlative(rank, "fastest")
            title = f"{_poss(hit['name'])} {word} v {hit['opp']} came off {b} balls, {sup} {scope['label']} {word} since {since}"
            top = reached[:CHART_ROWS]
            if hit not in top:
                top = top[:CHART_ROWS - 1] + [hit]
            # One batter can hold several of the fastest; the opponent tells the innings apart.
            rows = [{"rank": sum(1 for x in balls if x < r[f"b{t}"]) + 1,
                     "label": f"{r['name']} v {_short_team(r['opp'])}, {r['date'].year}",
                     "balls": r[f"b{t}"], "display": f"{r[f'b{t}']} balls", "highlight": r is hit} for r in top]
            facts.append(_fact(f"bat_fastest_{t}", hit["name"], hit["team"], title, {"balls": b, "milestone": t, "n": n, "since": since},
                               (RANK_MAX + 1 - rank) * math.log10(n) + (1 if t >= 100 else 0),
                               f"Balls faced to reach {t}, ranked against all {n:,} {scope['label']} innings that reached it "
                               f"in Hindsight's ball-by-ball data since {since}.",
                               {"metric": "balls", "group": "innings", "rows": rows, "lower_is_better": True,
                                "metric_label": f"balls to {t}"}, rank, n, since_year=since))
    return facts


# ------------------------------------------------------------------------------------- venue

def _team_totals(db: Session, fmt: str, gender: str) -> List[Dict[str, Any]]:
    """Every innings total (innings 1-2) of this format since 2015, from ball-by-ball data."""
    def build():
        rows = db.execute(text("""
            SELECT dd.p_match AS match_id, dd.inns, dd.team_bat AS team, m.venue, m.date, m.winner,
                   MAX(dd.inns_runs) AS runs, MAX(dd.inns_wkts) AS wkts, MAX(dd.max_balls) AS max_balls
            FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
            WHERE m.format = :fmt AND m.gender = :gender AND m.date >= :since AND dd.inns IN (1, 2)
            GROUP BY 1, 2, 3, 4, 5, 6
        """), {"fmt": fmt, "gender": gender, "since": SINCE}).mappings()
        return [{**dict(r), "match_id": str(r["match_id"])} for r in rows]
    return _cached(db, ("totals", fmt, gender), build)


def _this_match_totals(db: Session, match: Dict[str, Any]) -> List[Dict[str, Any]]:
    """This match's innings totals for a Cricsheet-loaded match (no delivery_details yet)."""
    rows = db.execute(text("""
        SELECT innings AS inns, batting_team AS team,
               SUM(COALESCE(runs_off_bat, 0) + COALESCE(extras, 0)) AS runs,
               COUNT(*) FILTER (WHERE wicket_type IS NOT NULL AND wicket_type <> '' AND wicket_type <> 'retired hurt') AS wkts
        FROM deliveries WHERE match_id = :m AND innings IN (1, 2) GROUP BY 1, 2
    """), {"m": str(match["id"])}).mappings()
    return [{**dict(r), "match_id": str(match["id"]), "venue": match.get("venue"), "date": match["date"],
             "winner": match.get("winner"), "max_balls": None} for r in rows]


def venue_records(db: Session, match: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    fmt, gender, mid, venue = scope["fmt"], match.get("gender") or "male", str(match["id"]), match.get("venue")
    if not venue:
        return []
    full = FULL_BALLS.get(fmt)
    pop = [r for r in _team_totals(db, fmt, gender) if r["venue"] == venue and r["date"] <= match["date"]]
    mine = [r for r in pop if r["match_id"] == mid] or _this_match_totals(db, match)
    pop = [r for r in pop if r["match_id"] != mid] + mine
    # Reduced-overs innings make "lowest defended" and "highest chase" meaningless.
    complete = [r for r in pop if not r["max_balls"] or not full or r["max_balls"] >= full]
    ground, facts = _ground(venue), []
    for kind, rows, desc, label, plural in (
        ("venue_total", complete, True, f"highest {fmt} total", f"{fmt} innings totals"),
        ("venue_chase", [r for r in complete if r["inns"] == 2 and r["team"] == r["winner"]], True,
         f"highest successful {fmt} chase", f"successful {fmt} chases"),
        ("venue_defended", [r for r in complete if r["inns"] == 1 and r["team"] == r["winner"]], False,
         f"lowest {fmt} total defended", f"{fmt} totals defended"),
    ):
        n = len(rows)
        if n < VENUE_MIN[kind.split("_")[1]]:
            continue
        ordered = sorted(rows, key=lambda r: ((-r["runs"]) if desc else r["runs"], r["date"]))
        since = max(SINCE.year, min(r["date"].year for r in rows))   # a new ground has no 2015
        for hit in (r for r in ordered if r["match_id"] == mid):
            rank = sum(1 for r in rows if (r["runs"] > hit["runs"] if desc else r["runs"] < hit["runs"])) + 1
            if rank > VENUE_RANK_MAX[kind.split("_")[1]]:
                continue
            tied = sum(1 for r in rows if r["runs"] == hit["runs"]) > 1
            word = label.split(" ", 1)
            sup = ("joint " if tied else "") + _superlative(rank, word[0])
            score = f"{hit['runs']}/{hit['wkts']}"
            if kind == "venue_defended":
                title = f"{hit['team']} defended {hit['runs']} at {ground}, {sup} {word[1]} there since {since}"
            elif kind == "venue_chase":
                title = f"{_poss(hit['team'])} {score} chase at {ground} is {sup} {word[1]} there since {since}"
            else:
                title = f"{_poss(hit['team'])} {score} is {sup} {word[1]} at {ground} since {since}"
            top = ordered[:CHART_ROWS]
            if hit not in top:
                top = top[:CHART_ROWS - 1] + [hit]
            chart_rows = [{"rank": sum(1 for x in rows if (x["runs"] > r["runs"] if desc else x["runs"] < r["runs"])) + 1,
                           "label": f"{r['team']}, {r['date'].year}", "runs": r["runs"], "display": f"{r['runs']}/{r['wkts']}",
                           "highlight": r is hit} for r in top]
            facts.append(_fact(kind, hit["team"], hit["team"], title,
                               {"runs": hit["runs"], "wkts": hit["wkts"], "n": n, "since": since}, (4 - rank) * math.log10(n),
                               f"Ranked against all {n:,} {plural} at {venue} "
                               f"in Hindsight's ball-by-ball data since {since} (full-length innings).",
                               {"metric": "runs", "group": "innings", "rows": chart_rows, "lower_is_better": not desc,
                                "metric_label": "runs"}, rank, n, since_year=since))
    return facts


def framing_facts(db: Session, match: Dict[str, Any], scope: Dict[str, Any]) -> List[Dict[str, Any]]:
    facts: List[Dict[str, Any]] = []
    for producer in (team_streaks, team_firsts, player_streaks, batter_droughts, fastest_milestones, venue_records):
        facts += producer(db, match, scope)
    return facts
