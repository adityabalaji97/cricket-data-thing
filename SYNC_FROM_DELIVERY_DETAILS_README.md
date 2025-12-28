# Syncing from Delivery Details

This guide explains how to populate the `matches`, `batting_stats`, and `bowling_stats` tables from the `delivery_details` table when you have match IDs in `delivery_details` that don't exist in the legacy tables.

## Background

The app uses two data sources:
1. **Legacy Cricsheet JSON** → populates `matches`, `deliveries`, then `batting_stats`/`bowling_stats`
2. **Enhanced BBB Dataset** → populates `delivery_details` with richer data (wagon wheel, predictions, etc.)

Sometimes matches exist in `delivery_details` but not in the legacy tables. This sync process bridges that gap.

## Quick Start

```bash
# 1. Check current sync status
python sync_from_delivery_details.py --check

# 2. Optional: Explore the delivery_details data
python explore_delivery_details.py

# 3. Sync matches and stats (with limit for testing)
python sync_from_delivery_details.py --sync-all --limit 100

# 4. Full sync (after testing)
python sync_from_delivery_details.py --sync-all --confirm

# 5. Post-sync standardization
python venue_standardization.py
python fix_league_names.py
python calculate_missing_elo.py --confirm
```

## Scripts

### `sync_from_delivery_details.py`
Main sync orchestrator.

| Option | Description |
|--------|-------------|
| `--check` | Show sync status only (no changes) |
| `--sync-matches` | Create missing matches from delivery_details |
| `--sync-stats` | Create batting/bowling stats for matches without them |
| `--sync-all` | Full sync: matches + stats |
| `--limit N` | Process only N matches (for testing) |
| `--batch-size N` | Batch size for database inserts (default: 100) |
| `--confirm` | Skip confirmation prompt |

### `sync_stats_from_dd.py`
Creates `batting_stats` and `bowling_stats` by aggregating `delivery_details` data.

Can be run standalone:
```bash
python sync_stats_from_dd.py --limit 50
```

### `explore_delivery_details.py`
Diagnostic tool to understand the data in `delivery_details`:
- Shows sample records
- Displays toss field formats
- Lists competitions
- Shows dismissal types

## Data Mapping

### delivery_details → matches

| delivery_details | matches | Notes |
|-----------------|---------|-------|
| `match_id` | `id` | Direct |
| `date` | `date` | Direct |
| `ground` | `venue` | Direct |
| `country` | `city` | Approximation |
| `competition` | `competition` | Direct |
| `winner` | `winner` | Direct |
| `toss` | `toss_winner`, `toss_decision` | Parsed |
| `batting_team` (innings 1) | `team1` | Derived |
| `bowling_team` (innings 1) | `team2` | Derived |
| `max_balls / 6` | `overs` | Calculated |

**Fields set to NULL** (not available in delivery_details):
- `event_match_number`
- `outcome` (JSON with margin details)
- `player_of_match`

### delivery_details → batting_stats

| delivery_details | batting_stats | Notes |
|-----------------|---------------|-------|
| `batter` | `striker` | Direct |
| `batting_team` | `batting_team` | Direct |
| `score` | Aggregated to `runs` | Sum |
| Count where score=0 | `dots` | Count |
| Count where score=4 | `fours` | Count |
| Count where score=6 | `sixes` | Count |
| `out` | `wickets` | Count where true |

Phase boundaries (T20):
- Powerplay: overs 0-5
- Middle: overs 6-14
- Death: overs 15+

### delivery_details → bowling_stats

Similar mapping with bowler-specific calculations:
- Overs = legal deliveries / 6
- Wickets only count bowler-credited dismissals (bowled, caught, lbw, etc.)
- Economy = runs_conceded / overs

## Toss Parsing

The `toss` field in delivery_details can have various formats:
- `"Team Name, bat"`
- `"Team Name, field"`
- `"Team Name elected to bat"`
- Just team name

The sync script handles all these formats.

## Post-Sync Steps

After syncing, run the standard data pipeline:

1. **Venue Standardization**
   ```bash
   python venue_standardization.py
   ```
   Normalizes venue names (e.g., "Arun Jaitley Stadium" → "Feroz Shah Kotla")

2. **League Name Fixes**
   ```bash
   python fix_league_names.py
   ```
   Standardizes league names

3. **ELO Calculation**
   ```bash
   python calculate_missing_elo.py --confirm
   ```
   Calculates ELO ratings for new matches

## Troubleshooting

### "Could not determine both teams"
The match has only one unique team in its deliveries. This can happen with incomplete data.

### Fantasy points are 0
Check that the `fantasy_points_v2.py` module is properly imported and the stats have valid data.

### Missing stats for some matches
Run `--sync-stats` separately after ensuring matches exist:
```bash
python sync_from_delivery_details.py --sync-stats
```

## Complete Pipeline

For a fresh sync of everything:

```bash
# Step 1: Check status
python sync_from_delivery_details.py --check

# Step 2: Full sync
python sync_from_delivery_details.py --sync-all --confirm

# Step 3: Standardize venues
python venue_standardization.py

# Step 4: Fix league names
python fix_league_names.py

# Step 5: Calculate ELO
python calculate_missing_elo.py --confirm

# Step 6: Verify
python sync_from_delivery_details.py --check
```
