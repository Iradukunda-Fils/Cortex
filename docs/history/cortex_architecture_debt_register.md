# Cortex System Debt Register

> **Governance Status**: `NORMATIVE SYSTEM DEBT REGISTER`  
> **Baseline Release**: `v0.4.0-experimental` (Commit `012b0950968e`)  
> **Manifest SHA-256**: `d748ec7a5f52eabfbe703e057b5b9d41f37636695453df05b2fa201c881ccf56`  

---

## 1. Master Debt Item Catalog

### DEBT-003: Environment Variable Precedence Bypassing Schema Validation (RELEASE BLOCKER)
- **ID**: `DEBT-003`
- **Category**: `CONFIGURATION`
- **Severity**: `CRITICAL`
- **Description**: Environment variables (e.g., `CORTEX_MAX_WORKERS`) are read directly in python code with fallback defaults, bypassing the strict Draft 2020-12 JSON Schema validation pipeline executed for config files. Configuration resolution sets security ceilings, sandbox profiles, and resource caps, making it part of the control plane's security boundary.
- **Impact**: Malformed or out-of-range ENV values could crash worker lifecycle initialization at runtime or alter security settings without validation.
- **Evidence**: `cortex/tools/kernel/replica/lifecycle.py` uses `int(os.getenv("CORTEX_MAX_WORKERS", 4))` without schema validation.
- **Affected Components**: `cortex/tools/cli/`, `cortex/tools/kernel/replica/lifecycle.py`
- **Required Action**: Pass all environment variable overrides through `ConfigResolver` prior to initializing lifecycle manager.
- **Verification**: Test vector injecting invalid ENV variables expecting `ERR_CONFIG_INVALID`.
- **Priority**: `P0` (RELEASE BLOCKER for full configuration governance seal)
- **Release Target**: `v0.4.1-experimental`

---

### DEBT-002: Invocation Ledger Persistence, Snapshot Model & Memory Compaction
- **ID**: `DEBT-002`
- **Category**: `RELIABILITY / PERSISTENCE`
- **Severity**: `HIGH`
- **Description**: `InvocationLedger` stores all historical invocation records in RAM indefinitely. Compacting historical records is a high-risk persistence change, not merely a performance optimization. The compaction design must distinguish logical history from physical storage representation.
- **Impact**: Unbounded host memory growth under sustained load; risk of breaking rolling SHA-256 state chain continuity if historical payloads are naively pruned.
- **Evidence**: `ledger.py` contains `self._records: List[LedgerRecord] = []` with no snapshotting mechanism.
- **Required Action**: Implement immutable snapshot roots ($H_{\text{checkpoint}}$) such that:
  $$\text{Verify}(H_{\text{checkpoint}}, \text{trace}_{\text{after}})$$
  preserves causal chain continuity without deleting logical checkpoints.
- **Affected Components**: `cortex/tools/kernel/replica/ledger.py`, `cortex/tools/kernel/services/event_store.py`
- **Verification**: Assertion proving causal witness continuity over 1,000,000 invocations with periodic checkpointing.
- **Priority**: `P0`
- **Release Target**: `v0.4.1-experimental`

---

### DEBT-001: Concrete-to-Coq Control Plane Refinement Simulation Bridge
- **ID**: `DEBT-001`
- **Category**: `FORMAL`
- **Severity**: `HIGH`
- **Description**: The formal safety kernel in `verification/Phase4RoutingRefinement.v` proves safety properties for an abstract state machine (RD-F1..RD-F17). The mapping from Python dataclasses to Coq Record fields is empirical.
- **Impact**: Code changes in Python could introduce subtle semantic drift not caught by Coq.
- **Evidence**: `cortex_assurance_manifest.json` flags `CLAIM-PHASE-4-CONCRETE-TO-COQ-REFINEMENT` as `BOUNDED_OR_OPEN`.
- **Required Action**: Formalize concrete-to-Coq forward simulation refinement relation:
  $$R(C, M) \land C \to C' \implies \exists M'. M \to^* M' \land R(C', M')$$
- **Affected Components**: `cortex/tools/kernel/replica/`, `verification/Phase4RoutingRefinement.v`
- **Verification**: `coqc` compilation of simulation refinement module with 0 `Admitted` proofs.
- **Priority**: `P1`
- **Release Target**: `v0.5.0-experimental`

---

### DEBT-007: Gate J Independent Verifier Property Fuzzing Engine
- **ID**: `DEBT-007`
- **Category**: `SECURITY / FORMAL`
- **Severity**: `HIGH`
- **Description**: The standalone offline verifier (`cortex_verifier.py`) is verified against 5 golden evidence bundles, but topological edge cases could cause crashes or indeterminate verdicts.
- **Impact**: A hostile verifier payload could cause resource exhaustion or bypass verifier assertions.
- **Evidence**: `readiness.py` logs `[BLOCKED] F4c Universal Verifier Domain Equivalence (Open)`.
- **Required Action**: Construct automated property fuzzing engine covering 13 adversarial classes: valid, truncated, reordered, duplicated, forked, cyclic, oversized, malformed CBE, unknown schema, invalid signature, invalid root, unknown anchor, resource exhaustion. Must guarantee no crashes, bounded memory, and deterministic verdicts (`VALID` / `INVALID` / `INDETERMINATE`).
- **Affected Components**: `cortex/tools/cortex_verifier.py`, `tests/conformance/`
- **Verification**: `test_f4c_corpus_conformance.py` passing all 13 adversarial topological classes.
- **Priority**: `P1`
- **Release Target**: `v0.5.0-experimental`

---

### DEBT-004: Gate G Sandbox Taxonomy & Profile Hardening
- **ID**: `DEBT-004`
- **Category**: `SECURITY`
- **Severity**: `HIGH`
- **Description**: Sandbox profiles maintain a strict taxonomy: Profile A = Native Linux sandbox (Seccomp-BPF + Landlock + Namespaces); Profile B = WASM sandbox (Wasmtime isolation).
- **Impact**: Ambiguity in sandbox profiles could lead to misconfiguring security boundaries for non-Python compiled runtimes.
- **Evidence**: `docs/architecture/gate_g_complete_mediation_inventory.md`.
- **Required Action**: Maintain stable sandbox taxonomy. Finalize WASM Profile B isolation rules and add adversarial test suite.
- **Affected Components**: `cortex/tools/kernel/context.py`, `tests/conformance/test_gate_g_adversarial.py`
- **Verification**: `test_gate_g_profile_b.py` test suite passing clean.
- **Priority**: `P1`
- **Release Target**: `v0.5.0-experimental`

---

### DEBT-006: Hardware RTL Synthesizability Gate (Yosys)
- **ID**: `DEBT-006`
- **Category**: `HARDWARE`
- **Severity**: `MEDIUM`
- **Description**: SystemVerilog RTL (`rtl/cortex_stcr_pipeline.sv`) passes 12/12 verilated trace bridge tests, but Yosys synthesis check is unautomated. Yosys PASS proves synthesizability ($\text{RTL} \to \text{synthesizable}$), NOT formal correctness ($\text{RTL} \implies \text{Cortex semantics}$).
- **Impact**: Physical FPGA targets could fail synthesis due to un-supported SV constructs.
- **Evidence**: Makefile lacks Yosys target.
- **Required Action**: Add automated Yosys synthesis gate to CI, keeping synthesizability evidence strictly distinct from formal trace extraction proofs.
- **Affected Components**: `rtl/cortex_stcr_pipeline.sv`, `Makefile`
- **Verification**: `make synth-check` executing cleanly in CI.
- **Priority**: `P2`
- **Release Target**: `v0.6.0-experimental`

---

### DEBT-005: Documentation Audit Hyperlink & Style Warnings
- **ID**: `DEBT-005`
- **Category**: `DOCUMENTATION`
- **Severity**: `LOW`
- **Description**: Running `tools/assurance/docs_audit.py` executes 307 checks and reports 222 style/link warnings across markdown specification files.
- **Impact**: Minor developer confusion or broken cross-references in rendered documentation.
- **Evidence**: `docs_audit.py` output logs 222 warnings during release readiness run.
- **Affected Components**: `docs/architecture/*.md`, `docs/guides/*.md`
- **Required Action**: Reconcile relative link targets, standardize heading structures, and eliminate orphan anchors across spec docs.
- **Verification**: `python tools/assurance/docs_audit.py` returning 0 warnings.
- **Priority**: `P3`
- **Release Target**: `v0.4.1-experimental`

---

## 2. Debt Summary Matrix

| Debt ID | Category | Severity | Priority | Target Release | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEBT-003** | CONFIGURATION | CRITICAL | P0 (RELEASE BLOCKER) | v0.4.1-experimental | OPEN |
| **DEBT-002** | PERSISTENCE | HIGH | P0 | v0.4.1-experimental | OPEN |
| **DEBT-001** | FORMAL | HIGH | P1 | v0.5.0-experimental | OPEN |
| **DEBT-007** | SECURITY / FORMAL | HIGH | P1 | v0.5.0-experimental | OPEN |
| **DEBT-004** | SECURITY | HIGH | P1 | v0.5.0-experimental | OPEN |
| **DEBT-006** | HARDWARE | MEDIUM | P2 | v0.6.0-experimental | OPEN |
| **DEBT-005** | DOCUMENTATION | LOW | P3 | v0.4.1-experimental | OPEN |
