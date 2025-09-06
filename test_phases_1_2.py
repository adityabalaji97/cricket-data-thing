#!/usr/bin/env python3
"""
Test script for Phase 1 & 2: Delivery Columns Update

This script tests both Phase 1 (base columns) and Phase 2 (derived columns) functionality.
"""

import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from delivery_updater import DeliveryUpdater
from derived_columns_updater import DerivedColumnsUpdater


def test_derived_logic():
    """Test the derived column calculation logic."""
    print("=== Testing Derived Column Logic ===")
    
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    updater = DerivedColumnsUpdater(db_url)
    
    # Test crease combo logic
    test_cases_crease = [
        ('LHB', 'LHB', 'same'),
        ('RHB', 'RHB', 'same'),
        ('LHB', 'RHB', 'left_right'),
        ('RHB', 'LHB', 'left_right'),
        (None, 'LHB', 'unknown'),
        ('LHB', None, 'unknown'),
        ('unknown', 'RHB', 'unknown'),
        ('LHB', 'unknown', 'unknown')
    ]
    
    print("\nTesting crease_combo logic:")
    for striker, non_striker, expected in test_cases_crease:
        result = updater.calculate_crease_combo(striker, non_striker)
        status = "✅" if result == expected else "❌"
        print(f"{status} {striker} + {non_striker} = {result} (expected: {expected})")
    
    # Test ball direction logic
    test_cases_direction = [
        ('RHB', 'RO', 'intoBatter'),
        ('RHB', 'LC', 'intoBatter'),
        ('LHB', 'RL', 'intoBatter'),
        ('LHB', 'LO', 'intoBatter'),
        ('LHB', 'RO', 'awayFromBatter'),
        ('LHB', 'LC', 'awayFromBatter'),
        ('RHB', 'RL', 'awayFromBatter'),
        ('RHB', 'LO', 'awayFromBatter'),
        ('RHB', 'RM', 'unknown'),
        (None, 'RO', 'unknown'),
        ('RHB', None, 'unknown')
    ]
    
    print("\nTesting ball_direction logic:")
    for striker, bowler, expected in test_cases_direction:
        result = updater.calculate_ball_direction(striker, bowler)
        status = "✅" if result == expected else "❌"
        print(f"{status} {striker} vs {bowler} = {result} (expected: {expected})")
    
    updater.session.close()
    return True


def test_database_schema():
    """Test that the database schema includes all new columns."""
    print("\n=== Testing Database Schema ===")
    
    from sqlalchemy import create_engine, inspect
    
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    engine = create_engine(db_url)
    inspector = inspect(engine)
    
    # Get columns for deliveries table
    columns = inspector.get_columns('deliveries')
    column_names = [col['name'] for col in columns]
    
    # Check for Phase 1 columns
    phase1_columns = ['striker_batter_type', 'non_striker_batter_type', 'bowler_type']
    phase2_columns = ['crease_combo', 'ball_direction']
    
    print("Phase 1 columns:")
    for col in phase1_columns:
        status = "✅" if col in column_names else "❌"
        print(f"{status} {col}")
    
    print("\nPhase 2 columns:")
    for col in phase2_columns:
        status = "✅" if col in column_names else "❌"
        print(f"{status} {col}")
    
    return all(col in column_names for col in phase1_columns + phase2_columns)


def test_sample_data():
    """Test with a small sample of actual data."""
    print("\n=== Testing Sample Data Processing ===")
    
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    from models import Delivery
    
    db_url = "postgresql://aditya:aditya123@localhost:5432/cricket_db"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get a small sample of deliveries
        sample_deliveries = session.query(Delivery).limit(5).all()
        
        if not sample_deliveries:
            print("❌ No deliveries found in database")
            return False
        
        print(f"Sample data from {len(sample_deliveries)} deliveries:")
        for delivery in sample_deliveries:
            print(f"  Delivery {delivery.id}:")
            print(f"    Striker: {delivery.batter} ({delivery.striker_batter_type})")
            print(f"    Non-striker: {delivery.non_striker} ({delivery.non_striker_batter_type})")
            print(f"    Bowler: {delivery.bowler} ({delivery.bowler_type})")
            print(f"    Crease combo: {delivery.crease_combo}")
            print(f"    Ball direction: {delivery.ball_direction}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing sample data: {e}")
        return False
    finally:
        session.close()


if __name__ == "__main__":
    print("Phase 1 & 2 Delivery Columns Update - Test Script")
    print("=" * 60)
    
    # Test derived logic
    logic_ok = test_derived_logic()
    
    # Test database schema
    schema_ok = test_database_schema()
    
    # Test sample data
    sample_ok = test_sample_data()
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print(f"Derived logic: {'✅ OK' if logic_ok else '❌ Failed'}")
    print(f"Database schema: {'✅ OK' if schema_ok else '❌ Failed'}")
    print(f"Sample data: {'✅ OK' if sample_ok else '❌ Failed'}")
    
    if logic_ok and schema_ok:
        print("\n🎉 All tests passed! Ready to run the updates.")
        print("\nTo run the updates:")
        print("1. Phase 1: python delivery_updater.py")
        print("2. Phase 2: python derived_columns_updater.py")
        
        if not schema_ok:
            print("\n⚠️  Database schema missing columns. Run the SQL migrations first:")
            print("1. psql -d cricket_db -f phase1_add_columns.sql")
            print("2. psql -d cricket_db -f phase2_add_derived_columns.sql")
    else:
        print("\n⚠️  Some tests failed. Please fix issues before proceeding.")
        sys.exit(1)
