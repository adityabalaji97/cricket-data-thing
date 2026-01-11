#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_delivery_details_refresh.sh --dropbox-url <shared_url> [--csv-path data/t20_bbb.csv] [--skip-elo] [--dry-run]

Description:
  Downloads the delivery details CSV from Dropbox (shared URL converted to ?dl=1),
  stores it at the provided CSV path, then runs the delivery details pipeline.

Requirements:
  - DATABASE_URL must be set in the environment.

Examples:
  DATABASE_URL="postgresql://..." scripts/run_delivery_details_refresh.sh \
    --dropbox-url "https://www.dropbox.com/s/<id>/t20_bbb.csv?dl=0"

  DATABASE_URL="postgresql://..." scripts/run_delivery_details_refresh.sh \
    --dropbox-url "https://www.dropbox.com/s/<id>/t20_bbb.csv" \
    --csv-path data/t20_bbb.csv --skip-elo --dry-run
USAGE
}

dropbox_url=""
csv_path="data/t20_bbb.csv"
skip_elo="false"
dry_run="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dropbox-url)
      dropbox_url="${2:-}"
      shift 2
      ;;
    --csv-path)
      csv_path="${2:-}"
      shift 2
      ;;
    --skip-elo)
      skip_elo="true"
      shift
      ;;
    --dry-run)
      dry_run="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${dropbox_url}" ]]; then
  echo "ERROR: --dropbox-url is required."
  usage
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL must be set in the environment."
  exit 1
fi

if [[ "${dropbox_url}" != *"dropbox.com"* ]]; then
  echo "ERROR: Provided URL does not look like a Dropbox shared URL."
  exit 1
fi

direct_url="${dropbox_url}"
if [[ "${direct_url}" == *"?dl="* ]]; then
  direct_url="$(echo "${direct_url}" | sed -E 's/[?&]dl=[01]/?dl=1/')"
else
  direct_url="${direct_url}?dl=1"
fi

mkdir -p "$(dirname "${csv_path}")"

echo "Downloading delivery details CSV..."
echo "  Source: ${direct_url}"
echo "  Target: ${csv_path}"

if ! curl -fL --retry 3 --retry-delay 2 -o "${csv_path}" "${direct_url}"; then
  echo "ERROR: Download failed."
  exit 1
fi

echo "Download complete."
echo "Running delivery details pipeline..."

pipeline_args=(--csv "${csv_path}")
if [[ "${skip_elo}" == "true" ]]; then
  pipeline_args+=(--skip-elo)
fi
if [[ "${dry_run}" == "true" ]]; then
  pipeline_args+=(--dry-run)
fi

python scripts/load_delivery_details_pipeline.py "${pipeline_args[@]}"
