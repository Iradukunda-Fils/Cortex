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

echo "[1/7] Validating Lockfile Consistency (uv lock --check)..."
uv lock --check

echo "[2/7] Checking Contract Freeze Specifications..."
if [ -f "scripts/check_contract_freeze.sh" ]; then
    ./scripts/check_contract_freeze.sh
fi

echo "[3/7] Running Code Quality & Style Analysis (ruff check)..."
uv run ruff check .

echo "[4/7] Running Strict Static Type Checking (pyright)..."
uv run pyright

echo "[5/7] Executing Full Regression Test Suite (unittest)..."
uv run python -m unittest discover -s tests -v


echo "[6/7] Running Repository Documentation Coherence Audit (docs_audit.py)..."
uv run python3 tools/assurance/docs_audit.py

echo "[7/7] Verifying Coq Print Assumptions Audit Artifact Consistency..."
uv run python3 scripts/verify_coq_assumptions.py

echo "================================================================="
echo " [✓] ALL VERIFICATION GATES PASSED CLEANLY"
echo "================================================================="
