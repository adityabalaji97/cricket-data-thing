"""
Query Builder Router - Using delivery_details table

Provides flexible querying of ball-by-ball cricket data with filtering,
grouping, and aggregation capabilities.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_session
from services.query_builder_v2 import query_deliveries_service

router = APIRouter(prefix="/query", tags=["query_builder"])


@router.get("/deliveries")
def query_deliveries(
    # Basic filters
    venue: Optional[str] = Query(default=None, description="Filter by venue/ground"),
    start_date: Optional[date] = Query(default=None, description="Start date filter"),
    end_date: Optional[date] = Query(default=None, description="End date filter"),
    leagues: List[str] = Query(default=[], description="Filter by leagues (IPL, BBL, T20I, etc.)"),
    teams: List[str] = Query(default=[], description="Filter by teams (batting or bowling)"),
    batting_teams: List[str] = Query(default=[], description="Filter by specific batting teams"),
    bowling_teams: List[str] = Query(default=[], description="Filter by specific bowling teams"),
    players: List[str] = Query(default=[], description="Filter by players (batter or bowler)"),
    batters: List[str] = Query(default=[], description="Filter by specific batters"),
    bowlers: List[str] = Query(default=[], description="Filter by specific bowlers"),
    
    # Batter/Bowler attribute filters
    bat_hand: Optional[str] = Query(default=None, description="Filter by batting hand (LHB, RHB)"),
    bowl_style: List[str] = Query(default=[], description="Filter by bowling style (RF, RM, SLA, OB, etc.)"),
    bowl_kind: List[str] = Query(default=[], description="Filter by bowl kind (pace bowler, spin bowler, mixture/unknown)"),
    
    # Delivery detail filters (NEW)
    line: List[str] = Query(default=[], description="Filter by line (ON_THE_STUMPS, OUTSIDE_OFFSTUMP, DOWN_LEG, etc.)"),
    length: List[str] = Query(default=[], description="Filter by length (GOOD_LENGTH, YORKER, FULL, SHORT, etc.)"),
    shot: List[str] = Query(default=[], description="Filter by shot type (COVER_DRIVE, FLICK, PULL, DEFENDED, etc.)"),
    control: Optional[int] = Query(default=None, ge=0, le=1, description="Filter by shot control (0=uncontrolled, 1=controlled)"),
    wagon_zone: List[int] = Query(default=[], description="Filter by wagon wheel zone (0-8)"),
    
    # Match context filters
    innings: Optional[int] = Query(default=None, description="Filter by innings (1 or 2)"),
    over_min: Optional[int] = Query(default=None, ge=0, le=19, description="Minimum over (0-19)"),
    over_max: Optional[int] = Query(default=None, ge=0, le=19, description="Maximum over (0-19)"),
    
    # Grouping and aggregation
    group_by: List[str] = Query(default=[], description="Group results by columns"),
    show_summary_rows: bool = Query(default=False, description="Include summary rows for multi-level grouping"),
    
    # Filters for grouped results
    min_balls: Optional[int] = Query(default=None, ge=1, description="Minimum balls for grouped results"),
    max_balls: Optional[int] = Query(default=None, ge=1, description="Maximum balls for grouped results"),
    min_runs: Optional[int] = Query(default=None, ge=0, description="Minimum runs for grouped results"),
    max_runs: Optional[int] = Query(default=None, ge=0, description="Maximum runs for grouped results"),
    
    # Pagination and limits
    limit: int = Query(default=1000, le=10000, description="Maximum results (max 10,000)"),
    offset: int = Query(default=0, ge=0, description="Results to skip"),
    
    # Include international matches
    include_international: bool = Query(default=False, description="Include international T20I matches"),
    top_teams: Optional[int] = Query(default=None, description="Include only top N international teams"),
    
    db: Session = Depends(get_session)
):
    """
    Query ball-by-ball data from delivery_details with flexible filtering and grouping.
    
    **New Features:**
    - Line analysis (ON_THE_STUMPS, OUTSIDE_OFFSTUMP, DOWN_LEG)
    - Length analysis (GOOD_LENGTH, YORKER, FULL, SHORT)
    - Shot type analysis (COVER_DRIVE, FLICK, PULL, etc.)
    - Shot control metrics
    - Wagon wheel zone filtering
    
    **Example Queries:**
    - Short ball shots: `?length=SHORT&group_by=shot&min_balls=50`
    - Controlled vs uncontrolled by zone: `?group_by=control,wagon_zone`
    - Spin bowling by line: `?bowl_kind=spin bowler&group_by=line,length`
    """
    try:
        result = query_deliveries_service(
            venue=venue,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            teams=teams,
            batting_teams=batting_teams,
            bowling_teams=bowling_teams,
            players=players,
            batters=batters,
            bowlers=bowlers,
            bat_hand=bat_hand,
            bowl_style=bowl_style,
            bowl_kind=bowl_kind,
            line=line,
            length=length,
            shot=shot,
            control=control,
            wagon_zone=wagon_zone,
            innings=innings,
            over_min=over_min,
            over_max=over_max,
            group_by=group_by,
            show_summary_rows=show_summary_rows,
            min_balls=min_balls,
            max_balls=max_balls,
            min_runs=min_runs,
            max_runs=max_runs,
            limit=limit,
            offset=offset,
            include_international=include_international,
            top_teams=top_teams,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deliveries/columns")
def get_available_columns(db: Session = Depends(get_session)):
    """
    Get available columns for filtering and grouping, with dynamic coverage statistics.
    
    Returns column options fetched from the database along with data coverage
    percentages to help users understand data availability.
    """
    try:
        from sqlalchemy.sql import text
        
        # Get total row count
        total_count = db.execute(text("SELECT COUNT(*) FROM delivery_details")).scalar()
        
        # Fetch distinct values and coverage for key columns
        def get_options_with_coverage(column_name):
            query = text(f"""
                SELECT 
                    COUNT(*) FILTER (WHERE {column_name} IS NOT NULL) as non_null_count,
                    COUNT(DISTINCT {column_name}) as distinct_count
                FROM delivery_details
            """)
            result = db.execute(query).fetchone()
            coverage = (result[0] / total_count * 100) if total_count > 0 else 0
            
            # Get distinct values
            values_query = text(f"""
                SELECT DISTINCT {column_name} 
                FROM delivery_details 
                WHERE {column_name} IS NOT NULL 
                ORDER BY {column_name}
            """)
            values = [row[0] for row in db.execute(values_query).fetchall()]
            
            return {
                "options": values,
                "coverage_percent": round(coverage, 1),
                "distinct_count": result[1]
            }
        
        # Get options for each column
        line_data = get_options_with_coverage("line")
        length_data = get_options_with_coverage("length")
        shot_data = get_options_with_coverage("shot")
        control_data = get_options_with_coverage("control")
        wagon_zone_data = get_options_with_coverage("wagon_zone")
        bowl_style_data = get_options_with_coverage("bowl_style")
        bowl_kind_data = get_options_with_coverage("bowl_kind")
        bat_hand_data = get_options_with_coverage("bat_hand")
        
        # Get dropdown options for basic filters (from delivery_details)
        venues_query = text("SELECT DISTINCT ground FROM delivery_details WHERE ground IS NOT NULL ORDER BY ground")
        venues = [row[0] for row in db.execute(venues_query).fetchall()]
        
        batters_query = text("SELECT DISTINCT bat FROM delivery_details WHERE bat IS NOT NULL ORDER BY bat")
        batters = [row[0] for row in db.execute(batters_query).fetchall()]
        
        bowlers_query = text("SELECT DISTINCT bowl FROM delivery_details WHERE bowl IS NOT NULL ORDER BY bowl")
        bowlers = [row[0] for row in db.execute(bowlers_query).fetchall()]
        
        batting_teams_query = text("SELECT DISTINCT team_bat FROM delivery_details WHERE team_bat IS NOT NULL ORDER BY team_bat")
        batting_teams = [row[0] for row in db.execute(batting_teams_query).fetchall()]
        
        bowling_teams_query = text("SELECT DISTINCT team_bowl FROM delivery_details WHERE team_bowl IS NOT NULL ORDER BY team_bowl")
        bowling_teams = [row[0] for row in db.execute(bowling_teams_query).fetchall()]
        
        # Combine teams (union of batting and bowling teams)
        all_teams = sorted(list(set(batting_teams + bowling_teams)))
        
        competitions_query = text("SELECT DISTINCT competition FROM delivery_details WHERE competition IS NOT NULL ORDER BY competition")
        competitions = [row[0] for row in db.execute(competitions_query).fetchall()]
        
        return {
            "total_deliveries": total_count,
            
            "filter_columns": {
                "basic": ["venue", "start_date", "end_date", "leagues", "teams", "batting_teams", "bowling_teams", "players", "batters", "bowlers"],
                "match": ["innings", "over_min", "over_max"],
                "batter": ["bat_hand"],
                "bowler": ["bowl_style", "bowl_kind"],
                "delivery": ["line", "length", "shot", "control", "wagon_zone"],
                "grouped_filters": ["min_balls", "max_balls", "min_runs", "max_runs"]
            },
            
            "group_by_columns": [
                "venue", "country", "match_id", "competition", "year",
                "batting_team", "bowling_team", "batter", "bowler",
                "innings", "phase",
                "bat_hand", "bowl_style", "bowl_kind",
                "line", "length", "shot", "control", "wagon_zone"
            ],
            
            # Options with coverage info
            "line_options": line_data["options"],
            "line_coverage": line_data["coverage_percent"],
            
            "length_options": length_data["options"],
            "length_coverage": length_data["coverage_percent"],
            
            "shot_options": shot_data["options"],
            "shot_coverage": shot_data["coverage_percent"],
            
            "control_options": [0, 1],
            "control_coverage": control_data["coverage_percent"],
            
            "wagon_zone_options": wagon_zone_data["options"],
            "wagon_zone_coverage": wagon_zone_data["coverage_percent"],
            
            "bowl_style_options": bowl_style_data["options"],
            "bowl_style_coverage": bowl_style_data["coverage_percent"],
            
            "bowl_kind_options": bowl_kind_data["options"],
            "bowl_kind_coverage": bowl_kind_data["coverage_percent"],
            
            "bat_hand_options": bat_hand_data["options"],
            "bat_hand_coverage": bat_hand_data["coverage_percent"],
            
            "innings_options": [1, 2],
            
            # Basic filter options (from delivery_details)
            "venues": venues,
            "batters": batters,
            "bowlers": bowlers,
            "teams": all_teams,
            "batting_teams": batting_teams,
            "bowling_teams": bowling_teams,
            "competitions": competitions,
            
            # Coverage summary for UI warnings
            "coverage_summary": {
                "high": ["wagon_zone", "bat_hand", "bowl_style", "bowl_kind"],  # >90%
                "medium": ["shot", "control"],  # 50-90%
                "low": ["line", "length"]  # <50%
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
