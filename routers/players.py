from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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
