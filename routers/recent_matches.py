from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_session
from services.recent_matches import get_recent_matches_by_league_service

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
