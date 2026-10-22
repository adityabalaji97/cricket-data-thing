"""
On this day: the daily look back. Picks the best story among the men's T20s played on today's month and day in past
years (2015 on, when Impact and win probability start), and builds it as a carousel (ON_THIS_DAY_PLAN.md, chunks 1-2).

    candidates(db, day)          -> every eligible match on that calendar day, with its story numbers and a score
    pick(db, day, avoid=())      -> the best candidate (competitions in `avoid` lose out to anything comparable)
    post(db, day, avoid=())      -> {hook, sub, kicker, cards, title, verdict, players, teams, day, caption, ...} or None

The story score, every number from ball_metrics / the scorecard service:
  stage        the match's place: IPL, or a T20I between two of the top 12, counts most; the big leagues next
  performance  the match's biggest Impact (batting or bowling), as the scorecard counts it
  comeback     the loser's peak win probability (a side at 90% that lost is a story)
  final        a league final or playoff (inferred: an unnumbered match at the end of a season whose league matches
               are numbered)
  anniversary  a round number of years ago (5, 10, 15, 20)

The carousel: the hook (the year and the story), How it was won, where the performance ranks in the competition's
history, the loser's win probability with its swing overs, the score race, and the Impact scorecards.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.ig_posts.cards import card, fmt

FIRST_YEAR = 2015
TOP_FULL = 12
BIG_LEAGUES = ("IPL", "BBL", "PSL", "CPL", "SA20", "The Hundred", "T20 Blast", "LPL", "BPL", "ILT20", "MLC")
STAGE = {"top": 1.0, "big": 0.65, "other": 0.3}
IMPACT_FULL = 40.0      # an Impact this big is a full-strength performance story
COMEBACK_FROM = 75.0    # the loser's peak win probability at which a comeback starts to count
RANK_ROWS = 8
ROUND_YEARS = (5, 10, 15, 20)


def _comp_key(row: Dict[str, Any]) -> str:
    from services.recent_matches import _canonical_competition_key

    if row["match_type"] == "international":
        return "T20I"
    return _canonical_competition_key(row["competition"]) or row["competition"]


def _stage(row: Dict[str, Any], key: str) -> str:
    from models import INTERNATIONAL_TEAMS_RANKED

    if key == "IPL":
        return "top"
    if key == "T20I":
        top = set(INTERNATIONAL_TEAMS_RANKED[:TOP_FULL])
        return "top" if row["team1"] in top and row["team2"] in top else "other"
    return "big" if key in BIG_LEAGUES else "other"


def candidates(db: Session, day: date) -> List[Dict[str, Any]]:
    from models import INTERNATIONAL_TEAMS_RANKED
    from services.match_browse import top_impact

    rows = [dict(r) for r in db.execute(text("""
        SELECT m.id, m.date, m.team1, m.team2, m.winner, m.venue, m.competition, m.match_type, m.event_match_number,
               NOT EXISTS (SELECT 1 FROM matches n WHERE n.competition = m.competition AND n.format = 'T20'
                           AND n.date > m.date AND n.date <= m.date + 120) AS last_of_season,
               EXISTS (SELECT 1 FROM matches n WHERE n.competition = m.competition AND n.format = 'T20'
                       AND n.event_match_number IS NULL AND n.date > m.date AND n.date <= m.date + 10) AS before_knockout,
               -- Only a competition that numbers its league matches marks its knockouts by leaving them unnumbered.
               EXISTS (SELECT 1 FROM matches n WHERE n.competition = m.competition AND n.format = 'T20'
                       AND n.event_match_number IS NOT NULL AND n.date < m.date AND n.date >= m.date - 120) AS numbered
        FROM matches m
        WHERE m.format = 'T20' AND m.gender = 'male' AND to_char(m.date, 'MM-DD') = :md
          AND m.date >= :first AND m.date < :this_year AND m.winner IS NOT NULL
          -- Rain rules (D/L), bowl-outs and the like: win probability doesn't know about a revised target, so a
          -- "99% to win" there can be the model, not the match.
          AND (m.outcome IS NULL OR m.outcome->>'method' IS NULL)
          AND (m.match_type = 'league' OR (m.team1 = ANY(:intl) AND m.team2 = ANY(:intl)))
          AND EXISTS (SELECT 1 FROM ball_metrics bm WHERE bm.p_match = m.id::text)
    """), {"md": day.strftime("%m-%d"), "first": date(FIRST_YEAR, 1, 1), "this_year": date(day.year, 1, 1),
           "intl": INTERNATIONAL_TEAMS_RANKED}).mappings()]
    if not rows:
        return []
    ids = [str(r["id"]) for r in rows]
    tops = top_impact(db, ids)
    wp = db.execute(text("""
        SELECT bm.p_match, bm.inns, MIN(dd.team_bat) AS bat, MAX(bm.wp_after) AS hi, MIN(bm.wp_after) AS lo
        FROM ball_metrics bm JOIN delivery_details dd ON dd.id = bm.delivery_id
        WHERE bm.p_match = ANY(:ids) AND bm.inns IN (1, 2) GROUP BY 1, 2
    """), {"ids": ids}).mappings().all()
    peaks: Dict[str, float] = {}
    out = []
    for r in rows:
        mid = str(r["id"])
        loser = r["team2"] if r["winner"] == r["team1"] else r["team1"]
        for w in (w for w in wp if w["p_match"] == mid):
            peak = (w["hi"] if w["bat"] == loser else 1 - w["lo"]) * 100
            peaks[mid] = max(peaks.get(mid, 0.0), peak)
        key = _comp_key(r)
        stage = _stage(r, key)
        league_unnumbered = r["match_type"] == "league" and r["event_match_number"] is None and r["numbered"]
        final = league_unnumbered and r["last_of_season"]
        playoff = league_unnumbered and not final and r["before_knockout"]
        top = tops.get(mid)
        years = day.year - r["date"].year
        performance = min(1.5, (top["impact"] if top else 0) / IMPACT_FULL)
        comeback = max(0.0, (peaks.get(mid, 0) - COMEBACK_FROM) / (100 - COMEBACK_FROM)) * 1.3
        story = max(performance, comeback) + (0.5 if final else 0.25 if playoff else 0) \
            + (0.2 if years in ROUND_YEARS else 0)
        out.append({**r, "id": mid, "key": key, "stage": stage, "final": final, "playoff": playoff, "loser": loser,
                    "top": top, "loser_peak": round(peaks.get(mid, 0), 1), "years": years,
                    "angle": "comeback" if comeback > performance else "performance",
                    "score": round(STAGE[stage] * story, 3)})
    return sorted(out, key=lambda c: -c["score"])


def pick(db: Session, day: date, avoid=()) -> Optional[Dict[str, Any]]:
    """The best story; a competition in `avoid` (yesterday's) only wins when it is clearly the best (25% ahead)."""
    ranked = candidates(db, day)
    if not ranked:
        return None
    best = ranked[0]
    if best["key"] in avoid:
        other = next((c for c in ranked if c["key"] not in avoid), None)
        if other and other["score"] >= 0.8 * best["score"]:
            return other
    return best


# ---- cards ------------------------------------------------------------------------------------------------------

def _competition_ids_sql(key: str) -> tuple[str, Dict[str, Any]]:
    from models import INTERNATIONAL_TEAMS_RANKED
    from services.recent_matches import _competition_values_for_key

    if key == "T20I":
        top = INTERNATIONAL_TEAMS_RANKED[:TOP_FULL]
        return "m.match_type = 'international' AND m.team1 = ANY(:top) AND m.team2 = ANY(:top)", {"top": top}
    return "m.match_type = 'league' AND m.competition = ANY(:vals)", {"vals": _competition_values_for_key(key)}


def rank_card(db: Session, c: Dict[str, Any], sample: str, upto: date) -> Optional[Dict[str, Any]]:
    """Where the match's top performance ranks among every innings (or spell) in the competition, 2015 to `upto`
    (the post's day, so it ranks against everything since, not just what came before):
    the best RANK_ROWS, with this one highlighted (added at the bottom when it isn't among them)."""
    from services import query_cache

    top = c["top"]
    if not top:
        return None
    where, params = _competition_ids_sql(c["key"])
    role_col, team_col, sign = (("bat", "team_bat", "") if top["role"] == "bat" else ("bowl", "team_bowl", "-"))

    def run():
        rows = db.execute(text(f"""
            WITH ids AS (SELECT m.id::text AS id, m.date, m.team1, m.team2 FROM matches m
                         WHERE {where} AND m.format = 'T20' AND m.gender = 'male' AND m.date >= :first
                           AND m.date <= :upto),
            per AS (
                SELECT dd.p_match, COALESCE(pa.canonical_name, dd.{role_col}) AS name, MIN(dd.{team_col}) AS team,
                       {sign}SUM(bm.impact) AS impact
                FROM delivery_details dd JOIN ids ON ids.id = dd.p_match
                JOIN ball_metrics bm ON bm.delivery_id = dd.id
                LEFT JOIN player_alias_map pa ON LOWER(dd.{role_col}) = pa.name_key
                WHERE COALESCE(dd.wide, 0) = 0 AND dd.{role_col} IS NOT NULL
                GROUP BY 1, 2)
            SELECT per.*, ids.date, ids.team1, ids.team2 FROM per JOIN ids ON ids.id = per.p_match
            WHERE per.impact IS NOT NULL ORDER BY per.impact DESC
        """), {**params, "first": date(FIRST_YEAR, 1, 1), "upto": upto}).mappings().all()
        return [{**dict(r), "impact": float(r["impact"]), "date": str(r["date"])} for r in rows]

    rows = query_cache.cached_run(db, {"kind": "otd-rank", "v": 1, "key": c["key"], "role": top["role"],
                                       "upto": str(upto)}, lambda: {"rows": run()})["rows"]
    if len(rows) < 50:
        return None
    mine = next((i for i, r in enumerate(rows) if r["p_match"] == c["id"] and r["name"] == top["name"]), None)
    if mine is None:
        return None
    shown = rows[:RANK_ROWS] if mine < RANK_ROWS else rows[:RANK_ROWS - 1] + [rows[mine]]
    what = "innings" if top["role"] == "bat" else "bowling performances"
    scope = "T20Is between the top 12" if c["key"] == "T20I" else c["key"]
    pct = 100 * (mine + 1) / len(rows)
    rank_words = (f"the {fmt(mine + 1, 'int')}{_suffix(mine + 1)}-biggest" if mine < 100
                  else f"in the top {max(1, round(pct))}%")
    title = (f"{top['name']}'s {fmt(top['impact'], 'signed1')} is {rank_words} of {fmt(len(rows), 'int')} {what} "
             f"in {scope} since {FIRST_YEAR}, by Impact")
    rows_out = [{"name": r["name"], "value": round(r["impact"], 1), "team": r["team"],
                 "highlight": r["p_match"] == c["id"] and r["name"] == top["name"],
                 "detail": f"{r['date'][:4]} · {_short_team(r['team1'])} v {_short_team(r['team2'])}"} for r in shown]
    k = card("rank", "metric_bars", title, {
        "metric": {"label": "Impact", "format": "signed1", "signed": False}, "rows": rows_out,
        "label_width": 150,
    }, sample, f"Impact: runs added to (or saved from) the expected total. Every {'innings' if top['role'] == 'bat' else 'bowling performance'} "
               f"in {scope} from {FIRST_YEAR} to {upto:%b %Y}.")
    k["facts"] = {"rank": mine + 1, "of": len(rows), "pct": round(pct, 1)}
    return k


def _suffix(n: int) -> str:
    return "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _short_team(name: str) -> str:
    from models import teams_mapping

    return teams_mapping.get(name, name)


def _figure(sc: Dict[str, Any], name: str, role: str) -> Optional[str]:
    """The scorecard's line for the top performer: "102* (50)" or "5/41"."""
    for inn in sc.get("innings") or []:
        if role == "bat":
            r = next((r for r in inn["batting"] if r["name"] == name), None)
            if r:
                return f"{r['runs']}{'*' if r.get('not_out') else ''} off {r['balls']}"
        else:
            r = next((r for r in inn["bowling"] if r["name"] == name), None)
            if r:
                parts = str(r["figures"]).split("-")
                return f"{r['wickets']}/{parts[2]}" if len(parts) >= 3 else str(r["figures"])
    return None


# ---- the post ---------------------------------------------------------------------------------------------------

def post(db: Session, day: date, avoid=()) -> Optional[Dict[str, Any]]:
    from services.ig_posts.match import innings_scorecards
    from services.ig_posts.recap_series import (how_it_was_won, mark_wickets, score_race, wp_swings)
    from services.ig_posts.recap_special import Match
    from services.match_scorecard import get_match_scorecard_service

    c = pick(db, day, avoid)
    if not c:
        return None
    stage_word = "Final" if c["final"] else "Playoff" if c["playoff"] else None
    kicker = " · ".join(p for p in ["On this day", f"{c['key']} {c['date'].year}", stage_word] if p)
    sample = f"{c['key']} · {_short_team(c['team1'])} v {_short_team(c['team2'])} · {c['date']:%d %b %Y}"
    m = {"id": c["id"], "date": c["date"], "venue": c["venue"], "team1": c["team1"], "team2": c["team2"],
         "format": "T20", "winner": c["winner"]}
    x = Match(db, m, sample)
    if not x.innings[1] or not x.innings[2]:
        return None
    mark_wickets(x.balls)
    sc = get_match_scorecard_service(match_id=c["id"], min_balls=6, db=db)
    how = how_it_was_won(db, x, sc)
    if not how:
        return None
    rank, wp, race = rank_card(db, c, sample, day), wp_swings(x, sc), score_race(x)
    cards = [k for k in [how, rank, wp, race] if k] + innings_scorecards(db, c["id"], sample)
    top = c["top"]
    figure = _figure(sc, top["name"], top["role"]) if top else None
    ago = f"{c['years']} years ago today" if c["years"] > 1 else "A year ago today"
    if c["angle"] == "comeback" and c["loser_peak"] >= COMEBACK_FROM:
        chance = "more than 99%" if c["loser_peak"] >= 99.5 else f"{round(c['loser_peak'])}%"
        hook = f"{ago}, {c['loser']} were {chance} to win. They lost."
    elif top and figure:
        hook = f"{ago}: {top['name']}'s {figure}, {fmt(top['impact'], 'signed1')} runs of Impact."
    else:
        hook = f"{ago}: {_short_team(c['team1'])} v {_short_team(c['team2'])}."
    # The match itself, not a finding: How it was won (slide 2) leads with the finding, and saying it twice wastes a line.
    venue = (c["venue"] or "").split(",")[0]
    result = (sc.get("match") or {}).get("result_text") or ""
    sub = f"{_short_team(c['team1'])} v {_short_team(c['team2'])}" + (f" at {venue}" if venue else "") \
        + (f": {result}" if result else "")
    players = [p for p in [top["name"] if top else None] if p]
    lines = [how["payload"]["headline"]] + [k["title"] + "." for k in (rank, wp) if k]
    tags = ["#OnThisDay", _fixture_tag(c), *(["#" + "".join(ch for ch in top["name"] if ch.isalnum())] if top else []),
            _competition_tag(c["key"])]
    caption = {"lines": lines[:4], "prompt": "Do you remember this one?", "tags": [t for t in tags if t][:5],
               "players": players}
    return {"hook": hook, "sub": sub, "kicker": kicker, "cards": cards, "title": hook.rstrip("."),
            "verdict": " ".join(lines[:2]), "players": players, "teams": [c["team1"], c["team2"]], "day": day,
            "caption": caption, "match_id": c["id"], "candidate": {k: c[k] for k in (
                "id", "key", "stage", "final", "playoff", "loser_peak", "angle", "score", "years")},
            "method": "Impact and win probability are ball by ball (T20 Primer method), from 2015 on."}


def _fixture_tag(c: Dict[str, Any]) -> Optional[str]:
    a, b = _short_team(c["team1"]), _short_team(c["team2"])
    if c["key"] == "T20I":
        from services.ig_posts.recap_special import abbr

        a, b = abbr(c["team1"]), abbr(c["team2"])
    tag = f"#{a}v{b}".replace(" ", "")
    return tag if len(tag) <= 14 else None


def _competition_tag(key: str) -> Optional[str]:
    return {"T20I": "#T20I", "IPL": "#IPL", "BBL": "#BBL", "PSL": "#PSL", "CPL": "#CPL", "SA20": "#SA20",
            "The Hundred": "#TheHundred", "T20 Blast": "#T20Blast", "LPL": "#LPL", "BPL": "#BPL",
            "ILT20": "#ILT20", "MLC": "#MLC"}.get(key)
