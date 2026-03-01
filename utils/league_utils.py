from typing import List
from models import leagues_mapping, league_aliases


def get_league_variations(league_name: str) -> List[str]:
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

    # IPL variations
    elif 'ipl' in league_lower or 'indian premier league' in league_lower:
        variations.extend([
            'Indian Premier League',
            'IPL',
            'TATA IPL',
            'Vivo IPL'
        ])

    # BBL variations
    elif 'bbl' in league_lower or 'big bash' in league_lower:
        variations.extend([
            'Big Bash League',
            'BBL',
            'KFC Big Bash League',
            'Weber WBBL'  # Women's version
        ])

    # PSL variations
    elif 'psl' in league_lower or 'pakistan super league' in league_lower:
        variations.extend([
            'Pakistan Super League',
            'PSL',
            'HBL PSL'
        ])

    # CPL variations
    elif 'cpl' in league_lower or 'caribbean premier league' in league_lower:
        variations.extend([
            'Caribbean Premier League',
            'CPL',
            'Hero CPL'
        ])

    # The Hundred variations
    elif 'hundred' in league_lower:
        variations.extend([
            'The Hundred',
            'The Hundred Men',
            'The Hundred Women'
        ])

    return variations


def expand_league_abbreviations(abbrevs: List[str]) -> List[str]:
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
