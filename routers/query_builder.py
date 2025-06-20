from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_session
from services.query_builder import query_deliveries_service

router = APIRouter(prefix="/query", tags=["query_builder"])

@router.get("/deliveries")
def query_deliveries(
    # Basic filters
    venue: Optional[str] = Query(default=None, description="Filter by venue"),
    start_date: Optional[date] = Query(default=None, description="Start date filter"),
    end_date: Optional[date] = Query(default=None, description="End date filter"),
    leagues: List[str] = Query(default=[], description="Filter by leagues"),
    teams: List[str] = Query(default=[], description="Filter by teams (batting or bowling)"),
    batting_teams: List[str] = Query(default=[], description="Filter by specific batting teams"),
    bowling_teams: List[str] = Query(default=[], description="Filter by specific bowling teams"),
    players: List[str] = Query(default=[], description="Filter by players (batter or bowler)"),
    batters: List[str] = Query(default=[], description="Filter by specific batters"),
    bowlers: List[str] = Query(default=[], description="Filter by specific bowlers"),
    
    # Column-specific filters
    crease_combo: Optional[str] = Query(default=None, description="Filter by crease combination (rhb_rhb, lhb_lhb, lhb_rhb, unknown)"),
    ball_direction: Optional[str] = Query(default=None, description="Filter by ball direction (intoBatter, awayFromBatter, unknown)"),
    bowler_type: List[str] = Query(default=[], description="Filter by bowler type (RF, RM, RO, LF, LM, LO, etc.)"),
    striker_batter_type: Optional[str] = Query(default=None, description="Filter by striker batter type (LHB, RHB)"),
    non_striker_batter_type: Optional[str] = Query(default=None, description="Filter by non-striker batter type (LHB, RHB)"),
    innings: Optional[int] = Query(default=None, description="Filter by innings (1 or 2)"),
    over_min: Optional[int] = Query(default=None, ge=0, le=19, description="Minimum over (0-19)"),
    over_max: Optional[int] = Query(default=None, ge=0, le=19, description="Maximum over (0-19)"),
    wicket_type: Optional[str] = Query(default=None, description="Filter by wicket type"),
    
    # Grouping and aggregation
    group_by: List[str] = Query(default=[], description="Group results by columns"),
    show_summary_rows: bool = Query(default=False, description="Include summary rows for each group level with percentage calculations"),
    
    # Filters for grouped results (applied via HAVING clause)
    min_balls: Optional[int] = Query(default=None, ge=1, description="Minimum balls for grouped results"),
    max_balls: Optional[int] = Query(default=None, ge=1, description="Maximum balls for grouped results"),
    min_runs: Optional[int] = Query(default=None, ge=0, description="Minimum runs for grouped results"),
    max_runs: Optional[int] = Query(default=None, ge=0, description="Maximum runs for grouped results"),
    
    # Pagination and limits
    limit: int = Query(default=1000, le=10000, description="Maximum number of results (max 10,000)"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    
    # Include international matches
    include_international: bool = Query(default=False, description="Include international matches"),
    top_teams: Optional[int] = Query(default=None, description="Include only top N international teams"),
    
    db: Session = Depends(get_session)
):
    """
    Query deliveries data with flexible filtering and grouping options.
    
    This endpoint allows you to filter cricket deliveries by various criteria and group the results
    for analysis. Perfect for studying left-right combinations, bowling matchups, venue patterns, etc.
    
    **Example Queries:**
    - Left-arm spin vs mixed partnerships: `?bowler_type=LO&crease_combo=lhb_rhb`
    - Powerplay analysis: `?over_min=0&over_max=5&group_by=crease_combo,ball_direction`
    - Venue-specific patterns: `?venue=Wankhede Stadium&group_by=bowler_type,ball_direction`
    - KKR batting performance: `?batting_teams=KKR&group_by=batter&min_balls=50`
    - Multiple bowler types: `?bowler_type=LC&bowler_type=LO&bowler_type=RL&bowler_type=RO`
    """
    try:
        result = query_deliveries_service(
            # Basic filters
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
            
            # Column-specific filters
            crease_combo=crease_combo,
            ball_direction=ball_direction,
            bowler_type=bowler_type,
            striker_batter_type=striker_batter_type,
            non_striker_batter_type=non_striker_batter_type,
            innings=innings,
            over_min=over_min,
            over_max=over_max,
            wicket_type=wicket_type,
            
            # Grouping and aggregation
            group_by=group_by,
            show_summary_rows=show_summary_rows,
            
            # Filters for grouped results
            min_balls=min_balls,
            max_balls=max_balls,
            min_runs=min_runs,
            max_runs=max_runs,
            
            # Pagination and limits
            limit=limit,
            offset=offset,
            
            # Include international matches
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
    Get list of available columns for filtering and grouping.
    
    This endpoint returns metadata about available columns to help build the UI.
    """
    try:
        # Dynamically get bowler types from the database
        from sqlalchemy.sql import text
        bowler_types_query = text("""
            SELECT DISTINCT bowler_type
            FROM deliveries 
            WHERE bowler_type IS NOT NULL 
            AND bowler_type != ''
            ORDER BY bowler_type
        """)
        
        bowler_types_result = db.execute(bowler_types_query).fetchall()
        available_bowler_types = [row[0] for row in bowler_types_result]
        
        return {
            "filter_columns": {
                "basic": ["venue", "start_date", "end_date", "leagues", "teams", "batting_teams", "bowling_teams", "players", "batters", "bowlers"],
                "match": ["innings", "over_min", "over_max"],
                "players": ["striker_batter_type", "non_striker_batter_type", "bowler_type"],
                "left_right": ["crease_combo", "ball_direction"],
                "cricket": ["wicket_type"],
                "grouped_filters": ["min_balls", "max_balls", "min_runs", "max_runs"]
            },
            "group_by_columns": [
                "venue", "crease_combo", "ball_direction", "bowler_type", 
                "striker_batter_type", "non_striker_batter_type", "innings",
                "batting_team", "bowling_team", "batter", "bowler", "competition",
                "year",  # Extract year from match date
                "phase"  # Special computed column for powerplay/middle/death
            ],
            "crease_combo_options": ["rhb_rhb", "lhb_lhb", "lhb_rhb", "unknown"],
            "ball_direction_options": ["intoBatter", "awayFromBatter", "unknown"],
            "batter_type_options": ["LHB", "RHB"],
            "common_bowler_types": available_bowler_types,  # Now dynamically fetched
            "innings_options": [1, 2],
            "wicket_type_options": ["caught", "bowled", "lbw", "run out", "stumped", "hit wicket"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
