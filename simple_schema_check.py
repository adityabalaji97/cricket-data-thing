#!/usr/bin/env python3
"""
Simple schema checker for deliveries table
"""

import sys
import os
sys.path.append('/Users/adityabalaji/cdt/cricket-data-thing')

from sqlalchemy import text, inspect
from database import get_database_connection

def main():
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        # Check if table exists and get columns
        inspector = inspect(engine)
        
        if 'deliveries' not in inspector.get_table_names():
            print("ERROR: deliveries table does not exist")
            return
        
        print("=== DELIVERIES TABLE COLUMNS ===")
        columns = inspector.get_columns('deliveries')
        
        column_names = []
        for col in sorted(columns, key=lambda x: x['name']):
            col_name = col['name']
            col_type = str(col['type'])
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"{col_name:<30} {col_type:<20} {nullable}")
            column_names.append(col_name)
        
        print(f"\nTOTAL COLUMNS: {len(columns)}")
        
        # Check for specific enhancement columns
        print(f"\n=== ENHANCEMENT COLUMNS CHECK ===")
        
        enhancement_cols = [
            'striker_batter_type',
            'non_striker_batter_type', 
            'bowler_type',
            'crease_combo',
            'ball_direction',
            'striker_battertype',
            'non_striker_battertype',
            'creasecombo', 
            'balldirection'
        ]
        
        for col in enhancement_cols:
            exists = col in column_names or col.lower() in [c.lower() for c in column_names]
            status = "EXISTS" if exists else "MISSING"
            print(f"{col:<30} {status}")
        
        # Get total count
        result = session.execute(text("SELECT COUNT(*) FROM deliveries"))
        count = result.scalar()
        print(f"\nTOTAL DELIVERIES: {count:,}")
        
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()
