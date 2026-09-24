#!/usr/bin/env bash
# Flag light-theme colour literals in lines ADDED to src/ relative to a base ref.
#
# The app is dark throughout (src/theme/hindsightTheme.js). Hard-coded light colours bypass the
# theme and reappear as white islands -- the reason the preview header card was invisible and
# match-history opponents were unreadable. Existing literals are cleaned up page by page; this
# stops new ones landing. It checks only added lines, so it never fails on old code.
#
# Usage: scripts/check_theme_literals.sh [base-ref]   (default: origin/main)
# Exit 1 if any added line matches. Silence a deliberate one with `// theme-literal-ok` on it.

set -euo pipefail
BASE="${1:-origin/main}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Light colours used as BACKGROUNDS, and near-black used as TEXT. (Light hex values are fine as
# text on a dark page, so they are only flagged in background properties.) src/theme/ holds the
# palettes themselves and is excluded.
BG_PATTERN="(background(-color|Color|Image)?|bgcolor)[\"']? *: *[\"'\`]?[^,;}]*(#fff(fff)?\b|\bwhite\b|#f[0-9a-f]{5}\b|grey\.(50|100|200)\b|rgba\(255, ?255, ?255, ?(0?\.[89]|1)[0-9]*\))"
TEXT_PATTERN="(^|[^-a-z])color *: *[\"']?(#000(000)?|black|#0f172a|#1[0-9a-f]{5}|#2[0-9a-f]{5}|#333|#444|#555|#666)\b"

hits=$(git diff --unified=0 "$BASE" -- 'src/*.js' 'src/*.jsx' 'src/*.css' ':!src/theme/*' \
  | grep -E '^\+[^+]' \
  | grep -Eiv 'theme-literal-ok' \
  | grep -Ei "$BG_PATTERN|$TEXT_PATTERN" || true)

if [[ -n "$hits" ]]; then
  echo "Light-theme colour literals added (use theme palette tokens or src/theme/hindsightDark.js):"
  echo "$hits"
  exit 1
fi
echo "No new light-theme colour literals."
