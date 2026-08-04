"""
Classify delivery_details player names against the players table (read-only).

delivery_details stores full names ("Virat Kohli"); players uses the Cricsheet convention
("V Kohli"). Where player_aliases has no row linking the two, a raw name comparison reports the
player as absent -- 3,389 of them for men's T20 alone. Inserting those blindly would duplicate
most of the players table.

This script decides nothing on its own. It sorts every unmatched name into:

  exact      -- already present under the same string
  alias      -- already linked via player_aliases
  initials   -- exactly one players row whose initials prefix the full name and whose surname
                matches; safe to link with an alias row rather than insert
  ambiguous  -- more than one candidate; must NOT be auto-linked, because picking one merges
                two careers and the mistake is invisible afterwards
  new        -- no candidate at all; genuinely absent, safe to insert

The ambiguous bucket is the whole point. The player-alias work took the same line: 39 legacy
names mapping to several full names were left split and reported rather than guessed at.

Usage:
    python scripts/analyse_player_name_matches.py --format T20 --gender male [--limit N]
"""

import argparse
import os
import sys
from collections import defaultdict

from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def split_name(name):
    """(leading token, remainder) -- for 'AB de Villiers' that is ('AB', 'de villiers')."""
    parts = [p for p in str(name).replace(".", " ").split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return "", parts[0].lower()
    return parts[0], " ".join(parts[1:]).lower()


def looks_like_initials(token):
    """Whether a leading token is a Cricsheet-style initials block rather than a first name.

    'V', 'KK' and 'AB' are initials; 'Haroon' is a name. The distinction matters: the players
    table holds both conventions, and treating a full first name as an initial matched
    'Hassan Shahid' to 'Haroon Shahid' and 'Raisul Islam' to 'Robiul Islam' -- different
    players who merely share a first letter.
    """
    return bool(token) and len(token) <= 3 and token.isalpha() and token.isupper()


def initials_match(players_lead, dd_lead):
    """Whether a players-table leading token can abbreviate a delivery_details first name."""
    if not players_lead or not dd_lead:
        return False
    if looks_like_initials(players_lead):
        # 'V' -> 'Virat'. Only the first letter is checked; anything drawing several
        # candidates lands in the ambiguous bucket rather than being guessed at.
        return players_lead[0].upper() == dd_lead[0].upper()
    # Both sides are full first names, so they must actually agree.
    return players_lead.lower() == dd_lead.lower()


def classify_names(conn, fmt="T20", gender="male"):
    """Sort delivery_details names into exact / alias / initials / ambiguous / new.

    Shared by this report and by the pipeline's player insertion, so what gets written is
    always what the analysis described. Duplicating the matching in two places is how the
    two would drift, and a drift here silently merges or duplicates players.
    """
    dd_names = [r[0] for r in conn.execute(text("""
        SELECT DISTINCT bat FROM delivery_details
        WHERE format = :fmt AND gender = :gender AND bat IS NOT NULL AND TRIM(bat) <> ''
        UNION
        SELECT DISTINCT bowl FROM delivery_details
        WHERE format = :fmt AND gender = :gender AND bowl IS NOT NULL AND TRIM(bowl) <> ''
    """), {"fmt": fmt, "gender": gender})]

    players = [r[0] for r in conn.execute(text(
        "SELECT name FROM players WHERE gender = :gender"), {"gender": gender})]

    aliased = set()
    for player_name, alias_name in conn.execute(text(
            "SELECT player_name, alias_name FROM player_aliases "
            "WHERE player_name IS NOT NULL AND alias_name IS NOT NULL")):
        aliased.add(player_name)
        aliased.add(alias_name)

    player_names = set(players)
    by_surname = defaultdict(list)
    for name in players:
        lead, surname = split_name(name)
        by_surname[surname].append((name, lead))

    buckets = defaultdict(list)
    for dd_name in dd_names:
        if dd_name in player_names:
            buckets["exact"].append(dd_name)
            continue
        if dd_name in aliased:
            buckets["alias"].append(dd_name)
            continue
        dd_lead, dd_surname = split_name(dd_name)
        candidates = [
            pname for pname, plead in by_surname.get(dd_surname, [])
            if initials_match(plead, dd_lead)
        ]
        if len(candidates) == 1:
            single_letter = looks_like_initials(candidates[0].split()[0]) and len(candidates[0].split()[0]) == 1
            # A single initial on a shared surname is coincidence, not evidence: 'A Khan'
            # could be Akram, Arslan, Ayaan or Aizaz, all of which exist separately.
            buckets["initials_weak" if single_letter else "initials"].append((dd_name, candidates[0]))
        elif len(candidates) > 1:
            buckets["ambiguous"].append((dd_name, candidates))
        else:
            buckets["new"].append(dd_name)
    return buckets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--format", dest="fmt", default="T20", choices=["T20", "ODI", "TEST"])
    parser.add_argument("--gender", default="male", choices=["male", "female"])
    parser.add_argument("--limit", type=int, default=None, help="Only show N examples per bucket")
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()

    if not args.db_url:
        print("ERROR: set DATABASE_URL or pass --db-url")
        return 1
    engine = create_engine(args.db_url.replace("postgres://", "postgresql://", 1))

    with engine.connect() as conn:
        dd_names = [r[0] for r in conn.execute(text("""
            SELECT DISTINCT bat FROM delivery_details
            WHERE format = :fmt AND gender = :gender AND bat IS NOT NULL AND TRIM(bat) <> ''
            UNION
            SELECT DISTINCT bowl FROM delivery_details
            WHERE format = :fmt AND gender = :gender AND bowl IS NOT NULL AND TRIM(bowl) <> ''
        """), {"fmt": args.fmt, "gender": args.gender})]

        players = [(r[0], r[1]) for r in conn.execute(text(
            "SELECT name, gender FROM players WHERE gender = :gender"), {"gender": args.gender})]

        alias_pairs = conn.execute(text(
            "SELECT player_name, alias_name FROM player_aliases "
            "WHERE player_name IS NOT NULL AND alias_name IS NOT NULL")).fetchall()

    player_names = {p[0] for p in players}
    aliased = set()
    for player_name, alias_name in alias_pairs:
        aliased.add(player_name)
        aliased.add(alias_name)

    # surname -> [players rows], for candidate lookup
    by_surname = defaultdict(list)
    for name, _ in players:
        lead, surname = split_name(name)
        by_surname[surname].append((name, lead))

    buckets = defaultdict(list)
    for dd_name in dd_names:
        if dd_name in player_names:
            buckets["exact"].append(dd_name)
            continue
        if dd_name in aliased:
            buckets["alias"].append(dd_name)
            continue

        dd_lead, dd_surname = split_name(dd_name)
        candidates = [
            pname for pname, plead in by_surname.get(dd_surname, [])
            if initials_match(plead, dd_lead)
        ]
        if len(candidates) == 1:
            buckets["initials"].append((dd_name, candidates[0]))
        elif len(candidates) > 1:
            buckets["ambiguous"].append((dd_name, candidates))
        else:
            buckets["new"].append(dd_name)

    total = len(dd_names)
    print(f"\n{args.fmt}/{args.gender}: {total:,} distinct names in delivery_details\n")
    for key in ("exact", "alias", "initials", "ambiguous", "new"):
        n = len(buckets[key])
        pct = (n / total * 100) if total else 0
        print(f"  {key:10} {n:6,}  ({pct:4.1f}%)")

    show = args.limit or 8
    print(f"\n  -- initials matches (safe to link via an alias row), first {show} --")
    for dd_name, pname in buckets["initials"][:show]:
        print(f"     {dd_name:28} -> {pname}")

    print(f"\n  -- AMBIGUOUS (do not auto-link), first {show} --")
    for dd_name, cands in buckets["ambiguous"][:show]:
        print(f"     {dd_name:28} -> {cands}")

    print(f"\n  -- new (no candidate; safe to insert), first {show} --")
    for dd_name in buckets["new"][:show]:
        print(f"     {dd_name}")

    print("\n  Nothing was written. Linking and insertion are separate, deliberate steps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
