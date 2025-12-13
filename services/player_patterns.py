"""
Player Pattern Detection Service (MVP)
======================================
Extracts meaningful patterns from raw player statistics using simplified rule-based logic.

This is a simplified MVP version focusing on batters only with streamlined pattern detection.
"""

from typing import Dict, List, Any, Optional
import logging

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
