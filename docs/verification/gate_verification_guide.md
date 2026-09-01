# Cortex Gate Verification Guide

**Status**: FROZEN  
**Version**: Revision #5  
**Script**: `./scripts/verify.sh`  
**Machine Spec**: `docs/gate-specs/v03_architecture_gate_spec.json`

---

## 1. Overview

The Cortex Gate Verification Substrate enforces a zero-trust, continuous validation pipeline across code quality, lockfile integrity, contract specs, static typing, unit tests, and documentation snippets.

Executing `./scripts/verify.sh` runs all five canonical gates sequentially:

```bash
./scripts/verify.sh
```

---

## 2. The 5 Verification Gates

### Gate 1: Lockfile Consistency Check (`uv lock --check`)
- **Objective**: Guarantees that `pyproject.toml` and `uv.lock` are in exact 100% synchronization.
- **Remediation**: Run `uv lock` if dependencies change.

### Gate 2: Contract Freeze Specifications (`./scripts/check_contract_freeze.sh`)
- **Objective**: Ensures protected contract specifications are not mutated without explicit authorized commit tags (`breaking-contract-change`).
- **Target Paths**: `docs/adrs/ADR-003-polyglot-kernel.md`, `docs/gate-specs/v03_architecture_gate_spec.json`.

### Gate 3: Code Quality & Style Analysis (`uv run ruff check .`)
- **Objective**: Enforces PEP8, formatting, import sorting, and code style standards across Python files.

### Gate 4: Strict Static Type Checking (`uv run pyright`)
- **Objective**: Guarantees zero type errors (`0 errors`) under strict Pyright type checking mode.
- **Rule**: Prohibits untyped `Any` usage and missing type annotations across the public SDK and internal modules.

### Gate 5: Canonical Regression Test Suite (`uv run python -m unittest discover -s tests -v`)
- **Objective**: Executes all 172 regression tests, including:
  - `test_v020_public_api_surface.py`: Public SDK surface freeze (len 21).
  - `test_v020_docs_snippets.py`: Executability of markdown code blocks in `docs/` with zero internal module imports.
  - Security audit, workflow lifecycle, and telemetry suites.

---

## 3. Pre-Commit Zero-Diff Check

To verify repository isolation before committing:

```bash
git diff -- pyproject.toml uv.lock cortex/ tests/
```

Output MUST be empty (0 modified lines).
