"""
IPL Championship Prediction Engine (Phase 3)

Builds a multi-metric pre-season team ranking model using:
- IPL team results/ELO trends
- Roster-level batting/bowling aggregates
- Pace/spin splits
- Venue adaptability/archetype consistency
- Squad depth metrics

Scores are percentile-normalized across the 10 IPL teams, then combined with
category weights into a 0-100 composite score.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta, timezone
from difflib import get_close_matches
from math import sqrt
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from ipl_rosters import get_all_ipl_teams, get_ipl_roster, get_team_abbrev_from_name
from services.bowler_types import BOWLER_CATEGORY_SQL
from services.player_aliases import get_player_names
from services.teams import get_all_team_name_variations


CATEGORY_WEIGHTS = {
    "win_rate": 0.12,
    "elo": 0.10,
    "batting": 0.18,
    "bowling": 0.18,
    "pace_spin": 0.12,
    "venue_adaptability": 0.10,
    "situational": 0.10,
    "squad_depth": 0.10,
}


CATEGORY_METRIC_DEFS = {
    "win_rate": [
        {"key": "league_win_pct", "higher_is_better": True},
        {"key": "home_win_pct", "higher_is_better": True},
        {"key": "away_win_pct", "higher_is_better": True},
    ],
    "elo": [
        {"key": "peak_elo", "higher_is_better": True},
        {"key": "current_elo", "higher_is_better": True},
        {"key": "elo_trend", "higher_is_better": True},
    ],
    "batting": [
        {"key": "pp_sr", "higher_is_better": True},
        {"key": "pp_avg", "higher_is_better": True},
        {"key": "pp_boundary_pct", "higher_is_better": True},
        {"key": "pp_dot_pct", "higher_is_better": False},
        {"key": "pp_balls_per_six", "higher_is_better": False},
        {"key": "middle_sr", "higher_is_better": True},
        {"key": "middle_avg", "higher_is_better": True},
        {"key": "middle_boundary_pct", "higher_is_better": True},
        {"key": "middle_dot_pct", "higher_is_better": False},
        {"key": "middle_balls_per_six", "higher_is_better": False},
        {"key": "death_sr", "higher_is_better": True},
        {"key": "death_avg", "higher_is_better": True},
        {"key": "death_boundary_pct", "higher_is_better": True},
        {"key": "death_dot_pct", "higher_is_better": False},
        {"key": "death_balls_per_six", "higher_is_better": False},
    ],
    "bowling": [
        {"key": "pp_economy", "higher_is_better": False},
        {"key": "pp_bowling_sr", "higher_is_better": False},
        {"key": "pp_dot_pct", "higher_is_better": True},
        {"key": "pp_boundary_pct_conceded", "higher_is_better": False},
        {"key": "middle_economy", "higher_is_better": False},
        {"key": "middle_bowling_sr", "higher_is_better": False},
        {"key": "middle_dot_pct", "higher_is_better": True},
        {"key": "middle_boundary_pct_conceded", "higher_is_better": False},
        {"key": "death_economy", "higher_is_better": False},
        {"key": "death_bowling_sr", "higher_is_better": False},
        {"key": "death_dot_pct", "higher_is_better": True},
        {"key": "death_boundary_pct_conceded", "higher_is_better": False},
    ],
    "pace_spin": [
        {"key": "bat_sr_vs_pace", "higher_is_better": True},
        {"key": "bat_sr_vs_spin", "higher_is_better": True},
        {"key": "bat_avg_vs_pace", "higher_is_better": True},
        {"key": "bat_avg_vs_spin", "higher_is_better": True},
        {"key": "bat_boundary_pct_vs_pace", "higher_is_better": True},
        {"key": "bat_boundary_pct_vs_spin", "higher_is_better": True},
        {"key": "bat_dot_pct_vs_pace", "higher_is_better": False},
        {"key": "bat_dot_pct_vs_spin", "higher_is_better": False},
        {"key": "bowl_economy_pace", "higher_is_better": False},
        {"key": "bowl_economy_spin", "higher_is_better": False},
        {"key": "bowl_sr_pace", "higher_is_better": False},
        {"key": "bowl_sr_spin", "higher_is_better": False},
    ],
    "venue_adaptability": [
        {"key": "venue_bat_sr", "higher_is_better": True},
        {"key": "venue_bat_avg", "higher_is_better": True},
        {"key": "venue_bowl_economy", "higher_is_better": False},
        {"key": "venue_coverage", "higher_is_better": True},
        {"key": "archetype_consistency", "higher_is_better": True},
        {"key": "archetype_coverage", "higher_is_better": True},
        {"key": "archetype_mean_win_pct", "higher_is_better": True},
    ],
    "situational": [
        {"key": "chasing_win_pct", "higher_is_better": True},
        {"key": "defending_win_pct", "higher_is_better": True},
        {"key": "close_win_pct", "higher_is_better": True},
    ],
    "squad_depth": [
        {"key": "batting_depth_gini", "higher_is_better": False},
        {"key": "bowling_depth_gini", "higher_is_better": False},
        {"key": "all_rounder_count", "higher_is_better": True},
        {"key": "bench_strength", "higher_is_better": True},
        {"key": "bench_experience_pct", "higher_is_better": True},
    ],
}


MODEL_EXPLAINER = {
    "version": "ipl-2026-preseason-v1",
    "description": (
        "Composite prediction model that percentile-normalizes team metrics "
        "across all IPL teams and combines category scores using fixed weights."
    ),
    "steps": [
        "Resolve squad names to canonical player identities.",
        "Aggregate recent player performance into team-level category metrics.",
        "Convert each metric to percentile scores across all IPL teams.",
        "Average metric percentiles into category scores.",
        "Compute weighted composite score and rank teams.",
    ],
    "recency_weighting": {
        "last_180_days": 1.0,
        "181_to_365_days": 0.75,
        "366_to_730_days": 0.5,
        "older": 0.3,
    },
    "data_sources": [
        "matches",
        "batting_stats",
        "bowling_stats",
        "deliveries",
        "delivery_details",
        "player_aliases",
        "players",
        "ipl_rosters",
    ],
}


TEAM_HOME_VENUE_KEYWORDS = {
    "CSK": ["chennai", "chepauk", "m a chidambaram"],
    "MI": ["mumbai", "wankhede", "dy patil", "navi mumbai"],
    "KKR": ["kolkata", "eden gardens"],
    "DC": ["delhi", "arun jaitley", "feroz shah kotla", "visakhapatnam", "vizag"],
    "GT": ["ahmedabad", "narendra modi", "motera"],
    "LSG": ["lucknow", "ekana"],
    "PBKS": ["mohali", "chandigarh", "dharamsala", "mullanpur"],
    "RR": ["jaipur", "sawai mansingh", "guwahati"],
    "RCB": ["bengaluru", "bangalore", "chinnaswamy"],
    "SRH": ["hyderabad", "uppal", "rajiv gandhi"],
}


_CACHE_TTL_SECONDS = 30 * 60
_PREDICTION_CACHE: Dict[str, Dict[str, Any]] = {}


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return float(numerator) / float(denominator)


def _safe_pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    value = _safe_div(numerator, denominator)
    return None if value is None else value * 100.0


def _safe_economy(runs: Optional[float], balls: Optional[float]) -> Optional[float]:
    value = _safe_div(runs, balls)
    return None if value is None else value * 6.0


def _safe_bowling_sr(balls: Optional[float], wickets: Optional[float]) -> Optional[float]:
    return _safe_div(balls, wickets)


def _overs_to_balls(overs_value: Optional[float]) -> float:
    if overs_value is None:
        return 0.0
    whole = int(float(overs_value))
    decimal = round((float(overs_value) - whole) * 10)
    return float(whole * 6 + decimal)


def _round(value: Optional[float], digits: int = 3) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def _canonical_venue(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _is_home_venue(venue: Optional[str], team_abbrev: str) -> bool:
    venue_text = _canonical_venue(venue)
    if not venue_text:
        return False
    for keyword in TEAM_HOME_VENUE_KEYWORDS.get(team_abbrev, []):
        if keyword in venue_text:
            return True
    return False


def _compute_gini(values: List[float]) -> Optional[float]:
    if not values:
        return None
    cleaned = [max(0.0, float(v)) for v in values]
    total = sum(cleaned)
    if total == 0:
        return 0.0
    sorted_vals = sorted(cleaned)
    n = len(sorted_vals)
    cumulative = sum((index + 1) * value for index, value in enumerate(sorted_vals))
    gini = (2 * cumulative) / (n * total) - (n + 1) / n
    return max(0.0, min(1.0, float(gini)))


def _classify_role(batting_matches: int, bowling_matches: int) -> str:
    """
    Reuses doppelganger role logic from services/search.py.
    """
    total_matches = max(batting_matches, bowling_matches)
    if total_matches > 0 and bowling_matches >= 8:
        if batting_matches >= 0.4 * total_matches and bowling_matches >= 0.4 * total_matches:
            return "all_rounder"
    if bowling_matches >= batting_matches and bowling_matches >= 8:
        return "bowler"
    if batting_matches >= (2 * bowling_matches) or bowling_matches < 8:
        return "batter"
    return "all_rounder"


def _default_date_range(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[date, date]:
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=365))
    return start, end


def _weight_params(start: date, end: date) -> Dict[str, date]:
    return {
        "start_date": start,
        "end_date": end,
        "cutoff_180": end - timedelta(days=180),
        "cutoff_365": end - timedelta(days=365),
        "cutoff_730": end - timedelta(days=730),
    }


def _weight_case_sql() -> str:
    return """
        CASE
            WHEN m.date >= :cutoff_180 THEN 1.0
            WHEN m.date >= :cutoff_365 THEN 0.75
            WHEN m.date >= :cutoff_730 THEN 0.5
            ELSE 0.3
        END
    """


def _normalize_name_key(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _build_bulk_name_index(db: Session) -> Dict[str, Any]:
    alias_rows = db.execute(
        text(
            """
            SELECT player_name, alias_name
            FROM player_aliases
            """
        )
    ).fetchall()
    player_rows = db.execute(
        text(
            """
            SELECT name
            FROM players
            """
        )
    ).fetchall()

    exact_map: Dict[str, Dict[str, str]] = {}
    for row in alias_rows:
        legacy_name = row.player_name
        details_name = row.alias_name or legacy_name
        if legacy_name:
            exact_map.setdefault(
                _normalize_name_key(legacy_name),
                {"legacy_name": legacy_name, "details_name": details_name},
            )
        if details_name:
            exact_map.setdefault(
                _normalize_name_key(details_name),
                {"legacy_name": legacy_name or details_name, "details_name": details_name},
            )

    for row in player_rows:
        legacy_name = row.name
        if legacy_name:
            exact_map.setdefault(
                _normalize_name_key(legacy_name),
                {"legacy_name": legacy_name, "details_name": legacy_name},
            )

    return {
        "exact_map": exact_map,
        "fuzzy_keys": sorted(exact_map.keys()),
    }


def _resolve_name_with_bulk_index(
    name: str,
    index: Dict[str, Any],
) -> Dict[str, str]:
    if not name:
        return {"legacy_name": name, "details_name": name}

    key = _normalize_name_key(name)
    exact_map = index.get("exact_map", {})
    if key in exact_map:
        return dict(exact_map[key])

    fuzzy_keys = index.get("fuzzy_keys", [])
    matches = get_close_matches(key, fuzzy_keys, n=1, cutoff=0.9)
    if matches:
        return dict(exact_map[matches[0]])
    return {"legacy_name": name, "details_name": name}


def _resolve_roster_players(
    team_abbrev: str,
    db: Session,
    name_cache: Optional[Dict[str, Dict[str, str]]] = None,
    bulk_name_index: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    roster = get_ipl_roster(team_abbrev) or {}
    players = roster.get("players", [])
    resolved: Dict[str, Dict[str, str]] = {}

    for player in players:
        source_name = player.get("name")
        if not source_name:
            continue

        if name_cache is not None and source_name in name_cache:
            names = name_cache[source_name]
        elif bulk_name_index is not None:
            names = _resolve_name_with_bulk_index(source_name, bulk_name_index)
            if name_cache is not None:
                name_cache[source_name] = names
        else:
            names = get_player_names(source_name, db)
            if name_cache is not None:
                name_cache[source_name] = names

        legacy_name = names.get("legacy_name") or source_name
        details_name = names.get("details_name") or source_name
        role = player.get("role", "batter")

        existing = resolved.get(legacy_name)
        if existing:
            # Prefer all-rounder when duplicate aliases collapse to same legacy name.
            if role == "all-rounder" and existing.get("role") != "all-rounder":
                existing["role"] = role
            continue

        resolved[legacy_name] = {
            "name": legacy_name,
            "display_name": details_name,
            "role": role,
        }

    return list(resolved.values())


def compute_player_metrics(
    player_name: str,
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Any]:
    """
    Compute individual player metric profile (weighted by recency).
    """
    start, end = date_range
    params = _weight_params(start, end)
    params["player_name"] = player_name

    weight_case = _weight_case_sql()

    batting_row = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bs.*,
                    {weight_case} AS w
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE LOWER(bs.striker) = LOWER(:player_name)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                COUNT(DISTINCT match_id) AS matches,
                COALESCE(SUM(runs * w), 0) AS runs,
                COALESCE(SUM(balls_faced * w), 0) AS balls,
                COALESCE(SUM(wickets * w), 0) AS dismissals,
                COALESCE(SUM(dots * w), 0) AS dots,
                COALESCE(SUM((fours + sixes) * w), 0) AS boundaries
            FROM weighted
            """
        ),
        params,
    ).fetchone()

    bowling_row = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bw.*,
                    {weight_case} AS w
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE LOWER(bw.bowler) = LOWER(:player_name)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                COUNT(DISTINCT match_id) AS matches,
                COALESCE(SUM(runs_conceded * w), 0) AS runs_conceded,
                COALESCE(SUM(wickets * w), 0) AS wickets,
                COALESCE(SUM(dots * w), 0) AS dots,
                COALESCE(
                    SUM(
                        (FLOOR(COALESCE(overs, 0)) * 6
                        + ROUND((COALESCE(overs, 0) - FLOOR(COALESCE(overs, 0))) * 10)) * w
                    ),
                    0
                ) AS balls
            FROM weighted
            """
        ),
        params,
    ).fetchone()

    bat_runs = float(batting_row.runs or 0)
    bat_balls = float(batting_row.balls or 0)
    bat_dismissals = float(batting_row.dismissals or 0)
    bowl_runs = float(bowling_row.runs_conceded or 0)
    bowl_balls = float(bowling_row.balls or 0)
    bowl_wickets = float(bowling_row.wickets or 0)

    return {
        "player_name": player_name,
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "batting": {
            "matches": int(batting_row.matches or 0),
            "runs": _round(bat_runs, 2),
            "balls": _round(bat_balls, 2),
            "average": _round(_safe_div(bat_runs, bat_dismissals)),
            "strike_rate": _round(_safe_pct(bat_runs, bat_balls)),
            "dot_pct": _round(_safe_pct(float(batting_row.dots or 0), bat_balls)),
            "boundary_pct": _round(_safe_pct(float(batting_row.boundaries or 0), bat_balls)),
        },
        "bowling": {
            "matches": int(bowling_row.matches or 0),
            "runs_conceded": _round(bowl_runs, 2),
            "balls": _round(bowl_balls, 2),
            "wickets": _round(bowl_wickets, 2),
            "economy": _round(_safe_economy(bowl_runs, bowl_balls)),
            "strike_rate": _round(_safe_bowling_sr(bowl_balls, bowl_wickets)),
            "dot_pct": _round(_safe_pct(float(bowling_row.dots or 0), bowl_balls)),
        },
    }


def _fetch_team_match_rows(
    team_abbrev: str,
    date_range: Tuple[date, date],
    db: Session,
) -> List[Dict[str, Any]]:
    start, end = date_range
    team_variations = set(get_all_team_name_variations(team_abbrev))
    team_variations.add(team_abbrev)

    roster = get_ipl_roster(team_abbrev) or {}
    team_full_name = roster.get("full_name")
    if team_full_name:
        team_variations.add(team_full_name)

    rows = db.execute(
        text(
            """
            WITH
            team_matches AS (
                SELECT
                    m.id,
                    m.date,
                    m.venue,
                    m.event_name,
                    m.team1,
                    m.team2,
                    m.winner,
                    m.team1_elo,
                    m.team2_elo
                FROM matches m
                WHERE (m.team1 = ANY(:team_variations) OR m.team2 = ANY(:team_variations))
                  AND m.competition = 'Indian Premier League'
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            ),
            legacy_scores AS (
                SELECT
                    match_id,
                    innings,
                    COALESCE(SUM(runs_off_bat + extras), 0) AS runs,
                    COUNT(CASE WHEN wicket_type IS NOT NULL THEN 1 END) AS wickets
                FROM deliveries
                WHERE match_id IN (SELECT id FROM team_matches)
                GROUP BY match_id, innings
            ),
            dd_scores AS (
                SELECT
                    p_match AS match_id,
                    inns AS innings,
                    COALESCE(SUM(score), 0) AS runs,
                    COUNT(CASE WHEN out = 'true' THEN 1 END) AS wickets
                FROM delivery_details
                WHERE p_match IN (SELECT id FROM team_matches)
                GROUP BY p_match, inns
            ),
            combined_scores AS (
                SELECT
                    COALESCE(ls.match_id, dd.match_id) AS match_id,
                    COALESCE(ls.innings, dd.innings) AS innings,
                    COALESCE(ls.runs, dd.runs, 0) AS runs,
                    COALESCE(ls.wickets, dd.wickets, 0) AS wickets
                FROM legacy_scores ls
                FULL OUTER JOIN dd_scores dd
                    ON ls.match_id = dd.match_id AND ls.innings = dd.innings
            )
            SELECT
                tm.id,
                tm.date,
                tm.venue,
                tm.event_name,
                tm.team1,
                tm.team2,
                tm.winner,
                tm.team1_elo,
                tm.team2_elo,
                COALESCE((SELECT runs FROM combined_scores WHERE match_id = tm.id AND innings = 1), 0) AS innings1_runs,
                COALESCE((SELECT wickets FROM combined_scores WHERE match_id = tm.id AND innings = 1), 0) AS innings1_wkts,
                COALESCE((SELECT runs FROM combined_scores WHERE match_id = tm.id AND innings = 2), 0) AS innings2_runs,
                COALESCE((SELECT wickets FROM combined_scores WHERE match_id = tm.id AND innings = 2), 0) AS innings2_wkts
            FROM team_matches tm
            ORDER BY tm.date ASC, tm.id ASC
            """
        ),
        {
            "team_variations": list(team_variations),
            "start_date": start,
            "end_date": end,
        },
    ).fetchall()

    out: List[Dict[str, Any]] = []
    for row in rows:
        team_is_team1 = row.team1 in team_variations
        team_won = bool(row.winner and row.winner in team_variations)
        team_elo = row.team1_elo if team_is_team1 else row.team2_elo
        out.append(
            {
                "id": row.id,
                "date": row.date,
                "venue": row.venue,
                "event_name": row.event_name,
                "team1": row.team1,
                "team2": row.team2,
                "winner": row.winner,
                "team_is_team1": team_is_team1,
                "team_won": team_won,
                "team_batted_first": team_is_team1,
                "team_elo": float(team_elo) if team_elo is not None else None,
                "innings1_runs": float(row.innings1_runs or 0),
                "innings1_wkts": float(row.innings1_wkts or 0),
                "innings2_runs": float(row.innings2_runs or 0),
                "innings2_wkts": float(row.innings2_wkts or 0),
            }
        )
    return out


def _compute_team_result_metrics(
    team_abbrev: str,
    match_rows: List[Dict[str, Any]],
) -> Tuple[Dict[str, Optional[float]], Dict[str, Optional[float]]]:
    playoff_tokens = ("qualifier", "eliminator", "final", "playoff")

    league_wins = 0
    league_decisions = 0
    home_wins = 0
    home_decisions = 0
    away_wins = 0
    away_decisions = 0

    chasing_wins = 0
    chasing_total = 0
    defending_wins = 0
    defending_total = 0
    close_wins = 0
    close_total = 0

    for row in match_rows:
        decided = bool(row.get("winner"))
        is_league_stage = True
        event_name = (row.get("event_name") or "").lower()
        if event_name and any(token in event_name for token in playoff_tokens):
            is_league_stage = False

        if decided and is_league_stage:
            league_decisions += 1
            if row["team_won"]:
                league_wins += 1

        is_home = _is_home_venue(row.get("venue"), team_abbrev)
        if decided:
            if is_home:
                home_decisions += 1
                if row["team_won"]:
                    home_wins += 1
            else:
                away_decisions += 1
                if row["team_won"]:
                    away_wins += 1

            if row["team_batted_first"]:
                defending_total += 1
                if row["team_won"]:
                    defending_wins += 1
            else:
                chasing_total += 1
                if row["team_won"]:
                    chasing_wins += 1

            close_match = False
            winner = row["winner"]
            if winner == row["team1"]:
                run_margin = row["innings1_runs"] - row["innings2_runs"]
                close_match = run_margin < 15
            elif winner == row["team2"]:
                wickets_in_hand = 10 - row["innings2_wkts"]
                close_match = wickets_in_hand < 2

            if close_match:
                close_total += 1
                if row["team_won"]:
                    close_wins += 1

    win_rate_metrics = {
        "league_win_pct": _safe_div(league_wins, league_decisions),
        "home_win_pct": _safe_div(home_wins, home_decisions),
        "away_win_pct": _safe_div(away_wins, away_decisions),
        "league_matches_count": float(league_decisions),
        "home_matches_count": float(home_decisions),
        "away_matches_count": float(away_decisions),
    }
    situational_metrics = {
        "chasing_win_pct": _safe_div(chasing_wins, chasing_total),
        "defending_win_pct": _safe_div(defending_wins, defending_total),
        "close_win_pct": _safe_div(close_wins, close_total),
        "chasing_matches_count": float(chasing_total),
        "defending_matches_count": float(defending_total),
        "close_matches_count": float(close_total),
    }
    return win_rate_metrics, situational_metrics


def _compute_elo_metrics(match_rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    elo_values = [row["team_elo"] for row in match_rows if row.get("team_elo") is not None]
    if not elo_values:
        return {"peak_elo": None, "current_elo": None, "elo_trend": None, "elo_matches_count": 0.0}

    current = float(elo_values[-1])
    peak = float(max(elo_values))
    lookback_value = float(elo_values[-6]) if len(elo_values) >= 6 else float(elo_values[0])
    trend = current - lookback_value

    return {
        "peak_elo": peak,
        "current_elo": current,
        "elo_trend": trend,
        "elo_matches_count": float(len(elo_values)),
    }


def _fetch_weighted_batting_aggregates(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, float]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    weight_case = _weight_case_sql()

    row = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bs.*,
                    {weight_case} AS w
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE bs.striker = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                COALESCE(SUM(pp_runs * w), 0) AS pp_runs,
                COALESCE(SUM(pp_balls * w), 0) AS pp_balls,
                COALESCE(SUM(pp_wickets * w), 0) AS pp_wickets,
                COALESCE(SUM(pp_boundaries * w), 0) AS pp_boundaries,
                COALESCE(SUM(pp_dots * w), 0) AS pp_dots,
                COALESCE(SUM(middle_runs * w), 0) AS middle_runs,
                COALESCE(SUM(middle_balls * w), 0) AS middle_balls,
                COALESCE(SUM(middle_wickets * w), 0) AS middle_wickets,
                COALESCE(SUM(middle_boundaries * w), 0) AS middle_boundaries,
                COALESCE(SUM(middle_dots * w), 0) AS middle_dots,
                COALESCE(SUM(death_runs * w), 0) AS death_runs,
                COALESCE(SUM(death_balls * w), 0) AS death_balls,
                COALESCE(SUM(death_wickets * w), 0) AS death_wickets,
                COALESCE(SUM(death_boundaries * w), 0) AS death_boundaries,
                COALESCE(SUM(death_dots * w), 0) AS death_dots
            FROM weighted
            """
        ),
        params,
    ).fetchone()

    sixes_row = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    CASE
                        WHEN d.over < 6 THEN 'pp'
                        WHEN d.over < 15 THEN 'middle'
                        ELSE 'death'
                    END AS phase,
                    d.runs_off_bat,
                    {weight_case} AS w
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.batter = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                COALESCE(SUM(CASE WHEN phase = 'pp' AND runs_off_bat = 6 THEN w ELSE 0 END), 0) AS pp_sixes,
                COALESCE(SUM(CASE WHEN phase = 'middle' AND runs_off_bat = 6 THEN w ELSE 0 END), 0) AS middle_sixes,
                COALESCE(SUM(CASE WHEN phase = 'death' AND runs_off_bat = 6 THEN w ELSE 0 END), 0) AS death_sixes
            FROM weighted
            """
        ),
        params,
    ).fetchone()

    return {
        "pp_runs": float(row.pp_runs or 0),
        "pp_balls": float(row.pp_balls or 0),
        "pp_wickets": float(row.pp_wickets or 0),
        "pp_boundaries": float(row.pp_boundaries or 0),
        "pp_dots": float(row.pp_dots or 0),
        "pp_sixes": float(sixes_row.pp_sixes or 0),
        "middle_runs": float(row.middle_runs or 0),
        "middle_balls": float(row.middle_balls or 0),
        "middle_wickets": float(row.middle_wickets or 0),
        "middle_boundaries": float(row.middle_boundaries or 0),
        "middle_dots": float(row.middle_dots or 0),
        "middle_sixes": float(sixes_row.middle_sixes or 0),
        "death_runs": float(row.death_runs or 0),
        "death_balls": float(row.death_balls or 0),
        "death_wickets": float(row.death_wickets or 0),
        "death_boundaries": float(row.death_boundaries or 0),
        "death_dots": float(row.death_dots or 0),
        "death_sixes": float(sixes_row.death_sixes or 0),
    }


def _fetch_weighted_bowling_aggregates(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, float]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    weight_case = _weight_case_sql()

    row = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bw.*,
                    {weight_case} AS w
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE bw.bowler = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                COALESCE(SUM(pp_runs * w), 0) AS pp_runs,
                COALESCE(SUM(pp_wickets * w), 0) AS pp_wickets,
                COALESCE(SUM(pp_dots * w), 0) AS pp_dots,
                COALESCE(SUM(pp_boundaries * w), 0) AS pp_boundaries,
                COALESCE(
                    SUM(
                        (FLOOR(COALESCE(pp_overs, 0)) * 6
                        + ROUND((COALESCE(pp_overs, 0) - FLOOR(COALESCE(pp_overs, 0))) * 10)) * w
                    ),
                    0
                ) AS pp_balls,
                COALESCE(SUM(middle_runs * w), 0) AS middle_runs,
                COALESCE(SUM(middle_wickets * w), 0) AS middle_wickets,
                COALESCE(SUM(middle_dots * w), 0) AS middle_dots,
                COALESCE(SUM(middle_boundaries * w), 0) AS middle_boundaries,
                COALESCE(
                    SUM(
                        (FLOOR(COALESCE(middle_overs, 0)) * 6
                        + ROUND((COALESCE(middle_overs, 0) - FLOOR(COALESCE(middle_overs, 0))) * 10)) * w
                    ),
                    0
                ) AS middle_balls,
                COALESCE(SUM(death_runs * w), 0) AS death_runs,
                COALESCE(SUM(death_wickets * w), 0) AS death_wickets,
                COALESCE(SUM(death_dots * w), 0) AS death_dots,
                COALESCE(SUM(death_boundaries * w), 0) AS death_boundaries,
                COALESCE(
                    SUM(
                        (FLOOR(COALESCE(death_overs, 0)) * 6
                        + ROUND((COALESCE(death_overs, 0) - FLOOR(COALESCE(death_overs, 0))) * 10)) * w
                    ),
                    0
                ) AS death_balls
            FROM weighted
            """
        ),
        params,
    ).fetchone()

    return {
        "pp_runs": float(row.pp_runs or 0),
        "pp_wickets": float(row.pp_wickets or 0),
        "pp_dots": float(row.pp_dots or 0),
        "pp_boundaries": float(row.pp_boundaries or 0),
        "pp_balls": float(row.pp_balls or 0),
        "middle_runs": float(row.middle_runs or 0),
        "middle_wickets": float(row.middle_wickets or 0),
        "middle_dots": float(row.middle_dots or 0),
        "middle_boundaries": float(row.middle_boundaries or 0),
        "middle_balls": float(row.middle_balls or 0),
        "death_runs": float(row.death_runs or 0),
        "death_wickets": float(row.death_wickets or 0),
        "death_dots": float(row.death_dots or 0),
        "death_boundaries": float(row.death_boundaries or 0),
        "death_balls": float(row.death_balls or 0),
    }


def _fetch_precomputed_player_batting(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Dict[str, float]]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    weight_case = _weight_case_sql()

    rows = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bs.*,
                    {weight_case} AS w
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE bs.striker = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                striker AS player_name,
                COUNT(DISTINCT match_id) AS matches,
                COALESCE(SUM(runs * w), 0) AS runs,
                COALESCE(SUM(balls_faced * w), 0) AS balls,
                COALESCE(SUM(wickets * w), 0) AS dismissals,
                COALESCE(SUM(dots * w), 0) AS dots,
                COALESCE(SUM(fours * w), 0) AS fours,
                COALESCE(SUM(sixes * w), 0) AS sixes,
                COALESCE(SUM((fours + sixes) * w), 0) AS boundaries,
                COALESCE(SUM(pp_runs * w), 0) AS pp_runs,
                COALESCE(SUM(pp_balls * w), 0) AS pp_balls,
                COALESCE(SUM(pp_wickets * w), 0) AS pp_wickets,
                COALESCE(SUM(pp_boundaries * w), 0) AS pp_boundaries,
                COALESCE(SUM(pp_dots * w), 0) AS pp_dots,
                COALESCE(SUM(middle_runs * w), 0) AS middle_runs,
                COALESCE(SUM(middle_balls * w), 0) AS middle_balls,
                COALESCE(SUM(middle_wickets * w), 0) AS middle_wickets,
                COALESCE(SUM(middle_boundaries * w), 0) AS middle_boundaries,
                COALESCE(SUM(middle_dots * w), 0) AS middle_dots,
                COALESCE(SUM(death_runs * w), 0) AS death_runs,
                COALESCE(SUM(death_balls * w), 0) AS death_balls,
                COALESCE(SUM(death_wickets * w), 0) AS death_wickets,
                COALESCE(SUM(death_boundaries * w), 0) AS death_boundaries,
                COALESCE(SUM(death_dots * w), 0) AS death_dots
            FROM weighted
            GROUP BY striker
            """
        ),
        params,
    ).fetchall()

    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        out[row.player_name] = {
            "matches": float(row.matches or 0),
            "runs": float(row.runs or 0),
            "balls": float(row.balls or 0),
            "dismissals": float(row.dismissals or 0),
            "dots": float(row.dots or 0),
            "fours": float(row.fours or 0),
            "sixes": float(row.sixes or 0),
            "boundaries": float(row.boundaries or 0),
            "pp_runs": float(row.pp_runs or 0),
            "pp_balls": float(row.pp_balls or 0),
            "pp_wickets": float(row.pp_wickets or 0),
            "pp_boundaries": float(row.pp_boundaries or 0),
            "pp_dots": float(row.pp_dots or 0),
            "middle_runs": float(row.middle_runs or 0),
            "middle_balls": float(row.middle_balls or 0),
            "middle_wickets": float(row.middle_wickets or 0),
            "middle_boundaries": float(row.middle_boundaries or 0),
            "middle_dots": float(row.middle_dots or 0),
            "death_runs": float(row.death_runs or 0),
            "death_balls": float(row.death_balls or 0),
            "death_wickets": float(row.death_wickets or 0),
            "death_boundaries": float(row.death_boundaries or 0),
            "death_dots": float(row.death_dots or 0),
        }
    return out


def _fetch_precomputed_player_bowling(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Dict[str, float]]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    weight_case = _weight_case_sql()

    rows = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bw.*,
                    {weight_case} AS w
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE bw.bowler = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                bowler AS player_name,
                COUNT(DISTINCT match_id) AS matches,
                COALESCE(SUM(runs_conceded * w), 0) AS runs_conceded,
                COALESCE(SUM(wickets * w), 0) AS wickets,
                COALESCE(SUM(dots * w), 0) AS dots,
                COALESCE(SUM((fours_conceded + sixes_conceded) * w), 0) AS boundaries_conceded,
                COALESCE(
                    SUM(
                        (FLOOR(COALESCE(overs, 0)) * 6
                        + ROUND((COALESCE(overs, 0) - FLOOR(COALESCE(overs, 0))) * 10)) * w
                    ),
                    0
                ) AS balls,
                COALESCE(SUM(pp_runs * w), 0) AS pp_runs,
                COALESCE(SUM(pp_wickets * w), 0) AS pp_wickets,
                COALESCE(SUM(pp_dots * w), 0) AS pp_dots,
                COALESCE(SUM(pp_boundaries * w), 0) AS pp_boundaries,
                COALESCE(
                    SUM(
                        (FLOOR(COALESCE(pp_overs, 0)) * 6
                        + ROUND((COALESCE(pp_overs, 0) - FLOOR(COALESCE(pp_overs, 0))) * 10)) * w
                    ),
                    0
                ) AS pp_balls,
                COALESCE(SUM(middle_runs * w), 0) AS middle_runs,
                COALESCE(SUM(middle_wickets * w), 0) AS middle_wickets,
                COALESCE(SUM(middle_dots * w), 0) AS middle_dots,
                COALESCE(SUM(middle_boundaries * w), 0) AS middle_boundaries,
                COALESCE(
                    SUM(
                        (FLOOR(COALESCE(middle_overs, 0)) * 6
                        + ROUND((COALESCE(middle_overs, 0) - FLOOR(COALESCE(middle_overs, 0))) * 10)) * w
                    ),
                    0
                ) AS middle_balls,
                COALESCE(SUM(death_runs * w), 0) AS death_runs,
                COALESCE(SUM(death_wickets * w), 0) AS death_wickets,
                COALESCE(SUM(death_dots * w), 0) AS death_dots,
                COALESCE(SUM(death_boundaries * w), 0) AS death_boundaries,
                COALESCE(
                    SUM(
                        (FLOOR(COALESCE(death_overs, 0)) * 6
                        + ROUND((COALESCE(death_overs, 0) - FLOOR(COALESCE(death_overs, 0))) * 10)) * w
                    ),
                    0
                ) AS death_balls
            FROM weighted
            GROUP BY bowler
            """
        ),
        params,
    ).fetchall()

    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        out[row.player_name] = {
            "matches": float(row.matches or 0),
            "runs_conceded": float(row.runs_conceded or 0),
            "wickets": float(row.wickets or 0),
            "dots": float(row.dots or 0),
            "boundaries_conceded": float(row.boundaries_conceded or 0),
            "balls": float(row.balls or 0),
            "pp_runs": float(row.pp_runs or 0),
            "pp_wickets": float(row.pp_wickets or 0),
            "pp_dots": float(row.pp_dots or 0),
            "pp_boundaries": float(row.pp_boundaries or 0),
            "pp_balls": float(row.pp_balls or 0),
            "middle_runs": float(row.middle_runs or 0),
            "middle_wickets": float(row.middle_wickets or 0),
            "middle_dots": float(row.middle_dots or 0),
            "middle_boundaries": float(row.middle_boundaries or 0),
            "middle_balls": float(row.middle_balls or 0),
            "death_runs": float(row.death_runs or 0),
            "death_wickets": float(row.death_wickets or 0),
            "death_dots": float(row.death_dots or 0),
            "death_boundaries": float(row.death_boundaries or 0),
            "death_balls": float(row.death_balls or 0),
        }
    return out


def _fetch_precomputed_player_phase_sixes(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Dict[str, float]]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    weight_case = _weight_case_sql()

    rows = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    d.batter AS player_name,
                    CASE
                        WHEN d.over < 6 THEN 'pp'
                        WHEN d.over < 15 THEN 'middle'
                        ELSE 'death'
                    END AS phase,
                    {weight_case} AS w
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.batter = ANY(:players)
                  AND d.runs_off_bat = 6
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                player_name,
                COALESCE(SUM(CASE WHEN phase = 'pp' THEN w ELSE 0 END), 0) AS pp_sixes,
                COALESCE(SUM(CASE WHEN phase = 'middle' THEN w ELSE 0 END), 0) AS middle_sixes,
                COALESCE(SUM(CASE WHEN phase = 'death' THEN w ELSE 0 END), 0) AS death_sixes
            FROM weighted
            GROUP BY player_name
            """
        ),
        params,
    ).fetchall()

    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        out[row.player_name] = {
            "pp_sixes": float(row.pp_sixes or 0),
            "middle_sixes": float(row.middle_sixes or 0),
            "death_sixes": float(row.death_sixes or 0),
        }
    return out


def _fetch_precomputed_venue_batting_map(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Dict[str, Any]]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    weight_case = _weight_case_sql()

    rows = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bs.striker AS player_name,
                    m.venue,
                    bs.runs,
                    bs.balls_faced,
                    bs.wickets,
                    {weight_case} AS w
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE bs.striker = ANY(:players)
                  AND m.competition = 'Indian Premier League'
                  AND m.venue IS NOT NULL
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                player_name,
                venue,
                COALESCE(SUM(runs * w), 0) AS runs,
                COALESCE(SUM(balls_faced * w), 0) AS balls,
                COALESCE(SUM(wickets * w), 0) AS dismissals
            FROM weighted
            GROUP BY player_name, venue
            """
        ),
        params,
    ).fetchall()

    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        player = out.setdefault(
            row.player_name,
            {"runs": 0.0, "balls": 0.0, "dismissals": 0.0, "venues": set()},
        )
        player["runs"] += float(row.runs or 0)
        player["balls"] += float(row.balls or 0)
        player["dismissals"] += float(row.dismissals or 0)
        if row.venue:
            player["venues"].add(row.venue)
    return out


def _fetch_precomputed_venue_bowling_map(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Dict[str, Any]]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    weight_case = _weight_case_sql()

    rows = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bw.bowler AS player_name,
                    m.venue,
                    bw.runs_conceded,
                    (FLOOR(COALESCE(bw.overs, 0)) * 6
                    + ROUND((COALESCE(bw.overs, 0) - FLOOR(COALESCE(bw.overs, 0))) * 10)) AS balls,
                    {weight_case} AS w
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE bw.bowler = ANY(:players)
                  AND m.competition = 'Indian Premier League'
                  AND m.venue IS NOT NULL
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                player_name,
                venue,
                COALESCE(SUM(runs_conceded * w), 0) AS runs,
                COALESCE(SUM(balls * w), 0) AS balls
            FROM weighted
            GROUP BY player_name, venue
            """
        ),
        params,
    ).fetchall()

    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        player = out.setdefault(
            row.player_name,
            {"runs": 0.0, "balls": 0.0, "venues": set()},
        )
        player["runs"] += float(row.runs or 0)
        player["balls"] += float(row.balls or 0)
        if row.venue:
            player["venues"].add(row.venue)
    return out


def _fetch_precomputed_squad_depth_map(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Dict[str, float]]:
    if not players:
        return {}

    start, end = date_range
    rows = db.execute(
        text(
            """
            WITH roster AS (
                SELECT UNNEST(:players) AS player_name
            ),
            bat AS (
                SELECT
                    bs.striker AS player_name,
                    COUNT(DISTINCT bs.match_id) AS batting_matches,
                    COALESCE(SUM(bs.runs), 0) AS runs
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE bs.striker = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
                GROUP BY bs.striker
            ),
            bowl AS (
                SELECT
                    bw.bowler AS player_name,
                    COUNT(DISTINCT bw.match_id) AS bowling_matches,
                    COALESCE(SUM(bw.wickets), 0) AS wickets
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE bw.bowler = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
                GROUP BY bw.bowler
            )
            SELECT
                r.player_name,
                COALESCE(bat.batting_matches, 0) AS batting_matches,
                COALESCE(bat.runs, 0) AS runs,
                COALESCE(bowl.bowling_matches, 0) AS bowling_matches,
                COALESCE(bowl.wickets, 0) AS wickets
            FROM roster r
            LEFT JOIN bat ON bat.player_name = r.player_name
            LEFT JOIN bowl ON bowl.player_name = r.player_name
            """
        ),
        {"players": players, "start_date": start, "end_date": end},
    ).fetchall()

    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        out[row.player_name] = {
            "batting_matches": float(row.batting_matches or 0),
            "runs": float(row.runs or 0),
            "bowling_matches": float(row.bowling_matches or 0),
            "wickets": float(row.wickets or 0),
        }
    return out


def _fetch_precomputed_batting_kind_map(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    kind_case = BOWLER_CATEGORY_SQL.replace("bowler_type", "d.bowler_type")
    weight_case = _weight_case_sql()

    rows = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    d.batter AS player_name,
                    {kind_case} AS kind,
                    d.runs_off_bat,
                    d.extras,
                    d.player_dismissed,
                    d.batter,
                    {weight_case} AS w
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.batter = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                player_name,
                kind,
                COALESCE(SUM(w), 0) AS balls,
                COALESCE(SUM(runs_off_bat * w), 0) AS runs,
                COALESCE(SUM(CASE WHEN runs_off_bat = 0 AND COALESCE(extras, 0) = 0 THEN w ELSE 0 END), 0) AS dots,
                COALESCE(SUM(CASE WHEN runs_off_bat IN (4, 6) THEN w ELSE 0 END), 0) AS boundaries,
                COALESCE(SUM(CASE WHEN player_dismissed = batter THEN w ELSE 0 END), 0) AS dismissals
            FROM weighted
            WHERE kind IS NOT NULL
            GROUP BY player_name, kind
            """
        ),
        params,
    ).fetchall()

    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in rows:
        out.setdefault(row.player_name, {})
        out[row.player_name][row.kind] = {
            "balls": float(row.balls or 0),
            "runs": float(row.runs or 0),
            "dots": float(row.dots or 0),
            "boundaries": float(row.boundaries or 0),
            "dismissals": float(row.dismissals or 0),
        }
    return out


def _fetch_precomputed_bowling_kind_map(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    kind_case = BOWLER_CATEGORY_SQL.replace("bowler_type", "p.bowler_type")
    weight_case = _weight_case_sql()

    rows = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bw.bowler AS player_name,
                    {kind_case} AS kind,
                    bw.runs_conceded,
                    bw.wickets,
                    (FLOOR(COALESCE(bw.overs, 0)) * 6
                    + ROUND((COALESCE(bw.overs, 0) - FLOOR(COALESCE(bw.overs, 0))) * 10)) AS balls,
                    {weight_case} AS w
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                LEFT JOIN players p ON LOWER(p.name) = LOWER(bw.bowler)
                WHERE bw.bowler = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                player_name,
                kind,
                COALESCE(SUM(runs_conceded * w), 0) AS runs,
                COALESCE(SUM(wickets * w), 0) AS wickets,
                COALESCE(SUM(balls * w), 0) AS balls
            FROM weighted
            WHERE kind IS NOT NULL
            GROUP BY player_name, kind
            """
        ),
        params,
    ).fetchall()

    out: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in rows:
        out.setdefault(row.player_name, {})
        out[row.player_name][row.kind] = {
            "runs": float(row.runs or 0),
            "wickets": float(row.wickets or 0),
            "balls": float(row.balls or 0),
        }
    return out


def _phase_batting_metrics(prefix: str, metrics: Dict[str, float]) -> Dict[str, Optional[float]]:
    runs = metrics.get(f"{prefix}_runs", 0.0)
    balls = metrics.get(f"{prefix}_balls", 0.0)
    wickets = metrics.get(f"{prefix}_wickets", 0.0)
    boundaries = metrics.get(f"{prefix}_boundaries", 0.0)
    dots = metrics.get(f"{prefix}_dots", 0.0)
    sixes = metrics.get(f"{prefix}_sixes", 0.0)

    return {
        f"{prefix}_sr": _safe_pct(runs, balls),
        f"{prefix}_avg": _safe_div(runs, wickets),
        f"{prefix}_boundary_pct": _safe_pct(boundaries, balls),
        f"{prefix}_dot_pct": _safe_pct(dots, balls),
        f"{prefix}_balls_per_six": _safe_div(balls, sixes),
    }


def _phase_bowling_metrics(prefix: str, metrics: Dict[str, float]) -> Dict[str, Optional[float]]:
    runs = metrics.get(f"{prefix}_runs", 0.0)
    balls = metrics.get(f"{prefix}_balls", 0.0)
    wickets = metrics.get(f"{prefix}_wickets", 0.0)
    dots = metrics.get(f"{prefix}_dots", 0.0)
    boundaries = metrics.get(f"{prefix}_boundaries", 0.0)

    return {
        f"{prefix}_economy": _safe_economy(runs, balls),
        f"{prefix}_bowling_sr": _safe_bowling_sr(balls, wickets),
        f"{prefix}_dot_pct": _safe_pct(dots, balls),
        f"{prefix}_boundary_pct_conceded": _safe_pct(boundaries, balls),
    }


def _fetch_batting_pace_spin_metrics(
    batters: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Optional[float]]:
    if not batters:
        return {}

    params = _weight_params(*date_range)
    params["batters"] = batters
    kind_case = BOWLER_CATEGORY_SQL.replace("bowler_type", "d.bowler_type")
    weight_case = _weight_case_sql()

    rows = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    {kind_case} AS kind,
                    d.runs_off_bat,
                    d.extras,
                    d.player_dismissed,
                    d.batter,
                    {weight_case} AS w
                FROM deliveries d
                JOIN matches m ON d.match_id = m.id
                WHERE d.batter = ANY(:batters)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                kind,
                COALESCE(SUM(w), 0) AS balls,
                COALESCE(SUM(runs_off_bat * w), 0) AS runs,
                COALESCE(SUM(CASE WHEN runs_off_bat = 0 AND COALESCE(extras, 0) = 0 THEN w ELSE 0 END), 0) AS dots,
                COALESCE(SUM(CASE WHEN runs_off_bat IN (4, 6) THEN w ELSE 0 END), 0) AS boundaries,
                COALESCE(SUM(CASE WHEN player_dismissed = batter THEN w ELSE 0 END), 0) AS dismissals
            FROM weighted
            WHERE kind IS NOT NULL
            GROUP BY kind
            """
        ),
        params,
    ).fetchall()

    kind_map = {row.kind: row for row in rows}

    def _kind_stats(kind: str) -> Dict[str, Optional[float]]:
        row = kind_map.get(kind)
        if not row:
            return {"sr": None, "avg": None, "boundary_pct": None, "dot_pct": None, "balls": 0.0}
        balls = float(row.balls or 0)
        runs = float(row.runs or 0)
        dismissals = float(row.dismissals or 0)
        dots = float(row.dots or 0)
        boundaries = float(row.boundaries or 0)
        return {
            "sr": _safe_pct(runs, balls),
            "avg": _safe_div(runs, dismissals),
            "boundary_pct": _safe_pct(boundaries, balls),
            "dot_pct": _safe_pct(dots, balls),
            "balls": balls,
        }

    pace = _kind_stats("pace")
    spin = _kind_stats("spin")

    return {
        "bat_sr_vs_pace": pace["sr"],
        "bat_sr_vs_spin": spin["sr"],
        "bat_avg_vs_pace": pace["avg"],
        "bat_avg_vs_spin": spin["avg"],
        "bat_boundary_pct_vs_pace": pace["boundary_pct"],
        "bat_boundary_pct_vs_spin": spin["boundary_pct"],
        "bat_dot_pct_vs_pace": pace["dot_pct"],
        "bat_dot_pct_vs_spin": spin["dot_pct"],
        "bat_balls_vs_pace": pace["balls"],
        "bat_balls_vs_spin": spin["balls"],
    }


def _fetch_bowling_pace_spin_metrics(
    bowlers: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Optional[float]]:
    if not bowlers:
        return {}

    params = _weight_params(*date_range)
    params["bowlers"] = bowlers
    kind_case = BOWLER_CATEGORY_SQL.replace("bowler_type", "p.bowler_type")
    weight_case = _weight_case_sql()

    rows = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    {kind_case} AS kind,
                    bw.runs_conceded,
                    bw.wickets,
                    (FLOOR(COALESCE(bw.overs, 0)) * 6
                    + ROUND((COALESCE(bw.overs, 0) - FLOOR(COALESCE(bw.overs, 0))) * 10)) AS balls,
                    {weight_case} AS w
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                LEFT JOIN players p ON LOWER(p.name) = LOWER(bw.bowler)
                WHERE bw.bowler = ANY(:bowlers)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                kind,
                COALESCE(SUM(runs_conceded * w), 0) AS runs,
                COALESCE(SUM(wickets * w), 0) AS wickets,
                COALESCE(SUM(balls * w), 0) AS balls
            FROM weighted
            WHERE kind IS NOT NULL
            GROUP BY kind
            """
        ),
        params,
    ).fetchall()

    kind_map = {row.kind: row for row in rows}

    def _kind_stats(kind: str) -> Dict[str, Optional[float]]:
        row = kind_map.get(kind)
        if not row:
            return {"economy": None, "sr": None, "balls": 0.0}
        runs = float(row.runs or 0)
        balls = float(row.balls or 0)
        wickets = float(row.wickets or 0)
        return {
            "economy": _safe_economy(runs, balls),
            "sr": _safe_bowling_sr(balls, wickets),
            "balls": balls,
        }

    pace = _kind_stats("pace")
    spin = _kind_stats("spin")

    return {
        "bowl_economy_pace": pace["economy"],
        "bowl_economy_spin": spin["economy"],
        "bowl_sr_pace": pace["sr"],
        "bowl_sr_spin": spin["sr"],
        "bowl_balls_pace": pace["balls"],
        "bowl_balls_spin": spin["balls"],
    }


def _total_ipl_venues(db: Session) -> int:
    row = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT venue)
            FROM matches
            WHERE competition = 'Indian Premier League'
              AND venue IS NOT NULL
            """
        )
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _fetch_venue_experience_metrics(
    players: List[str],
    date_range: Tuple[date, date],
    total_venues: int,
    db: Session,
) -> Dict[str, Optional[float]]:
    if not players:
        return {}

    params = _weight_params(*date_range)
    params["players"] = players
    weight_case = _weight_case_sql()

    bat_row = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bs.runs,
                    bs.balls_faced,
                    bs.wickets,
                    m.venue,
                    {weight_case} AS w
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE bs.striker = ANY(:players)
                  AND m.competition = 'Indian Premier League'
                  AND m.venue IS NOT NULL
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                COALESCE(SUM(runs * w), 0) AS runs,
                COALESCE(SUM(balls_faced * w), 0) AS balls,
                COALESCE(SUM(wickets * w), 0) AS dismissals,
                COUNT(DISTINCT venue) AS venues
            FROM weighted
            """
        ),
        params,
    ).fetchone()

    bowl_row = db.execute(
        text(
            f"""
            WITH weighted AS (
                SELECT
                    bw.runs_conceded,
                    (FLOOR(COALESCE(bw.overs, 0)) * 6
                    + ROUND((COALESCE(bw.overs, 0) - FLOOR(COALESCE(bw.overs, 0))) * 10)) AS balls,
                    m.venue,
                    {weight_case} AS w
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE bw.bowler = ANY(:players)
                  AND m.competition = 'Indian Premier League'
                  AND m.venue IS NOT NULL
                  AND m.date >= :start_date
                  AND m.date <= :end_date
            )
            SELECT
                COALESCE(SUM(runs_conceded * w), 0) AS runs,
                COALESCE(SUM(balls * w), 0) AS balls,
                COUNT(DISTINCT venue) AS venues
            FROM weighted
            """
        ),
        params,
    ).fetchone()

    venue_count = max(int(bat_row.venues or 0), int(bowl_row.venues or 0))
    coverage = _safe_div(venue_count, total_venues if total_venues > 0 else None)

    return {
        "venue_bat_sr": _safe_pct(float(bat_row.runs or 0), float(bat_row.balls or 0)),
        "venue_bat_avg": _safe_div(float(bat_row.runs or 0), float(bat_row.dismissals or 0)),
        "venue_bowl_economy": _safe_economy(float(bowl_row.runs or 0), float(bowl_row.balls or 0)),
        "venue_coverage": coverage,
        "venue_count": float(venue_count),
    }


def _build_venue_archetypes(
    db: Session,
    date_range: Tuple[date, date],
) -> Dict[str, str]:
    start, end = date_range
    rows = db.execute(
        text(
            """
            SELECT
                ground AS venue,
                COALESCE(SUM(CASE WHEN LOWER(COALESCE(bowl_kind, '')) LIKE '%pace%' THEN score ELSE 0 END), 0) AS pace_runs,
                COALESCE(SUM(CASE WHEN LOWER(COALESCE(bowl_kind, '')) LIKE '%pace%' THEN 1 ELSE 0 END), 0) AS pace_balls,
                COALESCE(SUM(CASE WHEN LOWER(COALESCE(bowl_kind, '')) LIKE '%spin%' THEN score ELSE 0 END), 0) AS spin_runs,
                COALESCE(SUM(CASE WHEN LOWER(COALESCE(bowl_kind, '')) LIKE '%spin%' THEN 1 ELSE 0 END), 0) AS spin_balls
            FROM delivery_details
            WHERE ground IS NOT NULL
              AND date >= :start_date
              AND date <= :end_date
              AND bowl_kind IS NOT NULL
              AND (competition = 'Indian Premier League' OR competition = 'IPL')
            GROUP BY ground
            """
        ),
        {"start_date": start, "end_date": end},
    ).fetchall()

    if not rows:
        kind_case = BOWLER_CATEGORY_SQL.replace("bowler_type", "d.bowler_type")
        rows = db.execute(
            text(
                f"""
                WITH classified AS (
                    SELECT
                        m.venue AS venue,
                        {kind_case} AS kind,
                        COALESCE(d.runs_off_bat, 0) + COALESCE(d.extras, 0) AS runs
                    FROM deliveries d
                    JOIN matches m ON d.match_id = m.id
                    WHERE m.venue IS NOT NULL
                      AND m.date >= :start_date
                      AND m.date <= :end_date
                      AND m.competition = 'Indian Premier League'
                )
                SELECT
                    venue,
                    COALESCE(SUM(CASE WHEN kind = 'pace' THEN runs ELSE 0 END), 0) AS pace_runs,
                    COALESCE(SUM(CASE WHEN kind = 'pace' THEN 1 ELSE 0 END), 0) AS pace_balls,
                    COALESCE(SUM(CASE WHEN kind = 'spin' THEN runs ELSE 0 END), 0) AS spin_runs,
                    COALESCE(SUM(CASE WHEN kind = 'spin' THEN 1 ELSE 0 END), 0) AS spin_balls
                FROM classified
                GROUP BY venue
                """
            ),
            {"start_date": start, "end_date": end},
        ).fetchall()

    archetypes: Dict[str, str] = {}
    for row in rows:
        pace_balls = float(row.pace_balls or 0)
        spin_balls = float(row.spin_balls or 0)
        if pace_balls < 120 or spin_balls < 120:
            continue

        pace_econ = _safe_economy(float(row.pace_runs or 0), pace_balls)
        spin_econ = _safe_economy(float(row.spin_runs or 0), spin_balls)
        if pace_econ is None or spin_econ is None:
            continue

        if pace_econ + 0.25 < spin_econ:
            archetype = "pace_friendly"
        elif spin_econ + 0.25 < pace_econ:
            archetype = "spin_friendly"
        else:
            archetype = "balanced"

        archetypes[_canonical_venue(row.venue)] = archetype

    return archetypes


def _compute_archetype_metrics(
    match_rows: List[Dict[str, Any]],
    venue_archetypes: Dict[str, str],
) -> Dict[str, Optional[float]]:
    if not venue_archetypes:
        return {
            "archetype_consistency": None,
            "archetype_coverage": None,
            "archetype_mean_win_pct": None,
        }

    buckets = {
        "pace_friendly": {"wins": 0, "decisions": 0},
        "spin_friendly": {"wins": 0, "decisions": 0},
        "balanced": {"wins": 0, "decisions": 0},
    }

    for row in match_rows:
        if not row.get("winner"):
            continue
        archetype = venue_archetypes.get(_canonical_venue(row.get("venue")))
        if archetype not in buckets:
            continue
        buckets[archetype]["decisions"] += 1
        if row.get("team_won"):
            buckets[archetype]["wins"] += 1

    pct_values: List[float] = []
    covered = 0
    for key in ("pace_friendly", "spin_friendly", "balanced"):
        wins = buckets[key]["wins"]
        decisions = buckets[key]["decisions"]
        pct = _safe_div(wins, decisions)
        if pct is not None:
            pct_values.append(pct)
            covered += 1

    if not pct_values:
        consistency = None
        mean_pct = None
    elif len(pct_values) == 1:
        consistency = 0.5
        mean_pct = pct_values[0]
    else:
        mean_pct = sum(pct_values) / len(pct_values)
        variance = sum((value - mean_pct) ** 2 for value in pct_values) / len(pct_values)
        std_dev = sqrt(variance)
        consistency = max(0.0, min(1.0, 1.0 - (std_dev / 0.5)))

    return {
        "archetype_consistency": consistency,
        "archetype_coverage": covered / 3.0,
        "archetype_mean_win_pct": mean_pct,
    }


def _fetch_squad_depth_metrics(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Optional[float]]:
    if not players:
        return {}

    start, end = date_range
    rows = db.execute(
        text(
            """
            WITH roster AS (
                SELECT UNNEST(:players) AS player_name
            ),
            bat AS (
                SELECT
                    bs.striker AS player_name,
                    COUNT(DISTINCT bs.match_id) AS batting_matches,
                    COALESCE(SUM(bs.runs), 0) AS runs
                FROM batting_stats bs
                JOIN matches m ON bs.match_id = m.id
                WHERE bs.striker = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
                GROUP BY bs.striker
            ),
            bowl AS (
                SELECT
                    bw.bowler AS player_name,
                    COUNT(DISTINCT bw.match_id) AS bowling_matches,
                    COALESCE(SUM(bw.wickets), 0) AS wickets
                FROM bowling_stats bw
                JOIN matches m ON bw.match_id = m.id
                WHERE bw.bowler = ANY(:players)
                  AND m.date >= :start_date
                  AND m.date <= :end_date
                GROUP BY bw.bowler
            )
            SELECT
                r.player_name,
                COALESCE(bat.batting_matches, 0) AS batting_matches,
                COALESCE(bat.runs, 0) AS runs,
                COALESCE(bowl.bowling_matches, 0) AS bowling_matches,
                COALESCE(bowl.wickets, 0) AS wickets
            FROM roster r
            LEFT JOIN bat ON bat.player_name = r.player_name
            LEFT JOIN bowl ON bowl.player_name = r.player_name
            """
        ),
        {"players": players, "start_date": start, "end_date": end},
    ).fetchall()

    batting_contributions = [float(row.runs or 0) for row in rows if float(row.runs or 0) > 0]
    bowling_contributions = [float(row.wickets or 0) for row in rows if float(row.wickets or 0) > 0]

    experienced = 0
    all_rounders = 0
    for row in rows:
        batting_matches = int(row.batting_matches or 0)
        bowling_matches = int(row.bowling_matches or 0)
        if max(batting_matches, bowling_matches) > 0:
            experienced += 1
        role = _classify_role(batting_matches, bowling_matches)
        if role == "all_rounder":
            all_rounders += 1

    squad_size = len(players)
    return {
        "batting_depth_gini": _compute_gini(batting_contributions),
        "bowling_depth_gini": _compute_gini(bowling_contributions),
        "all_rounder_count": float(all_rounders),
        "bench_strength": float(experienced),
        "bench_experience_pct": _safe_div(experienced, squad_size),
        "roster_size": float(squad_size),
        "batting_contributor_count": float(len(batting_contributions)),
        "bowling_contributor_count": float(len(bowling_contributions)),
    }


def _sum_player_metrics(
    player_names: List[str],
    player_map: Dict[str, Dict[str, float]],
    keys: List[str],
) -> Dict[str, float]:
    totals = {key: 0.0 for key in keys}
    for player_name in player_names:
        metrics = player_map.get(player_name)
        if not metrics:
            continue
        for key in keys:
            totals[key] += float(metrics.get(key, 0) or 0)
    return totals


def _aggregate_batting_from_precomputed(
    player_names: List[str],
    precomputed: Dict[str, Any],
) -> Dict[str, float]:
    base_keys = [
        "pp_runs",
        "pp_balls",
        "pp_wickets",
        "pp_boundaries",
        "pp_dots",
        "middle_runs",
        "middle_balls",
        "middle_wickets",
        "middle_boundaries",
        "middle_dots",
        "death_runs",
        "death_balls",
        "death_wickets",
        "death_boundaries",
        "death_dots",
    ]
    totals = _sum_player_metrics(
        player_names,
        precomputed.get("player_batting", {}),
        base_keys,
    )
    totals.update({"pp_sixes": 0.0, "middle_sixes": 0.0, "death_sixes": 0.0})

    sixes_map = precomputed.get("player_phase_sixes", {})
    for player_name in player_names:
        sixes = sixes_map.get(player_name)
        if not sixes:
            continue
        totals["pp_sixes"] += float(sixes.get("pp_sixes", 0) or 0)
        totals["middle_sixes"] += float(sixes.get("middle_sixes", 0) or 0)
        totals["death_sixes"] += float(sixes.get("death_sixes", 0) or 0)
    return totals


def _aggregate_bowling_from_precomputed(
    player_names: List[str],
    precomputed: Dict[str, Any],
) -> Dict[str, float]:
    keys = [
        "pp_runs",
        "pp_wickets",
        "pp_dots",
        "pp_boundaries",
        "pp_balls",
        "middle_runs",
        "middle_wickets",
        "middle_dots",
        "middle_boundaries",
        "middle_balls",
        "death_runs",
        "death_wickets",
        "death_dots",
        "death_boundaries",
        "death_balls",
    ]
    return _sum_player_metrics(
        player_names,
        precomputed.get("player_bowling", {}),
        keys,
    )


def _aggregate_pace_spin_from_precomputed(
    player_names: List[str],
    precomputed: Dict[str, Any],
) -> Dict[str, Optional[float]]:
    batting_kind_map = precomputed.get("batting_kind_map", {})
    bowling_kind_map = precomputed.get("bowling_kind_map", {})

    batting_totals = {
        "pace": {"balls": 0.0, "runs": 0.0, "dots": 0.0, "boundaries": 0.0, "dismissals": 0.0},
        "spin": {"balls": 0.0, "runs": 0.0, "dots": 0.0, "boundaries": 0.0, "dismissals": 0.0},
    }
    bowling_totals = {
        "pace": {"runs": 0.0, "balls": 0.0, "wickets": 0.0},
        "spin": {"runs": 0.0, "balls": 0.0, "wickets": 0.0},
    }

    for player_name in player_names:
        player_bat_kinds = batting_kind_map.get(player_name, {})
        for kind in ("pace", "spin"):
            kind_stats = player_bat_kinds.get(kind)
            if not kind_stats:
                continue
            batting_totals[kind]["balls"] += float(kind_stats.get("balls", 0) or 0)
            batting_totals[kind]["runs"] += float(kind_stats.get("runs", 0) or 0)
            batting_totals[kind]["dots"] += float(kind_stats.get("dots", 0) or 0)
            batting_totals[kind]["boundaries"] += float(kind_stats.get("boundaries", 0) or 0)
            batting_totals[kind]["dismissals"] += float(kind_stats.get("dismissals", 0) or 0)

        player_bowl_kinds = bowling_kind_map.get(player_name, {})
        for kind in ("pace", "spin"):
            kind_stats = player_bowl_kinds.get(kind)
            if not kind_stats:
                continue
            bowling_totals[kind]["runs"] += float(kind_stats.get("runs", 0) or 0)
            bowling_totals[kind]["balls"] += float(kind_stats.get("balls", 0) or 0)
            bowling_totals[kind]["wickets"] += float(kind_stats.get("wickets", 0) or 0)

    def _bat_metrics(kind: str) -> Dict[str, Optional[float]]:
        stats = batting_totals[kind]
        balls = stats["balls"]
        runs = stats["runs"]
        dismissals = stats["dismissals"]
        dots = stats["dots"]
        boundaries = stats["boundaries"]
        return {
            "sr": _safe_pct(runs, balls),
            "avg": _safe_div(runs, dismissals),
            "boundary_pct": _safe_pct(boundaries, balls),
            "dot_pct": _safe_pct(dots, balls),
        }

    def _bowl_metrics(kind: str) -> Dict[str, Optional[float]]:
        stats = bowling_totals[kind]
        runs = stats["runs"]
        balls = stats["balls"]
        wickets = stats["wickets"]
        return {
            "economy": _safe_economy(runs, balls),
            "sr": _safe_bowling_sr(balls, wickets),
        }

    pace_bat = _bat_metrics("pace")
    spin_bat = _bat_metrics("spin")
    pace_bowl = _bowl_metrics("pace")
    spin_bowl = _bowl_metrics("spin")

    return {
        "bat_sr_vs_pace": pace_bat["sr"],
        "bat_sr_vs_spin": spin_bat["sr"],
        "bat_avg_vs_pace": pace_bat["avg"],
        "bat_avg_vs_spin": spin_bat["avg"],
        "bat_boundary_pct_vs_pace": pace_bat["boundary_pct"],
        "bat_boundary_pct_vs_spin": spin_bat["boundary_pct"],
        "bat_dot_pct_vs_pace": pace_bat["dot_pct"],
        "bat_dot_pct_vs_spin": spin_bat["dot_pct"],
        "bowl_economy_pace": pace_bowl["economy"],
        "bowl_economy_spin": spin_bowl["economy"],
        "bowl_sr_pace": pace_bowl["sr"],
        "bowl_sr_spin": spin_bowl["sr"],
        "bat_balls_vs_pace": batting_totals["pace"]["balls"],
        "bat_balls_vs_spin": batting_totals["spin"]["balls"],
        "bowl_balls_pace": bowling_totals["pace"]["balls"],
        "bowl_balls_spin": bowling_totals["spin"]["balls"],
    }


def _aggregate_venue_experience_from_precomputed(
    player_names: List[str],
    precomputed: Dict[str, Any],
    total_venues: int,
) -> Dict[str, Optional[float]]:
    batting_map = precomputed.get("venue_batting_map", {})
    bowling_map = precomputed.get("venue_bowling_map", {})

    bat_runs = 0.0
    bat_balls = 0.0
    bat_dismissals = 0.0
    bowl_runs = 0.0
    bowl_balls = 0.0
    bat_venues: Set[str] = set()
    bowl_venues: Set[str] = set()

    for player_name in player_names:
        bat = batting_map.get(player_name)
        if bat:
            bat_runs += float(bat.get("runs", 0) or 0)
            bat_balls += float(bat.get("balls", 0) or 0)
            bat_dismissals += float(bat.get("dismissals", 0) or 0)
            bat_venues.update(bat.get("venues", set()))

        bowl = bowling_map.get(player_name)
        if bowl:
            bowl_runs += float(bowl.get("runs", 0) or 0)
            bowl_balls += float(bowl.get("balls", 0) or 0)
            bowl_venues.update(bowl.get("venues", set()))

    venue_count = max(len(bat_venues), len(bowl_venues))
    coverage = _safe_div(venue_count, total_venues if total_venues > 0 else None)
    return {
        "venue_bat_sr": _safe_pct(bat_runs, bat_balls),
        "venue_bat_avg": _safe_div(bat_runs, bat_dismissals),
        "venue_bowl_economy": _safe_economy(bowl_runs, bowl_balls),
        "venue_coverage": coverage,
        "venue_count": float(venue_count),
    }


def _aggregate_squad_depth_from_precomputed(
    player_names: List[str],
    precomputed: Dict[str, Any],
) -> Dict[str, Optional[float]]:
    squad_depth_map = precomputed.get("squad_depth_map", {})

    batting_contributions: List[float] = []
    bowling_contributions: List[float] = []
    experienced = 0
    all_rounders = 0

    for player_name in player_names:
        summary = squad_depth_map.get(player_name, {})
        batting_matches = int(float(summary.get("batting_matches", 0) or 0))
        bowling_matches = int(float(summary.get("bowling_matches", 0) or 0))
        runs = float(summary.get("runs", 0) or 0)
        wickets = float(summary.get("wickets", 0) or 0)

        if runs > 0:
            batting_contributions.append(runs)
        if wickets > 0:
            bowling_contributions.append(wickets)

        if max(batting_matches, bowling_matches) > 0:
            experienced += 1
        if _classify_role(batting_matches, bowling_matches) == "all_rounder":
            all_rounders += 1

    squad_size = len(player_names)
    return {
        "batting_depth_gini": _compute_gini(batting_contributions),
        "bowling_depth_gini": _compute_gini(bowling_contributions),
        "all_rounder_count": float(all_rounders),
        "bench_strength": float(experienced),
        "bench_experience_pct": _safe_div(experienced, squad_size),
        "roster_size": float(squad_size),
        "batting_contributor_count": float(len(batting_contributions)),
        "bowling_contributor_count": float(len(bowling_contributions)),
    }


def _build_precomputed_maps(
    players: List[str],
    date_range: Tuple[date, date],
    db: Session,
) -> Dict[str, Any]:
    if not players:
        return {
            "player_batting": {},
            "player_phase_sixes": {},
            "player_bowling": {},
            "batting_kind_map": {},
            "bowling_kind_map": {},
            "venue_batting_map": {},
            "venue_bowling_map": {},
            "squad_depth_map": {},
        }

    return {
        "player_batting": _fetch_precomputed_player_batting(players, date_range, db),
        "player_phase_sixes": _fetch_precomputed_player_phase_sixes(players, date_range, db),
        "player_bowling": _fetch_precomputed_player_bowling(players, date_range, db),
        "batting_kind_map": _fetch_precomputed_batting_kind_map(players, date_range, db),
        "bowling_kind_map": _fetch_precomputed_bowling_kind_map(players, date_range, db),
        "venue_batting_map": _fetch_precomputed_venue_batting_map(players, date_range, db),
        "venue_bowling_map": _fetch_precomputed_venue_bowling_map(players, date_range, db),
        "squad_depth_map": _fetch_precomputed_squad_depth_map(players, date_range, db),
    }


def compute_team_metrics(
    team_abbrev: str,
    roster: List[Dict[str, str]],
    date_range: Tuple[date, date],
    db: Session,
    venue_archetypes: Optional[Dict[str, str]] = None,
    total_venues: Optional[int] = None,
    precomputed: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Optional[float]]]:
    player_names = [player["name"] for player in roster if player.get("name")]
    if not player_names:
        return {category: {} for category in CATEGORY_WEIGHTS.keys()}

    use_precomputed = precomputed is not None
    match_rows = _fetch_team_match_rows(team_abbrev, date_range, db)
    win_rate_metrics, situational_metrics = _compute_team_result_metrics(team_abbrev, match_rows)
    elo_metrics = _compute_elo_metrics(match_rows)

    if use_precomputed:
        batting_agg = _aggregate_batting_from_precomputed(player_names, precomputed)
        bowling_agg = _aggregate_bowling_from_precomputed(player_names, precomputed)
    else:
        batting_agg = _fetch_weighted_batting_aggregates(player_names, date_range, db)
        bowling_agg = _fetch_weighted_bowling_aggregates(player_names, date_range, db)

    batting_metrics = {}
    batting_metrics.update(_phase_batting_metrics("pp", batting_agg))
    batting_metrics.update(_phase_batting_metrics("middle", batting_agg))
    batting_metrics.update(_phase_batting_metrics("death", batting_agg))
    batting_metrics.update(
        {
            "pp_balls_used": batting_agg.get("pp_balls"),
            "pp_wickets_used": batting_agg.get("pp_wickets"),
            "middle_balls_used": batting_agg.get("middle_balls"),
            "middle_wickets_used": batting_agg.get("middle_wickets"),
            "death_balls_used": batting_agg.get("death_balls"),
            "death_wickets_used": batting_agg.get("death_wickets"),
        }
    )

    bowling_metrics = {}
    bowling_metrics.update(_phase_bowling_metrics("pp", bowling_agg))
    bowling_metrics.update(_phase_bowling_metrics("middle", bowling_agg))
    bowling_metrics.update(_phase_bowling_metrics("death", bowling_agg))
    bowling_metrics.update(
        {
            "pp_balls_used": bowling_agg.get("pp_balls"),
            "pp_wickets_used": bowling_agg.get("pp_wickets"),
            "middle_balls_used": bowling_agg.get("middle_balls"),
            "middle_wickets_used": bowling_agg.get("middle_wickets"),
            "death_balls_used": bowling_agg.get("death_balls"),
            "death_wickets_used": bowling_agg.get("death_wickets"),
        }
    )

    if use_precomputed:
        pace_spin_metrics = _aggregate_pace_spin_from_precomputed(player_names, precomputed)
    else:
        pace_spin_metrics = {}
        pace_spin_metrics.update(_fetch_batting_pace_spin_metrics(player_names, date_range, db))
        pace_spin_metrics.update(_fetch_bowling_pace_spin_metrics(player_names, date_range, db))

    resolved_total_venues = total_venues if total_venues is not None else _total_ipl_venues(db)
    if use_precomputed:
        venue_metrics = _aggregate_venue_experience_from_precomputed(
            player_names,
            precomputed,
            resolved_total_venues,
        )
    else:
        venue_metrics = _fetch_venue_experience_metrics(
            player_names,
            date_range,
            resolved_total_venues,
            db,
        )
    venue_metrics.update(_compute_archetype_metrics(match_rows, venue_archetypes or {}))

    if use_precomputed:
        squad_depth_metrics = _aggregate_squad_depth_from_precomputed(player_names, precomputed)
    else:
        squad_depth_metrics = _fetch_squad_depth_metrics(player_names, date_range, db)

    out = {
        "win_rate": win_rate_metrics,
        "elo": elo_metrics,
        "batting": batting_metrics,
        "bowling": bowling_metrics,
        "pace_spin": pace_spin_metrics,
        "venue_adaptability": venue_metrics,
        "situational": situational_metrics,
        "squad_depth": squad_depth_metrics,
    }

    # Keep raw payload compact and numeric-only where possible.
    for category, metrics in out.items():
        out[category] = {key: _round(value, 4) for key, value in metrics.items()}

    return out


def _metric_percentiles(
    team_to_value: Dict[str, Optional[float]],
    higher_is_better: bool,
) -> Dict[str, float]:
    present = {team: value for team, value in team_to_value.items() if value is not None}
    if len(present) < 2:
        return {team: 50.0 for team in team_to_value.keys()}

    adjusted = {
        team: (float(value) if higher_is_better else -float(value))
        for team, value in present.items()
    }
    values = sorted(adjusted.values())
    n = len(values)

    scores: Dict[str, float] = {}
    for team, value in adjusted.items():
        lower = sum(1 for candidate in values if candidate < value)
        equal = sum(1 for candidate in values if candidate == value)
        pct = ((lower + 0.5 * equal) / n) * 100.0
        scores[team] = pct

    for team in team_to_value.keys():
        if team not in scores:
            scores[team] = 50.0
    return scores


def _build_prediction_rows(
    team_category_raw: Dict[str, Dict[str, Dict[str, Optional[float]]]],
) -> List[Dict[str, Any]]:
    metric_score_maps: Dict[str, Dict[str, float]] = {}

    for category, metric_defs in CATEGORY_METRIC_DEFS.items():
        for metric_def in metric_defs:
            key = metric_def["key"]
            team_to_value = {
                team: team_category_raw[team].get(category, {}).get(key)
                for team in team_category_raw.keys()
            }
            metric_score_maps[key] = _metric_percentiles(
                team_to_value,
                metric_def["higher_is_better"],
            )

    rows: List[Dict[str, Any]] = []
    for team_abbrev, category_raw in team_category_raw.items():
        category_scores: Dict[str, Dict[str, Any]] = {}
        composite = 0.0

        for category, metric_defs in CATEGORY_METRIC_DEFS.items():
            metric_percentiles = [
                metric_score_maps[metric_def["key"]].get(team_abbrev, 50.0)
                for metric_def in metric_defs
            ]
            score = sum(metric_percentiles) / len(metric_percentiles) if metric_percentiles else 50.0
            composite += score * CATEGORY_WEIGHTS[category]
            category_scores[category] = {
                "score": round(score, 2),
                "raw": category_raw.get(category, {}),
            }

        full_name = (get_ipl_roster(team_abbrev) or {}).get("full_name", team_abbrev)
        rows.append(
            {
                "team": team_abbrev,
                "team_full_name": full_name,
                "composite_score": round(composite, 2),
                "category_scores": category_scores,
            }
        )

    rows.sort(key=lambda row: (-row["composite_score"], row["team"]))
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
        row["total_teams"] = total
    return rows


def _cache_key(start: date, end: date) -> str:
    return f"{start.isoformat()}__{end.isoformat()}"


def compute_all_predictions(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Compute and rank IPL title predictions for all teams.
    """
    start, end = _default_date_range(start_date, end_date)
    key = _cache_key(start, end)
    now = datetime.now(tz=timezone.utc)

    cached = _PREDICTION_CACHE.get(key)
    if cached and not force_refresh:
        age = (now - cached["generated_at"]).total_seconds()
        if age <= _CACHE_TTL_SECONDS:
            return cached["payload"]

    name_cache: Dict[str, Dict[str, str]] = {}
    bulk_name_index = _build_bulk_name_index(db)
    team_rosters: Dict[str, List[Dict[str, str]]] = {}
    for team_abbrev in get_all_ipl_teams():
        team_rosters[team_abbrev] = _resolve_roster_players(
            team_abbrev,
            db,
            name_cache=name_cache,
            bulk_name_index=bulk_name_index,
        )

    all_players = sorted(
        {
            player["name"]
            for roster in team_rosters.values()
            for player in roster
            if player.get("name")
        }
    )
    precomputed = _build_precomputed_maps(all_players, (start, end), db)

    team_raw: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {}
    venue_archetypes = _build_venue_archetypes(db, (start, end))
    venue_count = _total_ipl_venues(db)

    for team_abbrev, roster in team_rosters.items():
        team_raw[team_abbrev] = compute_team_metrics(
            team_abbrev=team_abbrev,
            roster=roster,
            date_range=(start, end),
            db=db,
            venue_archetypes=venue_archetypes,
            total_venues=venue_count,
            precomputed=precomputed,
        )

    ranked_rows = _build_prediction_rows(team_raw)
    payload = {
        "generated_at": now.isoformat(),
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "total_teams": len(ranked_rows),
        "model_explainer": {
            **MODEL_EXPLAINER,
            "category_weights": CATEGORY_WEIGHTS,
            "category_metric_keys": {
                category: [metric_def["key"] for metric_def in metric_defs]
                for category, metric_defs in CATEGORY_METRIC_DEFS.items()
            },
        },
        "predictions": ranked_rows,
    }
    _PREDICTION_CACHE[key] = {"generated_at": now, "payload": payload}
    return payload


def get_team_championship_score_service(
    team_name: str,
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    team_abbrev = get_team_abbrev_from_name(team_name)
    if not team_abbrev:
        raise ValueError(f"Unsupported IPL team: {team_name}")

    bundle = compute_all_predictions(
        db=db,
        start_date=start_date,
        end_date=end_date,
        force_refresh=force_refresh,
    )

    for row in bundle["predictions"]:
        if row["team"] == team_abbrev:
            team_row = dict(row)
            team_row["date_range"] = bundle.get("date_range")
            team_row["generated_at"] = bundle.get("generated_at")
            team_row["model_explainer"] = bundle.get("model_explainer")
            return team_row

    raise ValueError(f"Prediction not found for team: {team_name}")
