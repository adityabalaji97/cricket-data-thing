"""
Cleanup script to remove incorrect player aliases where last names don't match.

This script identifies and removes aliases created due to data mismatches between
the deliveries and delivery_details tables.

Usage:
    # Ensure DATABASE_URL is set (for example via a local .env)
    python scripts/cleanup_bad_aliases.py --db-url "$DATABASE_URL" --dry-run
    python scripts/cleanup_bad_aliases.py --db-url "$DATABASE_URL"
"""

import os
import sys
import argparse
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_engine(db_url):
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)


def get_last_name(full_name):
    """Extract last name from a player name."""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    return parts[-1] if parts else ""


def find_invalid_aliases(engine):
    """Find all aliases where last names don't match."""
    print("\nAnalyzing player_aliases table...")

    query = "SELECT id, player_name, alias_name FROM player_aliases"

    invalid_aliases = []

    with engine.connect() as conn:
        result = conn.execute(text(query))
        for row in result:
            id_, player_name, alias_name = row[0], row[1], row[2]

            player_last = get_last_name(player_name)
            alias_last = get_last_name(alias_name)

            # Check if last names don't match
            if player_last and alias_last and player_last != alias_last:
                invalid_aliases.append({
                    'id': id_,
                    'player_name': player_name,
                    'alias_name': alias_name,
                    'player_last': player_last,
                    'alias_last': alias_last
                })

    return invalid_aliases


def print_invalid_aliases(invalid_aliases):
    """Print invalid aliases for review."""
    print("\n" + "="*80)
    print("INVALID ALIASES FOUND (Last Name Mismatch)")
    print("="*80)

    # Group by alias_name to show the conflicts
    by_alias = {}
    for item in invalid_aliases:
        alias = item['alias_name']
        if alias not in by_alias:
            by_alias[alias] = []
        by_alias[alias].append(item)

    for alias in sorted(by_alias.keys()):
        items = by_alias[alias]
        if len(items) > 0:
            print(f"\n'{alias}' incorrectly points to:")
            for item in items:
                print(f"  ❌ {item['player_name']} (last: {item['player_last']} ≠ {item['alias_last']})")


def delete_invalid_aliases(engine, invalid_aliases, dry_run=False):
    """Delete invalid aliases from the database."""
    if not invalid_aliases:
        print("\n✅ No invalid aliases found!")
        return

    ids_to_delete = [item['id'] for item in invalid_aliases]

    print(f"\n{'[DRY RUN] Would delete' if dry_run else 'Deleting'} {len(ids_to_delete)} invalid aliases...")

    if dry_run:
        print("\nSample deletions:")
        for item in invalid_aliases[:10]:
            print(f"  ID {item['id']}: {item['player_name']} → {item['alias_name']}")
        if len(invalid_aliases) > 10:
            print(f"  ... and {len(invalid_aliases) - 10} more")
        return

    # Delete in batches
    batch_size = 100
    deleted = 0

    with engine.begin() as conn:
        for i in range(0, len(ids_to_delete), batch_size):
            batch = ids_to_delete[i:i+batch_size]
            placeholders = ','.join([f':id{j}' for j in range(len(batch))])
            params = {f'id{j}': id_ for j, id_ in enumerate(batch)}

            conn.execute(text(f"DELETE FROM player_aliases WHERE id IN ({placeholders})"), params)
            deleted += len(batch)
            print(f"  Deleted {deleted}/{len(ids_to_delete)}...", end='\r')

    print(f"\n✓ Deleted {deleted} invalid aliases")


def show_summary(engine):
    """Show summary statistics after cleanup."""
    print("\n" + "="*80)
    print("SUMMARY AFTER CLEANUP")
    print("="*80)

    with engine.connect() as conn:
        # Total aliases
        r = conn.execute(text("SELECT COUNT(*) FROM player_aliases"))
        print(f"Total aliases remaining: {r.scalar():,}")

        # Problematic aliases (pointing to multiple players)
        r = conn.execute(text("""
            SELECT COUNT(*)
            FROM (
                SELECT alias_name
                FROM player_aliases
                GROUP BY alias_name
                HAVING COUNT(DISTINCT player_name) > 1
            ) sub
        """))
        problematic = r.scalar()
        print(f"Aliases pointing to multiple players: {problematic}")

        if problematic > 0:
            r = conn.execute(text("""
                SELECT alias_name, string_agg(player_name, ', ') as players, COUNT(DISTINCT player_name) as num_players
                FROM player_aliases
                GROUP BY alias_name
                HAVING COUNT(DISTINCT player_name) > 1
                ORDER BY num_players DESC
                LIMIT 10
            """))
            print("\nRemaining multi-player aliases (may be legitimate variations):")
            for row in r:
                print(f"  '{row[0]}' → {row[1]}")


def main():
    parser = argparse.ArgumentParser(
        description='Cleanup invalid player aliases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (show what would be deleted)
  python scripts/cleanup_bad_aliases.py --db-url "$DATABASE_URL" --dry-run

  # Actually delete invalid aliases
  python scripts/cleanup_bad_aliases.py --db-url "$DATABASE_URL"
        """
    )
    parser.add_argument('--db-url', help='Database URL (or set DATABASE_URL env var)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without making changes')
    args = parser.parse_args()

    # Get database URL
    db_url = args.db_url or os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: Database URL required. Use --db-url or set DATABASE_URL environment variable.")
        sys.exit(1)

    engine = get_engine(db_url)
    db_display = db_url.split('@')[1] if '@' in db_url else 'localhost'

    print("="*80)
    print("PLAYER ALIASES CLEANUP SCRIPT")
    print("="*80)
    print(f"Database: {db_display}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE EXECUTION'}")
    print("="*80)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***")

    # Find invalid aliases
    invalid_aliases = find_invalid_aliases(engine)

    print(f"\nFound {len(invalid_aliases)} invalid aliases")

    if invalid_aliases:
        # Print them for review
        print_invalid_aliases(invalid_aliases)

        # Delete them
        delete_invalid_aliases(engine, invalid_aliases, dry_run=args.dry_run)

    if not args.dry_run and invalid_aliases:
        # Show summary
        show_summary(engine)

    print("\n" + "="*80)
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes were made")
    else:
        print("CLEANUP COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
