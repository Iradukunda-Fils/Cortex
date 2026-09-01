## 📌 Pull Request Overview

### 1. Summary of Changes
<!-- Provide a clear, concise 2-3 sentence summary of what this PR introduces or fixes. -->

### 2. Change Classification
<!-- Please check all that apply: -->
- [ ] 🚀 **Feature**: New capability, API symbol, or runtime enhancement
- [ ] 🐛 **Bug Fix**: Fixes a defect, crash, or unexpected behavior
- [ ] 🛡️ **Security / Isolation**: Security boundary, sandbox, or permission change
- [ ] 📜 **Formal Proof**: Coq formalization, theorem, or proof maintenance (`.v` file)
- [ ] 📚 **Documentation**: Updates to specs, release notes, or guides
- [ ] 🧹 **Refactoring / Maintenance**: Non-functional code cleanup or CI pipeline fix

---

## 🔗 Related Issue & Scope

- **Fixes Issue**: #<!-- Insert issue number, e.g. #23 -->
- **Assurance Domain**:
  - [ ] `Python Runtime / Kernel`
  - [ ] `Coq Formal Verification`
  - [ ] `WASM / Sandbox Subsystem`
  - [ ] `Documentation & Governance`

---

## 🧪 Verification & Evidence Checklist

<!-- Every PR must satisfy the 7-gate canonical verification pipeline before merging. -->

- [ ] Executed local canonical verification gate: `./scripts/verify.sh`
- [ ] All 566+ unit and conformance tests pass cleanly
- [ ] Strict type checking (`pyright`) passes with 0 errors
- [ ] Code formatting & linting (`ruff check .`) passes cleanly
- [ ] Documentation audit (`tools/assurance/docs_audit.py`) passes cleanly
- [ ] Lockfile (`uv.lock`) is up to date (`uv lock --check`)

---

## ⚠️ Architectural & Invariant Safety Check

- [ ] Does this PR modify any public SDK API symbol in `cortex/__init__.py`?
- [ ] Does this PR alter system invariants ($P1$–$P4$) or security ceilings?
- [ ] If changing proof files (`.v`), have you run `coqchk` to verify 0 Axioms / 0 Admits?

---

## 📝 Contributor Sign-Off

By submitting this pull request, I confirm that my contribution is made under the terms of the Apache 2.0 License.
