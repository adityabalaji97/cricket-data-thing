"""
Update players table with bat_hand/bowl_style from delivery_details.

Usage:
    python scripts/update_players_from_new_data.py --db-url "$DATABASE_URL" --dry-run
    python scripts/update_players_from_new_data.py --db-url "$DATABASE_URL"
    
    # Using environment variable:
    python scripts/update_players_from_new_data.py
"""

import os
import sys
import argparse
from collections import defaultdict
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_engine(db_url):
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)


def create_aliases_table(engine):
    """Create player_aliases table if not exists."""
    sql = """
    CREATE TABLE IF NOT EXISTS player_aliases (
        id SERIAL PRIMARY KEY,
        player_name VARCHAR NOT NULL,
        alias_name VARCHAR NOT NULL,
        source VARCHAR DEFAULT 'bbb_dataset',
        UNIQUE(player_name, alias_name)
    );
    """
    with engine.begin() as conn:
        conn.execute(text(sql))
    print("✓ player_aliases table ready")


def get_last_name(full_name):
    """Extract last name from a player name."""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    return parts[-1] if parts else ""


def is_valid_alias(existing_name, new_name):
    """
    Check if new_name is a valid alias for existing_name.

    Returns True only if last names match.
    This prevents cross-linking completely different players due to
    data mismatches between deliveries and delivery_details tables.
    """
    existing_last = get_last_name(existing_name)
    new_last = get_last_name(new_name)

    # Both must have a last name
    if not existing_last or not new_last:
        return False

    # Last names must match
    return existing_last == new_last


def build_player_mapping(engine):
    """
    Join deliveries with delivery_details to map player names and get bat_hand/bowl_style.

    FIXED: Adds last name validation to prevent incorrect aliases from data mismatches.
    """
    print("\nBuilding player mapping from DB...")

    batter_query = """
    SELECT
        d.batter as existing_name,
        dd.bat as new_name,
        dd.bat_hand
    FROM deliveries d
    JOIN delivery_details dd ON
        d.match_id = dd.p_match
        AND d.innings = dd.inns
        AND d.over = dd.over
        AND d.ball = dd.ball
    WHERE d.batter IS NOT NULL
        AND dd.bat IS NOT NULL
        AND dd.bat_hand IS NOT NULL
    GROUP BY d.batter, dd.bat, dd.bat_hand
    """

    bowler_query = """
    SELECT
        d.bowler as existing_name,
        dd.bowl as new_name,
        dd.bowl_style
    FROM deliveries d
    JOIN delivery_details dd ON
        d.match_id = dd.p_match
        AND d.innings = dd.inns
        AND d.over = dd.over
        AND d.ball = dd.ball
    WHERE d.bowler IS NOT NULL
        AND dd.bowl IS NOT NULL
        AND dd.bowl_style IS NOT NULL
    GROUP BY d.bowler, dd.bowl, dd.bowl_style
    """

    batters = defaultdict(lambda: {'aliases': set(), 'bat_hands': set()})
    bowlers = defaultdict(lambda: {'aliases': set(), 'bowl_styles': set()})

    invalid_batter_aliases = 0
    invalid_bowler_aliases = 0

    with engine.connect() as conn:
        print("  Fetching batter mappings...")
        result = conn.execute(text(batter_query))
        for row in result:
            existing_name, new_name, bat_hand = row[0], row[1], row[2]

            # FIXED: Only add alias if last names match
            if is_valid_alias(existing_name, new_name):
                batters[existing_name]['aliases'].add(new_name)
                batters[existing_name]['bat_hands'].add(bat_hand)
            else:
                invalid_batter_aliases += 1

        print("  Fetching bowler mappings...")
        result = conn.execute(text(bowler_query))
        for row in result:
            existing_name, new_name, bowl_style = row[0], row[1], row[2]

            # FIXED: Only add alias if last names match
            if is_valid_alias(existing_name, new_name):
                bowlers[existing_name]['aliases'].add(new_name)
                bowlers[existing_name]['bowl_styles'].add(bowl_style)
            else:
                invalid_bowler_aliases += 1

    print(f"  Found {len(batters):,} batters, {len(bowlers):,} bowlers")
    print(f"  Rejected {invalid_batter_aliases} invalid batter aliases (last name mismatch)")
    print(f"  Rejected {invalid_bowler_aliases} invalid bowler aliases (last name mismatch)")

    return batters, bowlers


def update_players(engine, batters, bowlers, dry_run=False):
    """Update players table using batch operations for speed."""

    print("\n" + "="*60)
    print("UPDATING PLAYERS TABLE")
    print("="*60)

    # Build update data
    batter_updates = []  # [(name, batter_type), ...]
    bowler_updates = []  # [(name, bowler_type), ...]
    alias_inserts = []   # [(player_name, alias_name), ...]

    all_players = set(batters.keys()) | set(bowlers.keys())

    for name in all_players:
        if name in batters:
            hands = batters[name]['bat_hands']
            if hands:
                batter_updates.append({'name': name, 'batter_type': list(hands)[0]})
            for alias in batters[name]['aliases']:
                if alias != name:
                    alias_inserts.append({'player_name': name, 'alias_name': alias})

        if name in bowlers:
            styles = bowlers[name]['bowl_styles']
            if styles:
                bowler_updates.append({'name': name, 'bowler_type': list(styles)[0]})
            for alias in bowlers[name]['aliases']:
                if alias != name:
                    alias_inserts.append({'player_name': name, 'alias_name': alias})

    # Dedupe aliases
    seen_aliases = set()
    unique_aliases = []
    for a in alias_inserts:
        key = (a['player_name'], a['alias_name'])
        if key not in seen_aliases:
            seen_aliases.add(key)
            unique_aliases.append(a)
    alias_inserts = unique_aliases

    print(f"Prepared {len(batter_updates):,} batter updates, {len(bowler_updates):,} bowler updates, {len(alias_inserts):,} aliases")

    if dry_run:
        print("\n[DRY RUN] Sample batter updates:")
        for u in batter_updates[:5]:
            print(f"  {u['name']}: {u['batter_type']}")
        print("\n[DRY RUN] Sample bowler updates:")
        for u in bowler_updates[:5]:
            print(f"  {u['name']}: {u['bowler_type']}")
        print("\n[DRY RUN] Sample aliases:")
        for a in alias_inserts[:5]:
            print(f"  {a['player_name']} → {a['alias_name']}")
        return

    with engine.begin() as conn:
        # Batch update batter_type using temp table
        if batter_updates:
            print(f"  Updating {len(batter_updates):,} batter types...")
            conn.execute(text("CREATE TEMP TABLE tmp_batter_updates (name VARCHAR, batter_type VARCHAR)"))

            # Insert in batches of 1000
            batch_size = 1000
            for i in range(0, len(batter_updates), batch_size):
                batch = batter_updates[i:i+batch_size]
                values = ", ".join([f"(:n{j}, :bt{j})" for j in range(len(batch))])
                params = {}
                for j, u in enumerate(batch):
                    params[f'n{j}'] = u['name']
                    params[f'bt{j}'] = u['batter_type']
                conn.execute(text(f"INSERT INTO tmp_batter_updates VALUES {values}"), params)

            result = conn.execute(text("""
                UPDATE players p
                SET batter_type = t.batter_type
                FROM tmp_batter_updates t
                WHERE p.name = t.name
            """))
            print(f"    ✓ Updated {result.rowcount:,} batter types")
            conn.execute(text("DROP TABLE tmp_batter_updates"))

        # Batch update bowler_type using temp table
        if bowler_updates:
            print(f"  Updating {len(bowler_updates):,} bowler types...")
            conn.execute(text("CREATE TEMP TABLE tmp_bowler_updates (name VARCHAR, bowler_type VARCHAR)"))

            for i in range(0, len(bowler_updates), batch_size):
                batch = bowler_updates[i:i+batch_size]
                values = ", ".join([f"(:n{j}, :bs{j})" for j in range(len(batch))])
                params = {}
                for j, u in enumerate(batch):
                    params[f'n{j}'] = u['name']
                    params[f'bs{j}'] = u['bowler_type']
                conn.execute(text(f"INSERT INTO tmp_bowler_updates VALUES {values}"), params)

            result = conn.execute(text("""
                UPDATE players p
                SET bowler_type = t.bowler_type
                FROM tmp_bowler_updates t
                WHERE p.name = t.name
            """))
            print(f"    ✓ Updated {result.rowcount:,} bowler types")
            conn.execute(text("DROP TABLE tmp_bowler_updates"))

        # Batch insert aliases
        if alias_inserts:
            print(f"  Inserting {len(alias_inserts):,} aliases...")
            inserted = 0
            for i in range(0, len(alias_inserts), batch_size):
                batch = alias_inserts[i:i+batch_size]
                values = ", ".join([f"(:pn{j}, :an{j})" for j in range(len(batch))])
                params = {}
                for j, a in enumerate(batch):
                    params[f'pn{j}'] = a['player_name']
                    params[f'an{j}'] = a['alias_name']
                conn.execute(text(f"""
                    INSERT INTO player_aliases (player_name, alias_name)
                    VALUES {values}
                    ON CONFLICT (player_name, alias_name) DO NOTHING
                """), params)
                inserted += len(batch)
                print(f"    Inserted {inserted:,}/{len(alias_inserts):,}...", end='\r')
            print(f"\n    ✓ Inserted aliases")

    print(f"\n✓ Batch updates complete")


def print_summary(engine):
    """Print summary."""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    with engine.connect() as conn:
        r = conn.execute(text("SELECT COUNT(*) FROM players WHERE batter_type IS NOT NULL"))
        print(f"Players with batter_type: {r.scalar():,}")
        
        r = conn.execute(text("SELECT COUNT(*) FROM players WHERE bowler_type IS NOT NULL"))
        print(f"Players with bowler_type: {r.scalar():,}")
        
        r = conn.execute(text("SELECT COUNT(*) FROM player_aliases"))
        print(f"Total aliases: {r.scalar():,}")
        
        r = conn.execute(text("""
            SELECT batter_type, COUNT(*) FROM players 
            WHERE batter_type IS NOT NULL GROUP BY batter_type
        """))
        print("\nBatter types:")
        for row in r:
            print(f"  {row[0]}: {row[1]:,}")
        
        r = conn.execute(text("""
            SELECT bowler_type, COUNT(*) FROM players 
            WHERE bowler_type IS NOT NULL GROUP BY bowler_type ORDER BY COUNT(*) DESC LIMIT 10
        """))
        print("\nBowler types (top 10):")
        for row in r:
            print(f"  {row[0]}: {row[1]:,}")


def main():
    parser = argparse.ArgumentParser(description='Update players with bat_hand/bowl_style from delivery_details')
    parser.add_argument('--db-url', help='Database URL (or set DATABASE_URL env var)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: Database URL required. Use --db-url or set DATABASE_URL environment variable.")
        sys.exit(1)
    
    engine = get_engine(db_url)
    db_display = db_url.split('@')[1] if '@' in db_url else 'localhost'
    print(f"Connecting to: {db_display}")
    
    if args.dry_run:
        print("\n*** DRY RUN MODE ***")
    
    create_aliases_table(engine)
    batters, bowlers = build_player_mapping(engine)
    update_players(engine, batters, bowlers, dry_run=args.dry_run)
    
    if not args.dry_run:
        print_summary(engine)


if __name__ == "__main__":
    main()
