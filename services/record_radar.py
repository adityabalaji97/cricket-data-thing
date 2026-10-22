"""
Record radar (RECORD_RADAR_PLAN.md): after a day's matches load, which leaderboards did they change?

A template is a count (sixes, runs, wickets...) under a condition (the powerplay, a batting position, against spin);
a scope is where it's counted (T20Is, a league, all men's T20s, one team's games). One scan per side (batting,
bowling) sums every ball up to the day into a small table, (player, team, competition, phase, batting position,
played-today) -> counts, from delivery_details plus the legacy table before 2015 (as services/idea_stats counts
records). Every template x scope is then a sum over that table, and the day's own part taken away gives each
player's count before the day. The query builder computes every metric for every group (37s for one all-T20s
leaderboard); a count needs none of them.

Events, per player who played that day:
  passed     moved above named players, into the top TOP_N (or level with one)
  entered    into the top TOP_N for the first time
  milestone  a round number on the template (100 sixes, 2,000 runs, 50 wickets)

Associates are included (they're in the data); a card labels them (decision 1). Family A only (ball counts from the
query builder); innings counts, within-innings and head-to-head follow (chunks 2-3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

TOP_N = 10
MAX_POS = 8          # batting positions 1-8 (a list "batting at 10" is a curiosity, not a record)
MAX_NTH = 25         # a milestone counts for the first 25 to reach it in the scope


@dataclass(frozen=True)
class Template:
    id: str
    label: str                       # "powerplay sixes": "most {label}"
    count: str                       # the query builder's column: sixes, fours, runs, wickets, dots
    who: str = "batter"              # batter | bowler
    phase: Optional[str] = None      # pp (overs 1-6) | death (16-20); None = every ball
    by_position: bool = False        # one leaderboard per batting position
    step: int = 50                   # milestones every `step` (100 sixes, 150...)
    min_milestone: int = 50



TEMPLATES: Tuple[Template, ...] = (
    Template("sixes", "sixes", "sixes"),
    Template("runs", "runs", "runs", step=1000, min_milestone=1000),
    Template("fours", "fours", "fours", step=100, min_milestone=100),
    Template("pp-sixes", "powerplay sixes", "sixes", phase="pp"),
    Template("pp-runs", "powerplay runs", "runs", phase="pp", step=500, min_milestone=500),
    Template("death-sixes", "death-overs sixes", "sixes", phase="death"),
    Template("pos-sixes", "sixes batting at {pos}", "sixes", by_position=True),
    Template("pos-runs", "runs batting at {pos}", "runs", by_position=True, step=1000, min_milestone=1000),
    Template("wickets", "wickets", "wickets", who="bowler", step=50, min_milestone=50),
    Template("pp-wickets", "powerplay wickets", "wickets", who="bowler", phase="pp", step=25, min_milestone=25),
    Template("death-wickets", "death-overs wickets", "wickets", who="bowler", phase="death", step=25, min_milestone=25),
)


@dataclass
class Scope:
    id: str
    label: str                       # "in T20Is", "in the IPL", "for India in T20Is", "in men's T20s"
    args: Dict[str, Any] = field(default_factory=dict)


def scopes_for(db, matches: List[Dict[str, Any]]) -> List[Scope]:
    """Every scope the day's matches count towards: their competitions, each T20I side, and all men's T20s."""
    from services.competition_aliases import canonical_competition, variants_for
    from services.competition_normalizer import international_competitions

    out: Dict[str, Scope] = {"all": Scope("all", "in men's T20s", {})}
    intl = set(international_competitions("T20"))
    for m in matches:
        comp = m["competition"]
        if comp in intl:
            out["t20i"] = Scope("t20i", "in T20Is", {"t20i": True})
            for team in (m["team1"], m["team2"]):
                out[f"t20i:{team}"] = Scope(f"t20i:{team}", f"for {team} in T20Is",
                                            {"t20i": True, "team": team})
        else:
            name = canonical_competition(comp) or comp
            out[f"league:{name}"] = Scope(f"league:{name}", f"in the {name}" if len(name) <= 5 else f"in {name}",
                                          {"comps": set(variants_for(name))})
    return list(out.values())


def day_matches(db, day: date) -> List[Dict[str, Any]]:
    rows = db.execute(text("""
        SELECT id, date, team1, team2, competition FROM matches
        WHERE date = :d AND format = 'T20' AND gender = 'male'
    """), {"d": day}).mappings().all()
    return [dict(r) for r in rows]


BOWLER_WICKETS = ("bowled", "caught", "lbw", "leg before wicket", "caught and bowled", "stumped", "hit wicket")
LEGACY_BEFORE = date(2015, 1, 1)


def cube(db, who: str, day: date) -> List[Dict[str, Any]]:
    """Every ball up to `day`, summed by (name, team, comp, t20i, phase, pos, today): batting -> runs, sixes, fours;
    bowling -> wickets. pos is the batting position (order of first ball faced in the innings); phase pp | mid | death."""
    from services.competition_normalizer import international_competitions
    from services.player_aliases import ALIAS_MAP_CTE

    bat = who == "batter"
    nm, lnm = ("dd.bat", "d.batter") if bat else ("dd.bowl", "d.bowler")
    tm, ltm = ("dd.team_bat", "d.batting_team") if bat else ("dd.team_bowl", "d.bowling_team")
    amt = "COALESCE(dd.batruns, 0)" if bat else \
        "CASE WHEN LOWER(COALESCE(dd.out::text, '')) = 'true' AND LOWER(COALESCE(dd.dismissal, '')) = ANY(:wk) THEN 1 ELSE 0 END"
    lamt = "COALESCE(d.runs_off_bat, 0)" if bat else "CASE WHEN LOWER(COALESCE(d.wicket_type, '')) = ANY(:wk) THEN 1 ELSE 0 END"
    sums = ("SUM(b.amt) AS runs, SUM(CASE WHEN b.amt = 6 THEN 1 ELSE 0 END) AS sixes, "
            "SUM(CASE WHEN b.amt = 4 THEN 1 ELSE 0 END) AS fours") if bat else "SUM(b.amt) AS wickets"
    # The batting position, from the order batters first faced a ball in the innings (bowling has none).
    pos = ("JOIN (SELECT mid, inns, name, RANK() OVER (PARTITION BY mid, inns ORDER BY MIN(o * 100 + bl)) AS pos "
           "FROM balls GROUP BY mid, inns, name) p USING (mid, inns, name)") if bat else ""
    rows = db.execute(text(f"""
        WITH {ALIAS_MAP_CTE},
        balls AS (
            SELECT COALESCE(am.canonical_name, {nm}) AS name, {tm} AS team, m.id::text AS mid, m.date, m.competition AS comp,
                   (m.match_type = 'international' AND m.competition = ANY(:intl)) AS t20i, dd.inns, dd.over AS o,
                   dd.ball AS bl, {amt} AS amt
            FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
            LEFT JOIN alias_map am ON LOWER({nm}) = am.name_key
            WHERE m.format = 'T20' AND m.gender = 'male' AND m.date <= :day
            UNION ALL
            SELECT COALESCE(am.canonical_name, {lnm}), {ltm}, m.id::text, m.date, m.competition,
                   (m.match_type = 'international' AND m.competition = ANY(:intl)), d.innings, d.over, d.ball, {lamt}
            FROM deliveries d JOIN matches m ON m.id = d.match_id
            LEFT JOIN alias_map am ON LOWER({lnm}) = am.name_key
            WHERE m.format = 'T20' AND m.gender = 'male' AND m.date < :legacy
        )
        SELECT b.name, b.team, b.comp, b.t20i,
               CASE WHEN b.o < 6 THEN 'pp' WHEN b.o >= 15 THEN 'death' ELSE 'mid' END AS phase,
               {"p.pos" if bat else "NULL::int"} AS pos, (b.date = :day) AS today, {sums}
        FROM balls b {pos}
        GROUP BY 1, 2, 3, 4, 5, 6, 7
    """), {"intl": international_competitions("T20"), "day": day, "legacy": LEGACY_BEFORE,
           "wk": list(BOWLER_WICKETS)}).mappings().all()
    return [dict(r) for r in rows]


def _in_scope(r: Dict[str, Any], scope: Scope) -> bool:
    a = scope.args
    if a.get("t20i") and not r["t20i"]:
        return False
    if a.get("team") and r["team"] != a["team"]:
        return False
    if a.get("comps") is not None and r["comp"] not in a["comps"]:
        return False
    return True


def _boards(t: Template, rows: List[Dict[str, Any]], scope: Scope, today_only: bool) -> Dict[Any, Dict[str, int]]:
    """{position or None: {player: count}} for the template in the scope (only the day's balls with today_only)."""
    out: Dict[Any, Dict[str, int]] = {}
    for r in rows:
        if (today_only and not r["today"]) or (t.phase and r["phase"] != t.phase) or not _in_scope(r, scope):
            continue
        key = r["pos"] if t.by_position else None
        if t.by_position and key is None:
            continue
        board = out.setdefault(key, {})
        board[r["name"]] = board.get(r["name"], 0) + int(r[t.count] or 0)
    return out


def _rank(board: Dict[str, int], player: str) -> int:
    mine = board.get(player, 0)
    return 1 + sum(1 for v in board.values() if v > mine)


def events_for(rows: List[Dict[str, Any]], t: Template, scope: Scope, day: date) -> List[Dict[str, Any]]:
    after = _boards(t, rows, scope, False)
    today = _boards(t, rows, scope, True)
    out = []
    for key, gained in today.items():
        board = after.get(key) or {}
        before = {p: v - gained.get(p, 0) for p, v in board.items()}
        label = t.label.format(pos=key) if t.by_position else t.label
        for player, add in gained.items():
            if add <= 0 or player not in board:
                continue
            now, was = board[player], before[player]
            r_now, r_was = _rank(board, player), _rank(before, player)
            base = {"template": t.id, "label": label, "scope": scope.id, "scope_label": scope.label, "player": player,
                    "before": was, "after": now, "rank_before": r_was, "rank_after": r_now, "day": day.isoformat(),
                    "position": key}
            if t.by_position and (key or 99) > MAX_POS:
                continue
            # A leaderboard move only counts at a size worth a record (the template's first milestone).
            if r_now <= TOP_N and now >= t.min_milestone:
                passed = sorted((p for p, v in board.items() if p != player and was <= before[p] < now and v < now),
                                key=lambda p: -board[p])
                level = [p for p, v in board.items() if p != player and v == now and before[p] >= was and before[p] != was]
                if passed or level:
                    out.append({**base, "kind": "passed", "passed": [(p, board[p]) for p in passed][:3],
                                "level": [(p, board[p]) for p in level][:2]})
                elif r_was > TOP_N:
                    out.append({**base, "kind": "entered"})
            m = (now // t.step) * t.step
            if m >= t.min_milestone and was < m <= now:
                nth = 1 + sum(1 for p, v in before.items() if p != player and v >= m)
                if nth <= MAX_NTH:
                    out.append({**base, "kind": "milestone", "milestone": m, "nth": nth})
    return out


def run_day(db, day: date, templates: Tuple[Template, ...] = TEMPLATES) -> List[Dict[str, Any]]:
    matches = day_matches(db, day)
    if not matches:
        return []
    cubes = {who: cube(db, who, day) for who in {t.who for t in templates}}
    out = []
    for scope in scopes_for(db, matches):
        for t in templates:
            out.extend(events_for(cubes[t.who], t, scope, day))
    return out


def headline(e: Dict[str, Any]) -> str:
    """The event in one line, player and number first."""
    from services.records import ordinal

    p, label, where = e["player"], e["label"], e["scope_label"]
    if e["kind"] == "milestone":
        nth = "" if e["nth"] == 1 else f", the {ordinal(e['nth'])} to get there"
        first = " first" if e["nth"] == 1 else ""
        return f"{p} reaches {e['milestone']:,} {label} {where}" + (", the first to get there" if first else nth)
    if e["kind"] == "passed":
        if e["rank_after"] == 1 and e["passed"]:
            return f"{p} now has the most {label} {where}: {e['after']:,}, past {e['passed'][0][0]} ({e['passed'][0][1]:,})"
        names = ", ".join(f"{n} ({v:,})" for n, v in e["passed"]) if e["passed"] else ""
        lvl = f", level with {e['level'][0][0]}" if e["level"] and not names else ""
        return (f"{p} moves to {ordinal(e['rank_after'])} for {label} {where} with {e['after']:,}"
                + (f", past {names}" if names else "") + lvl)
    return f"{p} enters the top {TOP_N} for {label} {where}: {ordinal(e['rank_after'])} with {e['after']:,}"
