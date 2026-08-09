# PyPI Production Release Guide for `cortex-runtime`

This guide explains how to publish **`cortex-runtime` v0.2.0** to PyPI using either **Automated GitHub OIDC** or **Manual Local Deployment**.

---

## 🚀 Method A: Automated Release via GitHub Actions (Recommended)

The repository includes a GitHub Actions workflow (`.github/workflows/pypi.yml`) configured for **PyPI Trusted Publishing (OIDC)**. No hardcoded API tokens or secret keys are needed.

### Steps:
1. Ensure all changes are committed and merged into `main`.
2. Create and push a version tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
3. GitHub Actions will automatically:
   - Run the test suite (`unittest`, `ruff`, `pyright`).
   - Build clean `.tar.gz` and `.whl` artifacts.
   - Publish `cortex-runtime` to PyPI via OIDC.

---

## 🛠️ Method B: Manual Local Deployment via Twine

If publishing directly from your terminal:

### Steps:
1. Install build tools:
   ```bash
   pip install build twine
   ```

2. Run the automated release script:
   ```bash
   ./scripts/publish_to_pypi.sh
   ```

3. When prompted by `twine upload`:
   - **Username**: `__token__`
   - **Password**: Enter your PyPI API token (`pypi-AgEI...`).

---

## 🧪 Post-Release Installation Verification

Once published, verify availability on PyPI:

```bash
# Install in a fresh environment
pip install cortex-runtime

# Test CLI
cortex --help
cortex init my_app

# Test Python API
python3 -c "import cortex; print(cortex.__all__)"
```
