# Cortex Standardized Merge & Squash Commit Templates

To maintain a clean, readable, and machine-parsable linear commit log on `main`, all Pull Requests merged into `main` must use the standardized merge formats below.

---

## 1. Standard Squash & Merge Commit Template

When merging a PR using **Squash and Merge** in GitHub:

### Commit Title Format
```text
<type>(<scope>): <short summary in imperative present tense> (#<PR-NUMBER>)
```

### Commit Body Template
```text
<type>(<scope>): <short summary> (#<PR-NUMBER>)

### Summary of Changes
- <Deliverable 1>
- <Deliverable 2>
- <Deliverable 3>

### Governance & Verification Evidence
- [x] Canonical verification pipeline passed (./scripts/verify.sh)
- [x] All 566+ unit and conformance tests pass
- [x] Coq print assumptions audit cleanly verified (0 Axioms)
- [x] Documentation audit passed (tools/assurance/docs_audit.py)

### Linked Issues & Gates
- Closes #<ISSUE-NUMBER>
- Governing Release Gate: Issue #23 / Issue #37
```

---

## 2. Examples by Change Type

### A. Feature Merge
```text
feat(sandbox): implement Profile_B_WASM_Strict security ceiling (#59)

### Summary of Changes
- Integrated WASM Profile B schema into ConfigResolver
- Added security ceiling normalization logic for WASM sandbox profiles
- Added conformance test suite for declared vs runtime sandbox boundary

### Governance & Verification Evidence
- [x] Canonical verification pipeline passed (./scripts/verify.sh)
- [x] All 566+ unit and conformance tests pass

### Linked Issues & Gates
- Closes #33
```

### B. Formal Proof Merge
```text
proof(refinement): complete Phase 8.0 forward simulation refinement theorem (#56)

### Summary of Changes
- Formalized universal forward simulation relation R(C, A) in Coq
- Machine-checked WAL prefix refinement theorem with zero admits
- Verified coqchk clean status across all Phase 8 proofs

### Governance & Verification Evidence
- [x] Coq print assumptions audit cleanly verified (0 Axioms, 0 Admits)
- [x] Canonical verification pipeline passed (./scripts/verify.sh)

### Linked Issues & Gates
- Closes #56
```

### C. Release Train Merge
```text
release(v1.0.0-rc1): lock release candidate baseline and governance dossier (#59)

### Summary of Changes
- Tagged v0.5.0, v0.6.0, and v1.0.0-RC1 release records under docs/release/
- Updated pyproject.toml package version to 1.0.0rc1 (PEP 440)
- Reorganized docs/ into 6 dedicated separation-of-concern portals

### Governance & Verification Evidence
- [x] Canonical verification pipeline passed (./scripts/verify.sh)

### Linked Issues & Gates
- Governed by Issue #23
```
