"""
2025 In Hindsight API Router

Provides endpoints for the "2025 In Hindsight" feature - 
a Spotify Wrapped-style experience for T20 cricket statistics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from database import get_session
from services.wrapped import WrappedService

router = APIRouter(prefix="/wrapped", tags=["wrapped"])
logger = logging.getLogger(__name__)

# Default date range for 2025 In Hindsight
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2025-12-31"

# Default settings
DEFAULT_TOP_TEAMS = 20

# Initialize service
wrapped_service = WrappedService()


@router.get("/2025/cards")
def get_wrapped_cards(
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=True),
    top_teams: int = Query(default=DEFAULT_TOP_TEAMS),
    db: Session = Depends(get_session)
):
    """
    Get all card data for the 2025 Wrapped experience.
    Returns an array of card objects with their data and metadata.
    
    - leagues: List of leagues to filter. If empty, includes ALL leagues from database.
    - include_international: Include international matches (default True)
    - top_teams: Number of top international teams to include (default 20)
    """
    try:
        return wrapped_service.get_all_cards(
            start_date=DEFAULT_START_DATE,
            end_date=DEFAULT_END_DATE,
            leagues=leagues,
            include_international=include_international,
            db=db,
            top_teams=top_teams
        )
    except Exception as e:
        logger.error(f"Error fetching wrapped cards: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/2025/card/{card_id}")
def get_wrapped_card(
    card_id: str,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=True),
    top_teams: int = Query(default=DEFAULT_TOP_TEAMS),
    db: Session = Depends(get_session)
):
    """
    Get data for a single wrapped card.
    Useful for deep linking to specific cards.
    
    - card_id: The card identifier (e.g., 'intro', 'powerplay_bullies')
    - leagues: List of leagues to filter. If empty, includes ALL leagues from database.
    - include_international: Include international matches (default True)
    - top_teams: Number of top international teams to include (default 20)
    """
    try:
        return wrapped_service.get_single_card(
            card_id=card_id,
            start_date=DEFAULT_START_DATE,
            end_date=DEFAULT_END_DATE,
            leagues=leagues,
            include_international=include_international,
            db=db,
            top_teams=top_teams
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching wrapped card {card_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/2025/metadata")
def get_wrapped_metadata():
    """
    Get metadata about the wrapped experience.
    Includes card order, titles, descriptions for the UI.
    """
    return {
        "year": 2025,
        "title": "2025 In Hindsight",
        "subtitle": "The Year in Review",
        "date_range": {
            "start": DEFAULT_START_DATE,
            "end": DEFAULT_END_DATE
        },
        "cards": [
            {
                "id": "intro",
                "title": "2025 in One Breath",
                "subtitle": "The rhythm of T20 cricket",
                "order": 1
            },
            {
                "id": "powerplay_bullies",
                "title": "Powerplay Bullies",
                "subtitle": "Who dominated the first 6 overs",
                "order": 2
            },
            {
                "id": "middle_merchants",
                "title": "Middle Merchants",
                "subtitle": "Masters of overs 7-15",
                "order": 3
            },
            {
                "id": "death_hitters",
                "title": "Death Hitters",
                "subtitle": "The finishers who lived dangerously",
                "order": 4
            },
            {
                "id": "pace_vs_spin",
                "title": "Pace vs Spin",
                "subtitle": "2025's split personality batters",
                "order": 5
            },
            {
                "id": "powerplay_thieves",
                "title": "PP Wicket Thieves",
                "subtitle": "Early breakthrough specialists",
                "order": 6
            },
            {
                "id": "nineteenth_over_gods",
                "title": "Death Over Gods",
                "subtitle": "Overs 16-20 bowling excellence",
                "order": 7
            },
            {
                "id": "elo_movers",
                "title": "ELO Movers",
                "subtitle": "Teams that transformed in 2025",
                "order": 8
            },
            {
                "id": "venue_vibes",
                "title": "Venue Vibes",
                "subtitle": "Par scores and chase bias",
                "order": 9
            },
            {
                "id": "controlled_aggression",
                "title": "Controlled Chaos",
                "subtitle": "The most efficient aggressors",
                "order": 10
            },
            {
                "id": "360_batters",
                "title": "360° Batters",
                "subtitle": "Who scores all around the ground",
                "order": 11
            },
            {
                "id": "batter_hand_breakdown",
                "title": "Left vs Right",
                "subtitle": "Batting hand breakdown",
                "order": 12
            },
            {
                "id": "length_masters",
                "title": "Length Masters",
                "subtitle": "Versatile scorers across all lengths",
                "order": 13
            },
            {
                "id": "rare_shot_specialists",
                "title": "Rare Shot Artists",
                "subtitle": "Masters of unconventional shots",
                "order": 14
            },
            {
                "id": "bowler_type_dominance",
                "title": "Pace vs Spin",
                "subtitle": "The bowling arms race",
                "order": 15
            }
        ]
    }
