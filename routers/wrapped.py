"""
Wrapped 2025 API Router

Provides endpoints for the "Hindsight 2025 Wrapped" feature - 
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

# Default date range for 2025 Wrapped
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
        "title": "Hindsight 2025 Wrapped",
        "subtitle": "The Year in Overs",
        "date_range": {
            "start": DEFAULT_START_DATE,
            "end": DEFAULT_END_DATE
        },
        "cards": [
            {
                "id": "intro",
                "title": "2025 in One Breath",
                "subtitle": "Global run rate by phase",
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
                "title": "Middle-Overs Merchants",
                "subtitle": "Masters of overs 7-15",
                "order": 3
            },
            {
                "id": "death_hitters",
                "title": "Death is a Personality Trait",
                "subtitle": "The finishers who lived dangerously",
                "order": 4
            },
            {
                "id": "pace_vs_spin",
                "title": "Pace vs Spin: 2025's Split Brain",
                "subtitle": "Who crushed what type of bowling",
                "order": 5
            },
            {
                "id": "powerplay_thieves",
                "title": "Powerplay Wicket Thieves",
                "subtitle": "Early breakthroughs specialists",
                "order": 6
            },
            {
                "id": "nineteenth_over_gods",
                "title": "The 19th Over Gods",
                "subtitle": "Death overs bowling excellence",
                "order": 7
            },
            {
                "id": "elo_movers",
                "title": "Teams That Became Different People",
                "subtitle": "Biggest ELO risers and fallers",
                "order": 8
            },
            {
                "id": "venue_vibes",
                "title": "Venues Had Vibes",
                "subtitle": "Par scores and chase bias",
                "order": 9
            }
        ]
    }
