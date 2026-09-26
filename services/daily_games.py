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


# ---------------------------------------------------------------------------- Player Journeys
#
# One IPL player per day: their franchise path (team + years, shown up front), guessed by name.
# Careers span both ball-by-ball tables -- legacy `deliveries` for seasons before 2015 and
# `delivery_details` from 2015 -- joined on canonical names via player_aliases. Guesses and hints
# are checked server-side, so the answer never reaches the browser until it is revealed.

JOURNEY_MIN_SEASONS = 4
JOURNEY_MIN_TEAMS = 2
JOURNEY_HINTS = ("style", "country", "numbers", "initials")
# Team names are shown as they were that season -- "Delhi Daredevils 2014-2015" is part of the
# clue. The legacy table has historical names, but delivery_details writes current names back to
# 2015, so those are restored by year: (current name, last season under the old name, old name).
IPL_HISTORICAL_NAMES = (
    ("Delhi Capitals", 2018, "Delhi Daredevils"),
    ("Punjab Kings", 2020, "Kings XI Punjab"),
    ("Royal Challengers Bengaluru", 2023, "Royal Challengers Bangalore"),
)
IPL_SPELLINGS = {"Rising Pune Supergiants": "Rising Pune Supergiant"}


def historical_team(team: str, year: int) -> str:
    team = IPL_SPELLINGS.get(team, team)
    for current, last_old_season, old in IPL_HISTORICAL_NAMES:
        if team == current and year <= last_old_season:
            return old
    return team
JOURNEY_MIN_RUNS = 500
JOURNEY_MIN_WICKETS = 25
BOWL_STYLE_LABELS = {
    "RF": "right-arm fast", "RFM": "right-arm fast-medium", "RMF": "right-arm medium-fast",
    "RM": "right-arm medium", "RS": "right-arm slow", "RSM": "right-arm slow-medium",
    "LF": "left-arm fast", "LFM": "left-arm fast-medium", "LMF": "left-arm medium-fast",
    "LM": "left-arm medium", "LS": "left-arm slow", "LSM": "left-arm slow-medium",
    "OB": "right-arm off-break", "LB": "right-arm leg-break", "LBG": "right-arm leg-break googly",
    "SLA": "slow left-arm orthodox", "LWS": "left-arm wrist-spin", "LAB": "left-arm off-break",
}


def _journey_pool(db: Session) -> Dict[str, Dict[str, Any]]:
    """canonical player -> {team_years: {(team, year)}, runs, balls, wickets} for IPL careers."""
    rows = db.execute(text("""
        WITH legacy AS (
            SELECT d.batter AS raw, d.batting_team AS team, EXTRACT(YEAR FROM m.date)::int AS year,
                   SUM(d.runs_off_bat) AS runs,
                   SUM(CASE WHEN COALESCE(d.wides, 0) = 0 THEN 1 ELSE 0 END) AS balls, 0 AS wickets
            FROM deliveries d JOIN matches m ON m.id = d.match_id
            WHERE m.competition IN ('Indian Premier League', 'IPL') AND m.date < DATE '2015-01-01'
            GROUP BY 1, 2, 3
            UNION ALL
            SELECT d.bowler, d.bowling_team, EXTRACT(YEAR FROM m.date)::int, 0, 0,
                   SUM(CASE WHEN d.wicket_type IS NOT NULL AND d.wicket_type NOT IN ('', 'run out', 'retired hurt', 'obstructing the field') THEN 1 ELSE 0 END)
            FROM deliveries d JOIN matches m ON m.id = d.match_id
            WHERE m.competition IN ('Indian Premier League', 'IPL') AND m.date < DATE '2015-01-01'
            GROUP BY 1, 2, 3
        ),
        modern AS (
            SELECT dd.bat AS raw, dd.team_bat AS team, dd.year, SUM(dd.batruns) AS runs,
                   SUM(CASE WHEN COALESCE(dd.wide, 0) = 0 THEN 1 ELSE 0 END) AS balls, 0 AS wickets
            FROM delivery_details dd
            WHERE dd.competition = 'IPL' AND dd.format = 'T20' AND dd.gender = 'male' AND dd.year >= 2015
            GROUP BY 1, 2, 3
            UNION ALL
            SELECT dd.bowl, dd.team_bowl, dd.year, 0, 0,
                   SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal <> '' AND LOWER(dd.dismissal) NOT LIKE '%run out%' THEN 1 ELSE 0 END)
            FROM delivery_details dd
            WHERE dd.competition = 'IPL' AND dd.format = 'T20' AND dd.gender = 'male' AND dd.year >= 2015
            GROUP BY 1, 2, 3
        )
        SELECT COALESCE(pa.alias_name, a.raw) AS player, a.team, a.year,
               SUM(a.runs) AS runs, SUM(a.balls) AS balls, SUM(a.wickets) AS wickets
        FROM (SELECT * FROM legacy UNION ALL SELECT * FROM modern) a
        LEFT JOIN player_aliases pa ON pa.player_name = a.raw
        WHERE a.raw IS NOT NULL AND a.team IS NOT NULL
        GROUP BY 1, 2, 3
    """)).fetchall()
    pool: Dict[str, Dict[str, Any]] = {}
    for player, team, year, runs, balls, wickets in rows:
        rec = pool.setdefault(player, {"team_years": set(), "runs": 0, "balls": 0, "wickets": 0})
        rec["team_years"].add((historical_team(team, int(year)), int(year)))
        rec["runs"] += int(runs or 0)
        rec["balls"] += int(balls or 0)
        rec["wickets"] += int(wickets or 0)
    return pool


def _eligible_journeys(pool: Dict[str, Dict[str, Any]]) -> List[str]:
    """Players with a real journey: several seasons and more than one franchise."""
    names = []
    for name, rec in pool.items():
        seasons = {year for _, year in rec["team_years"]}
        teams = {team for team, _ in rec["team_years"]}
        first = name.split()[0] if name.split() else ""
        notable = rec["runs"] >= JOURNEY_MIN_RUNS or rec["wickets"] >= JOURNEY_MIN_WICKETS
        # A lone initial ("A Symonds") is a legacy name with no alias -- not a fair thing to type.
        if (len(seasons) >= JOURNEY_MIN_SEASONS and len(teams) >= JOURNEY_MIN_TEAMS and notable
                and len(first) > 1 and name.replace(" ", "").isalpha()):
            names.append(name)
    return sorted(names)


def journey_pool(db: Session) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    today = today_ist()
    return _cached(("journey-pool", today), lambda: (lambda pool: (pool, _eligible_journeys(pool)))(_journey_pool(db)))


def journey_player(db: Session, puzzle_id: str) -> Tuple[str, Dict[str, Any], Optional[date]]:
    """The player for a puzzle id: an ISO date (the daily) or a practice token."""
    pool, eligible = journey_pool(db)
    try:
        day = resolve_day(date.fromisoformat(puzzle_id))
        rng = rng_for("player-journey", day)
    except ValueError:
        day = None
        rng = random.Random(int(hashlib.sha256(f"practice:{puzzle_id}".encode()).hexdigest()[:16], 16))
    name = rng.choice(eligible)
    return name, pool[name], day


def collapse_journey(team_years) -> List[Dict[str, Any]]:
    """[(team, year)] -> [{team, years: '2008-2010'}] in career order (a gap starts a new stint)."""
    ordered = sorted(team_years, key=lambda ty: (ty[1], ty[0]))
    stints: List[Dict[str, Any]] = []
    for team, year in ordered:
        last = stints[-1] if stints else None
        if last and last["team"] == team and year == last["end"] + 1:
            last["end"] = year
        elif last and last["team"] == team and year == last["end"]:
            continue
        else:
            stints.append({"team": team, "start": year, "end": year})
    return [{"team": s["team"], "years": f"{s['start']}" if s["start"] == s["end"] else f"{s['start']}-{s['end']}"} for s in stints]


def name_shape(name: str) -> List[int]:
    """Letters per word, for the answer slots (spaces and punctuation are not typed)."""
    return [len([c for c in word if c.isalpha()]) for word in name.split() if any(c.isalpha() for c in word)]


def letters(text_: str) -> str:
    return "".join(c for c in (text_ or "").upper() if c.isalpha())


def journey_hint(db: Session, name: str, rec: Dict[str, Any], key: str) -> str:
    if key == "initials":
        return " ".join(word[0].upper() for word in name.split() if word)
    if key == "numbers":
        sr = f" @ SR {rec['runs'] * 100.0 / rec['balls']:.0f}" if rec["balls"] >= 60 else ""
        parts = []
        if rec["runs"] >= 50:
            parts.append(f"{rec['runs']:,} IPL runs{sr}")
        if rec["wickets"] >= 5:
            parts.append(f"{rec['wickets']} IPL wickets")
        return " · ".join(parts) or f"{rec['runs']} runs, {rec['wickets']} wickets"
    profile = db.execute(text("""
        SELECT p.batting_hand, p.bowling_type, p.bowler_type, p.nationality
        FROM players p
        WHERE p.name = :name OR p.name IN (SELECT player_name FROM player_aliases WHERE alias_name = :name)
        ORDER BY (p.nationality IS NULL), (p.batting_hand IS NULL)
        LIMIT 1
    """), {"name": name}).mappings().first() or {}
    def clean(value):
        return None if value in (None, "", "-") or str(value).lower() == "nan" else value

    if key == "country":
        return clean(profile.get("nationality")) or "Not recorded"
    # Fall back to the ball-by-ball feed for handedness / bowling style.
    feed = db.execute(text("""
        SELECT
            (SELECT dd.bat_hand FROM delivery_details dd
              WHERE dd.bat IN (:name, (SELECT player_name FROM player_aliases WHERE alias_name = :name LIMIT 1))
                AND dd.bat_hand IS NOT NULL AND dd.bat_hand NOT IN ('', '-') LIMIT 1) AS bat_hand,
            (SELECT dd.bowl_style FROM delivery_details dd
              WHERE dd.bowl IN (:name, (SELECT player_name FROM player_aliases WHERE alias_name = :name LIMIT 1))
                AND dd.bowl_style IS NOT NULL AND dd.bowl_style NOT IN ('', '-') LIMIT 1) AS bowl_style
    """), {"name": name}).mappings().first() or {}
    # style: role from IPL numbers + handedness + bowling style
    runs, wickets = rec["runs"], rec["wickets"]
    role = "All-rounder" if runs >= 800 and wickets >= 30 else "Bowler" if wickets >= 30 else "Batter"
    raw_hand = (clean(profile.get("batting_hand")) or clean(feed.get("bat_hand")) or "").upper()
    hand = {"RHB": "right-hand bat", "LHB": "left-hand bat"}.get(raw_hand)
    raw_bowl = clean(feed.get("bowl_style")) or clean(profile.get("bowling_type")) or clean(profile.get("bowler_type"))
    bowl = None
    if raw_bowl:
        codes = [BOWL_STYLE_LABELS.get(code.strip().upper(), code.strip()) for code in str(raw_bowl).split("/")]
        bowl = " / ".join(codes)
    # Only mention bowling for players who actually bowled in the IPL.
    if rec["wickets"] < 5:
        bowl = None
    return " · ".join(part for part in (role, hand, bowl) if part)
