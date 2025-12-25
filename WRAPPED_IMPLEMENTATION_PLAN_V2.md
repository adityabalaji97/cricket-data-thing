# Wrapped/Hindsight 2025 - Implementation Plan V2

## Overview

This document outlines prioritized implementation tasks for the 2025 In Hindsight feature. Tasks are organized by priority and include detailed step-by-step instructions suitable for a junior developer or LLM.

**Last Updated:** December 2025

---

## Table of Contents

1. [Phase 1: Critical Bug Fixes](#phase-1-critical-bug-fixes)
2. [Phase 2: Card Data Migration to delivery_details](#phase-2-card-data-migration-to-delivery_details)
3. [Phase 3: New Card - Middle Overs Squeeze](#phase-3-new-card---middle-overs-squeeze)
4. [Phase 4: Card Metric Enhancements](#phase-4-card-metric-enhancements)
5. [Phase 5: Query Recreation Fixes](#phase-5-query-recreation-fixes)
6. [Phase 6: Player Aliases Integration (App-Wide)](#phase-6-player-aliases-integration-app-wide)
7. [Phase 7: Customizable Filters (Three-Dot Menu)](#phase-7-customizable-filters-three-dot-menu)
8. [Phase 8: Profile Page Enhancements](#phase-8-profile-page-enhancements)
9. [Phase 9: Venue Vibes Audit](#phase-9-venue-vibes-audit)

---

## Phase 1: Critical Bug Fixes

### 1.1 Fix Grey Tint on Image Save

**Priority:** HIGH  
**Estimated Time:** 1-2 hours  
**Files to Modify:**
- `/src/utils/shareUtils.js`
- `/src/components/wrapped/wrapped.css`

**Problem Description:**
When users click "Save Image" on mobile, the saved image has a grey tint overlay, as if a modal was open during capture.

**Root Cause Analysis:**
The html2canvas library captures the current visual state of the DOM. If there's any overlay, backdrop, or opacity change during capture, it gets included in the image.

**Step-by-Step Fix:**

1. **Open `/src/utils/shareUtils.js`**

2. **Update the `captureElementAsImage` function** to temporarily hide any overlays:

```javascript
export const captureElementAsImage = async (element) => {
  if (!element) {
    console.error('No element provided to capture');
    return null;
  }

  const html2canvas = await getHtml2Canvas();
  if (!html2canvas) return null;

  try {
    // STEP 1: Temporarily hide any overlays or modals
    const overlays = document.querySelectorAll('.MuiBackdrop-root, .MuiModal-root, .wrapped-nav-hints');
    const originalStyles = [];
    
    overlays.forEach((overlay, index) => {
      originalStyles[index] = overlay.style.display;
      overlay.style.display = 'none';
    });

    // STEP 2: Remove any opacity/filter from parent containers temporarily
    const container = element.closest('.wrapped-container');
    let originalContainerStyle = null;
    if (container) {
      originalContainerStyle = container.style.cssText;
      container.style.filter = 'none';
      container.style.opacity = '1';
    }

    // STEP 3: Capture the element
    const canvas = await html2canvas(element, {
      backgroundColor: '#121212',
      scale: 2,
      useCORS: true,
      logging: false,
      allowTaint: true,
      width: element.offsetWidth,
      height: element.offsetHeight,
      // Important: ignore elements that might cause overlay
      ignoreElements: (el) => {
        return el.classList.contains('MuiBackdrop-root') ||
               el.classList.contains('wrapped-nav-hints') ||
               el.classList.contains('wrapped-action-btn-share');
      }
    });

    // STEP 4: Restore original styles
    overlays.forEach((overlay, index) => {
      overlay.style.display = originalStyles[index];
    });
    
    if (container && originalContainerStyle !== null) {
      container.style.cssText = originalContainerStyle;
    }

    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('Error capturing element:', error);
    return null;
  }
};
```

3. **Check `/src/components/wrapped/wrapped.css`** for any styles that might add overlays:

Look for and temporarily disable during capture:
- `::before` or `::after` pseudo-elements with backgrounds
- Any `backdrop-filter` or `filter` properties
- Gradient overlays on the container

4. **Test the fix:**
   - Open the wrapped experience on mobile (or mobile emulator)
   - Navigate to any card
   - Click "Save Image"
   - Verify the saved image has no grey tint
   - Test on iOS Safari and Android Chrome

---

### 1.2 Fix Multi-Column group_by Error

**Priority:** HIGH  
**Estimated Time:** 30 minutes  
**Files to Modify:**
- `/routers/query_builder_v2.py`

**Problem Description:**
When users click "Recreate Query" from a card, the URL might contain `group_by=batter,shot` (comma-separated). FastAPI parses this as a single string `['batter,shot']` instead of `['batter', 'shot']`, causing the error:
```
500: Database query failed: 400: Invalid group_by columns: ['batter,shot']
```

**Step-by-Step Fix:**

1. **Open `/routers/query_builder_v2.py`**

2. **Add a preprocessing step** at the beginning of the `query_deliveries` function to split comma-separated values:

```python
@router.get("/deliveries")
def query_deliveries(
    # ... existing parameters ...
    group_by: List[str] = Query(default=[], description="Group results by columns"),
    # ... rest of parameters ...
):
    """
    Query ball-by-ball data...
    """
    try:
        # PREPROCESSING: Handle comma-separated group_by values
        # This handles URLs like ?group_by=batter,shot which FastAPI parses as ['batter,shot']
        processed_group_by = []
        for item in group_by:
            if ',' in item:
                # Split comma-separated values and strip whitespace
                processed_group_by.extend([col.strip() for col in item.split(',')])
            else:
                processed_group_by.append(item.strip())
        
        # Remove empty strings and duplicates while preserving order
        seen = set()
        group_by = []
        for col in processed_group_by:
            if col and col not in seen:
                seen.add(col)
                group_by.append(col)
        
        # Continue with the service call using processed group_by
        result = query_deliveries_service(
            # ... all parameters ...
            group_by=group_by,  # Use the processed list
            # ... rest of parameters ...
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

3. **Also apply the same fix to other list parameters** that might have this issue:
   - `leagues`
   - `teams`
   - `batting_teams`
   - `bowling_teams`
   - `players`
   - `batters`
   - `bowlers`
   - `bowl_style`
   - `bowl_kind`
   - `crease_combo`
   - `line`
   - `length`
   - `shot`
   - `wagon_zone`

4. **Create a helper function** at the top of the file:

```python
def preprocess_list_param(items: List[str]) -> List[str]:
    """
    Preprocess list parameters to handle comma-separated values.
    Converts ['a,b', 'c'] to ['a', 'b', 'c']
    """
    if not items:
        return []
    
    processed = []
    for item in items:
        if ',' in str(item):
            processed.extend([x.strip() for x in str(item).split(',')])
        else:
            processed.append(str(item).strip() if item else '')
    
    # Remove empty strings and duplicates while preserving order
    seen = set()
    result = []
    for item in processed:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    
    return result
```

5. **Apply the helper to all list params** at the start of `query_deliveries`:

```python
# Preprocess all list parameters
leagues = preprocess_list_param(leagues)
teams = preprocess_list_param(teams)
batting_teams = preprocess_list_param(batting_teams)
bowling_teams = preprocess_list_param(bowling_teams)
players = preprocess_list_param(players)
batters = preprocess_list_param(batters)
bowlers = preprocess_list_param(bowlers)
group_by = preprocess_list_param(group_by)
bowl_style = preprocess_list_param(bowl_style)
bowl_kind = preprocess_list_param(bowl_kind)
crease_combo = preprocess_list_param(crease_combo)
line = preprocess_list_param(line)
length = preprocess_list_param(length)
shot = preprocess_list_param(shot)
# wagon_zone needs special handling since it's List[int]
wagon_zone = [int(x) for x in preprocess_list_param([str(x) for x in wagon_zone])] if wagon_zone else []
```

6. **Test the fix:**
   - Navigate to `/query/deliveries?group_by=batter,shot&min_balls=100`
   - Verify it returns grouped results without error
   - Test from a Wrapped card's "Recreate Query" button

---

## Phase 2: Card Data Migration to delivery_details

### Overview

The following cards currently use legacy tables (`deliveries`, `batting_stats`, `bowling_stats`) and need to be migrated to use `delivery_details` for consistency and access to advanced metrics.

**Important Notes:**
- `delivery_details` only contains data from 2015 onwards
- For Wrapped 2025, this is fine since we're only looking at 2025 data
- The table uses different column names (see mapping below)

### Column Name Mapping

| Legacy Table | delivery_details |
|-------------|------------------|
| `d.batter` | `dd.bat` |
| `d.bowler` | `dd.bowl` |
| `d.batting_team` | `dd.team_bat` |
| `d.bowling_team` | `dd.team_bowl` |
| `d.runs_off_bat` | `dd.batruns` |
| `d.runs_off_bat + d.extras` | `dd.score` |
| `d.wicket_type` | `dd.dismissal` |
| `d.over` | `dd.over` |
| `d.innings` | `dd.inns` |
| `d.match_id` | `dd.p_match` |
| `m.venue` | `dd.ground` |
| `m.date` | `dd.match_date` |
| `m.competition` | `dd.competition` |
| `EXTRACT(YEAR FROM m.date)` | `dd.year` |

### Phase Boundaries in delivery_details

```sql
-- Powerplay: overs 0-5 (over < 6)
-- Middle: overs 6-14 (over >= 6 AND over < 15)
-- Death: overs 15-19 (over >= 15)
```

---

### 2.1 Migrate Intro Card

**Priority:** MEDIUM  
**Estimated Time:** 1 hour  
**File to Modify:** `/services/wrapped.py`

**Current Implementation:** Uses `deliveries` table joined with `matches`

**New Implementation:**

```python
def get_intro_card_data(
    self,
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """Card 1: Global run rate and wicket cost by phase - using delivery_details."""
    
    params = {
        "start_year": int(start_date[:4]),
        "end_year": int(end_date[:4]),
    }
    
    # Add league filter if specified
    league_filter = ""
    if leagues:
        league_filter = "AND dd.competition = ANY(:leagues)"
        params["leagues"] = leagues
    
    # Add international filter
    intl_filter = ""
    if include_international:
        if top_teams:
            intl_filter = "OR (dd.competition = 'T20I' AND dd.team_bat = ANY(:top_teams) AND dd.team_bowl = ANY(:top_teams))"
            params["top_teams"] = INTERNATIONAL_TEAMS_RANKED[:top_teams]
        else:
            intl_filter = "OR dd.competition = 'T20I'"
    
    query = text(f"""
        WITH phase_data AS (
            SELECT 
                CASE 
                    WHEN dd.over < 6 THEN 'powerplay'
                    WHEN dd.over >= 6 AND dd.over < 15 THEN 'middle'
                    ELSE 'death'
                END as phase,
                COUNT(*) as balls,
                SUM(dd.score) as runs,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' 
                    AND dd.dismissal NOT IN ('run out', 'retired hurt', 'retired out')
                    THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND (1=0 {league_filter} {intl_filter})
            GROUP BY phase
        )
        SELECT 
            phase,
            balls,
            runs,
            wickets,
            dots,
            boundaries,
            ROUND(CAST(runs * 6.0 / NULLIF(balls, 0) AS numeric), 2) as run_rate,
            ROUND(CAST(runs AS numeric) / NULLIF(wickets, 0), 2) as runs_per_wicket,
            ROUND(CAST(dots * 100.0 / NULLIF(balls, 0) AS numeric), 1) as dot_percentage,
            ROUND(CAST(boundaries * 100.0 / NULLIF(balls, 0) AS numeric), 1) as boundary_percentage
        FROM phase_data
        ORDER BY 
            CASE phase 
                WHEN 'powerplay' THEN 1 
                WHEN 'middle' THEN 2 
                WHEN 'death' THEN 3 
            END
    """)
    
    results = db.execute(query, params).fetchall()
    
    # Get total matches count from delivery_details
    matches_query = text(f"""
        SELECT COUNT(DISTINCT dd.p_match) as total_matches
        FROM delivery_details dd
        WHERE dd.year >= :start_year
        AND dd.year <= :end_year
        AND (1=0 {league_filter} {intl_filter})
    """)
    
    matches_result = db.execute(matches_query, params).fetchone()
    
    # Get batting first vs chase win statistics
    # Note: delivery_details has 'winner' column we can use
    toss_query = text(f"""
        WITH match_results AS (
            SELECT DISTINCT 
                dd.p_match,
                dd.winner,
                FIRST_VALUE(dd.team_bat) OVER (
                    PARTITION BY dd.p_match 
                    ORDER BY dd.inns, dd.over, dd.ball
                ) as batting_first_team
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.winner IS NOT NULL
            AND (1=0 {league_filter} {intl_filter})
        )
        SELECT 
            SUM(CASE WHEN winner = batting_first_team THEN 1 ELSE 0 END) as bat_first_wins,
            SUM(CASE WHEN winner != batting_first_team THEN 1 ELSE 0 END) as chase_wins,
            COUNT(*) as total_decided
        FROM match_results
    """)
    
    toss_result = db.execute(toss_query, params).fetchone()
    
    bat_first_wins = toss_result.bat_first_wins if toss_result and toss_result.bat_first_wins else 0
    chase_wins = toss_result.chase_wins if toss_result and toss_result.chase_wins else 0
    total_decided = bat_first_wins + chase_wins
    bat_first_pct = round((bat_first_wins * 100.0 / total_decided), 1) if total_decided > 0 else 50.0
    
    return {
        "card_id": "intro",
        "card_title": "2025 in One Breath",
        "card_subtitle": "The rhythm of T20 cricket",
        "total_matches": matches_result.total_matches if matches_result else 0,
        "toss_stats": {
            "bat_first_wins": bat_first_wins,
            "chase_wins": chase_wins,
            "total_decided": total_decided,
            "bat_first_pct": bat_first_pct
        },
        "phases": [
            {
                "phase": row.phase,
                "balls": row.balls,
                "runs": row.runs,
                "wickets": row.wickets,
                "run_rate": float(row.run_rate) if row.run_rate else 0,
                "runs_per_wicket": float(row.runs_per_wicket) if row.runs_per_wicket else 0,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
            }
            for row in results
        ],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&group_by=phase"
        }
    }
```

---

### 2.2 Migrate Powerplay Bullies Card

**Priority:** MEDIUM  
**Estimated Time:** 1 hour  
**File to Modify:** `/services/wrapped.py`

**Current Implementation:** Uses `batting_stats` table (pre-aggregated)

**New Implementation using delivery_details:**

```python
def get_powerplay_bullies_data(
    self,
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 100,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """Card 2: Top batters in powerplay - using delivery_details."""
    
    params = {
        "start_year": int(start_date[:4]),
        "end_year": int(end_date[:4]),
        "min_balls": min_balls
    }
    
    # Build competition filter
    league_filter = ""
    if leagues:
        league_filter = "AND dd.competition = ANY(:leagues)"
        params["leagues"] = leagues
    
    intl_filter = ""
    if include_international:
        if top_teams:
            intl_filter = "OR (dd.competition = 'T20I' AND dd.team_bat = ANY(:top_teams) AND dd.team_bowl = ANY(:top_teams))"
            params["top_teams"] = INTERNATIONAL_TEAMS_RANKED[:top_teams]
        else:
            intl_filter = "OR dd.competition = 'T20I'"
    
    query = text(f"""
        WITH powerplay_stats AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                COUNT(*) as balls,
                SUM(dd.batruns) as runs,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                COUNT(DISTINCT dd.p_match) as innings
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.over < 6  -- Powerplay overs 0-5
            AND dd.bat_hand IN ('LHB', 'RHB')
            AND (1=0 {league_filter} {intl_filter})
            GROUP BY dd.bat, dd.team_bat
        ),
        player_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM powerplay_stats
            ORDER BY player, balls DESC
        ),
        player_totals AS (
            SELECT 
                player,
                SUM(balls) as balls,
                SUM(runs) as runs,
                SUM(wickets) as wickets,
                SUM(dots) as dots,
                SUM(boundaries) as boundaries,
                SUM(innings) as innings
            FROM powerplay_stats
            GROUP BY player
            HAVING SUM(balls) >= :min_balls
        )
        SELECT 
            pt.player, ppt.team, pt.balls, pt.runs, pt.wickets, pt.dots, pt.boundaries, pt.innings,
            ROUND(CAST(pt.runs * 100.0 / NULLIF(pt.balls, 0) AS numeric), 2) as strike_rate,
            ROUND(CAST(pt.runs AS numeric) / NULLIF(pt.wickets, 0), 2) as average,
            ROUND(CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as dot_percentage,
            ROUND(CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as boundary_percentage
        FROM player_totals pt
        JOIN player_primary_team ppt ON pt.player = ppt.player
        ORDER BY strike_rate DESC
        LIMIT 20
    """)
    
    results = db.execute(query, params).fetchall()
    
    return {
        "card_id": "powerplay_bullies",
        "card_title": "Powerplay Bullies",
        "card_subtitle": f"Who dominated the first 6 overs (min {min_balls} balls)",
        "visualization_type": "scatter",
        "x_axis": "dot_percentage",
        "y_axis": "strike_rate",
        "players": [
            {
                "name": row.player,
                "team": row.team,
                "balls": row.balls,
                "runs": row.runs,
                "innings": row.innings,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                "average": float(row.average) if row.average else 0,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0
            }
            for row in results
        ],
        "deep_links": {
            "comparison": f"/comparison?start_date={start_date}&end_date={end_date}",
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=0&over_max=5&group_by=batter&min_balls={min_balls}"
        }
    }
```

---

### 2.3 Migrate Middle Merchants Card

**Priority:** MEDIUM  
**Estimated Time:** 1 hour  
**File to Modify:** `/services/wrapped.py`

**Enhancement Notes:** Prioritize LOW dot ball % and HIGH boundary % when ranking

**New Implementation:**

```python
def get_middle_merchants_data(
    self,
    start_date: str,
    end_date: str,
    leagues: List[str],
    include_international: bool,
    db: Session,
    min_balls: int = 150,
    top_teams: int = DEFAULT_TOP_TEAMS
) -> Dict[str, Any]:
    """Card 3: Best middle-overs batters - prioritizing low dot% and high boundary%."""
    
    params = {
        "start_year": int(start_date[:4]),
        "end_year": int(end_date[:4]),
        "min_balls": min_balls
    }
    
    # Build competition filter (same pattern as above)
    league_filter = ""
    if leagues:
        league_filter = "AND dd.competition = ANY(:leagues)"
        params["leagues"] = leagues
    
    intl_filter = ""
    if include_international:
        if top_teams:
            intl_filter = "OR (dd.competition = 'T20I' AND dd.team_bat = ANY(:top_teams) AND dd.team_bowl = ANY(:top_teams))"
            params["top_teams"] = INTERNATIONAL_TEAMS_RANKED[:top_teams]
        else:
            intl_filter = "OR dd.competition = 'T20I'"
    
    query = text(f"""
        WITH middle_stats AS (
            SELECT 
                dd.bat as player,
                dd.team_bat as team,
                COUNT(*) as balls,
                SUM(dd.batruns) as runs,
                SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
                SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
                SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
                COUNT(DISTINCT dd.p_match) as innings
            FROM delivery_details dd
            WHERE dd.year >= :start_year
            AND dd.year <= :end_year
            AND dd.over >= 6 AND dd.over < 15  -- Middle overs 6-14
            AND dd.bat_hand IN ('LHB', 'RHB')
            AND (1=0 {league_filter} {intl_filter})
            GROUP BY dd.bat, dd.team_bat
        ),
        player_primary_team AS (
            SELECT DISTINCT ON (player) player, team
            FROM middle_stats
            ORDER BY player, balls DESC
        ),
        player_totals AS (
            SELECT 
                player,
                SUM(balls) as balls,
                SUM(runs) as runs,
                SUM(wickets) as wickets,
                SUM(dots) as dots,
                SUM(boundaries) as boundaries,
                SUM(innings) as innings
            FROM middle_stats
            GROUP BY player
            HAVING SUM(balls) >= :min_balls
        )
        SELECT 
            pt.player, ppt.team, pt.balls, pt.runs, pt.wickets, pt.dots, pt.boundaries, pt.innings,
            ROUND(CAST(pt.runs * 100.0 / NULLIF(pt.balls, 0) AS numeric), 2) as strike_rate,
            ROUND(CAST(pt.runs AS numeric) / NULLIF(pt.wickets, 0), 2) as average,
            ROUND(CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as dot_percentage,
            ROUND(CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric), 1) as boundary_percentage,
            -- NEW: Composite score prioritizing low dot% and high boundary%
            -- Formula: (boundary% * 2) + (50 - dot%) + (SR - 100) / 10
            ROUND(
                (CAST(pt.boundaries * 100.0 / NULLIF(pt.balls, 0) AS numeric) * 2) +
                (50 - CAST(pt.dots * 100.0 / NULLIF(pt.balls, 0) AS numeric)) +
                (CAST(pt.runs * 100.0 / NULLIF(pt.balls, 0) AS numeric) - 100) / 10
            , 2) as middle_overs_score
        FROM player_totals pt
        JOIN player_primary_team ppt ON pt.player = ppt.player
        WHERE pt.wickets > 0  -- Need at least 1 dismissal for average
        ORDER BY middle_overs_score DESC  -- NEW: Order by composite score
        LIMIT 20
    """)
    
    results = db.execute(query, params).fetchall()
    
    return {
        "card_id": "middle_merchants",
        "card_title": "Middle Merchants",
        "card_subtitle": f"Masters of overs 7-15 (min {min_balls} balls)",
        "visualization_type": "scatter",
        "x_axis": "dot_percentage",  # Lower is better
        "y_axis": "boundary_percentage",  # Higher is better
        "ranking_note": "Ranked by composite score: high boundary%, low dot%, high SR",
        "players": [
            {
                "name": row.player,
                "team": row.team,
                "balls": row.balls,
                "runs": row.runs,
                "innings": row.innings,
                "strike_rate": float(row.strike_rate) if row.strike_rate else 0,
                "average": float(row.average) if row.average else 0,
                "dot_percentage": float(row.dot_percentage) if row.dot_percentage else 0,
                "boundary_percentage": float(row.boundary_percentage) if row.boundary_percentage else 0,
                "middle_overs_score": float(row.middle_overs_score) if row.middle_overs_score else 0
            }
            for row in results
        ],
        "deep_links": {
            "query_builder": f"/query?start_date={start_date}&end_date={end_date}&over_min=6&over_max=14&group_by=batter&min_balls={min_balls}"
        }
    }
```

---

### 2.4-2.6 Additional Card Migrations

The remaining cards (Death Hitters, PP Wicket Thieves, Death Over Gods) follow the same pattern as above. Key differences:

- **Death Hitters**: Add `sixes` and `runs_from_sixes` columns, order by composite of SR + six_runs_percentage
- **PP Wicket Thieves**: Filter `dd.over < 6`, group by bowler, highlight dot% and boundary%
- **Death Over Gods**: Filter `dd.over >= 15`, group by bowler, composite score of economy + boundary% + wickets

---

## Phase 3: New Card - Middle Overs Squeeze

**Priority:** MEDIUM  
**Estimated Time:** 2 hours  
**Files to Modify:**
- `/services/wrapped.py` - Add `get_middle_overs_squeeze_data` method
- `/src/components/wrapped/WrappedCard.jsx` - Register card
- `/src/components/wrapped/cards/MiddleOversSqueezeCard.jsx` - Create component

**Key Metrics:**
- Low economy rate
- High dot ball percentage  
- Low boundary percentage
- Wickets taken

**Squeeze Score Formula:**
```
squeeze_score = (50 - economy*5) + (dot% * 0.5) + (20 - boundary%)
```

---

## Phase 4: Card Metric Enhancements

### 4.1 Pace vs Spin - Add "Complete Batters"
Show players who excel against BOTH pace AND spin (SR > 120, dot% < 35, boundary% > 10 against both)

### 4.2 Rare Shot Artists - Top 1 Per Shot
Instead of top 3 overall, show the best player for EACH rare shot type

### 4.3 Better #2-#5 Display
Add collapsible "Show more" for ranks #2-#5 on Length Masters, Controlled Chaos, 360 Batters

### 4.4 LHB Mirroring
Mirror wagon wheel zones (swap 0↔2, 3↔5, 6↔8) and flip pitch map X coordinates for left-handers

---

## Phase 5: Query Recreation Fixes

### 5.1 Remove Buttons for Non-Recreatable Cards
Cards using pred_score, win_prob, or ELO should NOT have "Recreate Query" buttons:
- Needle Movers
- Chase Masters  
- ELO Movers

### 5.2 Verify Deep Links Match Backend Queries

| Card | Required URL Params |
|------|-------------------|
| Powerplay Bullies | `over_min=0&over_max=5&group_by=batter` |
| Middle Merchants | `over_min=6&over_max=14&group_by=batter` |
| Death Hitters | `over_min=15&over_max=19&group_by=batter` |
| PP Wicket Thieves | `over_min=0&over_max=5&group_by=bowler` |
| Death Over Gods | `over_min=15&over_max=19&group_by=bowler` |
| Middle Overs Squeeze | `over_min=6&over_max=14&group_by=bowler` |

---

## Phase 6: Player Aliases Integration (App-Wide)

**Currently Integrated:** Query Builder only

**Needs Integration:**
- Player Profile/Search
- Venue Analysis
- Matchup Analysis
- Fantasy Analysis
- Team Profiles

**Implementation:** Create shared utility in `/services/player_aliases.py` with `expand_player_names()` function

---

## Phase 7: Customizable Filters (Three-Dot Menu)

**Files to Create/Modify:**
- `/src/components/wrapped/WrappedFilterMenu.jsx` (NEW)
- `/src/components/wrapped/WrappedHeader.jsx`
- `/src/components/wrapped/WrappedStoryContainer.jsx`

**Features:**
- Date range picker (start/end date)
- Multi-select leagues dropdown
- Reset to defaults button
- Apply filters refreshes all cards

---

## Phase 8: Profile Page Enhancements

### 8.1 Add Wagon Wheel to Batter Profile
- Show 360° scoring distribution
- Filter by phase, bowler style, line, length
- Mirror for LHB players

### 8.2 Add Pitch Map to Bowler Profile  
- Show ball pitching locations
- Color by outcome (dots, boundaries, wickets)
- Filter by batter hand, phase

---

## Phase 9: Venue Vibes Audit

**Task:** Compare Venue Vibes card data with main Venue Analysis page

**Check:**
- Par scores match
- Chase win percentages match
- Match counts match
- Both use delivery_details table

---

## Priority Summary

| Phase | Priority | Time | Description |
|-------|----------|------|-------------|
| 1.1 | HIGH | 1-2h | Grey tint fix |
| 1.2 | HIGH | 30m | group_by error fix |
| 2.x | MEDIUM | 6h | Card migrations |
| 3 | MEDIUM | 2h | Middle Overs Squeeze |
| 4.x | MEDIUM | 3h | Metric enhancements |
| 5.x | MEDIUM | 1h | Query recreation |
| 6 | MEDIUM | 2h | Player aliases |
| 7 | LOW | 2h | Filter menu |
| 8 | LOW | 4h | Profile enhancements |
| 9 | LOW | 1h | Venue audit |

**Total: ~22-24 hours**

---

*Document Version: 2.0*  
*Last Updated: December 2025*
