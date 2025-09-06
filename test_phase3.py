#!/usr/bin/env python3
"""
Test script for Phase 3: Player Data Update

This script can be run to test the player data update functionality.
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from player_data_updater import PlayerDataUpdater


def test_excel_inspection():
    """Test Excel file inspection without database updates."""
    print("=== Testing Excel File Inspection ===")
    
    excel_path = "/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx"
    
    # Create a dummy database URL for testing (won't be used for inspection)
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    
    try:
        updater = PlayerDataUpdater(db_url, excel_path)
        
        # Test Excel loading and validation
        df = updater.load_excel_data()
        is_valid = updater.validate_excel_data(df)
        
        if is_valid:
            print("✅ Excel file loaded and validated successfully")
            print(f"Total rows in Excel: {len(df)}")
            print(f"Columns found: {list(df.columns)}")
            
            # Show sample data for verification
            print("\n=== Sample Data Preview ===")
            required_cols = ['Player', 'batterType', 'bowlHand', 'bowlType', 'bowlerType']
            for col in required_cols:
                if col in df.columns:
                    sample_values = df[col].head(3).tolist()
                    unique_count = df[col].nunique()
                    null_count = df[col].isnull().sum()
                    print(f"{col}: {sample_values} (unique: {unique_count}, nulls: {null_count})")
            
            return True
        else:
            print("❌ Excel file validation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during Excel inspection: {e}")
        return False


def test_database_connection():
    """Test database connection without making changes."""
    print("\n=== Testing Database Connection ===")
    
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    excel_path = "/Users/adityabalaji/cdt/cricket-data-thing/T20_masterPlayers.xlsx"
    
    try:
        updater = PlayerDataUpdater(db_url, excel_path)
        
        # Test getting current players
        current_players = updater.get_current_players()
        print(f"✅ Database connection successful")
        print(f"Current players in database: {len(current_players)}")
        
        # Show a few sample player names
        sample_names = list(current_players.keys())[:5]
        print(f"Sample player names: {sample_names}")
        
        updater.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    print("Phase 3 Player Data Update - Test Script")
    print("=" * 50)
    
    # Test Excel inspection
    excel_ok = test_excel_inspection()
    
    # Test database connection
    db_ok = test_database_connection()
    
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print(f"Excel file: {'✅ OK' if excel_ok else '❌ Failed'}")
    print(f"Database: {'✅ OK' if db_ok else '❌ Failed'}")
    
    if excel_ok and db_ok:
        print("\n🎉 All tests passed! Ready to run player data update.")
        print("To run the actual update, use:")
        print("python player_data_updater.py")
    else:
        print("\n⚠️  Some tests failed. Please fix issues before proceeding.")
        sys.exit(1)
