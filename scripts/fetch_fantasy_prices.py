#!/usr/bin/env python3
"""
Scraper for IPL 2026 fantasy player prices from fantasy.iplt20.com.

Fetches all player credits/prices from the official season-long fantasy API
and saves them to data/ipl_2026_player_prices.json.

Requires auth cookies from a logged-in fantasy.iplt20.com session.

Usage:
    python scripts/fetch_fantasy_prices.py --auth-token <JWT> [--cookie <my11_cla cookie>]

    # Or set env vars:
    export FANTASY_AUTH_TOKEN="eyJhbG..."
    export FANTASY_COOKIE='{"UserName":"...","GUID":"..."}'
    python scripts/fetch_fantasy_prices.py
"""

import argparse
import json
import os
import sys
import urllib.parse
from pathlib import Path

from typing import Optional

import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://fantasy.iplt20.com/classic/api"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "ipl_2026_player_prices.json"

SKILL_MAP = {
    "BATSMAN": "batter",
    "BOWLER": "bowler",
    "ALL ROUNDER": "all-rounder",
    "WICKET KEEPER": "wicket-keeper",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def build_cookies(auth_token: str, my11_cla: Optional[str] = None) -> str:
    """Build cookie header string."""
    parts = [f"my11c-authToken={auth_token}"]
    if my11_cla:
        # URL-encode if it's raw JSON
        if my11_cla.startswith("{"):
            my11_cla = urllib.parse.quote(my11_cla)
        parts.append(f"my11_cla={my11_cla}")
    return "; ".join(parts)


def fetch_fixtures(cookies: str) -> list:
    """Fetch tour fixtures to get gameday IDs."""
    resp = requests.get(
        f"{BASE_URL}/feed/tour-fixtures",
        headers={**HEADERS, "Cookie": cookies},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("Data", {}).get("Value"):
        print("ERROR: Could not fetch fixtures. Token may be expired.")
        sys.exit(1)

    return data["Data"]["Value"]


def fetch_players(cookies: str, gameday_id: int, tour_gameday_id: int, phase_id: int) -> list:
    """Fetch all players for a given gameday."""
    resp = requests.get(
        f"{BASE_URL}/feed/gamedayplayers",
        params={
            "optType": 1,
            "gamedayId": gameday_id,
            "tourgamedayId": tour_gameday_id,
            "phaseId": phase_id,
        },
        headers={**HEADERS, "Cookie": cookies},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    meta = data.get("Meta", {})
    if not meta.get("Success", True) and meta.get("RetVal") == -40:
        return []

    players_data = data.get("Data", {}).get("Value", {}).get("Players", [])
    return players_data


def transform_player(raw: dict) -> dict:
    """Transform raw API player to our format."""
    return {
        "id": raw["Id"],
        "name": raw["Name"],
        "team": raw["TeamShortName"],
        "team_full": raw["TeamName"],
        "team_id": raw["TeamId"],
        "role": SKILL_MAP.get(raw["SkillName"], raw["SkillName"].lower()),
        "role_raw": raw["SkillName"],
        "credits": raw["Value"],
        "is_overseas": raw["isUnCap"] == 0 and not _is_indian(raw),
        "is_uncapped": raw["isUnCap"] == 1,
        "selected_pct": raw.get("SelectedPer", 0),
        "cap_selected_pct": raw.get("CapSelectedPer", 0),
        "vcap_selected_pct": raw.get("VCapSelectedPer", 0),
    }


def _is_indian(player: dict) -> bool:
    """Heuristic: uncapped players are always Indian in IPL context.
    For capped players, we can't determine nationality from this API alone,
    so we leave is_overseas as False by default and rely on ipl_rosters.py
    for the authoritative overseas flag."""
    return player.get("isUnCap") == 1


def resolve_names(players: list) -> list:
    """Resolve fantasy names to our canonical DB names."""
    try:
        from database import SessionLocal
        from services.player_aliases import resolve_to_legacy_name, get_player_names
    except Exception as e:
        print(f"  Skipping name resolution (DB not available): {e}")
        return players

    db = SessionLocal()
    resolved = 0
    try:
        for p in players:
            original = p["name"]
            legacy = resolve_to_legacy_name(original, db)
            names = get_player_names(legacy, db)
            canonical = names["legacy_name"]
            if canonical != original:
                p["name_fantasy"] = original
                p["name"] = canonical
                resolved += 1
        print(f"  Resolved {resolved}/{len(players)} names to canonical form")
    finally:
        db.close()

    return players


def main():
    parser = argparse.ArgumentParser(description="Fetch fantasy player prices from fantasy.iplt20.com")
    parser.add_argument("--auth-token", default=os.environ.get("FANTASY_AUTH_TOKEN"),
                        help="my11c-authToken JWT (or set FANTASY_AUTH_TOKEN env var)")
    parser.add_argument("--cookie", default=os.environ.get("FANTASY_COOKIE"),
                        help="my11_cla cookie JSON (or set FANTASY_COOKIE env var)")
    parser.add_argument("--no-resolve", action="store_true",
                        help="Skip canonical name resolution via DB")
    parser.add_argument("--output", default=str(OUTPUT_PATH),
                        help=f"Output file path (default: {OUTPUT_PATH})")
    args = parser.parse_args()

    if not args.auth_token:
        print("ERROR: --auth-token is required (or set FANTASY_AUTH_TOKEN env var)")
        print("Get it from browser DevTools > Application > Cookies > my11c-authToken")
        sys.exit(1)

    cookies = build_cookies(args.auth_token, args.cookie)

    # 1. Fetch fixtures to find the first active gameday
    print("Fetching tour fixtures...")
    fixtures = fetch_fixtures(cookies)
    print(f"  Found {len(fixtures)} fixtures")

    # Use the first fixture (gameday 1) — all players are available for pre-season
    first = fixtures[0]
    gd_id = first["TeamGamedayId"]
    tgd_id = first["TourGamedayId"]
    phase_id = first["PhaseId"]
    print(f"  Using gameday {gd_id} (match: {first['MatchName']})")

    # 2. Fetch all players
    print("Fetching player prices...")
    raw_players = fetch_players(cookies, gd_id, tgd_id, phase_id)
    if not raw_players:
        print("ERROR: No players returned. Auth token may be expired.")
        sys.exit(1)
    print(f"  Fetched {len(raw_players)} players")

    # 3. Transform
    players = [transform_player(p) for p in raw_players]

    # 4. Resolve names
    if not args.no_resolve:
        print("Resolving names to canonical form...")
        players = resolve_names(players)

    # 5. Build output
    from collections import Counter
    teams = Counter(p["team"] for p in players)
    roles = Counter(p["role"] for p in players)

    output = {
        "source": "fantasy.iplt20.com",
        "season": "IPL 2026",
        "fetched_from_match": first["MatchName"],
        "total_players": len(players),
        "by_team": dict(sorted(teams.items())),
        "by_role": dict(sorted(roles.items())),
        "players": sorted(players, key=lambda p: (-p["credits"], p["name"])),
    }

    # 6. Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(players)} players to {output_path}")
    print(f"  Teams: {dict(sorted(teams.items()))}")
    print(f"  Roles: {dict(sorted(roles.items()))}")

    # Show top players by credits
    print(f"\nTop 10 by credits:")
    for p in output["players"][:10]:
        print(f"  {p['credits']:5.1f} cr  {p['name']:25s} ({p['team']}) {p['role']}")


if __name__ == "__main__":
    main()
