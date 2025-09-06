# Bowler Data Management Scripts

This collection of scripts helps identify and update missing bowler information in the cricket database.

## Scripts Overview

### 1. `analyze_bowler_data.py` - Main Analysis Script
**Purpose**: Identifies bowlers with missing or incomplete bowling information

**Features**:
- Finds bowlers in deliveries table who don't exist in players table
- Identifies bowlers with missing `bowler_type`, `bowl_hand`, or `bowl_type` fields
- Generates CSV files for manual data entry
- Provides detailed summary reports with delivery counts for prioritization

**Usage**:
```bash
python analyze_bowler_data.py
```

**Output Files**:
- `missing_bowlers_YYYYMMDD_HHMMSS.csv` - Bowlers not in players table
- `incomplete_bowlers_YYYYMMDD_HHMMSS.csv` - Bowlers with partial info

### 2. `update_bowler_info.py` - Update Script
**Purpose**: Updates bowler information using filled CSV files

**Features**:
- Processes CSV files with manual data entry
- Adds new players to database
- Updates existing players with missing information
- Interactive single-player update mode
- Comprehensive error handling and reporting

**Usage**:
```bash
# Process missing bowlers CSV (adds new players)
python update_bowler_info.py --csv missing_bowlers_20241207_123456.csv

# Process incomplete bowlers CSV (updates existing players)
python update_bowler_info.py --csv incomplete_bowlers_20241207_123456.csv

# Interactive single bowler update
python update_bowler_info.py --single-update "Player Name"
```

### 3. `bowling_reference_guide.py` - Reference Tool
**Purpose**: Provides bowling classification reference and lookup tools

**Features**:
- Complete bowling type classifications
- Example combinations for well-known players
- Interactive lookup tool for suggestions
- Tips for manual data entry

**Usage**:
```bash
python bowling_reference_guide.py
```

## Workflow for Manual Updates

### Step 1: Analyze Current Data
```bash
python analyze_bowler_data.py
```

This will:
- Generate two CSV files
- Print a summary report showing the scope of missing data
- Prioritize bowlers by delivery count (most frequent first)

### Step 2: Fill CSV Files Manually

#### For `missing_bowlers_*.csv`:
- Use the bowling reference guide for classifications
- Focus on high delivery count bowlers first
- Fields to fill:
  - `bowler_type`: Primary category (Fast, Spin, etc.)
  - `bowl_hand`: R or L
  - `bowl_type`: Detailed code (RF, SLA, etc.)
  - `nationality`: Optional
  - `notes`: Any additional information

#### For `incomplete_bowlers_*.csv`:
- Review current information in the CSV
- Fill only the missing fields in the `new_*` columns
- Leave existing correct information unchanged

### Step 3: Update Database
```bash
# Update with filled CSV files
python update_bowler_info.py --csv missing_bowlers_20241207_123456.csv
python update_bowler_info.py --csv incomplete_bowlers_20241207_123456.csv
```

### Step 4: Verify Updates
```bash
# Re-run analysis to check progress
python analyze_bowler_data.py
```

## CSV File Formats

### Missing Bowlers CSV
```csv
bowler_name,delivery_count,bowler_type,bowl_hand,bowl_type,bowling_type,nationality,notes
Jasprit Bumrah,1234,Fast,R,RF,,India,
```

### Incomplete Bowlers CSV
```csv
bowler_name,delivery_count,current_bowler_type,current_bowl_hand,current_bowl_type,current_bowling_type,missing_fields,new_bowler_type,new_bowl_hand,new_bowl_type,notes
Player Name,567,Fast,,RF,,bowl_hand,Fast,R,RF,
```

## Bowling Classification Reference

### Primary Categories (bowler_type)
- `Fast`: Fast bowlers (>140 kmph)
- `Fast Medium`: Fast medium bowlers (130-140 kmph)
- `Medium`: Medium pace bowlers (120-130 kmph)
- `Off Spin`: Off spin bowlers
- `Leg Spin`: Leg spin bowlers
- `Left-arm Orthodox`: Left-arm orthodox spinners
- `Part-time`: Part-time bowlers

### Hand Classification (bowl_hand)
- `R`: Right-arm
- `L`: Left-arm

### Detailed Types (bowl_type)
- `RF`: Right-arm Fast
- `LF`: Left-arm Fast
- `RM`: Right-arm Medium
- `ROB`: Right-arm Off Break
- `RLB`: Right-arm Leg Break
- `SLA`: Slow Left-arm Orthodox
- `SLAC`: Slow Left-arm Chinaman

## Tips for Manual Entry

1. **Prioritize by Delivery Count**: Focus on bowlers with the most deliveries first
2. **Use Cricket References**: Check cricinfo, espncricinfo, or similar sources for player information
3. **Common Patterns**:
   - Fast bowlers: Usually RF/LF
   - Off spinners: Usually ROB
   - Leg spinners: Usually RLB
   - Left-arm orthodox: Usually SLA
4. **Part-time Bowlers**: Many batsmen bowl occasionally - classify as "Part-time"
5. **When in Doubt**: Use the interactive reference tool or ask for help

## Error Handling

The scripts include comprehensive error handling:
- Database connection issues
- CSV format problems
- Duplicate entries
- Invalid data types
- Transaction rollbacks on errors

## Data Quality

The analysis script provides quality metrics:
- Total bowlers identified
- Coverage percentages
- Sample size validation
- Missing field breakdowns

## Future Enhancements

Potential improvements:
- Automated lookup using external cricket APIs
- Machine learning suggestions based on name patterns
- Integration with real-time cricket data feeds
- Bulk import from cricket databases

---

For questions or issues, refer to the script documentation or run scripts with `--help` flag.
