#!/usr/bin/env bash

set -euo pipefail

# Vercel ignores a build when this script exits 0.
# It proceeds with a build when this script exits 1.
#
# Strategy:
# - Build if any frontend-relevant files changed.
# - Skip if only backend/docs/data/scripts changed.

BASE_REF="${VERCEL_GIT_PREVIOUS_SHA:-HEAD^}"
HEAD_REF="${VERCEL_GIT_COMMIT_SHA:-HEAD}"

if ! git rev-parse --verify "${BASE_REF}" >/dev/null 2>&1; then
  echo "No previous commit available in clone; proceeding with build."
  exit 1
fi

changed_files="$(git diff --name-only "${BASE_REF}" "${HEAD_REF}" || true)"

if [[ -z "${changed_files}" ]]; then
  echo "No changed files detected; skipping build."
  exit 0
fi

frontend_paths='^(src/|public/|api/|package\.json$|package-lock\.json$|vercel\.json$|\.vercelignore$)'

if echo "${changed_files}" | grep -E -q "${frontend_paths}"; then
  echo "Frontend-relevant changes detected; proceeding with build."
  exit 1
fi

echo "No frontend-relevant changes detected; skipping build."
exit 0
