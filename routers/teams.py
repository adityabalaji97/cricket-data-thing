from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_session
from services.teams import get_team_matches_service, get_team_batting_stats_service, get_team_phase_stats_service
from services.teams_fixed import get_team_phase_stats_service_fixed

router = APIRouter(prefix="/teams", tags=["teams"])

@router.get("/{team_name}/matches")
def get_team_matches(
    team_name: str,
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_session)
):
    """
    Get all matches played by a specific team within a date range
    
    Args:
        team_name: Name of the team (can be full name or abbreviation from /teams endpoint)
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        List of matches with team scores, opponents, results, and match details
    """
    try:
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
            "matches": matches
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
