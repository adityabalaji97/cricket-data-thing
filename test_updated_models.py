#!/usr/bin/env python3
"""
Test the updated models to ensure they work correctly
"""

try:
    from models import Match, Delivery, Player, Base
    from database import get_database_connection
    print("✅ Successfully imported models")
    
    # Test creating a Delivery object with enhancement columns
    delivery = Delivery(
        match_id="test_match",
        innings=1,
        over=1,
        ball=1,
        batter="Test Batter",
        non_striker="Test Non-Striker",
        bowler="Test Bowler",
        runs_off_bat=4,
        extras=0,
        batting_team="Team A",
        bowling_team="Team B",
        # Test the new enhancement columns
        striker_batter_type="RHB",
        non_striker_batter_type="LHB", 
        bowler_type="RM",
        crease_combo="lhb_rhb",
        ball_direction="intoBatter"
    )
    
    print("✅ Successfully created Delivery object with enhancement columns")
    print(f"   striker_batter_type: {delivery.striker_batter_type}")
    print(f"   non_striker_batter_type: {delivery.non_striker_batter_type}")
    print(f"   bowler_type: {delivery.bowler_type}")
    print(f"   crease_combo: {delivery.crease_combo}")
    print(f"   ball_direction: {delivery.ball_direction}")
    
    print("\n🎉 Models updated successfully!")
    print("You can now run your enhanced loader without the 'invalid keyword argument' error.")
    
except Exception as e:
    print(f"❌ Error testing models: {e}")
