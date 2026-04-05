"""
Relative and percentile metrics service for players and teams.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from services.analytics_common import (
    build_matches_filter_sql,
    normalize_leagues,
    percentile_rank,
    safe_rate,
)
from services.matchups import get_all_team_name_variations
from services.player_aliases import get_all_name_variants, get_player_names


def _resolve_effective_start_date(
    *,
    db: Session,
    start_date: Optional[date],
    benchmark_window_matches: int,
) -> Optional[date]:
    if start_date is not None:
        return start_date
    if benchmark_window_matches <= 0:
        return None
    row = db.execute(
        text(
            """
            SELECT date
            FROM matches
            ORDER BY date DESC
            OFFSET :offset
            LIMIT 1
            """
        ),
        {"offset": max(0, benchmark_window_matches - 1)},
    ).fetchone()
    return row[0] if row else None


def _batting_metrics_from_row(row: Optional[Dict]) -> Dict:
    if not row:
        return {
            "innings_count": 0,
            "avg_runs": None,
            "strike_rate": None,
            "fantasy_points_avg": None,
        }
    innings_count = int(row.get("innings_count") or 0)
    runs = float(row.get("runs") or 0)
    balls = float(row.get("balls") or 0)
    fantasy_avg = float(row.get("fantasy_avg") or 0) if row.get("fantasy_avg") is not None else None
    avg_runs = (runs / innings_count) if innings_count else None
    strike_rate = safe_rate(runs, balls, scale=100.0)
    return {
        "innings_count": innings_count,
        "avg_runs": round(avg_runs, 2) if avg_runs is not None else None,
        "strike_rate": round(strike_rate, 2) if strike_rate is not None else None,
        "fantasy_points_avg": round(fantasy_avg, 2) if fantasy_avg is not None else None,
    }


def _bowling_metrics_from_row(row: Optional[Dict]) -> Dict:
    if not row:
        return {
            "innings_count": 0,
            "wickets_per_innings": None,
            "economy": None,
            "bowling_strike_rate": None,
            "fantasy_points_avg": None,
        }
    innings_count = int(row.get("innings_count") or 0)
    wickets = float(row.get("wickets") or 0)
    runs = float(row.get("runs_conceded") or 0)
    balls = float(row.get("balls_bowled") or 0)
    fantasy_avg = float(row.get("fantasy_avg") or 0) if row.get("fantasy_avg") is not None else None
    wkts_per_inns = (wickets / innings_count) if innings_count else None
    economy = safe_rate(runs, balls, scale=6.0)
    bowling_sr = safe_rate(balls, wickets, scale=1.0)
    return {
        "innings_count": innings_count,
        "wickets_per_innings": round(wkts_per_inns, 3) if wkts_per_inns is not None else None,
        "economy": round(economy, 2) if economy is not None else None,
        "bowling_strike_rate": round(bowling_sr, 2) if bowling_sr is not None else None,
        "fantasy_points_avg": round(fantasy_avg, 2) if fantasy_avg is not None else None,
    }


def _metric_payload(
    value: Optional[float],
    values: List[Optional[float]],
    *,
    higher_is_better: bool,
) -> Dict:
    return {
        "value": value,
        "percentile": percentile_rank(value, values, higher_is_better=higher_is_better),
        "higher_is_better": higher_is_better,
    }


def _player_batting_agg(
    *,
    db: Session,
    player_variants: List[str],
    innings: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Optional[Dict]:
    params: Dict = {"player_variants": player_variants, "innings": innings}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            COUNT(*) AS innings_count,
            SUM(COALESCE(bs.runs, 0)) AS runs,
            SUM(COALESCE(bs.balls_faced, 0)) AS balls,
            AVG(bs.fantasy_points) AS fantasy_avg
        FROM batting_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.striker = ANY(:player_variants)
          AND bs.innings = :innings
          {match_filter}
        """
    )
    row = db.execute(query, params).mappings().first()
    return dict(row) if row else None


def _player_bowling_agg(
    *,
    db: Session,
    player_variants: List[str],
    innings: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Optional[Dict]:
    params: Dict = {"player_variants": player_variants, "innings": innings}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            COUNT(*) AS innings_count,
            SUM(COALESCE(bs.runs_conceded, 0)) AS runs_conceded,
            SUM(COALESCE(bs.wickets, 0)) AS wickets,
            SUM((FLOOR(COALESCE(bs.overs, 0))::int * 6) + ROUND((COALESCE(bs.overs, 0) - FLOOR(COALESCE(bs.overs, 0))) * 10)::int) AS balls_bowled,
            AVG(bs.fantasy_points) AS fantasy_avg
        FROM bowling_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.bowler = ANY(:player_variants)
          AND bs.innings = :innings
          {match_filter}
        """
    )
    row = db.execute(query, params).mappings().first()
    return dict(row) if row else None


def _population_batting_values(
    *,
    db: Session,
    innings: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Dict[str, List[Optional[float]]]:
    params: Dict = {"innings": innings}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            bs.striker AS entity,
            COUNT(*) AS innings_count,
            SUM(COALESCE(bs.runs, 0)) AS runs,
            SUM(COALESCE(bs.balls_faced, 0)) AS balls,
            AVG(bs.fantasy_points) AS fantasy_avg
        FROM batting_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.innings = :innings
          {match_filter}
        GROUP BY bs.striker
        HAVING COUNT(*) >= 3
        """
    )
    rows = db.execute(query, params).mappings().all()
    avg_runs: List[Optional[float]] = []
    strike_rates: List[Optional[float]] = []
    fantasy: List[Optional[float]] = []
    for row in rows:
        innings_count = int(row.get("innings_count") or 0)
        runs = float(row.get("runs") or 0)
        balls = float(row.get("balls") or 0)
        avg_runs.append((runs / innings_count) if innings_count else None)
        strike_rates.append(safe_rate(runs, balls, scale=100.0))
        fantasy.append(float(row.get("fantasy_avg")) if row.get("fantasy_avg") is not None else None)
    return {
        "avg_runs": avg_runs,
        "strike_rate": strike_rates,
        "fantasy_points_avg": fantasy,
        "sample_size": [len(rows)],
    }


def _population_bowling_values(
    *,
    db: Session,
    innings: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Dict[str, List[Optional[float]]]:
    params: Dict = {"innings": innings}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            bs.bowler AS entity,
            COUNT(*) AS innings_count,
            SUM(COALESCE(bs.runs_conceded, 0)) AS runs_conceded,
            SUM(COALESCE(bs.wickets, 0)) AS wickets,
            SUM((FLOOR(COALESCE(bs.overs, 0))::int * 6) + ROUND((COALESCE(bs.overs, 0) - FLOOR(COALESCE(bs.overs, 0))) * 10)::int) AS balls_bowled,
            AVG(bs.fantasy_points) AS fantasy_avg
        FROM bowling_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.innings = :innings
          {match_filter}
        GROUP BY bs.bowler
        HAVING COUNT(*) >= 3
        """
    )
    rows = db.execute(query, params).mappings().all()
    wickets_per_innings: List[Optional[float]] = []
    economy: List[Optional[float]] = []
    strike_rate: List[Optional[float]] = []
    fantasy: List[Optional[float]] = []
    for row in rows:
        innings_count = int(row.get("innings_count") or 0)
        runs = float(row.get("runs_conceded") or 0)
        wickets = float(row.get("wickets") or 0)
        balls = float(row.get("balls_bowled") or 0)
        wickets_per_innings.append((wickets / innings_count) if innings_count else None)
        economy.append(safe_rate(runs, balls, scale=6.0))
        strike_rate.append(safe_rate(balls, wickets, scale=1.0))
        fantasy.append(float(row.get("fantasy_avg")) if row.get("fantasy_avg") is not None else None)
    return {
        "wickets_per_innings": wickets_per_innings,
        "economy": economy,
        "bowling_strike_rate": strike_rate,
        "fantasy_points_avg": fantasy,
        "sample_size": [len(rows)],
    }


def _inning_payload(
    *,
    batting_metrics: Dict,
    bowling_metrics: Dict,
    batting_distribution: Dict[str, List[Optional[float]]],
    bowling_distribution: Dict[str, List[Optional[float]]],
) -> Dict:
    sample_size = int((batting_distribution.get("sample_size") or [0])[0] or 0)
    return {
        "batting": {
            "innings_count": batting_metrics["innings_count"],
            "avg_runs": _metric_payload(
                batting_metrics["avg_runs"],
                batting_distribution["avg_runs"],
                higher_is_better=True,
            ),
            "strike_rate": _metric_payload(
                batting_metrics["strike_rate"],
                batting_distribution["strike_rate"],
                higher_is_better=True,
            ),
            "fantasy_points_avg": _metric_payload(
                batting_metrics["fantasy_points_avg"],
                batting_distribution["fantasy_points_avg"],
                higher_is_better=True,
            ),
        },
        "bowling": {
            "innings_count": bowling_metrics["innings_count"],
            "wickets_per_innings": _metric_payload(
                bowling_metrics["wickets_per_innings"],
                bowling_distribution["wickets_per_innings"],
                higher_is_better=True,
            ),
            "economy": _metric_payload(
                bowling_metrics["economy"],
                bowling_distribution["economy"],
                higher_is_better=False,
            ),
            "bowling_strike_rate": _metric_payload(
                bowling_metrics["bowling_strike_rate"],
                bowling_distribution["bowling_strike_rate"],
                higher_is_better=False,
            ),
            "fantasy_points_avg": _metric_payload(
                bowling_metrics["fantasy_points_avg"],
                bowling_distribution["fantasy_points_avg"],
                higher_is_better=True,
            ),
        },
        "benchmark_context": {
            "sample_players_or_teams": sample_size,
            "method": "Innings-specific percentile benchmark across filtered sample.",
        },
    }


def get_player_relative_metrics(
    *,
    db: Session,
    player_name: str,
    benchmark_window_matches: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: Optional[List[str]],
    include_international: bool,
    venue: Optional[str],
) -> Dict:
    effective_start_date = _resolve_effective_start_date(
        db=db,
        start_date=start_date,
        benchmark_window_matches=benchmark_window_matches,
    )
    names = get_player_names(player_name, db)
    variants = get_all_name_variants(
        [player_name, names["legacy_name"], names["details_name"]],
        db,
    )
    expanded = normalize_leagues(leagues)

    payload = {
        "player_name": player_name,
        "resolved_names": names,
        "benchmark_window_matches": benchmark_window_matches,
        "effective_start_date": str(effective_start_date) if effective_start_date else None,
    }

    for innings in (1, 2):
        batting_target = _batting_metrics_from_row(
            _player_batting_agg(
                db=db,
                player_variants=variants,
                innings=innings,
                start_date=effective_start_date,
                end_date=end_date,
                leagues=expanded,
                include_international=include_international,
                venue=venue,
            )
        )
        bowling_target = _bowling_metrics_from_row(
            _player_bowling_agg(
                db=db,
                player_variants=variants,
                innings=innings,
                start_date=effective_start_date,
                end_date=end_date,
                leagues=expanded,
                include_international=include_international,
                venue=venue,
            )
        )
        batting_pop = _population_batting_values(
            db=db,
            innings=innings,
            start_date=effective_start_date,
            end_date=end_date,
            leagues=expanded,
            include_international=include_international,
            venue=venue,
        )
        bowling_pop = _population_bowling_values(
            db=db,
            innings=innings,
            start_date=effective_start_date,
            end_date=end_date,
            leagues=expanded,
            include_international=include_international,
            venue=venue,
        )
        payload[f"innings_{innings}"] = _inning_payload(
            batting_metrics=batting_target,
            bowling_metrics=bowling_target,
            batting_distribution=batting_pop,
            bowling_distribution=bowling_pop,
        )
    return payload


def _team_batting_agg(
    *,
    db: Session,
    team_variants: List[str],
    innings: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Optional[Dict]:
    params: Dict = {"team_variants": team_variants, "innings": innings}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            COUNT(*) AS innings_count,
            SUM(COALESCE(bs.runs, 0)) AS runs,
            SUM(COALESCE(bs.balls_faced, 0)) AS balls,
            AVG(bs.fantasy_points) AS fantasy_avg
        FROM batting_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.batting_team = ANY(:team_variants)
          AND bs.innings = :innings
          {match_filter}
        """
    )
    row = db.execute(query, params).mappings().first()
    return dict(row) if row else None


def _team_bowling_agg(
    *,
    db: Session,
    team_variants: List[str],
    innings: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Optional[Dict]:
    params: Dict = {"team_variants": team_variants, "innings": innings}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            COUNT(*) AS innings_count,
            SUM(COALESCE(bs.runs_conceded, 0)) AS runs_conceded,
            SUM(COALESCE(bs.wickets, 0)) AS wickets,
            SUM((FLOOR(COALESCE(bs.overs, 0))::int * 6) + ROUND((COALESCE(bs.overs, 0) - FLOOR(COALESCE(bs.overs, 0))) * 10)::int) AS balls_bowled,
            AVG(bs.fantasy_points) AS fantasy_avg
        FROM bowling_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.bowling_team = ANY(:team_variants)
          AND bs.innings = :innings
          {match_filter}
        """
    )
    row = db.execute(query, params).mappings().first()
    return dict(row) if row else None


def _team_population_batting_values(
    *,
    db: Session,
    innings: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Dict[str, List[Optional[float]]]:
    params: Dict = {"innings": innings}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            bs.batting_team AS entity,
            COUNT(*) AS innings_count,
            SUM(COALESCE(bs.runs, 0)) AS runs,
            SUM(COALESCE(bs.balls_faced, 0)) AS balls,
            AVG(bs.fantasy_points) AS fantasy_avg
        FROM batting_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.innings = :innings
          {match_filter}
        GROUP BY bs.batting_team
        HAVING COUNT(*) >= 5
        """
    )
    rows = db.execute(query, params).mappings().all()
    avg_runs: List[Optional[float]] = []
    strike_rates: List[Optional[float]] = []
    fantasy: List[Optional[float]] = []
    for row in rows:
        innings_count = int(row.get("innings_count") or 0)
        runs = float(row.get("runs") or 0)
        balls = float(row.get("balls") or 0)
        avg_runs.append((runs / innings_count) if innings_count else None)
        strike_rates.append(safe_rate(runs, balls, scale=100.0))
        fantasy.append(float(row.get("fantasy_avg")) if row.get("fantasy_avg") is not None else None)
    return {
        "avg_runs": avg_runs,
        "strike_rate": strike_rates,
        "fantasy_points_avg": fantasy,
        "sample_size": [len(rows)],
    }


def _team_population_bowling_values(
    *,
    db: Session,
    innings: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    venue: Optional[str],
) -> Dict[str, List[Optional[float]]]:
    params: Dict = {"innings": innings}
    match_filter = build_matches_filter_sql(
        alias="m",
        start_date=start_date,
        end_date=end_date,
        leagues=leagues,
        include_international=include_international,
        venue=venue,
        params=params,
    )
    query = text(
        f"""
        SELECT
            bs.bowling_team AS entity,
            COUNT(*) AS innings_count,
            SUM(COALESCE(bs.runs_conceded, 0)) AS runs_conceded,
            SUM(COALESCE(bs.wickets, 0)) AS wickets,
            SUM((FLOOR(COALESCE(bs.overs, 0))::int * 6) + ROUND((COALESCE(bs.overs, 0) - FLOOR(COALESCE(bs.overs, 0))) * 10)::int) AS balls_bowled,
            AVG(bs.fantasy_points) AS fantasy_avg
        FROM bowling_stats bs
        JOIN matches m ON m.id = bs.match_id
        WHERE bs.innings = :innings
          {match_filter}
        GROUP BY bs.bowling_team
        HAVING COUNT(*) >= 5
        """
    )
    rows = db.execute(query, params).mappings().all()
    wickets_per_innings: List[Optional[float]] = []
    economy: List[Optional[float]] = []
    strike_rate: List[Optional[float]] = []
    fantasy: List[Optional[float]] = []
    for row in rows:
        innings_count = int(row.get("innings_count") or 0)
        runs = float(row.get("runs_conceded") or 0)
        wickets = float(row.get("wickets") or 0)
        balls = float(row.get("balls_bowled") or 0)
        wickets_per_innings.append((wickets / innings_count) if innings_count else None)
        economy.append(safe_rate(runs, balls, scale=6.0))
        strike_rate.append(safe_rate(balls, wickets, scale=1.0))
        fantasy.append(float(row.get("fantasy_avg")) if row.get("fantasy_avg") is not None else None)
    return {
        "wickets_per_innings": wickets_per_innings,
        "economy": economy,
        "bowling_strike_rate": strike_rate,
        "fantasy_points_avg": fantasy,
        "sample_size": [len(rows)],
    }


def get_team_relative_metrics(
    *,
    db: Session,
    team_name: str,
    benchmark_window_matches: int,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: Optional[List[str]],
    include_international: bool,
    venue: Optional[str],
) -> Dict:
    effective_start_date = _resolve_effective_start_date(
        db=db,
        start_date=start_date,
        benchmark_window_matches=benchmark_window_matches,
    )
    team_variants = get_all_team_name_variations(team_name)
    expanded = normalize_leagues(leagues)

    payload = {
        "team_name": team_name,
        "resolved_team_variants": team_variants,
        "benchmark_window_matches": benchmark_window_matches,
        "effective_start_date": str(effective_start_date) if effective_start_date else None,
    }

    for innings in (1, 2):
        batting_target = _batting_metrics_from_row(
            _team_batting_agg(
                db=db,
                team_variants=team_variants,
                innings=innings,
                start_date=effective_start_date,
                end_date=end_date,
                leagues=expanded,
                include_international=include_international,
                venue=venue,
            )
        )
        bowling_target = _bowling_metrics_from_row(
            _team_bowling_agg(
                db=db,
                team_variants=team_variants,
                innings=innings,
                start_date=effective_start_date,
                end_date=end_date,
                leagues=expanded,
                include_international=include_international,
                venue=venue,
            )
        )
        batting_pop = _team_population_batting_values(
            db=db,
            innings=innings,
            start_date=effective_start_date,
            end_date=end_date,
            leagues=expanded,
            include_international=include_international,
            venue=venue,
        )
        bowling_pop = _team_population_bowling_values(
            db=db,
            innings=innings,
            start_date=effective_start_date,
            end_date=end_date,
            leagues=expanded,
            include_international=include_international,
            venue=venue,
        )
        payload[f"innings_{innings}"] = _inning_payload(
            batting_metrics=batting_target,
            bowling_metrics=bowling_target,
            batting_distribution=batting_pop,
            bowling_distribution=bowling_pop,
        )
    return payload
