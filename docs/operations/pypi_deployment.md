# PyPI Production Release Guide for `cortex-runtime` (via Astral `uv`)

This guide explains how to publish **`cortex-runtime` v0.2.0** to PyPI using **Astral `uv`**, providing high-speed package building (`uv build`) and tokenless/OIDC publishing (`uv publish`).

---

## 🚀 Method A: Automated Release via GitHub Actions (Recommended)

The repository includes a GitHub Actions workflow (`.github/workflows/pypi.yml`) powered by `astral-sh/setup-uv@v3` and **PyPI Trusted Publishing (OIDC)**.

### Steps:
1. Ensure all changes are committed and merged into `main`.
2. Create and push a version tag:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
3. GitHub Actions will automatically:
   - Run quality gates (`ruff`, `pyright`, `unittest`).
   - Execute `uv build` to construct `.tar.gz` and `.whl` artifacts in milliseconds.
   - Execute `uv publish` to release `cortex-runtime` to PyPI via OIDC.

---

## 🛠️ Method B: Manual Local Deployment via `uv`

If publishing directly from your local terminal using `uv`:

### Steps:
1. Ensure `uv` is installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Run the automated publish script:
   ```bash
   ./scripts/publish_to_pypi.sh
   ```
   Or execute directly:
   ```bash
   uv build
   uv publish
   ```

3. When prompted by `uv publish`:
   - Set token environment variable `UV_PUBLISH_TOKEN=pypi-AgEI...` or enter your API token interactively.

---

## 🧪 Post-Release Installation Verification

Once published, verify availability on PyPI:

```bash
# Install in a fresh environment via uv
uv venv --clear .venv-verify
uv pip install --python .venv-verify/bin/python cortex-runtime

# Test CLI
.venv-verify/bin/cortex --help
.venv-verify/bin/cortex init my_app

# Clean up
rm -rf .venv-verify
```
