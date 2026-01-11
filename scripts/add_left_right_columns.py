"""
Add left-right analysis columns to delivery_details.
Data is already loaded - just need to add and populate columns.

Usage:
    python scripts/add_left_right_columns.py --db-url "$DATABASE_URL"
    python scripts/add_left_right_columns.py --dry-run
    
    # Using environment variable:
    python scripts/add_left_right_columns.py
"""

import os
import sys
import argparse
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_engine(db_url):
    """Create database engine."""
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)


def add_columns(engine):
    """Add the 4 new columns if they don't exist."""
    print("=" * 60)
    print("STEP 1: Adding columns...")
    print("=" * 60)
    
    columns = [
        ("non_striker", "VARCHAR(100)"),
        ("striker_batter_type", "VARCHAR(10)"),
        ("non_striker_batter_type", "VARCHAR(10)"),
        ("crease_combo", "VARCHAR(20)"),
    ]
    
    with engine.connect() as conn:
        # Get existing columns
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'delivery_details'
        """))
        existing = {row[0] for row in result.fetchall()}
        
        for col_name, col_type in columns:
            if col_name not in existing:
                conn.execute(text(f"ALTER TABLE delivery_details ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"  Added: {col_name}")
            else:
                print(f"  Exists: {col_name}")


def populate_non_striker(engine):
    """Get non_striker from deliveries table."""
    print("\n" + "=" * 60)
    print("STEP 2: Populating non_striker from deliveries table...")
    print("=" * 60)
    
    sql = """
        UPDATE delivery_details dd
        SET non_striker = d.non_striker
        FROM deliveries d
        WHERE dd.p_match::text = d.match_id
          AND dd.inns = d.innings
          AND dd.over = d.over
          AND dd.ball = d.ball
          AND dd.non_striker IS NULL
          AND d.non_striker IS NOT NULL
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        conn.commit()
        print(f"  Updated {result.rowcount:,} rows")
        
        # Check coverage
        result = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE non_striker IS NOT NULL"))
        has_ns = result.scalar()
        result = conn.execute(text("SELECT COUNT(*) FROM delivery_details"))
        total = result.scalar()
        if total > 0:
            print(f"  Coverage: {has_ns:,} / {total:,} ({100*has_ns/total:.1f}%)")
    
    return has_ns


def infer_non_striker(engine):
    """Infer non_striker from ball sequence for any still missing."""
    print("\n" + "=" * 60)
    print("STEP 3: Inferring non_striker from sequence...")
    print("=" * 60)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE non_striker IS NULL"))
        missing = result.scalar()
        print(f"  Missing: {missing:,}")
        
        if missing == 0:
            return 0
        
        sql = """
            WITH ordered_balls AS (
                SELECT id, p_match, inns, over, ball, bat, non_striker,
                    LAG(bat) OVER (PARTITION BY p_match, inns ORDER BY over, ball) as prev_bat,
                    LEAD(bat) OVER (PARTITION BY p_match, inns ORDER BY over, ball) as next_bat
                FROM delivery_details
            ),
            inferred AS (
                SELECT id,
                    CASE
                        WHEN bat != prev_bat AND prev_bat IS NOT NULL THEN prev_bat
                        WHEN bat != next_bat AND next_bat IS NOT NULL THEN next_bat
                    END as inferred_ns
                FROM ordered_balls WHERE non_striker IS NULL
            )
            UPDATE delivery_details dd
            SET non_striker = i.inferred_ns
            FROM inferred i
            WHERE dd.id = i.id AND i.inferred_ns IS NOT NULL
        """
        
        result = conn.execute(text(sql))
        conn.commit()
        print(f"  Inferred {result.rowcount:,} rows")
        
        result = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE non_striker IS NULL"))
        still_missing = result.scalar()
        print(f"  Still missing: {still_missing:,}")
    
    return result.rowcount


def populate_striker_batter_type(engine):
    """Copy bat_hand to striker_batter_type."""
    print("\n" + "=" * 60)
    print("STEP 4: Populating striker_batter_type from bat_hand...")
    print("=" * 60)
    
    sql = """
        UPDATE delivery_details
        SET striker_batter_type = bat_hand
        WHERE striker_batter_type IS NULL
          AND bat_hand IS NOT NULL
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        conn.commit()
        print(f"  Updated {result.rowcount:,} rows")


def populate_non_striker_batter_type(engine):
    """Lookup non_striker batting hand from players table."""
    print("\n" + "=" * 60)
    print("STEP 5: Populating non_striker_batter_type from players...")
    print("=" * 60)
    
    sql = """
        UPDATE delivery_details dd
        SET non_striker_batter_type = p.batting_hand
        FROM players p
        WHERE dd.non_striker = p.name
          AND dd.non_striker_batter_type IS NULL
          AND p.batting_hand IS NOT NULL
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        conn.commit()
        print(f"  Updated {result.rowcount:,} rows")
        
        # Check coverage
        result = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE non_striker_batter_type IS NOT NULL"))
        has_type = result.scalar()
        result = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE non_striker IS NOT NULL"))
        has_ns = result.scalar()
        if has_ns > 0:
            print(f"  Coverage: {has_type:,} / {has_ns:,} ({100*has_type/has_ns:.1f}% of rows with non_striker)")


def generate_crease_combo(engine):
    """Generate crease_combo from striker and non_striker types."""
    print("\n" + "=" * 60)
    print("STEP 6: Generating crease_combo...")
    print("=" * 60)
    
    sql = """
        UPDATE delivery_details
        SET crease_combo = striker_batter_type || '_' || non_striker_batter_type
        WHERE striker_batter_type IS NOT NULL
          AND non_striker_batter_type IS NOT NULL
          AND crease_combo IS NULL
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        conn.commit()
        print(f"  Generated {result.rowcount:,} rows")


def print_summary(engine):
    """Print final summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM delivery_details")).scalar()
        with_ns = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE non_striker IS NOT NULL")).scalar()
        with_cc = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE crease_combo IS NOT NULL")).scalar()
        
        print(f"  Total records: {total:,}")
        if total > 0:
            print(f"  With non_striker: {with_ns:,} ({100*with_ns/total:.1f}%)")
            print(f"  With crease_combo: {with_cc:,} ({100*with_cc/total:.1f}%)")
        
        result = conn.execute(text("""
            SELECT crease_combo, COUNT(*) as cnt FROM delivery_details
            WHERE crease_combo IS NOT NULL GROUP BY crease_combo ORDER BY cnt DESC
        """))
        combos = result.fetchall()
        if combos:
            print("\n  Crease combo distribution:")
            for combo, count in combos:
                print(f"    {combo}: {count:,}")


def main():
    parser = argparse.ArgumentParser(description='Add left-right analysis columns to delivery_details')
    parser.add_argument('--db-url', help='Database URL (or set DATABASE_URL env var)')
    parser.add_argument('--dry-run', action='store_true', help='Show current state without making changes')
    args = parser.parse_args()
    
    # Get database URL
    db_url = args.db_url or os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: Database URL required. Use --db-url or set DATABASE_URL environment variable.")
        sys.exit(1)
    
    print("=" * 60)
    print("ADD LEFT-RIGHT ANALYSIS COLUMNS")
    print("=" * 60)
    
    engine = get_engine(db_url)
    db_display = db_url.split('@')[1] if '@' in db_url else 'localhost'
    print(f"Connecting to: {db_display}")
    
    if args.dry_run:
        print("\n*** DRY RUN MODE ***")
        print_summary(engine)
        return
    
    add_columns(engine)
    populate_non_striker(engine)
    infer_non_striker(engine)
    populate_striker_batter_type(engine)
    populate_non_striker_batter_type(engine)
    generate_crease_combo(engine)
    print_summary(engine)
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
