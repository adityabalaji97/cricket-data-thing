from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_session
from services.teams import get_team_matches_service, get_team_batting_stats_service, get_team_phase_stats_service
from services.teams_fixed import get_team_phase_stats_service_fixed, get_team_bowling_phase_stats_service_fixed
from services.teams_batting_order import get_team_batting_order_service
from services.teams_bowling_order import get_team_bowling_order_service
from services.elo import get_team_elo_stats_service, get_team_matches_with_elo_service

router = APIRouter(prefix="/teams", tags=["teams"])

@router.get("/{team_name}/matches")
def get_team_matches(
    team_name: str,
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    include_elo: bool = Query(False, description="Include ELO ratings in match data"),
    db: Session = Depends(get_session)
):
    """
    Get all matches played by a specific team within a date range
    
    Args:
        team_name: Name of the team (can be full name or abbreviation from /teams endpoint)
        start_date: Optional start date filter
        end_date: Optional end date filter
        include_elo: Whether to include ELO ratings in the response
    
    Returns:
        List of matches with team scores, opponents, results, and match details
    """
    try:
        if include_elo:
            matches = get_team_matches_with_elo_service(
                team_name=team_name,
                start_date=start_date,
                end_date=end_date,
                db=db
            )
        else:
            matches = get_team_matches_service(
                team_name=team_name,
                start_date=start_date,
                end_date=end_date,
                db=db
            )
        
        return {
            "team": team_name,
            "total_matches": len(matches),
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "includes_elo": include_elo,
            "matches": matches
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{team_name}/elo-stats")
def get_team_elo_stats(
    team_name: str,
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """
    Get ELO statistics for a team within a date range
    
    Args:
        team_name: Name of the team (can be full name or abbreviation)
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        ELO statistics including starting ELO, ending ELO, peak ELO, lowest ELO, and history
    """
    try:
        elo_stats = get_team_elo_stats_service(
            team_name=team_name,
            start_date=start_date,
            end_date=end_date,
            db=db
        )
        
        return elo_stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{team_name}/bowling-phase-stats")
def get_team_bowling_phase_stats(
    team_name: str,
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """
    Get aggregated phase-wise bowling statistics for a team (for radar chart)
    
    Args:
        team_name: Name of the team (can be full name or abbreviation)
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        Aggregated phase-wise bowling stats including averages, strike rates and economy rates by phase
    """
    try:
        bowling_phase_stats = get_team_bowling_phase_stats_service_fixed(
            team_name=team_name,
            start_date=start_date,
            end_date=end_date,
            db=db
        )
        
        return {
            "team": team_name,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "bowling_phase_stats": bowling_phase_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{team_name}/batting-stats")
def get_team_batting_stats(
    team_name: str,
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """
    Get all batting stats for a specific team within a date range
    
    Args:
        team_name: Name of the team (can be full name or abbreviation)
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        List of batting stats records with detailed metrics for each player performance
    """
    try:
        batting_stats = get_team_batting_stats_service(
            team_name=team_name,
            start_date=start_date,
            end_date=end_date,
            db=db
        )
        
        return {
            "team": team_name,
            "total_records": len(batting_stats),
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "batting_stats": batting_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{team_name}/phase-stats")
def get_team_phase_stats(
    team_name: str,
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """
    Get aggregated phase-wise batting statistics for a team (for radar chart)
    
    Args:
        team_name: Name of the team (can be full name or abbreviation)
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        Aggregated phase-wise stats including averages and strike rates by phase
    """
    try:
        phase_stats = get_team_phase_stats_service_fixed(
            team_name=team_name,
            start_date=start_date,
            end_date=end_date,
            db=db
        )
        
        return {
            "team": team_name,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "phase_stats": phase_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{team_name}/batting-order")
def get_team_batting_order(
    team_name: str,
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    players: Optional[List[str]] = Query(None, description="Optional custom player list"),
    db: Session = Depends(get_session)
):
    """
    Get batting order with aggregated overall and phase-wise statistics
    
    Args:
        team_name: Name of the team (can be full name or abbreviation)
        start_date: Optional start date filter
        end_date: Optional end date filter
        players: Optional custom player list (overrides team-based filtering)
    
    Returns:
        Batting order with overall and phase-wise stats for each player
    """
    try:
        batting_order_data = get_team_batting_order_service(
            team_name=team_name,
            start_date=start_date,
            end_date=end_date,
            players=players,
            db=db
        )
        
        return batting_order_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{team_name}/bowling-order")
def get_team_bowling_order(
    team_name: str,
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    players: Optional[List[str]] = Query(None, description="Optional custom player list"),
    db: Session = Depends(get_session)
):
    """
    Get bowling order with aggregated overall and phase-wise statistics
    
    Args:
        team_name: Name of the team (can be full name or abbreviation)
        start_date: Optional start date filter
        end_date: Optional end date filter
        players: Optional custom player list (overrides team-based filtering)
    
    Returns:
        Bowling order with overall and phase-wise stats for each player, including most frequent over combinations
    """
    try:
        bowling_order_data = get_team_bowling_order_service(
            team_name=team_name,
            start_date=start_date,
            end_date=end_date,
            players=players,
            db=db
        )
        
        return bowling_order_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
