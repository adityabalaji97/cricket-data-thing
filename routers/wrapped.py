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
from services.wrapped import (
    WrappedService, 
    CARD_CONFIG, 
    get_card_order, 
    get_initial_card_ids, 
    get_lazy_card_ids,
    WRAPPED_DEFAULT_LEAGUES,
    WRAPPED_DEFAULT_TOP_TEAMS,
    WRAPPED_DEFAULT_INCLUDE_INTERNATIONAL
)

router = APIRouter(prefix="/wrapped", tags=["wrapped"])
logger = logging.getLogger(__name__)

# Default date range for 2025 In Hindsight
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2025-12-31"


# Initialize service
wrapped_service = WrappedService()


@router.get("/2025/cards")
def get_wrapped_cards(
    leagues: List[str] = Query(default=None),
    include_international: bool = Query(default=None),
    top_teams: int = Query(default=None),
    db: Session = Depends(get_session)
):
    """
    Get all card data for the 2025 Wrapped experience.
    Returns an array of card objects with their data and metadata.
    
    NOTE: This endpoint loads ALL cards. For faster initial load,
    use /2025/cards/initial instead.
    
    - leagues: List of leagues to filter. If not provided, uses default top leagues (IPL, SA20, BBL, etc.)
    - include_international: Include international matches (default True)
    - top_teams: Number of top international teams to include (default 20)
    """
    try:
        # Apply defaults if not provided
        effective_leagues = leagues if leagues is not None else WRAPPED_DEFAULT_LEAGUES
        effective_include_international = include_international if include_international is not None else WRAPPED_DEFAULT_INCLUDE_INTERNATIONAL
        effective_top_teams = top_teams if top_teams is not None else WRAPPED_DEFAULT_TOP_TEAMS
        
        return wrapped_service.get_all_cards(
            start_date=DEFAULT_START_DATE,
            end_date=DEFAULT_END_DATE,
            leagues=effective_leagues,
            include_international=effective_include_international,
            db=db,
            top_teams=effective_top_teams
        )
    except Exception as e:
        logger.error(f"Error fetching wrapped cards: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/2025/cards/initial")
def get_initial_cards(
    start_date: str = Query(default=DEFAULT_START_DATE),
    end_date: str = Query(default=DEFAULT_END_DATE),
    leagues: List[str] = Query(default=None),
    include_international: bool = Query(default=None),
    top_teams: int = Query(default=None),
    no_leagues: bool = Query(default=False, description="If true, don't include any leagues (T20I only)"),
    db: Session = Depends(get_session)
):
    """
    Get only the initial batch of cards for fast first load.
    Returns cards marked as 'initial: True' in CARD_CONFIG.
    
    Use this endpoint for the initial page load, then lazy-load
    remaining cards using /2025/cards/batch as user navigates.
    
    - start_date: Start date (YYYY-MM-DD), default 2025-01-01
    - end_date: End date (YYYY-MM-DD), default 2025-12-31
    - leagues: List of leagues to filter (if not provided, uses defaults)
    - include_international: Include T20I matches between top teams
    - no_leagues: If true, don't include any leagues (for T20I only mode)
    """
    try:
        # Handle leagues: if no_leagues is True, use empty list; otherwise use provided or defaults
        if no_leagues:
            effective_leagues = []
        else:
            effective_leagues = leagues if leagues is not None else WRAPPED_DEFAULT_LEAGUES
        
        effective_include_international = include_international if include_international is not None else WRAPPED_DEFAULT_INCLUDE_INTERNATIONAL
        effective_top_teams = top_teams if top_teams is not None else WRAPPED_DEFAULT_TOP_TEAMS
        
        initial_ids = get_initial_card_ids()
        result = wrapped_service.get_cards_batch(
            card_ids=initial_ids,
            start_date=start_date,
            end_date=end_date,
            leagues=effective_leagues,
            include_international=effective_include_international,
            db=db,
            top_teams=effective_top_teams
        )
        # Add metadata about remaining cards
        result["initial_load"] = True
        result["remaining_card_ids"] = get_lazy_card_ids()
        result["total_cards_available"] = len(CARD_CONFIG)
        # Include current filters in response
        result["applied_filters"] = {
            "start_date": start_date,
            "end_date": end_date,
            "leagues": effective_leagues,
            "include_international": effective_include_international
        }
        return result
    except Exception as e:
        logger.error(f"Error fetching initial cards: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/2025/cards/batch")
def get_cards_batch(
    card_ids: List[str] = Query(..., description="List of card IDs to fetch"),
    start_date: str = Query(default=DEFAULT_START_DATE),
    end_date: str = Query(default=DEFAULT_END_DATE),
    leagues: List[str] = Query(default=None),
    include_international: bool = Query(default=None),
    top_teams: int = Query(default=None),
    no_leagues: bool = Query(default=False, description="If true, don't include any leagues (T20I only)"),
    db: Session = Depends(get_session)
):
    """
    Get data for a specific batch of cards.
    Use this for lazy-loading cards as user navigates through the experience.
    
    - card_ids: List of card IDs to fetch (required)
    - start_date: Start date (YYYY-MM-DD), default 2025-01-01
    - end_date: End date (YYYY-MM-DD), default 2025-12-31
    - leagues: List of leagues to filter
    - include_international: Include international matches
    - top_teams: Number of top international teams to include
    - no_leagues: If true, don't include any leagues (for T20I only mode)
    """
    try:
        # Handle leagues: if no_leagues is True, use empty list; otherwise use provided or defaults
        if no_leagues:
            effective_leagues = []
        else:
            effective_leagues = leagues if leagues is not None else WRAPPED_DEFAULT_LEAGUES
        
        effective_include_international = include_international if include_international is not None else WRAPPED_DEFAULT_INCLUDE_INTERNATIONAL
        effective_top_teams = top_teams if top_teams is not None else WRAPPED_DEFAULT_TOP_TEAMS
        
        return wrapped_service.get_cards_batch(
            card_ids=card_ids,
            start_date=start_date,
            end_date=end_date,
            leagues=effective_leagues,
            include_international=effective_include_international,
            db=db,
            top_teams=effective_top_teams
        )
    except Exception as e:
        logger.error(f"Error fetching cards batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/2025/card/{card_id}")
def get_wrapped_card(
    card_id: str,
    leagues: List[str] = Query(default=None),
    include_international: bool = Query(default=None),
    top_teams: int = Query(default=None),
    db: Session = Depends(get_session)
):
    """
    Get data for a single wrapped card.
    Useful for deep linking to specific cards.
    
    - card_id: The card identifier (e.g., 'intro', 'powerplay_bullies')
    - leagues: List of leagues to filter. If not provided, uses default top leagues.
    - include_international: Include international matches (default True)
    - top_teams: Number of top international teams to include (default 20)
    """
    try:
        # Apply defaults if not provided
        effective_leagues = leagues if leagues is not None else WRAPPED_DEFAULT_LEAGUES
        effective_include_international = include_international if include_international is not None else WRAPPED_DEFAULT_INCLUDE_INTERNATIONAL
        effective_top_teams = top_teams if top_teams is not None else WRAPPED_DEFAULT_TOP_TEAMS
        
        return wrapped_service.get_single_card(
            card_id=card_id,
            start_date=DEFAULT_START_DATE,
            end_date=DEFAULT_END_DATE,
            leagues=effective_leagues,
            include_international=effective_include_international,
            db=db,
            top_teams=effective_top_teams
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
    
    Card order is determined by position in CARD_CONFIG.
    To reorder cards, modify CARD_CONFIG in services/wrapped.py.
    """
    return {
        "year": 2025,
        "title": "2025 In Hindsight",
        "subtitle": "The Year in Review",
        "date_range": {
            "start": DEFAULT_START_DATE,
            "end": DEFAULT_END_DATE
        },
        "total_cards": len(CARD_CONFIG),
        "initial_card_ids": get_initial_card_ids(),
        "lazy_card_ids": get_lazy_card_ids(),
        "default_filters": {
            "leagues": WRAPPED_DEFAULT_LEAGUES,
            "include_international": WRAPPED_DEFAULT_INCLUDE_INTERNATIONAL,
            "top_teams": WRAPPED_DEFAULT_TOP_TEAMS
        },
        "cards": [
            {
                "id": card["id"],
                "title": card["title"],
                "subtitle": card["subtitle"],
                "initial": card.get("initial", False),
                "order": idx + 1
            }
            for idx, card in enumerate(CARD_CONFIG)
        ]
    }
