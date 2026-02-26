#!/bin/bash
set -e
echo "Running sanity tests..."
cd "$(dirname "$0")/.."
python -m pytest tests/ -v --tb=short
echo "Sanity tests passed!"
