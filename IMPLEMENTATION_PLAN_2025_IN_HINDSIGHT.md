# 2025 In Hindsight - Implementation Plan

## Overview

This document outlines the implementation plan for transforming "Wrapped 2025" into "2025 In Hindsight" - a comprehensive cricket analytics experience leveraging the enhanced `delivery_details` dataset (2015+) with advanced metrics including wagon wheel data, delivery details, and predictive metrics.

**Target Audience**: This plan is designed for an LLM or junior developer who needs explicit, step-by-step guidance.

---

## Table of Contents

1. [Phase 1: Naming & Branding Update](#phase-1-naming--branding-update)
2. [Phase 2: Database Schema & Data Exploration](#phase-2-database-schema--data-exploration)
3. [Phase 3: Backend Service - New Metrics](#phase-3-backend-service---new-metrics)
4. [Phase 4: Reusable Visualization Components](#phase-4-reusable-visualization-components)
5. [Phase 5: New Card Implementations](#phase-5-new-card-implementations)
6. [Phase 6: Frontend Integration](#phase-6-frontend-integration)
7. [Testing Checklist](#testing-checklist)

---

## Phase 1: Naming & Branding Update

### 1.1 Backend Router Updates

**File**: `/routers/wrapped.py`

**Changes Required**:
1. Update route prefix from `/wrapped` to `/hindsight` (or keep `/wrapped` for backwards compatibility and add alias)
2. Update all docstrings and comments from "Wrapped 2025" to "2025 In Hindsight"
3. Update the `/2025/metadata` endpoint response:

```python
# BEFORE
return {
    "year": 2025,
    "title": "Hindsight 2025 Wrapped",
    "subtitle": "The Year in Overs",
    ...
}

# AFTER
return {
    "year": 2025,
    "title": "2025 In Hindsight",
    "subtitle": "The Year in Review",
    ...
}
```

### 1.2 Backend Service Updates

**File**: `/services/wrapped.py`

**Changes Required**:
1. Update module docstring from "Wrapped 2025 Service Layer" to "2025 In Hindsight Service Layer"
2. Update `WrappedService` class to `HindsightService` (optional, but cleaner)
3. Update all card titles and subtitles to use "In Hindsight" branding

### 1.3 Frontend Updates

**Files to Update**:
- `/src/components/wrapped/WrappedPage.jsx` - Update loading text, error messages
- `/src/components/wrapped/WrappedHeader.jsx` - Update header title
- `/src/components/wrapped/WrappedStoryContainer.jsx` - Update any "Wrapped" references
- `/src/components/wrapped/wrapped.css` - Consider renaming CSS variables (optional)

**Example Change in WrappedPage.jsx**:
```jsx
// BEFORE
<p>Loading your 2025 Wrapped...</p>

// AFTER
<p>Loading 2025 In Hindsight...</p>
```

### 1.4 Optional: Directory Renaming

Consider renaming directories for clarity:
- `/src/components/wrapped/` → `/src/components/hindsight/`
- `/services/wrapped.py` → `/services/hindsight.py`
- `/routers/wrapped.py` → `/routers/hindsight.py`

**Note**: If renaming, update all imports accordingly.

---

## Phase 2: Database Schema & Data Exploration

### 2.1 Relevant Columns in `delivery_details` Table

The enhanced dataset (2015+) includes these columns we'll use:

```sql
-- Wagon Wheel Data
wagon_x INTEGER,          -- X coordinate (-150 to 150 typical range)
wagon_y INTEGER,          -- Y coordinate (0 to ~250 typical range)  
wagon_zone INTEGER,       -- Zone 0-8 (9 zones around the ground)

-- Delivery Details
line VARCHAR(30),         -- ON_THE_STUMPS, OUTSIDE_OFFSTUMP, OUTSIDE_LEG, etc.
length VARCHAR(30),       -- GOOD_LENGTH, YORKER, FULL, SHORT, BACK_OF_LENGTH, etc.
shot VARCHAR(30),         -- COVER_DRIVE, FLICK, DEFENDED, PULL, SWEEP, etc.
control INTEGER,          -- 0 (uncontrolled) or 1 (controlled)

-- Predictive Metrics
pred_score FLOAT,         -- Expected score (-1 = no data)
win_prob FLOAT,           -- Win probability (-1 = no data)

-- Player/Match Context
bat_hand VARCHAR(10),     -- LHB, RHB
bowl_style VARCHAR(10),   -- RF, RFM, RM, LF, LFM, LM, RO, RL, LO, LC
bowl_kind VARCHAR(30),    -- pace, spin (derived from bowl_style)
inns INTEGER,             -- Innings number (1 or 2)
team_bat VARCHAR,         -- Batting team name
team_bowl VARCHAR,        -- Bowling team name
```

### 2.2 Data Exploration Queries

Before implementing, run these queries to understand data distribution:

```sql
-- Check wagon_zone distribution
SELECT wagon_zone, COUNT(*) as balls, 
       ROUND(SUM(batruns)::numeric / COUNT(*) * 100, 2) as sr
FROM delivery_details 
WHERE wagon_zone IS NOT NULL AND year = 2025
GROUP BY wagon_zone ORDER BY wagon_zone;

-- Check length distribution
SELECT length, COUNT(*) as balls,
       ROUND(SUM(batruns)::numeric / COUNT(*) * 100, 2) as sr
FROM delivery_details 
WHERE length IS NOT NULL AND year = 2025
GROUP BY length ORDER BY balls DESC;

-- Check shot distribution  
SELECT shot, COUNT(*) as balls,
       ROUND(SUM(batruns)::numeric / COUNT(*) * 100, 2) as sr
FROM delivery_details 
WHERE shot IS NOT NULL AND year = 2025
GROUP BY shot ORDER BY balls DESC;

-- Check control distribution
SELECT control, COUNT(*) as balls,
       ROUND(SUM(batruns)::numeric / COUNT(*) * 100, 2) as sr
FROM delivery_details 
WHERE control IS NOT NULL AND year = 2025
GROUP BY control;

-- Check pred_score validity
SELECT COUNT(*) as total,
       SUM(CASE WHEN pred_score >= 0 THEN 1 ELSE 0 END) as valid_pred_score,
       SUM(CASE WHEN win_prob >= 0 THEN 1 ELSE 0 END) as valid_win_prob
FROM delivery_details WHERE year = 2025;

-- Check innings distribution for predictive metrics
SELECT inns, 
       AVG(CASE WHEN pred_score >= 0 THEN pred_score END) as avg_pred_score,
       AVG(CASE WHEN win_prob >= 0 THEN win_prob END) as avg_win_prob
FROM delivery_details WHERE year = 2025
GROUP BY inns;
```

### 2.3 Wagon Zone Mapping

The wagon wheel is divided into 9 zones (0-8). Standard cricket field mapping:

```
Zone Layout (facing bowler's end):
        
       [6]    [7]    [8]
         \    |    /
          \   |   /
    [3] --- Batter --- [5]
          /   |   \
         /    |    \
       [0]    [1]    [2]
              |
           (Bowler)

Zone 0: Fine Leg / Third Man (offside for LHB)
Zone 1: Straight behind
Zone 2: Fine Leg / Third Man (legside for LHB)
Zone 3: Square leg / Point (legside)
Zone 4: Behind wicket (keeper area - usually no zone 4 in most datasets)
Zone 5: Square leg / Point (offside)
Zone 6: Midwicket / Cover (legside)
Zone 7: Straight down ground
Zone 8: Midwicket / Cover (offside)
```

**Important**: The wagon_zone numbering may vary by data source. Verify with actual data before implementing visualizations.

---

## Phase 3: Backend Service - New Metrics

### 3.1 New Service Methods Structure

Add these methods to `/services/wrapped.py` (or new `/services/hindsight.py`):

```python
class HindsightService:
    # Existing methods...
    
    # NEW METHODS TO ADD:
    def get_needle_movers_first_innings(self, ...) -> Dict[str, Any]:
        """Card: Who moves pred_score most in 1st innings"""
        pass
    
    def get_chase_masters(self, ...) -> Dict[str, Any]:
        """Card: Who affects win_prob most in 2nd innings"""
        pass
    
    def get_360_batters(self, ...) -> Dict[str, Any]:
        """Card: Wagon wheel spread analysis"""
        pass
    
    def get_length_masters(self, ...) -> Dict[str, Any]:
        """Card: Scoring vs all lengths"""
        pass
    
    def get_rare_shot_specialists(self, ...) -> Dict[str, Any]:
        """Card: Least played shots & who's best at them"""
        pass
    
    def get_sweep_evolution(self, ...) -> Dict[str, Any]:
        """Card: Sweep/reverse sweep trends 2025 vs historical"""
        pass
    
    def get_controlled_aggression_leaders(self, ...) -> Dict[str, Any]:
        """Card: Controlled aggression metric leaders"""
        pass
    
    def get_batter_hand_breakdown(self, ...) -> Dict[str, Any]:
        """Card: LHB vs RHB analysis with crease combos"""
        pass
    
    def get_bowler_type_dominance(self, ...) -> Dict[str, Any]:
        """Card: Pace vs Spin breakdown by bowling style"""
        pass
```

### 3.2 Metric Calculations - Detailed Specifications

#### 3.2.1 Needle Movers (First Innings)

**Concept**: Identify batters who increase expected score the most while at the crease.

**SQL Logic**:
```sql
WITH batter_stints AS (
    -- Group consecutive balls by the same batter into "stints"
    SELECT 
        bat,
        team_bat,
        p_match,
        inns,
        MIN(pred_score) as start_pred_score,
        MAX(pred_score) as end_pred_score,
        COUNT(*) as balls,
        SUM(batruns) as runs
    FROM delivery_details
    WHERE year = 2025 
    AND inns = 1
    AND pred_score >= 0  -- Valid pred_score only
    GROUP BY bat, team_bat, p_match, inns
),
batter_impact AS (
    SELECT 
        bat,
        team_bat,
        COUNT(*) as innings,
        SUM(balls) as total_balls,
        SUM(runs) as total_runs,
        AVG(end_pred_score - start_pred_score) as avg_pred_score_delta,
        SUM(end_pred_score - start_pred_score) as total_pred_score_added
    FROM batter_stints
    WHERE balls >= 10  -- Minimum balls faced per stint
    GROUP BY bat, team_bat
    HAVING SUM(balls) >= 100  -- Minimum total balls
)
SELECT * FROM batter_impact
ORDER BY avg_pred_score_delta DESC
LIMIT 20;
```

**Metric Output**:
- `avg_pred_score_delta`: Average runs added to expected score per stint
- `total_pred_score_added`: Total expected runs added across all innings
- `pred_score_per_ball`: Average pred_score change per ball faced

**Response Structure**:
```python
{
    "card_id": "needle_movers",
    "card_title": "Needle Movers",
    "card_subtitle": "Who raised the expected score most in 1st innings",
    "visualization_type": "bar_with_delta",
    "players": [
        {
            "name": "Player Name",
            "team": "Team",
            "innings": 15,
            "balls": 450,
            "runs": 580,
            "avg_pred_score_delta": 12.5,
            "pred_score_per_ball": 0.28,
            "strike_rate": 128.9
        },
        ...
    ]
}
```

#### 3.2.2 Chase Masters (Second Innings)

**Concept**: Identify batters who increase win probability most while chasing.

**SQL Logic**:
```sql
WITH chase_impact AS (
    SELECT 
        bat,
        team_bat,
        p_match,
        MIN(win_prob) as start_win_prob,
        MAX(win_prob) as end_win_prob,
        COUNT(*) as balls,
        SUM(batruns) as runs,
        -- Track if they were in when match was won
        MAX(CASE WHEN winner = team_bat THEN 1 ELSE 0 END) as won_from_here
    FROM delivery_details dd
    WHERE year = 2025 
    AND inns = 2
    AND win_prob >= 0  -- Valid win_prob only
    GROUP BY bat, team_bat, p_match, winner
),
aggregated AS (
    SELECT 
        bat,
        team_bat,
        COUNT(*) as chases,
        SUM(balls) as total_balls,
        SUM(runs) as total_runs,
        AVG(end_win_prob - start_win_prob) as avg_win_prob_delta,
        AVG(CASE WHEN start_win_prob < 0.5 THEN end_win_prob - start_win_prob END) as avg_delta_from_behind,
        SUM(won_from_here) as matches_won
    FROM chase_impact
    WHERE balls >= 10
    GROUP BY bat, team_bat
    HAVING SUM(balls) >= 75  -- Lower threshold for chases
)
SELECT * FROM aggregated
ORDER BY avg_win_prob_delta DESC
LIMIT 20;
```

**Response Structure**:
```python
{
    "card_id": "chase_masters", 
    "card_title": "Chase Masters",
    "card_subtitle": "Who swings win probability while chasing",
    "visualization_type": "scatter",
    "x_axis": "start_win_prob",  # Avg situation they came in at
    "y_axis": "avg_win_prob_delta",  # How much they moved it
    "players": [...]
}
```

#### 3.2.3 360 Score (Wagon Wheel Spread)

**Concept**: Measure how evenly a batter scores across all wagon wheel zones. A "360 player" scores in all directions.

**Metric Calculation**:
```python
def calculate_360_score(zone_runs: Dict[int, int], zone_balls: Dict[int, int]) -> float:
    """
    360 Score = 100 - (Standard Deviation of zone run percentages * scaling_factor)
    
    A perfect 360 player has equal run distribution across zones (low std dev = high score)
    A one-dimensional player scores heavily in 1-2 zones (high std dev = low score)
    """
    total_runs = sum(zone_runs.values())
    if total_runs == 0:
        return 0
    
    # Calculate percentage of runs in each zone
    zone_percentages = []
    for zone in range(9):  # Zones 0-8
        pct = (zone_runs.get(zone, 0) / total_runs) * 100
        zone_percentages.append(pct)
    
    # Standard deviation of percentages
    # Perfect distribution = 11.11% per zone (100/9)
    mean_pct = 100 / 9  # 11.11%
    variance = sum((pct - mean_pct) ** 2 for pct in zone_percentages) / 9
    std_dev = variance ** 0.5
    
    # Convert to 0-100 score (lower std_dev = higher score)
    # Max std_dev would be ~33 (all runs in one zone)
    score = max(0, 100 - (std_dev * 3))
    return round(score, 1)
```

**SQL Query**:
```sql
WITH zone_stats AS (
    SELECT 
        bat,
        team_bat,
        wagon_zone,
        COUNT(*) as balls,
        SUM(batruns) as runs,
        SUM(CASE WHEN batruns IN (4,6) THEN 1 ELSE 0 END) as boundaries
    FROM delivery_details
    WHERE year = 2025
    AND wagon_zone IS NOT NULL
    GROUP BY bat, team_bat, wagon_zone
),
player_totals AS (
    SELECT 
        bat,
        team_bat,
        SUM(balls) as total_balls,
        SUM(runs) as total_runs,
        SUM(boundaries) as total_boundaries,
        -- JSON aggregate zone data for processing
        json_agg(json_build_object(
            'zone', wagon_zone,
            'balls', balls,
            'runs', runs
        )) as zone_data
    FROM zone_stats
    GROUP BY bat, team_bat
    HAVING SUM(balls) >= 200  -- Minimum sample
)
SELECT * FROM player_totals
ORDER BY total_runs DESC
LIMIT 50;
```

**Post-Processing in Python**:
Calculate the 360_score for each player from their zone_data JSON.

**Response Structure**:
```python
{
    "card_id": "360_batters",
    "card_title": "360° Batters",
    "card_subtitle": "Who scores all around the ground",
    "visualization_type": "wagon_wheel",  # New component needed
    "players": [
        {
            "name": "Player Name",
            "team": "Team",
            "360_score": 78.5,
            "total_runs": 650,
            "total_balls": 480,
            "zone_breakdown": [
                {"zone": 0, "runs": 45, "balls": 52, "pct": 6.9},
                {"zone": 1, "runs": 80, "balls": 58, "pct": 12.3},
                # ... zones 2-8
            ]
        },
        ...
    ],
    "top_3_wagon_data": [...]  # Detailed data for top 3 to render wagon wheels
}
```

#### 3.2.4 Length Masters

**Concept**: Measure batting versatility against different bowling lengths.

**SQL Query**:
```sql
WITH length_stats AS (
    SELECT 
        bat,
        team_bat,
        length,
        COUNT(*) as balls,
        SUM(batruns) as runs,
        SUM(CASE WHEN batruns IN (4,6) THEN 1 ELSE 0 END) as boundaries,
        SUM(CASE WHEN control = 1 THEN 1 ELSE 0 END) as controlled
    FROM delivery_details
    WHERE year = 2025
    AND length IS NOT NULL
    GROUP BY bat, team_bat, length
),
player_by_length AS (
    SELECT 
        bat,
        team_bat,
        length,
        balls,
        runs,
        ROUND(runs * 100.0 / NULLIF(balls, 0), 2) as strike_rate
    FROM length_stats
),
-- Get global averages per length for comparison
global_length_avg AS (
    SELECT 
        length,
        ROUND(SUM(runs) * 100.0 / NULLIF(SUM(balls), 0), 2) as global_sr
    FROM length_stats
    GROUP BY length
),
player_versatility AS (
    SELECT 
        p.bat,
        p.team_bat,
        SUM(p.balls) as total_balls,
        SUM(p.runs) as total_runs,
        -- Count lengths where player beats global average
        SUM(CASE WHEN p.strike_rate > g.global_sr THEN 1 ELSE 0 END) as lengths_beaten,
        -- Calculate "Length Versatility Score"
        AVG(p.strike_rate - g.global_sr) as avg_sr_vs_global
    FROM player_by_length p
    JOIN global_length_avg g ON p.length = g.length
    GROUP BY p.bat, p.team_bat
    HAVING SUM(p.balls) >= 200
)
SELECT * FROM player_versatility
ORDER BY lengths_beaten DESC, avg_sr_vs_global DESC
LIMIT 20;
```

**Length Versatility Score Calculation**:
```python
def calculate_length_versatility(length_data: List[Dict]) -> float:
    """
    Score based on:
    1. Number of lengths where SR > global average (max 6-7 lengths)
    2. Magnitude of outperformance
    
    Score = (lengths_beaten / total_lengths) * 50 + (avg_sr_delta / 20) * 50
    """
    lengths_beaten = sum(1 for l in length_data if l['sr'] > l['global_sr'])
    total_lengths = len(length_data)
    sr_deltas = [l['sr'] - l['global_sr'] for l in length_data]
    avg_delta = sum(sr_deltas) / len(sr_deltas) if sr_deltas else 0
    
    length_score = (lengths_beaten / total_lengths) * 50
    performance_score = min(50, max(0, (avg_delta / 20) * 50))
    
    return round(length_score + performance_score, 1)
```

**Response Structure**:
```python
{
    "card_id": "length_masters",
    "card_title": "Length Masters", 
    "card_subtitle": "Who scores against any length",
    "visualization_type": "heatmap_comparison",
    "length_order": ["YORKER", "FULL", "GOOD_LENGTH", "BACK_OF_LENGTH", "SHORT"],
    "global_averages": {
        "YORKER": 110.5,
        "FULL": 142.3,
        "GOOD_LENGTH": 118.7,
        "BACK_OF_LENGTH": 125.4,
        "SHORT": 155.2
    },
    "players": [
        {
            "name": "Player Name",
            "team": "Team",
            "versatility_score": 82.5,
            "length_breakdown": {
                "YORKER": {"balls": 45, "runs": 52, "sr": 115.6},
                "FULL": {"balls": 120, "runs": 185, "sr": 154.2},
                # ... other lengths
            }
        },
        ...
    ]
}
```

#### 3.2.5 Rare Shot Specialists

**Concept**: Find the least played shots in 2025 and identify who's best at them.

**SQL Query**:
```sql
-- Step 1: Find rare shots (bottom 20% by frequency)
WITH shot_frequency AS (
    SELECT 
        shot,
        COUNT(*) as total_plays,
        SUM(batruns) as total_runs,
        ROUND(SUM(batruns) * 100.0 / NULLIF(COUNT(*), 0), 2) as global_sr
    FROM delivery_details
    WHERE year = 2025 AND shot IS NOT NULL
    GROUP BY shot
),
rare_shots AS (
    SELECT shot, total_plays, total_runs, global_sr
    FROM shot_frequency
    WHERE total_plays < (SELECT PERCENTILE_CONT(0.3) WITHIN GROUP (ORDER BY total_plays) FROM shot_frequency)
    ORDER BY total_plays ASC
),
-- Step 2: Find players who play these rare shots well
player_rare_shots AS (
    SELECT 
        d.bat,
        d.team_bat,
        d.shot,
        COUNT(*) as plays,
        SUM(d.batruns) as runs,
        ROUND(SUM(d.batruns) * 100.0 / NULLIF(COUNT(*), 0), 2) as player_sr,
        r.global_sr,
        ROUND(SUM(d.batruns) * 100.0 / NULLIF(COUNT(*), 0) - r.global_sr, 2) as sr_vs_global
    FROM delivery_details d
    JOIN rare_shots r ON d.shot = r.shot
    WHERE d.year = 2025
    GROUP BY d.bat, d.team_bat, d.shot, r.global_sr
    HAVING COUNT(*) >= 10  -- Minimum plays of this shot
)
SELECT * FROM player_rare_shots
ORDER BY sr_vs_global DESC
LIMIT 30;
```

**Response Structure**:
```python
{
    "card_id": "rare_shot_specialists",
    "card_title": "Rare Shot Specialists",
    "card_subtitle": "Masters of cricket's forgotten art",
    "visualization_type": "grouped_bar",
    "rare_shots": [
        {
            "shot": "UPPER_CUT",
            "global_plays": 1234,
            "global_sr": 125.5,
            "specialists": [
                {"name": "Player A", "team": "Team", "plays": 45, "sr": 178.2},
                {"name": "Player B", "team": "Team", "plays": 38, "sr": 165.8}
            ]
        },
        # ... more rare shots
    ]
}
```

#### 3.2.6 Sweep Evolution

**Concept**: Compare sweep/reverse sweep efficacy in 2025 vs historical years.

**SQL Query**:
```sql
WITH sweep_stats AS (
    SELECT 
        year,
        bat,
        team_bat,
        shot,
        COUNT(*) as plays,
        SUM(batruns) as runs,
        SUM(CASE WHEN dismissal IS NOT NULL THEN 1 ELSE 0 END) as dismissals,
        SUM(CASE WHEN control = 1 THEN 1 ELSE 0 END) as controlled
    FROM delivery_details
    WHERE shot IN ('SWEEP', 'REVERSE_SWEEP', 'SLOG_SWEEP', 'PADDLE_SWEEP')
    AND year >= 2020  -- Last 5 years for trend
    GROUP BY year, bat, team_bat, shot
),
yearly_totals AS (
    SELECT 
        year,
        shot,
        SUM(plays) as total_plays,
        SUM(runs) as total_runs,
        SUM(dismissals) as total_dismissals,
        ROUND(SUM(runs) * 100.0 / NULLIF(SUM(plays), 0), 2) as sr,
        ROUND(SUM(plays)::numeric / NULLIF(SUM(dismissals), 0), 2) as balls_per_dismissal
    FROM sweep_stats
    GROUP BY year, shot
),
player_2025_sweeps AS (
    SELECT 
        bat,
        team_bat,
        SUM(plays) as sweep_plays,
        SUM(runs) as sweep_runs,
        ROUND(SUM(runs) * 100.0 / NULLIF(SUM(plays), 0), 2) as sweep_sr,
        ROUND(SUM(controlled) * 100.0 / NULLIF(SUM(plays), 0), 2) as sweep_control_pct
    FROM sweep_stats
    WHERE year = 2025
    GROUP BY bat, team_bat
    HAVING SUM(plays) >= 20
)
SELECT * FROM player_2025_sweeps
ORDER BY sweep_sr DESC
LIMIT 20;
```

**Response Structure**:
```python
{
    "card_id": "sweep_evolution",
    "card_title": "Sweep Revolution",
    "card_subtitle": "The rise of the sweep shot",
    "visualization_type": "line_with_leaders",
    "yearly_trends": [
        {"year": 2020, "SWEEP": {"plays": 5000, "sr": 115.2}, "REVERSE_SWEEP": {...}},
        {"year": 2021, ...},
        # ... up to 2025
    ],
    "2025_leaders": [
        {
            "name": "Player Name",
            "team": "Team",
            "sweep_plays": 45,
            "sweep_sr": 168.9,
            "sweep_control_pct": 78.5
        },
        ...
    ]
}
```

#### 3.2.7 Controlled Aggression Metric

**Concept**: Composite metric combining control%, strike rate, boundary%, and dot%.

**Formula**:
```python
def calculate_controlled_aggression(
    control_pct: float,    # 0-100
    strike_rate: float,    # Typically 100-200
    boundary_pct: float,   # 0-30 typically  
    dot_pct: float         # 20-50 typically
) -> float:
    """
    Controlled Aggression Score = 
        (Control% * 0.25) +                    # Max ~25 points
        ((SR - 100) / 2 * 0.35) +              # Max ~35 points (if SR=170)
        (Boundary% * 1.0 * 0.25) +             # Max ~25 points (if boundary=25%)
        ((50 - Dot%) * 0.3 * 0.15)             # Max ~15 points (if dot=0%)
    
    Normalized to 0-100 scale.
    """
    control_score = control_pct * 0.25
    sr_score = max(0, (strike_rate - 100) / 2) * 0.35
    boundary_score = boundary_pct * 1.0 * 0.25
    dot_score = max(0, (50 - dot_pct) * 0.3) * 0.15
    
    raw_score = control_score + sr_score + boundary_score + dot_score
    # Normalize to 0-100 (max theoretical ~100)
    return min(100, round(raw_score, 1))
```

**SQL Query**:
```sql
WITH player_stats AS (
    SELECT 
        bat,
        team_bat,
        COUNT(*) as balls,
        SUM(batruns) as runs,
        SUM(CASE WHEN batruns = 0 AND wide = 0 AND noball = 0 THEN 1 ELSE 0 END) as dots,
        SUM(CASE WHEN batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
        SUM(CASE WHEN control = 1 THEN 1 ELSE 0 END) as controlled_shots,
        SUM(CASE WHEN control IS NOT NULL THEN 1 ELSE 0 END) as control_data_balls
    FROM delivery_details
    WHERE year = 2025
    GROUP BY bat, team_bat
    HAVING COUNT(*) >= 150  -- Minimum balls
),
calculated AS (
    SELECT 
        bat,
        team_bat,
        balls,
        runs,
        ROUND(runs * 100.0 / balls, 2) as strike_rate,
        ROUND(dots * 100.0 / balls, 2) as dot_pct,
        ROUND(boundaries * 100.0 / balls, 2) as boundary_pct,
        ROUND(controlled_shots * 100.0 / NULLIF(control_data_balls, 0), 2) as control_pct
    FROM player_stats
)
SELECT * FROM calculated
ORDER BY strike_rate DESC
LIMIT 50;  -- Get top 50, calculate CA score in Python
```

**Response Structure**:
```python
{
    "card_id": "controlled_aggression",
    "card_title": "Controlled Chaos",
    "card_subtitle": "The most efficient aggressors",
    "visualization_type": "radar_comparison",
    "metric_weights": {
        "control_pct": 0.25,
        "strike_rate": 0.35,
        "boundary_pct": 0.25,
        "dot_pct": 0.15
    },
    "players": [
        {
            "name": "Player Name",
            "team": "Team",
            "ca_score": 78.5,
            "balls": 450,
            "strike_rate": 145.2,
            "control_pct": 72.5,
            "boundary_pct": 18.5,
            "dot_pct": 28.3
        },
        ...
    ]
}
```

#### 3.2.8 Batter Hand Breakdown & Crease Combos

**Concept**: Analyze performance by batter handedness and crease combinations.

**SQL Query**:
```sql
-- Part 1: Overall LHB vs RHB
WITH hand_stats AS (
    SELECT 
        bat_hand,
        COUNT(*) as balls,
        SUM(batruns) as runs,
        SUM(CASE WHEN dismissal IS NOT NULL THEN 1 ELSE 0 END) as wickets,
        SUM(CASE WHEN batruns IN (4,6) THEN 1 ELSE 0 END) as boundaries,
        SUM(CASE WHEN control = 1 THEN 1 ELSE 0 END) as controlled
    FROM delivery_details
    WHERE year = 2025 AND bat_hand IS NOT NULL
    GROUP BY bat_hand
),

-- Part 2: Crease combo analysis
crease_stats AS (
    SELECT 
        crease_combo,
        COUNT(*) as balls,
        SUM(batruns) as runs,
        SUM(CASE WHEN dismissal IS NOT NULL THEN 1 ELSE 0 END) as wickets,
        ROUND(SUM(batruns) * 100.0 / NULLIF(COUNT(*), 0), 2) as sr
    FROM delivery_details
    WHERE year = 2025 
    AND crease_combo IS NOT NULL
    -- Only valid combos
    AND crease_combo IN ('LHB_LHB', 'RHB_RHB', 'LHB_RHB', 'RHB_LHB')
    GROUP BY crease_combo
),

-- Part 3: Top performers by hand
top_by_hand AS (
    SELECT 
        bat_hand,
        bat,
        team_bat,
        COUNT(*) as balls,
        SUM(batruns) as runs,
        ROUND(SUM(batruns) * 100.0 / NULLIF(COUNT(*), 0), 2) as sr,
        ROW_NUMBER() OVER (PARTITION BY bat_hand ORDER BY SUM(batruns) DESC) as rn
    FROM delivery_details
    WHERE year = 2025 AND bat_hand IS NOT NULL
    GROUP BY bat_hand, bat, team_bat
    HAVING COUNT(*) >= 100
)
SELECT * FROM top_by_hand WHERE rn <= 5;
```

**Response Structure**:
```python
{
    "card_id": "batter_hand_breakdown",
    "card_title": "Lefty vs Righty",
    "card_subtitle": "The handedness battle of 2025",
    "visualization_type": "comparison_with_crease",
    "hand_comparison": {
        "LHB": {
            "balls": 125000,
            "runs": 156000,
            "strike_rate": 124.8,
            "average": 28.5,
            "boundary_pct": 14.2
        },
        "RHB": {
            "balls": 375000,
            "runs": 478000,
            "strike_rate": 127.5,
            "average": 30.2,
            "boundary_pct": 15.1
        }
    },
    "crease_combos": [
        {"combo": "LHB_LHB", "balls": 25000, "sr": 122.5, "label": "Both Left"},
        {"combo": "RHB_RHB", "balls": 200000, "sr": 128.2, "label": "Both Right"},
        {"combo": "LHB_RHB", "balls": 150000, "sr": 126.8, "label": "Mixed"}
    ],
    "top_lhb": [...],
    "top_rhb": [...]
}
```

#### 3.2.9 Bowler Type Dominance

**Concept**: Analyze bowling performance by pace vs spin, broken down by specific bowling styles.

**SQL Query**:
```sql
WITH bowl_type_stats AS (
    SELECT 
        bowl_kind,  -- 'pace' or 'spin'
        bowl_style, -- RF, RFM, RM, LF, LFM, LM, RO, RL, LO, LC
        bowl,
        team_bowl,
        COUNT(*) as balls,
        SUM(score) as runs,
        SUM(CASE WHEN dismissal IS NOT NULL AND dismissal != '' THEN 1 ELSE 0 END) as wickets,
        SUM(CASE WHEN batruns = 0 AND wide = 0 AND noball = 0 THEN 1 ELSE 0 END) as dots
    FROM delivery_details
    WHERE year = 2025
    AND bowl_kind IS NOT NULL
    GROUP BY bowl_kind, bowl_style, bowl, team_bowl
),

-- Aggregate by kind (pace/spin)
kind_totals AS (
    SELECT 
        bowl_kind,
        SUM(balls) as total_balls,
        SUM(runs) as total_runs,
        SUM(wickets) as total_wickets,
        SUM(dots) as total_dots,
        ROUND(SUM(runs) * 6.0 / NULLIF(SUM(balls), 0), 2) as economy,
        ROUND(SUM(balls)::numeric / NULLIF(SUM(wickets), 0), 2) as strike_rate
    FROM bowl_type_stats
    GROUP BY bowl_kind
),

-- Top bowlers per style
top_by_style AS (
    SELECT 
        bowl_kind,
        bowl_style,
        bowl,
        team_bowl,
        balls,
        runs,
        wickets,
        ROUND(runs * 6.0 / NULLIF(balls, 0), 2) as economy,
        ROUND(dots * 100.0 / NULLIF(balls, 0), 2) as dot_pct,
        ROW_NUMBER() OVER (
            PARTITION BY bowl_style 
            ORDER BY wickets DESC, runs * 6.0 / NULLIF(balls, 0) ASC
        ) as rn
    FROM bowl_type_stats
    WHERE balls >= 100
)
SELECT * FROM top_by_style WHERE rn <= 3;
```

**Response Structure**:
```python
{
    "card_id": "bowler_type_dominance",
    "card_title": "Pace vs Spin",
    "card_subtitle": "The bowling arms race of 2025",
    "visualization_type": "treemap_with_leaders",
    "kind_comparison": {
        "pace": {
            "balls": 350000,
            "wickets": 8500,
            "economy": 8.2,
            "strike_rate": 24.5,
            "dot_pct": 38.2
        },
        "spin": {
            "balls": 150000,
            "wickets": 3200,
            "economy": 7.8,
            "strike_rate": 28.1,
            "dot_pct": 35.5
        }
    },
    "style_breakdown": [
        {
            "style": "RF",
            "label": "Right Fast",
            "kind": "pace",
            "balls": 85000,
            "economy": 8.5,
            "top_bowler": {"name": "Bowler A", "wickets": 45}
        },
        {
            "style": "RO",
            "label": "Right Off-spin",
            "kind": "spin",
            "balls": 45000,
            "economy": 7.6,
            "top_bowler": {"name": "Bowler B", "wickets": 32}
        },
        # ... all styles
    ]
}
```

---

## Phase 4: Reusable Visualization Components

### 4.1 Wagon Wheel Component

**File**: `/src/components/common/WagonWheel.jsx`

**Purpose**: Reusable wagon wheel visualization showing run distribution by zone.

**Component Props**:
```javascript
WagonWheel.propTypes = {
    // Zone data: [{zone: 0, runs: 45, balls: 52, pct: 6.9}, ...]
    zoneData: PropTypes.array.isRequired,
    
    // Player name for labeling
    playerName: PropTypes.string,
    
    // Size variant
    size: PropTypes.oneOf(['small', 'medium', 'large']),
    
    // Show percentages or raw runs
    displayMode: PropTypes.oneOf(['percentage', 'runs', 'sr']),
    
    // Color scheme
    colorScale: PropTypes.oneOf(['heat', 'green', 'blue']),
    
    // Interactive hover
    interactive: PropTypes.bool
};
```

**Implementation Approach**:
1. Use SVG for the cricket field outline
2. Draw 9 zones as pie slices
3. Color intensity based on run distribution
4. Optional: Plot individual wagon_x/wagon_y points for detailed view

**Key SVG Structure**:
```jsx
<svg viewBox="-150 -20 300 280">
    {/* Field boundary */}
    <ellipse cx="0" cy="130" rx="140" ry="130" fill="#2d5a2d" stroke="#fff"/>
    
    {/* Zone segments */}
    {zones.map(zone => (
        <path 
            key={zone.id}
            d={calculateZonePath(zone.id)}
            fill={getZoneColor(zone.pct)}
            opacity={0.7}
        />
    ))}
    
    {/* Pitch rectangle */}
    <rect x="-5" y="100" width="10" height="40" fill="#c4a76c"/>
    
    {/* Zone labels */}
    {zones.map(zone => (
        <text key={zone.id} x={zone.labelX} y={zone.labelY}>
            {displayMode === 'percentage' ? `${zone.pct}%` : zone.runs}
        </text>
    ))}
</svg>
```

### 4.2 Controlled Aggression Radar Component

**File**: `/src/components/common/ControlledAggressionRadar.jsx`

**Purpose**: Radar/spider chart showing the 4 components of the CA metric.

**Implementation**: Use Recharts `RadarChart` with custom styling.

```jsx
import { RadarChart, PolarGrid, PolarAngleAxis, Radar } from 'recharts';

const ControlledAggressionRadar = ({ player, showComparison, comparisonData }) => {
    const data = [
        { metric: 'Control %', value: normalizeControl(player.control_pct), fullMark: 100 },
        { metric: 'Strike Rate', value: normalizeSR(player.strike_rate), fullMark: 100 },
        { metric: 'Boundary %', value: normalizeBoundary(player.boundary_pct), fullMark: 100 },
        { metric: 'Anti-Dot', value: normalizeAntiDot(player.dot_pct), fullMark: 100 }
    ];
    
    return (
        <RadarChart data={data}>
            <PolarGrid />
            <PolarAngleAxis dataKey="metric" />
            <Radar dataKey="value" fill="#1DB954" fillOpacity={0.6} />
            {showComparison && (
                <Radar dataKey="comparison" fill="#666" fillOpacity={0.3} />
            )}
        </RadarChart>
    );
};
```

### 4.3 Length Heatmap Component

**File**: `/src/components/common/LengthHeatmap.jsx`

**Purpose**: Show player's SR vs global SR for each length as a heatmap row.

**Implementation**:
```jsx
const LengthHeatmap = ({ playerData, globalAverages, lengths }) => {
    const getColor = (playerSR, globalSR) => {
        const delta = playerSR - globalSR;
        if (delta > 20) return '#1DB954';  // Strong green
        if (delta > 0) return '#4CAF50';   // Light green
        if (delta > -20) return '#ff9800'; // Orange
        return '#f44336';                   // Red
    };
    
    return (
        <Box className="length-heatmap">
            {lengths.map(length => {
                const player = playerData[length] || { sr: 0, balls: 0 };
                const global = globalAverages[length];
                return (
                    <Box 
                        key={length}
                        className="heatmap-cell"
                        sx={{ backgroundColor: getColor(player.sr, global) }}
                    >
                        <Typography variant="caption">{length}</Typography>
                        <Typography variant="body2">{player.sr}</Typography>
                        <Typography variant="caption">
                            ({player.sr > global ? '+' : ''}{(player.sr - global).toFixed(1)})
                        </Typography>
                    </Box>
                );
            })}
        </Box>
    );
};
```

### 4.4 Crease Combo Visualization

**File**: `/src/components/common/CreaseComboViz.jsx`

**Purpose**: Visual representation of crease combinations with performance stats.

**Implementation**: Simple bar comparison with icons.

```jsx
const CreaseComboViz = ({ comboData }) => {
    const comboLabels = {
        'lhb_lhb': { label: 'L + L', icons: ['🫲', '🫲'] },
        'rhb_rhb': { label: 'R + R', icons: ['🫱', '🫱'] },
        'lhb_rhb': { label: 'L + R', icons: ['🫲', '🫱'] }
    };
    
    return (
        <Box className="crease-combo-viz">
            {comboData.map(combo => (
                <Box key={combo.combo} className="combo-item">
                    <Box className="combo-icons">
                        {comboLabels[combo.combo.toLowerCase()]?.icons.map((icon, i) => (
                            <span key={i}>{icon}</span>
                        ))}
                    </Box>
                    <Typography>{combo.label}</Typography>
                    <Typography variant="h6">{combo.sr} SR</Typography>
                    <Typography variant="caption">{combo.balls.toLocaleString()} balls</Typography>
                </Box>
            ))}
        </Box>
    );
};
```

---

## Phase 5: New Card Implementations

### 5.1 Card Component File Structure

Create new files in `/src/components/wrapped/cards/`:

```
cards/
├── IntroCard.jsx           (existing)
├── PowerplayBulliesCard.jsx (existing)
├── ...                     (existing cards)
├── NeedleMoversCard.jsx    (NEW)
├── ChaseMastersCard.jsx    (NEW)
├── ThreeSixtyBattersCard.jsx (NEW)
├── LengthMastersCard.jsx   (NEW)
├── RareShotCard.jsx        (NEW)
├── SweepEvolutionCard.jsx  (NEW)
├── ControlledAggressionCard.jsx (NEW)
├── BatterHandCard.jsx      (NEW)
├── BowlerTypeDominanceCard.jsx (NEW)
└── index.js                (update exports)
```

### 5.2 Card Registration

Update `/src/components/wrapped/WrappedCard.jsx`:

```javascript
import NeedleMoversCard from './cards/NeedleMoversCard';
import ChaseMastersCard from './cards/ChaseMastersCard';
import ThreeSixtyBattersCard from './cards/ThreeSixtyBattersCard';
// ... import other new cards

const cardComponents = {
    // Existing
    'intro': IntroCard,
    'powerplay_bullies': PowerplayBulliesCard,
    // ... existing cards
    
    // NEW CARDS
    'needle_movers': NeedleMoversCard,
    'chase_masters': ChaseMastersCard,
    '360_batters': ThreeSixtyBattersCard,
    'length_masters': LengthMastersCard,
    'rare_shot_specialists': RareShotCard,
    'sweep_evolution': SweepEvolutionCard,
    'controlled_aggression': ControlledAggressionCard,
    'batter_hand_breakdown': BatterHandCard,
    'bowler_type_dominance': BowlerTypeDominanceCard,
};
```

### 5.3 Backend Card Registration

Update `/services/wrapped.py` `get_all_cards()`:

```python
def get_all_cards(self, ...):
    cards = []
    
    # Existing cards
    cards.append(self.get_intro_card_data(...))
    # ...
    
    # NEW CARDS - Add in desired order
    try:
        cards.append(self.get_needle_movers_first_innings(...))
    except Exception as e:
        logger.error(f"Error fetching needle movers: {e}")
        cards.append({"card_id": "needle_movers", "error": str(e)})
    
    try:
        cards.append(self.get_chase_masters(...))
    except Exception as e:
        logger.error(f"Error fetching chase masters: {e}")
        cards.append({"card_id": "chase_masters", "error": str(e)})
    
    # ... add other new cards
    
    return {...}
```

### 5.4 Metadata Update

Update `/routers/wrapped.py` `get_wrapped_metadata()`:

```python
"cards": [
    # Existing cards...
    
    # NEW CARDS
    {
        "id": "needle_movers",
        "title": "Needle Movers",
        "subtitle": "Who raised the expected score most",
        "order": 10
    },
    {
        "id": "chase_masters",
        "title": "Chase Masters", 
        "subtitle": "Win probability swing kings",
        "order": 11
    },
    {
        "id": "360_batters",
        "title": "360° Batters",
        "subtitle": "Scoring all around the ground",
        "order": 12
    },
    # ... other new cards
]
```

---

## Phase 6: Frontend Integration

### 6.1 Example: NeedleMoversCard Implementation

**File**: `/src/components/wrapped/cards/NeedleMoversCard.jsx`

```jsx
import React from 'react';
import { Box, Typography } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import TeamBadge from '../TeamBadge';

const NeedleMoversCard = ({ data }) => {
    if (!data.players || data.players.length === 0) {
        return <Typography>No needle mover data available</Typography>;
    }

    const chartData = data.players.slice(0, 10).map(p => ({
        name: p.name,
        team: p.team,
        delta: p.avg_pred_score_delta,
        runs: p.runs,
        balls: p.balls,
        sr: p.strike_rate
    }));

    const handlePlayerClick = (playerName) => {
        const url = `/player?name=${encodeURIComponent(playerName)}&start_date=2025-01-01&end_date=2025-12-31&autoload=true`;
        window.open(url, '_blank', 'noopener,noreferrer');
    };

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const player = payload[0].payload;
            return (
                <Box className="wrapped-tooltip">
                    <Typography variant="subtitle2">
                        {player.name} <TeamBadge team={player.team} />
                    </Typography>
                    <Typography variant="body2">Avg Pred Score Δ: +{player.delta.toFixed(1)}</Typography>
                    <Typography variant="body2">{player.runs} runs @ {player.sr} SR</Typography>
                </Box>
            );
        }
        return null;
    };

    return (
        <Box className="needle-movers-content">
            {/* Hero stat */}
            <Box className="intro-stat-hero">
                <Typography variant="h3" sx={{ color: '#1DB954', fontWeight: 700 }}>
                    +{data.players[0]?.avg_pred_score_delta?.toFixed(1)}
                </Typography>
                <Typography variant="caption" sx={{ color: '#b3b3b3' }}>
                    runs added to expected score per innings
                </Typography>
            </Box>

            {/* Top 3 */}
            <Box className="top-players-list">
                {data.players.slice(0, 3).map((player, index) => (
                    <Box 
                        key={player.name}
                        className="top-player-item"
                        onClick={() => handlePlayerClick(player.name)}
                    >
                        <Typography variant="h5" className="rank">#{index + 1}</Typography>
                        <Box className="player-info">
                            <Typography variant="subtitle1" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                {player.name}
                                <TeamBadge team={player.team} />
                            </Typography>
                            <Typography variant="body2">
                                +{player.avg_pred_score_delta.toFixed(1)} pred score | {player.innings} innings
                            </Typography>
                        </Box>
                    </Box>
                ))}
            </Box>

            {/* Bar Chart */}
            <Box className="scatter-chart">
                <ResponsiveContainer width="100%" height={150}>
                    <BarChart data={chartData} layout="vertical" margin={{ left: 60, right: 10 }}>
                        <XAxis type="number" tick={{ fontSize: 10, fill: '#b3b3b3' }} />
                        <YAxis 
                            type="category" 
                            dataKey="name" 
                            tick={{ fontSize: 9, fill: '#b3b3b3' }}
                            width={60}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar 
                            dataKey="delta" 
                            fill="#1DB954"
                            cursor="pointer"
                            onClick={(data) => handlePlayerClick(data.name)}
                        >
                            {chartData.map((entry, index) => (
                                <Cell 
                                    key={index}
                                    fill={index < 3 ? '#1DB954' : '#666'}
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </Box>
        </Box>
    );
};

export default NeedleMoversCard;
```

### 6.2 CSS Additions

Add to `/src/components/wrapped/wrapped.css`:

```css
/* ============================================
   Needle Movers Card
   ============================================ */

.needle-movers-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    align-items: center;
}

/* ============================================
   360 Batters Card (Wagon Wheel)
   ============================================ */

.wagon-wheel-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.wagon-wheel-container {
    width: 100%;
    max-width: 280px;
    margin: 0 auto;
}

.wagon-wheel-legend {
    display: flex;
    justify-content: center;
    gap: 16px;
    flex-wrap: wrap;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
}

.legend-color {
    width: 12px;
    height: 12px;
    border-radius: 2px;
}

/* ============================================
   Length Masters Card (Heatmap)
   ============================================ */

.length-heatmap-content {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.length-heatmap-row {
    display: flex;
    gap: 4px;
    justify-content: center;
}

.heatmap-cell {
    padding: 8px 6px;
    border-radius: 4px;
    text-align: center;
    min-width: 50px;
}

/* ============================================
   Crease Combo Visualization
   ============================================ */

.crease-combo-container {
    display: flex;
    justify-content: center;
    gap: 16px;
}

.combo-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 12px;
    background: var(--wrapped-card-bg);
    border-radius: 8px;
    min-width: 80px;
}

.combo-icons {
    font-size: 24px;
    display: flex;
    gap: 4px;
}
```

---

## Testing Checklist

### Backend Testing

- [ ] Run data exploration queries to verify column availability
- [ ] Test each new service method individually with sample data
- [ ] Verify SQL queries handle NULL values gracefully
- [ ] Test with empty result sets (no data matching filters)
- [ ] Verify JSON serialization of all response structures
- [ ] Load test with full date range

### Frontend Testing

- [ ] Each new card renders without errors
- [ ] Tooltips work on all interactive elements
- [ ] Player click-through navigation works
- [ ] Mobile responsiveness (360px, 414px, 768px breakpoints)
- [ ] Safari-specific testing (especially for wagon wheel SVG)
- [ ] PNG export functionality with new cards
- [ ] Deep linking to specific cards works

### Integration Testing

- [ ] Full wrapped experience flows through all cards
- [ ] API response times acceptable (<2s per card)
- [ ] Error states display correctly for failed cards
- [ ] Progress bar reflects correct number of cards
- [ ] Swiping/navigation works with new card count

---

## Implementation Order Recommendation

1. **Phase 1**: Branding updates (low risk, high visibility)
2. **Phase 2**: Data exploration (understand what's possible)
3. **Phase 3.1-3.2**: Needle Movers + Chase Masters (predictive metrics)
4. **Phase 4.1**: Wagon Wheel component (reusable, needed for 360 batters)
5. **Phase 3.3 + 5**: 360 Batters card (uses wagon wheel)
6. **Phase 3.7 + 4.2**: Controlled Aggression (composite metric + radar)
7. **Phase 3.4 + 4.3**: Length Masters (length analysis + heatmap)
8. **Phase 3.8 + 4.4**: Batter Hand Breakdown (crease combo viz)
9. **Phase 3.9**: Bowler Type Dominance (treemap)
10. **Phase 3.5-3.6**: Rare Shots + Sweep Evolution (shot analysis)

---

## Notes for Implementer

1. **Always query year = 2025** for the main metrics unless doing historical comparison
2. **Handle -1 values** in pred_score and win_prob as "no data available"
3. **Normalize crease_combo** to lowercase and treat RHB_LHB same as LHB_RHB
4. **Cache wagon wheel zone paths** - they're static geometry
5. **Use existing TeamBadge component** for team display consistency
6. **Follow existing card patterns** for consistent UX
7. **Test SQL queries in psql first** before implementing in Python
8. **Use the query_builder_v2.py patterns** for building WHERE clauses

---

*Last Updated: December 2025*
*Author: Claude (Implementation Planning)*
