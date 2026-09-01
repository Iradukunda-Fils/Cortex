# Cortex Developer Pull Request & Merge Governance Guide

Welcome to the **Cortex Platform** Pull Request (PR) and Merge Governance Guide.

This guide outlines our enterprise-grade branching standards, Conventional Commits format, PR checklist, and automated merge gates to ensure seamless collaboration for open-source contributors and core maintainers.

---

## 🌲 1. Branching Strategy & Naming Conventions

All development occurs on short-lived topic branches branched off `main`:

| Category | Branch Naming Convention | Example |
| :--- | :--- | :--- |
| **New Features** | `feat/<short-description>` | `feat/wasm-profile-b-sandbox` |
| **Bug Fixes** | `fix/<short-description>` | `fix/wal-sequence-gap` |
| **Formal Proofs** | `proof/<theorem-name>` | `proof/wal-prefix-refinement` |
| **Documentation** | `docs/<section-name>` | `docs/security-review-dossier` |
| **Performance** | `perf/<benchmark-target>` | `perf/cbe-zero-copy-codec` |

---

## 💬 2. Conventional Commit & PR Title Standard

PR titles and commit messages must follow the **Conventional Commits** specification (`<type>: <description>`):

- `feat:` New capability, feature, or public API symbol.
- `fix:` Bug fix or defect resolution.
- `proof:` Coq formalization, theorem, or proof maintenance.
- `docs:` Documentation improvements or spec updates.
- `test:` Unit, integration, or conformance test additions.
- `refactor:` Code refactoring with zero functional/behavioral change.
- `chore:` CI, build script, or dependency update.

**Examples**:
- `feat(sandbox): add Profile_B_WASM_Strict ceiling enforcement`
- `fix(wal): prevent race condition during crash log replay`
- `proof(refinement): complete Phase 8.0 forward simulation theorem`

---

## ⚙️ 3. Automated PR Merge Gates

Every Pull Request must pass **4 Mandatory CI Automated Gates** before it can be merged into `main`:

$$\boxed{ \text{Lockfile Check} \land \text{Ruff Check} \land \text{Pyright Type Check} \land \text{566 Tests Pass} \land \text{Docs Audit} }$$

1. **Lockfile Consistency (`uv lock --check`)**: `uv.lock` must match `pyproject.toml`.
2. **Code Quality & Style (`ruff check .`)**: 0 lint or code style violations.
3. **Strict Type Checking (`pyright`)**: 0 static type errors.
4. **Full Test Suite (`unittest`)**: 100% test parity (566+ unit & conformance tests pass).
5. **Documentation Coherence (`tools/assurance/docs_audit.py`)**: 0 broken path or symbol references.
6. **Coq Assumptions Audit (`scripts/verify_coq_assumptions.py`)**: 0 unverified proof drifts.

---

## 🔀 4. Merge Strategy

- **Squash and Merge**: Preferred for all feature, fix, and documentation PRs to maintain a clean linear `main` history.
- **Rebase and Merge**: Permitted for large multi-commit formal proof milestones (`proof/*`).
- **Direct Pushes to `main`**: Strictly prohibited via GitHub branch protection rules.
