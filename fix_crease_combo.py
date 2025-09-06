#!/usr/bin/env python3
"""
Fix Crease Combo Data Script

This script updates the crease_combo column in the deliveries table
by recalculating it from striker_batter_type and non_striker_batter_type.

Usage: python fix_crease_combo.py
"""

import os
from sqlalchemy import create_engine, text
from database import get_session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_current_state(db):
    """Check the current state of crease_combo data"""
    print("🔍 Checking current state of crease_combo data...")
    
    # Overall stats
    query = text("""
        SELECT 
            COUNT(*) as total_deliveries,
            COUNT(CASE WHEN crease_combo != 'unknown' THEN 1 END) as populated_combos,
            COUNT(CASE WHEN striker_batter_type IS NOT NULL AND non_striker_batter_type IS NOT NULL THEN 1 END) as has_both_types,
            ROUND(
                100.0 * COUNT(CASE WHEN crease_combo != 'unknown' THEN 1 END) / COUNT(*), 
                2
            ) as populated_percentage
        FROM deliveries
    """)
    
    result = db.execute(query).fetchone()
    print(f"📊 Total deliveries: {result[0]:,}")
    print(f"📊 Populated combos: {result[1]:,}")
    print(f"📊 Has both batter types: {result[2]:,}")
    print(f"📊 Populated percentage: {result[3]}%")
    
    # Distribution
    dist_query = text("""
        SELECT 
            crease_combo,
            COUNT(*) as count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
        FROM deliveries
        GROUP BY crease_combo
        ORDER BY count DESC
    """)
    
    print("\n📊 Current crease_combo distribution:")
    results = db.execute(dist_query).fetchall()
    for row in results:
        print(f"  {row[0]}: {row[1]:,} ({row[2]}%)")
    
    return result[1]  # Return populated_combos count

def show_sample_data(db, note="Sample data"):
    """Show sample data to verify the logic"""
    print(f"\n🔍 {note}:")
    
    query = text("""
        SELECT 
            batter,
            striker_batter_type,
            non_striker_batter_type,
            crease_combo
        FROM deliveries 
        WHERE striker_batter_type IS NOT NULL 
          AND non_striker_batter_type IS NOT NULL 
        LIMIT 5
    """)
    
    results = db.execute(query).fetchall()
    for row in results:
        print(f"  {row[0]}: {row[1]} + {row[2]} = {row[3]}")

def fix_crease_combo_data(db):
    """Fix the crease_combo data by recalculating it"""
    print("\n🔧 Updating crease_combo data...")
    
    update_query = text("""
        UPDATE deliveries 
        SET crease_combo = CASE 
            WHEN striker_batter_type = 'RHB' AND non_striker_batter_type = 'RHB' THEN 'rhb_rhb'
            WHEN striker_batter_type = 'LHB' AND non_striker_batter_type = 'LHB' THEN 'lhb_lhb'  
            WHEN (striker_batter_type = 'LHB' AND non_striker_batter_type = 'RHB') 
              OR (striker_batter_type = 'RHB' AND non_striker_batter_type = 'LHB') THEN 'lhb_rhb'
            ELSE 'unknown'
        END
        WHERE striker_batter_type IS NOT NULL 
          AND non_striker_batter_type IS NOT NULL
    """)
    
    result = db.execute(update_query)
    db.commit()
    
    print(f"✅ Updated {result.rowcount:,} rows")
    return result.rowcount

def main():
    """Main function to fix crease combo data"""
    print("🏏 Fix Crease Combo Data Script")
    print("=" * 50)
    
    # Get database session
    db = next(get_session())
    
    try:
        # Check current state
        current_populated = check_current_state(db)
        show_sample_data(db, "Current sample data")
        
        # Confirm with user
        print(f"\n⚠️  This will update the crease_combo column for deliveries where both batter types are known.")
        print(f"📊 Currently {current_populated:,} deliveries have populated crease_combo values")
        
        confirm = input("\n🤔 Do you want to proceed with the update? (type 'YES' to confirm): ")
        
        if confirm != 'YES':
            print("❌ Update cancelled by user")
            return
        
        # Perform the update
        updated_rows = fix_crease_combo_data(db)
        
        # Check results
        print("\n🔍 Checking results after update...")
        new_populated = check_current_state(db)
        show_sample_data(db, "Sample data after update")
        
        # Summary
        improvement = new_populated - current_populated
        print(f"\n🎉 SUCCESS!")
        print(f"📈 Improved populated combos from {current_populated:,} to {new_populated:,}")
        print(f"📈 Net improvement: +{improvement:,} populated combinations")
        print(f"🔧 Total rows updated: {updated_rows:,}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
