# Cortex Commit Quality & Repository Hygiene Policy

- **Document ID**: `CORTEX-POLICY-COMMIT-2026`
- **Status**: **NORMATIVE ENFORCED**

---

## 1. Commit Structure & Messages

1. **Imperative Subject Lines**: Commit messages must use the imperative mood (e.g., `feat(f4c): implement verifier totality and determinism tests`).
2. **Component Prefix Scope**: Use standardized scope prefixes:
   - `feat(f4c)`: Evidence domain and verifier equivalence work.
   - `cert(gate-g)` / `cert(gate-h)`: Conformance gate updates.
   - `proof(coq)`: Coq formal proof verification updates.
   - `rel(engine)`: Release readiness engine and tooling updates.
3. **No Uncertified Mainline Commits**: No commit shall be merged into `main` unless `python3 tools/release/readiness.py` yields `CONTROLLED_EXPERIMENTAL` or higher.

---

## 2. Git & Schema Invariants

1. **Canonical Manifest Symlink**: `docs/architecture/cortex_assurance_manifest.json` MUST be tracked as a relative symbolic link (`Git mode 120000`) pointing to `../../cortex_assurance_manifest.json`.
2. **Schema Uniformity**: All `$schema` references MUST resolve locally and deterministically (`./docs/architecture/...` or `./...`).
