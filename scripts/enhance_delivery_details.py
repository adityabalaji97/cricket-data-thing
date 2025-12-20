"""
Enhance delivery_details table with additional columns from CSV
and left-right batter analysis columns.

Usage:
    DATABASE_URL="postgresql://..." python scripts/enhance_delivery_details.py
"""

import os
import sys
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text

# =============================================================================
# CONFIGURATION
# =============================================================================
CSV_FILE_PATH = "/Users/adityabalaji/Downloads/t20_bbb.csv"

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required")
    print('Usage: DATABASE_URL="postgresql://..." python scripts/enhance_delivery_details.py')
    sys.exit(1)

# =============================================================================
# COLUMN MAPPINGS
# =============================================================================
CSV_TO_DB_MAPPING = {
    "p_match": "match_id",
    "inns": "innings",
    "bat": "batter",
    "bowl": "bowler",
    "team_bat": "batting_team",
    "team_bowl": "bowling_team",
    "bat_hand": "bat_hand",
    "bowl_style": "bowl_style",
    "bowl_kind": "bowl_kind",
    "date": "date",
    "year": "year",
    "ground": "ground",
    "country": "country",
    "competition": "competition",
    "score": "score",
    "outcome": "outcome",
    "out": "out",
    "dismissal": "dismissal",
    "noball": "noball",
    "wide": "wide",
    "byes": "byes",
    "legbyes": "legbyes",
    "batruns": "batruns",
    "ballfaced": "ballfaced",
    "bowlruns": "bowlruns",
    "cur_bat_runs": "cur_bat_runs",
    "cur_bat_bf": "cur_bat_bf",
    "cur_bowl_ovr": "cur_bowl_ovr",
    "cur_bowl_wkts": "cur_bowl_wkts",
    "cur_bowl_runs": "cur_bowl_runs",
    "inns_runs": "inns_runs",
    "inns_wkts": "inns_wkts",
    "inns_balls": "inns_balls",
    "inns_runs_rem": "inns_runs_rem",
    "inns_balls_rem": "inns_balls_rem",
    "inns_rr": "inns_rr",
    "inns_rrr": "inns_rrr",
    "target": "target",
    "max_balls": "max_balls",
    "winner": "winner",
    "toss": "toss",
}

NULLABLE_COLUMNS = ["inns_runs_rem", "inns_rrr", "target", "dismissal", "outcome"]
MATCH_ID_COLUMN = "match_id"


def get_engine():
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return create_engine(url)


def check_table_schema(engine):
    global MATCH_ID_COLUMN
    
    print("=" * 60)
    print("STEP 0: Checking delivery_details table schema...")
    print("=" * 60)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'delivery_details'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        
        if not columns:
            print("  ERROR: delivery_details table does not exist!")
            return None
        
        print(f"  Found {len(columns)} columns")
        col_dict = {col_name: col_type for col_name, col_type in columns}
        
        if 'match_id' in col_dict:
            MATCH_ID_COLUMN = 'match_id'
        elif 'p_match' in col_dict:
            MATCH_ID_COLUMN = 'p_match'
        else:
            possible = [c for c in col_dict.keys() if 'match' in c.lower()]
            if possible:
                MATCH_ID_COLUMN = possible[0]
            else:
                print("  ERROR: Cannot find match identifier column!")
                return None
        
        print(f"  Match ID column: {MATCH_ID_COLUMN}")
        return col_dict


def run_migration(engine, existing_columns):
    print("\n" + "=" * 60)
    print("STEP 1: Running schema migration...")
    print("=" * 60)
    
    new_columns = [
        ("batter", "VARCHAR(100)"),
        ("bowler", "VARCHAR(100)"),
        ("non_striker", "VARCHAR(100)"),
        ("batting_team", "VARCHAR(100)"),
        ("bowling_team", "VARCHAR(100)"),
        ("bat_hand", "VARCHAR(10)"),
        ("bowl_style", "VARCHAR(20)"),
        ("bowl_kind", "VARCHAR(30)"),
        ("date", "DATE"),
        ("year", "INTEGER"),
        ("ground", "VARCHAR(200)"),
        ("country", "VARCHAR(100)"),
        ("competition", "VARCHAR(100)"),
        ("score", "INTEGER"),
        ("outcome", "VARCHAR(50)"),
        ("out", "BOOLEAN"),
        ("dismissal", "VARCHAR(50)"),
        ("noball", "INTEGER"),
        ("wide", "INTEGER"),
        ("byes", "INTEGER"),
        ("legbyes", "INTEGER"),
        ("batruns", "INTEGER"),
        ("ballfaced", "INTEGER"),
        ("bowlruns", "INTEGER"),
        ("cur_bat_runs", "INTEGER"),
        ("cur_bat_bf", "INTEGER"),
        ("cur_bowl_ovr", "FLOAT"),
        ("cur_bowl_wkts", "INTEGER"),
        ("cur_bowl_runs", "INTEGER"),
        ("inns_runs", "INTEGER"),
        ("inns_wkts", "INTEGER"),
        ("inns_balls", "INTEGER"),
        ("inns_runs_rem", "INTEGER"),
        ("inns_balls_rem", "INTEGER"),
        ("inns_rr", "FLOAT"),
        ("inns_rrr", "FLOAT"),
        ("target", "INTEGER"),
        ("max_balls", "INTEGER"),
        ("winner", "VARCHAR(100)"),
        ("toss", "VARCHAR(100)"),
        ("striker_batter_type", "VARCHAR(10)"),
        ("non_striker_batter_type", "VARCHAR(10)"),
        ("crease_combo", "VARCHAR(20)"),
    ]
    
    with engine.connect() as conn:
        added = 0
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                try:
                    conn.execute(text(f"ALTER TABLE delivery_details ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print(f"  Added: {col_name}")
                    added += 1
                except Exception as e:
                    conn.rollback()
        print(f"  Added {added} new columns.")


def load_and_prepare_csv(csv_path):
    print("\n" + "=" * 60)
    print("STEP 2: Loading CSV data...")
    print("=" * 60)
    
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df):,} rows")
    
    df = df.rename(columns=CSV_TO_DB_MAPPING)
    df["match_id"] = df["match_id"].astype(str)
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%y", errors="coerce")
    
    if "out" in df.columns:
        df["out"] = df["out"].apply(lambda x: str(x).upper() == "TRUE")
    
    for col in NULLABLE_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: None if pd.isna(x) or str(x).strip() == "" else x)
    
    return df


def check_data_overlap(engine, df):
    print("\n" + "=" * 60)
    print("STEP 2B: Checking data overlap...")
    print("=" * 60)
    
    match_col = MATCH_ID_COLUMN
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM delivery_details"))
        total_db = result.scalar()
        print(f"  Records in delivery_details: {total_db:,}")
        
        if total_db == 0:
            print("  WARNING: Table is empty!")
            return False
        
        # Sample from DB
        result = conn.execute(text(f"SELECT DISTINCT {match_col} FROM delivery_details LIMIT 5"))
        db_samples = [str(row[0]) for row in result.fetchall()]
        print(f"  Sample DB match IDs: {db_samples}")
        
        # Sample from CSV
        csv_samples = df["match_id"].unique()[:5].tolist()
        print(f"  Sample CSV match IDs: {csv_samples}")
        
        # Check overlap
        csv_matches = set(df["match_id"].unique())
        result = conn.execute(text(f"SELECT DISTINCT {match_col} FROM delivery_details"))
        db_matches = {str(row[0]) for row in result.fetchall()}
        
        overlap = csv_matches & db_matches
        print(f"  CSV unique matches: {len(csv_matches):,}")
        print(f"  DB unique matches: {len(db_matches):,}")
        print(f"  Overlapping: {len(overlap):,}")
        
        return len(overlap) > 0


def update_from_csv_bulk(engine, df):
    print("\n" + "=" * 60)
    print("STEP 3: Bulk updating from CSV...")
    print("=" * 60)
    
    match_col = MATCH_ID_COLUMN
    
    update_columns = [
        "batter", "bowler", "batting_team", "bowling_team",
        "bat_hand", "bowl_style", "bowl_kind", "year",
        "ground", "country", "competition", "score", "outcome",
        "out", "dismissal", "noball", "wide", "byes", "legbyes",
        "batruns", "ballfaced", "bowlruns", "cur_bat_runs", "cur_bat_bf",
        "cur_bowl_ovr", "cur_bowl_wkts", "cur_bowl_runs", "inns_runs",
        "inns_wkts", "inns_balls", "inns_runs_rem", "inns_balls_rem",
        "inns_rr", "inns_rrr", "target", "max_balls", "winner", "toss"
    ]
    update_columns = [c for c in update_columns if c in df.columns]
    
    key_cols = ["match_id", "innings", "over", "ball"]
    upload_df = df[key_cols + update_columns].copy()
    
    # Convert date to string for temp table
    if "date" in upload_df.columns:
        upload_df = upload_df.drop(columns=["date"])
        update_columns = [c for c in update_columns if c != "date"]
    
    with engine.connect() as conn:
        print("  Creating temp table...")
        conn.execute(text("DROP TABLE IF EXISTS temp_csv_data"))
        conn.commit()
        
        # Upload to temp table
        print(f"  Uploading {len(upload_df):,} rows...")
        upload_df.to_sql("temp_csv_data", conn, if_exists="replace", index=False, method="multi", chunksize=10000)
        
        # Build bulk update
        set_clause = ", ".join([f"{col} = t.{col}" for col in update_columns])
        
        update_sql = f"""
            UPDATE delivery_details dd
            SET {set_clause}
            FROM temp_csv_data t
            WHERE dd.{match_col}::text = t.match_id::text
              AND dd.innings = t.innings
              AND dd.over = t.over
              AND dd.ball = t.ball
        """
        
        print("  Running bulk UPDATE...")
        result = conn.execute(text(update_sql))
        updated = result.rowcount
        conn.commit()
        
        conn.execute(text("DROP TABLE IF EXISTS temp_csv_data"))
        conn.commit()
    
    print(f"  Updated {updated:,} rows")
    return updated


def populate_non_striker_from_deliveries(engine):
    print("\n" + "=" * 60)
    print("STEP 4A: Populating non_striker from deliveries...")
    print("=" * 60)
    
    match_col = MATCH_ID_COLUMN
    
    sql = f"""
        UPDATE delivery_details dd
        SET non_striker = d.non_striker
        FROM deliveries d
        WHERE dd.{match_col}::text = d.match_id::text
          AND dd.innings = d.innings
          AND dd.over = d.over
          AND dd.ball = d.ball
          AND dd.non_striker IS NULL
          AND d.non_striker IS NOT NULL
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        conn.commit()
        print(f"  Updated {result.rowcount:,} rows")
    return result.rowcount


def infer_non_striker_from_sequence(engine):
    print("\n" + "=" * 60)
    print("STEP 4B: Inferring non_striker from sequence...")
    print("=" * 60)
    
    match_col = MATCH_ID_COLUMN
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM delivery_details WHERE non_striker IS NULL"))
        missing = result.scalar()
        print(f"  Missing non_striker: {missing:,}")
        
        if missing == 0:
            return 0
        
        sql = f"""
            WITH ordered_balls AS (
                SELECT id, {match_col}, innings, over, ball, batter, score, non_striker,
                    LAG(batter) OVER (PARTITION BY {match_col}, innings ORDER BY over, ball) as prev_batter,
                    LEAD(batter) OVER (PARTITION BY {match_col}, innings ORDER BY over, ball) as next_batter
                FROM delivery_details
            ),
            inferred AS (
                SELECT id,
                    CASE
                        WHEN batter != prev_batter AND prev_batter IS NOT NULL THEN prev_batter
                        WHEN batter != next_batter AND next_batter IS NOT NULL THEN next_batter
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
        print(f"  Still missing: {result.scalar():,}")
    
    return result.rowcount


def populate_batter_types(engine):
    print("\n" + "=" * 60)
    print("STEP 5: Populating batter types...")
    print("=" * 60)
    
    with engine.connect() as conn:
        result1 = conn.execute(text("""
            UPDATE delivery_details dd
            SET striker_batter_type = p.batting_hand
            FROM players p
            WHERE dd.batter = p.name AND dd.striker_batter_type IS NULL AND p.batting_hand IS NOT NULL
        """))
        print(f"  Striker types: {result1.rowcount:,}")
        
        result2 = conn.execute(text("""
            UPDATE delivery_details dd
            SET non_striker_batter_type = p.batting_hand
            FROM players p
            WHERE dd.non_striker = p.name AND dd.non_striker_batter_type IS NULL AND p.batting_hand IS NOT NULL
        """))
        print(f"  Non-striker types: {result2.rowcount:,}")
        conn.commit()


def generate_crease_combo(engine):
    print("\n" + "=" * 60)
    print("STEP 6: Generating crease_combo...")
    print("=" * 60)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE delivery_details
            SET crease_combo = striker_batter_type || '_' || non_striker_batter_type
            WHERE striker_batter_type IS NOT NULL
              AND non_striker_batter_type IS NOT NULL
              AND crease_combo IS NULL
        """))
        conn.commit()
        print(f"  Generated {result.rowcount:,} rows")


def print_summary(engine):
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
    print("=" * 60)
    print("DELIVERY DETAILS ENHANCEMENT SCRIPT")
    print("=" * 60)
    
    if not os.path.exists(CSV_FILE_PATH):
        print(f"ERROR: CSV not found: {CSV_FILE_PATH}")
        sys.exit(1)
    
    engine = get_engine()
    
    existing_columns = check_table_schema(engine)
    if existing_columns is None:
        sys.exit(1)
    
    run_migration(engine, existing_columns)
    
    df = load_and_prepare_csv(CSV_FILE_PATH)
    
    if not check_data_overlap(engine, df):
        print("\nNo overlapping data found. Exiting.")
        sys.exit(1)
    
    update_from_csv_bulk(engine, df)
    
    populate_non_striker_from_deliveries(engine)
    infer_non_striker_from_sequence(engine)
    populate_batter_types(engine)
    generate_crease_combo(engine)
    
    print_summary(engine)
    print("\nDONE!")


if __name__ == "__main__":
    main()
