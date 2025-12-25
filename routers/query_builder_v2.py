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


def preprocess_list_param(items: List[str]) -> List[str]:
    """
    Preprocess list parameters to handle comma-separated values.
    
    This fixes an issue where URLs like ?group_by=batter,shot are parsed
    by FastAPI as ['batter,shot'] instead of ['batter', 'shot'].
    
    Converts ['a,b', 'c'] to ['a', 'b', 'c']
    Also removes empty strings and duplicates while preserving order.
    """
    if not items:
        return []
    
    processed = []
    for item in items:
        if item is None:
            continue
        item_str = str(item)
        if ',' in item_str:
            # Split comma-separated values and strip whitespace
            processed.extend([x.strip() for x in item_str.split(',')])
        else:
            processed.append(item_str.strip())
    
    # Remove empty strings and duplicates while preserving order
    seen = set()
    result = []
    for item in processed:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    
    return result


def preprocess_int_list_param(items: List[int]) -> List[int]:
    """
    Preprocess integer list parameters to handle comma-separated string values.
    
    Handles cases where wagon_zone might come in as ['0,1,2'] instead of [0, 1, 2].
    """
    if not items:
        return []
    
    processed = []
    for item in items:
        if item is None:
            continue
        # Handle case where it might be a string like "0,1,2"
        if isinstance(item, str):
            if ',' in item:
                processed.extend([int(x.strip()) for x in item.split(',') if x.strip().isdigit()])
            elif item.strip().isdigit():
                processed.append(int(item.strip()))
        else:
            processed.append(int(item))
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for item in processed:
        if item not in seen:
            seen.add(item)
            result.append(item)
    
    return result


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
    crease_combo: List[str] = Query(default=[], description="Filter by crease combo (RHB_RHB, RHB_LHB, LHB_RHB, LHB_LHB)"),
    
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
    - Crease combo analysis (RHB_RHB, LHB_RHB, etc.)
    
    **Example Queries:**
    - Short ball shots: `?length=SHORT&group_by=shot&min_balls=50`
    - Controlled vs uncontrolled by zone: `?group_by=control,wagon_zone`
    - Spin bowling by line: `?bowl_kind=spin bowler&group_by=line,length`
    - Left-right combo analysis: `?group_by=crease_combo&min_balls=100`
    """
    try:
        # PREPROCESSING: Handle comma-separated list parameters
        # This fixes URLs like ?group_by=batter,shot which FastAPI parses as ['batter,shot']
        leagues = preprocess_list_param(leagues)
        teams = preprocess_list_param(teams)
        batting_teams = preprocess_list_param(batting_teams)
        bowling_teams = preprocess_list_param(bowling_teams)
        players = preprocess_list_param(players)
        batters = preprocess_list_param(batters)
        bowlers = preprocess_list_param(bowlers)
        bowl_style = preprocess_list_param(bowl_style)
        bowl_kind = preprocess_list_param(bowl_kind)
        crease_combo = preprocess_list_param(crease_combo)
        line = preprocess_list_param(line)
        length = preprocess_list_param(length)
        shot = preprocess_list_param(shot)
        group_by = preprocess_list_param(group_by)
        
        # Handle wagon_zone separately since it's List[int]
        wagon_zone = preprocess_int_list_param(wagon_zone)
        
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
            crease_combo=crease_combo,
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
    Get available columns for filtering and grouping.
    
    Reads from precomputed query_builder_metadata table for fast response.
    Run scripts/refresh_query_builder_metadata.py to update after data loads.
    """
    try:
        from sqlalchemy.sql import text
        
        # Read all metadata in one query
        result = db.execute(text("""
            SELECT key, values, coverage_percent
            FROM query_builder_metadata
        """)).fetchall()
        
        # Build lookup dict
        metadata = {}
        for row in result:
            # JSONB returns already-parsed Python objects, no need for json.loads
            metadata[row[0]] = {
                "values": row[1] if row[1] else [],
                "coverage": row[2]
            }
        
        # Helper to get values with fallback
        def get_values(key):
            return metadata.get(key, {}).get("values", [])
        
        def get_coverage(key):
            return metadata.get(key, {}).get("coverage")
        
        # Get total deliveries
        total_deliveries = get_values("total_deliveries")
        if isinstance(total_deliveries, int):
            total_count = total_deliveries
        elif isinstance(total_deliveries, list) and len(total_deliveries) == 0:
            total_count = metadata.get("total_deliveries", {}).get("values", 0)
        else:
            total_count = total_deliveries
        
        # Combine batting and bowling teams for "teams" dropdown
        batting_teams = get_values("batting_teams")
        bowling_teams = get_values("bowling_teams")
        all_teams = sorted(list(set(batting_teams + bowling_teams)))
        
        return {
            "total_deliveries": total_count,
            
            "filter_columns": {
                "basic": ["venue", "start_date", "end_date", "leagues", "teams", "batting_teams", "bowling_teams", "players", "batters", "bowlers"],
                "match": ["innings", "over_min", "over_max"],
                "batter": ["bat_hand", "crease_combo"],
                "bowler": ["bowl_style", "bowl_kind"],
                "delivery": ["line", "length", "shot", "control", "wagon_zone"],
                "grouped_filters": ["min_balls", "max_balls", "min_runs", "max_runs"]
            },
            
            "group_by_columns": [
                "venue", "country", "match_id", "competition", "year",
                "batting_team", "bowling_team", "batter", "bowler",
                "innings", "phase",
                "bat_hand", "bowl_style", "bowl_kind", "crease_combo",
                "line", "length", "shot", "control", "wagon_zone"
            ],
            
            # Options with coverage info
            "line_options": get_values("line"),
            "line_coverage": get_coverage("line"),
            
            "length_options": get_values("length"),
            "length_coverage": get_coverage("length"),
            
            "shot_options": get_values("shot"),
            "shot_coverage": get_coverage("shot"),
            
            "control_options": [0, 1],
            "control_coverage": get_coverage("control"),
            
            "wagon_zone_options": get_values("wagon_zone"),
            "wagon_zone_coverage": get_coverage("wagon_zone"),
            
            "bowl_style_options": get_values("bowl_style"),
            "bowl_style_coverage": get_coverage("bowl_style"),
            
            "bowl_kind_options": get_values("bowl_kind"),
            "bowl_kind_coverage": get_coverage("bowl_kind"),
            
            "bat_hand_options": get_values("bat_hand"),
            "bat_hand_coverage": get_coverage("bat_hand"),
            
            "crease_combo_options": ["RHB_RHB", "RHB_LHB", "LHB_RHB", "LHB_LHB"],
            "crease_combo_coverage": get_coverage("crease_combo"),
            
            "innings_options": [1, 2],
            
            # Basic filter options
            "venues": get_values("venues"),
            "batters": get_values("batters"),
            "bowlers": get_values("bowlers"),
            "teams": all_teams,
            "batting_teams": batting_teams,
            "bowling_teams": bowling_teams,
            "competitions": get_values("competitions"),
            
            # Coverage summary for UI warnings
            "coverage_summary": {
                "high": ["wagon_zone", "bat_hand", "bowl_style", "bowl_kind", "crease_combo"],
                "medium": ["shot", "control"],
                "low": ["line", "length"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
