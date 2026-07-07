#!/bin/bash
# Run the full test suite with coverage, logging output to a file.
# Usage: ./run_tests.sh [extra pytest args...]
#
# Output goes to test-results/latest.log (and stdout).
# Coverage report goes to test-results/coverage.xml.

set -euo pipefail

RESULTS_DIR="test-results"
mkdir -p "$RESULTS_DIR"

LOG_FILE="$RESULTS_DIR/latest.log"

echo "Running tests — log: $LOG_FILE"

uv run pytest \
    --tb=short \
    -v \
    -n auto \
    --cov=sparkmeter \
    --cov-report=xml:"$RESULTS_DIR/coverage.xml" \
    --cov-report=term-missing \
    "$@" \
    2>&1 | tee "$LOG_FILE"
