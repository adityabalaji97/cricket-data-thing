"""
Matches the ball-by-ball feed caught part-way and never finished (NZ v India, Oct 2026: 118 and 103 balls of the first
innings, no result), healed from Cricsheet, and handed back to the feed when it catches up.

    stuck(db, match)                       -> True when we hold a feed match Cricsheet has with more legal balls
    dd_rows(match, name_of, pid_of, meta)  -> the Cricsheet balls as delivery_details rows (the feed's conventions)
    heal(session, match, name_of, pid_of)  -> replace the partial feed rows with Cricsheet's; data_source 'cricsheet_dd'
    feed_caught_up(feed_legal, ours_legal) -> the feed has at least as many legal balls as we hold (hand it back)

A healed match is in delivery_details like any other, so the query builder, the stats and the Primer metrics (Impact,
win probability: computed from the balls by compute_primer_metrics.py, the next nightly step) all see it. What Cricsheet
lacks is the feed's tagging: line, length, shot, control, wagon wheel. When the feed's file later has the match with at
least as many legal balls, scripts/load_delivery_details_pipeline.py (step 2d) swaps the feed's rows back in and the
nightly steps rebuild stats, metrics and partnerships from them. Until then the feed's partial rows can't come back:
they share (p_match, inns, over, ball) with the healed rows, the loader's duplicate key.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Optional

from sqlalchemy import text

HEALED = "cricsheet_dd"
DISMISSALS = {"lbw": "leg before wicket", "caught and bowled": "caught", "retired hurt": "retired not out (hurt)"}
NOT_BOWLERS = {"run out", "retired hurt", "retired out", "obstructing the field", "retired not out (hurt)"}


def _legal(b: Dict) -> bool:
    extras = b.get("extras") or {}
    return not extras.get("wides") and not extras.get("noballs")


def legal_balls(match) -> int:
    return sum(_legal(b) for _, inn in match.innings() for over in inn.get("overs", []) for b in over["deliveries"])


def ours_legal(db, match_id: str) -> int:
    return db.execute(text("""SELECT COUNT(*) FROM delivery_details
                              WHERE p_match = :m AND COALESCE(wide, 0) = 0 AND COALESCE(noball, 0) = 0"""),
                      {"m": str(match_id)}).scalar() or 0


def stuck(db, match) -> bool:
    """A feed match (data_source 'bbb') Cricsheet has with more legal balls: the feed caught it part-way."""
    src = db.execute(text("SELECT data_source FROM matches WHERE id = :m"), {"m": match.match_id}).scalar()
    return src == "bbb" and legal_balls(match) > ours_legal(db, match.match_id)


def feed_caught_up(feed_legal: int, ours: int) -> bool:
    return feed_legal >= ours > 0


def _result(match) -> Optional[str]:
    return ((match.info.get("outcome") or {}).get("winner"))


def dd_rows(match, name_of: Callable, pid_of: Callable, meta: Dict, hands: Dict[str, Dict]) -> List[Dict]:
    """Cricsheet balls as delivery_details rows: over from 0, ball counting every delivery in the over (wides and
    no-balls too), running innings/batter/bowler figures after each ball, the target and what's left of the chase.
    meta: the match columns (match_date, ground, country, competition, toss, tournament, season, daynight...);
    hands: name -> {bat_hand, bowl_style, bowl_kind}."""
    from team_standardization import TEAM_RAW_TO_CANONICAL

    canonical_team = lambda n: TEAM_RAW_TO_CANONICAL.get(n, n) if n else n  # noqa: E731
    teams = [canonical_team(t) for t in match.info["teams"]]
    max_balls = int(match.info.get("overs") or 20) * 6
    winner = _result(match)
    rows, first_total = [], None
    for inns_no, inn in match.innings():
        team_bat = canonical_team(inn["team"])
        team_bowl = next((t for t in teams if t != team_bat), None)
        target = (first_total + 1) if inns_no == 2 and first_total is not None else None
        runs = wkts = legal = 0
        bat = defaultdict(lambda: [0, 0])                  # name -> [runs, balls faced]
        bowl = defaultdict(lambda: [0, 0, 0])              # name -> [legal balls, runs, wickets]
        for over in inn.get("overs", []):
            for ball_no, b in enumerate(over["deliveries"], 1):
                extras = b.get("extras") or {}
                wicket = (b.get("wickets") or [None])[0]
                penalty = extras.get("penalty", 0)
                score = b["runs"]["total"] - penalty
                batter, bowler, ns = name_of(b["batter"]), name_of(b["bowler"]), name_of(b.get("non_striker"))
                is_legal = _legal(b)
                runs += score
                legal += is_legal
                wkts += 1 if wicket and wicket.get("kind") not in ("retired hurt",) else 0
                bat[batter][0] += b["runs"]["batter"]
                bat[batter][1] += 0 if extras.get("wides") else 1
                bowler_runs = score - extras.get("byes", 0) - extras.get("legbyes", 0)
                bw = bowl[bowler]
                bw[0] += is_legal
                bw[1] += bowler_runs
                bw[2] += 1 if wicket and wicket.get("kind") not in NOT_BOWLERS else 0
                kind = wicket["kind"] if wicket else None
                h_bat, h_bowl = hands.get(batter, {}), hands.get(bowler, {})
                rows.append({
                    "p_match": match.match_id, "match_id": match.match_id, "inns": inns_no, "innings": inns_no,
                    "over": over["over"], "ball": ball_no, "ball_id": float(f"{over['over']}.{ball_no}"),
                    "bat": batter, "batter": batter, "p_bat": pid_of(b["batter"]), "non_striker": ns,
                    "bowl": bowler, "bowler": bowler, "p_bowl": pid_of(b["bowler"]),
                    "team_bat": team_bat, "batting_team": team_bat, "team_bowl": team_bowl, "bowling_team": team_bowl,
                    "score": score, "batruns": b["runs"]["batter"], "bowlruns": bowler_runs,
                    "ballfaced": 0 if extras.get("wides") else 1,
                    "noball": extras.get("noballs", 0), "wide": extras.get("wides", 0),
                    "byes": extras.get("byes", 0), "legbyes": extras.get("legbyes", 0),
                    "out": "true" if wicket else "false",
                    "bat_out": "true" if wicket and wicket.get("player_out") == b["batter"] else "false",
                    "dismissal": DISMISSALS.get(kind, kind) if kind else None,
                    "p_out": pid_of(wicket.get("player_out")) if wicket else None,
                    "outcome": _outcome(b, extras, wicket),
                    "cur_bat_runs": bat[batter][0], "cur_bat_bf": bat[batter][1],
                    "cur_bowl_ovr": float(f"{bw[0] // 6}.{bw[0] % 6}"), "cur_bowl_runs": bw[1], "cur_bowl_wkts": bw[2],
                    "inns_runs": runs, "inns_wkts": wkts, "inns_balls": legal,
                    "inns_balls_rem": max_balls - legal, "max_balls": max_balls,
                    "target": str(target) if target else None,
                    "inns_runs_rem": str(target - runs) if target else None,
                    "inns_rr": round(6 * runs / legal, 2) if legal else None,
                    "inns_rrr": (str(round(6 * (target - runs) / (max_balls - legal), 2))
                                 if target and max_balls > legal else None),
                    "winner": winner,
                    "bat_hand": h_bat.get("bat_hand"), "bowl_style": h_bowl.get("bowl_style"),
                    "bowl_kind": h_bowl.get("bowl_kind"),
                    **meta,
                })
        if inns_no == 1:
            first_total = runs
    return rows


def _outcome(b: Dict, extras: Dict, wicket: Optional[Dict]) -> str:
    if wicket:
        return "out"
    if extras.get("wides"):
        return "wide"
    if extras.get("noballs"):
        return "no ball"
    runs = b["runs"]["batter"]
    if runs in (4, 6):
        return "four" if runs == 4 else "six"
    if extras.get("legbyes"):
        return "leg bye"
    if extras.get("byes"):
        return "bye"
    return "run" if runs else "no run"


META = ("match_date", "year", "ground", "country", "competition", "toss", "tournament", "season", "daynight",
        "trophy_name", "format", "gender", "date")


def heal(session, match, name_of: Callable, pid_of: Callable) -> Dict:
    """Replace a stuck feed match's rows with Cricsheet's: its delivery_details rows, stats, Primer metrics and
    partnership stands go (the nightly steps rebuild the last three; the stats are rebuilt here), the matches row
    takes Cricsheet's result and data_source 'cricsheet_dd'. One transaction."""
    from sync_stats_from_dd import StatsFromDeliveryDetails

    mid = match.match_id
    first = session.execute(text(f"SELECT {', '.join(META)} FROM delivery_details WHERE p_match = :m LIMIT 1"),
                            {"m": mid}).mappings().first() or {}
    meta = {k: first.get(k) for k in META}
    # Batting hand and bowling style: as the feed had them for these players (in this match, else their latest).
    names = {name_of(n) for n in match.player_ids()}
    hands: Dict[str, Dict] = {}
    for r in session.execute(text("""
            SELECT DISTINCT ON (bat) bat, bat_hand FROM delivery_details WHERE bat = ANY(:n) AND bat_hand IS NOT NULL
            ORDER BY bat, match_date DESC"""), {"n": list(names)}):
        hands.setdefault(r[0], {})["bat_hand"] = r[1]
    for r in session.execute(text("""
            SELECT DISTINCT ON (bowl) bowl, bowl_style, bowl_kind FROM delivery_details
            WHERE bowl = ANY(:n) AND bowl_style IS NOT NULL ORDER BY bowl, match_date DESC"""), {"n": list(names)}):
        hands.setdefault(r[0], {}).update(bowl_style=r[1], bowl_kind=r[2])
    rows = dd_rows(match, name_of, pid_of, meta, hands)
    before = ours_legal(session, mid)
    for table, col in (("ball_metrics", "p_match"), ("partnership_stands", "p_match"), ("batting_stats", "match_id"),
                       ("bowling_stats", "match_id"), ("delivery_details", "p_match")):
        session.execute(text(f"DELETE FROM {table} WHERE {col}::text = :m"), {"m": mid})
    cols = sorted({k for r in rows for k in r})
    session.execute(text(f"INSERT INTO delivery_details ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"),
                    [{c: r.get(c) for c in cols} for r in rows])
    winner = _result(match)
    outcome = match.info.get("outcome") or {}
    session.execute(text("""UPDATE matches SET data_source = :src, winner = COALESCE(:w, winner),
                            outcome = COALESCE(CAST(:o AS json), outcome) WHERE id = :m"""),
                    {"src": HEALED, "w": winner, "o": __import__("json").dumps(outcome) if outcome else None, "m": mid})
    stats = StatsFromDeliveryDetails().process_match_stats(session, mid)
    return {"match": mid, "legal_before": before, "legal_after": legal_balls(match), "rows": len(rows), **stats}
