# Cortex Code Quality & Software Engineering Policy

- **Document ID**: `CORTEX-POLICY-CQ-2026`
- **Status**: **NORMATIVE ENFORCED**
- **Target**: All polyglot codebase components (Python, Rust, Go, SystemVerilog, Coq)

---

## 1. Zero-Trust Substrate Rules

1. **No Ad-Hoc Dependencies**: High-assurance verifiers (e.g., `tools/cortex_verifier.py`) MUST be zero-dependency, relying exclusively on stdlib primitives.
2. **$O(1)$ Memory Scaling**: All Layer 2 streaming codecs and verifier loop structures MUST execute within constant stack and heap bounds under adversarial input.
3. **Fail-Closed Execution**: Any unexpected parser state, type mismatch, or payload mutation MUST immediately terminate execution and emit an explicit diagnostic trap code (`TRAP_...`).
4. **Deterministic CBE Serialization**: Key-value structures MUST use lexicographically sorted key pairs and explicit type byte markers.

---

## 2. Polyglot Language Constraints

- **Python**: Enforce Python 3.10+ native typing annotations. Zero `Any` types without explicit suppression comments. Linting via `ruff check` and type-checking via `pyright`.
- **Rust**: Enforce `#![deny(unsafe_code)]` in non-substrate crates. Zero panics in production paths.
- **Go**: Strict standard library usage. Zero unchecked error returns.
- **Coq**: Zero admitted proofs (`Admitted`), zero unapproved axioms (`Axiom`). Machine-checked via `coqchk`.
- **SystemVerilog**: Non-synthesizable constructs restricted to testbenches (`tb/`). Synthesisable RTL (`rtl/`) MUST pass Verilator linting (`-Wall`).
