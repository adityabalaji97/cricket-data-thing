"""
Wrapped Service

Main service class that orchestrates all wrapped card data fetching.
All cards now use proper competition filtering.
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

# Import ALL modular card functions
from .card_intro import get_intro_data
from .card_powerplay_bullies import get_powerplay_bullies_data
from .card_death_hitters import get_death_hitters_data
from .card_middle_merchants import get_middle_merchants_data
from .card_pace_vs_spin import get_pace_vs_spin_data
from .card_controlled_aggression import get_controlled_aggression_data
from .card_uncontrolled_chaos import get_uncontrolled_chaos_data
from .card_three_sixty_batters import get_three_sixty_batters_data
from .card_rare_shot_specialists import get_rare_shot_specialists_data
from .card_length_masters import get_length_masters_data
from .card_sweep_evolution import get_sweep_evolution_data
from .card_powerplay_thieves import get_powerplay_thieves_data
from .card_middle_overs_squeeze import get_middle_overs_squeeze_data
from .card_nineteenth_over_gods import get_nineteenth_over_gods_data
from .card_bowler_type_dominance import get_bowler_type_dominance_data
from .card_needle_movers import get_needle_movers_data
from .card_chase_masters import get_chase_masters_data
from .card_venue_vibes import get_venue_vibes_data
from .card_elo_movers import get_elo_movers_data
from .card_batter_hand_breakdown import get_batter_hand_breakdown_data
from .card_bowler_handedness import get_bowler_handedness_data

logger = logging.getLogger(__name__)

# All cards are now migrated to new modular structure with proper filtering
MIGRATED_CARDS = {
    "intro": get_intro_data,
    "powerplay_bullies": get_powerplay_bullies_data,
    "middle_merchants": get_middle_merchants_data,
    "death_hitters": get_death_hitters_data,
    "pace_vs_spin": get_pace_vs_spin_data,
    "controlled_aggression": get_controlled_aggression_data,
    "uncontrolled_chaos": get_uncontrolled_chaos_data,
    "three_sixty_batters": get_three_sixty_batters_data,
    "rare_shot_specialists": get_rare_shot_specialists_data,
    "length_masters": get_length_masters_data,
    "sweep_evolution": get_sweep_evolution_data,
    "powerplay_thieves": get_powerplay_thieves_data,
    "middle_overs_squeeze": get_middle_overs_squeeze_data,
    "nineteenth_over_gods": get_nineteenth_over_gods_data,
    "bowler_type_dominance": get_bowler_type_dominance_data,
    "needle_movers": get_needle_movers_data,
    "chase_masters": get_chase_masters_data,
    "venue_vibes": get_venue_vibes_data,
    "elo_movers": get_elo_movers_data,
    "batter_hand_breakdown": get_batter_hand_breakdown_data,
    "bowler_handedness": get_bowler_handedness_data,
}


class WrappedService:
    """
    Service class for fetching wrapped card data.
    
    All cards now use the new modular structure with proper competition filtering.
    """
    
    def __init__(self):
        self._card_methods = MIGRATED_CARDS.copy()
    
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
        """
        if card_id in self._card_methods:
            method = self._card_methods[card_id]
            return method(
                start_date=start_date,
                end_date=end_date,
                leagues=leagues,
                include_international=include_international,
                db=db,
                top_teams=top_teams
            )
        
        # Fallback: return placeholder for unknown cards
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
