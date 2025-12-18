# Query Builder Migration to delivery_details Table

## Implementation Plan

**Date Created:** December 18, 2025  
**Priority:** HIGH - Hero Feature  
**Estimated Effort:** 2-3 hours  

---

## Overview

This document outlines the step-by-step migration of the Query Builder from the `deliveries` table to the new `delivery_details` table, which contains richer ball-by-ball data including wagon wheel coordinates, line, length, shot type, and control metrics.

---

## Table Schema Comparison

### Current: `deliveries` table
```
match_id, innings, over, ball, batter, bowler, runs_off_bat, extras, 
wicket_type, batting_team, bowling_team, crease_combo, ball_direction, 
bowler_type, striker_batter_type, non_striker_batter_type
```

### New: `delivery_details` table
```
p_match, inns, over, ball, bat, bowl, score, batruns, bowlruns,
team_bat, team_bowl, bat_hand, bowl_style, bowl_kind, 
wagon_x, wagon_y, wagon_zone, line, length, shot, control,
pred_score, win_prob, competition, year, ground, country, winner, toss,
outcome, out, dismissal, wide, noball, byes, legbyes, ...
```

### Key Column Mappings
| Old (deliveries) | New (delivery_details) | Notes |
|------------------|------------------------|-------|
| match_id | p_match | Same values |
| innings | inns | Same values |
| batter | bat | Full names in new |
| bowler | bowl | Full names in new |
| runs_off_bat | batruns | Batter runs only |
| batting_team | team_bat | |
| bowling_team | team_bowl | |
| striker_batter_type | bat_hand | RHB/LHB |
| bowler_type | bowl_style | RF/RM/SLA/OB etc. |
| N/A | bowl_kind | pace bowler/spin bowler/mixture |
| N/A | line | ON_THE_STUMPS, OUTSIDE_OFFSTUMP, etc. |
| N/A | length | GOOD_LENGTH, YORKER, FULL, etc. |
| N/A | shot | COVER_DRIVE, FLICK, DEFENDED, etc. |
| N/A | control | 0 or 1 |
| N/A | wagon_x, wagon_y, wagon_zone | Wagon wheel data |
| wicket_type | dismissal | |
| extras | wide + noball + byes + legbyes | Computed |

---

## Files to Modify

All files are under: `/Users/adityabalaji/cdt/cricket-data-thing/`

| File | Type | Changes |
|------|------|---------|
| `services/query_builder.py` | Backend | Major rewrite - switch to delivery_details |
| `routers/query_builder.py` | Backend | Add new filter parameters |
| `src/components/QueryFilters.jsx` | Frontend | Add new filter UI elements |
| `src/components/QueryBuilder.jsx` | Frontend | Update filter state |

---

## Step-by-Step Implementation

### STEP 1: Update Backend Service (`services/query_builder.py`)

**Location:** `/Users/adityabalaji/cdt/cricket-data-thing/services/query_builder.py`

#### 1.1 Update Column Mapping Function

Replace `get_grouping_columns_map()` with new mappings:

```python
def get_grouping_columns_map():
    """Map user-friendly group_by values to delivery_details column names."""
    return {
        # Location
        "venue": "dd.ground",
        "country": "dd.country",
        
        # Match identifiers
        "match_id": "dd.p_match",
        "competition": "dd.competition",
        "year": "dd.year",
        
        # Teams
        "batting_team": "dd.team_bat",
        "bowling_team": "dd.team_bowl",
        
        # Players
        "batter": "dd.bat",
        "bowler": "dd.bowl",
        
        # Innings/Phase
        "innings": "dd.inns",
        "phase": "CASE WHEN dd.over < 6 THEN 'powerplay' WHEN dd.over < 15 THEN 'middle' ELSE 'death' END",
        
        # Batter attributes
        "bat_hand": "dd.bat_hand",
        
        # Bowler attributes  
        "bowl_style": "dd.bowl_style",
        "bowl_kind": "dd.bowl_kind",
        
        # NEW: Delivery details
        "line": "dd.line",
        "length": "dd.length",
        "shot": "dd.shot",
        "control": "dd.control",
        "wagon_zone": "dd.wagon_zone",
    }
```

#### 1.2 Update WHERE Clause Builder

Modify `build_where_clause()` to use `delivery_details` columns:

**Key changes:**
- Change table alias from `d` to `dd`
- Remove JOIN with `matches` table (delivery_details has all match info)
- Update column names per mapping above
- Add new filter conditions for line, length, shot, control, wagon_zone

```python
# Example filter updates:
if bat_hand:
    conditions.append("dd.bat_hand = :bat_hand")
    params["bat_hand"] = bat_hand

if line:
    conditions.append("dd.line = ANY(:line)")
    params["line"] = line

if length:
    conditions.append("dd.length = ANY(:length)")
    params["length"] = length

if shot:
    conditions.append("dd.shot = ANY(:shot)")
    params["shot"] = shot

if control is not None:
    conditions.append("dd.control = :control")
    params["control"] = control

if wagon_zone:
    conditions.append("dd.wagon_zone = ANY(:wagon_zone)")
    params["wagon_zone"] = wagon_zone

if bowl_kind:
    conditions.append("dd.bowl_kind = ANY(:bowl_kind)")
    params["bowl_kind"] = bowl_kind
```

#### 1.3 Update Ungrouped Query

Modify `handle_ungrouped_query()`:

```python
main_query = f"""
    SELECT 
        dd.p_match as match_id,
        dd.inns as innings,
        dd.over,
        dd.ball,
        dd.bat as batter,
        dd.bowl as bowler,
        dd.batruns as runs_off_bat,
        dd.team_bat as batting_team,
        dd.team_bowl as bowling_team,
        dd.bat_hand,
        dd.bowl_style,
        dd.bowl_kind,
        dd.line,
        dd.length,
        dd.shot,
        dd.control,
        dd.wagon_x,
        dd.wagon_y,
        dd.wagon_zone,
        dd.dismissal as wicket_type,
        dd.ground as venue,
        dd.match_date as date,
        dd.competition,
        dd.year
    FROM delivery_details dd
    {where_clause}
    ORDER BY dd.year DESC, dd.p_match, dd.inns, dd.over, dd.ball
    LIMIT :limit
    OFFSET :offset
"""
```

#### 1.4 Update Grouped Query Aggregations

Modify `handle_grouped_query()`:

```python
# Update runs calculation
runs_calculation = "SUM(dd.batruns)" if use_runs_off_bat_only else "SUM(dd.score)"

# Update aggregation metrics
aggregation_query = f"""
    SELECT 
        {select_group_clause},
        COUNT(*) as balls,
        {runs_calculation} as runs,
        SUM(CASE WHEN dd.dismissal IS NOT NULL AND dd.dismissal != '' THEN 1 ELSE 0 END) as wickets,
        SUM(CASE WHEN dd.batruns = 0 AND dd.wide = 0 AND dd.noball = 0 THEN 1 ELSE 0 END) as dots,
        SUM(CASE WHEN dd.batruns IN (4, 6) THEN 1 ELSE 0 END) as boundaries,
        SUM(CASE WHEN dd.batruns = 4 THEN 1 ELSE 0 END) as fours,
        SUM(CASE WHEN dd.batruns = 6 THEN 1 ELSE 0 END) as sixes,
        -- NEW: Control percentage (when control data available)
        CASE WHEN SUM(CASE WHEN dd.control IS NOT NULL THEN 1 ELSE 0 END) > 0
            THEN (CAST(SUM(CASE WHEN dd.control = 1 THEN 1 ELSE 0 END) AS DECIMAL) * 100.0) / 
                  SUM(CASE WHEN dd.control IS NOT NULL THEN 1 ELSE 0 END)
            ELSE NULL END as control_percentage,
        ... (rest of metrics)
    FROM delivery_details dd
    {where_clause}
    GROUP BY {group_by_clause}
    {having_clause}
    ORDER BY runs DESC
    LIMIT :limit
    OFFSET :offset
"""
```

---

### STEP 2: Update Backend Router (`routers/query_builder.py`)

**Location:** `/Users/adityabalaji/cdt/cricket-data-thing/routers/query_builder.py`

#### 2.1 Add New Query Parameters

Add these new parameters to `query_deliveries()` function:

```python
@router.get("/deliveries")
def query_deliveries(
    # ... existing params ...
    
    # NEW: Delivery detail filters
    line: List[str] = Query(default=[], description="Filter by line (ON_THE_STUMPS, OUTSIDE_OFFSTUMP, DOWN_LEG, etc.)"),
    length: List[str] = Query(default=[], description="Filter by length (GOOD_LENGTH, YORKER, FULL, SHORT, etc.)"),
    shot: List[str] = Query(default=[], description="Filter by shot type (COVER_DRIVE, FLICK, PULL, etc.)"),
    control: Optional[int] = Query(default=None, ge=0, le=1, description="Filter by shot control (0=no control, 1=controlled)"),
    wagon_zone: List[int] = Query(default=[], description="Filter by wagon wheel zone (0-8)"),
    bowl_kind: List[str] = Query(default=[], description="Filter by bowl kind (pace bowler, spin bowler, mixture/unknown)"),
    bat_hand: Optional[str] = Query(default=None, description="Filter by batting hand (LHB, RHB)"),
    
    # ... rest of params ...
):
```

#### 2.2 Update Columns Endpoint

Update `get_available_columns()` to return new options:

```python
@router.get("/deliveries/columns")
def get_available_columns(db: Session = Depends(get_session)):
    try:
        from sqlalchemy.sql import text
        
        # Fetch dynamic options from delivery_details
        line_query = text("SELECT DISTINCT line FROM delivery_details WHERE line IS NOT NULL ORDER BY line")
        length_query = text("SELECT DISTINCT length FROM delivery_details WHERE length IS NOT NULL ORDER BY length")
        shot_query = text("SELECT DISTINCT shot FROM delivery_details WHERE shot IS NOT NULL ORDER BY shot")
        bowl_style_query = text("SELECT DISTINCT bowl_style FROM delivery_details WHERE bowl_style IS NOT NULL ORDER BY bowl_style")
        bowl_kind_query = text("SELECT DISTINCT bowl_kind FROM delivery_details WHERE bowl_kind IS NOT NULL ORDER BY bowl_kind")
        
        line_options = [row[0] for row in db.execute(line_query).fetchall()]
        length_options = [row[0] for row in db.execute(length_query).fetchall()]
        shot_options = [row[0] for row in db.execute(shot_query).fetchall()]
        bowl_style_options = [row[0] for row in db.execute(bowl_style_query).fetchall()]
        bowl_kind_options = [row[0] for row in db.execute(bowl_kind_query).fetchall()]
        
        return {
            "filter_columns": {
                "basic": ["venue", "start_date", "end_date", "leagues", "teams", "batting_teams", "bowling_teams", "players", "batters", "bowlers"],
                "match": ["innings", "over_min", "over_max"],
                "batter": ["bat_hand"],
                "bowler": ["bowl_style", "bowl_kind"],
                "delivery": ["line", "length", "shot", "control", "wagon_zone"],
                "grouped_filters": ["min_balls", "max_balls", "min_runs", "max_runs"]
            },
            "group_by_columns": [
                "venue", "country", "match_id", "competition", "year",
                "batting_team", "bowling_team", "batter", "bowler",
                "innings", "phase",
                "bat_hand", "bowl_style", "bowl_kind",
                "line", "length", "shot", "control", "wagon_zone"
            ],
            "line_options": line_options,
            "length_options": length_options,
            "shot_options": shot_options,
            "bat_hand_options": ["LHB", "RHB"],
            "bowl_style_options": bowl_style_options,
            "bowl_kind_options": bowl_kind_options,
            "wagon_zone_options": [0, 1, 2, 3, 4, 5, 6, 7, 8],
            "control_options": [0, 1],
            "innings_options": [1, 2],
            
            # DEPRECATED - keep for backward compatibility
            "crease_combo_options": [],
            "ball_direction_options": [],
            "batter_type_options": ["LHB", "RHB"],
            "common_bowler_types": bowl_style_options,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### STEP 3: Update Frontend State (`src/components/QueryBuilder.jsx`)

**Location:** `/Users/adityabalaji/cdt/cricket-data-thing/src/components/QueryBuilder.jsx`

#### 3.1 Update Initial Filter State

```javascript
const [filters, setFilters] = useState({
    // Basic filters
    venue: null,
    start_date: null,
    end_date: null,
    leagues: [],
    teams: [],
    batting_teams: [],
    bowling_teams: [],
    players: [],
    batters: [],
    bowlers: [],
    
    // Match context
    innings: null,
    over_min: null,
    over_max: null,
    
    // Batter filters
    bat_hand: null,
    
    // Bowler filters
    bowl_style: [],      // Renamed from bowler_type
    bowl_kind: [],       // NEW
    
    // NEW: Delivery detail filters
    line: [],
    length: [],
    shot: [],
    control: null,
    wagon_zone: [],
    
    // Grouped result filters
    min_balls: null,
    max_balls: null,
    min_runs: null,
    max_runs: null,
    
    // Pagination
    limit: 1000,
    offset: 0,
    
    // International matches
    include_international: false,
    top_teams: 10,
    
    // Summary rows
    show_summary_rows: false
});
```

#### 3.2 Update Clear Filters Function

Update `clearFilters()` to reset new fields.

#### 3.3 Update Prefilled Queries

Update `PREFILLED_QUERIES` array with new filter names and add new example queries showcasing line/length/shot:

```javascript
{
    title: "Full length balls to RHB batters - shot distribution",
    description: "See what shots RHB batters play to full length deliveries",
    filters: {
      bat_hand: "RHB",
      length: ["FULL"],
      min_balls: 50
    },
    groupBy: ["shot"],
    tags: ["Length", "Shot", "RHB", "Full"]
},
{
    title: "Controlled vs uncontrolled shots by wagon zone",
    description: "Analyze where batters hit with and without control",
    filters: {
      min_balls: 100
    },
    groupBy: ["control", "wagon_zone"],
    tags: ["Control", "Wagon Wheel", "Shot Quality"]
}
```

---

### STEP 4: Update Frontend Filters (`src/components/QueryFilters.jsx`)

**Location:** `/Users/adityabalaji/cdt/cricket-data-thing/src/components/QueryFilters.jsx`

#### 4.1 Add New Filter UI Elements

Add these new filter components in the appropriate Grid rows:

```jsx
{/* NEW: Line Filter */}
<Grid item xs={12} sm={6} md={3}>
  <Autocomplete
    multiple
    value={filters.line || []}
    onChange={(e, value) => handleFilterChange('line', value)}
    options={availableColumns?.line_options || []}
    renderTags={(value, getTagProps) =>
      value.map((option, index) => (
        <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
      ))
    }
    renderInput={(params) => (
      <TextField {...params} label="Line" size="small" />
    )}
  />
</Grid>

{/* NEW: Length Filter */}
<Grid item xs={12} sm={6} md={3}>
  <Autocomplete
    multiple
    value={filters.length || []}
    onChange={(e, value) => handleFilterChange('length', value)}
    options={availableColumns?.length_options || []}
    renderTags={(value, getTagProps) =>
      value.map((option, index) => (
        <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
      ))
    }
    renderInput={(params) => (
      <TextField {...params} label="Length" size="small" />
    )}
  />
</Grid>

{/* NEW: Shot Filter */}
<Grid item xs={12} sm={6} md={3}>
  <Autocomplete
    multiple
    value={filters.shot || []}
    onChange={(e, value) => handleFilterChange('shot', value)}
    options={availableColumns?.shot_options || []}
    renderTags={(value, getTagProps) =>
      value.map((option, index) => (
        <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
      ))
    }
    renderInput={(params) => (
      <TextField {...params} label="Shot Type" size="small" />
    )}
  />
</Grid>

{/* NEW: Control Filter */}
<Grid item xs={12} sm={6} md={3}>
  <FormControl size="small" fullWidth>
    <InputLabel>Shot Control</InputLabel>
    <Select
      value={filters.control ?? ''}
      onChange={(e) => handleFilterChange('control', e.target.value === '' ? null : parseInt(e.target.value))}
      label="Shot Control"
    >
      <MenuItem value="">All</MenuItem>
      <MenuItem value={1}>Controlled</MenuItem>
      <MenuItem value={0}>Uncontrolled</MenuItem>
    </Select>
  </FormControl>
</Grid>

{/* NEW: Wagon Zone Filter */}
<Grid item xs={12} sm={6} md={3}>
  <Autocomplete
    multiple
    value={filters.wagon_zone || []}
    onChange={(e, value) => handleFilterChange('wagon_zone', value)}
    options={[0, 1, 2, 3, 4, 5, 6, 7, 8]}
    getOptionLabel={(option) => `Zone ${option}`}
    renderTags={(value, getTagProps) =>
      value.map((option, index) => (
        <Chip variant="outlined" label={`Z${option}`} size="small" {...getTagProps({ index })} />
      ))
    }
    renderInput={(params) => (
      <TextField {...params} label="Wagon Zone" size="small" />
    )}
  />
</Grid>

{/* NEW: Bowl Kind Filter */}
<Grid item xs={12} sm={6} md={3}>
  <Autocomplete
    multiple
    value={filters.bowl_kind || []}
    onChange={(e, value) => handleFilterChange('bowl_kind', value)}
    options={availableColumns?.bowl_kind_options || []}
    renderTags={(value, getTagProps) =>
      value.map((option, index) => (
        <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
      ))
    }
    renderInput={(params) => (
      <TextField {...params} label="Bowl Kind" size="small" />
    )}
  />
</Grid>

{/* RENAMED: Bat Hand (was Striker Type) */}
<Grid item xs={12} sm={6} md={3}>
  <FormControl size="small" fullWidth>
    <InputLabel>Bat Hand</InputLabel>
    <Select
      value={filters.bat_hand || ''}
      onChange={(e) => handleFilterChange('bat_hand', e.target.value || null)}
      label="Bat Hand"
    >
      <MenuItem value="">All</MenuItem>
      <MenuItem value="RHB">Right Hand (RHB)</MenuItem>
      <MenuItem value="LHB">Left Hand (LHB)</MenuItem>
    </Select>
  </FormControl>
</Grid>

{/* RENAMED: Bowl Style (was Bowler Type) */}
<Grid item xs={12} sm={6} md={3}>
  <Autocomplete
    multiple
    value={filters.bowl_style || []}
    onChange={(e, value) => handleFilterChange('bowl_style', value)}
    options={availableColumns?.bowl_style_options || availableColumns?.common_bowler_types || []}
    renderTags={(value, getTagProps) =>
      value.map((option, index) => (
        <Chip variant="outlined" label={option} size="small" {...getTagProps({ index })} />
      ))
    }
    renderInput={(params) => (
      <TextField {...params} label="Bowl Style" size="small" />
    )}
  />
</Grid>
```

#### 4.2 Remove Deprecated Filters

Remove or hide these filters (no longer in delivery_details):
- `crease_combo`
- `ball_direction`
- `striker_batter_type`
- `non_striker_batter_type`

---

### STEP 5: Update URL Parameter Parser (if applicable)

**Location:** `/Users/adityabalaji/cdt/cricket-data-thing/src/utils/urlParamParser.js`

Add parsing for new filter parameters to maintain shareable URLs.

---

## Testing Checklist

### Backend Tests
- [ ] `/query/deliveries/columns` returns new options (line, length, shot, etc.)
- [ ] Ungrouped query returns delivery_details columns
- [ ] Grouped query aggregations work correctly
- [ ] Filtering by line works
- [ ] Filtering by length works
- [ ] Filtering by shot works
- [ ] Filtering by control works
- [ ] Filtering by wagon_zone works
- [ ] Filtering by bowl_kind works
- [ ] Grouping by new columns works
- [ ] control_percentage appears in grouped results

### Frontend Tests
- [ ] New filter dropdowns appear and populate
- [ ] Selecting filters updates state correctly
- [ ] Execute query sends new parameters
- [ ] Results display new columns
- [ ] Prefilled queries work with new schema
- [ ] Clear filters resets new fields
- [ ] URL sharing works with new params

---

## Rollback Plan

If issues arise:
1. Keep old service file as `query_builder_old.py`
2. Router can switch between services via feature flag
3. Frontend can check API version and show appropriate filters

---

## Data Coverage Notes

From validation report:
- **line/length:** 38% coverage (non-null)
- **shot:** 50% coverage
- **control:** 50% coverage
- **wagon_x/y/zone:** 99% coverage

UI should indicate when filtering on sparse columns may reduce results significantly.

---

## Questions to Resolve Before Implementation

1. Should we keep backward compatibility with old filter names (`bowler_type` → `bowl_style`)?
2. Should we show a warning when filtering on columns with low coverage (line/length)?
3. Do we want to add a wagon wheel visualization component?

---

## Appendix: Wagon Zone Reference

```
     8   1   2
      \  |  /
   7 -- [B] -- 3
      /  |  \
     6   5   4
```

Zone 0 = No shot / unknown
