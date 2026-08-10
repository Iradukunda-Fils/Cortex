#!/usr/bin/env bash
set -euo pipefail

# Canonical Verification Pipeline Script for Cortex
# Ensures local environment passes all quality, lint, typing, and test gates.

echo "================================================================="
echo "               CORTEX CANONICAL VERIFICATION GATE                "
echo "================================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

echo "[1/5] Validating Lockfile Consistency (uv lock --check)..."
uv lock --check

echo "[2/5] Checking Contract Freeze Specifications..."
if [ -f "scripts/check_contract_freeze.sh" ]; then
    ./scripts/check_contract_freeze.sh
fi

echo "[3/5] Running Code Quality & Style Analysis (ruff check)..."
uv run ruff check .

echo "[4/5] Running Strict Static Type Checking (pyright)..."
uv run pyright

echo "[5/5] Executing Full Regression Test Suite (unittest)..."
uv run python -m unittest discover -s tests -v

echo "================================================================="
echo " [✓] ALL VERIFICATION GATES PASSED CLEANLY"
echo "================================================================="
