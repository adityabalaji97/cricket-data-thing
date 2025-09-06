#!/usr/bin/env python3
"""
Master Execution Script for Left-Right Analysis Implementation

This script orchestrates the complete implementation of left-right analysis
across all three phases as specified in your requirements:

Phase 3: Update player data from Excel
Phase 1: Add base columns to deliveries table
Phase 2: Add derived columns to deliveries table

Usage:
    python run_all_phases.py --phase=all
    python run_all_phases.py --phase=3
    python run_all_phases.py --phase=1
    python run_all_phases.py --phase=2
"""

import sys
import os
import argparse
import time
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from player_data_updater import PlayerDataUpdater
from delivery_updater import DeliveryUpdater
from derived_columns_updater import DerivedColumnsUpdater


def run_phase_3():
    """Run Phase 3: Update player data from Excel."""
    print("\n" + "="*60)
    print("PHASE 3: Update Player Data from Excel")
    print("="*60)
    
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    excel_path = "/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx"
    
    try:
        updater = PlayerDataUpdater(db_url, excel_path)
        results = updater.update_players()
        
        print(f"✅ Phase 3 completed successfully!")
        print(f"   Total processed: {results['total_processed']}")
        print(f"   Updated existing: {results['updated']}")
        print(f"   New players added: {results['new']}")
        print(f"   Errors: {results['errors']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 3 failed: {e}")
        return False


def run_phase_1():
    """Run Phase 1: Add base columns to deliveries table."""
    print("\n" + "="*60)
    print("PHASE 1: Add Base Columns to Deliveries Table")
    print("="*60)
    
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    
    try:
        updater = DeliveryUpdater(db_url)
        results = updater.run_update(batch_size=1000)
        
        print(f"✅ Phase 1 completed successfully!")
        print(f"   Total updated: {results['total_updated']}")
        print(f"   Total errors: {results['total_errors']}")
        print(f"   Batches processed: {results['batch_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 1 failed: {e}")
        return False


def run_phase_2():
    """Run Phase 2: Add derived columns to deliveries table."""
    print("\n" + "="*60)
    print("PHASE 2: Add Derived Columns to Deliveries Table")
    print("="*60)
    
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    
    try:
        updater = DerivedColumnsUpdater(db_url)
        results = updater.run_update(batch_size=1000)
        
        print(f"✅ Phase 2 completed successfully!")
        print(f"   Total updated: {results['total_updated']}")
        print(f"   Total errors: {results['total_errors']}")
        print(f"   Batches processed: {results['batch_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 2 failed: {e}")
        return False


def check_database_schema():
    """Check if the required columns exist in the database."""
    print("Checking database schema...")
    
    try:
        from sqlalchemy import create_engine, inspect
        db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        # Get columns for deliveries table
        columns = inspector.get_columns('deliveries')
        column_names = [col['name'] for col in columns]
        
        # Check for required columns
        required_columns = [
            'striker_batter_type', 'non_striker_batter_type', 'bowler_type',
            'crease_combo', 'ball_direction'
        ]
        
        missing_columns = [col for col in required_columns if col not in column_names]
        
        if missing_columns:
            print(f"❌ Missing database columns: {missing_columns}")
            print("\n🔧 Please run database migrations first:")
            print("   python run_migrations.py")
            print("   OR")
            print("   psql -d cricket_db -f phase1_add_columns.sql")
            print("   psql -d cricket_db -f phase2_add_derived_columns.sql")
            return False
        else:
            print("✅ All required database columns exist")
            return True
            
    except Exception as e:
        print(f"❌ Error checking database schema: {e}")
        return False


def check_prerequisites():
    """Check that database and Excel file exist."""
    print("Checking prerequisites...")
    
    # Check Excel file
    excel_path = "/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx"
    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        return False
    
    # Test database connection
    try:
        from sqlalchemy import create_engine
        db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
        engine = create_engine(db_url)
        connection = engine.connect()
        connection.close()
        print("✅ Database connection OK")
        print("✅ Excel file found")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Run left-right analysis implementation phases')
    parser.add_argument('--phase', choices=['all', '3', '1', '2'], default='all',
                       help='Which phase to run (default: all)')
    
    args = parser.parse_args()
    
    print("LEFT-RIGHT ANALYSIS IMPLEMENTATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Running phase(s): {args.phase}")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites check failed. Please fix issues before proceeding.")
        return 1
    
    # Check database schema
    if not check_database_schema():
        print("\n❌ Database schema check failed. Please run migrations first.")
        return 1
    
    start_time = time.time()
    success = True
    
    # Run phases based on argument
    if args.phase == 'all':
        # Run all phases in sequence
        phases = [
            ("Phase 3", run_phase_3),
            ("Phase 1", run_phase_1), 
            ("Phase 2", run_phase_2)
        ]
        
        for phase_name, phase_func in phases:
            if not phase_func():
                print(f"\n💥 {phase_name} failed. Stopping execution.")
                success = False
                break
                
    elif args.phase == '3':
        success = run_phase_3()
    elif args.phase == '1':
        success = run_phase_1()
    elif args.phase == '2':
        success = run_phase_2()
    
    # Summary
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80)
    print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Completed at: {datetime.now().isoformat()}")
    
    if success:
        print("\n🎉 All phases completed successfully!")
        print("\nYour deliveries table now includes:")
        print("  • striker_batter_type (LHB/RHB)")
        print("  • non_striker_batter_type (LHB/RHB)")
        print("  • bowler_type (LO/LM/RL/RM/RO/etc)")
        print("  • crease_combo (same/left_right/unknown)")
        print("  • ball_direction (intoBatter/awayFromBatter/unknown)")
        print("\nReady for left-right analysis aggregations!")
    else:
        print("\n💥 Execution failed. Check error messages above.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
