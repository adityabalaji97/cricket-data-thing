"""
Player Pattern Detection Service (MVP)
======================================
Extracts meaningful patterns from raw player statistics using simplified rule-based logic.

This is a simplified MVP version focusing on batters only with streamlined pattern detection.
"""

from typing import Dict, List, Any, Optional
import logging
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is 0"""
    if denominator == 0:
        return default
    return round(numerator / denominator, 2)


def _get_bowling_type_name(code: str) -> str:
    """Convert bowling type code to readable name."""
    mapping = {
        "RF": "right-arm fast",
        "RFM": "right-arm fast-medium",
        "RM": "right-arm medium",
        "LF": "left-arm fast",
        "LFM": "left-arm fast-medium",
        "LM": "left-arm medium",
        "RO": "off-spin",
        "RL": "leg-spin",
        "LO": "left-arm orthodox",
        "LC": "left-arm chinaman"
    }
    return mapping.get(code, code)


# =============================================================================
# BATTER PATTERN DETECTION
# =============================================================================

def detect_batter_patterns(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract patterns from batter statistics (simplified MVP version).
    
    Args:
        stats: Raw stats from /player/{name}/stats endpoint
        
    Returns:
        Structured pattern data for LLM synthesis
    """
    try:
        overall = stats.get("overall", {})
        phase_stats = stats.get("phase_stats", {}).get("overall", {})
        pace_stats = stats.get("phase_stats", {}).get("pace", {})
        spin_stats = stats.get("phase_stats", {}).get("spin", {})
        bowling_types = stats.get("phase_stats", {}).get("bowling_types", {})
        innings = stats.get("innings", [])
        
        # Basic pattern structure
        patterns = {
            "player_name": stats.get("player_name", "Unknown"),
            "matches": overall.get("matches", 0),
            "total_runs": overall.get("runs", 0),
            "overall_average": overall.get("average", 0),
            "overall_strike_rate": overall.get("strike_rate", 0),
            "overall_dot_percentage": overall.get("dot_percentage", 0),
            "overall_boundary_percentage": overall.get("boundary_percentage", 0),
        }
        
        # Detect primary phase
        patterns["phase_distribution"] = _calculate_phase_distribution(phase_stats)
        patterns["primary_phase"] = _detect_primary_phase(patterns["phase_distribution"])
        
        # Detect batting style
        patterns["style_classification"], patterns["style_evidence"] = _classify_batting_style(
            overall, phase_stats
        )
        
        # Detect strengths (top 2 for MVP)
        patterns["strengths"] = _detect_batter_strengths(
            phase_stats, pace_stats, spin_stats, bowling_types
        )
        
        # Detect weaknesses (top 1 for MVP)
        patterns["weaknesses"] = _detect_batter_weaknesses(
            phase_stats, pace_stats, spin_stats, bowling_types
        )
        
        # Entry pattern
        patterns.update(_analyze_entry_pattern(innings))
        
        # Pace vs Spin preference
        patterns.update(_analyze_pace_spin_preference(pace_stats, spin_stats))
        
        logger.info(f"Successfully detected patterns for {patterns['player_name']}")
        return patterns
        
    except Exception as e:
        logger.error(f"Error detecting batter patterns: {str(e)}", exc_info=True)
        raise


def _calculate_phase_distribution(phase_stats: Dict) -> Dict[str, float]:
    """Calculate percentage of balls faced in each phase."""
    pp_balls = phase_stats.get("powerplay", {}).get("balls", 0)
    mid_balls = phase_stats.get("middle", {}).get("balls", 0)
    death_balls = phase_stats.get("death", {}).get("balls", 0)
    
    total = pp_balls + mid_balls + death_balls
    if total == 0:
        return {"powerplay": 33.3, "middle": 33.3, "death": 33.3}
    
    return {
        "powerplay": round((pp_balls / total) * 100, 1),
        "middle": round((mid_balls / total) * 100, 1),
        "death": round((death_balls / total) * 100, 1)
    }


def _detect_primary_phase(distribution: Dict[str, float]) -> str:
    """Determine player's primary batting phase (simplified)."""
    max_phase = max(distribution, key=distribution.get)
    max_pct = distribution[max_phase]
    
    # Simplified: If any phase > 42%, they're a specialist
    if max_pct > 42:
        return max_phase
    else:
        return "balanced"


def _classify_batting_style(overall: Dict, phase_stats: Dict) -> tuple:
    """
    Classify batting style based on key metrics (simplified for MVP).
    
    Returns:
        tuple: (style_classification, list of evidence points)
    """
    sr = overall.get("strike_rate", 0)
    avg = overall.get("average", 0)
    dot_pct = overall.get("dot_percentage", 0)
    boundary_pct = overall.get("boundary_percentage", 0)
    
    evidence = []
    
    # Simplified classification with 4 categories
    
    # Aggressor: High SR (135+) and high boundaries (14%+)
    if sr >= 135 and boundary_pct >= 14:
        evidence.append(f"High strike rate ({sr:.0f})")
        evidence.append(f"Frequent boundaries ({boundary_pct:.1f}%)")
        return "aggressor", evidence
    
    # Anchor: Good average (28+), moderate SR, rotates strike well
    if avg >= 28 and 115 <= sr < 135 and dot_pct < 40:
        evidence.append(f"Reliable average ({avg:.1f})")
        evidence.append(f"Rotates strike well ({dot_pct:.1f}% dots)")
        return "anchor", evidence
    
    # Finisher: Strong in death overs
    death_sr = phase_stats.get("death", {}).get("strike_rate", 0)
    if death_sr >= 145:
        evidence.append(f"Explosive in death overs (SR {death_sr:.0f})")
        return "finisher", evidence
    
    # Accumulator: High average, conservative approach
    if avg >= 25 and sr < 120:
        evidence.append(f"Consistent scorer (Avg {avg:.1f})")
        return "accumulator", evidence
    
    # Default: Balanced
    return "balanced", ["Versatile batting approach"]


def _detect_batter_strengths(
    phase_stats: Dict, 
    pace_stats: Dict, 
    spin_stats: Dict,
    bowling_types: Dict
) -> List[Dict]:
    """
    Detect up to 2 key strengths (simplified for MVP).
    
    Criteria for strength:
    - SR >= 140 OR Avg >= 35 in a specific context
    - Minimum 25 balls sample size (reduced from 30)
    """
    strengths = []
    
    # Check phase-wise strengths
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = phase_stats.get(phase_name, {})
        balls = phase_data.get("balls", 0)
        
        if balls >= 25:
            sr = phase_data.get("strike_rate", 0)
            avg = phase_data.get("average", 0)
            
            if sr >= 140 or avg >= 35:
                strengths.append({
                    "context": f"in {phase_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": balls,
                    "strength_score": (sr / 130) + (avg / 30)  # Combined score for sorting
                })
    
    # Check vs pace (any phase)
    pace_overall = pace_stats.get("overall", {})
    pace_balls = pace_overall.get("balls", 0)
    if pace_balls >= 40:
        sr = pace_overall.get("strike_rate", 0)
        avg = pace_overall.get("average", 0)
        
        if sr >= 145 or avg >= 40:
            strengths.append({
                "context": "vs pace",
                "strike_rate": sr,
                "average": avg,
                "balls": pace_balls,
                "strength_score": (sr / 130) + (avg / 30)
            })
    
    # Check vs spin (any phase)
    spin_overall = spin_stats.get("overall", {})
    spin_balls = spin_overall.get("balls", 0)
    if spin_balls >= 40:
        sr = spin_overall.get("strike_rate", 0)
        avg = spin_overall.get("average", 0)
        
        if sr >= 135 or avg >= 38:
            strengths.append({
                "context": "vs spin",
                "strike_rate": sr,
                "average": avg,
                "balls": spin_balls,
                "strength_score": (sr / 130) + (avg / 30)
            })
    
    # Check specific bowling types (only if really dominant)
    for bowl_type, type_stats in bowling_types.items():
        overall_type = type_stats.get("overall", {})
        balls = overall_type.get("balls", 0)
        
        if balls >= 50:
            sr = overall_type.get("strike_rate", 0)
            avg = overall_type.get("average", 0)
            
            # Higher threshold for specific bowling types
            if sr >= 155 or avg >= 45:
                bowl_type_name = _get_bowling_type_name(bowl_type)
                strengths.append({
                    "context": f"vs {bowl_type_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": balls,
                    "strength_score": (sr / 130) + (avg / 30)
                })
    
    # Sort by strength score and return top 2
    strengths.sort(key=lambda x: x.get("strength_score", 0), reverse=True)
    return strengths[:2]


def _detect_batter_weaknesses(
    phase_stats: Dict,
    pace_stats: Dict,
    spin_stats: Dict,
    bowling_types: Dict
) -> List[Dict]:
    """
    Detect top 1 key weakness (simplified for MVP).
    
    Criteria for weakness:
    - SR <= 110 OR Avg <= 20 in a specific context
    - Minimum 20 balls sample size
    """
    weaknesses = []
    
    # Check specific bowling types for weaknesses
    for bowl_type, type_stats in bowling_types.items():
        overall_type = type_stats.get("overall", {})
        balls = overall_type.get("balls", 0)
        
        if balls >= 20:
            sr = overall_type.get("strike_rate", 0)
            avg = overall_type.get("average", 0)
            
            # Weakness: Low SR or low average
            if sr <= 110 or (avg > 0 and avg <= 20):
                bowl_type_name = _get_bowling_type_name(bowl_type)
                
                # Calculate weakness severity
                weakness_score = 0
                if sr > 0:
                    weakness_score += max(0, (110 - sr) / 30)
                if avg > 0:
                    weakness_score += max(0, (20 - avg) / 10)
                
                weaknesses.append({
                    "context": f"vs {bowl_type_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": balls,
                    "weakness_score": weakness_score
                })
    
    # Check phase-wise weaknesses vs spin
    for phase_name in ["powerplay", "middle", "death"]:
        spin_phase = spin_stats.get(phase_name, {})
        balls = spin_phase.get("balls", 0)
        
        if balls >= 20:
            sr = spin_phase.get("strike_rate", 0)
            avg = spin_phase.get("average", 0)
            
            if sr <= 105 or (avg > 0 and avg <= 18):
                weakness_score = 0
                if sr > 0:
                    weakness_score += max(0, (105 - sr) / 30)
                if avg > 0:
                    weakness_score += max(0, (18 - avg) / 10)
                
                weaknesses.append({
                    "context": f"vs spin in {phase_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": balls,
                    "weakness_score": weakness_score
                })
    
    # Sort by severity and return top 1
    weaknesses.sort(key=lambda x: x.get("weakness_score", 0), reverse=True)
    return weaknesses[:1]


def _analyze_entry_pattern(innings: List[Dict]) -> Dict:
    """Analyze when the batter typically comes in to bat."""
    if not innings:
        return {
            "typical_batting_position": None,
            "entry_pattern": "unknown",
            "avg_entry_over": None
        }
    
    positions = []
    entry_overs = []
    
    for inning in innings:
        pos = inning.get("batting_position")
        if pos:
            positions.append(pos)
        
        entry = inning.get("entry_point", {})
        entry_over = entry.get("overs")
        if entry_over is not None:
            entry_overs.append(float(entry_over))
    
    # Calculate mode of batting position (most common)
    if positions:
        from collections import Counter
        position_counts = Counter(positions)
        typical_position = position_counts.most_common(1)[0][0]
    else:
        typical_position = None
    
    # Calculate average entry over
    avg_entry = sum(entry_overs) / len(entry_overs) if entry_overs else None
    
    # Classify entry pattern
    if avg_entry is not None:
        if avg_entry <= 3:
            entry_pattern = "early"
        elif avg_entry <= 10:
            entry_pattern = "middle"
        else:
            entry_pattern = "late"
    else:
        entry_pattern = "unknown"
    
    return {
        "typical_batting_position": typical_position,
        "entry_pattern": entry_pattern,
        "avg_entry_over": round(avg_entry, 1) if avg_entry else None
    }


def _analyze_pace_spin_preference(pace_stats: Dict, spin_stats: Dict) -> Dict:
    """Determine if batter prefers pace or spin."""
    pace_overall = pace_stats.get("overall", {})
    spin_overall = spin_stats.get("overall", {})
    
    pace_sr = pace_overall.get("strike_rate", 0)
    pace_avg = pace_overall.get("average", 0)
    spin_sr = spin_overall.get("strike_rate", 0)
    spin_avg = spin_overall.get("average", 0)
    
    # Calculate preference score (weighted SR + Avg)
    pace_score = (pace_sr / 100) + (pace_avg / 25) if pace_sr > 0 else 0
    spin_score = (spin_sr / 100) + (spin_avg / 25) if spin_sr > 0 else 0
    
    if pace_score > spin_score * 1.15:
        preference = "pace"
    elif spin_score > pace_score * 1.15:
        preference = "spin"
    else:
        preference = "balanced"
    
    return {
        "pace_sr": pace_sr,
        "pace_avg": pace_avg,
        "spin_sr": spin_sr,
        "spin_avg": spin_avg,
        "preferred_bowling_type": preference
    }


# =============================================================================
# BOWLER PATTERN DETECTION
# =============================================================================

def detect_bowler_patterns(stats: Dict[str, Any], db=None, filters: dict = None) -> Dict[str, Any]:
    """
    Extract patterns from bowler statistics.
    
    Args:
        stats: Raw stats from /player/{name}/bowling_stats endpoint
        db: Database session (optional, for crease_combo queries)
        filters: Filter dict with start_date, end_date, leagues etc.
        
    Returns:
        Structured pattern data for LLM synthesis
    """
    try:
        overall = stats.get("overall", {})
        phase_stats = stats.get("phase_stats", {})
        over_stats = stats.get("over_distribution", [])  # Key is "over_distribution" from bowling_stats endpoint
        innings = stats.get("innings", [])
        
        patterns = {
            "player_name": stats.get("player_name", "Unknown"),
            "matches": overall.get("matches", 0),
            "total_wickets": overall.get("wickets", 0),
            "total_overs": overall.get("overs", 0),
            "overall_economy": overall.get("economy", 0),
            "overall_average": overall.get("average", 0),
            "overall_strike_rate": overall.get("strike_rate", 0),
            "overall_dot_percentage": overall.get("dot_percentage", 0),
        }
        
        # Detect primary phase
        patterns["phase_distribution"] = _calculate_bowling_phase_distribution(phase_stats)
        patterns["primary_phase"] = _detect_bowling_primary_phase(patterns["phase_distribution"])
        
        # Detect bowling profile
        patterns["profile_classification"], patterns["profile_evidence"] = _classify_bowling_profile(overall)
        
        # Detect strengths
        patterns["strengths"] = _detect_bowler_strengths(phase_stats)
        
        # Detect weaknesses  
        patterns["weaknesses"] = _detect_bowler_weaknesses(phase_stats)
        
        # Analyze over usage pattern
        patterns.update(_analyze_over_usage(over_stats, overall))
        
        # Consistency analysis
        patterns.update(_analyze_bowling_consistency(innings))
        
        # Crease combo analysis (if db available)
        if db and filters:
            player_name = patterns.get("player_name", "")
            crease_combo_stats = get_bowler_crease_combo_stats(player_name, filters, db)
            ball_direction_stats = get_bowler_ball_direction_stats(player_name, filters, db)
            
            patterns["crease_combo_stats"] = crease_combo_stats
            patterns["ball_direction_stats"] = ball_direction_stats
            patterns["best_crease_combo"] = _find_best_crease_combo(crease_combo_stats)
            patterns["worst_crease_combo"] = _find_worst_crease_combo(crease_combo_stats)
        else:
            patterns["crease_combo_stats"] = {}
            patterns["ball_direction_stats"] = {}
            patterns["best_crease_combo"] = None
            patterns["worst_crease_combo"] = None
        
        logger.info(f"Successfully detected bowler patterns for {patterns['player_name']}")
        return patterns
        
    except Exception as e:
        logger.error(f"Error detecting bowler patterns: {str(e)}", exc_info=True)
        raise


def _calculate_bowling_phase_distribution(phase_stats: Dict) -> Dict[str, Dict]:
    """
    Calculate comprehensive phase distribution including:
    - % of overs in each phase
    - % of wickets in each phase
    - Economy per phase
    - Strike rate per phase
    - Dot percentage per phase
    
    Args:
        phase_stats: Dict with powerplay/middle/death phase data
        
    Returns:
        Dict with detailed stats for each phase
    """
    # Calculate totals first
    total_overs = sum(
        phase_stats.get(p, {}).get("overs", 0) 
        for p in ["powerplay", "middle", "death"]
    )
    total_wickets = sum(
        phase_stats.get(p, {}).get("wickets", 0) 
        for p in ["powerplay", "middle", "death"]
    )
    
    if total_overs == 0:
        return {
            "powerplay": {"overs_percentage": 33.3, "wickets_percentage": 33.3, "economy": 0, "strike_rate": 999, "overs": 0, "wickets": 0, "dot_percentage": 0},
            "middle": {"overs_percentage": 33.3, "wickets_percentage": 33.3, "economy": 0, "strike_rate": 999, "overs": 0, "wickets": 0, "dot_percentage": 0},
            "death": {"overs_percentage": 33.3, "wickets_percentage": 33.3, "economy": 0, "strike_rate": 999, "overs": 0, "wickets": 0, "dot_percentage": 0}
        }
    
    result = {}
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = phase_stats.get(phase_name, {})
        overs = phase_data.get("overs", 0)
        wickets = phase_data.get("wickets", 0)
        runs = phase_data.get("runs", 0)
        balls = phase_data.get("balls", int(overs * 6)) if overs > 0 else 0
        dots = phase_data.get("dots", 0)
        
        result[phase_name] = {
            "overs_percentage": round((overs / total_overs * 100), 1) if total_overs > 0 else 0,
            "wickets_percentage": round((wickets / total_wickets * 100), 1) if total_wickets > 0 else 0,
            "economy": round((runs * 6 / balls), 2) if balls > 0 else 0,
            "strike_rate": round(balls / wickets, 1) if wickets > 0 else 999,
            "dot_percentage": round((dots * 100 / balls), 1) if balls > 0 else 0,
            "wickets": wickets,
            "overs": overs
        }
    
    return result


def _detect_bowling_primary_phase(distribution: Dict[str, Dict]) -> str:
    """Determine bowler's primary phase based on overs percentage."""
    # Extract overs_percentage from each phase
    phase_pcts = {}
    for phase, data in distribution.items():
        if isinstance(data, dict):
            phase_pcts[phase] = data.get("overs_percentage", 0)
        else:
            # Fallback for old format
            phase_pcts[phase] = data
    
    if not phase_pcts:
        return "workhorse"
    
    max_phase = max(phase_pcts, key=phase_pcts.get)
    max_pct = phase_pcts[max_phase]
    
    if max_pct > 50:
        return f"{max_phase}_specialist"
    elif max_pct > 40:
        return max_phase
    else:
        return "workhorse"


def _classify_bowling_profile(overall: Dict) -> tuple:
    """Classify bowling profile based on key metrics."""
    economy = overall.get("economy", 0)
    sr = overall.get("strike_rate", 0)
    dot_pct = overall.get("dot_percentage", 0)
    
    evidence = []
    
    # Wicket taker: Low SR (<18)
    if sr > 0 and sr <= 18:
        evidence.append(f"Excellent strike rate ({sr:.1f})")
        return "wicket_taker", evidence
    
    # Economical: Low economy (<7.5), high dots
    if economy > 0 and economy <= 7.5 and dot_pct >= 40:
        evidence.append(f"Miserly economy ({economy:.2f})")
        evidence.append(f"High dot percentage ({dot_pct:.1f}%)")
        return "economical", evidence
    
    # Restrictive: High dots
    if dot_pct >= 45:
        evidence.append(f"Builds pressure ({dot_pct:.1f}% dots)")
        return "restrictive", evidence
    
    # Balanced
    if economy > 0 and economy <= 8.5 and sr > 0 and sr <= 24:
        evidence.append(f"Balanced profile (Econ: {economy:.2f}, SR: {sr:.1f})")
        return "balanced", evidence
    
    return "impact", ["Capable of match-winning spells"]


def _detect_bowler_strengths(phase_stats: Dict) -> List[Dict]:
    """Detect bowler strengths by phase."""
    strengths = []
    
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = phase_stats.get(phase_name, {})
        overs = phase_data.get("overs", 0)
        
        if overs >= 8:
            economy = phase_data.get("economy", 0)
            sr = phase_data.get("strike_rate", 0)
            wickets = phase_data.get("wickets", 0)
            
            # Strong in phase: Low economy or good SR
            if (economy > 0 and economy <= 7.5) or (sr > 0 and sr <= 16):
                strength_score = 0
                if economy > 0:
                    strength_score += max(0, (8.5 - economy) / 2)
                if sr > 0:
                    strength_score += max(0, (20 - sr) / 5)
                
                strengths.append({
                    "context": f"in {phase_name}",
                    "economy": economy,
                    "strike_rate": sr,
                    "wickets": wickets,
                    "overs": overs,
                    "strength_score": strength_score
                })
    
    strengths.sort(key=lambda x: x.get("strength_score", 0), reverse=True)
    return strengths[:2]


def _detect_bowler_weaknesses(phase_stats: Dict) -> List[Dict]:
    """Detect bowler weaknesses by phase."""
    weaknesses = []
    
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = phase_stats.get(phase_name, {})
        overs = phase_data.get("overs", 0)
        
        if overs >= 5:
            economy = phase_data.get("economy", 0)
            
            if economy >= 9.5:
                weaknesses.append({
                    "context": f"in {phase_name}",
                    "economy": economy,
                    "overs": overs,
                    "weakness_score": economy
                })
    
    weaknesses.sort(key=lambda x: x.get("weakness_score", 0), reverse=True)
    return weaknesses[:1]


def _analyze_over_usage(over_stats: List[Dict], overall: Dict) -> Dict:
    """
    Analyze which overs the bowler typically bowls.
    
    Args:
        over_stats: List of dicts from bowling_stats endpoint
            Each dict has: over_number, instances_bowled/times_bowled, matches_percentage, etc.
        overall: Overall stats dict with matches count
        
    Returns:
        Dict with typical_overs, overs_per_match, usage_pattern, primary_over info
    """
    if not over_stats:
        return {
            "typical_overs": [],
            "overs_per_match": 0,
            "usage_pattern": "unknown",
            "primary_over": None,
            "primary_over_percentage": 0
        }
    
    matches = overall.get("matches", 1)
    total_overs = overall.get("overs", 0)
    overs_per_match = round(total_overs / matches, 1) if matches > 0 else 0
    
    # Sort by frequency (handle both field names: instances_bowled or times_bowled)
    sorted_overs = sorted(
        over_stats, 
        key=lambda x: x.get("instances_bowled", x.get("times_bowled", 0)), 
        reverse=True
    )
    
    # Get top 4 most frequently bowled overs with details
    typical_overs = []
    for over_data in sorted_overs[:4]:
        over_num = over_data.get("over_number", 0)
        display_over = over_num + 1  # Convert to 1-indexed for display
        frequency = over_data.get("instances_bowled", over_data.get("times_bowled", 0))
        
        # Calculate percentage if not provided
        percentage = over_data.get("matches_percentage", 0)
        if percentage == 0 and matches > 0 and frequency > 0:
            percentage = round((frequency / matches) * 100, 1)
        
        typical_overs.append({
            "over": display_over,
            "frequency": frequency,
            "percentage": round(percentage, 1)
        })
    
    # Determine primary over (most frequently bowled)
    primary_over = typical_overs[0] if typical_overs else None
    
    # Determine usage pattern based on typical overs
    if typical_overs:
        over_numbers = [o["over"] for o in typical_overs]
        avg_over = sum(over_numbers) / len(over_numbers)
        
        if avg_over <= 6:
            usage_pattern = "powerplay_specialist"
        elif avg_over >= 17:
            usage_pattern = "death_specialist"
        elif all(6 < o <= 15 for o in over_numbers):
            usage_pattern = "middle_overs"
        else:
            usage_pattern = "flexible"
    else:
        usage_pattern = "unknown"
    
    return {
        "typical_overs": typical_overs,
        "overs_per_match": overs_per_match,
        "usage_pattern": usage_pattern,
        "primary_over": primary_over["over"] if primary_over else None,
        "primary_over_percentage": primary_over["percentage"] if primary_over else 0
    }


def _analyze_bowling_consistency(innings: List[Dict]) -> Dict:
    """Analyze bowling consistency."""
    if not innings:
        return {
            "consistency_rating": "unknown",
            "wicket_hauls_percentage": 0
        }
    
    wicket_list = [i.get("wickets", 0) for i in innings]
    total_innings = len(wicket_list)
    
    # 2+ wicket hauls percentage
    two_plus = sum(1 for w in wicket_list if w >= 2)
    two_plus_pct = round((two_plus / total_innings * 100), 1) if total_innings > 0 else 0
    
    # Consistency based on variance
    if total_innings > 1:
        avg_wickets = sum(wicket_list) / total_innings
        if avg_wickets > 0:
            variance = sum((w - avg_wickets) ** 2 for w in wicket_list) / total_innings
            cv = (variance ** 0.5) / avg_wickets
            
            if cv < 0.8:
                consistency = "high"
            elif cv < 1.2:
                consistency = "medium"
            else:
                consistency = "low"
        else:
            consistency = "low"
    else:
        consistency = "unknown"
    
    return {
        "consistency_rating": consistency,
        "wicket_hauls_percentage": two_plus_pct
    }


# =============================================================================
# BOWLER MATCHUP ANALYSIS (Crease Combo & Ball Direction)
# =============================================================================

def get_bowler_crease_combo_stats(player_name: str, filters: dict, db) -> Dict[str, Any]:
    """
    Query deliveries table to get bowler performance vs different crease combinations.
    
    Args:
        player_name: The bowler's name
        filters: Dict containing start_date, end_date, leagues, venue, etc.
        db: Database session
        
    Returns:
        Dict with stats for each crease combo (Right-Right, Right-Left, Left-Right, Left-Left)
    """
    if not db:
        return {}
    
    try:
        # Build filter conditions
        conditions = ["d.bowler = :player_name", "d.crease_combo IS NOT NULL"]
        params = {"player_name": player_name}
        
        if filters.get("start_date"):
            conditions.append("m.date >= :start_date")
            params["start_date"] = filters["start_date"]
        
        if filters.get("end_date"):
            conditions.append("m.date <= :end_date")
            params["end_date"] = filters["end_date"]
        
        if filters.get("venue"):
            conditions.append("m.venue = :venue")
            params["venue"] = filters["venue"]
        
        if filters.get("leagues") and len(filters["leagues"]) > 0:
            conditions.append("m.competition = ANY(:leagues)")
            params["leagues"] = filters["leagues"]
        
        where_clause = " AND ".join(conditions)
        
        query = text(f"""
            SELECT 
                d.crease_combo,
                COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) as legal_balls,
                SUM(d.runs_off_bat + d.extras) as runs,
                SUM(CASE WHEN d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out') 
                THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE {where_clause}
            GROUP BY d.crease_combo
            HAVING COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) >= 30
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        
        crease_stats = {}
        for row in rows:
            balls = row.legal_balls or 0
            runs = row.runs or 0
            wickets = row.wickets or 0
            dots = row.dots or 0
            
            if balls > 0:
                crease_stats[row.crease_combo] = {
                    "balls": balls,
                    "runs": runs,
                    "wickets": wickets,
                    "dots": dots,
                    "economy": round((runs * 6 / balls), 2),
                    "strike_rate": round(balls / wickets, 1) if wickets > 0 else 999,
                    "dot_percentage": round((dots * 100 / balls), 1)
                }
        
        logger.info(f"Got crease combo stats for {player_name}: {list(crease_stats.keys())}")
        return crease_stats
        
    except Exception as e:
        logger.error(f"Error getting crease combo stats for {player_name}: {str(e)}")
        return {}


def get_bowler_ball_direction_stats(player_name: str, filters: dict, db) -> Dict[str, Any]:
    """
    Query deliveries table to get bowler performance by ball direction.
    
    Ball direction is calculated based on bowler type + striker handedness:
    - intoBatter: Ball moving towards the striker (e.g., off-spinner to RHB)
    - awayFromBatter: Ball moving away from the striker (e.g., off-spinner to LHB)
    
    Args:
        player_name: The bowler's name
        filters: Dict containing start_date, end_date, leagues, venue, etc.
        db: Database session
        
    Returns:
        Dict with stats for each ball direction
    """
    if not db:
        return {}
    
    try:
        # Build filter conditions
        conditions = ["d.bowler = :player_name", "d.ball_direction IS NOT NULL"]
        params = {"player_name": player_name}
        
        if filters.get("start_date"):
            conditions.append("m.date >= :start_date")
            params["start_date"] = filters["start_date"]
        
        if filters.get("end_date"):
            conditions.append("m.date <= :end_date")
            params["end_date"] = filters["end_date"]
        
        if filters.get("venue"):
            conditions.append("m.venue = :venue")
            params["venue"] = filters["venue"]
        
        if filters.get("leagues") and len(filters["leagues"]) > 0:
            conditions.append("m.competition = ANY(:leagues)")
            params["leagues"] = filters["leagues"]
        
        where_clause = " AND ".join(conditions)
        
        query = text(f"""
            SELECT 
                d.ball_direction,
                COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) as legal_balls,
                SUM(d.runs_off_bat + d.extras) as runs,
                SUM(CASE WHEN d.wicket_type IS NOT NULL 
                    AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out') 
                THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN d.runs_off_bat = 0 AND d.extras = 0 THEN 1 ELSE 0 END) as dots
            FROM deliveries d
            JOIN matches m ON d.match_id = m.id
            WHERE {where_clause}
            GROUP BY d.ball_direction
            HAVING COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) >= 50
        """)
        
        result = db.execute(query, params)
        rows = result.fetchall()
        
        direction_stats = {}
        for row in rows:
            balls = row.legal_balls or 0
            runs = row.runs or 0
            wickets = row.wickets or 0
            dots = row.dots or 0
            
            if balls > 0:
                direction_stats[row.ball_direction] = {
                    "balls": balls,
                    "runs": runs,
                    "wickets": wickets,
                    "dots": dots,
                    "economy": round((runs * 6 / balls), 2),
                    "strike_rate": round(balls / wickets, 1) if wickets > 0 else 999,
                    "dot_percentage": round((dots * 100 / balls), 1)
                }
        
        logger.info(f"Got ball direction stats for {player_name}: {list(direction_stats.keys())}")
        return direction_stats
        
    except Exception as e:
        logger.error(f"Error getting ball direction stats for {player_name}: {str(e)}")
        return {}


def _find_best_crease_combo(crease_stats: Dict) -> Optional[Dict]:
    """
    Find the crease combination where the bowler performs best.
    
    "Best" = lowest economy rate with minimum 30 balls sample
    
    Args:
        crease_stats: Dict from get_bowler_crease_combo_stats()
        
    Returns:
        Dict with combo name and stats, or None if no data
    """
    if not crease_stats:
        return None
    
    best = None
    best_economy = float('inf')
    
    for combo, stats in crease_stats.items():
        if stats.get("balls", 0) >= 30:
            economy = stats.get("economy", float('inf'))
            if economy < best_economy:
                best_economy = economy
                best = {
                    "combo": combo,
                    "economy": economy,
                    "strike_rate": stats.get("strike_rate", 0),
                    "dot_percentage": stats.get("dot_percentage", 0),
                    "balls": stats.get("balls", 0),
                    "wickets": stats.get("wickets", 0)
                }
    
    return best


def _find_worst_crease_combo(crease_stats: Dict) -> Optional[Dict]:
    """
    Find the crease combination where the bowler struggles.
    
    "Worst" = highest economy rate with minimum 30 balls sample
    
    Args:
        crease_stats: Dict from get_bowler_crease_combo_stats()
        
    Returns:
        Dict with combo name and stats, or None if no data
    """
    if not crease_stats:
        return None
    
    worst = None
    worst_economy = 0
    
    for combo, stats in crease_stats.items():
        if stats.get("balls", 0) >= 30:
            economy = stats.get("economy", 0)
            if economy > worst_economy:
                worst_economy = economy
                worst = {
                    "combo": combo,
                    "economy": economy,
                    "strike_rate": stats.get("strike_rate", 0),
                    "dot_percentage": stats.get("dot_percentage", 0),
                    "balls": stats.get("balls", 0),
                    "wickets": stats.get("wickets", 0)
                }
    
    return worst
