"""
Bowler Types Classification Service

Comprehensive mapping of bowling styles to categories (pace/spin).
Based on analysis of both `players.bowler_type` and `delivery_details.bowl_style`.

Bowling Style Abbreviations:
- R/L: Right/Left arm
- F/M/S: Fast/Medium/Slow
- O: Off-break (off-spin)
- B: Leg-break (leg-spin)
- BG: Googly (leg-spin variation)
- WS: Wrist-spin
- SLA: Slow Left Arm (orthodox left-arm spin)
- AB: ?
- SM: Slow Medium
"""

from typing import Literal, Optional

BowlingCategory = Literal['pace', 'spin', 'unknown']


# Comprehensive mapping based on analysis of both tables
PACE_TYPES = {
    # Fast bowlers
    'RF',    # Right-arm Fast
    'LF',    # Left-arm Fast
    'RFM',   # Right-arm Fast-Medium
    'LFM',   # Left-arm Fast-Medium

    # Medium pace bowlers
    'RM',    # Right-arm Medium
    'LM',    # Left-arm Medium
    'RMF',   # Right-arm Medium-Fast
    'LMF',   # Left-arm Medium-Fast

    # Slow-medium (still pace)
    'LS',    # Left-arm Slow
    'RS',    # Right-arm Slow
    'LSM',   # Left-arm Slow-Medium
    'RSM',   # Right-arm Slow-Medium

    # Combo types with pace as primary
    'RFM/LB',       # Right Fast-Medium who also bowls leg-spin
    'RFM/LBG',      # Right Fast-Medium who also bowls googly
    'RFM/OB',       # Right Fast-Medium who also bowls off-spin
    'RFM/OB/LBG',   # Right Fast-Medium with off-spin and googly
    'RMF/LB',       # Right Medium-Fast who also bowls leg-spin
    'RMF/OB',       # Right Medium-Fast who also bowls off-spin
    'RM/LB',        # Right Medium who also bowls leg-spin
    'RM/LBG',       # Right Medium who also bowls googly variations
    'RM/OB',        # Right Medium who also bowls off-spin
    'RM/OB/LB',     # Right Medium with off-spin and leg-spin
    'RM/RSM',       # Right Medium with slow-medium variations
    'LFM/SLA',      # Left Fast-Medium who also bowls slow left-arm spin
    'LM/SLA/LWS',   # Left Medium with slow left-arm and wrist-spin
    'LMF/RM',       # Left Medium-Fast with right-medium variations
}

SPIN_TYPES = {
    # Off-spin (finger spin, turns away from right-hander for RH bowler)
    'OB',    # Off-Break
    'RO',    # Right-arm Off-break (alternative notation)
    'LO',    # Left-arm Off-break (rare)

    # Leg-spin (wrist spin, turns into right-hander for RH bowler)
    'LB',    # Leg-Break
    'LBG',   # Leg-Break Googly
    'RL',    # Right-arm Leg-spin (alternative notation)

    # Slow left-arm orthodox (finger spin)
    'SLA',   # Slow Left-Arm orthodox

    # Wrist spin
    'LWS',   # Left-arm Wrist-Spin (chinaman)

    # Rare/specialized spin types
    'RAB',   # Right-Arm ?
    'LAB',   # Left-Arm ?
    'LC',    # Left-arm Chinaman (wrist-spin)

    # Combo types with spin as primary
    'OB/LB',        # Off-spinner who also bowls leg-spin
    'OB/LBG',       # Off-spinner with googly
    'OB/SLA',       # Off-spinner with slow left-arm variations
    'SLA/LWS',      # Slow left-arm with wrist-spin
}

# Types that don't fit into pace or spin
UNKNOWN_TYPES = {
    '-',         # No bowling type specified
    'NaN',       # Missing data
    'unknown',   # Explicitly unknown
}


def categorize_bowling_style(bowling_style: Optional[str]) -> BowlingCategory:
    """
    Categorize a bowling style into pace, spin, or unknown.

    Args:
        bowling_style: The bowler type/style (e.g., 'RF', 'OB', 'RFM/LB')

    Returns:
        'pace', 'spin', or 'unknown'

    Examples:
        >>> categorize_bowling_style('RF')
        'pace'
        >>> categorize_bowling_style('OB')
        'spin'
        >>> categorize_bowling_style('RFM/OB')
        'pace'  # Pace with spin variations - primary skill is pace
        >>> categorize_bowling_style('-')
        'unknown'
    """
    if not bowling_style or bowling_style in UNKNOWN_TYPES:
        return 'unknown'

    # Check pace types first (includes combo types where pace is primary)
    if bowling_style in PACE_TYPES:
        return 'pace'

    # Check spin types
    if bowling_style in SPIN_TYPES:
        return 'spin'

    # Unknown type not in our mapping
    return 'unknown'


def get_bowler_category_sql_case() -> str:
    """
    Generate SQL CASE statement for categorizing bowling styles.

    Use this in SQL queries to categorize bowlers without Python.

    Returns:
        SQL CASE statement that returns 'pace', 'spin', or NULL

    Example:
        SELECT
            bowler,
            {get_bowler_category_sql_case()} as bowling_category
        FROM players
    """
    pace_list = "', '".join(sorted(PACE_TYPES))
    spin_list = "', '".join(sorted(SPIN_TYPES))

    return f"""CASE
        WHEN bowler_type IN ('{pace_list}') THEN 'pace'
        WHEN bowler_type IN ('{spin_list}') THEN 'spin'
        ELSE NULL
    END"""


def get_all_pace_types() -> set[str]:
    """Get all known pace bowling types."""
    return PACE_TYPES.copy()


def get_all_spin_types() -> set[str]:
    """Get all known spin bowling types."""
    return SPIN_TYPES.copy()


def get_all_bowling_types() -> dict[str, BowlingCategory]:
    """
    Get mapping of all bowling types to their categories.

    Returns:
        Dictionary mapping bowling type to category
    """
    mapping = {}
    for bt in PACE_TYPES:
        mapping[bt] = 'pace'
    for bt in SPIN_TYPES:
        mapping[bt] = 'spin'
    for bt in UNKNOWN_TYPES:
        mapping[bt] = 'unknown'
    return mapping


# Pre-generated SQL for convenience
BOWLER_CATEGORY_SQL = f"""CASE
    WHEN bowler_type IN ('{"', '".join(sorted(PACE_TYPES))}') THEN 'pace'
    WHEN bowler_type IN ('{"', '".join(sorted(SPIN_TYPES))}') THEN 'spin'
    ELSE NULL
END"""

# Alternative for delivery_details which uses bowl_style instead of bowler_type
BOWL_STYLE_CATEGORY_SQL = f"""CASE
    WHEN bowl_style IN ('{"', '".join(sorted(PACE_TYPES))}') THEN 'pace'
    WHEN bowl_style IN ('{"', '".join(sorted(SPIN_TYPES))}') THEN 'spin'
    ELSE NULL
END"""
