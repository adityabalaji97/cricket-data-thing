"""
Refresh query_builder_metadata table with precomputed values.

Run after data loads or periodically:
    python scripts/refresh_query_builder_metadata.py --db-url "postgres://..."
"""

import os
import sys
import argparse
import json
from datetime import datetime
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_engine(db_url):
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)


def refresh_metadata(engine):
    """Refresh all metadata from delivery_details."""
    
    print("Refreshing query_builder_metadata...")
    start_time = datetime.now()
    
    with engine.begin() as conn:
        # Get total count first
        total_count = conn.execute(text("SELECT COUNT(*) FROM delivery_details")).scalar()
        print(f"Total deliveries: {total_count:,}")
        
        # Define columns to cache with their coverage calculation
        columns_config = [
            # (key, column_name, needs_coverage)
            ("line", "line", True),
            ("length", "length", True),
            ("shot", "shot", True),
            ("control", "control", True),
            ("wagon_zone", "wagon_zone", True),
            ("bowl_style", "bowl_style", True),
            ("bowl_kind", "bowl_kind", True),
            ("bat_hand", "bat_hand", True),
            ("venues", "ground", False),
            ("batters", "bat", False),
            ("bowlers", "bowl", False),
            ("batting_teams", "team_bat", False),
            ("bowling_teams", "team_bowl", False),
            ("competitions", "competition", False),
        ]
        
        for key, column, needs_coverage in columns_config:
            print(f"  Processing {key}...", end=" ")
            
            # Get distinct values
            values_query = text(f"""
                SELECT DISTINCT {column} 
                FROM delivery_details 
                WHERE {column} IS NOT NULL 
                ORDER BY {column}
            """)
            values = [row[0] for row in conn.execute(values_query).fetchall()]
            
            # Calculate coverage if needed
            coverage = None
            if needs_coverage:
                coverage_query = text(f"""
                    SELECT COUNT(*) FROM delivery_details WHERE {column} IS NOT NULL
                """)
                non_null_count = conn.execute(coverage_query).scalar()
                coverage = round((non_null_count / total_count * 100), 1) if total_count > 0 else 0
            
            # Upsert into metadata table
            upsert_query = text("""
                INSERT INTO query_builder_metadata (key, values, coverage_percent, distinct_count, updated_at)
                VALUES (:key, :values, :coverage, :distinct_count, NOW())
                ON CONFLICT (key) DO UPDATE SET
                    values = :values,
                    coverage_percent = :coverage,
                    distinct_count = :distinct_count,
                    updated_at = NOW()
            """)
            
            conn.execute(upsert_query, {
                "key": key,
                "values": json.dumps(values),
                "coverage": coverage,
                "distinct_count": len(values)
            })
            
            coverage_str = f"({coverage}% coverage)" if coverage else ""
            print(f"{len(values):,} values {coverage_str}")
        
        # Store total count
        conn.execute(text("""
            INSERT INTO query_builder_metadata (key, values, distinct_count, updated_at)
            VALUES ('total_deliveries', :values, :count, NOW())
            ON CONFLICT (key) DO UPDATE SET
                values = :values,
                distinct_count = :count,
                updated_at = NOW()
        """), {"values": json.dumps(total_count), "count": total_count})
        
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n✓ Metadata refresh complete in {elapsed:.1f}s")


def show_metadata(engine):
    """Display current metadata."""
    print("\nCurrent metadata:")
    print("-" * 60)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT key, distinct_count, coverage_percent, updated_at
            FROM query_builder_metadata
            ORDER BY key
        """))
        
        for row in result:
            coverage = f"{row[2]}%" if row[2] else "-"
            print(f"  {row[0]:<20} {row[1]:>8} values  {coverage:>8} coverage  (updated: {row[3]})")


def main():
    parser = argparse.ArgumentParser(description='Refresh query builder metadata')
    parser.add_argument('--db-url', required=True, help='Database URL')
    parser.add_argument('--show-only', action='store_true', help='Only show current metadata')
    args = parser.parse_args()
    
    engine = get_engine(args.db_url)
    
    if args.show_only:
        show_metadata(engine)
    else:
        refresh_metadata(engine)
        show_metadata(engine)


if __name__ == "__main__":
    main()
