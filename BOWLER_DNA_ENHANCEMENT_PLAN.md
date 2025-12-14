# Bowler DNA Summary Enhancement Plan

> **Goal**: Improve the bowler DNA summary to provide more insightful, data-driven analysis with specific numbers and contextual matchup information.
>
> **Target Developer Level**: Junior (detailed step-by-step guidance included)
>
> **Estimated Effort**: 2-3 days

---

## Table of Contents

1. [Current Issues](#1-current-issues)
2. [Database Schema Reference](#2-database-schema-reference)
3. [Enhancement Overview](#3-enhancement-overview)
4. [Implementation Steps](#4-implementation-steps)
5. [Testing Checklist](#5-testing-checklist)

---

## 1. Current Issues

### Issue 1: Primary Phase - Missing Wicket Stats
**Current Output:**
> "DL Chahar predominantly operates in the powerplay phase, bowling 76.9% of his overs during this critical period."

**Problem:** Only shows % of overs, but doesn't tell us HOW EFFECTIVE the bowler is in that phase.

**Desired Output:**
> "DL Chahar is a powerplay specialist (76.9% of overs), taking 65% of his wickets in this phase with an economy of 6.31 and SR of 18.2."

---

### Issue 2: Bowling Profile - Vague Description
**Current Output:**
> "He is classified as an impact bowler, capable of delivering match-winning spells that can change the course of a game."

**Problem:** This is generic marketing speak with no numbers. Meaningless for analysis.

**Desired Output:**
> "Wicket-taker profile with SR 22.3 and 39.9% dots - takes a wicket every 3.7 overs on average."

---

### Issue 3: Dominance - Unclear Metric & Missing Matchup Data
**Current Output:**
> "No specific strengths listed, but his ability to take wickets is evident with a wicket haul percentage of 26.2%."

**Problems:**
1. "wicket haul percentage" is not a standard cricket term and is confusing
2. Missing analysis of performance vs different crease combinations (RR, RL, LR, LL)
3. Missing batter handedness analysis

**Desired Output:**
> "Dominates vs Right-Right crease combo (Econ 6.8, SR 16.2) - excels when both batters are right-handed. Also strong in powerplay (Econ 6.31, 53.8% dots)."

---

### Issue 4: Vulnerability - Missing Contextual Details
**Current Output:**
> "In the death overs, he struggles with an economy of 10.59 across 19.1 overs, indicating a significant weakness in this phase."

**Problem:** Missing analysis of:
- Which crease combinations cause problems
- Batter handedness matchups (important for spinners especially)
- Ball direction effectiveness

**Desired Output:**
> "Struggles in death overs (Econ 10.59) and vs Left-Right crease combos (Econ 9.2) where ball moves away from the left-hander."

---

### Issue 5: Usage Pattern - Not Reading Available Data
**Current Output:**
> "His typical overs are not specified, but he is primarily utilized in the early stages of the innings."

**Problem:** The `over_stats` data IS available (Over 0: 53 times, Over 2: 49 times, etc.) but the pattern detection code isn't processing it correctly.

**Desired Output:**
> "Primary overs: 1st, 3rd, and 5th - bowls the 1st over in 86.9% of matches. Most common spell: overs 1, 3, 5, 7."

---

## 2. Database Schema Reference

### Key Columns in `deliveries` Table

These columns are already populated and available for querying:

```python
# From models.py - Delivery class

# Batter type at striker's end
striker_batter_type = Column(String(10), nullable=True)
# Values: "RHB" (Right Hand Bat), "LHB" (Left Hand Bat)

# Batter type at non-striker's end  
non_striker_batter_type = Column(String(10), nullable=True)
# Values: "RHB", "LHB"

# Bowler's bowling type
bowler_type = Column(String(10), nullable=True)
# Values: "RF", "RFM", "RM", "LF", "LFM", "LM", "RO", "RL", "LO", "LC"

# Combination of striker + non-striker handedness
crease_combo = Column(String(20), nullable=True)
# Values: "Right-Right", "Right-Left", "Left-Right", "Left-Left"
# Format: "{striker_hand}-{non_striker_hand}"

# Direction ball moves relative to striker
ball_direction = Column(String(20), nullable=True)
# Values: "intoBatter", "awayFromBatter", "straight"
# Determined by bowler type + striker handedness
```

### How to Query These (Reference from query_builder.py)

```python
# Filter by crease combo
conditions.append("d.crease_combo = :crease_combo")
params["crease_combo"] = "Right-Right"

# Filter by ball direction
conditions.append("d.ball_direction = :ball_direction")
params["ball_direction"] = "intoBatter"

# Filter by striker batter type
conditions.append("d.striker_batter_type = :striker_batter_type")
params["striker_batter_type"] = "RHB"
```

---

## 3. Enhancement Overview

### New Data to Extract

We need to add the following to the bowler pattern detection:

| Category | New Fields | Source |
|----------|------------|--------|
| Phase Stats | wickets_percentage, phase_economy, phase_sr, phase_dots | `/player/{name}/bowling_stats` |
| Crease Combo | stats for RR, RL, LR, LL combinations | New query on `deliveries` |
| Ball Direction | stats for intoBatter, awayFromBatter | New query on `deliveries` |
| Over Usage | top_overs list with frequencies, most_common_spell | `over_stats` from bowling endpoint |

### Files to Modify

1. **`services/player_patterns.py`** - Add new pattern detection functions
2. **`routers/player_summary.py`** - Update bowler endpoint to fetch additional data
3. **`routers/player_summary.py`** - Update prompts and fallback summary

---

## 4. Implementation Steps

### Step 4.1: Add Crease Combo Query Function

**File:** `services/player_patterns.py`

**What to do:** Create a new helper function that queries the deliveries table to get bowler stats broken down by crease combination.

**Location:** Add this after the `detect_bowler_patterns()` function (around line 500)

```python
def get_bowler_crease_combo_stats(player_name: str, filters: dict, db) -> Dict[str, Any]:
    """
    Query deliveries table to get bowler performance vs different crease combinations.
    
    Args:
        player_name: The bowler's name
        filters: Dict containing start_date, end_date, leagues, etc.
        db: Database session
        
    Returns:
        Dict with stats for each crease combo (Right-Right, Right-Left, Left-Right, Left-Left)
    """
    # TODO: Implement this query
    pass
```

**SQL Query to Use:**

```sql
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
WHERE d.bowler = :player_name
AND d.crease_combo IS NOT NULL
-- Add date/league filters here
GROUP BY d.crease_combo
HAVING COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) >= 30  -- Minimum sample size
```

**Expected Output Structure:**

```python
{
    "Right-Right": {
        "balls": 245,
        "runs": 312,
        "wickets": 18,
        "dots": 98,
        "economy": 7.64,
        "strike_rate": 13.6,
        "dot_percentage": 40.0
    },
    "Right-Left": {
        "balls": 180,
        "runs": 276,
        "wickets": 12,
        # ... etc
    },
    # ... Left-Right, Left-Left
}
```

---

### Step 4.2: Add Ball Direction Query Function

**File:** `services/player_patterns.py`

**What to do:** Create a function to get stats by ball direction (into batter vs away from batter).

**Why this matters:** For spinners especially, knowing if they're effective when the ball turns into the batter vs away is crucial.

```python
def get_bowler_ball_direction_stats(player_name: str, filters: dict, db) -> Dict[str, Any]:
    """
    Query deliveries table to get bowler performance by ball direction.
    
    Ball direction is calculated based on bowler type + striker handedness:
    - intoBatter: Ball moving towards the striker
    - awayFromBatter: Ball moving away from the striker
    
    Example: Right-arm off-spinner vs LHB = awayFromBatter
    """
    # TODO: Implement this query
    pass
```

**SQL Query to Use:**

```sql
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
WHERE d.bowler = :player_name
AND d.ball_direction IS NOT NULL
-- Add date/league filters here
GROUP BY d.ball_direction
HAVING COUNT(CASE WHEN d.wides = 0 AND d.noballs = 0 THEN 1 END) >= 50
```

---

### Step 4.3: Enhance Phase Stats with Wicket Distribution

**File:** `services/player_patterns.py`

**What to do:** Modify `_calculate_bowling_phase_distribution()` to also calculate wicket percentages per phase.

**Current code calculates:**
- % of overs in each phase

**New code should also calculate:**
- % of wickets in each phase
- Economy in each phase
- Strike rate in each phase

**Location:** Modify the `_calculate_bowling_phase_distribution()` function

**Before (current):**
```python
def _calculate_bowling_phase_distribution(phase_stats: Dict) -> Dict[str, float]:
    """Calculate percentage of overs bowled in each phase."""
    pp_overs = phase_stats.get("powerplay", {}).get("overs", 0)
    mid_overs = phase_stats.get("middle", {}).get("overs", 0)
    death_overs = phase_stats.get("death", {}).get("overs", 0)
    
    total = pp_overs + mid_overs + death_overs
    # ... returns only percentages
```

**After (enhanced):**
```python
def _calculate_bowling_phase_distribution(phase_stats: Dict) -> Dict[str, Dict]:
    """
    Calculate comprehensive phase distribution including:
    - % of overs in each phase
    - % of wickets in each phase
    - Economy per phase
    - Strike rate per phase
    """
    result = {}
    
    # Calculate totals first
    total_overs = sum(
        phase_stats.get(p, {}).get("overs", 0) 
        for p in ["powerplay", "middle", "death"]
    )
    total_wickets = sum(
        phase_stats.get(p, {}).get("wickets", 0) 
        for p in ["powerplay", "middle", "death"]
    )
    
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = phase_stats.get(phase_name, {})
        overs = phase_data.get("overs", 0)
        wickets = phase_data.get("wickets", 0)
        runs = phase_data.get("runs", 0)
        balls = phase_data.get("balls", overs * 6)  # Approximate if not available
        
        result[phase_name] = {
            "overs_percentage": round((overs / total_overs * 100), 1) if total_overs > 0 else 0,
            "wickets_percentage": round((wickets / total_wickets * 100), 1) if total_wickets > 0 else 0,
            "economy": round((runs * 6 / balls), 2) if balls > 0 else 0,
            "strike_rate": round(balls / wickets, 1) if wickets > 0 else 999,
            "wickets": wickets,
            "overs": overs
        }
    
    return result
```

---

### Step 4.4: Fix Over Usage Pattern Detection

**File:** `services/player_patterns.py`

**What to do:** Fix `_analyze_over_usage()` to properly read the `over_stats` data.

**Current problem:** The function returns `typical_overs: []` even when data exists.

**Root cause:** The function expects `over_stats` but the bowling endpoint returns `over_distribution`.

**Location:** Modify `_analyze_over_usage()` function

**Steps:**

1. Check what the actual key name is in the stats dict (it's `over_distribution`, not `over_stats`)
2. Sort overs by `instances_bowled` or `times_bowled` field
3. Extract top 4-5 most bowled overs
4. Calculate percentage of matches where each over is bowled

**Enhanced function:**

```python
def _analyze_over_usage(over_distribution: List[Dict], overall: Dict) -> Dict:
    """
    Analyze which overs the bowler typically bowls.
    
    Args:
        over_distribution: List of dicts from bowling_stats endpoint
            Each dict has: over_number, instances_bowled, matches_percentage, etc.
        overall: Overall stats dict with matches count
    """
    if not over_distribution:
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
    
    # Sort by frequency (instances_bowled or times_bowled)
    sorted_overs = sorted(
        over_distribution, 
        key=lambda x: x.get("instances_bowled", x.get("times_bowled", 0)), 
        reverse=True
    )
    
    # Get top 4 most frequently bowled overs
    # Note: over_number is 0-indexed, add 1 for display
    typical_overs = []
    for over_data in sorted_overs[:4]:
        over_num = over_data.get("over_number", 0)
        display_over = over_num + 1  # Convert to 1-indexed
        frequency = over_data.get("instances_bowled", over_data.get("times_bowled", 0))
        percentage = over_data.get("matches_percentage", 0)
        
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
```

---

### Step 4.5: Update detect_bowler_patterns() Main Function

**File:** `services/player_patterns.py`

**What to do:** Update the main function to:
1. Accept database session as parameter (needed for new queries)
2. Call the new crease_combo and ball_direction functions
3. Use enhanced phase distribution

**New function signature:**

```python
def detect_bowler_patterns(stats: Dict[str, Any], db=None, filters: dict=None) -> Dict[str, Any]:
    """
    Extract patterns from bowler statistics.
    
    Args:
        stats: Raw stats from /player/{name}/bowling_stats endpoint
        db: Database session (optional, for crease_combo queries)
        filters: Filter dict with start_date, end_date, leagues etc.
        
    Returns:
        Structured pattern data for LLM synthesis
    """
```

**Add to the patterns dict:**

```python
# After existing pattern detection...

# Add crease combo analysis (if db available)
if db and filters:
    patterns["crease_combo_stats"] = get_bowler_crease_combo_stats(
        player_name=patterns["player_name"],
        filters=filters,
        db=db
    )
    patterns["ball_direction_stats"] = get_bowler_ball_direction_stats(
        player_name=patterns["player_name"],
        filters=filters,
        db=db
    )
else:
    patterns["crease_combo_stats"] = {}
    patterns["ball_direction_stats"] = {}

# Add best/worst crease combo
patterns["best_crease_combo"] = _find_best_crease_combo(patterns["crease_combo_stats"])
patterns["worst_crease_combo"] = _find_worst_crease_combo(patterns["crease_combo_stats"])
```

---

### Step 4.6: Add Helper Functions for Best/Worst Matchups

**File:** `services/player_patterns.py`

**What to do:** Add functions to identify best and worst matchups from the crease combo data.

```python
def _find_best_crease_combo(crease_stats: Dict) -> Dict:
    """
    Find the crease combination where the bowler performs best.
    
    "Best" = lowest economy rate with minimum 30 balls sample
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


def _find_worst_crease_combo(crease_stats: Dict) -> Dict:
    """
    Find the crease combination where the bowler struggles.
    
    "Worst" = highest economy rate with minimum 30 balls sample
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
```

---

### Step 4.7: Update Bowler Endpoint to Pass DB Session

**File:** `routers/player_summary.py`

**What to do:** Modify the `/bowler/{player_name}` endpoint to pass the database session and filters to the pattern detection function.

**Find this code (around line 380):**

```python
# Detect patterns
logger.info(f"Detecting bowler patterns for {player_name}")
patterns = detect_bowler_patterns(stats)
```

**Replace with:**

```python
# Detect patterns (pass db and filters for advanced queries)
logger.info(f"Detecting bowler patterns for {player_name}")
patterns = detect_bowler_patterns(
    stats=stats,
    db=db,
    filters=filters
)
```

---

### Step 4.8: Update Bowler Prompt Template

**File:** `routers/player_summary.py`

**What to do:** Update `BOWLER_SUMMARY_PROMPT` to reflect the new data structure and desired output format.

**New prompt:**

```python
BOWLER_SUMMARY_PROMPT = """You are a cricket analyst writing a concise "Player DNA" summary. Based on the pattern data below, write a brief, insightful summary of this bowler's style.

## Pattern Data
{pattern_json}

## Output Format
Write exactly 5 bullet points, each on a new line starting with an emoji and label:

🎯 Primary Phase: [Which phase they bowl most AND their effectiveness there - include overs%, wickets%, economy]
⚡ Bowling Profile: [Their style classification with key numbers - economy, SR, dot%, wickets per match]
💪 Dominance: [Best matchup from crease_combo_stats or phase strengths - be specific with numbers]
⚠️ Vulnerability: [Weakness from worst_crease_combo or phase weakness - include specific numbers]
📊 Usage Pattern: [Which overs they typically bowl with percentages from typical_overs]

## Rules
1. Be SPECIFIC - every bullet must include at least 2 numbers
2. Keep each bullet to ONE sentence
3. Format economy as "Econ 7.2" and strike rate as "SR 18"
4. For crease combos, translate to readable format:
   - "Right-Right" = "vs two right-handers"
   - "Right-Left" = "vs right-hander with left-hander at non-striker"
   - etc.
5. Use typical_overs data to state actual over numbers (they are 1-indexed in the data)
6. If crease_combo_stats is empty, focus on phase-based strengths/weaknesses

## Example Output
🎯 Primary Phase: Powerplay specialist (76.9% of overs) taking 65% of wickets in this phase with Econ 6.31 and SR 18.2.
⚡ Bowling Profile: Wicket-taking seamer (SR 22.3, Econ 8.49) who builds pressure with 39.9% dots - averages 0.9 wickets per match.
💪 Dominance: Excels vs two right-handers (Econ 6.8, SR 16.2, 45% dots) in the powerplay.
⚠️ Vulnerability: Struggles in death overs (Econ 10.59) and vs right-left combinations (Econ 9.2).
📊 Usage Pattern: Bowls 1st over in 86.9% of matches, typically overs 1, 3, 5 - averages 3.2 overs per match.

Now generate the summary:"""
```

---

### Step 4.9: Update Fallback Summary Function

**File:** `routers/player_summary.py`

**What to do:** Update `generate_bowler_fallback_summary()` to use the new pattern fields.

**Key changes:**

1. Use `phase_distribution` with enhanced structure (includes wickets%, economy, SR)
2. Use `best_crease_combo` and `worst_crease_combo` for dominance/vulnerability
3. Use enhanced `typical_overs` list

```python
def generate_bowler_fallback_summary(patterns: dict) -> str:
    """Generate a basic bowler summary without LLM (fallback)."""
    lines = []
    
    # Primary Phase - Now with wicket stats
    phase_dist = patterns.get("phase_distribution", {})
    primary = patterns.get("primary_phase", "balanced")
    
    # Find the dominant phase
    max_phase = None
    max_overs_pct = 0
    for phase_name, phase_data in phase_dist.items():
        if isinstance(phase_data, dict):
            overs_pct = phase_data.get("overs_percentage", 0)
            if overs_pct > max_overs_pct:
                max_overs_pct = overs_pct
                max_phase = phase_name
                max_phase_data = phase_data
    
    if max_phase and max_overs_pct > 40:
        wickets_pct = max_phase_data.get("wickets_percentage", 0)
        economy = max_phase_data.get("economy", 0)
        lines.append(
            f"🎯 Primary Phase: {max_phase.title()} specialist ({max_overs_pct:.0f}% of overs) "
            f"taking {wickets_pct:.0f}% of wickets with Econ {economy:.2f}"
        )
    else:
        lines.append(f"🎯 Primary Phase: Workhorse who bowls across all phases")
    
    # Bowling Profile - With actual numbers
    economy = patterns.get("overall_economy", 0)
    sr = patterns.get("overall_strike_rate", 0)
    dot_pct = patterns.get("overall_dot_percentage", 0)
    matches = patterns.get("matches", 1)
    wickets = patterns.get("total_wickets", 0)
    wpg = round(wickets / matches, 1) if matches > 0 else 0
    
    profile = patterns.get("profile_classification", "balanced")
    lines.append(
        f"⚡ Bowling Profile: {profile.replace('_', ' ').title()} "
        f"(SR {sr:.1f}, Econ {economy:.2f}, {dot_pct:.1f}% dots) - {wpg} wickets per match"
    )
    
    # Dominance - Best crease combo or phase
    best_combo = patterns.get("best_crease_combo")
    if best_combo:
        combo_name = _format_crease_combo(best_combo["combo"])
        lines.append(
            f"💪 Dominance: Excels {combo_name} "
            f"(Econ {best_combo['economy']:.2f}, SR {best_combo['strike_rate']:.1f})"
        )
    else:
        # Fall back to phase strengths
        strengths = patterns.get("strengths", [])
        if strengths:
            s = strengths[0]
            lines.append(
                f"💪 Dominance: Strong {s.get('context', '')} "
                f"(Econ {s.get('economy', 0):.2f})"
            )
        else:
            lines.append("💪 Dominance: Consistent across all matchups")
    
    # Vulnerability - Worst crease combo or phase
    worst_combo = patterns.get("worst_crease_combo")
    if worst_combo and worst_combo["economy"] >= 9.0:
        combo_name = _format_crease_combo(worst_combo["combo"])
        lines.append(
            f"⚠️ Vulnerability: Struggles {combo_name} (Econ {worst_combo['economy']:.2f})"
        )
    else:
        weaknesses = patterns.get("weaknesses", [])
        if weaknesses:
            w = weaknesses[0]
            lines.append(
                f"⚠️ Vulnerability: Can be expensive {w.get('context', '')} "
                f"(Econ {w.get('economy', 0):.2f})"
            )
        else:
            lines.append("⚠️ Vulnerability: No clear vulnerabilities identified")
    
    # Usage Pattern - With actual over numbers
    typical_overs = patterns.get("typical_overs", [])
    overs_per_match = patterns.get("overs_per_match", 0)
    
    if typical_overs and len(typical_overs) > 0:
        # Get the primary over with its percentage
        primary_over = typical_overs[0]
        over_nums = [str(o["over"]) for o in typical_overs[:3]]
        lines.append(
            f"📊 Usage Pattern: Bowls over {primary_over['over']} in {primary_over['percentage']:.0f}% "
            f"of matches, typically overs {', '.join(over_nums)} - {overs_per_match:.1f} overs per match"
        )
    else:
        lines.append(f"📊 Usage Pattern: Flexible usage, averaging {overs_per_match:.1f} overs per match")
    
    return "\n".join(lines)


def _format_crease_combo(combo: str) -> str:
    """Convert crease combo code to readable format."""
    mapping = {
        "Right-Right": "vs two right-handers",
        "Right-Left": "vs right-hander (left at non-striker)",
        "Left-Right": "vs left-hander (right at non-striker)",
        "Left-Left": "vs two left-handers"
    }
    return mapping.get(combo, f"vs {combo}")
```

---

### Step 4.10: Add Crease Combo Query Implementation

**File:** `services/player_patterns.py`

**What to do:** Implement the actual SQL query for crease combo stats.

```python
from sqlalchemy.sql import text

def get_bowler_crease_combo_stats(player_name: str, filters: dict, db) -> Dict[str, Any]:
    """
    Query deliveries table to get bowler performance vs different crease combinations.
    """
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
        
        # Add league filters if needed (similar to main.py pattern)
        # ... 
        
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
        
        results = db.execute(query, params).fetchall()
        
        crease_stats = {}
        for row in results:
            balls = row.legal_balls or 0
            runs = row.runs or 0
            wickets = row.wickets or 0
            dots = row.dots or 0
            
            crease_stats[row.crease_combo] = {
                "balls": balls,
                "runs": runs,
                "wickets": wickets,
                "dots": dots,
                "economy": round((runs * 6 / balls), 2) if balls > 0 else 0,
                "strike_rate": round(balls / wickets, 1) if wickets > 0 else 999,
                "dot_percentage": round((dots * 100 / balls), 1) if balls > 0 else 0
            }
        
        return crease_stats
        
    except Exception as e:
        logger.error(f"Error getting crease combo stats: {str(e)}")
        return {}
```

---

## 5. Testing Checklist

### Manual Testing Steps

After implementing the changes, test with these players:

| Player | Type | Expected Behavior |
|--------|------|-------------------|
| DL Chahar | Powerplay pacer | Should show strong PP stats, typical overs 1, 3, 5 |
| JJ Bumrah | Death specialist | Should show strong death stats, typical overs 17, 19 |
| R Ashwin | Spin bowler | Should show ball_direction analysis (vs RHB/LHB) |
| Rashid Khan | Leg spinner | Should show crease_combo patterns |

### Test Queries

1. **Verify crease_combo data exists:**
```sql
SELECT crease_combo, COUNT(*) 
FROM deliveries 
WHERE bowler = 'DL Chahar' AND crease_combo IS NOT NULL 
GROUP BY crease_combo;
```

2. **Verify ball_direction data exists:**
```sql
SELECT ball_direction, COUNT(*) 
FROM deliveries 
WHERE bowler = 'R Ashwin' AND ball_direction IS NOT NULL 
GROUP BY ball_direction;
```

3. **Verify over distribution is populated:**
Check the `/player/DL+Chahar/bowling_stats` endpoint and confirm `over_distribution` array has data.

### Expected API Response Changes

The `/player-summary/bowler/{name}?include_patterns=true` endpoint should now include:

```json
{
  "patterns": {
    "phase_distribution": {
      "powerplay": {
        "overs_percentage": 76.9,
        "wickets_percentage": 65.0,
        "economy": 6.31,
        "strike_rate": 18.2
      }
    },
    "crease_combo_stats": {
      "Right-Right": { "economy": 6.8, "strike_rate": 16.2 },
      "Right-Left": { "economy": 9.2, "strike_rate": 28.5 }
    },
    "best_crease_combo": { "combo": "Right-Right", "economy": 6.8 },
    "worst_crease_combo": { "combo": "Right-Left", "economy": 9.2 },
    "typical_overs": [
      { "over": 1, "frequency": 53, "percentage": 86.9 },
      { "over": 3, "frequency": 49, "percentage": 80.3 }
    ]
  }
}
```

---

## Summary of Changes

| File | Changes |
|------|---------|
| `services/player_patterns.py` | Add `get_bowler_crease_combo_stats()`, `get_bowler_ball_direction_stats()`, enhance `_calculate_bowling_phase_distribution()`, fix `_analyze_over_usage()`, add `_find_best_crease_combo()`, `_find_worst_crease_combo()` |
| `routers/player_summary.py` | Update `BOWLER_SUMMARY_PROMPT`, update `generate_bowler_fallback_summary()`, pass db/filters to pattern detection |

---

**Document Version**: 1.0  
**Created**: December 2024  
**Author**: Hindsight Cricket Analytics
