# Enhanced Error Logging for Phase Stats API

We've added comprehensive error logging to identify the exact failure point in the phase stats API.

## Files Added:

1. **services/teams_enhanced_logging.py** - Enhanced version with detailed logging
2. **debug_enhanced_phase_stats.py** - API testing script with detailed output
3. **test_database_direct.py** - Direct database query testing

## Setup:

The router has been temporarily modified to use the enhanced logging version.

## How to Debug:

### Step 1: Test Database Directly
```bash
cd /Users/adityabalaji/cdt/cricket-data-thing
python test_database_direct.py
```

This will test the SQL queries directly and show if there are database-level issues.

### Step 2: Test API with Enhanced Logging
```bash
# In one terminal, start the server:
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, run the debug script:
python debug_enhanced_phase_stats.py
```

### Step 3: Check Server Logs

Look for detailed logs in the server terminal. The enhanced logging will show:
- **Step 1:** Team variations lookup
- **Step 2:** Team type determination (international vs league)
- **Step 3:** Team phase stats query execution
- **Step 4:** Data validation
- **Step 5:** Benchmark context determination
- **Step 6:** Benchmark query execution
- **Step 7:** Normalization calculations
- **Step 8:** Response formatting

## What to Look For:

### Common Issues:

1. **SQL Syntax Error:** Look for "TEAM QUERY FAILED" or "BENCHMARK QUERY FAILED"
2. **Parameter Binding Issues:** Check if team_variations array is properly formatted
3. **Percentile Function Issues:** PostgreSQL vs other DB differences
4. **NULL Division:** Issues with NULLIF functions
5. **Data Type Mismatches:** Casting errors in complex calculations

### Expected Log Output:

```
INFO - === STARTING PHASE STATS SERVICE ===
INFO - Team: RCB, Start: 2023-01-01, End: 2025-09-06
INFO - Step 1: Getting team variations
INFO - Team variations: ['Royal Challengers Bangalore', 'Royal Challengers Bengaluru']
INFO - Step 2: Determining team type
INFO - Is international team: False
INFO - Step 3: Executing team phase stats query
INFO - Team query parameters: {...}
INFO - Team query executed successfully
...
```

### If You See an Error:

1. **Note the step number** where it fails
2. **Copy the exact error message** and SQL query
3. **Check the parameters** being passed
4. **Look for the specific SQL error** in the traceback

## Quick Fixes for Common Issues:

### Issue 1: Array Parameter Binding
If you see errors related to `team_variations`, the issue might be PostgreSQL array handling.

### Issue 2: Percentile Functions
If percentile_cont fails, we may need to use a different approach for calculating percentiles.

### Issue 3: Complex CTE Query
If the benchmark query fails, we can simplify it step by step.

## Reverting Changes:

Once we identify and fix the issue, revert the router back to the original:

```python
# In routers/teams.py, change back to:
from services.teams import get_team_matches_service, get_team_batting_stats_service, get_team_phase_stats_service

# And use:
phase_stats = get_team_phase_stats_service(
    team_name=team_name,
    start_date=start_date,
    end_date=end_date,
    db=db
)
```

## Next Steps:

Run the debug scripts and report back with:
1. **Which step fails** (if any)
2. **The exact error message**
3. **The SQL query and parameters** that caused the failure

This will allow us to create a targeted fix for the specific issue.
