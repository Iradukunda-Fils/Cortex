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

echo "[1/6] Validating Lockfile Consistency (uv lock --check)..."
uv lock --check

echo "[2/6] Checking Contract Freeze Specifications..."
if [ -f "scripts/check_contract_freeze.sh" ]; then
    ./scripts/check_contract_freeze.sh
fi

echo "[3/6] Running Code Quality & Style Analysis (ruff check)..."
uv run ruff check .

echo "[4/6] Running Strict Static Type Checking (pyright)..."
uv run pyright

echo "[5/6] Executing Full Regression Test Suite (unittest)..."
uv run python -m unittest discover -s tests -v

echo "[6/6] Running Repository Documentation Coherence Audit (docs_audit.py)..."
uv run python3 tools/assurance/docs_audit.py

echo "================================================================="
echo " [✓] ALL VERIFICATION GATES PASSED CLEANLY"
echo "================================================================="
