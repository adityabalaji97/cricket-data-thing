"""
Query Helpers for Wrapped Cards

Shared SQL query building utilities with proper competition/league filtering.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.sql import text
from sqlalchemy.orm import Session

from .constants import (
    WRAPPED_DEFAULT_LEAGUES,
    WRAPPED_DEFAULT_TOP_TEAMS,
    INTERNATIONAL_TEAMS_RANKED
)


def build_competition_filter(
    leagues: List[str],
    include_international: bool,
    top_teams: int = WRAPPED_DEFAULT_TOP_TEAMS,
    table_alias: str = "dd"
) -> Tuple[str, Dict]:
    """
    Build SQL WHERE clause for competition filtering.
    
    Args:
        leagues: List of league names/abbreviations to include
        include_international: Whether to include T20I matches
        top_teams: Number of top international teams for T20I filtering
        table_alias: Table alias (dd for delivery_details, m for matches)
    
    Returns:
        Tuple of (where_clause_fragment, params_dict)
    """
    conditions = []
    params = {}
    
    # League filtering
    if leagues:
        conditions.append(f"{table_alias}.competition = ANY(:wrapped_leagues)")
        params["wrapped_leagues"] = leagues
    
    # International T20 filtering
    if include_international:
        top_team_list = INTERNATIONAL_TEAMS_RANKED[:top_teams]
        # For delivery_details, we use team_bat and team_bowl
        if table_alias == "dd":
            int_condition = f"""
                ({table_alias}.competition = 'T20I' 
                 AND {table_alias}.team_bat = ANY(:wrapped_top_teams) 
                 AND {table_alias}.team_bowl = ANY(:wrapped_top_teams))
            """
        else:
            # For matches table, use team1 and team2
            int_condition = f"""
                ({table_alias}.competition = 'T20I' 
                 AND {table_alias}.team1 = ANY(:wrapped_top_teams) 
                 AND {table_alias}.team2 = ANY(:wrapped_top_teams))
            """
        conditions.append(int_condition)
        params["wrapped_top_teams"] = top_team_list
    
    # Combine with OR (match leagues OR internationals)
    if conditions:
        where_fragment = "AND (" + " OR ".join(conditions) + ")"
    else:
        where_fragment = ""
    
    return where_fragment, params


def build_date_filter(
    start_date: str,
    end_date: str,
    table_alias: str = "dd",
    use_year: bool = True
) -> Tuple[str, Dict]:
    """
    Build SQL WHERE clause for date filtering.
    
    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        table_alias: Table alias
        use_year: If True, filter by year column; if False, filter by date column
    
    Returns:
        Tuple of (where_clause_fragment, params_dict)
    """
    params = {}
    
    if use_year:
        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        where_fragment = f"AND {table_alias}.year >= :start_year AND {table_alias}.year <= :end_year"
        params["start_year"] = start_year
        params["end_year"] = end_year
    else:
        where_fragment = f"AND {table_alias}.date >= :start_date AND {table_alias}.date <= :end_date"
        params["start_date"] = start_date
        params["end_date"] = end_date
    
    return where_fragment, params


def build_base_filters(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    top_teams: int = WRAPPED_DEFAULT_TOP_TEAMS,
    table_alias: str = "dd",
    use_year: bool = True,
    extra_conditions: List[str] = None
) -> Tuple[str, Dict]:
    """
    Build complete WHERE clause combining date and competition filters.
    
    Args:
        start_date: Start date string
        end_date: End date string
        leagues: List of leagues to include
        include_international: Include T20I matches
        top_teams: Number of top teams for T20I
        table_alias: Table alias
        use_year: Use year column for date filtering
        extra_conditions: Additional WHERE conditions to append
    
    Returns:
        Tuple of (complete_where_clause, combined_params_dict)
    """
    # Build date filter
    date_clause, date_params = build_date_filter(
        start_date, end_date, table_alias, use_year
    )
    
    # Build competition filter
    comp_clause, comp_params = build_competition_filter(
        leagues, include_international, top_teams, table_alias
    )
    
    # Combine
    where_clause = f"WHERE 1=1 {date_clause} {comp_clause}"
    params = {**date_params, **comp_params}
    
    # Add extra conditions
    if extra_conditions:
        for condition in extra_conditions:
            where_clause += f" AND {condition}"
    
    return where_clause, params


def execute_query(db: Session, query: str, params: Dict) -> list:
    """
    Execute a SQL query and return results.
    
    Args:
        db: Database session
        query: SQL query string
        params: Query parameters
    
    Returns:
        List of result rows
    """
    return db.execute(text(query), params).fetchall()


def build_query_url(
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    top_teams: int = WRAPPED_DEFAULT_TOP_TEAMS,
    **extra_params
) -> str:
    """
    Build a query builder URL with all filter parameters.
    
    Args:
        start_date: Start date string
        end_date: End date string
        leagues: List of leagues
        include_international: Include international matches
        top_teams: Top teams count
        **extra_params: Additional URL parameters (group_by, min_balls, over_min, etc.)
    
    Returns:
        Query builder URL string
    """
    params = []
    
    # Date range
    params.append(f"start_date={start_date}")
    params.append(f"end_date={end_date}")
    
    # Leagues - add each as separate parameter
    for league in leagues:
        params.append(f"leagues={league}")
    
    # International settings
    if include_international:
        params.append("include_international=true")
        params.append(f"top_teams={top_teams}")
    else:
        params.append("include_international=false")
    
    # Add extra parameters
    for key, value in extra_params.items():
        if value is not None:
            if isinstance(value, list):
                for v in value:
                    params.append(f"{key}={v}")
            else:
                params.append(f"{key}={value}")
    
    return "/query?" + "&".join(params)
