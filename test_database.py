#!/usr/bin/env python3
"""
Simple test to check database connection and current players table structure
"""

from sqlalchemy.orm import sessionmaker
from database import get_database_connection
from models import Player

def test_database_connection():
    """Test database connection and examine players table"""
    try:
        # Get database connection
        engine, SessionLocal = get_database_connection()
        session = SessionLocal()
        
        print("✓ Database connection successful")
        
        # Count total players
        total_players = session.query(Player).count()
        print(f"✓ Total players in database: {total_players}")
        
        # Get sample players to see current structure
        sample_players = session.query(Player).limit(5).all()
        
        print("\nSample players (first 5):")
        for player in sample_players:
            print(f"  Name: {player.name}")
            print(f"  Current batter_type: {player.batter_type}")
            print(f"  Current bowler_type: {player.bowler_type}")
            print(f"  Current bowl_hand: {player.bowl_hand}")
            print(f"  Current bowl_type: {player.bowl_type}")
            print("  ---")
        
        # Check for players with missing data
        missing_batter_type = session.query(Player).filter(Player.batter_type.is_(None)).count()
        missing_bowler_type = session.query(Player).filter(Player.bowler_type.is_(None)).count()
        missing_bowl_hand = session.query(Player).filter(Player.bowl_hand.is_(None)).count()
        missing_bowl_type = session.query(Player).filter(Player.bowl_type.is_(None)).count()
        
        print(f"\nCurrent data completeness:")
        print(f"  Missing batter_type: {missing_batter_type}")
        print(f"  Missing bowler_type: {missing_bowler_type}")
        print(f"  Missing bowl_hand: {missing_bowl_hand}")
        print(f"  Missing bowl_type: {missing_bowl_type}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"✗ Database connection failed: {str(e)}")
        return False

def main():
    """Main function"""
    print("Testing database connection...")
    success = test_database_connection()
    
    if success:
        print("\n✓ Database test completed successfully!")
    else:
        print("\n✗ Database test failed!")
    
    return success

if __name__ == "__main__":
    main()
