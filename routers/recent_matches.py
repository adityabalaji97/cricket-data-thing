from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_session
from services.recent_matches import get_recent_matches_by_league_service, get_recent_matches_discover_service

router = APIRouter(prefix="/recent-matches", tags=["recent-matches"])

@router.get("/by-league")
def get_recent_matches_by_league(
    db: Session = Depends(get_session)
):
    """
    Get the most recent match for each league and T20 internationals,
    along with match counts for each competition
    
    Returns:
        Dictionary containing:
        - recent_matches: List of most recent matches per league/T20I
        - competition_stats: Match counts and date ranges by competition
        - summary statistics
    """
    try:
        result = get_recent_matches_by_league_service(db=db)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover")
def get_recent_matches_discover(
    competition: str = Query("all", description="all, T20I, or a league competition name"),
    limit: int = Query(12, ge=1, le=48),
    offset: int = Query(0, ge=0),
    per_group: int = Query(3, ge=1, le=6),
    db: Session = Depends(get_session),
):
    """
    Browse recent scorecard-ready matches.

    competition=all returns grouped latest matches per competition.
    competition=T20I or a league returns a flat paginated list.
    """
    try:
        return get_recent_matches_discover_service(
            db=db,
            competition=competition,
            limit=limit,
            offset=offset,
            per_group=per_group,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
