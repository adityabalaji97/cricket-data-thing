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
          -- Only finished matches: the nightly file can hold a match cut off mid-innings (no winner, no outcome yet);
          -- counting it would draft records from half a game and mark the day done before the rest arrives.
          AND (winner IS NOT NULL OR outcome IS NOT NULL)
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
    pid = "dd.p_bat" if bat else "dd.p_bowl"
    tm, ltm = ("dd.team_bat", "d.batting_team") if bat else ("dd.team_bowl", "d.bowling_team")
    amt = "COALESCE(dd.batruns, 0)" if bat else \
        "CASE WHEN LOWER(COALESCE(dd.out::text, '')) = 'true' AND LOWER(COALESCE(dd.dismissal, '')) = ANY(:wk) THEN 1 ELSE 0 END"
    lamt = "COALESCE(d.runs_off_bat, 0)" if bat else "CASE WHEN LOWER(COALESCE(d.wicket_type, '')) = ANY(:wk) THEN 1 ELSE 0 END"
    sums = ("SUM(b.amt) AS runs, SUM(CASE WHEN b.amt = 6 THEN 1 ELSE 0 END) AS sixes, "
            "SUM(CASE WHEN b.amt = 4 THEN 1 ELSE 0 END) AS fours") if bat else "SUM(b.amt) AS wickets"
    # The batting position, from the order batters first faced a ball in the innings (bowling has none).
    pos = ("JOIN (SELECT mid, inns, name, RANK() OVER (PARTITION BY mid, inns ORDER BY MIN(o * 100 + bl)) AS pos "
           "FROM balls GROUP BY mid, inns, name) p USING (mid, inns, name)") if bat else ""  # one name per innings
    rows = db.execute(text(f"""
        WITH {ALIAS_MAP_CTE},
        balls AS (
            SELECT {pid} AS pid, COALESCE(am.canonical_name, {nm}) AS name, {tm} AS team, m.id::text AS mid, m.date, m.competition AS comp,
                   (m.match_type = 'international' AND m.competition = ANY(:intl)) AS t20i, dd.inns, dd.over AS o,
                   dd.ball AS bl, {amt} AS amt
            FROM delivery_details dd JOIN matches m ON m.id = dd.p_match
            LEFT JOIN alias_map am ON LOWER({nm}) = am.name_key
            WHERE m.format = 'T20' AND m.gender = 'male' AND m.date <= :day
            UNION ALL
            SELECT NULL::bigint, COALESCE(am.canonical_name, {lnm}), {ltm}, m.id::text, m.date, m.competition,
                   (m.match_type = 'international' AND m.competition = ANY(:intl)), d.innings, d.over, d.ball, {lamt}
            FROM deliveries d JOIN matches m ON m.id = d.match_id
            LEFT JOIN alias_map am ON LOWER({lnm}) = am.name_key
            WHERE m.format = 'T20' AND m.gender = 'male' AND m.date < :legacy
        )
        SELECT b.pid, b.name, b.team, b.comp, b.t20i,
               CASE WHEN b.o < 6 THEN 'pp' WHEN b.o >= 15 THEN 'death' ELSE 'mid' END AS phase,
               {"p.pos" if bat else "NULL::int"} AS pos, (b.date = :day) AS today, {sums}
        FROM balls b {pos}
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    """), {"intl": international_competitions("T20"), "day": day, "legacy": LEGACY_BEFORE,
           "wk": list(BOWLER_WICKETS)}).mappings().all()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------------------------
# Who is who: by ESPNcricinfo player id (delivery_details.p_bat / p_bowl), not by name. Names collide: India's,
# Indonesia's and Haryana's Rohit Sharma are three players (34102, 1542004, 934943), and counting by name gave India's
# Rohit Indonesia's three powerplay sixes (101, not 98). Each id gets one display name; where ids share a name, the one
# with the most balls keeps it and the others carry their main side: "Rohit Sharma (Indonesia)". Balls before 2015
# (the legacy table) have no ids and go by name to that name's main player.
# --------------------------------------------------------------------------------------------


def identities(db) -> Tuple[Dict[int, str], Dict[str, str]]:
    """({player id: display name}, {name: display name of its main player}): the stored player_identity table
    (services/player_identity.py, rebuilt nightly), or computed here when it's empty."""
    from services import player_identity

    try:
        display, main = player_identity.load(db)
        if display:
            return display, main
    except Exception:  # the table isn't there (a database before migration 026)
        db.rollback()
    from services.competition_normalizer import international_competitions
    from services.player_aliases import ALIAS_MAP_CTE

    rows = db.execute(text(f"""
        WITH {ALIAS_MAP_CTE}, b AS (
            SELECT dd.p_bat AS pid, COALESCE(am.canonical_name, dd.bat) AS name, dd.team_bat AS team,
                   (m.match_type = 'international' AND m.competition = ANY(:intl)) AS t20i
            FROM delivery_details dd JOIN matches m ON m.id = dd.p_match LEFT JOIN alias_map am ON LOWER(dd.bat) = am.name_key
            WHERE m.format = 'T20' AND m.gender = 'male' AND dd.p_bat IS NOT NULL
            UNION ALL
            SELECT dd.p_bowl, COALESCE(am.canonical_name, dd.bowl), dd.team_bowl,
                   (m.match_type = 'international' AND m.competition = ANY(:intl))
            FROM delivery_details dd JOIN matches m ON m.id = dd.p_match LEFT JOIN alias_map am ON LOWER(dd.bowl) = am.name_key
            WHERE m.format = 'T20' AND m.gender = 'male' AND dd.p_bowl IS NOT NULL
        )
        SELECT pid, name, team, t20i, COUNT(*) FROM b GROUP BY 1, 2, 3, 4
    """), {"intl": international_competitions("T20")}).all()
    names: Dict[int, Dict[str, int]] = {}
    teams: Dict[int, Dict[Tuple[str, bool], int]] = {}
    for pid, name, team, t20i, n in rows:
        names.setdefault(pid, {})[name] = names.setdefault(pid, {}).get(name, 0) + n
        teams.setdefault(pid, {})[(team, bool(t20i))] = n + teams.setdefault(pid, {}).get((team, bool(t20i)), 0)
    canonical = {pid: max(ns, key=ns.get) for pid, ns in names.items()}
    balls = {pid: sum(ns.values()) for pid, ns in names.items()}

    def side(pid: int) -> str:
        t = teams[pid]
        national = {k: v for k, v in t.items() if k[1]}
        return max(national or t, key=(national or t).get)[0]

    by_name: Dict[str, List[int]] = {}
    for pid, name in canonical.items():
        by_name.setdefault(name, []).append(pid)
    display: Dict[int, str] = {}
    main: Dict[str, str] = {}
    for name, pids in by_name.items():
        pids.sort(key=lambda p: -balls[p])
        main[name] = name
        display[pids[0]] = name
        for p in pids[1:]:
            display[p] = f"{name} ({side(p)})"
    return display, main


def with_identities(rows: List[Dict[str, Any]], display: Dict[int, str], main: Dict[str, str]) -> List[Dict[str, Any]]:
    """The counts table under each player's display name: by id where the ball has one, else by name."""
    return [{**r, "name": display.get(r["pid"], r["name"]) if r.get("pid") is not None else main.get(r["name"], r["name"])}
            for r in rows]


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
    display, main = identities(db)
    cubes = {who: with_identities(cube(db, who, day), display, main) for who in {t.who for t in templates}}
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


# --------------------------------------------------------------------------------------------
# Chunk 4: which events become drafts (at most 3 a day, on the bench for the user to pick)
# --------------------------------------------------------------------------------------------

DAILY_CAP = 3
MAJOR_LEAGUES = {"IPL", "BBL", "PSL", "CPL", "SA20", "Men's Hundred", "T20 Blast", "MLC", "ILT20", "BPL", "LPL"}
TEMPLATE_WEIGHT = {"sixes": 1.3, "runs": 1.3, "wickets": 1.3, "pp-sixes": 1.2, "death-sixes": 1.1, "pp-wickets": 1.1,
                   "death-wickets": 1.1, "pos-sixes": 1.0, "pos-runs": 1.0, "fours": 0.9, "pp-runs": 0.9}


def _scope_weight(scope_id: str) -> float:
    if scope_id in ("all", "t20i"):
        return 1.3
    if scope_id.startswith("league:"):
        return 1.15 if scope_id.split(":", 1)[1] in MAJOR_LEAGUES else 0.6
    # One side's T20Is: a top-12 side's list is a story for most readers, an associate side's less so (still in,
    # labelled; decision 1).
    from models import INTERNATIONAL_TEAMS_RANKED

    return 0.9 if scope_id.split(":", 1)[1] in INTERNATIONAL_TEAMS_RANKED[:12] else 0.45


def _kind_weight(e: Dict[str, Any]) -> float:
    if e["kind"] == "passed":
        return 3.0 if e["rank_after"] == 1 else 2.0 if e["rank_after"] <= 3 else 1.2
    if e["kind"] == "milestone":
        return 2.5 if e["nth"] == 1 else 1.6 if e["nth"] <= 5 else 1.0
    return 1.0  # entered the top 10


def fame(cubes: Dict[str, List[Dict[str, Any]]]) -> Dict[str, float]:
    """How well known a player is, from his career in the data: 0.4 + up to 1 for runs (5,000) + up to 1 for wickets
    (200). Associates are in (decision 1); a long career anywhere ranks them, a short one doesn't."""
    runs: Dict[str, int] = {}
    wkts: Dict[str, int] = {}
    for r in cubes.get("batter", []):
        runs[r["name"]] = runs.get(r["name"], 0) + int(r["runs"] or 0)
    for r in cubes.get("bowler", []):
        wkts[r["name"]] = wkts.get(r["name"], 0) + int(r["wickets"] or 0)
    return {n: 0.4 + min(1.0, runs.get(n, 0) / 5000) + min(1.0, wkts.get(n, 0) / 200) for n in set(runs) | set(wkts)}


def score(e: Dict[str, Any], fame_of: Dict[str, float]) -> float:
    return round(_kind_weight(e) * _scope_weight(e["scope"]) * TEMPLATE_WEIGHT.get(e["template"], 1.0)
                 * fame_of.get(e["player"], 0.4), 3)


def pick(events: List[Dict[str, Any]], fame_of: Dict[str, float], k: int = DAILY_CAP) -> List[Dict[str, Any]]:
    """The best k events, one per player (three stories, not one player three times)."""
    out, seen = [], set()
    for e in sorted(events, key=lambda e: -score(e, fame_of)):
        if e["player"] in seen:
            continue
        seen.add(e["player"])
        out.append({**e, "score": score(e, fame_of)})
        if len(out) == k:
            break
    return out


def leaderboard(rows: List[Dict[str, Any]], e: Dict[str, Any], top: int = 8) -> List[Tuple[str, int]]:
    t = next(t for t in TEMPLATES if t.id == e["template"])
    scope = _scope_of(e)
    board = _boards(t, rows, scope, False).get(e["position"]) or {}
    ranked = sorted(board.items(), key=lambda kv: (-kv[1], kv[0]))
    out = ranked[:top]
    if e["player"] not in dict(out):
        out = out[: top - 1] + [(e["player"], board.get(e["player"], 0))]
    return out


def _scope_of(e: Dict[str, Any]) -> Scope:
    sid = e["scope"]
    if sid == "all":
        return Scope("all", e["scope_label"], {})
    if sid == "t20i":
        return Scope("t20i", e["scope_label"], {"t20i": True})
    if sid.startswith("t20i:"):
        return Scope(sid, e["scope_label"], {"t20i": True, "team": sid.split(":", 1)[1]})
    from services.competition_aliases import variants_for

    return Scope(sid, e["scope_label"], {"comps": set(variants_for(sid.split(":", 1)[1]))})


def query_params(e: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """The query builder's version of the leaderboard (for the post's link)."""
    t = next(t for t in TEMPLATES if t.id == e["template"])
    sid = e["scope"]
    p: Dict[str, Any] = {"metrics_perspective": "batting" if t.who == "batter" else "bowling"}
    if sid == "all":
        p.update(leagues=[], include_international=False)
    elif sid.startswith("t20i"):
        p.update(include_international=True)
        if ":" in sid:
            p["batting_teams" if t.who == "batter" else "bowling_teams"] = [sid.split(":", 1)[1]]
    else:
        p.update(leagues=[sid.split(":", 1)[1]])
    if t.phase == "pp":
        p["over_max"] = 5
    elif t.phase == "death":
        p["over_min"] = 15
    return p, [t.who] + (["batting_position"] if t.by_position else [])


def post_for(db, e: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """A queueable post: hook, the leaderboard (the player in lime, the passed in the list), the end slide."""
    from services import ig_captions, ig_carousel
    from services.ig_links import query_path

    t = next(t for t in TEMPLATES if t.id == e["template"])
    hook = headline(e)
    board = leaderboard(rows, e)
    count_word = t.label.format(pos=e["position"]) if t.by_position else t.label
    passed = {n for n, _ in e.get("passed") or []}
    level = {n for n, _ in e.get("level") or []}
    d = date.fromisoformat(e["day"])
    when = f"{d.day} {d.strftime('%b')}"
    card_rows = [{"name": n, "value": v, "highlight": n == e["player"],
                  "detail": (f"{e['before']:,} before {when}" if n == e["player"] else
                             "passed" if n in passed else "level" if n in level else "")}
                 for n, v in board]
    card = {"id": "board", "visual": "metric_bars", "title": hook,
            "help": "", "sample": f"Most {count_word} {e['scope_label']}, to {when} {d.year} · associates included",
            "payload": {"metric": {"label": count_word.capitalize(), "format": "int", "signed": False},
                        "rows": card_rows, "label_width": 140}}
    slides = [{"type": "hook", "text": hook, "kicker": f"Record radar · {e['scope_label'].split(' ', 1)[1]}",
               "sub": "Where he now stands"},
              {"type": "card", "card": card, "teams": None},
              {"type": "end", "heading": "Find your player", "body": "Every leaderboard is free in the query builder."}]
    key = f"record-{e['template']}-{e['scope'].replace(':', '-')}-{e['player'].replace(' ', '-').lower()}-{e['day']}"
    carousel = ig_carousel.save(db, slides, hook, {"radar": key}, "record-radar")
    params, group_by = query_params(e)
    fact = {"kind": "record", "title": hook, "hook": hook, "subject": e["player"], "subject_role": "player",
            "event": {k: v for k, v in e.items() if k != "score"}, "score": e.get("score"),
            "link": query_path(params, group_by), "carousel_id": carousel["id"], "slides": len(slides), "render": True}
    caption = ig_captions.build(hook, "", "record", None, [e["player"]], "Record radar",
                                body=[f"Most {count_word} {e['scope_label']}: " + ", ".join(f"{n} {v:,}" for n, v in board[:3]) + "."])
    return {"key": key, "pillar": "reactive", "fact": fact, "snapshot_id": carousel["id"], "warnings": [],
            "players": [e["player"]], "caption": caption}


def drafts_for_day(db, day: date, k: int = DAILY_CAP) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """The day's best k events (scored) and the counts tables they came from."""
    matches = day_matches(db, day)
    if not matches:
        return [], {}
    display, main = identities(db)
    cubes = {who: with_identities(cube(db, who, day), display, main) for who in ("batter", "bowler")}
    events = []
    for scope in scopes_for(db, matches):
        for t in TEMPLATES:
            events.extend(events_for(cubes[t.who], t, scope, day))
    return pick(events, fame(cubes), k), cubes
