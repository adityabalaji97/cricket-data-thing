from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_session
from services.search import (
    search_entities,
    get_random_entity,
    get_player_profile,
    get_player_doppelgangers,
    get_doppelganger_leaderboard,
)
from typing import Optional, List
from datetime import date

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/suggestions")
def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=10, le=20, description="Max results"),
    db: Session = Depends(get_session)
):
    """
    Get autocomplete suggestions for players, teams, and venues.
    
    Returns results ranked by relevance (exact match > prefix > contains).
    Each result includes 'name' and 'type' (player/team/venue).
    """
    try:
        results = search_entities(q, db, limit)
        return {"suggestions": results, "query": q}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/random")
def get_random_suggestion(db: Session = Depends(get_session)):
    """
    Get a random entity for 'I'm Feeling Lucky' feature.
    
    Returns a random player, team, or venue with its type.
    """
    try:
        result = get_random_entity(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Random selection failed: {str(e)}")


@router.get("/player/{player_name}")
def get_player_search_profile(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_session)
):
    """
    Get unified player profile with both batting and bowling career stats.
    
    Uses default date range (Jan 1 of previous year to today) if not specified.
    Returns comprehensive stats for both batting and bowling roles.
    
    Example response:
    {
        "found": true,
        "player_name": "Virat Kohli",
        "player_info": {
            "batting_hand": "Right",
            "bowling_style": "RM",
            "role": "batter",
            "recent_teams": ["Royal Challengers Bengaluru", "India"]
        },
        "batting": {
            "has_stats": true,
            "matches": 45,
            "runs": 1200,
            "average": 42.5,
            "strike_rate": 135.2,
            ...
        },
        "bowling": {
            "has_stats": false,
            "matches": 0,
            ...
        }
    }
    """
    try:
        result = get_player_profile(player_name, db, start_date, end_date)
        
        if not result.get("found"):
            raise HTTPException(status_code=404, detail=result.get("error", "Player not found"))
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get player profile: {str(e)}")


@router.get("/player/{player_name}/doppelgangers")
def get_player_doppelganger_profile(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=None, description="League competitions to include; omit to leave unfiltered"),
    include_international: Optional[bool] = Query(default=None, description="Include international matches"),
    top_teams: Optional[int] = Query(default=None, ge=1, le=30, description="Limit internationals to top N teams"),
    role: Optional[str] = Query(default=None, description="Override role: batter, bowler, or all_rounder"),
    min_matches: int = Query(default=10, ge=1, le=200, description="Minimum matches for candidate pool"),
    top_n: int = Query(default=5, ge=1, le=20, description="How many similar/dissimilar players to return"),
    db: Session = Depends(get_session)
):
    """
    Find most similar and dissimilar players (doppelgänger search) based on
    normalized player-level batting and bowling metrics.
    """
    try:
        result = get_player_doppelgangers(
            player_name=player_name,
            db=db,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            role=role,
            min_matches=min_matches,
            top_n=top_n
        )

        if not result.get("found"):
            raise HTTPException(status_code=404, detail=result.get("error", "Player not found"))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get doppelgänger search results: {str(e)}")


@router.get("/doppelgangers/leaderboard")
def get_doppelganger_leaderboard_route(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=None, description="League competitions to include (omit to use default top-5 preset, empty with other filters => all leagues)"),
    include_international: Optional[bool] = Query(default=None, description="Include international matches"),
    top_teams: Optional[int] = Query(default=None, ge=1, le=30, description="Limit internationals to top N teams"),
    min_batting_innings: int = Query(default=25, ge=1, le=500, description="Minimum batting innings"),
    min_bowling_balls: int = Query(default=240, ge=1, le=10000, description="Minimum bowling balls"),
    top_n_pairs: int = Query(default=10, ge=1, le=50, description="Pairs to return"),
    batter_metric_level: str = Query(default="bowling_type", description="Batter metric level: basic, pace_spin, bowling_type"),
    db: Session = Depends(get_session)
):
    """
    Global similarity leaderboard for batters and bowlers, restricted to
    top franchise leagues and top international teams.
    """
    try:
        return get_doppelganger_leaderboard(
            db=db,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            min_batting_innings=min_batting_innings,
            min_bowling_balls=min_bowling_balls,
            top_n_pairs=top_n_pairs,
            batter_metric_level=batter_metric_level,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get doppelganger leaderboard: {str(e)}")
