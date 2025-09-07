#!/usr/bin/env python3
"""
Test script to verify that team name normalization is working correctly
"""

from elo_calculator import normalize_team_name, teams_are_same, ELOCalculator

def test_team_normalization():
    """Test that team name normalization works correctly"""
    print("=== TESTING TEAM NAME NORMALIZATION ===")
    
    # Test cases for RCB
    test_cases = [
        ("Royal Challengers Bangalore", "Royal Challengers Bengaluru", True),
        ("Royal Challengers Bangalore", "Mumbai Indians", False),
        ("Chennai Super Kings", "CSK", True),  # This should actually be False since CSK is the normalized form
        ("Delhi Capitals", "Delhi Daredevils", True),
        ("Kings XI Punjab", "Punjab Kings", True),
    ]
    
    print(f"{'Team 1':<25} {'Team 2':<25} {'Same?':<6} {'Expected':<8}")
    print("-" * 70)
    
    for team1, team2, expected in test_cases:
        result = teams_are_same(team1, team2)
        status = "✓" if result == expected else "✗"
        print(f"{team1:<25} {team2:<25} {result!s:<6} {expected!s:<8} {status}")
    
    print("\n=== TESTING NORMALIZATION MAPPINGS ===")
    test_teams = [
        "Royal Challengers Bangalore",
        "Royal Challengers Bengaluru", 
        "Mumbai Indians",
        "Chennai Super Kings",
        "Delhi Capitals",
        "Delhi Daredevils",
        "Kings XI Punjab",
        "Punjab Kings"
    ]
    
    for team in test_teams:
        normalized = normalize_team_name(team)
        print(f"{team:<30} -> {normalized}")

def test_elo_calculation_with_rcb():
    """Test ELO calculation with RCB team name variations"""
    print("\n=== TESTING ELO CALCULATION WITH RCB VARIATIONS ===")
    
    calculator = ELOCalculator()
    
    # Simulate some matches with different RCB name variations
    matches = [
        ("Mumbai Indians", "Royal Challengers Bangalore", "Royal Challengers Bangalore"),
        ("Royal Challengers Bengaluru", "Delhi Capitals", "Royal Challengers Bengaluru"),
        ("Chennai Super Kings", "Royal Challengers Bangalore", "Chennai Super Kings"),
    ]
    
    print(f"{'Match':<50} {'Winner':<25} {'Status'}")
    print("-" * 85)
    
    for team1, team2, winner in matches:
        try:
            old_1, old_2, new_1, new_2 = calculator.update_ratings(team1, team2, winner)
            print(f"{team1} vs {team2:<25} {winner:<25} Success")
            print(f"  {normalize_team_name(team1)}: {old_1} -> {new_1}")
            print(f"  {normalize_team_name(team2)}: {old_2} -> {new_2}")
        except Exception as e:
            print(f"{team1} vs {team2:<25} {winner:<25} Error: {e}")
    
    print(f"\nFinal ratings:")
    for team, rating in sorted(calculator.team_ratings.items(), key=lambda x: x[1], reverse=True):
        print(f"  {team}: {rating}")

if __name__ == "__main__":
    test_team_normalization()
    test_elo_calculation_with_rcb()
