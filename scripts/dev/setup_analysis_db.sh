#!/usr/bin/env bash
# Build hindsight_analysis: a local, read-only-use copy of production holding the FULL men's T20
# ball-by-ball history from 2015 (delivery_details + ball_metrics) plus every match row and the
# name tables, for analysis/hypotheses. hindsight_local (2024 onward) stays untouched, so its
# goldens keep working.
#
# Reads production once, read-only (COPY ... TO STDOUT); never writes there.
#
# Usage:
#   scripts/dev/setup_analysis_db.sh
#   DATABASE_URL=postgresql://localhost:5432/hindsight_analysis python -m analysis.hypotheses.run_all
#
# Size: roughly 3-4 GB locally (men's T20 2015+ ball rows and their metrics).
# Needs PostgreSQL 16 client binaries, like scripts/dev/setup_local_db.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PG16_BIN="${PG16_BIN:-/Applications/pgAdmin 4.app/Contents/SharedSupport}"
PSQL="$PG16_BIN/psql"
PG_DUMP="$PG16_BIN/pg_dump"
[[ -x "$PG_DUMP" ]] || { echo "ERROR: PG16 client binaries not found at $PG16_BIN" >&2; exit 1; }
export PGCONNECT_TIMEOUT="${PGCONNECT_TIMEOUT:-20}"

PROD_URL="$(grep -E '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)"
PROD_URL="${PROD_URL/postgres:\/\//postgresql://}"
[[ -n "$PROD_URL" ]] || { echo "ERROR: DATABASE_URL not found in .env" >&2; exit 1; }
[[ "$PROD_URL" == *"sslmode="* ]] || PROD_URL="${PROD_URL}?sslmode=require"
# Every production statement runs in a read-only session.
export PGOPTIONS="-c default_transaction_read_only=on"

ANALYSIS_DB="${ANALYSIS_DB:-hindsight_analysis}"
LOCAL_URL="postgresql://localhost:5432/$ANALYSIS_DB"
[[ "$ANALYSIS_DB" != "hindsight_local" ]] || { echo "Refusing to overwrite hindsight_local" >&2; exit 1; }

echo "==> Recreating $ANALYSIS_DB"
PGOPTIONS= "$PSQL" -q postgresql://localhost:5432/postgres \
  -c "DROP DATABASE IF EXISTS $ANALYSIS_DB;" -c "CREATE DATABASE $ANALYSIS_DB;"

echo "==> Schema from production"
"$PG_DUMP" --schema-only --no-owner --no-privileges --no-tablespaces "$PROD_URL" \
  | PGOPTIONS= "$PSQL" -q -v ON_ERROR_STOP=1 "$LOCAL_URL"

copy_query() {
  local table="$1" query="$2"
  printf '    %-24s ' "$table"
  "$PSQL" -q "$PROD_URL" -c "\\copy ($query) TO STDOUT" \
    | PGOPTIONS= "$PSQL" -q -v ON_ERROR_STOP=1 "$LOCAL_URL" -c "\\copy $table FROM STDIN"
  PGOPTIONS= "$PSQL" -qtA "$LOCAL_URL" -c "SELECT count(*) FROM $table"
}

echo "==> Reference tables"
for t in players player_aliases query_builder_metadata matches metric_models match_par; do
  copy_query "$t" "SELECT * FROM $t"
done

echo "==> Men's T20 ball-by-ball from 2015 (the big one)"
copy_query delivery_details \
  "SELECT * FROM delivery_details WHERE format = 'T20' AND gender = 'male' AND match_date >= '2015-01-01'"
copy_query ball_metrics "SELECT * FROM ball_metrics"

echo "==> Materialised name views + ANALYZE"
PGOPTIONS= "$PSQL" -q -v ON_ERROR_STOP=1 "$LOCAL_URL" <<'SQL'
REFRESH MATERIALIZED VIEW player_alias_unambiguous;
REFRESH MATERIALIZED VIEW player_alias_map;
REFRESH MATERIALIZED VIEW player_name_spellings;
ANALYZE;
SQL

echo
echo "Ready: export DATABASE_URL=$LOCAL_URL"
echo "Then:  python -m analysis.hypotheses.run_all"
echo "       HINDSIGHT_FULL_DATA=1 pytest -s tests/test_validation_first_over.py"
