"""
Wrapped Service

Main service class that orchestrates all wrapped card data fetching.
Supports both new modular cards and legacy cards during migration.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
import logging

from .constants import (
    CARD_CONFIG,
    WRAPPED_DEFAULT_LEAGUES,
    WRAPPED_DEFAULT_TOP_TEAMS,
    WRAPPED_DEFAULT_INCLUDE_INTERNATIONAL,
    get_card_config_by_id
)

# Import NEW modular card functions (properly filtered)
from .card_intro import get_intro_data
from .card_powerplay_bullies import get_powerplay_bullies_data
from .card_death_hitters import get_death_hitters_data
from .card_middle_merchants import get_middle_merchants_data

logger = logging.getLogger(__name__)

# Cards that have been migrated to new modular structure
MIGRATED_CARDS = {
    "intro": get_intro_data,
    "powerplay_bullies": get_powerplay_bullies_data,
    "death_hitters": get_death_hitters_data,
    "middle_merchants": get_middle_merchants_data,
}


class WrappedService:
    """
    Service class for fetching wrapped card data.
    
    Uses new modular cards where available, falls back to legacy for others.
    """
    
    def __init__(self):
        self._legacy_service = None
        self._card_methods = MIGRATED_CARDS.copy()
    
    def _get_legacy_service(self):
        """Lazy load legacy service for unmigrated cards."""
        if self._legacy_service is None:
            try:
                # Import legacy wrapped module
                from services import wrapped_legacy as legacy_wrapped
                self._legacy_service = legacy_wrapped.WrappedService()
            except ImportError:
                logger.warning("Legacy wrapped service not available")
                self._legacy_service = None
        return self._legacy_service
    
    def get_card_data(
        self,
        card_id: str,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        top_teams: int = WRAPPED_DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """
        Get data for a single card by ID.
        Uses migrated method if available, otherwise falls back to legacy.
        """
        # Check if we have a migrated method for this card
        if card_id in self._card_methods:
            method = self._card_methods[card_id]
            logger.info(f"Using NEW modular method for card: {card_id}")
            return method(
                start_date=start_date,
                end_date=end_date,
                leagues=leagues,
                include_international=include_international,
                db=db,
                top_teams=top_teams
            )
        
        # Try legacy service for unmigrated cards
        legacy = self._get_legacy_service()
        if legacy:
            logger.info(f"Using LEGACY method for card: {card_id}")
            # Use get_single_card which returns {success, card}
            result = legacy.get_single_card(
                card_id=card_id,
                start_date=start_date,
                end_date=end_date,
                leagues=leagues,
                include_international=include_international,
                db=db,
                top_teams=top_teams
            )
            # Extract the card data from the result
            if result.get("success") and result.get("card"):
                return result["card"]
            return result
        
        # Fallback: return placeholder
        card_config = get_card_config_by_id(card_id)
        if card_config:
            return {
                "card_id": card_id,
                "card_title": card_config["title"],
                "card_subtitle": card_config["subtitle"],
                "visualization_type": "placeholder",
                "message": "Card not yet available",
                "data": {}
            }
        
        raise ValueError(f"Unknown card ID: {card_id}")
    
    def get_single_card(
        self,
        card_id: str,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        top_teams: int = WRAPPED_DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """
        Get data for a single card.
        """
        try:
            card_data = self.get_card_data(
                card_id=card_id,
                start_date=start_date,
                end_date=end_date,
                leagues=leagues,
                include_international=include_international,
                db=db,
                top_teams=top_teams
            )
            
            return {
                "success": True,
                "card": card_data
            }
        except Exception as e:
            logger.error(f"Error fetching card {card_id}: {str(e)}")
            raise
    
    def get_cards_batch(
        self,
        card_ids: List[str],
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        top_teams: int = WRAPPED_DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """
        Get data for multiple cards.
        """
        cards = []
        errors = []
        
        for card_id in card_ids:
            try:
                card_data = self.get_card_data(
                    card_id=card_id,
                    start_date=start_date,
                    end_date=end_date,
                    leagues=leagues,
                    include_international=include_international,
                    db=db,
                    top_teams=top_teams
                )
                cards.append(card_data)
            except Exception as e:
                logger.error(f"Error fetching card {card_id}: {str(e)}")
                errors.append({"card_id": card_id, "error": str(e)})
        
        return {
            "success": len(errors) == 0,
            "cards": cards,
            "errors": errors if errors else None,
            "fetched_count": len(cards),
            "requested_count": len(card_ids)
        }
    
    def get_all_cards(
        self,
        start_date: str,
        end_date: str,
        leagues: List[str],
        include_international: bool,
        db: Session,
        top_teams: int = WRAPPED_DEFAULT_TOP_TEAMS
    ) -> Dict[str, Any]:
        """
        Get data for all cards.
        """
        all_card_ids = [card["id"] for card in CARD_CONFIG]
        return self.get_cards_batch(
            card_ids=all_card_ids,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            db=db,
            top_teams=top_teams
        )
