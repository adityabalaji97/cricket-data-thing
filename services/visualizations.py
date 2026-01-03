"""
Visualization Data Service - Wagon Wheel and Pitch Map Data

Provides data for wagon wheel and pitch map visualizations from delivery_details table.
"""

from sqlalchemy.sql import text
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import date
import logging
from models import leagues_mapping

logger = logging.getLogger(__name__)


def expand_league_abbreviations(abbrevs: List[str]) -> List[str]:
    """
    Expand league abbreviations to include all variations.
    This matches the approach used in query_builder_v2.

    For each league, includes:
    - The input value itself
    - Both full name and abbreviation (if mapping exists)
    - Any aliases (if applicable)
    """
    if not abbrevs:
        return []

    expanded = []
    for abbrev in abbrevs:
        expanded.append(abbrev)

        # If input is a full name, add the abbreviation
        if abbrev in leagues_mapping:
            expanded.append(leagues_mapping[abbrev])
        # If input is an abbreviation, add the full name
        else:
            # Try to find full name by looking up in reverse
            for full_name, short_name in leagues_mapping.items():
                if short_name == abbrev:
                    expanded.append(full_name)
                    break

    # Remove duplicates while preserving order
    return list(dict.fromkeys(expanded))


def get_wagon_wheel_data(
    db: Session,
    batter: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    venue: Optional[str] = None,
    leagues: List[str] = None,
    include_international: bool = False,
    top_teams: Optional[int] = None,
    phase: Optional[str] = None,  # overall, powerplay, middle, death
    bowl_kind: Optional[str] = None,  # pace, spin
    bowl_style: Optional[str] = None,  # specific bowler types
) -> List[Dict[str, Any]]:
    """
    Get wagon wheel data for a batter with optional filters.

    Returns individual deliveries with wagon coordinates (wagon_x, wagon_y)
    where the ball ended up after the shot.

    Args:
        db: Database session
        batter: Name of the batter
        start_date: Filter by start date
        end_date: Filter by end date
        venue: Filter by venue
        leagues: List of league names to include
        include_international: Include international matches
        top_teams: If including international, limit to top N teams
        phase: Match phase (powerplay: 0-5, middle: 6-14, death: 15+)
        bowl_kind: Filter by bowling kind (pace bowler, spin bowler)
        bowl_style: Filter by specific bowling style

    Returns:
        List of deliveries with wagon coordinates and metadata
    """
    try:
        logger.info(f"Fetching wagon wheel data for {batter}")

        # Build WHERE conditions
        conditions = ["dd.bat = :batter", "dd.wagon_x IS NOT NULL", "dd.wagon_y IS NOT NULL"]
        params = {"batter": batter}

        if start_date:
            conditions.append("dd.match_date >= :start_date")
            params["start_date"] = str(start_date)

        if end_date:
            conditions.append("dd.match_date <= :end_date")
            params["end_date"] = str(end_date)

        if venue:
            conditions.append("dd.ground = :venue")
            params["venue"] = venue

        # League/competition filters
        if leagues or include_international:
            comp_conditions = []
            if leagues:
                # Expand leagues to include both full names and abbreviations
                expanded_leagues = expand_league_abbreviations(leagues)
                comp_conditions.append("dd.competition = ANY(:leagues)")
                params["leagues"] = expanded_leagues

            if include_international:
                if top_teams:
                    # Add top international teams
                    from models import INTERNATIONAL_TEAMS_RANKED
                    top_team_names = INTERNATIONAL_TEAMS_RANKED[:top_teams]
                    team_placeholders = ", ".join([f":team_{i}" for i in range(len(top_team_names))])
                    comp_conditions.append(f"""(
                        dd.competition LIKE '%International%'
                        AND (dd.team_bat IN ({team_placeholders}) OR dd.team_bowl IN ({team_placeholders}))
                    )""")
                    for i, team in enumerate(top_team_names):
                        params[f"team_{i}"] = team
                else:
                    comp_conditions.append("dd.competition LIKE '%International%'")

            if comp_conditions:
                conditions.append(f"({' OR '.join(comp_conditions)})")

        # Phase filter
        if phase and phase != "overall":
            if phase == "powerplay":
                conditions.append("dd.over BETWEEN 0 AND 5")
            elif phase == "middle":
                conditions.append("dd.over BETWEEN 6 AND 14")
            elif phase == "death":
                conditions.append("dd.over >= 15")

        # Bowling filters
        if bowl_kind:
            conditions.append("dd.bowl_kind = :bowl_kind")
            params["bowl_kind"] = bowl_kind

        if bowl_style:
            conditions.append("dd.bowl_style = :bowl_style")
            params["bowl_style"] = bowl_style

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT
                dd.wagon_x,
                dd.wagon_y,
                dd.wagon_zone,
                dd.score as runs,
                dd.shot,
                dd.line,
                dd.length,
                dd.bowl_kind,
                dd.bowl_style,
                dd.bowl as bowler,
                dd.over,
                dd.p_match as match_id,
                dd.match_date as date,
                dd.ground as venue,
                dd.competition,
                CASE
                    WHEN dd.over BETWEEN 0 AND 5 THEN 'powerplay'
                    WHEN dd.over BETWEEN 6 AND 14 THEN 'middle'
                    ELSE 'death'
                END as phase
            FROM delivery_details dd
            WHERE {where_clause}
            ORDER BY dd.date, dd.match_id, dd.over, dd.ball
        """)

        result = db.execute(query, params).fetchall()

        deliveries = [
            {
                "wagon_x": row.wagon_x,
                "wagon_y": row.wagon_y,
                "wagon_zone": row.wagon_zone,
                "runs": row.runs,
                "shot": row.shot,
                "line": row.line,
                "length": row.length,
                "bowl_kind": row.bowl_kind,
                "bowl_style": row.bowl_style,
                "bowler": row.bowler,
                "over": row.over,
                "phase": row.phase,
                "match_id": row.match_id,
                "date": str(row.date) if row.date else None,
                "venue": row.venue,
                "competition": row.competition,
            }
            for row in result
        ]

        logger.info(f"Found {len(deliveries)} deliveries with wagon wheel data for {batter}")
        return deliveries

    except Exception as e:
        logger.error(f"Error fetching wagon wheel data: {str(e)}")
        raise Exception(f"Failed to fetch wagon wheel data: {str(e)}")


def get_pitch_map_data(
    db: Session,
    batter: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    venue: Optional[str] = None,
    leagues: List[str] = None,
    include_international: bool = False,
    top_teams: Optional[int] = None,
    phase: Optional[str] = None,
    bowl_kind: Optional[str] = None,
    bowl_style: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get pitch map data for a batter with optional filters.

    Returns aggregated statistics by line and length combinations.

    Args:
        Same as get_wagon_wheel_data

    Returns:
        List of pitch map cells with aggregated statistics
    """
    try:
        logger.info(f"Fetching pitch map data for {batter}")

        # Build WHERE conditions (same as wagon wheel)
        conditions = ["dd.bat = :batter", "dd.line IS NOT NULL", "dd.length IS NOT NULL"]
        params = {"batter": batter}

        if start_date:
            conditions.append("dd.match_date >= :start_date")
            params["start_date"] = str(start_date)

        if end_date:
            conditions.append("dd.match_date <= :end_date")
            params["end_date"] = str(end_date)

        if venue:
            conditions.append("dd.ground = :venue")
            params["venue"] = venue

        # League/competition filters
        if leagues or include_international:
            comp_conditions = []
            if leagues:
                # Expand leagues to include both full names and abbreviations
                expanded_leagues = expand_league_abbreviations(leagues)
                comp_conditions.append("dd.competition = ANY(:leagues)")
                params["leagues"] = expanded_leagues

            if include_international:
                if top_teams:
                    from models import INTERNATIONAL_TEAMS_RANKED
                    top_team_names = INTERNATIONAL_TEAMS_RANKED[:top_teams]
                    team_placeholders = ", ".join([f":team_{i}" for i in range(len(top_team_names))])
                    comp_conditions.append(f"""(
                        dd.competition LIKE '%International%'
                        AND (dd.team_bat IN ({team_placeholders}) OR dd.team_bowl IN ({team_placeholders}))
                    )""")
                    for i, team in enumerate(top_team_names):
                        params[f"team_{i}"] = team
                else:
                    comp_conditions.append("dd.competition LIKE '%International%'")

            if comp_conditions:
                conditions.append(f"({' OR '.join(comp_conditions)})")

        # Phase filter
        if phase and phase != "overall":
            if phase == "powerplay":
                conditions.append("dd.over BETWEEN 0 AND 5")
            elif phase == "middle":
                conditions.append("dd.over BETWEEN 6 AND 14")
            elif phase == "death":
                conditions.append("dd.over >= 15")

        # Bowling filters
        if bowl_kind:
            conditions.append("dd.bowl_kind = :bowl_kind")
            params["bowl_kind"] = bowl_kind

        if bowl_style:
            conditions.append("dd.bowl_style = :bowl_style")
            params["bowl_style"] = bowl_style

        where_clause = " AND ".join(conditions)

        query = text(f"""
            SELECT
                dd.line,
                dd.length,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.out = 'True' THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN dd.score = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.score = 4 THEN 1 ELSE 0 END) as fours,
                SUM(CASE WHEN dd.score = 6 THEN 1 ELSE 0 END) as sixes,
                SUM(CASE WHEN dd.control = 1 THEN 1 ELSE 0 END) as controlled_shots,
                CASE
                    WHEN SUM(CASE WHEN dd.out = 'True' THEN 1 ELSE 0 END) > 0
                    THEN CAST(SUM(dd.score) AS FLOAT) / SUM(CASE WHEN dd.out = 'True' THEN 1 ELSE 0 END)
                    ELSE NULL
                END as average,
                CAST(SUM(dd.score) AS FLOAT) * 100.0 / COUNT(*) as strike_rate,
                CAST(SUM(CASE WHEN dd.score = 0 THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / COUNT(*) as dot_percentage,
                CAST(SUM(CASE WHEN dd.score IN (4, 6) THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / COUNT(*) as boundary_percentage,
                CAST(SUM(CASE WHEN dd.control = 1 THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / COUNT(*) as control_percentage
            FROM delivery_details dd
            WHERE {where_clause}
            GROUP BY dd.line, dd.length
            ORDER BY dd.line, dd.length
        """)

        result = db.execute(query, params).fetchall()

        cells = [
            {
                "line": row.line,
                "length": row.length,
                "balls": row.balls,
                "runs": row.runs,
                "wickets": row.wickets,
                "dots": row.dots,
                "fours": row.fours,
                "sixes": row.sixes,
                "controlled_shots": row.controlled_shots,
                "average": float(row.average) if row.average else None,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0,
                "control_percentage": float(row.control_percentage) if row.control_percentage else 0,
            }
            for row in result
        ]

        logger.info(f"Found {len(cells)} pitch map cells for {batter}")
        return cells

    except Exception as e:
        logger.error(f"Error fetching pitch map data: {str(e)}")
        raise Exception(f"Failed to fetch pitch map data: {str(e)}")
