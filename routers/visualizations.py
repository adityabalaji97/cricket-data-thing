"""
Visualizations Router - Wagon Wheel and Pitch Map Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_session
from services.visualizations import (
    get_wagon_wheel_data,
    get_pitch_map_data,
    get_bowler_wagon_wheel_data,
    get_bowler_pitch_map_data,
    get_venue_wagon_wheel_data,
    get_venue_pitch_map_data,
)

router = APIRouter(prefix="/visualizations", tags=["visualizations"])


@router.get("/player/{player_name}/wagon-wheel")
def get_player_wagon_wheel(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    venue: Optional[str] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    phase: Optional[str] = Query(default="overall"),
    bowl_kind: Optional[str] = Query(default=None),
    bowl_style: Optional[str] = Query(default=None),
    line: Optional[str] = Query(default=None),
    length: Optional[str] = Query(default=None),
    shot: Optional[str] = Query(default=None),
    db: Session = Depends(get_session)
):
    """
    Get wagon wheel visualization data for a batter.

    Returns individual deliveries with wagon coordinates (wagon_x, wagon_y) showing
    where the ball ended up after the batter played the shot.

    **Parameters:**
    - **player_name**: Name of the batter
    - **start_date**: Filter by start date (YYYY-MM-DD)
    - **end_date**: Filter by end date (YYYY-MM-DD)
    - **venue**: Filter by specific venue
    - **leagues**: List of league names to include
    - **include_international**: Include international matches
    - **top_teams**: If including international, limit to top N ranked teams
    - **phase**: Match phase filter - "overall", "powerplay" (0-5), "middle" (6-14), "death" (15+)
    - **bowl_kind**: Filter by bowling kind - "pace bowler" or "spin bowler"
    - **bowl_style**: Filter by specific bowling style (e.g., "RF", "SLO", etc.)
    - **line**: Filter by ball line (e.g., "OUTSIDE_OFFSTUMP", "ON_STUMPS", etc.)
    - **length**: Filter by ball length (e.g., "FULL", "GOOD_LENGTH", "SHORT", etc.)
    - **shot**: Filter by shot type (e.g., "COVER_DRIVE", "PULL", "CUT", etc.)

    **Returns:**
    ```json
    {
        "deliveries": [
            {
                "wagon_x": 220,
                "wagon_y": 145,
                "wagon_zone": 3,
                "runs": 4,
                "shot": "COVER_DRIVE",
                "line": "OUTSIDE_OFFSTUMP",
                "length": "FULL",
                "bowl_kind": "pace bowler",
                "bowl_style": "RF",
                "bowler": "J Bumrah",
                "over": 12,
                "phase": "middle",
                "match_id": "12345",
                "date": "2024-05-15",
                "venue": "Wankhede Stadium",
                "competition": "Indian Premier League"
            },
            ...
        ],
        "total_deliveries": 450,
        "filters": {
            "phase": "overall",
            "bowl_kind": null,
            "bowl_style": null
        }
    }
    ```
    """
    try:
        deliveries = get_wagon_wheel_data(
            db=db,
            batter=player_name,
            start_date=start_date,
            end_date=end_date,
            venue=venue,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            phase=phase,
            bowl_kind=bowl_kind,
            bowl_style=bowl_style,
            line=line,
            length=length,
            shot=shot
        )

        return {
            "deliveries": deliveries,
            "total_deliveries": len(deliveries),
            "filters": {
                "phase": phase,
                "bowl_kind": bowl_kind,
                "bowl_style": bowl_style,
                "line": line,
                "length": length,
                "shot": shot
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch wagon wheel data: {str(e)}")


@router.get("/player/{player_name}/pitch-map")
def get_player_pitch_map(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    venue: Optional[str] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    phase: Optional[str] = Query(default="overall"),
    bowl_kind: Optional[str] = Query(default=None),
    bowl_style: Optional[str] = Query(default=None),
    line: Optional[str] = Query(default=None),
    length: Optional[str] = Query(default=None),
    shot: Optional[str] = Query(default=None),
    db: Session = Depends(get_session)
):
    """
    Get pitch map visualization data for a batter.

    Returns aggregated statistics by line and length combinations, showing how
    the batter performs against different ball types.

    **Parameters:**
    - Same as wagon-wheel endpoint

    **Returns:**
    ```json
    {
        "cells": [
            {
                "line": "OUTSIDE_OFFSTUMP",
                "length": "GOOD_LENGTH",
                "balls": 125,
                "runs": 178,
                "wickets": 3,
                "dots": 42,
                "fours": 18,
                "sixes": 5,
                "controlled_shots": 95,
                "average": 59.33,
                "strike_rate": 142.4,
                "dot_percentage": 33.6,
                "boundary_percentage": 18.4,
                "control_percentage": 76.0
            },
            ...
        ],
        "total_balls": 450,
        "filters": {
            "phase": "overall",
            "bowl_kind": null,
            "bowl_style": null
        }
    }
    ```
    """
    try:
        cells = get_pitch_map_data(
            db=db,
            batter=player_name,
            start_date=start_date,
            end_date=end_date,
            venue=venue,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            phase=phase,
            bowl_kind=bowl_kind,
            bowl_style=bowl_style,
            line=line,
            length=length,
            shot=shot
        )

        total_balls = sum(cell["balls"] for cell in cells)

        return {
            "cells": cells,
            "total_balls": total_balls,
            "filters": {
                "phase": phase,
                "bowl_kind": bowl_kind,
                "bowl_style": bowl_style,
                "line": line,
                "length": length,
                "shot": shot
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pitch map data: {str(e)}")


@router.get("/bowler/{player_name}/wagon-wheel")
def get_bowler_wagon_wheel(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    venue: Optional[str] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    phase: Optional[str] = Query(default="overall"),
    line: Optional[str] = Query(default=None),
    length: Optional[str] = Query(default=None),
    shot: Optional[str] = Query(default=None),
    db: Session = Depends(get_session)
):
    """
    Get wagon wheel visualization data for a bowler - shows where they were hit.

    **Parameters:**
    - **player_name**: Name of the bowler
    - **start_date**: Filter by start date (YYYY-MM-DD)
    - **end_date**: Filter by end date (YYYY-MM-DD)
    - **venue**: Filter by specific venue
    - **leagues**: List of league names to include
    - **include_international**: Include international matches
    - **top_teams**: If including international, limit to top N ranked teams
    - **phase**: Match phase filter - "overall", "powerplay" (0-5), "middle" (6-14), "death" (15+)
    - **line**: Filter by ball line
    - **length**: Filter by ball length
    - **shot**: Filter by shot type

    **Returns:**
    Deliveries showing where the bowler was hit with wagon coordinates.
    """
    try:
        deliveries = get_bowler_wagon_wheel_data(
            db=db,
            bowler=player_name,
            start_date=start_date,
            end_date=end_date,
            venue=venue,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            phase=phase,
            line=line,
            length=length,
            shot=shot
        )

        return {
            "deliveries": deliveries,
            "total_deliveries": len(deliveries),
            "filters": {
                "phase": phase,
                "line": line,
                "length": length,
                "shot": shot
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bowler wagon wheel data: {str(e)}")


@router.get("/bowler/{player_name}/pitch-map")
def get_bowler_pitch_map(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    venue: Optional[str] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    phase: Optional[str] = Query(default="overall"),
    line: Optional[str] = Query(default=None),
    length: Optional[str] = Query(default=None),
    shot: Optional[str] = Query(default=None),
    db: Session = Depends(get_session)
):
    """
    Get pitch map visualization data for a bowler.

    Returns aggregated statistics by line and length combinations, showing
    the bowler's economy and effectiveness in different areas.

    **Parameters:**
    - Same as bowler wagon-wheel endpoint

    **Returns:**
    Pitch map cells with economy, dot percentage, boundary percentage, and wickets.
    """
    try:
        cells = get_bowler_pitch_map_data(
            db=db,
            bowler=player_name,
            start_date=start_date,
            end_date=end_date,
            venue=venue,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            phase=phase,
            line=line,
            length=length,
            shot=shot
        )

        total_balls = sum(cell["balls"] for cell in cells)

        return {
            "cells": cells,
            "total_balls": total_balls,
            "filters": {
                "phase": phase,
                "line": line,
                "length": length,
                "shot": shot
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bowler pitch map data: {str(e)}")


@router.get("/venue/{venue}/wagon-wheel")
def get_venue_wagon_wheel(
    venue: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    phase: Optional[str] = Query(default="overall"),
    bowl_kind: Optional[str] = Query(default=None),
    bowl_style: Optional[str] = Query(default=None),
    line: Optional[str] = Query(default=None),
    length: Optional[str] = Query(default=None),
    shot: Optional[str] = Query(default=None),
    db: Session = Depends(get_session)
):
    try:
        deliveries = get_venue_wagon_wheel_data(
            db=db,
            venue=venue,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            phase=phase,
            bowl_kind=bowl_kind,
            bowl_style=bowl_style,
            line=line,
            length=length,
            shot=shot
        )
        return {
            "deliveries": deliveries,
            "total_deliveries": len(deliveries),
            "filters": {
                "phase": phase,
                "bowl_kind": bowl_kind,
                "bowl_style": bowl_style,
                "line": line,
                "length": length,
                "shot": shot
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch venue wagon wheel data: {str(e)}")


@router.get("/venue/{venue}/pitch-map")
def get_venue_pitch_map(
    venue: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    phase: Optional[str] = Query(default="overall"),
    bowl_kind: Optional[str] = Query(default=None),
    bowl_style: Optional[str] = Query(default=None),
    line: Optional[str] = Query(default=None),
    length: Optional[str] = Query(default=None),
    shot: Optional[str] = Query(default=None),
    db: Session = Depends(get_session)
):
    try:
        cells = get_venue_pitch_map_data(
            db=db,
            venue=venue,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            phase=phase,
            bowl_kind=bowl_kind,
            bowl_style=bowl_style,
            line=line,
            length=length,
            shot=shot
        )
        return {
            "cells": cells,
            "total_balls": sum(cell["balls"] for cell in cells),
            "filters": {
                "phase": phase,
                "bowl_kind": bowl_kind,
                "bowl_style": bowl_style,
                "line": line,
                "length": length,
                "shot": shot
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch venue pitch map data: {str(e)}")
