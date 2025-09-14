#!/usr/bin/env python3
"""
Test the fixed Delhi team variations function
"""

import sys
import os
sys.path.append('/Users/adityabalaji/cdt/cricket-data-thing')

from services.elo import get_all_team_name_variations, get_delhi_team_name_variations

def test_fixed_variations():
    print("=== Testing Fixed Delhi Team Variations ===\n")
    
    print("1. Testing get_delhi_team_name_variations:")
    test_cases = ['Delhi Capitals', 'Delhi Daredevils', 'DC']
    for name in test_cases:
        result = get_delhi_team_name_variations(name)
        print(f"  '{name}' -> {result}")
    
    print("\n2. Testing get_all_team_name_variations (should use Delhi handler):")
    test_cases = ['Delhi Capitals', 'Delhi Daredevils', 'DC', 'Chennai Super Kings', 'CSK']
    for name in test_cases:
        result = get_all_team_name_variations(name)
        print(f"  '{name}' -> {result}")
    
    print("\n3. Expected behavior:")
    print("  - 'Delhi Capitals' should return ['Delhi Capitals', 'Delhi Daredevils']")
    print("  - This will fetch ALL Delhi matches from both team periods")
    print("  - The ELO racer chart should show complete Delhi history")

if __name__ == "__main__":
    test_fixed_variations()
