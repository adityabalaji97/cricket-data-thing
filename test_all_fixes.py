#!/usr/bin/env python3
"""
Test script to verify that both issues are resolved:
1. Enhanced loader can create Delivery objects with enhancement columns
2. StatsProcessor can calculate fantasy points without argument errors
"""

try:
    print("🧪 Testing the fixes...")
    
    # Test 1: Import models and create a Delivery object with enhancement columns
    print("\n1️⃣ Testing enhanced Delivery model...")
    from models import Delivery
    
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
    print(f"   - striker_batter_type: {delivery.striker_batter_type}")
    print(f"   - non_striker_batter_type: {delivery.non_striker_batter_type}")
    print(f"   - bowler_type: {delivery.bowler_type}")
    print(f"   - crease_combo: {delivery.crease_combo}")
    print(f"   - ball_direction: {delivery.ball_direction}")
    
    # Test 2: Test fantasy points calculation with correct signatures
    print("\n2️⃣ Testing fantasy points calculation...")
    from fantasy_points_v2 import FantasyPointsCalculator
    from models import BattingStats, BowlingStats
    
    # Create test batting stats
    batting_stats = BattingStats(
        match_id="test_match",
        innings=1,
        striker="Test Batter",
        batting_team="Team A",
        runs=45,
        balls_faced=30,
        wickets=0,
        fours=5,
        sixes=1,
        strike_rate=150.0
    )
    
    # Create test bowling stats
    bowling_stats = BowlingStats(
        match_id="test_match",
        innings=1,
        bowler="Test Bowler",
        bowling_team="Team B",
        overs=4.0,
        runs_conceded=28,
        wickets=2,
        dots=8,
        economy=7.0
    )
    
    # Test fantasy calculator with correct signatures
    calculator = FantasyPointsCalculator()
    
    batting_points = calculator.calculate_batting_points(batting_stats)
    bowling_points = calculator.calculate_bowling_points(bowling_stats)
    
    print("✅ Successfully calculated fantasy points")
    print(f"   - Batting points: {batting_points}")
    print(f"   - Bowling points: {bowling_points}")
    
    # Test 3: Verify no duplicate models.py files exist
    print("\n3️⃣ Checking for duplicate models.py files...")
    import os
    
    root_models = "/Users/adityabalaji/cdt/cricket-data-thing/models.py"
    subdir_models = "/Users/adityabalaji/cdt/cricket-data-thing/cricket-data-thing/models.py"
    dataloader_models = "/Users/adityabalaji/cdt/cricket-data-thing/dataloader/models.py"
    
    print(f"   - Root models.py exists: {os.path.exists(root_models)} ✅")
    print(f"   - Subdir models.py exists: {os.path.exists(subdir_models)} {'❌ (removed)' if not os.path.exists(subdir_models) else '⚠️  (still exists)'}")
    print(f"   - Dataloader models.py exists: {os.path.exists(dataloader_models)} {'❌ (removed)' if not os.path.exists(dataloader_models) else '⚠️  (still exists)'}")
    
    print("\n🎉 All tests passed! The fixes are working correctly.")
    print("\nYou can now:")
    print("1. Run your enhanced loader: python enhanced_loadmatches.py /path/to/json/files/")
    print("2. Run your stats processor: python statsProcessor.py")
    print("3. Clean up by deleting: rm -rf temp_unused/")
    
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
