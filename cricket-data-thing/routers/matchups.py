from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_session
from services.matchups import get_team_matchups_service
import json

router = APIRouter(prefix="/teams", tags=["matchups"])

@router.get("/{team1}/{team2}/matchups")
def get_team_matchups(
    team1: str,
    team2: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    team1_players: List[str] = Query(default=[]),
    team2_players: List[str] = Query(default=[]),
    db: Session = Depends(get_session)
):
    result = get_team_matchups_service(
        team1=team1,
        team2=team2,
        start_date=start_date,
        end_date=end_date,
        team1_players=team1_players,
        team2_players=team2_players,
        db=db
    )
    return result