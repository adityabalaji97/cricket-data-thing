from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from database import get_session
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
def get_dismissal_stats(player_name: str, db: Session = Depends(get_session)):
    """Get dismissal mode distribution for a batter."""
    try:
        query = text("""
            SELECT
                d.wicket_type,
                COUNT(*) as count,
                CASE
                    WHEN d.over < 6 THEN 'powerplay'
                    WHEN d.over < 16 THEN 'middle'
                    ELSE 'death'
                END as phase
            FROM deliveries d
            WHERE d.batter = :player_name
              AND d.wicket_type IS NOT NULL
              AND d.wicket_type != ''
            GROUP BY d.wicket_type, phase
            ORDER BY count DESC
        """)
        rows = db.execute(query, {"player_name": player_name}).fetchall()

        overall = {}
        by_phase = {}
        for row in rows:
            wt = row.wicket_type
            count = row.count
            phase = row.phase
            overall[wt] = overall.get(wt, 0) + count
            if phase not in by_phase:
                by_phase[phase] = {}
            by_phase[phase][wt] = by_phase[phase].get(wt, 0) + count

        return {
            "player_name": player_name,
            "overall": overall,
            "by_phase": by_phase
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dismissal stats: {str(e)}")


@router.get("/{player_name}/bowling_dismissal_stats")
def get_bowling_dismissal_stats(player_name: str, db: Session = Depends(get_session)):
    """Get dismissal mode distribution for a bowler (how they take wickets)."""
    try:
        query = text("""
            SELECT
                d.wicket_type,
                COUNT(*) as count,
                CASE
                    WHEN d.over < 6 THEN 'powerplay'
                    WHEN d.over < 16 THEN 'middle'
                    ELSE 'death'
                END as phase
            FROM deliveries d
            WHERE d.bowler = :player_name
              AND d.wicket_type IS NOT NULL
              AND d.wicket_type != ''
            GROUP BY d.wicket_type, phase
            ORDER BY count DESC
        """)
        rows = db.execute(query, {"player_name": player_name}).fetchall()

        overall = {}
        by_phase = {}
        for row in rows:
            wt = row.wicket_type
            count = row.count
            phase = row.phase
            overall[wt] = overall.get(wt, 0) + count
            if phase not in by_phase:
                by_phase[phase] = {}
            by_phase[phase][wt] = by_phase[phase].get(wt, 0) + count

        return {
            "player_name": player_name,
            "overall": overall,
            "by_phase": by_phase
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bowling dismissal stats: {str(e)}")


@router.get("/{player_name}/player_type")
def get_player_type(player_name: str, db: Session = Depends(get_session)):
    """Detect if player has batting and/or bowling data."""
    try:
        batting_query = text("SELECT COUNT(*) FROM deliveries WHERE batter = :name LIMIT 1")
        bowling_query = text("SELECT COUNT(*) FROM deliveries WHERE bowler = :name LIMIT 1")

        has_batting = db.execute(batting_query, {"name": player_name}).scalar() > 0
        has_bowling = db.execute(bowling_query, {"name": player_name}).scalar() > 0

        return {
            "player_name": player_name,
            "has_batting_data": has_batting,
            "has_bowling_data": has_bowling
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect player type: {str(e)}")
