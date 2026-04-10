#!/usr/bin/env python3
"""
Audit: Static Roster Names vs Database

For every player in ipl_rosters.py, checks:
1. Alias resolution in player_aliases table
2. Whether the alias points to the right player (wrong-match detection)
3. Delivery data presence in deliveries + delivery_details tables

Output: formatted table grouped by team with status per player.
Statuses: OK, NO_DATA, WRONG_MATCH, NO_ALIAS
"""

import sys
import os

# Add the blah directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from dotenv import load_dotenv

load_dotenv()
# Also load from cdt .env which has the prod DATABASE_URL
load_dotenv(os.path.expanduser("~/cdt/cricket-data-thing/.env"), override=True)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aditya:aditya123@localhost:5432/cricket_db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

from ipl_rosters import IPL_2026_ROSTERS


def check_alias(db, name: str) -> dict:
    """Check player_aliases for this name (both directions)."""
    # Check as alias_name (display/new name)
    row = db.execute(
        text("SELECT id, player_name, alias_name FROM player_aliases WHERE LOWER(alias_name) = LOWER(:n) LIMIT 1"),
        {"n": name},
    ).fetchone()
    if row:
        return {"match_type": "alias_name", "id": row[0], "player_name": row[1], "alias_name": row[2]}

    # Check as player_name (legacy name)
    row = db.execute(
        text("SELECT id, player_name, alias_name FROM player_aliases WHERE LOWER(player_name) = LOWER(:n) LIMIT 1"),
        {"n": name},
    ).fetchone()
    if row:
        return {"match_type": "player_name", "id": row[0], "player_name": row[1], "alias_name": row[2]}

    return None


def check_wrong_match(roster_name: str, alias_result: dict) -> bool:
    """
    Detect if alias matched the wrong person.
    Compares roster full name against both player_name and alias_name.
    A wrong match is when only a surname matches but the first name is different.
    """
    if not alias_result:
        return False

    roster_lower = roster_name.lower().strip()
    pn = (alias_result["player_name"] or "").lower().strip()
    an = (alias_result["alias_name"] or "").lower().strip()

    # Exact match on either side is fine
    if roster_lower == pn or roster_lower == an:
        return False

    # Check if roster name is a known abbreviation of the alias
    # e.g. "KL Rahul" matching "KL Rahul" - handled above
    # e.g. "M Siddharth" matching "Manimaran Siddharth" — ok if last name matches
    roster_parts = roster_lower.split()
    pn_parts = pn.split()
    an_parts = an.split()

    # If last names match and roster has an initial that matches first letter of full name, it's OK
    if len(roster_parts) >= 2 and len(an_parts) >= 2:
        if roster_parts[-1] == an_parts[-1]:
            # Last name matches — check if first part is an initial
            if len(roster_parts[0]) <= 2 and an_parts[0].startswith(roster_parts[0].rstrip(".")):
                return False
    if len(roster_parts) >= 2 and len(pn_parts) >= 2:
        if roster_parts[-1] == pn_parts[-1]:
            if len(roster_parts[0]) <= 2 and pn_parts[0].startswith(roster_parts[0].rstrip(".")):
                return False

    # If we got here, the names don't match well — flag as potential wrong match
    return True


def count_delivery_rows(db, name: str, canonical: str = None) -> dict:
    """Count rows in deliveries and delivery_details for this player."""
    names_to_check = {name}
    if canonical and canonical.lower() != name.lower():
        names_to_check.add(canonical)

    total_del = 0
    total_dd = 0

    for n in names_to_check:
        # deliveries table (batter/bowler columns)
        row = db.execute(
            text("SELECT COUNT(*) FROM deliveries WHERE LOWER(batter) = LOWER(:n) OR LOWER(bowler) = LOWER(:n)"),
            {"n": n},
        ).fetchone()
        total_del += row[0]

        # delivery_details table (bat/bowl columns on prod, batter/bowler on local)
        row = db.execute(
            text("SELECT COUNT(*) FROM delivery_details WHERE LOWER(bat) = LOWER(:n) OR LOWER(bowl) = LOWER(:n)"),
            {"n": n},
        ).fetchone()
        total_dd += row[0]

    return {"deliveries": total_del, "delivery_details": total_dd}


def fuzzy_search_db(db, name: str) -> list:
    """Search for similar names in deliveries when exact match fails."""
    # Use last name for fuzzy search
    parts = name.split()
    if len(parts) < 2:
        search_term = name
    else:
        search_term = parts[-1]  # last name

    results = db.execute(
        text("""
            SELECT DISTINCT name_found, source FROM (
                SELECT batter AS name_found, 'deliveries.batter' AS source FROM deliveries
                WHERE LOWER(batter) LIKE :pattern
                UNION
                SELECT bowler, 'deliveries.bowler' FROM deliveries
                WHERE LOWER(bowler) LIKE :pattern
                UNION
                SELECT bat, 'delivery_details.bat' FROM delivery_details
                WHERE LOWER(bat) LIKE :pattern
                UNION
                SELECT bowl, 'delivery_details.bowl' FROM delivery_details
                WHERE LOWER(bowl) LIKE :pattern
            ) sub
            ORDER BY name_found
            LIMIT 10
        """),
        {"pattern": f"%{search_term.lower()}%"},
    ).fetchall()

    return [(r[0], r[1]) for r in results]


def main():
    db = Session()
    try:
        issues = {"NO_DATA": [], "WRONG_MATCH": [], "NO_ALIAS": []}
        all_results = []

        for team_abbrev, team_data in IPL_2026_ROSTERS.items():
            team_name = team_data["full_name"]
            players = team_data["players"]

            print(f"\n{'='*90}")
            print(f"  {team_abbrev} — {team_name}  ({len(players)} players)")
            print(f"{'='*90}")
            print(f"  {'Player':<30} {'Role':<14} {'Alias':<30} {'Del':>6} {'DD':>6}  Status")
            print(f"  {'-'*30} {'-'*14} {'-'*30} {'-'*6} {'-'*6}  {'-'*12}")

            for p in players:
                name = p["name"]
                role = p["role"]

                alias_result = check_alias(db, name)
                wrong = check_wrong_match(name, alias_result) if alias_result else False

                canonical = None
                alias_display = "—"
                if alias_result:
                    if alias_result["match_type"] == "alias_name":
                        canonical = alias_result["player_name"]
                        alias_display = f"→ {canonical} (legacy)"
                    else:
                        canonical = alias_result["alias_name"]
                        alias_display = f"→ {canonical} (detail)"

                counts = count_delivery_rows(db, name, canonical)
                total = counts["deliveries"] + counts["delivery_details"]

                if wrong:
                    status = "WRONG_MATCH"
                elif total == 0 and alias_result:
                    status = "NO_DATA"
                elif total == 0 and not alias_result:
                    status = "NO_DATA"
                elif not alias_result and total > 0:
                    status = "NO_ALIAS"
                else:
                    status = "OK"

                marker = ""
                if status == "WRONG_MATCH":
                    marker = " !!!"
                    issues["WRONG_MATCH"].append((team_abbrev, name, alias_display))
                elif status == "NO_DATA":
                    marker = " *"
                    issues["NO_DATA"].append((team_abbrev, name, role))
                elif status == "NO_ALIAS":
                    marker = " ~"
                    issues["NO_ALIAS"].append((team_abbrev, name))

                print(f"  {name:<30} {role:<14} {alias_display:<30} {counts['deliveries']:>6} {counts['delivery_details']:>6}  {status}{marker}")

                all_results.append({
                    "team": team_abbrev,
                    "name": name,
                    "role": role,
                    "alias": alias_result,
                    "wrong_match": wrong,
                    "counts": counts,
                    "status": status,
                })

            # For NO_DATA players, do fuzzy search to find possible DB names
            no_data_players = [r for r in all_results if r["team"] == team_abbrev and r["status"] in ("NO_DATA",)]
            if no_data_players:
                print(f"\n  Fuzzy search for NO_DATA players:")
                for r in no_data_players:
                    suggestions = fuzzy_search_db(db, r["name"])
                    if suggestions:
                        print(f"    {r['name']}  →  possible matches:")
                        for s_name, s_source in suggestions:
                            print(f"      - {s_name}  ({s_source})")
                    else:
                        print(f"    {r['name']}  →  no similar names found (likely uncapped/new)")

        # Summary
        print(f"\n{'='*90}")
        print(f"  SUMMARY")
        print(f"{'='*90}")
        total_players = len(all_results)
        ok_count = sum(1 for r in all_results if r["status"] == "OK")
        print(f"  Total players: {total_players}")
        print(f"  OK:            {ok_count}")
        print(f"  NO_ALIAS:      {len(issues['NO_ALIAS'])}  (have data but no alias row)")
        print(f"  NO_DATA:       {len(issues['NO_DATA'])}  (no delivery data found)")
        print(f"  WRONG_MATCH:   {len(issues['WRONG_MATCH'])}  (alias points to wrong player)")

        if issues["WRONG_MATCH"]:
            print(f"\n  WRONG_MATCH details:")
            for team, name, alias in issues["WRONG_MATCH"]:
                print(f"    [{team}] {name}  {alias}")

        if issues["NO_ALIAS"]:
            print(f"\n  NO_ALIAS players (have data, need alias row):")
            for team, name in issues["NO_ALIAS"]:
                print(f"    [{team}] {name}")

        if issues["NO_DATA"]:
            print(f"\n  NO_DATA players (may need name fix or are genuinely uncapped):")
            for team, name, role in issues["NO_DATA"]:
                print(f"    [{team}] {name} ({role})")

    finally:
        db.close()


if __name__ == "__main__":
    main()
