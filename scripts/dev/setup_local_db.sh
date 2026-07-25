#!/usr/bin/env bash
# Build/refresh the local development database (hindsight_local) from a subset of production.
#
# Why a subset and not a full restore: prod is ~6.3 GB and this machine has limited free disk.
# We copy every small table in full, and slice the two huge ball-by-ball tables to the windows
# that actually exercise both code paths:
#   * 2024-01-01 onwards  -> delivery_details (the modern path, incl. IPL 2024/25/26, T20 WC 2024)
#   * 2013-01-01..2014-12-31 -> deliveries (the legacy pre-2015 path, needed to test table routing)
#
# Usage:
#   scripts/dev/setup_local_db.sh              # create + populate (drops existing hindsight_local)
#   scripts/dev/setup_local_db.sh --schema-only
#
# Requires PostgreSQL 16 client binaries (prod is PG16; pg_dump 14 refuses to talk to a PG16
# server). pgAdmin 4 ships them, so we use those by default -- no extra install needed.
# The local *server* can stay on PG14: we dump plain SQL, which restores across versions.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# --- Postgres 16 binaries -----------------------------------------------------
PG16_BIN="${PG16_BIN:-/Applications/pgAdmin 4.app/Contents/SharedSupport}"
if [[ ! -x "$PG16_BIN/pg_dump" ]]; then
  echo "ERROR: PG16 client binaries not found at $PG16_BIN" >&2
  echo "Point PG16_BIN at a directory containing pg_dump/psql v16, e.g. pgAdmin's" >&2
  echo "  /Applications/pgAdmin 4.app/Contents/SharedSupport" >&2
  echo "or install them: conda create -y -n pg16 -c conda-forge postgresql=16" >&2
  exit 1
fi
PSQL="$PG16_BIN/psql"
PG_DUMP="$PG16_BIN/pg_dump"

# Fail fast instead of hanging if the production connection stalls.
export PGCONNECT_TIMEOUT="${PGCONNECT_TIMEOUT:-20}"

# --- Connection strings -------------------------------------------------------
# Prod URL comes from .env (never modified by this script).
PROD_URL="$(grep -E '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)"
PROD_URL="${PROD_URL/postgres:\/\//postgresql://}"
if [[ -z "$PROD_URL" ]]; then
  echo "ERROR: DATABASE_URL not found in .env" >&2
  exit 1
fi
# Heroku RDS requires SSL.
[[ "$PROD_URL" == *"sslmode="* ]] || PROD_URL="${PROD_URL}?sslmode=require"

LOCAL_DB="${LOCAL_DB:-hindsight_local}"
LOCAL_URL="${LOCAL_URL:-postgresql://localhost:5432/$LOCAL_DB}"

# Match subset: modern window for delivery_details + legacy window for deliveries.
MODERN_FROM="${MODERN_FROM:-2024-01-01}"
LEGACY_FROM="${LEGACY_FROM:-2013-01-01}"
LEGACY_TO="${LEGACY_TO:-2015-01-01}"
MATCH_FILTER="date >= '$MODERN_FROM' OR (date >= '$LEGACY_FROM' AND date < '$LEGACY_TO')"

echo "==> Local target : $LOCAL_URL"
echo "==> Match subset : $MATCH_FILTER"
echo

# --- 1. Recreate the local database ------------------------------------------
echo "==> Dropping and recreating $LOCAL_DB"
"$PSQL" -q postgresql://localhost:5432/postgres \
  -c "DROP DATABASE IF EXISTS $LOCAL_DB;" \
  -c "CREATE DATABASE $LOCAL_DB;"

# --- 2. Schema ----------------------------------------------------------------
echo "==> Copying schema from production"
"$PG_DUMP" --schema-only --no-owner --no-privileges --no-tablespaces "$PROD_URL" \
  | "$PSQL" -q -v ON_ERROR_STOP=1 "$LOCAL_URL"

if [[ "${1:-}" == "--schema-only" ]]; then
  echo "==> Schema-only run complete."
  exit 0
fi

# --- 3. Data ------------------------------------------------------------------
# copy_full <table>            : stream an entire table
# copy_query <table> <select>  : stream the result of a SELECT into <table>
copy_full() {
  local table="$1"
  printf '    %-24s ' "$table"
  "$PSQL" -q "$PROD_URL" -c "\\copy (SELECT * FROM $table) TO STDOUT" \
    | "$PSQL" -q -v ON_ERROR_STOP=1 "$LOCAL_URL" -c "\\copy $table FROM STDIN"
  "$PSQL" -qtA "$LOCAL_URL" -c "SELECT count(*) FROM $table"
}

copy_query() {
  local table="$1" query="$2"
  printf '    %-24s ' "$table"
  "$PSQL" -q "$PROD_URL" -c "\\copy ($query) TO STDOUT" \
    | "$PSQL" -q -v ON_ERROR_STOP=1 "$LOCAL_URL" -c "\\copy $table FROM STDIN"
  "$PSQL" -qtA "$LOCAL_URL" -c "SELECT count(*) FROM $table"
}

echo "==> Copying reference tables (full)"
copy_full players
copy_full player_aliases
copy_full query_builder_metadata

echo "==> Copying matches (subset)"
copy_query matches "SELECT * FROM matches WHERE $MATCH_FILTER"

echo "==> Copying per-match stats (subset, FK-dependent on matches)"
copy_query batting_stats \
  "SELECT bs.* FROM batting_stats bs JOIN matches m ON m.id = bs.match_id WHERE m.$MATCH_FILTER"
copy_query bowling_stats \
  "SELECT bw.* FROM bowling_stats bw JOIN matches m ON m.id = bw.match_id WHERE m.$MATCH_FILTER"

echo "==> Copying ball-by-ball (the big ones)"
# Legacy table: only the pre-2015 window, to exercise the legacy code path.
copy_query deliveries \
  "SELECT d.* FROM deliveries d JOIN matches m ON m.id = d.match_id
   WHERE m.date >= '$LEGACY_FROM' AND m.date < '$LEGACY_TO'"
# Modern table: no FK to matches, so filter it directly on its own date column.
# NB: the `date` column is entirely NULL in production -- `match_date` (varchar, ISO
# 'YYYY-MM-DD') is the populated one, so compare lexicographically against that.
copy_query delivery_details \
  "SELECT * FROM delivery_details WHERE match_date >= '$MODERN_FROM'"

# --- 4. Fix sequences ---------------------------------------------------------
# COPY does not advance serial sequences; without this the first local INSERT
# collides with an existing id.
echo "==> Resetting sequences"
"$PSQL" -q -v ON_ERROR_STOP=1 "$LOCAL_URL" <<'SQL'
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT s.relname AS seq, t.relname AS tbl, a.attname AS col
    FROM pg_class s
    JOIN pg_depend d  ON d.objid = s.oid AND d.classid = 'pg_class'::regclass
    JOIN pg_class t   ON t.oid = d.refobjid
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
    WHERE s.relkind = 'S'
  LOOP
    EXECUTE format('SELECT setval(%L, COALESCE((SELECT MAX(%I) FROM %I), 1))',
                   r.seq, r.col, r.tbl);
  END LOOP;
END $$;
SQL

echo "==> ANALYZE"
"$PSQL" -q "$LOCAL_URL" -c "ANALYZE;"

echo
echo "==> Done. Summary:"
"$PSQL" "$LOCAL_URL" -c "
SELECT relname AS table, n_live_tup AS rows, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC;"
echo
echo "Local DB ready:  export DATABASE_URL=$LOCAL_URL"
