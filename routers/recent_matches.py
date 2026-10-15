from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
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
    flat: bool = Query(False, description="With competition=all, return one date-sorted list "
                                          "instead of per-competition groups"),
    team: Optional[str] = Query(None, description="Team abbreviation or full name, matched against either side"),
    window: str = Query("all", description="all, 7, 30, or 90 day recency window"),
    date_from: Optional[str] = Query(None, description="Inclusive ISO start date"),
    date_to: Optional[str] = Query(None, description="Inclusive ISO end date"),
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
            team=team,
            window=window,
            date_from=date_from,
            date_to=date_to,
            flat=flat,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browse")
def browse_matches(
    competition: str = Query("all", description="all, T20I, ODI, Test, or a league"),
    team: Optional[str] = Query(None, description="A side, either team1 or team2"),
    opponent: Optional[str] = Query(None, description="The other side, for head-to-heads"),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month_day: Optional[str] = Query(None, description="MM-DD: this calendar day in every year (on this day)"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(24, ge=1, le=48),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
):
    """Every scorecard, newest first, filtered (services/match_browse.py); each with its biggest Impact."""
    from services.match_browse import browse

    try:
        return browse(db, competition=competition, team=team, opponent=opponent, year=year, month_day=month_day,
                      date_from=date_from, date_to=date_to, limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
