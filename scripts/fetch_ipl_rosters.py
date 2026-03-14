#!/usr/bin/env python3
"""
One-time scraper for IPL 2026 rosters from iplt20.com.

Fetches all 10 team pages, parses player names and roles,
resolves names through our canonical name resolver, and
outputs a Python config file (ipl_rosters.py).

Usage:
    python scripts/fetch_ipl_rosters.py [--resolve-names]

    --resolve-names  Connect to DB and resolve names via player_aliases
                     (requires DATABASE_URL or local postgres)
"""

import argparse
import json
import re
import sys
import os

import requests
from bs4 import BeautifulSoup

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEAM_SLUGS = {
    "CSK": "chennai-super-kings",
    "MI": "mumbai-indians",
    "KKR": "kolkata-knight-riders",
    "DC": "delhi-capitals",
    "GT": "gujarat-titans",
    "LSG": "lucknow-super-giants",
    "PBKS": "punjab-kings",
    "RR": "rajasthan-royals",
    "RCB": "royal-challengers-bengaluru",
    "SRH": "sunrisers-hyderabad",
}

TEAM_FULL_NAMES = {
    "CSK": "Chennai Super Kings",
    "MI": "Mumbai Indians",
    "KKR": "Kolkata Knight Riders",
    "DC": "Delhi Capitals",
    "GT": "Gujarat Titans",
    "LSG": "Lucknow Super Giants",
    "PBKS": "Punjab Kings",
    "RR": "Rajasthan Royals",
    "RCB": "Royal Challengers Bengaluru",
    "SRH": "Sunrisers Hyderabad",
}

BASE_URL = "https://www.iplt20.com/teams"


def normalize_role(role_text: str) -> str:
    """Normalize role text from iplt20.com to our standard roles."""
    role_lower = role_text.lower().strip()
    if "all-rounder" in role_lower or "all rounder" in role_lower:
        return "all-rounder"
    elif "bowl" in role_lower:
        return "bowler"
    else:
        return "batter"


def fetch_team_roster(team_abbrev: str, slug: str) -> list:
    """Fetch and parse a single team's roster from iplt20.com."""
    url = f"{BASE_URL}/{slug}"
    print(f"  Fetching {team_abbrev} from {url}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36"
    }

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    players = []

    # iplt20.com uses structured sections for each role category
    # Look for player cards/items with name and role info
    player_elements = soup.select(".ih-p-name, .player-name, [class*='player']")

    if not player_elements:
        print(f"  WARNING: Could not find player elements for {team_abbrev}")
        print(f"  Page title: {soup.title.string if soup.title else 'N/A'}")
        return players

    # Parse based on the page structure
    current_role = "batter"
    for elem in player_elements:
        name_tag = elem.select_one("h2, h3, .ih-p-name, a")
        role_tag = elem.select_one(".ih-p-role, .player-role, [class*='role']")

        if name_tag:
            name = name_tag.get_text(strip=True)
            role = normalize_role(role_tag.get_text()) if role_tag else current_role
            if name:
                players.append({"name": name, "role": role})

    print(f"  Found {len(players)} players for {team_abbrev}")
    return players


def resolve_names_via_db(rosters: dict) -> dict:
    """
    Resolve scraped names to canonical legacy names using our DB.
    Falls back to fuzzy matching if exact match fails.
    """
    from database import SessionLocal
    from services.player_aliases import resolve_to_legacy_name, get_player_names
    from sqlalchemy.sql import text

    db = SessionLocal()
    resolved_count = 0
    unresolved = []

    try:
        for abbrev, data in rosters.items():
            for player in data["players"]:
                original_name = player["name"]

                # Try alias resolution first
                names = get_player_names(original_name, db)
                legacy = names["legacy_name"]

                # Check if this legacy name exists in our players table
                exists = db.execute(
                    text("SELECT 1 FROM players WHERE LOWER(name) = LOWER(:n) LIMIT 1"),
                    {"n": legacy}
                ).fetchone()

                if exists:
                    player["name"] = legacy
                    if legacy != original_name:
                        resolved_count += 1
                        print(f"  Resolved: {original_name} -> {legacy}")
                    continue

                # Try fuzzy match against players table
                fuzzy = db.execute(
                    text("""
                        SELECT name FROM players
                        WHERE LOWER(name) LIKE :pattern
                        ORDER BY LENGTH(name)
                        LIMIT 3
                    """),
                    {"pattern": f"%{original_name.split()[-1].lower()}%"}
                ).fetchall()

                if fuzzy:
                    # Take the best match (shortest name containing the surname)
                    player["name"] = fuzzy[0][0]
                    resolved_count += 1
                    print(f"  Fuzzy resolved: {original_name} -> {fuzzy[0][0]}")
                else:
                    unresolved.append(f"{abbrev}: {original_name}")

        print(f"\nResolved {resolved_count} names")
        if unresolved:
            print(f"Unresolved ({len(unresolved)}):")
            for u in unresolved:
                print(f"  - {u}")

    finally:
        db.close()

    return rosters


def output_python_config(rosters: dict, output_path: str):
    """Write rosters dict as a Python config file."""
    print(f"\nWriting to {output_path}...")

    lines = ['"""', 'IPL 2026 Pre-Season Rosters', '',
             'Auto-generated by scripts/fetch_ipl_rosters.py',
             'Remove once the season starts.', '"""', '',
             'IPL_2026_ROSTERS = {']

    for abbrev, data in rosters.items():
        lines.append(f'    "{abbrev}": {{')
        lines.append(f'        "full_name": "{data["full_name"]}",')
        lines.append(f'        "players": [')
        for p in data["players"]:
            lines.append(f'            {{"name": "{p["name"]}", "role": "{p["role"]}"}},')
        lines.append(f'        ],')
        lines.append(f'    }},')

    lines.append('}')

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Done! Written {sum(len(d['players']) for d in rosters.values())} players across {len(rosters)} teams")


def main():
    parser = argparse.ArgumentParser(description="Fetch IPL 2026 rosters from iplt20.com")
    parser.add_argument("--resolve-names", action="store_true",
                        help="Resolve names via database player_aliases")
    parser.add_argument("--output", default="ipl_rosters_generated.py",
                        help="Output file path (default: ipl_rosters_generated.py)")
    args = parser.parse_args()

    print("Fetching IPL 2026 rosters from iplt20.com...")
    print("=" * 60)

    rosters = {}
    for abbrev, slug in TEAM_SLUGS.items():
        players = fetch_team_roster(abbrev, slug)
        rosters[abbrev] = {
            "full_name": TEAM_FULL_NAMES[abbrev],
            "players": players,
        }

    total = sum(len(d["players"]) for d in rosters.values())
    print(f"\nScraped {total} players across {len(rosters)} teams")

    if args.resolve_names:
        print("\nResolving names via database...")
        rosters = resolve_names_via_db(rosters)

    output_python_config(rosters, args.output)


if __name__ == "__main__":
    main()
