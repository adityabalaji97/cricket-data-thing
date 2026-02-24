from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from services.delivery_data_service import (
    build_competition_filter_delivery_details,
    build_venue_filter_delivery_details,
)
from services.visualizations import expand_league_abbreviations
from services.wrapped.card_length_masters import LENGTH_LABELS, LENGTH_ORDER


def get_venue_delivery_stats_payload(
    *,
    venue: str,
    start_date: Optional[date],
    end_date: Optional[date],
    leagues: List[str],
    include_international: bool,
    top_teams: Optional[int],
    team1: Optional[str],
    team2: Optional[str],
    db: Session,
) -> Dict[str, Any]:
    expanded_leagues = expand_league_abbreviations(leagues) if leagues else []

    params: Dict[str, Any] = {
        "venue": venue if venue and venue != "All Venues" else None,
        "start_date": start_date,
        "end_date": end_date,
        "leagues": expanded_leagues,
        "team1": team1,
        "team2": team2,
    }

    venue_filter = build_venue_filter_delivery_details(venue, params)
    competition_filter = build_competition_filter_delivery_details(
        expanded_leagues, include_international, top_teams, params
    )

    team_filter = ""
    if team1 and team2:
        team_filter = """
            AND (
                (dd.team_bat = :team1 AND dd.team_bowl = :team2)
                OR (dd.team_bat = :team2 AND dd.team_bowl = :team1)
            )
        """
    elif team1:
        team_filter = "AND (dd.team_bat = :team1 OR dd.team_bowl = :team1)"
    elif team2:
        team_filter = "AND (dd.team_bat = :team2 OR dd.team_bowl = :team2)"

    base_cte = f"""
        WITH filtered AS (
            SELECT
                dd.p_match,
                dd.over,
                dd.score,
                dd.control,
                dd.line,
                dd.length,
                dd.shot,
                dd.out
            FROM delivery_details dd
            WHERE 1=1
                {venue_filter}
                AND (:start_date IS NULL OR dd.match_date::date >= :start_date)
                AND (:end_date IS NULL OR dd.match_date::date <= :end_date)
                {competition_filter}
                {team_filter}
        )
    """

    coverage_query = text(base_cte + """
        SELECT
            COUNT(*) as total_balls,
            COUNT(DISTINCT p_match) as matches_covered,
            SUM(CASE WHEN length IS NOT NULL AND TRIM(length) != '' THEN 1 ELSE 0 END) as balls_with_length,
            SUM(CASE WHEN line IS NOT NULL AND TRIM(line) != '' THEN 1 ELSE 0 END) as balls_with_line,
            SUM(CASE WHEN shot IS NOT NULL AND TRIM(shot) != '' THEN 1 ELSE 0 END) as balls_with_shot,
            SUM(CASE WHEN control IS NOT NULL THEN 1 ELSE 0 END) as balls_with_control
        FROM filtered
    """)

    length_query = text(base_cte + """
        SELECT
            UPPER(REPLACE(TRIM(length), ' ', '_')) as bucket,
            COUNT(*) as balls,
            SUM(COALESCE(score, 0)) as runs,
            SUM(CASE WHEN out::boolean = true THEN 1 ELSE 0 END) as wickets,
            SUM(CASE WHEN control = 1 THEN 1 ELSE 0 END) as controlled_balls,
            SUM(CASE WHEN control IS NOT NULL THEN 1 ELSE 0 END) as balls_with_control
        FROM filtered
        WHERE length IS NOT NULL AND TRIM(length) != ''
        GROUP BY UPPER(REPLACE(TRIM(length), ' ', '_'))
    """)

    line_query = text(base_cte + """
        SELECT
            UPPER(REPLACE(TRIM(line), ' ', '_')) as bucket,
            COUNT(*) as balls,
            SUM(COALESCE(score, 0)) as runs,
            SUM(CASE WHEN out::boolean = true THEN 1 ELSE 0 END) as wickets,
            SUM(CASE WHEN control = 1 THEN 1 ELSE 0 END) as controlled_balls,
            SUM(CASE WHEN control IS NOT NULL THEN 1 ELSE 0 END) as balls_with_control
        FROM filtered
        WHERE line IS NOT NULL AND TRIM(line) != ''
        GROUP BY UPPER(REPLACE(TRIM(line), ' ', '_'))
    """)

    shot_query = text(base_cte + """
        SELECT
            UPPER(REPLACE(TRIM(shot), ' ', '_')) as shot_type,
            COUNT(*) as balls,
            SUM(COALESCE(score, 0)) as runs,
            SUM(CASE WHEN control = 1 THEN 1 ELSE 0 END) as controlled_balls,
            SUM(CASE WHEN control IS NOT NULL THEN 1 ELSE 0 END) as balls_with_control
        FROM filtered
        WHERE shot IS NOT NULL AND TRIM(shot) != ''
        GROUP BY UPPER(REPLACE(TRIM(shot), ' ', '_'))
        ORDER BY COUNT(*) DESC
        LIMIT 15
    """)

    phase_query = text(base_cte + """
        SELECT
            CASE
                WHEN over < 6 THEN 'PP'
                WHEN over < 11 THEN 'Mid1'
                WHEN over < 15 THEN 'Mid2'
                ELSE 'Death'
            END as phase,
            COUNT(*) as total_balls,
            SUM(COALESCE(score, 0)) as runs,
            SUM(CASE WHEN control = 1 THEN 1 ELSE 0 END) as controlled_balls,
            SUM(CASE WHEN control IS NOT NULL THEN 1 ELSE 0 END) as balls_with_control
        FROM filtered
        GROUP BY 1
    """)

    coverage_row = db.execute(coverage_query, params).fetchone()

    total_balls = int((coverage_row.total_balls or 0) if coverage_row else 0)
    balls_with_length = int((coverage_row.balls_with_length or 0) if coverage_row else 0)
    balls_with_line = int((coverage_row.balls_with_line or 0) if coverage_row else 0)
    balls_with_shot = int((coverage_row.balls_with_shot or 0) if coverage_row else 0)
    balls_with_control = int((coverage_row.balls_with_control or 0) if coverage_row else 0)
    matches_covered = int((coverage_row.matches_covered or 0) if coverage_row else 0)

    if total_balls == 0:
        return {
            "length_distribution": [],
            "line_distribution": [],
            "shot_distribution": [],
            "control_by_phase": [],
            "data_coverage": {
                "total_balls": 0,
                "balls_with_length": 0,
                "balls_with_control": 0,
                "balls_with_shot": 0,
                "balls_with_line": 0,
                "matches_covered": 0,
            },
        }

    def _label(value: Optional[str]) -> str:
        if not value:
            return "Unknown"
        return value.replace("_", " ").title()

    length_rows = db.execute(length_query, params).fetchall()
    line_rows = db.execute(line_query, params).fetchall()
    shot_rows = db.execute(shot_query, params).fetchall()
    phase_rows = db.execute(phase_query, params).fetchall()

    length_distribution = []
    for row in length_rows:
        balls = int(row.balls or 0)
        runs = int(row.runs or 0)
        wickets = int(row.wickets or 0)
        control_known = int(row.balls_with_control or 0)
        controlled = int(row.controlled_balls or 0)
        length_distribution.append(
            {
                "length_type": row.bucket,
                "label": LENGTH_LABELS.get(row.bucket, _label(row.bucket)),
                "balls": balls,
                "runs": runs,
                "strike_rate": round((runs * 100.0 / balls), 2) if balls else 0,
                "wickets": wickets,
                "control_percentage": round((controlled * 100.0 / control_known), 2) if control_known else None,
                "percentage": round((balls * 100.0 / balls_with_length), 2) if balls_with_length else 0,
            }
        )

    length_order_map = {name: idx for idx, name in enumerate(LENGTH_ORDER)}
    length_distribution.sort(key=lambda item: length_order_map.get(item["length_type"], 999))

    line_distribution = []
    for row in line_rows:
        balls = int(row.balls or 0)
        runs = int(row.runs or 0)
        wickets = int(row.wickets or 0)
        control_known = int(row.balls_with_control or 0)
        controlled = int(row.controlled_balls or 0)
        line_distribution.append(
            {
                "line_type": row.bucket,
                "label": _label(row.bucket),
                "balls": balls,
                "runs": runs,
                "strike_rate": round((runs * 100.0 / balls), 2) if balls else 0,
                "wickets": wickets,
                "control_percentage": round((controlled * 100.0 / control_known), 2) if control_known else None,
                "percentage": round((balls * 100.0 / balls_with_line), 2) if balls_with_line else 0,
            }
        )
    line_distribution.sort(key=lambda item: item["balls"], reverse=True)

    shot_distribution = []
    for row in shot_rows:
        balls = int(row.balls or 0)
        runs = int(row.runs or 0)
        control_known = int(row.balls_with_control or 0)
        controlled = int(row.controlled_balls or 0)
        shot_distribution.append(
            {
                "shot_type": row.shot_type,
                "label": _label(row.shot_type),
                "balls": balls,
                "runs": runs,
                "strike_rate": round((runs * 100.0 / balls), 2) if balls else 0,
                "control_percentage": round((controlled * 100.0 / control_known), 2) if control_known else None,
            }
        )

    phase_seed = {
        "PP": {"phase": "PP", "total_balls": 0, "runs": 0, "balls_with_control": 0, "controlled_balls": 0},
        "Mid1": {"phase": "Mid1", "total_balls": 0, "runs": 0, "balls_with_control": 0, "controlled_balls": 0},
        "Mid2": {"phase": "Mid2", "total_balls": 0, "runs": 0, "balls_with_control": 0, "controlled_balls": 0},
        "Death": {"phase": "Death", "total_balls": 0, "runs": 0, "balls_with_control": 0, "controlled_balls": 0},
    }
    for row in phase_rows:
        if row.phase in phase_seed:
            phase_seed[row.phase] = {
                "phase": row.phase,
                "total_balls": int(row.total_balls or 0),
                "runs": int(row.runs or 0),
                "balls_with_control": int(row.balls_with_control or 0),
                "controlled_balls": int(row.controlled_balls or 0),
            }

    control_by_phase = []
    for phase_key in ["PP", "Mid1", "Mid2", "Death"]:
        phase = phase_seed[phase_key]
        total = phase["total_balls"]
        known = phase["balls_with_control"]
        control_by_phase.append(
            {
                "phase": phase_key,
                "total_balls": total,
                "control_percentage": round((phase["controlled_balls"] * 100.0 / known), 2) if known else None,
                "strike_rate": round((phase["runs"] * 100.0 / total), 2) if total else 0,
            }
        )

    return {
        "length_distribution": length_distribution,
        "line_distribution": line_distribution,
        "shot_distribution": shot_distribution,
        "control_by_phase": control_by_phase,
        "data_coverage": {
            "total_balls": total_balls,
            "balls_with_length": balls_with_length,
            "balls_with_control": balls_with_control,
            "balls_with_shot": balls_with_shot,
            "balls_with_line": balls_with_line,
            "matches_covered": matches_covered,
        },
    }
