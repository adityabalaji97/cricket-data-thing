"""Full-database SQLite cache builder with incremental refresh.

Dumps all required tables from a remote RDS (or any SQLAlchemy source)
into a local SQLite file so ML training can run entirely offline.

Usage:
    python ml/cache_manager.py build   --cache ml/all_cache.db
    python ml/cache_manager.py refresh --cache ml/all_cache.db
    python ml/cache_manager.py list-leagues --cache ml/all_cache.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Tables to cache with their indexes for fast lookups.
CACHE_TABLES = {
    "matches": {
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date)",
            "CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition)",
            "CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches(winner)",
            "CREATE INDEX IF NOT EXISTS idx_matches_venue ON matches(venue)",
        ],
    },
    "delivery_details": {
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_dd_match_id ON delivery_details(match_id)",
            "CREATE INDEX IF NOT EXISTS idx_dd_match_date ON delivery_details(match_date)",
            "CREATE INDEX IF NOT EXISTS idx_dd_ground ON delivery_details(ground)",
            "CREATE INDEX IF NOT EXISTS idx_dd_competition ON delivery_details(competition)",
        ],
    },
    "batting_stats": {
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_bs_match_id ON batting_stats(match_id)",
            "CREATE INDEX IF NOT EXISTS idx_bs_batting_team ON batting_stats(batting_team)",
        ],
    },
    "bowling_stats": {
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_bw_match_id ON bowling_stats(match_id)",
            "CREATE INDEX IF NOT EXISTS idx_bw_bowling_team ON bowling_stats(bowling_team)",
        ],
    },
    "team_phase_stats": {
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_tps_team ON team_phase_stats(team)",
        ],
    },
    "player_baselines": {
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_pb_player ON player_baselines(player_name)",
        ],
    },
}

# Small aggregate tables that are fully re-dumped on refresh.
AGGREGATE_TABLES = {"team_phase_stats", "player_baselines"}

BATCH_SIZE = 5000


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure JSON-serializable values for SQLite (convert dicts/lists to JSON strings)."""
    out = {}
    for k, v in row.items():
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v)
        else:
            out[k] = v
    return out


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cur.fetchone()[0] > 0


def _remote_table_exists(session: Session, table_name: str) -> bool:
    """Check if a table exists on the remote DB."""
    try:
        session.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
        return True
    except Exception:
        session.rollback()
        return False


def _dump_table(
    session: Session,
    conn: sqlite3.Connection,
    table_name: str,
    where_clause: str = "",
    params: Optional[Dict[str, Any]] = None,
) -> int:
    """Dump rows from remote session into local SQLite table. Returns row count."""
    sql = f"SELECT * FROM {table_name}"
    if where_clause:
        sql += f" {where_clause}"

    result = session.execute(text(sql), params or {})
    columns = list(result.keys())
    total = 0

    batch: List[Dict[str, Any]] = []
    for row in result:
        batch.append(_serialize_row(dict(zip(columns, row))))
        if len(batch) >= BATCH_SIZE:
            _insert_batch(conn, table_name, columns, batch)
            total += len(batch)
            batch = []

    if batch:
        _insert_batch(conn, table_name, columns, batch)
        total += len(batch)

    return total


def _insert_batch(
    conn: sqlite3.Connection,
    table_name: str,
    columns: List[str],
    batch: List[Dict[str, Any]],
) -> None:
    if not batch:
        return
    placeholders = ", ".join(["?"] * len(columns))
    col_names = ", ".join(f'"{c}"' for c in columns)
    sql = f'INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders})'
    rows = [tuple(row.get(c) for c in columns) for row in batch]
    conn.executemany(sql, rows)
    conn.commit()


_NUMERIC_COLUMNS = {
    "score", "noball", "wide", "byes", "legbyes", "over", "wagon_zone",
    "control", "runs", "balls_faced", "strike_rate", "fantasy_points",
    "batting_points", "bowling_points", "fielding_points", "sr_diff",
    "batting_position", "entry_overs", "overs", "runs_conceded", "wickets",
    "economy", "economy_diff", "avg_runs", "avg_wickets", "matches_played",
    "avg_strike_rate", "avg_balls_faced", "boundary_percentage",
    "dot_percentage", "avg_economy", "team1_elo", "team2_elo",
    "pp_runs", "middle_runs", "death_runs", "pp_wickets", "middle_wickets",
    "death_wickets", "ones", "twos", "threes", "fours", "sixes",
    "wpa_batter", "wpa_bowler",
}


def _create_table_from_remote(
    session: Session,
    conn: sqlite3.Connection,
    table_name: str,
) -> List[str]:
    """Create a SQLite table mirroring the remote schema. Returns column names.

    Numeric columns are declared as REAL for faster reads (avoids pd.to_numeric).
    """
    result = session.execute(text(f"SELECT * FROM {table_name} LIMIT 0"))
    columns = list(result.keys())

    col_defs = []
    for c in columns:
        col_type = "REAL" if c in _NUMERIC_COLUMNS else "TEXT"
        col_defs.append(f'"{c}" {col_type}')

    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    col_defs_str = ", ".join(col_defs)
    conn.execute(f"CREATE TABLE {table_name} ({col_defs_str})")
    conn.commit()
    return columns


def _create_metadata_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _cache_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    conn.commit()


def _set_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO _cache_metadata (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()


def _get_metadata(conn: sqlite3.Connection, key: str) -> Optional[str]:
    if not _table_exists(conn, "_cache_metadata"):
        return None
    cur = conn.execute("SELECT value FROM _cache_metadata WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_full_cache(remote_session: Session, cache_path: str) -> None:
    """Dump all tables from remote DB into a fresh SQLite cache file."""
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing file for clean build.
    if path.exists():
        path.unlink()

    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    _create_metadata_table(conn)

    start = time.time()
    for table_name, table_config in CACHE_TABLES.items():
        if not _remote_table_exists(remote_session, table_name):
            print(f"[cache] Skipping {table_name} (not found on remote)")
            continue

        print(f"[cache] Dumping {table_name}...")
        _create_table_from_remote(remote_session, conn, table_name)
        count = _dump_table(remote_session, conn, table_name)
        print(f"[cache] Dumped {count:,} {table_name} rows")

        for idx_sql in table_config["indexes"]:
            conn.execute(idx_sql)
        conn.commit()

    _set_metadata(conn, "last_refresh_timestamp", datetime.utcnow().isoformat())
    _set_metadata(conn, "built_at", datetime.utcnow().isoformat())

    elapsed = time.time() - start
    print(f"[cache] Full build complete in {elapsed:.1f}s -> {path}")
    conn.close()


def refresh_cache(remote_session: Session, cache_path: str) -> None:
    """Incrementally refresh cache with new matches since last refresh."""
    path = Path(cache_path)
    if not path.exists():
        print(f"[cache] No cache found at {path}. Run 'build' first.")
        return

    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    _create_metadata_table(conn)

    last_refresh = _get_metadata(conn, "last_refresh_timestamp")
    if not last_refresh:
        print("[cache] No last_refresh_timestamp found. Run 'build' first.")
        conn.close()
        return

    print(f"[cache] Last refresh: {last_refresh}")

    # Find new matches since last refresh.
    new_matches = remote_session.execute(
        text("SELECT id FROM matches WHERE date > :last_date ORDER BY date"),
        {"last_date": last_refresh[:10]},  # Use just the date part
    ).fetchall()

    new_match_ids = [str(r[0]) for r in new_matches]
    print(f"[cache] Found {len(new_match_ids)} new matches since {last_refresh[:10]}")

    if new_match_ids:
        # Insert new match rows.
        for i in range(0, len(new_match_ids), BATCH_SIZE):
            batch_ids = new_match_ids[i : i + BATCH_SIZE]
            placeholders = ", ".join(f":id{j}" for j in range(len(batch_ids)))
            params = {f"id{j}": mid for j, mid in enumerate(batch_ids)}

            for table_name in ["matches", "delivery_details", "batting_stats", "bowling_stats"]:
                if not _remote_table_exists(remote_session, table_name):
                    continue
                id_col = "id" if table_name == "matches" else "match_id"
                count = _dump_table(
                    remote_session,
                    conn,
                    table_name,
                    where_clause=f"WHERE {id_col} IN ({placeholders})",
                    params=params,
                )
                if count > 0:
                    print(f"[cache] Added {count:,} rows to {table_name}")

    # Re-dump aggregate tables entirely (they're small).
    for table_name in AGGREGATE_TABLES:
        if not _remote_table_exists(remote_session, table_name):
            continue
        print(f"[cache] Re-dumping {table_name}...")
        _create_table_from_remote(remote_session, conn, table_name)
        count = _dump_table(remote_session, conn, table_name)
        # Re-create indexes.
        for idx_sql in CACHE_TABLES[table_name]["indexes"]:
            conn.execute(idx_sql)
        conn.commit()
        print(f"[cache] Dumped {count:,} {table_name} rows")

    _set_metadata(conn, "last_refresh_timestamp", datetime.utcnow().isoformat())
    print("[cache] Refresh complete.")
    conn.close()


def list_leagues(cache_path: str) -> List[str]:
    """List all trainable leagues from the cache."""
    path = Path(cache_path)
    if not path.exists():
        print(f"[cache] No cache found at {path}")
        return []

    conn = sqlite3.connect(str(path))
    cur = conn.execute(
        """
        SELECT DISTINCT competition
        FROM matches
        WHERE winner IS NOT NULL
          AND competition IS NOT NULL
        ORDER BY competition
        """
    )
    leagues = [row[0] for row in cur.fetchall()]
    conn.close()
    return leagues


def get_last_refresh(cache_path: str) -> Optional[str]:
    """Get the last refresh timestamp from the cache, or None if not found."""
    path = Path(cache_path)
    if not path.exists():
        return None
    conn = sqlite3.connect(str(path))
    ts = _get_metadata(conn, "last_refresh_timestamp")
    conn.close()
    return ts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _get_remote_session() -> Session:
    from database import SessionLocal
    return SessionLocal()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage full-database SQLite cache for ML training.")
    parser.add_argument("command", choices=["build", "refresh", "list-leagues"], help="Command to run.")
    parser.add_argument("--cache", type=str, default="ml/all_cache.db", help="Path to SQLite cache file.")
    args = parser.parse_args()

    if args.command == "list-leagues":
        leagues = list_leagues(args.cache)
        print(f"\nTrainable leagues ({len(leagues)}):")
        for league in leagues:
            print(f"  - {league}")
        return

    session = _get_remote_session()
    try:
        if args.command == "build":
            build_full_cache(session, args.cache)
        elif args.command == "refresh":
            refresh_cache(session, args.cache)
    finally:
        session.close()


if __name__ == "__main__":
    main()
