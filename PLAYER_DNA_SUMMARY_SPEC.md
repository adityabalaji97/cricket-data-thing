# LLM-Driven Player Summary ("Player DNA") - Implementation Spec

> **Goal**: Generate insightful, narrative summaries of player performance patterns that go beyond raw statistics to tell a story about how a player plays.
>
> **Example Output**:
> ```
> 📊 Player DNA: Virat Kohli
> 
> Primary Role: Middle-overs anchor who accelerates in death
> Batting Style: Calculated aggressor (SR 138) who rotates strike well (only 28% dots)
> Sweet Spot: Against pace in powerplay (SR 152, Avg 48) - exceptional against RF/RFM
> Vulnerability: Left-arm orthodox in middle overs (SR 108, dismissed 2.3x more often)
> Entry Pattern: Typically bats at #3, enters within first 3 overs in 68% of innings
> ```
>
> **Estimated Effort**: 3-4 days  
> **Monetization Potential**: High (differentiating feature, insight layer)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Extraction Schema](#2-data-extraction-schema)
3. [Pattern Detection Rules](#3-pattern-detection-rules)
4. [LLM Prompt Design](#4-llm-prompt-design)
5. [Backend Implementation](#5-backend-implementation)
6. [Frontend Component](#6-frontend-component)
7. [Caching Strategy](#7-caching-strategy)
8. [Cost Analysis](#8-cost-analysis)
9. [Testing Strategy](#9-testing-strategy)

---

## 1. Architecture Overview

### 1.1 Design Philosophy

The key insight is that **most intelligence comes from rule-based pattern detection**, with the LLM providing **natural language synthesis**. This approach:

- **Reduces cost**: LLM only synthesizes pre-computed insights
- **Improves accuracy**: Rule-based detection is deterministic
- **Enables caching**: Same patterns = same summary
- **Maintains consistency**: No hallucination of stats

### 1.2 System Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Existing API   │     │ Pattern Detector│     │   LLM Service   │     │    Frontend     │
│                 │     │                 │     │                 │     │                 │
│ /player/stats   │────▶│ Extract key     │────▶│ Synthesize      │────▶│ Display DNA     │
│ /player/bowling │     │ patterns into   │     │ patterns into   │     │ summary card    │
│                 │     │ structured JSON │     │ natural prose   │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
         │                      │                       │
         │                      ▼                       │
         │              ┌─────────────────┐             │
         │              │ Pattern Schema  │             │
         │              │ {               │             │
         │              │   role: "...",  │             │
         │              │   strengths: [],│             │
         │              │   weaknesses: []│             │
         │              │ }               │             │
         │              └─────────────────┘             │
         │                                              │
         └──────────────────────────────────────────────┘
                    (Cache layer for repeat queries)
```

### 1.3 Key Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| Pattern Detector | Extract insights from raw stats | Python (rule-based) |
| LLM Synthesizer | Convert patterns to prose | OpenAI GPT-4o-mini |
| Summary Cache | Store generated summaries | Redis/In-memory |
| Frontend Card | Display DNA summary | React Component |

---

## 2. Data Extraction Schema

### 2.1 Batter Pattern Schema

This is the structured data we extract from the existing `/player/{name}/stats` endpoint before sending to the LLM.

```python
@dataclass
class BatterPatternData:
    """Structured pattern data extracted from batter statistics."""
    
    # Identity
    player_name: str
    matches: int
    total_runs: int
    
    # Overall Profile
    overall_average: float
    overall_strike_rate: float
    overall_dot_percentage: float
    overall_boundary_percentage: float
    
    # Role Classification
    primary_phase: str  # "powerplay" | "middle" | "death" | "balanced"
    phase_distribution: Dict[str, float]  # % of balls faced in each phase
    
    # Batting Style
    style_classification: str  # "anchor" | "aggressor" | "accumulator" | "finisher"
    style_evidence: List[str]  # Supporting data points
    
    # Strengths (up to 3)
    strengths: List[Dict[str, Any]]
    # Example: {"context": "vs pace in powerplay", "sr": 152, "avg": 48, "balls": 245}
    
    # Weaknesses (up to 2)
    weaknesses: List[Dict[str, Any]]
    # Example: {"context": "vs LO in middle", "sr": 98, "dismissal_rate": 2.3}
    
    # Entry Pattern
    typical_batting_position: int
    entry_pattern: str  # "early" | "middle" | "late" | "flexible"
    avg_entry_over: float
    
    # Consistency
    consistency_rating: str  # "high" | "medium" | "low"
    fifty_plus_percentage: float  # % of innings with 50+ scores
    
    # vs Pace/Spin Split
    pace_sr: float
    pace_avg: float
    spin_sr: float
    spin_avg: float
    preferred_bowling_type: str  # "pace" | "spin" | "balanced"
```

### 2.2 Bowler Pattern Schema

```python
@dataclass
class BowlerPatternData:
    """Structured pattern data extracted from bowler statistics."""
    
    # Identity
    player_name: str
    matches: int
    total_wickets: int
    total_overs: float
    
    # Overall Profile
    overall_economy: float
    overall_average: float
    overall_strike_rate: float
    overall_dot_percentage: float
    
    # Role Classification
    primary_phase: str  # "powerplay" | "middle" | "death" | "specialist" | "workhorse"
    phase_distribution: Dict[str, float]  # % of overs bowled in each phase
    
    # Bowling Profile
    profile_classification: str  # "wicket_taker" | "economical" | "balanced" | "restrictive"
    profile_evidence: List[str]
    
    # Strengths (up to 3)
    strengths: List[Dict[str, Any]]
    # Example: {"context": "vs RHB in death", "economy": 6.2, "wickets_per_over": 0.4}
    
    # Weaknesses (up to 2)  
    weaknesses: List[Dict[str, Any]]
    # Example: {"context": "vs LHB in powerplay", "economy": 9.8}
    
    # Usage Pattern
    typical_overs: List[int]  # Most common overs bowled (e.g., [17, 19])
    over_combination_pattern: str  # "death_specialist" | "pp_middle" | "flexible"
    overs_per_match: float
    
    # Handedness Matchup
    vs_rhb_economy: float
    vs_lhb_economy: float
    preferred_matchup: str  # "RHB" | "LHB" | "balanced"
    
    # Consistency
    consistency_rating: str
    three_plus_wicket_percentage: float
```

---

## 3. Pattern Detection Rules

### 3.1 Batter Pattern Detection

Create file: `services/player_patterns.py`

```python
"""
Player Pattern Detection Service
================================
Extracts meaningful patterns from raw player statistics using rule-based logic.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class BattingStyle(Enum):
    ANCHOR = "anchor"
    AGGRESSOR = "aggressor"
    ACCUMULATOR = "accumulator"
    FINISHER = "finisher"
    BALANCED = "balanced"


class Phase(Enum):
    POWERPLAY = "powerplay"
    MIDDLE = "middle"
    DEATH = "death"


# =============================================================================
# BATTER PATTERN DETECTION
# =============================================================================

def detect_batter_patterns(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract patterns from batter statistics.
    
    Args:
        stats: Raw stats from /player/{name}/stats endpoint
        
    Returns:
        Structured pattern data for LLM synthesis
    """
    overall = stats.get("overall", {})
    phase_stats = stats.get("phase_stats", {}).get("overall", {})
    pace_stats = stats.get("phase_stats", {}).get("pace", {})
    spin_stats = stats.get("phase_stats", {}).get("spin", {})
    bowling_types = stats.get("phase_stats", {}).get("bowling_types", {})
    innings = stats.get("innings", [])
    
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
    
    # Detect strengths
    patterns["strengths"] = _detect_batter_strengths(
        phase_stats, pace_stats, spin_stats, bowling_types
    )
    
    # Detect weaknesses
    patterns["weaknesses"] = _detect_batter_weaknesses(
        phase_stats, pace_stats, spin_stats, bowling_types
    )
    
    # Detect entry pattern
    patterns.update(_analyze_entry_pattern(innings))
    
    # Pace vs Spin preference
    patterns.update(_analyze_pace_spin_preference(pace_stats, spin_stats))
    
    # Consistency analysis
    patterns.update(_analyze_consistency(innings, overall))
    
    return patterns


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
    """Determine player's primary batting phase."""
    # If any phase > 45%, they're a specialist
    max_phase = max(distribution, key=distribution.get)
    max_pct = distribution[max_phase]
    
    if max_pct > 45:
        return max_phase
    elif max_pct < 38:
        return "balanced"
    else:
        return max_phase


def _classify_batting_style(overall: Dict, phase_stats: Dict) -> tuple:
    """
    Classify batting style based on key metrics.
    
    Returns:
        tuple: (style_classification, list of evidence points)
    """
    sr = overall.get("strike_rate", 0)
    avg = overall.get("average", 0)
    dot_pct = overall.get("dot_percentage", 0)
    boundary_pct = overall.get("boundary_percentage", 0)
    death_sr = phase_stats.get("death", {}).get("strike_rate", 0)
    
    evidence = []
    
    # Aggressor: High SR (140+), high boundary % (15%+)
    if sr >= 140 and boundary_pct >= 15:
        evidence.append(f"High strike rate ({sr:.1f})")
        evidence.append(f"High boundary percentage ({boundary_pct:.1f}%)")
        return "aggressor", evidence
    
    # Anchor: Good average (30+), moderate SR (120-140), low dots
    if avg >= 30 and 120 <= sr < 140 and dot_pct < 35:
        evidence.append(f"Strong average ({avg:.1f})")
        evidence.append(f"Rotates strike well ({dot_pct:.1f}% dots)")
        return "anchor", evidence
    
    # Finisher: Death SR > 150, primary phase is death
    if death_sr >= 150:
        evidence.append(f"Explosive in death overs (SR {death_sr:.1f})")
        return "finisher", evidence
    
    # Accumulator: High average, lower SR
    if avg >= 25 and sr < 125:
        evidence.append(f"Consistent scorer (Avg {avg:.1f})")
        evidence.append(f"Conservative approach (SR {sr:.1f})")
        return "accumulator", evidence
    
    return "balanced", ["Versatile batting profile"]


def _detect_batter_strengths(
    phase_stats: Dict, 
    pace_stats: Dict, 
    spin_stats: Dict,
    bowling_types: Dict
) -> List[Dict]:
    """
    Detect up to 3 key strengths.
    
    Criteria for strength:
    - SR >= 140 OR Avg >= 35 in a specific context
    - Minimum 30 balls sample size
    """
    strengths = []
    
    # Check phase-wise strengths
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = phase_stats.get(phase_name, {})
        if phase_data.get("balls", 0) >= 30:
            sr = phase_data.get("strike_rate", 0)
            avg = phase_data.get("average", 0)
            
            if sr >= 145 or avg >= 40:
                strengths.append({
                    "context": f"in {phase_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": phase_data.get("balls", 0),
                    "strength_type": "high_sr" if sr >= 145 else "high_avg"
                })
    
    # Check vs pace by phase
    for phase_name in ["powerplay", "middle", "death"]:
        pace_phase = pace_stats.get(phase_name, {})
        if pace_phase.get("balls", 0) >= 30:
            sr = pace_phase.get("strike_rate", 0)
            avg = pace_phase.get("average", 0)
            
            if sr >= 150 or avg >= 45:
                strengths.append({
                    "context": f"vs pace in {phase_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": pace_phase.get("balls", 0),
                    "strength_type": "vs_pace"
                })
    
    # Check vs spin by phase
    for phase_name in ["powerplay", "middle", "death"]:
        spin_phase = spin_stats.get(phase_name, {})
        if spin_phase.get("balls", 0) >= 30:
            sr = spin_phase.get("strike_rate", 0)
            avg = spin_phase.get("average", 0)
            
            if sr >= 140 or avg >= 40:
                strengths.append({
                    "context": f"vs spin in {phase_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": spin_phase.get("balls", 0),
                    "strength_type": "vs_spin"
                })
    
    # Check specific bowling types
    for bowl_type, type_stats in bowling_types.items():
        overall_type = type_stats.get("overall", {})
        if overall_type.get("balls", 0) >= 50:
            sr = overall_type.get("strike_rate", 0)
            avg = overall_type.get("average", 0)
            
            if sr >= 160 or avg >= 50:
                bowl_type_name = _get_bowling_type_name(bowl_type)
                strengths.append({
                    "context": f"vs {bowl_type_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": overall_type.get("balls", 0),
                    "strength_type": f"vs_{bowl_type}"
                })
    
    # Sort by combined score (normalized SR + normalized Avg)
    def strength_score(s):
        sr_score = min(s.get("strike_rate", 0) / 150, 1.5)  # Cap at 1.5
        avg_score = min(s.get("average", 0) / 40, 1.5)
        return sr_score + avg_score
    
    strengths.sort(key=strength_score, reverse=True)
    return strengths[:3]  # Return top 3


def _detect_batter_weaknesses(
    phase_stats: Dict,
    pace_stats: Dict,
    spin_stats: Dict,
    bowling_types: Dict
) -> List[Dict]:
    """
    Detect up to 2 key weaknesses.
    
    Criteria for weakness:
    - SR <= 110 OR Avg <= 20 in a specific context
    - Higher dismissal rate (balls per dismissal < 15)
    - Minimum 20 balls sample size
    """
    weaknesses = []
    
    # Calculate overall dismissal rate for comparison
    overall_balls = sum(
        phase_stats.get(p, {}).get("balls", 0) 
        for p in ["powerplay", "middle", "death"]
    )
    
    # Check specific bowling types for weaknesses
    for bowl_type, type_stats in bowling_types.items():
        overall_type = type_stats.get("overall", {})
        balls = overall_type.get("balls", 0)
        
        if balls >= 25:
            sr = overall_type.get("strike_rate", 0)
            avg = overall_type.get("average", 0)
            
            # Weakness: Low SR or low average
            if sr <= 110 or (avg > 0 and avg <= 18):
                bowl_type_name = _get_bowling_type_name(bowl_type)
                
                # Calculate dismissal rate comparison if we have wickets
                runs = overall_type.get("runs", 0)
                dismissal_rate = None
                if avg > 0 and runs > 0:
                    wickets = runs / avg
                    if wickets > 0:
                        balls_per_dismissal = balls / wickets
                        dismissal_rate = round(balls_per_dismissal, 1)
                
                weaknesses.append({
                    "context": f"vs {bowl_type_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": balls,
                    "balls_per_dismissal": dismissal_rate,
                    "weakness_type": f"vs_{bowl_type}"
                })
    
    # Check phase-wise weaknesses vs spin
    for phase_name in ["powerplay", "middle", "death"]:
        spin_phase = spin_stats.get(phase_name, {})
        if spin_phase.get("balls", 0) >= 25:
            sr = spin_phase.get("strike_rate", 0)
            avg = spin_phase.get("average", 0)
            
            if sr <= 105 or (avg > 0 and avg <= 15):
                weaknesses.append({
                    "context": f"vs spin in {phase_name}",
                    "strike_rate": sr,
                    "average": avg,
                    "balls": spin_phase.get("balls", 0),
                    "weakness_type": "vs_spin_phase"
                })
    
    # Sort by severity (lower SR and Avg = more severe)
    def weakness_score(w):
        sr_score = max(0, (110 - w.get("strike_rate", 110)) / 30)
        avg_score = max(0, (20 - w.get("average", 20)) / 10) if w.get("average", 0) > 0 else 0.5
        return sr_score + avg_score
    
    weaknesses.sort(key=weakness_score, reverse=True)
    return weaknesses[:2]  # Return top 2


def _analyze_entry_pattern(innings: List[Dict]) -> Dict:
    """Analyze when the batter typically comes in to bat."""
    if not innings:
        return {
            "typical_batting_position": None,
            "entry_pattern": "unknown",
            "avg_entry_over": None
        }
    
    positions = [i.get("batting_position") for i in innings if i.get("batting_position")]
    entry_overs = [
        i.get("entry_point", {}).get("overs", 0) 
        for i in innings 
        if i.get("entry_point", {}).get("overs") is not None
    ]
    
    # Calculate mode of batting position
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
        elif avg_entry <= 8:
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


def _analyze_consistency(innings: List[Dict], overall: Dict) -> Dict:
    """Analyze batting consistency."""
    if not innings:
        return {
            "consistency_rating": "unknown",
            "fifty_plus_percentage": 0
        }
    
    runs_list = [i.get("runs", 0) for i in innings]
    total_innings = len(runs_list)
    
    fifties = sum(1 for r in runs_list if r >= 50)
    fifty_plus_pct = (fifties / total_innings * 100) if total_innings > 0 else 0
    
    # Calculate standard deviation relative to average
    avg = overall.get("average", 0)
    if avg > 0 and total_innings > 1:
        variance = sum((r - avg) ** 2 for r in runs_list) / total_innings
        std_dev = variance ** 0.5
        cv = std_dev / avg  # Coefficient of variation
        
        if cv < 0.6:
            consistency = "high"
        elif cv < 0.9:
            consistency = "medium"
        else:
            consistency = "low"
    else:
        consistency = "unknown"
    
    return {
        "consistency_rating": consistency,
        "fifty_plus_percentage": round(fifty_plus_pct, 1)
    }


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
# BOWLER PATTERN DETECTION
# =============================================================================

def detect_bowler_patterns(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract patterns from bowler statistics.
    
    Args:
        stats: Raw stats from /player/{name}/bowling_stats endpoint
        
    Returns:
        Structured pattern data for LLM synthesis
    """
    overall = stats.get("overall", {})
    phase_stats = stats.get("phase_stats", {})
    over_distribution = stats.get("over_distribution", [])
    batter_handedness = stats.get("batter_handedness", {})
    over_combinations = stats.get("over_combinations", [])
    innings = stats.get("innings", [])
    
    patterns = {
        "player_name": stats.get("player_name", "Unknown"),
        "matches": overall.get("matches", 0),
        "total_wickets": overall.get("wickets", 0),
        "total_overs": overall.get("overs", 0),
        "overall_economy": overall.get("economy_rate", 0),
        "overall_average": overall.get("bowling_average", 0),
        "overall_strike_rate": overall.get("bowling_strike_rate", 0),
        "overall_dot_percentage": overall.get("dot_percentage", 0),
    }
    
    # Detect primary phase
    patterns["phase_distribution"] = _calculate_bowling_phase_distribution(phase_stats)
    patterns["primary_phase"] = _detect_bowling_primary_phase(patterns["phase_distribution"])
    
    # Detect bowling profile
    patterns["profile_classification"], patterns["profile_evidence"] = _classify_bowling_profile(
        overall, phase_stats
    )
    
    # Detect strengths
    patterns["strengths"] = _detect_bowler_strengths(phase_stats, batter_handedness)
    
    # Detect weaknesses
    patterns["weaknesses"] = _detect_bowler_weaknesses(phase_stats, batter_handedness)
    
    # Analyze usage pattern
    patterns.update(_analyze_bowling_usage(over_distribution, over_combinations, overall))
    
    # Handedness matchup
    patterns.update(_analyze_handedness_matchup(batter_handedness))
    
    # Consistency
    patterns.update(_analyze_bowling_consistency(innings, overall))
    
    return patterns


def _calculate_bowling_phase_distribution(phase_stats: Dict) -> Dict[str, float]:
    """Calculate percentage of overs bowled in each phase."""
    pp_overs = phase_stats.get("powerplay", {}).get("overs", 0)
    mid_overs = phase_stats.get("middle", {}).get("overs", 0)
    death_overs = phase_stats.get("death", {}).get("overs", 0)
    
    total = pp_overs + mid_overs + death_overs
    if total == 0:
        return {"powerplay": 33.3, "middle": 33.3, "death": 33.3}
    
    return {
        "powerplay": round((pp_overs / total) * 100, 1),
        "middle": round((mid_overs / total) * 100, 1),
        "death": round((death_overs / total) * 100, 1)
    }


def _detect_bowling_primary_phase(distribution: Dict[str, float]) -> str:
    """Determine bowler's primary phase."""
    max_phase = max(distribution, key=distribution.get)
    max_pct = distribution[max_phase]
    
    # Specialist threshold is higher for bowlers (50%)
    if max_pct > 50:
        return f"{max_phase}_specialist"
    elif max_pct > 40:
        return max_phase
    else:
        return "workhorse"  # Bowls across all phases


def _classify_bowling_profile(overall: Dict, phase_stats: Dict) -> tuple:
    """Classify bowling profile."""
    economy = overall.get("economy_rate", 0)
    sr = overall.get("bowling_strike_rate", 0)
    avg = overall.get("bowling_average", 0)
    dot_pct = overall.get("dot_percentage", 0)
    
    evidence = []
    
    # Wicket taker: Low SR (<18), good economy
    if sr > 0 and sr <= 18:
        evidence.append(f"Excellent strike rate ({sr:.1f})")
        return "wicket_taker", evidence
    
    # Economical: Low economy (<7.5), high dots
    if economy <= 7.5 and dot_pct >= 40:
        evidence.append(f"Miserly economy ({economy:.2f})")
        evidence.append(f"High dot ball percentage ({dot_pct:.1f}%)")
        return "economical", evidence
    
    # Restrictive: High dots, moderate economy
    if dot_pct >= 45:
        evidence.append(f"Builds pressure ({dot_pct:.1f}% dots)")
        return "restrictive", evidence
    
    # Balanced
    if economy <= 8.5 and sr <= 24:
        evidence.append(f"Balanced profile (Econ: {economy:.2f}, SR: {sr:.1f})")
        return "balanced", evidence
    
    return "impact", ["Capable of match-winning spells"]


def _detect_bowler_strengths(phase_stats: Dict, handedness: Dict) -> List[Dict]:
    """Detect bowler strengths."""
    strengths = []
    
    # Phase-wise strengths
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = phase_stats.get(phase_name, {})
        overs = phase_data.get("overs", 0)
        
        if overs >= 10:  # Minimum sample
            economy = phase_data.get("economy", 0)
            sr = phase_data.get("bowling_strike_rate", 0)
            
            # Strong in phase: Low economy or low SR
            if economy <= 7.0 or (sr > 0 and sr <= 15):
                strengths.append({
                    "context": f"in {phase_name}",
                    "economy": economy,
                    "strike_rate": sr,
                    "overs": overs,
                    "strength_type": "phase"
                })
    
    # Handedness strengths
    for hand in ["Right hand", "Left hand"]:
        hand_data = handedness.get(hand, {}).get("overall", {})
        balls = hand_data.get("balls", 0)
        
        if balls >= 60:
            economy = hand_data.get("economy", 0)
            sr = hand_data.get("bowling_strike_rate", 0)
            
            if economy <= 7.0 or (sr > 0 and sr <= 14):
                hand_short = "RHB" if hand == "Right hand" else "LHB"
                strengths.append({
                    "context": f"vs {hand_short}",
                    "economy": economy,
                    "strike_rate": sr,
                    "balls": balls,
                    "strength_type": "handedness"
                })
    
    # Sort by combined effectiveness
    def strength_score(s):
        econ_score = max(0, (8 - s.get("economy", 8)) / 2)
        sr_score = max(0, (20 - s.get("strike_rate", 20)) / 5) if s.get("strike_rate", 0) > 0 else 0
        return econ_score + sr_score
    
    strengths.sort(key=strength_score, reverse=True)
    return strengths[:3]


def _detect_bowler_weaknesses(phase_stats: Dict, handedness: Dict) -> List[Dict]:
    """Detect bowler weaknesses."""
    weaknesses = []
    
    # Phase-wise weaknesses
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = phase_stats.get(phase_name, {})
        overs = phase_data.get("overs", 0)
        
        if overs >= 8:
            economy = phase_data.get("economy", 0)
            
            if economy >= 9.5:
                weaknesses.append({
                    "context": f"in {phase_name}",
                    "economy": economy,
                    "overs": overs,
                    "weakness_type": "phase"
                })
    
    # Handedness weaknesses
    for hand in ["Right hand", "Left hand"]:
        hand_data = handedness.get(hand, {}).get("overall", {})
        balls = hand_data.get("balls", 0)
        
        if balls >= 50:
            economy = hand_data.get("economy", 0)
            
            if economy >= 9.5:
                hand_short = "RHB" if hand == "Right hand" else "LHB"
                weaknesses.append({
                    "context": f"vs {hand_short}",
                    "economy": economy,
                    "balls": balls,
                    "weakness_type": "handedness"
                })
    
    weaknesses.sort(key=lambda w: w.get("economy", 0), reverse=True)
    return weaknesses[:2]


def _analyze_bowling_usage(
    over_distribution: List[Dict], 
    over_combinations: List[Dict],
    overall: Dict
) -> Dict:
    """Analyze when the bowler is typically used."""
    if not over_distribution:
        return {
            "typical_overs": [],
            "over_combination_pattern": "unknown",
            "overs_per_match": 0
        }
    
    # Find most frequent overs (bowled in >40% of matches)
    matches = overall.get("matches", 1)
    typical_overs = [
        od["over_number"] 
        for od in over_distribution 
        if od.get("matches_percentage", 0) >= 40
    ]
    
    # Determine pattern from combinations
    if over_combinations:
        top_combo = over_combinations[0].get("overs", [])
        
        # Check if death specialist (overs 16-19)
        if all(o >= 15 for o in top_combo if o is not None):
            pattern = "death_specialist"
        # Check if powerplay specialist (overs 0-5)
        elif all(o < 6 for o in top_combo if o is not None):
            pattern = "powerplay_specialist"
        # Check if middle specialist
        elif all(5 < o < 15 for o in top_combo if o is not None):
            pattern = "middle_specialist"
        else:
            pattern = "flexible"
    else:
        pattern = "flexible"
    
    overs_per_match = overall.get("overs", 0) / matches if matches > 0 else 0
    
    return {
        "typical_overs": typical_overs[:5],  # Top 5 most bowled overs
        "over_combination_pattern": pattern,
        "overs_per_match": round(overs_per_match, 1)
    }


def _analyze_handedness_matchup(handedness: Dict) -> Dict:
    """Analyze performance vs different handed batters."""
    rhb = handedness.get("Right hand", {}).get("overall", {})
    lhb = handedness.get("Left hand", {}).get("overall", {})
    
    rhb_econ = rhb.get("economy", 0)
    lhb_econ = lhb.get("economy", 0)
    
    if rhb_econ > 0 and lhb_econ > 0:
        if rhb_econ < lhb_econ * 0.85:
            preference = "RHB"
        elif lhb_econ < rhb_econ * 0.85:
            preference = "LHB"
        else:
            preference = "balanced"
    else:
        preference = "unknown"
    
    return {
        "vs_rhb_economy": rhb_econ,
        "vs_lhb_economy": lhb_econ,
        "preferred_matchup": preference
    }


def _analyze_bowling_consistency(innings: List[Dict], overall: Dict) -> Dict:
    """Analyze bowling consistency."""
    if not innings:
        return {
            "consistency_rating": "unknown",
            "three_plus_wicket_percentage": 0
        }
    
    wicket_list = [i.get("wickets", 0) for i in innings]
    total_innings = len(wicket_list)
    
    three_plus = sum(1 for w in wicket_list if w >= 3)
    three_plus_pct = (three_plus / total_innings * 100) if total_innings > 0 else 0
    
    # Calculate consistency based on wicket variance
    avg_wickets = overall.get("wickets", 0) / total_innings if total_innings > 0 else 0
    if avg_wickets > 0 and total_innings > 1:
        variance = sum((w - avg_wickets) ** 2 for w in wicket_list) / total_innings
        std_dev = variance ** 0.5
        cv = std_dev / avg_wickets
        
        if cv < 0.7:
            consistency = "high"
        elif cv < 1.0:
            consistency = "medium"
        else:
            consistency = "low"
    else:
        consistency = "unknown"
    
    return {
        "consistency_rating": consistency,
        "three_plus_wicket_percentage": round(three_plus_pct, 1)
    }
```

---

## 4. LLM Prompt Design

### 4.1 Batter Summary Prompt

```python
BATTER_SUMMARY_PROMPT = """You are a cricket analyst writing a concise "Player DNA" summary. Based on the pattern data below, write a brief, insightful summary of this batter's playing style.

## Pattern Data
{pattern_json}

## Output Format
Write exactly 5 bullet points, each on a new line starting with an emoji and label:

🎯 Primary Role: [1 sentence describing their main role based on phase_distribution and style]
⚡ Batting Style: [1 sentence about their approach using style_classification and evidence]
💪 Sweet Spot: [Best matchup from strengths list with key stats]
⚠️ Vulnerability: [Main weakness from weaknesses list, or "No significant weaknesses" if empty]
📊 Entry Pattern: [When they typically bat based on entry_pattern and batting_position]

## Rules
1. Be specific - use actual numbers from the data
2. Keep each bullet to ONE sentence
3. Use cricket terminology appropriately
4. If a weakness list is empty, write "No clear vulnerabilities in current dataset"
5. Format numbers nicely (e.g., "SR 145.2" not "strike_rate: 145.23456")
6. For strengths/weaknesses, mention the context (e.g., "vs left-arm spin in death overs")

## Example Output
🎯 Primary Role: Middle-overs anchor who faces 45% of balls between overs 7-15
⚡ Batting Style: Calculated aggressor (SR 138) who rotates strike exceptionally well (only 28% dots)
💪 Sweet Spot: Devastating against pace in powerplay (SR 152, Avg 48) with a boundary every 4.2 balls
⚠️ Vulnerability: Struggles against left-arm orthodox in middle overs (SR 98, gets out 2x more often)
📊 Entry Pattern: Typically bats at #3, entering within the first 3 overs in 72% of innings

Now generate the summary for the player data provided:"""


BOWLER_SUMMARY_PROMPT = """You are a cricket analyst writing a concise "Player DNA" summary. Based on the pattern data below, write a brief, insightful summary of this bowler's style.

## Pattern Data
{pattern_json}

## Output Format
Write exactly 5 bullet points, each on a new line starting with an emoji and label:

🎯 Primary Phase: [1 sentence about when they bowl based on phase_distribution]
⚡ Bowling Profile: [1 sentence about their style using profile_classification]
💪 Dominance: [Best matchup from strengths list with key stats]
⚠️ Vulnerability: [Main weakness from weaknesses list, or "No significant weaknesses"]
📊 Usage Pattern: [Which overs they typically bowl based on typical_overs]

## Rules
1. Be specific - use actual numbers from the data
2. Keep each bullet to ONE sentence
3. Use cricket terminology appropriately
4. Format economy as "Econ 7.2" and strike rate as "SR 18"
5. For typical_overs, translate to human format (e.g., "overs 17 and 19" not "[16, 18]")
6. Note: over numbers in data are 0-indexed, so over 16 = 17th over

## Example Output
🎯 Primary Phase: Death specialist who bowls 62% of overs in the final 5 overs
⚡ Bowling Profile: Wicket-taking threat (SR 16.2) who builds pressure through dots (44%)
💪 Dominance: Exceptional vs RHB in death overs (Econ 6.8, takes a wicket every 12 balls)
⚠️ Vulnerability: Can be expensive vs LHB in powerplay (Econ 9.4)
📊 Usage Pattern: Team's go-to bowler for overs 17 and 19, rarely bowls the 18th

Now generate the summary for the player data provided:"""
```

### 4.2 Prompt Optimization Notes

| Optimization | Rationale |
|--------------|-----------|
| Structured output format | Ensures consistent parsing |
| Explicit emoji labels | Visual consistency |
| Example output | Few-shot learning improves quality |
| Number formatting rules | Prevents ugly decimals |
| One sentence per point | Keeps it scannable |

---

## 5. Backend Implementation

### 5.1 API Endpoint

Create file: `routers/player_summary.py`

```python
"""
Player Summary API
==================
Generates AI-powered player DNA summaries.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
import hashlib
import json
import openai
import os
import logging

from database import get_session
from services.player_patterns import detect_batter_patterns, detect_bowler_patterns

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/player-summary", tags=["Player Summary"])

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
MAX_TOKENS = 500
TEMPERATURE = 0.3  # Slightly higher for more natural writing

# In-memory cache (use Redis in production)
summary_cache = {}


# =============================================================================
# Request/Response Models
# =============================================================================

class SummaryResponse(BaseModel):
    success: bool
    player_name: str
    player_type: str  # "batter" or "bowler"
    summary: Optional[str] = None
    patterns: Optional[dict] = None  # Include raw patterns for debugging
    error: Optional[str] = None
    cached: bool = False


# =============================================================================
# Prompts
# =============================================================================

BATTER_SUMMARY_PROMPT = """You are a cricket analyst writing a concise "Player DNA" summary. Based on the pattern data below, write a brief, insightful summary of this batter's playing style.

## Pattern Data
{pattern_json}

## Output Format
Write exactly 5 bullet points, each on a new line starting with an emoji and label:

🎯 Primary Role: [1 sentence describing their main role based on phase_distribution and style]
⚡ Batting Style: [1 sentence about their approach using style_classification and evidence]
💪 Sweet Spot: [Best matchup from strengths list with key stats]
⚠️ Vulnerability: [Main weakness from weaknesses list, or "No significant weaknesses" if empty]
📊 Entry Pattern: [When they typically bat based on entry_pattern and batting_position]

## Rules
1. Be specific - use actual numbers from the data
2. Keep each bullet to ONE sentence
3. Use cricket terminology appropriately
4. If weaknesses list is empty, write "No clear vulnerabilities identified in current dataset"
5. Format numbers nicely (e.g., "SR 145" not "strike_rate: 145.23456")
6. For strengths/weaknesses, mention the context (e.g., "vs left-arm spin in death overs")

Now generate the summary:"""


BOWLER_SUMMARY_PROMPT = """You are a cricket analyst writing a concise "Player DNA" summary. Based on the pattern data below, write a brief, insightful summary of this bowler's style.

## Pattern Data
{pattern_json}

## Output Format
Write exactly 5 bullet points, each on a new line starting with an emoji and label:

🎯 Primary Phase: [1 sentence about when they bowl based on phase_distribution]
⚡ Bowling Profile: [1 sentence about their style using profile_classification]
💪 Dominance: [Best matchup from strengths list with key stats]
⚠️ Vulnerability: [Main weakness from weaknesses list, or "No significant weaknesses"]
📊 Usage Pattern: [Which overs they typically bowl based on typical_overs]

## Rules
1. Be specific - use actual numbers
2. Keep each bullet to ONE sentence
3. Format economy as "Econ 7.2" and strike rate as "SR 18"
4. For typical_overs, translate to human format (e.g., "overs 17 and 19")
5. Note: over numbers are 0-indexed, add 1 for display (over 16 = 17th over)

Now generate the summary:"""


# =============================================================================
# Helper Functions
# =============================================================================

def get_cache_key(player_name: str, player_type: str, filters: dict) -> str:
    """Generate cache key from player and filters."""
    filter_str = json.dumps(filters, sort_keys=True)
    combined = f"{player_name}:{player_type}:{filter_str}"
    return hashlib.md5(combined.encode()).hexdigest()


def generate_summary_with_llm(patterns: dict, player_type: str) -> str:
    """Call OpenAI to generate summary from patterns."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    # Select appropriate prompt
    if player_type == "batter":
        prompt = BATTER_SUMMARY_PROMPT.format(pattern_json=json.dumps(patterns, indent=2))
    else:
        prompt = BOWLER_SUMMARY_PROMPT.format(pattern_json=json.dumps(patterns, indent=2))
    
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE
    )
    
    return response.choices[0].message.content.strip()


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/batter/{player_name}", response_model=SummaryResponse)
async def get_batter_summary(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    include_patterns: bool = Query(default=False),
    db: Session = Depends(get_session)
):
    """
    Generate AI-powered batting summary for a player.
    
    This endpoint:
    1. Fetches player stats from existing endpoint
    2. Extracts patterns using rule-based detection
    3. Generates natural language summary using LLM
    4. Caches result for subsequent requests
    """
    try:
        # Build filter dict for cache key
        filters = {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "leagues": leagues,
            "include_international": include_international,
            "top_teams": top_teams,
            "venue": venue
        }
        
        # Check cache
        cache_key = get_cache_key(player_name, "batter", filters)
        if cache_key in summary_cache:
            cached_result = summary_cache[cache_key]
            return SummaryResponse(
                success=True,
                player_name=player_name,
                player_type="batter",
                summary=cached_result["summary"],
                patterns=cached_result["patterns"] if include_patterns else None,
                cached=True
            )
        
        # Fetch stats from existing endpoint (internal call)
        # In production, you'd call the actual endpoint or service
        from main import get_player_stats  # Import the existing function
        
        stats = get_player_stats(
            player_name=player_name,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            venue=venue,
            db=db
        )
        
        # Detect patterns
        patterns = detect_batter_patterns(stats)
        patterns["player_name"] = player_name
        
        # Generate summary
        summary = generate_summary_with_llm(patterns, "batter")
        
        # Cache result
        summary_cache[cache_key] = {
            "summary": summary,
            "patterns": patterns
        }
        
        return SummaryResponse(
            success=True,
            player_name=player_name,
            player_type="batter",
            summary=summary,
            patterns=patterns if include_patterns else None,
            cached=False
        )
        
    except Exception as e:
        logger.error(f"Error generating batter summary: {e}")
        return SummaryResponse(
            success=False,
            player_name=player_name,
            player_type="batter",
            error=str(e)
        )


@router.get("/bowler/{player_name}", response_model=SummaryResponse)
async def get_bowler_summary(
    player_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    leagues: List[str] = Query(default=[]),
    include_international: bool = Query(default=False),
    top_teams: Optional[int] = Query(default=None),
    venue: Optional[str] = None,
    include_patterns: bool = Query(default=False),
    db: Session = Depends(get_session)
):
    """Generate AI-powered bowling summary for a player."""
    try:
        filters = {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "leagues": leagues,
            "include_international": include_international,
            "top_teams": top_teams,
            "venue": venue
        }
        
        cache_key = get_cache_key(player_name, "bowler", filters)
        if cache_key in summary_cache:
            cached_result = summary_cache[cache_key]
            return SummaryResponse(
                success=True,
                player_name=player_name,
                player_type="bowler",
                summary=cached_result["summary"],
                patterns=cached_result["patterns"] if include_patterns else None,
                cached=True
            )
        
        # Fetch stats
        from main import get_player_bowling_stats
        
        stats = get_player_bowling_stats(
            player_name=player_name,
            start_date=start_date,
            end_date=end_date,
            leagues=leagues,
            include_international=include_international,
            top_teams=top_teams,
            venue=venue,
            db=db
        )
        
        # Detect patterns
        patterns = detect_bowler_patterns(stats)
        patterns["player_name"] = player_name
        
        # Generate summary
        summary = generate_summary_with_llm(patterns, "bowler")
        
        # Cache
        summary_cache[cache_key] = {
            "summary": summary,
            "patterns": patterns
        }
        
        return SummaryResponse(
            success=True,
            player_name=player_name,
            player_type="bowler",
            summary=summary,
            patterns=patterns if include_patterns else None,
            cached=False
        )
        
    except Exception as e:
        logger.error(f"Error generating bowler summary: {e}")
        return SummaryResponse(
            success=False,
            player_name=player_name,
            player_type="bowler",
            error=str(e)
        )


@router.delete("/cache")
async def clear_summary_cache():
    """Clear the summary cache (admin endpoint)."""
    global summary_cache
    count = len(summary_cache)
    summary_cache = {}
    return {"cleared": count}
```

### 5.2 Register Router

Add to `main.py`:

```python
from routers.player_summary import router as player_summary_router

app.include_router(player_summary_router)
```

---

## 6. Frontend Component

### 6.1 PlayerDNASummary Component

Create file: `src/components/PlayerDNASummary.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Skeleton,
  Alert,
  IconButton,
  Tooltip,
  Collapse,
  Chip
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import axios from 'axios';
import config from '../config';

/**
 * PlayerDNASummary Component
 * 
 * Displays an AI-generated summary of a player's playing style.
 * 
 * @param {string} playerName - The player's name
 * @param {string} playerType - "batter" or "bowler"
 * @param {object} filters - Current filter settings (dates, leagues, etc.)
 * @param {boolean} autoLoad - Whether to load automatically (default: true)
 */
const PlayerDNASummary = ({ 
  playerName, 
  playerType = "batter",
  filters = {},
  autoLoad = true
}) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(true);
  const [cached, setCached] = useState(false);
  
  const fetchSummary = async () => {
    if (!playerName) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.venue) params.append('venue', filters.venue);
      if (filters.leagues) {
        filters.leagues.forEach(l => params.append('leagues', l));
      }
      if (filters.includeInternational) {
        params.append('include_international', 'true');
      }
      if (filters.topTeams) {
        params.append('top_teams', filters.topTeams);
      }
      
      const endpoint = playerType === "batter" 
        ? `/player-summary/batter/${encodeURIComponent(playerName)}`
        : `/player-summary/bowler/${encodeURIComponent(playerName)}`;
      
      const response = await axios.get(
        `${config.API_URL}${endpoint}?${params}`
      );
      
      if (response.data.success) {
        setSummary(response.data.summary);
        setCached(response.data.cached);
      } else {
        setError(response.data.error || 'Failed to generate summary');
      }
    } catch (err) {
      console.error('Error fetching player summary:', err);
      setError('Unable to generate AI summary. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    if (autoLoad && playerName) {
      fetchSummary();
    }
  }, [playerName, JSON.stringify(filters)]);
  
  // Parse summary into bullet points
  const parseSummary = (text) => {
    if (!text) return [];
    
    return text.split('\n')
      .filter(line => line.trim())
      .map(line => {
        // Extract emoji, label, and content
        const match = line.match(/^([🎯⚡💪⚠️📊])\s*([^:]+):\s*(.+)$/);
        if (match) {
          return {
            emoji: match[1],
            label: match[2].trim(),
            content: match[3].trim()
          };
        }
        return { emoji: '•', label: '', content: line.trim() };
      });
  };
  
  const bulletPoints = parseSummary(summary);
  
  if (!playerName) return null;
  
  return (
    <Card 
      sx={{ 
        mb: 3,
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
        color: 'white',
        position: 'relative',
        overflow: 'visible'
      }}
    >
      {/* AI Badge */}
      <Chip
        icon={<AutoAwesomeIcon sx={{ color: '#ffd700 !important' }} />}
        label="AI Insight"
        size="small"
        sx={{
          position: 'absolute',
          top: -12,
          right: 16,
          backgroundColor: '#2d2d44',
          color: '#ffd700',
          fontWeight: 'bold',
          fontSize: '0.7rem'
        }}
      />
      
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            🧬 Player DNA
            {cached && (
              <Chip 
                label="cached" 
                size="small" 
                sx={{ 
                  ml: 1, 
                  height: 20, 
                  fontSize: '0.65rem',
                  backgroundColor: 'rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.7)'
                }} 
              />
            )}
          </Typography>
          
          <Box>
            <Tooltip title="Regenerate summary">
              <IconButton 
                size="small" 
                onClick={fetchSummary}
                disabled={loading}
                sx={{ color: 'white' }}
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <IconButton 
              size="small"
              onClick={() => setExpanded(!expanded)}
              sx={{ color: 'white' }}
            >
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        </Box>
        
        <Collapse in={expanded}>
          {/* Loading State */}
          {loading && (
            <Box>
              {[1, 2, 3, 4, 5].map(i => (
                <Skeleton 
                  key={i}
                  variant="text" 
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.1)',
                    mb: 1.5,
                    height: 24
                  }} 
                />
              ))}
            </Box>
          )}
          
          {/* Error State */}
          {error && !loading && (
            <Alert 
              severity="warning" 
              sx={{ 
                backgroundColor: 'rgba(255,152,0,0.1)',
                color: 'white'
              }}
            >
              {error}
            </Alert>
          )}
          
          {/* Summary Content */}
          {summary && !loading && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {bulletPoints.map((point, index) => (
                <Box 
                  key={index}
                  sx={{ 
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 1.5,
                    p: 1.5,
                    borderRadius: 1,
                    backgroundColor: 'rgba(255,255,255,0.05)',
                    transition: 'background-color 0.2s',
                    '&:hover': {
                      backgroundColor: 'rgba(255,255,255,0.08)'
                    }
                  }}
                >
                  <Typography 
                    component="span" 
                    sx={{ fontSize: '1.2rem', lineHeight: 1.4 }}
                  >
                    {point.emoji}
                  </Typography>
                  <Box sx={{ flex: 1 }}>
                    {point.label && (
                      <Typography 
                        component="span"
                        sx={{ 
                          fontWeight: 'bold',
                          color: '#90caf9',
                          mr: 0.5
                        }}
                      >
                        {point.label}:
                      </Typography>
                    )}
                    <Typography 
                      component="span"
                      sx={{ color: 'rgba(255,255,255,0.9)' }}
                    >
                      {point.content}
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          )}
          
          {/* No Summary State */}
          {!summary && !loading && !error && (
            <Typography sx={{ color: 'rgba(255,255,255,0.6)', textAlign: 'center', py: 2 }}>
              Click refresh to generate AI summary
            </Typography>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default PlayerDNASummary;
```

### 6.2 Integration into Profile Pages

**In `PlayerProfile.jsx`:**

```jsx
// Add import
import PlayerDNASummary from './PlayerDNASummary';

// In render, after CareerStatsCards:
{stats && !loading && (
  <Box sx={{ mt: 4 }}>
    <CareerStatsCards stats={stats} />
    
    {/* AI Summary - NEW */}
    <PlayerDNASummary
      playerName={selectedPlayer}
      playerType="batter"
      filters={{
        startDate: dateRange.start,
        endDate: dateRange.end,
        venue: selectedVenue !== 'All Venues' ? selectedVenue : null,
        leagues: competitionFilters.leagues,
        includeInternational: competitionFilters.international,
        topTeams: competitionFilters.topTeams
      }}
    />
    
    {/* Rest of existing content */}
    ...
  </Box>
)}
```

**In `BowlerProfile.jsx`:**

```jsx
// Add import
import PlayerDNASummary from './PlayerDNASummary';

// In render, after BowlingCareerStatsCards:
{stats && !loading && (
  <Box sx={{ mt: 4 }}>
    <BowlingCareerStatsCards stats={stats} />
    
    {/* AI Summary - NEW */}
    <PlayerDNASummary
      playerName={selectedPlayer}
      playerType="bowler"
      filters={{
        startDate: dateRange.start,
        endDate: dateRange.end,
        venue: selectedVenue !== 'All Venues' ? selectedVenue : null,
        leagues: competitionFilters.leagues,
        includeInternational: competitionFilters.international,
        topTeams: competitionFilters.topTeams
      }}
    />
    
    {/* Rest of existing content */}
    ...
  </Box>
)}
```

---

## 7. Caching Strategy

### 7.1 Cache Key Structure

```
player_summary:{player_name}:{player_type}:{filter_hash}

Example:
player_summary:V Kohli:batter:a1b2c3d4e5f6
```

### 7.2 Cache Invalidation Rules

| Event | Action |
|-------|--------|
| New match data loaded | Clear all cache |
| Filter change | Generate new key (different hash) |
| Manual refresh | Bypass cache, regenerate |
| 24 hours elapsed | Auto-expire |

### 7.3 Production Cache (Redis)

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)
CACHE_TTL = 86400  # 24 hours

def get_cached_summary(cache_key: str) -> Optional[dict]:
    cached = redis_client.get(f"summary:{cache_key}")
    if cached:
        return json.loads(cached)
    return None

def set_cached_summary(cache_key: str, data: dict):
    redis_client.setex(
        f"summary:{cache_key}",
        CACHE_TTL,
        json.dumps(data)
    )
```

---

## 8. Cost Analysis

### 8.1 Token Estimation

| Component | Tokens | Notes |
|-----------|--------|-------|
| Pattern data | ~800 | JSON structure |
| Prompt template | ~300 | Fixed overhead |
| Output | ~150 | 5 bullet points |
| **Total per request** | **~1,250** | |

### 8.2 Cost per Summary

| Model | Input Cost | Output Cost | Total/Summary |
|-------|------------|-------------|---------------|
| GPT-4o | $5/1M | $15/1M | ~$0.008 |
| **GPT-4o-mini** | **$0.15/1M** | **$0.60/1M** | **~$0.0003** |

### 8.3 Monthly Cost Projection

| Scenario | Unique Players/Month | Cost (GPT-4o-mini) |
|----------|---------------------|-------------------|
| Light | 500 | $0.15 |
| Medium | 5,000 | $1.50 |
| Heavy | 50,000 | $15.00 |

**Key insight**: With aggressive caching, most requests hit cache. Real API calls are ~10-20% of total requests.

---

## 9. Testing Strategy

### 9.1 Unit Tests for Pattern Detection

```python
import pytest
from services.player_patterns import detect_batter_patterns, detect_bowler_patterns

class TestBatterPatterns:
    
    def test_aggressor_classification(self):
        """Test that high SR batters are classified as aggressors."""
        stats = {
            "overall": {
                "matches": 50,
                "runs": 1500,
                "average": 35,
                "strike_rate": 150,
                "boundary_percentage": 18,
                "dot_percentage": 28
            },
            "phase_stats": {
                "overall": {
                    "powerplay": {"balls": 300, "runs": 400, "strike_rate": 133},
                    "middle": {"balls": 400, "runs": 500, "strike_rate": 125},
                    "death": {"balls": 500, "runs": 800, "strike_rate": 160}
                }
            },
            "innings": []
        }
        
        patterns = detect_batter_patterns(stats)
        
        assert patterns["style_classification"] == "aggressor"
        assert patterns["overall_strike_rate"] == 150
    
    def test_death_specialist_detection(self):
        """Test that batters facing >45% balls in death are specialists."""
        stats = {
            "overall": {"matches": 50, "runs": 1000},
            "phase_stats": {
                "overall": {
                    "powerplay": {"balls": 200},
                    "middle": {"balls": 250},
                    "death": {"balls": 550}  # 55% of balls
                }
            },
            "innings": []
        }
        
        patterns = detect_batter_patterns(stats)
        
        assert patterns["primary_phase"] == "death"
        assert patterns["phase_distribution"]["death"] == 55.0


class TestBowlerPatterns:
    
    def test_death_specialist_bowler(self):
        """Test death specialist bowler detection."""
        stats = {
            "overall": {"matches": 40, "wickets": 50, "overs": 120},
            "phase_stats": {
                "powerplay": {"overs": 20},
                "middle": {"overs": 30},
                "death": {"overs": 70}  # 58% of overs
            },
            "over_distribution": [],
            "over_combinations": [],
            "batter_handedness": {},
            "innings": []
        }
        
        patterns = detect_bowler_patterns(stats)
        
        assert "death" in patterns["primary_phase"]
```

### 9.2 Integration Tests

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_batter_summary_endpoint():
    response = client.get("/player-summary/batter/V Kohli")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "🎯" in data["summary"]  # Has expected emoji

def test_bowler_summary_endpoint():
    response = client.get("/player-summary/bowler/JJ Bumrah")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
```

### 9.3 Manual Test Cases

| Player | Type | Expected Traits |
|--------|------|-----------------|
| V Kohli | Batter | Anchor/Middle overs |
| MS Dhoni | Batter | Finisher/Death specialist |
| JJ Bumrah | Bowler | Death specialist/Wicket-taker |
| R Ashwin | Bowler | Economical/Middle overs |

---

## File Summary

| File | Action | Purpose |
|------|--------|---------|
| `services/player_patterns.py` | **CREATE** | Pattern detection logic (~400 lines) |
| `routers/player_summary.py` | **CREATE** | API endpoint (~200 lines) |
| `src/components/PlayerDNASummary.jsx` | **CREATE** | Frontend component (~180 lines) |
| `src/components/PlayerProfile.jsx` | **MODIFY** | Integrate summary |
| `src/components/BowlerProfile.jsx` | **MODIFY** | Integrate summary |
| `main.py` | **MODIFY** | Register router |

---

## Implementation Order

1. **Day 1**: Create `services/player_patterns.py` with batter patterns
2. **Day 2**: Add bowler patterns, create API endpoint
3. **Day 3**: Build frontend component, integrate
4. **Day 4**: Testing, refinement, caching optimization

---

**Document Version**: 1.0  
**Created**: December 2024  
**Author**: Implementation Spec for Hindsight Cricket Analytics
