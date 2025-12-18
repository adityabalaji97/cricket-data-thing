"""
Update players table with bat_hand/bowl_style from delivery_details.

Usage:
    python scripts/update_players_from_new_data.py --db-url "postgres://..." --dry-run
    python scripts/update_players_from_new_data.py --db-url "postgres://..."
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


def build_player_mapping(engine):
    """
    Join deliveries with delivery_details to map player names and get bat_hand/bowl_style.
    """
    print("\nBuilding player mapping from DB...")
    
    # Batter mapping: join on match/innings/over/ball, get existing name + new name + bat_hand
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
    
    with engine.connect() as conn:
        print("  Fetching batter mappings...")
        result = conn.execute(text(batter_query))
        for row in result:
            batters[row[0]]['aliases'].add(row[1])
            batters[row[0]]['bat_hands'].add(row[2])
        
        print("  Fetching bowler mappings...")
        result = conn.execute(text(bowler_query))
        for row in result:
            bowlers[row[0]]['aliases'].add(row[1])
            bowlers[row[0]]['bowl_styles'].add(row[2])
    
    print(f"  Found {len(batters):,} batters, {len(bowlers):,} bowlers")
    return batters, bowlers


def update_players(engine, batters, bowlers, dry_run=False):
    """Update players table."""
    
    print("\n" + "="*60)
    print("UPDATING PLAYERS TABLE")
    print("="*60)
    
    updates = []
    
    # Combine batter and bowler info
    all_players = set(batters.keys()) | set(bowlers.keys())
    
    for name in all_players:
        update = {'name': name, 'aliases': set()}
        
        if name in batters:
            update['aliases'] |= batters[name]['aliases']
            hands = batters[name]['bat_hands']
            if hands:
                update['batter_type'] = list(hands)[0]  # Take first
        
        if name in bowlers:
            update['aliases'] |= bowlers[name]['aliases']
            styles = bowlers[name]['bowl_styles']
            if styles:
                update['bowler_type'] = list(styles)[0]
        
        updates.append(update)
    
    print(f"Prepared {len(updates):,} player updates")
    
    if dry_run:
        print("\n[DRY RUN] Sample updates:")
        for u in updates[:15]:
            print(f"  {u['name']}: bat={u.get('batter_type')}, bowl={u.get('bowler_type')}, aliases={list(u['aliases'])[:2]}")
        return
    
    # Execute updates
    updated = 0
    aliases_added = 0
    
    with engine.begin() as conn:
        for u in updates:
            # Update batter_type
            if u.get('batter_type'):
                conn.execute(text(
                    "UPDATE players SET batter_type = :bt WHERE name = :name"
                ), {'bt': u['batter_type'], 'name': u['name']})
            
            # Update bowler_type
            if u.get('bowler_type'):
                conn.execute(text(
                    "UPDATE players SET bowler_type = :bs WHERE name = :name"
                ), {'bs': u['bowler_type'], 'name': u['name']})
            
            updated += 1
            
            # Add aliases
            for alias in u['aliases']:
                if alias != u['name']:
                    conn.execute(text("""
                        INSERT INTO player_aliases (player_name, alias_name)
                        VALUES (:pn, :an)
                        ON CONFLICT (player_name, alias_name) DO NOTHING
                    """), {'pn': u['name'], 'an': alias})
                    aliases_added += 1
            
            if updated % 500 == 0:
                print(f"  Updated {updated:,}...", end='\r')
    
    print(f"\n✓ Updated {updated:,} players, added {aliases_added:,} aliases")


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
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-url', required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    engine = get_engine(args.db_url)
    print(f"Connecting to: {args.db_url.split('@')[1]}")
    
    create_aliases_table(engine)
    batters, bowlers = build_player_mapping(engine)
    update_players(engine, batters, bowlers, dry_run=args.dry_run)
    
    if not args.dry_run:
        print_summary(engine)


if __name__ == "__main__":
    main()
