#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Cortex Platform PyPI Production Release (via Astral uv) ==="

# 1. Clean previous build artifacts
echo "[1/4] Cleaning legacy build artifacts..."
rm -rf build/ dist/ *.egg-info

# 2. Build distribution artifacts with uv
echo "[2/4] Building wheel and source distributions with uv build..."
uv build

# 3. Validate metadata via twine
echo "[3/4] Validating PyPI metadata with twine..."
python3 -m twine check dist/*

# 4. Publish to PyPI via uv publish
echo "[4/4] Publishing to PyPI via uv publish..."
uv publish

echo "[+] Release complete! Install via: pip install cortex-runtime"
