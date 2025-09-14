#!/usr/bin/env python3
"""
Debug the get_all_team_name_variations function specifically for Delhi teams
"""

# Add the path to import from the services
import sys
import os
sys.path.append('/Users/adityabalaji/cdt/cricket-data-thing')

from models import teams_mapping
from services.elo import get_all_team_name_variations

def debug_team_variations():
    print("=== Debugging get_all_team_name_variations for Delhi teams ===\n")
    
    print("Current teams_mapping for Delhi:")
    delhi_entries = {k: v for k, v in teams_mapping.items() if 'Delhi' in k}
    for full_name, abbrev in delhi_entries.items():
        print(f"  '{full_name}' -> '{abbrev}'")
    
    print("\nTesting get_all_team_name_variations:")
    
    test_names = [
        'Delhi Capitals',
        'Delhi Daredevils', 
        'DC',
        'DD'
    ]
    
    for name in test_names:
        variations = get_all_team_name_variations(name)
        print(f"  '{name}' -> {variations}")
    
    print("\nThe problem:")
    print("If both 'Delhi Capitals' and 'Delhi Daredevils' return the same variations,")
    print("then they'll both search for the same database records and return identical data.")
    
    print("\nReverse mapping analysis:")
    # Recreate the reverse mapping logic from the function
    reverse_mapping = {}
    for full_name, abbrev in teams_mapping.items():
        if abbrev not in reverse_mapping:
            reverse_mapping[abbrev] = []
        reverse_mapping[abbrev].append(full_name)
    
    print("Reverse mapping contents:")
    for abbrev, names in reverse_mapping.items():
        if 'Delhi' in str(names):
            print(f"  '{abbrev}' -> {names}")

if __name__ == "__main__":
    debug_team_variations()
