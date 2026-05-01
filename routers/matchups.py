from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_session
from services.matchups import get_team_matchups_service

router = APIRouter(prefix="/teams", tags=["matchups"])

@router.get("/{team1}/{team2}/matchups")
def get_team_matchups(
    team1: str,
    team2: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    team1_players: List[str] = Query(default=[]),
    team2_players: List[str] = Query(default=[]),
    use_current_roster: bool = Query(default=False),
    innings_position: Optional[int] = Query(default=None, ge=1, le=2),
    venue_filter: Optional[str] = Query(default=None),
    min_balls: int = Query(default=6, ge=1),
    day_or_night: Optional[str] = Query(default=None, pattern="^(day|night)$"),
    db: Session = Depends(get_session)
):
    result = get_team_matchups_service(
        team1=team1,
        team2=team2,
        start_date=start_date,
        end_date=end_date,
        team1_players=team1_players,
        team2_players=team2_players,
        db=db,
        use_current_roster=use_current_roster,
        innings_position=innings_position,
        venue_filter=venue_filter,
        min_balls=min_balls,
        day_or_night=day_or_night,
    )
    return result
