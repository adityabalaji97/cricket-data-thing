"""
Simple test to verify the enhanced league matching logic works locally
"""

# Simulate the enhanced functions
def test_league_expansion():
    
    leagues_mapping = {
        "Indian Premier League": "IPL",
        "Big Bash League": "BBL", 
        "Pakistan Super League": "PSL",
        "Caribbean Premier League": "CPL",
        "SA20": "SA20",
        "International League T20": "ILT20",
        "Bangladesh Premier League": "BPL",
        "Lanka Premier League": "LPL",
        "Major League Cricket": "MLC",
        "Vitality Blast": "VB"
    }

    league_aliases = {
        "HRV Cup": "Super Smash",
        "HRV Twenty20": "Super Smash",
        "NatWest T20 Blast": "Vitality Blast",
        "Vitality Blast Men": "Vitality Blast"
    }

    def get_league_variations(league_name: str):
        """Get common variations for specific league names"""
        variations = []
        league_lower = league_name.lower()
        
        # Major League Cricket variations
        if 'major league cricket' in league_lower or league_name == 'MLC':
            variations.extend([
                'Major League Cricket',
                'MLC',
                'Major League Cricket USA',
                'MLC USA'
            ])
        
        # Vitality Blast variations  
        elif 'vitality blast' in league_lower or 'blast' in league_lower:
            variations.extend([
                'Vitality Blast',
                'Vitality Blast Men',
                'T20 Blast',
                'NatWest T20 Blast',
                'Vitality T20 Blast'
            ])
        
        return variations

    def expand_league_abbreviations(abbrevs):
        """Enhanced version that handles partial matches and common variations"""
        expanded = []
        
        for abbrev in abbrevs:
            # Add the original term
            expanded.append(abbrev)
            
            # Check exact matches in leagues_mapping
            if abbrev in leagues_mapping:
                expanded.append(leagues_mapping[abbrev])
            
            # Check reverse mapping (abbrev -> full name)
            reverse_mapping = {v: k for k, v in leagues_mapping.items()}
            if abbrev in reverse_mapping:
                expanded.append(reverse_mapping[abbrev])
            
            # Check aliases
            if abbrev in league_aliases:
                expanded.append(league_aliases[abbrev])
            
            # Check reverse aliases
            reverse_aliases = {v: k for k, v in league_aliases.items()}
            if abbrev in reverse_aliases:
                expanded.append(reverse_aliases[abbrev])
            
            # Handle common variations for specific leagues
            variations = get_league_variations(abbrev)
            expanded.extend(variations)
        
        # Remove duplicates while preserving order
        result = []
        for item in expanded:
            if item not in result:
                result.append(item)
        
        return result

    # Test cases
    test_cases = [
        "Major League Cricket",
        "MLC",
        "Vitality Blast",
        "Vitality Blast Men",
        "IPL"
    ]
    
    print("=== Testing Enhanced League Expansion ===")
    for test in test_cases:
        result = expand_league_abbreviations([test])
        print(f"'{test}' -> {result}")
    
    print("\n=== Testing SQL Parameter Generation ===")
    
    # Test how this would work in the SQL query
    leagues = ["Major League Cricket"]
    expanded_leagues = expand_league_abbreviations(leagues)
    
    print(f"Original: {leagues}")
    print(f"Expanded: {expanded_leagues}")
    
    # Simulate the ILIKE conditions
    print(f"\nSQL ILIKE conditions would be:")
    for i, league in enumerate(expanded_leagues):
        print(f"  m.competition ILIKE '%{league}%'")
    
    print(f"\nExact match condition:")
    print(f"  m.competition = ANY({expanded_leagues})")

if __name__ == "__main__":
    test_league_expansion()
