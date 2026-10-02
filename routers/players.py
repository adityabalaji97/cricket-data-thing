from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from database import get_session
from services.dismissal_stats import get_dismissal_breakdown
from services.players import get_batters_service, get_bowlers_service

router = APIRouter(prefix="/players", tags=["players"])

@router.get("/batters")
def get_batters(db: Session = Depends(get_session)):
    """
    Get list of all batters from the database.
    
    Returns a list of unique batter names who have batting records in the system.
    Data is sorted alphabetically for easy selection in dropdowns.
    
    **Returns:**
    - List of batter names (strings)
    
    **Example Response:**
    ```json
    ["A Badoni", "A Mishra", "A Nortje", "AB de Villiers", "AJ Finch", ...]
    ```
    """
    try:
        return get_batters_service(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch batters: {str(e)}")

@router.get("/bowlers") 
def get_bowlers(db: Session = Depends(get_session)):
    """
    Get list of all bowlers from the database.
    
    Returns a list of unique bowler names who have bowling records in the system.
    Data is sorted alphabetically for easy selection in dropdowns.
    
    **Returns:**
    - List of bowler names (strings)
    
    **Example Response:**
    ```json
    ["A Mishra", "A Nortje", "A Russell", "AA Nortje", "AB de Villiers", ...]
    ```
    """
    try:
        return get_bowlers_service(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bowlers: {str(e)}")

@router.get("/all")
def get_all_players(db: Session = Depends(get_session)):
    """
    Get combined list of all players (batters and bowlers) from the database.
    
    Returns a dictionary with separate lists for batters and bowlers.
    Useful for populating multiple dropdowns in a single API call.
    
    **Returns:**
    - Dictionary with 'batters' and 'bowlers' arrays
    
    **Example Response:**
    ```json
    {
        "batters": ["A Badoni", "A Mishra", ...],
        "bowlers": ["A Mishra", "A Nortje", ...]
    }
    ```
    """
    try:
        batters = get_batters_service(db)
        bowlers = get_bowlers_service(db)
        
        return {
            "batters": batters,
            "bowlers": bowlers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch players: {str(e)}")


@router.get("/{player_name}/dismissal_stats")
def get_dismissal_stats(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    db: Session = Depends(get_session),
):
    """How a batter gets out, under the profile page's filters (services/dismissal_stats.py)."""
    try:
        return get_dismissal_breakdown(
            db, player_name, "batter", start_date=start_date, end_date=end_date, leagues=leagues,
            include_international=include_international, top_teams=top_teams, venue=venue,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dismissal stats: {str(e)}")


@router.get("/{player_name}/bowling_dismissal_stats")
def get_bowling_dismissal_stats(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    db: Session = Depends(get_session),
):
    """How a bowler takes wickets, under the profile page's filters (services/dismissal_stats.py)."""
    try:
        return get_dismissal_breakdown(
            db, player_name, "bowler", start_date=start_date, end_date=end_date, leagues=leagues,
            include_international=include_international, top_teams=top_teams, venue=venue,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bowling dismissal stats: {str(e)}")


@router.get("/{player_name}/player_type")
def get_player_type(player_name: str, db: Session = Depends(get_session)):
    """Detect if player has batting and/or bowling data.

    Checks every stored spelling of the player (expand_name_group) in the per-innings stats tables,
    which hold both naming conventions. It used to look up the exact URL name in the legacy
    deliveries table only, so full names ("Jasprit Bumrah", which search and the player list now
    use) came back as no batting and no bowling, and the profile hid its Batting/Bowling toggle.
    """
    from services.player_aliases import expand_name_group

    try:
        names = expand_name_group([player_name], db) or [player_name]
        has_batting = bool(db.execute(
            text("SELECT EXISTS (SELECT 1 FROM batting_stats WHERE striker = ANY(:names))"), {"names": names}
        ).scalar())
        has_bowling = bool(db.execute(
            text("SELECT EXISTS (SELECT 1 FROM bowling_stats WHERE bowler = ANY(:names))"), {"names": names}
        ).scalar())

        return {
            "player_name": player_name,
            "has_batting_data": has_batting,
            "has_bowling_data": has_bowling
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect player type: {str(e)}")
