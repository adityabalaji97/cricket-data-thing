#!/usr/bin/env bash
# Start the API against the LOCAL development database.
#
# database.py calls load_dotenv() with the default override=False, so an exported
# DATABASE_URL takes precedence over the production URL in .env. That is why this
# script never touches .env -- it just exports the local URL first.
#
# Usage: scripts/dev/run_local_api.sh [extra uvicorn args]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export DATABASE_URL="${LOCAL_URL:-postgresql://localhost:5432/hindsight_local}"

# A local Postgres has no reason to run the tiny production pool.
export DB_POOL_SIZE="${DB_POOL_SIZE:-5}"
export DB_MAX_OVERFLOW="${DB_MAX_OVERFLOW:-5}"

# Guard against ever pointing this at production by accident.
if [[ "$DATABASE_URL" == *"amazonaws.com"* || "$DATABASE_URL" == *"heroku"* ]]; then
  echo "REFUSING TO START: DATABASE_URL looks like production ($DATABASE_URL)" >&2
  echo "This script is for local development only." >&2
  exit 1
fi

echo "==> API on http://localhost:8000  (db: $DATABASE_URL)"
exec uvicorn main:app --reload --host 127.0.0.1 --port 8000 "$@"
