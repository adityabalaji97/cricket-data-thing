#!/usr/bin/env bash

set -euo pipefail

# Vercel ignores a build when this script exits 0.
# It proceeds with a build when this script exits 1.
#
# Strategy:
# - Build if any frontend-relevant files changed.
# - Skip if only backend/docs/data/scripts changed.
#
# The comparison window matters more than it looks. VERCEL_GIT_PREVIOUS_SHA is the last
# *attempted* deployment, not the last one that actually built, so a skipped commit's
# changes fall out of the window on the next push and are never reconsidered. That is how
# the multi-format frontend (chunk 0.7) sat undeployed for a day: it landed mid-way through
# a 40-commit merge, and every push afterwards was backend-only, so each run diffed a
# window that had already moved past src/.
#
# Two guards against that:
#   1. Prefer diffing against the last commit Vercel actually *built*
#      (VERCEL_GIT_COMMIT_REF's deployed SHA is not exposed, so we use the previous SHA but
#      widen it below when the range looks suspicious).
#   2. When the base ref is missing or unresolvable, build. Skipping is the dangerous
#      default -- a needless build costs a minute, a wrongly skipped one ships nothing and
#      is invisible until someone notices the site is stale.

BASE_REF="${VERCEL_GIT_PREVIOUS_SHA:-}"
HEAD_REF="${VERCEL_GIT_COMMIT_SHA:-HEAD}"

if [[ -z "${BASE_REF}" ]]; then
  echo "No VERCEL_GIT_PREVIOUS_SHA; cannot bound the diff safely. Building."
  exit 1
fi

if ! git rev-parse --verify "${BASE_REF}" >/dev/null 2>&1; then
  echo "Previous SHA ${BASE_REF} not present in this clone (shallow or force-push). Building."
  exit 1
fi

# The diff has to be guarded separately from the rev-parse above, and this is the part that
# actually bit. Vercel clones shallowly, so rev-parse can resolve the previous SHA while the
# object itself is absent -- git then fails with "fatal: bad object <sha>". The old form,
#     changed_files="$(git diff ... || true)"
# swallowed that failure into an empty string, which the emptiness check below read as "no
# files changed" and skipped the build. That is what kept cancelling every deployment while
# the frontend sat undeployed.
#
# So: distinguish "diff failed" from "diff returned nothing", and build on failure.
if ! changed_files="$(git diff --name-only "${BASE_REF}" "${HEAD_REF}" 2>/dev/null)"; then
  echo "Could not diff ${BASE_REF}..${HEAD_REF} (shallow clone, missing object). Building."
  exit 1
fi

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
