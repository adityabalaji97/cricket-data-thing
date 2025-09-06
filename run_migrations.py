#!/usr/bin/env python3
"""
Database Migration Runner for Left-Right Analysis

This script runs the SQL migrations to add the required columns
to the deliveries table before running the Python updates.
"""

import psycopg2
import sys
import os
from pathlib import Path


def run_sql_file(connection, file_path):
    """
    Execute SQL commands from a file.
    
    Args:
        connection: Database connection
        file_path: Path to SQL file
    """
    try:
        with open(file_path, 'r') as file:
            sql_content = file.read()
        
        cursor = connection.cursor()
        cursor.execute(sql_content)
        connection.commit()
        cursor.close()
        
        print(f"✅ Successfully executed: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error executing {file_path}: {e}")
        connection.rollback()
        return False


def main():
    """Run database migrations."""
    print("Left-Right Analysis - Database Migration Runner")
    print("=" * 60)
    
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'cricket_db',
        'user': 'aditya',
        'password': 'aditya123'
    }
    
    try:
        # Connect to database
        print("Connecting to database...")
        connection = psycopg2.connect(**db_params)
        print("✅ Database connection successful")
        
        # Get current directory
        current_dir = Path(__file__).parent
        
        # Migration files in order
        migrations = [
            current_dir / "phase1_add_columns.sql",
            current_dir / "phase2_add_derived_columns.sql"
        ]
        
        # Run each migration
        all_successful = True
        for migration_file in migrations:
            if migration_file.exists():
                success = run_sql_file(connection, migration_file)
                if not success:
                    all_successful = False
                    break
            else:
                print(f"❌ Migration file not found: {migration_file}")
                all_successful = False
                break
        
        if all_successful:
            print("\n🎉 All migrations completed successfully!")
            print("\nNew columns added to deliveries table:")
            print("  • striker_batter_type")
            print("  • non_striker_batter_type") 
            print("  • bowler_type")
            print("  • crease_combo")
            print("  • ball_direction")
            print("\nYou can now run the Python scripts:")
            print("  python run_all_phases.py --phase=all")
        else:
            print("\n💥 Some migrations failed!")
            return 1
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return 1
    finally:
        if 'connection' in locals():
            connection.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
