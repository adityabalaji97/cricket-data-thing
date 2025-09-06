#!/usr/bin/env python3
"""
Script to populate new delivery columns for left-right analysis

This script:
1. Adds new columns to deliveries table (if not already added)
2. Populates striker_batterType, non_striker_batterType, bowler_type from players table
3. Calculates derived fields: creaseCombo and ballDirection
4. Processes data in batches for efficiency

New columns:
- striker_batterType: LHB/RHB from players.batter_type
- non_striker_batterType: LHB/RHB from players.batter_type  
- bowler_type: bowling type from players.bowler_type
- creaseCombo: same/unknown/left_right based on both batters' types
- ballDirection: intoBatter/awayFromBatter/unknown based on batter type + bowling type
"""

import os
import sys
from sqlalchemy import create_engine, text
from database import get_database_url
from datetime import datetime

def check_and_add_columns(engine):
    """Check if new columns exist, add them if they don't"""
    print("Checking delivery table schema...")
    
    with engine.begin() as conn:
        # Check which columns already exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'deliveries' 
            AND column_name IN ('striker_battertype', 'non_striker_battertype', 'bowler_type', 'creasecombo', 'balldirection')
        """))
        
        existing_columns = [row[0] for row in result.fetchall()]
        print(f"Existing new columns: {existing_columns}")
        
        # Add missing columns
        new_columns = [
            ('striker_batterType', 'VARCHAR(10)'),
            ('non_striker_batterType', 'VARCHAR(10)'), 
            ('bowler_type', 'VARCHAR(10)'),
            ('creaseCombo', 'VARCHAR(20)'),
            ('ballDirection', 'VARCHAR(20)')
        ]
        
        for col_name, col_type in new_columns:
            if col_name.lower() not in existing_columns:
                print(f"Adding column: {col_name}")
                conn.execute(text(f"ALTER TABLE deliveries ADD COLUMN {col_name} {col_type}"))
            else:
                print(f"Column {col_name} already exists")

def get_delivery_count(engine):
    """Get total count of deliveries for progress tracking"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM deliveries"))
        return result.fetchone()[0]

def update_deliveries_batch(engine, offset, batch_size):
    """Update a batch of deliveries with new column data"""
    
    update_query = text("""
        UPDATE deliveries 
        SET 
            striker_batterType = COALESCE(p1.batter_type, 'unknown'),
            non_striker_batterType = COALESCE(p2.batter_type, 'unknown'),
            bowler_type = COALESCE(p3.bowler_type, 'unknown')
        FROM 
            (SELECT id, batter, non_striker, bowler 
             FROM deliveries 
             ORDER BY id 
             LIMIT :batch_size OFFSET :offset) AS d
        LEFT JOIN players p1 ON d.batter = p1.name
        LEFT JOIN players p2 ON d.non_striker = p2.name  
        LEFT JOIN players p3 ON d.bowler = p3.name
        WHERE deliveries.id = d.id
    """)
    
    with engine.begin() as conn:
        result = conn.execute(update_query, {"batch_size": batch_size, "offset": offset})
        return result.rowcount

def calculate_derived_fields_batch(engine, offset, batch_size):
    """Calculate creaseCombo and ballDirection for a batch of deliveries"""
    
    # First, update creaseCombo
    crease_combo_query = text("""
        UPDATE deliveries 
        SET creaseCombo = CASE
            WHEN striker_batterType = 'unknown' OR non_striker_batterType = 'unknown' THEN 'unknown'
            WHEN striker_batterType = non_striker_batterType THEN 'same'
            WHEN striker_batterType != non_striker_batterType THEN 'left_right'
            ELSE 'unknown'
        END
        WHERE id IN (
            SELECT id FROM deliveries 
            ORDER BY id 
            LIMIT :batch_size OFFSET :offset
        )
    """)
    
    # Then, update ballDirection
    ball_direction_query = text("""
        UPDATE deliveries 
        SET ballDirection = CASE
            WHEN striker_batterType = 'unknown' OR bowler_type = 'unknown' THEN 'unknown'
            WHEN (striker_batterType = 'RHB' AND bowler_type IN ('RO', 'LC')) 
                 OR (striker_batterType = 'LHB' AND bowler_type IN ('RL', 'LO')) THEN 'intoBatter'
            WHEN (striker_batterType = 'LHB' AND bowler_type IN ('RO', 'LC'))
                 OR (striker_batterType = 'RHB' AND bowler_type IN ('RL', 'LO')) THEN 'awayFromBatter'
            ELSE 'unknown'
        END
        WHERE id IN (
            SELECT id FROM deliveries 
            ORDER BY id 
            LIMIT :batch_size OFFSET :offset
        )
    """)
    
    with engine.begin() as conn:
        # Update creaseCombo
        result1 = conn.execute(crease_combo_query, {"batch_size": batch_size, "offset": offset})
        
        # Update ballDirection  
        result2 = conn.execute(ball_direction_query, {"batch_size": batch_size, "offset": offset})
        
        return result1.rowcount, result2.rowcount

def update_deliveries_data():
    """Main function to update all delivery records"""
    print("Starting deliveries table update...")
    
    # Connect to database
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    try:
        # Add columns if they don't exist
        check_and_add_columns(engine)
        
        # Get total count for progress tracking
        total_deliveries = get_delivery_count(engine)
        print(f"Total deliveries to process: {total_deliveries:,}")
        
        # Process in batches
        batch_size = 10000  # Process 10k records at a time
        processed = 0
        
        print("\nStep 1: Updating player types from players table...")
        
        for offset in range(0, total_deliveries, batch_size):
            current_batch_size = min(batch_size, total_deliveries - offset)
            
            updated = update_deliveries_batch(engine, offset, current_batch_size)
            processed += updated
            
            progress = (processed / total_deliveries) * 100
            print(f"Progress: {processed:,}/{total_deliveries:,} ({progress:.1f}%) - Updated {updated:,} records")
        
        print(f"\nStep 1 completed: Updated {processed:,} delivery records with player types")
        
        # Reset counter for derived fields
        processed = 0
        print("\nStep 2: Calculating derived fields (creaseCombo, ballDirection)...")
        
        for offset in range(0, total_deliveries, batch_size):
            current_batch_size = min(batch_size, total_deliveries - offset)
            
            crease_updated, ball_updated = calculate_derived_fields_batch(engine, offset, current_batch_size)
            processed += crease_updated
            
            progress = (processed / total_deliveries) * 100
            print(f"Progress: {processed:,}/{total_deliveries:,} ({progress:.1f}%) - Updated {crease_updated:,} crease, {ball_updated:,} ball direction")
        
        print(f"\nStep 2 completed: Updated {processed:,} delivery records with derived fields")
        
        # Generate summary statistics
        print("\nGenerating summary statistics...")
        with engine.connect() as conn:
            # Count by striker batter type
            result = conn.execute(text("""
                SELECT striker_batterType, COUNT(*) as count 
                FROM deliveries 
                GROUP BY striker_batterType 
                ORDER BY count DESC
            """))
            print("\nStriker batter type distribution:")
            for row in result:
                print(f"  {row[0]}: {row[1]:,}")
            
            # Count by crease combo
            result = conn.execute(text("""
                SELECT creaseCombo, COUNT(*) as count 
                FROM deliveries 
                GROUP BY creaseCombo 
                ORDER BY count DESC
            """))
            print("\nCrease combination distribution:")
            for row in result:
                print(f"  {row[0]}: {row[1]:,}")
            
            # Count by ball direction
            result = conn.execute(text("""
                SELECT ballDirection, COUNT(*) as count 
                FROM deliveries 
                GROUP BY ballDirection 
                ORDER BY count DESC
            """))
            print("\nBall direction distribution:")
            for row in result:
                print(f"  {row[0]}: {row[1]:,}")
        
        print(f"\nDeliveries table update completed successfully!")
        print(f"Total records processed: {total_deliveries:,}")
        
    except Exception as e:
        print(f"Error updating deliveries: {str(e)}")
        raise
    finally:
        engine.dispose()

def main():
    """Main entry point"""
    try:
        print("=== Deliveries Table Update for Left-Right Analysis ===")
        print(f"Started at: {datetime.now()}")
        
        # Confirm before proceeding
        confirm = input("\nThis will update all delivery records. Proceed? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled")
            return
        
        update_deliveries_data()
        
        print(f"\nCompleted at: {datetime.now()}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
