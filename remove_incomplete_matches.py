#!/usr/bin/env python3
"""
Remove incomplete matches from all tables.
Incomplete = innings 1 doesn't start at over 0

Usage:
    python remove_incomplete_matches.py --check      # Preview what will be deleted
    python remove_incomplete_matches.py --delete     # Actually delete
"""

import argparse
from database import get_database_connection
from sqlalchemy import text

def get_incomplete_match_ids(session):
    """Get match IDs where innings 1 doesn't start at over 0"""
    result = session.execute(text('''
        WITH innings_starts AS (
            SELECT p_match, inns, MIN(over) as first_over
            FROM delivery_details
            WHERE p_match IS NOT NULL AND inns = 1
            GROUP BY p_match, inns
        )
        SELECT p_match
        FROM innings_starts
        WHERE first_over > 0
    ''')).fetchall()
    return [r[0] for r in result]

def check_incomplete(session, match_ids):
    """Show what would be deleted"""
    print(f"\n=== INCOMPLETE MATCHES TO REMOVE: {len(match_ids)} ===\n")
    
    if match_ids:
        details = session.execute(text('''
            SELECT DISTINCT p_match, match_date, competition, ground,
                   MIN(over) as first_over, COUNT(*) as deliveries
            FROM delivery_details
            WHERE p_match = ANY(:ids) AND inns = 1
            GROUP BY p_match, match_date, competition, ground
            ORDER BY match_date DESC
        '''), {'ids': match_ids}).fetchall()
        
        print(f"{'Match ID':<12} | {'Date':<12} | {'Competition':<25} | First Over | Dels")
        print("-" * 80)
        for d in details:
            print(f"{d[0]:<12} | {d[1]} | {(d[2] or '')[:25]:<25} | {d[4]:>10} | {d[5]}")
    
    print("\n--- Rows to delete per table ---")
    
    # All tables that reference matches - in correct deletion order
    tables = [
        ('batting_stats', 'match_id'),
        ('bowling_stats', 'match_id'),
        ('deliveries', 'match_id'),        # Legacy deliveries table
        ('delivery_details', 'p_match'),   # New delivery_details table
        ('matches', 'id'),
    ]
    
    total = 0
    for table, col in tables:
        try:
            count = session.execute(text(f'''
                SELECT COUNT(*) FROM {table} WHERE {col} = ANY(:ids)
            '''), {'ids': match_ids}).scalar()
            print(f"  {table}: {count:,} rows")
            total += count
        except Exception as e:
            print(f"  {table}: Error - {e}")
    
    print(f"\n  TOTAL: {total:,} rows to delete")
    return match_ids

def delete_incomplete(session, match_ids):
    """Delete incomplete matches from all tables"""
    if not match_ids:
        print("No incomplete matches to delete.")
        return
    
    print(f"\n=== DELETING {len(match_ids)} INCOMPLETE MATCHES ===\n")
    
    # Delete in correct order (foreign key dependencies)
    tables = [
        ('batting_stats', 'match_id'),
        ('bowling_stats', 'match_id'),
        ('deliveries', 'match_id'),        # Legacy deliveries table
        ('delivery_details', 'p_match'),   # New delivery_details table  
        ('matches', 'id'),
    ]
    
    for table, col in tables:
        try:
            result = session.execute(text(f'''
                DELETE FROM {table} WHERE {col} = ANY(:ids)
            '''), {'ids': match_ids})
            print(f"  ✅ {table}: deleted {result.rowcount:,} rows")
        except Exception as e:
            print(f"  ❌ {table}: Error - {e}")
    
    session.commit()
    print("\n✅ Cleanup complete!")

def main():
    parser = argparse.ArgumentParser(description='Remove incomplete matches')
    parser.add_argument('--check', action='store_true', help='Preview only')
    parser.add_argument('--delete', action='store_true', help='Actually delete')
    args = parser.parse_args()
    
    if not args.check and not args.delete:
        print("Use --check to preview or --delete to remove")
        return
    
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        match_ids = get_incomplete_match_ids(session)
        
        if args.check:
            check_incomplete(session, match_ids)
            print("\nRun with --delete to remove these matches.")
        
        elif args.delete:
            check_incomplete(session, match_ids)
            confirm = input("\n⚠️  Proceed with deletion? (yes/N): ").strip().lower()
            if confirm == 'yes':
                delete_incomplete(session, match_ids)
            else:
                print("Cancelled.")
                session.rollback()
    
    finally:
        session.close()

if __name__ == "__main__":
    main()
