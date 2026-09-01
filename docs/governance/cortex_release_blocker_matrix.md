# Cortex Release Blocker Matrix

> **Governance Status**: `NORMATIVE RELEASE BLOCKER MATRIX`  
> **Baseline Release Tag**: `v0.5.0-experimental` (`v0.5.0rc1`)  
> **Commit SHA**: `9ad95fd`  
> **Current `main` SHA**: `9ad95fd`  
> **Assurance Manifest SHA-256**: `d748ec7a5f52eabfbe703e057b5b9d41f37636695453df05b2fa201c881ccf56`  

---

## 1. Governance Classification Taxonomy

Release blockers and work items are strictly categorized to prevent research tasks or optional profiles from artificially serializing release engineering:

1. **`Release + Security Blocker`**: Must be completely sealed before `v0.4.1-experimental` tag can be published.
2. **`Release + Integrity Blocker`**: High-risk persistence or state integrity requirement for release stability.
3. **`Formal Assurance Target`**: Coq formal proofs and simulation refinement modules.
4. **`Security Hardening`**: Empirical adversarial fuzzing and complete mediation testing.
5. **`Future Execution Profile`**: Non-blocking alternative runtime sandbox profiles (e.g. WASM Profile B).
6. **`Hardware Assurance Track`**: SystemVerilog trace extraction and synthesis checks.
7. **`Engineering Hygiene`**: Documentation warnings and cross-reference fixes.

---

## 2. Master Blocker & Work Item Catalog

| Work Item ID | Title / Subsystem | Classification | Depends-On | Implementation Dependency | Release Blocker Status | Remote GitHub Issue | Required Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BLK-P0-01** | Align ENV Configuration Precedence with Schema Validation (`DEBT-003`) | `Release + Security Blocker` | Baseline Tag `v0.4.0` | `BLOCKING` | **VERIFIED COMPLETE** | [#30](https://github.com/Iradukunda-Fils/Cortex/issues/30) | `tests/kernel/test_cli_env_precedence.py` (15 boundary vectors) |
| **BLK-P0-02** | Persistence Snapshot Model & Memory Compaction for `InvocationLedger` (`DEBT-002`) | `Release + Integrity Blocker` | Issue #30 | `SOFT-SEQUENCING` | **VERIFIED COMPLETE** | [#31](https://github.com/Iradukunda-Fils/Cortex/issues/31) | $\text{Verify}(H_{\text{checkpoint}}, \text{trace}_{\text{after}})$ assertion in compaction test |
| **BLK-P1-01** | Concrete-to-Coq Forward Simulation Refinement Bridge (`DEBT-001`) | `Formal Assurance Target` | Issue #30 | `PARALLEL FORMAL` | **ASSURANCE TARGET** (`v0.5.0`) | [#32](https://github.com/Iradukunda-Fils/Cortex/issues/32) | Coq compilation (`coqc`) of simulation module with 0 `Admitted` proofs |
| **BLK-P1-02** | Single-Gateway Dynamic Load Balancer Engine (`load_balancer.py`) | `Release + Architecture Target` | Issue #30, PR #27 Merged | `BLOCKING` | **VERIFIED COMPLETE** | [#34](https://github.com/Iradukunda-Fils/Cortex/issues/34) | `tests/conformance/test_replica_phase_5.py` (LB-1..LB-14) |
| **TRK-SEC-01**| Gate J Independent Verifier 13-Class Property Fuzzing Engine | `Security Hardening` | None | `PARALLEL` | **SECURITY TRACK** (`v0.5.0`) | [#36](https://github.com/Iradukunda-Fils/Cortex/issues/36) | `python tests/conformance/fuzz_verifier.py` (1,000+ synthetic graphs) |
| **TRK-FRM-01**| F4c Verifier Domain Universal Equivalence Coq Proof | `Formal Assurance Target` | None | `PARALLEL` | **VERIFIED COMPLETE** | [#21](https://github.com/Iradukunda-Fils/Cortex/issues/21) | Formal Coq proof file compiled clean without axioms |
| **TRK-WASM-01**| Gate G WASM Sandbox Profile B Certification Suite | `Future Execution Profile` | None | `PARALLEL` | **FUTURE PROFILE TRACK** | [#33](https://github.com/Iradukunda-Fils/Cortex/issues/33) | `tests/conformance/test_gate_g_profile_b.py` passing 100% |
| **TRK-HW-01** | SystemVerilog RTL Step Extraction Universal Coq Proof | `Hardware Assurance Track` | None | `PARALLEL` | **VERIFIED COMPLETE** | [#22](https://github.com/Iradukunda-Fils/Cortex/issues/22) | Machine-checked Coq extraction theorem |
| **TRK-HW-02** | SystemVerilog STCR Pipeline Yosys Synthesis Gate | `Hardware Assurance Track` | None | `PARALLEL` | **HARDWARE TRACK** (`v0.6.0`) | [#37](https://github.com/Iradukunda-Fils/Cortex/issues/37) | `make synth-check` executing clean in CI |
| **TRK-DOC-01**| Documentation Audit Hyperlink & Warning Cleanup | `Engineering Hygiene` | None | `PARALLEL` | **HYGIENE TRACK** (`v0.4.1`) | [#35](https://github.com/Iradukunda-Fils/Cortex/issues/35) | `python tools/assurance/docs_audit.py` returning 0 warnings |

---

## 3. Governance Dependency Rules

1. **`BLOCKING`**: Hard technical prerequisite for implementation (e.g. Issue #30 configuration precedence & PR #27 merge on `main` must complete before starting Issue #34 Phase 5 coding).
2. **`SOFT-SEQUENCING`**: Recommended operational ordering for engineering safety. Issue #31 (Ledger Compaction) does NOT prevent compiling or implementing Issue #34, but MUST be completed before `v0.4.1-experimental` or `v0.5.0-experimental` can be released.
3. **`PARALLEL FORMAL`**: Issue #32 (Concrete-to-Coq Refinement) runs in parallel with Phase 5 coding, but is required for `v0.5.0-experimental` formal assurance sign-off.
4. **`PARALLEL TRACKS`**: Independent workstreams (Security Fuzzing #36, Formal Equivalence #21, Hardware Synthesis #37, WASM Profile B #33, Docs Cleanup #35) proceed in parallel without blocking release core execution.
