# Delivery Data Fix Summary

## Problem Identified

The `/venue_notes`, `/venue-bowling-stats`, `/venues/{venue}/teams/{team1}/{team2}/history`, and `/teams/{team1}/{team2}/matchups` endpoints were returning zero/empty values for recent matches (after 2025-11-27).

### Root Cause

**Data is split across two tables:**
- **`deliveries` table**: Contains data from 2005-02-17 to 2025-11-27 (7,974 matches)
- **`delivery_details` table**: Contains data from 2015-01-01 to 2025-12-27 (9,350 matches)

**The endpoints were only querying `deliveries`**, which doesn't have recent match data.

Recent matches (like the 2025-12-27 Paarl Royals match) exist ONLY in `delivery_details`, not in `deliveries`.

## Solution Implemented

### 1. Created Dual-Table Service (`services/delivery_data_service.py`)

A new shared service that:
- Automatically routes queries to the correct table based on date range
- Provides unified functions for common queries (venue stats, match totals, etc.)
- Handles the differences in column names between tables:
  - `deliveries`: uses `m.venue`, `d.runs_off_bat + d.extras`, `d.match_id`
  - `delivery_details`: uses `dd.ground`, `dd.score`, `dd.p_match`

### 2. Updated `/venue_notes` Endpoint

**Before:**
- Hardcoded to query only `deliveries` table
- Had a bug: `competition_filter = "AND false"` when no leagues/international specified

**After:**
- Uses `get_venue_match_stats()` from the new service
- Automatically queries `delivery_details` for 2015+ data
- Returns actual data for recent matches

### 3. Routing Logic

```python
def should_use_delivery_details(start_date, end_date):
    # Query entirely before 2015 → use deliveries
    # Query entirely after 2025-11-27 → use delivery_details
    # Query from 2015+ → use delivery_details (has more complete/recent data)
```

## Testing Results

✅ **Test Case: Boland Park, Paarl (2025-12-01 to 2026-01-02)**

**Before Fix:**
```json
{
  "total_matches": 0,
  "highest_total": 0,
  "average_first_innings": 0.0
}
```

**After Fix:**
```json
{
  "total_matches": 1,
  "highest_total": 186,
  "average_first_innings": 186.0
}
```

## Remaining Work

### Endpoints Still Need Updating:

1. ❌ `/venue-bowling-stats` - Still queries `deliveries` only
2. ❌ `/venues/{venue}/teams/{team1}/{team2}/history` - Still queries `deliveries` only
3. ❌ `/teams/{team1}/{team2}/matchups` - Needs dual-table support

These endpoints will continue to return empty/zero values for recent matches until updated.

### Phase-Wise Stats

The `/venue_notes` endpoint currently returns empty `phase_wise_stats` because we simplified the initial fix. The phase-wise stats query needs to be added to the dual-table service.

## Data Sync Note

### Player Names

The two tables use **different player name formats**:
- `deliveries`: Abbreviated names ("AJ Finch", "V Kohli")
- `delivery_details`: Full names ("Aaron Finch", "Virat Kohli")

The `player_aliases` table (3,625 mappings) is already used by search and query endpoints to handle this. The `batting_stats` and `bowling_stats` tables use the abbreviated format.

## Files Modified

1. **Created:** `services/delivery_data_service.py` - Dual-table routing service
2. **Modified:** `main.py` - Updated `/venue_notes` endpoint to use new service

## Next Steps

1. Update remaining endpoints to use `delivery_data_service.py`
2. Add phase-wise stats support to the dual-table service
3. Consider updating the data pipeline to keep `deliveries` table current
4. Or, standardize on `delivery_details` as the primary table for all recent data

## Performance Note

The `delivery_details` table has 2.1M records vs `deliveries` with 1.8M records. Queries should perform similarly, but consider adding indexes on:
- `delivery_details.ground` (for venue queries)
- `delivery_details.match_date` (for date range queries)
- `delivery_details.competition` (for league filtering)
