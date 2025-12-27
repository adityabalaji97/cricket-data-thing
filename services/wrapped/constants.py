"""
Wrapped Feature Constants

Central configuration for the 2025 In Hindsight feature.
"""

from typing import List

# =============================================================================
# DEFAULT FILTER CONFIGURATION
# =============================================================================
# Top 5 T20 leagues + PSL, plus T20Is between top 20 international teams

WRAPPED_DEFAULT_LEAGUES = [
    'Indian Premier League',
    'IPL',
    'SA20', 
    'Big Bash League',
    'BBL',
    'Vitality Blast',
    'T20 Blast',
    'Super Smash',
    'Pakistan Super League',
    'PSL'
]

WRAPPED_DEFAULT_TOP_TEAMS = 20
WRAPPED_DEFAULT_INCLUDE_INTERNATIONAL = True

# Top 20 international teams (used for T20I filtering)
INTERNATIONAL_TEAMS_RANKED = [
    'India', 'Australia', 'England', 'West Indies', 'New Zealand',
    'South Africa', 'Pakistan', 'Sri Lanka', 'Bangladesh', 'Afghanistan',
    'Ireland', 'Zimbabwe', 'Scotland', 'Netherlands', 'Namibia',
    'UAE', 'Nepal', 'USA', 'Oman', 'Papua New Guinea'
]

# Default minimum balls threshold for player stats
DEFAULT_MIN_BALLS = 100
DEFAULT_TOP_TEAMS = 20

# =============================================================================
# CARD CONFIGURATION
# =============================================================================
# Order determines display sequence. 'initial: True' marks cards for first load.

CARD_CONFIG = [
    {
        "id": "intro",
        "title": "2025 In Hindsight",
        "subtitle": "Your year in T20 cricket",
        "initial": True,
        "method": "get_intro_data"
    },
    {
        "id": "powerplay_bullies",
        "title": "Powerplay Bullies",
        "subtitle": "Highest strike rates in overs 1-6",
        "initial": False,
        "method": "get_powerplay_bullies_data"
    },
    {
        "id": "powerplay_thieves",
        "title": "Powerplay Thieves",
        "subtitle": "Best economy in overs 1-6",
        "initial": False,
        "method": "get_powerplay_thieves_data"
    },
    {
        "id": "middle_merchants",
        "title": "Middle Merchants",
        "subtitle": "Best performers in overs 7-15",
        "initial": False,
        "method": "get_middle_merchants_data"
    },
    {
        "id": "middle_overs_squeeze",
        "title": "Middle Overs Squeeze",
        "subtitle": "Spinners who choked the run flow",
        "initial": False,
        "method": "get_middle_overs_squeeze_data"
    },
    {
        "id": "death_hitters",
        "title": "Death Hitters",
        "subtitle": "Most destructive in overs 16-20",
        "initial": False,
        "method": "get_death_hitters_data"
    },
    {
        "id": "nineteenth_over_gods",
        "title": "Death Over Gods",
        "subtitle": "Who owned the crucial 19th over?",
        "initial": False,
        "method": "get_nineteenth_over_gods_data"
    },
    {
        "id": "needle_movers",
        "title": "Needle Movers",
        "subtitle": "Who moved the predicted score most?",
        "initial": True,
        "method": "get_needle_movers_data"
    },
    {
        "id": "chase_masters",
        "title": "Chase Masters",
        "subtitle": "Who moves win probability in chases?",
        "initial": True,
        "method": "get_chase_masters_data"
    },
    {
        "id": "bowler_type_dominance",
        "title": "Bowler Type Dominance",
        "subtitle": "Which bowling styles ruled?",
        "initial": False,
        "method": "get_bowler_type_dominance_data"
    },
    {
        "id": "pace_vs_spin",
        "title": "Pace vs Spin",
        "subtitle": "Who dominated which bowling type?",
        "initial": True,
        "method": "get_pace_vs_spin_data"
    },
    {
        "id": "controlled_aggression",
        "title": "Controlled Aggression",
        "subtitle": "High strike rate + high control %",
        "initial": False,
        "method": "get_controlled_aggression_data"
    },
    {
        "id": "bowler_handedness",
        "title": "Bowler Handedness",
        "subtitle": "Left arm vs Right arm bowling",
        "initial": False,
        "method": "get_bowler_handedness_data"
    },
    {
        "id": "three_sixty_batters",
        "title": "360° Batters",
        "subtitle": "Most zones hit by batters",
        "initial": False,
        "method": "get_three_sixty_batters_data"
    },
    {
        "id": "rare_shot_specialists",
        "title": "Rare Shot Specialists",
        "subtitle": "Masters of unconventional shots",
        "initial": False,
        "method": "get_rare_shot_specialists_data"
    },
    {
        "id": "length_masters",
        "title": "Length Masters",
        "subtitle": "Bowlers who nail their lengths",
        "initial": False,
        "method": "get_length_masters_data"
    },
    {
        "id": "sweep_evolution",
        "title": "Sweep Evolution",
        "subtitle": "The rise of the sweep shots",
        "initial": False,
        "method": "get_sweep_evolution_data"
    }
]
"""
{
    "id": "venue_vibes",
    "title": "Venue Vibes",
    "subtitle": "How different grounds played",
    "initial": False,
    "method": "get_venue_vibes_data"
},
{
    "id": "elo_movers",
    "title": "ELO Movers",
    "subtitle": "Biggest rating changes",
    "initial": False,
    "method": "get_elo_movers_data"
},
{
    "id": "batter_hand_breakdown",
    "title": "Batter Hand Breakdown",
    "subtitle": "Left vs Right hand performance",
    "initial": False,
    "method": "get_batter_hand_breakdown_data"
},
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_card_order() -> List[str]:
    """Get ordered list of card IDs."""
    return [card["id"] for card in CARD_CONFIG]


def get_initial_card_ids() -> List[str]:
    """Get card IDs marked for initial load."""
    return [card["id"] for card in CARD_CONFIG if card.get("initial", False)]


def get_lazy_card_ids() -> List[str]:
    """Get card IDs for lazy loading (not initial)."""
    return [card["id"] for card in CARD_CONFIG if not card.get("initial", False)]


def get_card_config_by_id(card_id: str) -> dict:
    """Get card configuration by ID."""
    for card in CARD_CONFIG:
        if card["id"] == card_id:
            return card
    return None
