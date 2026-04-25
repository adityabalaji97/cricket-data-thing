"""
Create performance indexes on delivery_details for venue similarity queries.

Usage:
    python create_indexes.py

Reads DATABASE_URL from .env (same as the app).
Uses autocommit mode because CREATE INDEX CONCURRENTLY cannot run inside a transaction.
"""

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Use psycopg2 directly for autocommit (required by CREATE INDEX CONCURRENTLY)
try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

INDEXES = [
    ("idx_dd_ground", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_ground ON delivery_details(ground)"),
    ("idx_dd_ground_over", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_ground_over ON delivery_details(ground, over)"),
    ("idx_dd_ground_line_length", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_ground_line_length ON delivery_details(ground, line, length)"),
    ("idx_dd_ground_wagon_zone", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_ground_wagon_zone ON delivery_details(ground, wagon_zone)"),
    ("idx_dd_match_date", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_match_date ON delivery_details(match_date)"),
    # Composite for query-builder Stage-2 join (group_by batter+venue) — see handle_grouped_query in services/query_builder_v2.py
    ("idx_dd_bat_ground", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dd_bat_ground ON delivery_details(bat, ground)"),
]


def main():
    # psycopg2 needs the URL in a format it understands
    dsn = DATABASE_URL.replace("postgresql://", "postgres://", 1) if DATABASE_URL.startswith("postgresql://") else DATABASE_URL
    host_info = DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else "localhost"
    print(f"Connecting to: {host_info}")

    conn = psycopg2.connect(dsn)
    conn.set_session(autocommit=True)
    cur = conn.cursor()

    print(f"\nCreating {len(INDEXES)} indexes on delivery_details (CONCURRENTLY)...\n")

    for name, sql in INDEXES:
        print(f"  Creating {name}...", end=" ", flush=True)
        start = time.time()
        try:
            cur.execute(sql)
            elapsed = time.time() - start
            print(f"done ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - start
            print(f"FAILED ({elapsed:.1f}s): {e}")

    cur.close()
    conn.close()
    print("\nAll done.")


if __name__ == "__main__":
    main()
