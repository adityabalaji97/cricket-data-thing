"""
Daily games (growth plan G2): one shared puzzle per day, the same for everyone.

  Call It           5 real chase moments; guess the chasing side's win chance.
  Higher or Lower   a chain of player-seasons; is the next one's Impact higher or lower?

Puzzles are deterministic in (game, date) -- the date rolls over at midnight IST -- so every
player sees the same set and results can be compared and shared. Answers are served separately
(reveal endpoints) so the question payload does not give them away. Both draw on the T20 Primer
tables (ball_metrics), so they only exist because Hindsight has win probability and Impact.
"""

from __future__ import annotations

import hashlib
import random
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

IST = timezone(timedelta(hours=5, minutes=30))
LAUNCH_DATE = date(2026, 9, 26)  # puzzle #1
TOP_T20I_TEAMS = (
    "India", "Australia", "England", "West Indies", "New Zealand",
    "South Africa", "Pakistan", "Sri Lanka", "Bangladesh", "Afghanistan",
)
MAJOR_LEAGUES = ("IPL", "BBL", "PSL", "SA20", "CPL", "ILT20", "MLC")

CALL_IT_MOMENTS = 5
HIGHER_LOWER_LENGTH = 11  # 10 guesses
ESTABLISHED_BALLS = 600

_pool_cache: Dict[Tuple[str, date], Tuple[float, Any]] = {}
_POOL_TTL = 6 * 3600


def today_ist(now: Optional[datetime] = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(IST).date()


def puzzle_number(day: date) -> int:
    return (day - LAUNCH_DATE).days + 1


def rng_for(game: str, day: date) -> random.Random:
    seed = int(hashlib.sha256(f"hindsight:{game}:{day.isoformat()}".encode()).hexdigest()[:16], 16)
    return random.Random(seed)


def resolve_day(day: Optional[date]) -> date:
    """Today (IST) by default; the future is not playable, the past is (archive)."""
    today = today_ist()
    if day is None or day > today:
        return today
    return max(day, LAUNCH_DATE)


def _cached(key: Tuple[str, date], build):
    hit = _pool_cache.get(key)
    if hit and time.time() - hit[0] < _POOL_TTL:
        return hit[1]
    value = build()
    _pool_cache[key] = (time.time(), value)
    return value


# ------------------------------------------------------------------------------------ Call It


# Share of the five daily slots by competition group: the audience is mostly Indian, so the
# IPL and top-team T20Is lead; the other leagues keep it varied.
CALL_IT_GROUP_WEIGHTS = (("IPL", 0.4), ("T20I", 0.25), ("OTHER", 0.35))


def _eligible_chases(db: Session, day: date) -> Dict[str, List[str]]:
    """Decided chases from the three years before `day`, grouped as IPL / T20I / other leagues."""
    rows = db.execute(text("""
        SELECT DISTINCT dd.p_match, CASE WHEN dd.competition IN ('IPL', 'T20I') THEN dd.competition ELSE 'OTHER' END AS grp
        FROM delivery_details dd
        JOIN matches m ON m.id = dd.p_match
        WHERE dd.format = 'T20' AND dd.gender = 'male' AND dd.inns = 2
          AND m.date BETWEEN :start AND :end
          AND m.winner IS NOT NULL AND m.winner <> ''
          AND (dd.competition = ANY(:leagues)
               OR (dd.competition = 'T20I' AND dd.team_bat = ANY(:teams) AND dd.team_bowl = ANY(:teams)))
        ORDER BY dd.p_match
    """), {"start": day - timedelta(days=3 * 365), "end": day - timedelta(days=1),
           "leagues": list(MAJOR_LEAGUES), "teams": list(TOP_T20I_TEAMS)}).fetchall()
    groups: Dict[str, List[str]] = {name: [] for name, _ in CALL_IT_GROUP_WEIGHTS}
    for match_id, group in rows:
        groups.setdefault(group, []).append(match_id)
    return groups


def _moment_for(db: Session, match_id: str) -> Optional[Dict[str, Any]]:
    """The highest-leverage chase state whose result was genuinely open, with its context."""
    row = db.execute(text("""
        SELECT dd.id, dd.team_bat, dd.team_bowl, dd.competition, dd.year, dd.ground,
               bm.wp_before, bm.leverage,
               (dd.inns_runs - dd.score) AS runs_before,
               (dd.inns_wkts - CASE WHEN LOWER(COALESCE(dd.out, '')) = 'true' THEN 1 ELSE 0 END) AS wkts_before,
               dd.inns_balls_rem + CASE WHEN COALESCE(dd.wide, 0) = 0 AND COALESCE(dd.noball, 0) = 0 THEN 1 ELSE 0 END AS balls_left,
               NULLIF(dd.target, '')::numeric::int AS target,
               m.winner, m.date
        FROM delivery_details dd
        JOIN ball_metrics bm ON bm.delivery_id = dd.id
        JOIN matches m ON m.id = dd.p_match
        WHERE dd.p_match = :match_id AND dd.inns = 2
          AND bm.wp_before BETWEEN 0.15 AND 0.85
          AND dd.inns_balls_rem BETWEEN 12 AND 48
        ORDER BY bm.leverage DESC, dd.id
        LIMIT 1
    """), {"match_id": match_id}).mappings().first()
    if not row or not row["target"]:
        return None
    return dict(row)


def call_it_puzzle(db: Session, day: date) -> Dict[str, Any]:
    def build():
        groups = _eligible_chases(db, day)
        rng = rng_for("call-it", day)
        for matches in groups.values():
            rng.shuffle(matches)
        names = [name for name, _ in CALL_IT_GROUP_WEIGHTS]
        weights = [weight for _, weight in CALL_IT_GROUP_WEIGHTS]
        moments, seen = [], set()
        attempts = 0
        while len(moments) < CALL_IT_MOMENTS and attempts < 60 and any(groups.values()):
            attempts += 1
            group = rng.choices(names, weights)[0]
            if not groups.get(group):
                continue
            match_id = groups[group].pop()
            if match_id in seen:
                continue
            seen.add(match_id)
            moment = _moment_for(db, match_id)
            if moment:
                moments.append({**moment, "match_id": match_id})
        return moments

    return _cached(("call-it", day), build)


def call_it_question(moment: Dict[str, Any], index: int) -> Dict[str, Any]:
    needed = int(moment["target"]) - int(moment["runs_before"])
    return {
        "index": index,
        "batting_team": moment["team_bat"],
        "bowling_team": moment["team_bowl"],
        "competition": moment["competition"],
        "season": moment["year"],
        "venue": moment["ground"],
        "target": int(moment["target"]),
        "score": f"{int(moment['runs_before'])}/{int(moment['wkts_before'])}",
        "runs_needed": needed,
        "balls_left": int(moment["balls_left"]),
        "wickets_left": 10 - int(moment["wkts_before"]),
    }


def call_it_answer(moment: Dict[str, Any], index: int) -> Dict[str, Any]:
    return {
        "index": index,
        "winner": moment["winner"],
        "chasing_side_won": moment["winner"] == moment["team_bat"],
        "model_win_probability": round(float(moment["wp_before"]), 3),
        "match_id": moment["match_id"],
        "date": moment["date"].isoformat() if moment.get("date") else None,
    }


# ---------------------------------------------------------------------------- Higher or Lower


def _player_seasons(db: Session, day: date) -> List[Dict[str, Any]]:
    """Batter-seasons (per competition) with >= 150 balls in the last four seasons before `day`."""
    rows = db.execute(text("""
        SELECT dd.bat AS player, dd.competition, dd.year,
               COUNT(*) AS balls, SUM(dd.batruns) AS runs,
               SUM(bm.impact) AS impact, SUM(bm.raa) AS raa, SUM(bm.wpa) AS wpa
        FROM delivery_details dd
        JOIN ball_metrics bm ON bm.delivery_id = dd.id
        WHERE dd.format = 'T20' AND dd.gender = 'male' AND COALESCE(dd.wide, 0) = 0
          AND dd.year BETWEEN :first AND :last
          AND (dd.competition = ANY(:leagues) OR (dd.competition = 'T20I' AND dd.team_bat = ANY(:teams)))
        GROUP BY dd.bat, dd.competition, dd.year
        HAVING COUNT(*) >= 150
        ORDER BY dd.bat, dd.competition, dd.year
    """), {"first": day.year - 4, "last": day.year, "leagues": list(MAJOR_LEAGUES), "teams": list(TOP_T20I_TEAMS)}).mappings().all()
    # Recognisable names only: players with >= 600 balls across these seasons, not one-season wonders.
    totals: Dict[str, int] = {}
    for r in rows:
        totals[r["player"]] = totals.get(r["player"], 0) + int(r["balls"])
    return [dict(r) for r in rows if totals[r["player"]] >= ESTABLISHED_BALLS]


def higher_lower_puzzle(db: Session, day: date) -> List[Dict[str, Any]]:
    """A chain alternating close (< 15 runs apart) and clear (> 30) Impact gaps, no repeats."""
    def build():
        pool = _player_seasons(db, day)
        rng = rng_for("higher-lower", day)
        rng.shuffle(pool)
        if not pool:
            return []
        chain = [pool[0]]
        used = {pool[0]["player"]}
        for step in range(1, HIGHER_LOWER_LENGTH):
            last = float(chain[-1]["impact"])
            close = step % 2 == 1
            def fits(item):
                gap = abs(float(item["impact"]) - last)
                return item["player"] not in used and gap >= 2 and (gap < 15 if close else gap > 30)
            nxt = next((item for item in pool if fits(item)), None) or next(
                (item for item in pool if item["player"] not in used and abs(float(item["impact"]) - last) >= 2), None)
            if nxt is None:
                break
            chain.append(nxt)
            used.add(nxt["player"])
        return chain

    return _cached(("higher-lower", day), build)


def higher_lower_card(item: Dict[str, Any], index: int, reveal: bool) -> Dict[str, Any]:
    balls = int(item["balls"])
    card = {
        "index": index,
        "player": item["player"],
        "competition": item["competition"],
        "season": item["year"],
        "balls": balls,
        "runs": int(item["runs"] or 0),
        "strike_rate": round(float(item["runs"] or 0) * 100.0 / balls, 1) if balls else None,
    }
    if reveal:
        card.update({
            "impact": round(float(item["impact"]), 1),
            "raa": round(float(item["raa"]), 1),
            "wpa": round(float(item["wpa"]), 2),
        })
    return card
