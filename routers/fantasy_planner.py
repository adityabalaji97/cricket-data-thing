"""
Fantasy Team Planner API endpoints.

Provides schedule, recommendations, player outlook, and transfer planning
for IPL 2026 season-long fantasy (fantasy.iplt20.com).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_session
from services.fantasy_planner import (
    get_schedule_with_density,
    get_fantasy_recommendations,
    get_player_outlook,
    get_transfer_plan,
)

router = APIRouter(prefix="/fantasy-planner", tags=["fantasy-planner"])


@router.get("/schedule")
def schedule(
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD), defaults to today"),
):
    """Full IPL 2026 schedule with per-team fixture density analysis."""
    return get_schedule_with_density(from_date=from_date)


@router.get("/recommendations")
def recommendations(
    current_team: Optional[str] = Query(None, description="Comma-separated current player names"),
    matches_ahead: int = Query(3, ge=1, le=20),
    transfers_remaining: int = Query(160, ge=0),
    matches_played: int = Query(0, ge=0),
    from_date: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    """Recommend optimal 11-player squad for upcoming matches."""
    team_list = [n.strip() for n in current_team.split(",")] if current_team else None
    return get_fantasy_recommendations(
        db=db,
        matches_ahead=matches_ahead,
        current_team=team_list,
        transfers_remaining=transfers_remaining,
        matches_played=matches_played,
        from_date=from_date,
    )


@router.get("/player/{player_name}/outlook")
def player_outlook(
    player_name: str,
    from_date: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    """Player's upcoming fixtures, venue history, and expected points per match."""
    return get_player_outlook(db=db, player_name=player_name, from_date=from_date)


@router.get("/transfer-plan")
def transfer_plan(
    current_team: Optional[str] = Query(None, description="Comma-separated current player names"),
    gameweek_start: int = Query(1, ge=1),
    gameweek_end: int = Query(3, ge=1),
    transfers_budget: int = Query(160, ge=0),
    from_date: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    """Multi-gameweek transfer plan minimizing transfers while maximizing points."""
    team_list = [n.strip() for n in current_team.split(",")] if current_team else []
    return get_transfer_plan(
        db=db,
        current_team=team_list,
        gameweek_start=gameweek_start,
        gameweek_end=gameweek_end,
        transfers_budget=transfers_budget,
        from_date=from_date,
    )
