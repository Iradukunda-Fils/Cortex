#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Cortex Platform PyPI Production Release ==="

# 1. Clean previous build artifacts
echo "[1/4] Cleaning legacy build artifacts..."
rm -rf build/ dist/ *.egg-info

# 2. Build distribution artifacts
echo "[2/4] Building wheel and source distributions..."
python3 -m build

# 3. Validate metadata via twine
echo "[3/4] Validating PyPI metadata with twine..."
python3 -m twine check dist/*

# 4. Upload to PyPI
echo "[4/4] Uploading to PyPI..."
python3 -m twine upload dist/*

echo "[+] Release complete! Install via: pip install cortex-runtime"
