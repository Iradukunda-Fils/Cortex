# Cortex Open Work Register
**Authoritative Remaining Engineering Obligations & Backlog Ledger**  
**Date:** August 22, 2026  
**Repository Baseline SHA:** `f74f41f` (`main`)

---

## Open Work Register

| Work ID | Description | Source | Issue | Priority | Security Impact | Formal Impact | Dependency | Target Release | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OPEN-003** | External Security Review & P0-P13 Production Readiness | Security Plan | #23 | CRITICAL | Critical (Production Sign-off) | High (Full Matrix P1..P4) | WORK-021, WORK-022 | v1.0.0 | OPEN_REQUIRED |
| **OPEN-005** | Concrete-to-Coq Forward Simulation Refinement Relation | DEBT-005 | #32 | HIGH | High (Code-to-Proof Soundness) | Critical (Bridge concrete Python -> Rocq) | #21 | v0.4.1 | OPEN_REQUIRED |
| **OPEN-006** | Finalize WASM Profile B Sandbox Filters & Test Matrix | DEBT-006 | #33 | MEDIUM | High (Sandbox Isolation) | Medium (Gate G bounds) | None | v0.4.1 | OPEN_REQUIRED |
| **OPEN-007** | Single-Gateway Dynamic Load Balancer Engine (`load_balancer.py`) | Phase 5 Spec | #34 | HIGH | Medium (Availability & Rate Limits) | Medium (Routing Safety) | PR #27 spec | v0.5.0 | OPEN_REQUIRED |
| **OPEN-008** | Resolve 222 Hyperlink and Formatting Documentation Warnings | DEBT-007 | #35 | LOW | Low (Developer Experience) | Low (Documentation Integrity) | None | v0.4.1 | OPEN_REQUIRED |
| **OPEN-009** | Gate J 13-Class Property-Based Fuzzing Engine | DEBT-008 | #36 | HIGH | High (Adversarial Evidence Fuzzing) | High (Gate J Independent Verifier) | None | v0.4.1 | OPEN_REQUIRED |
| **OPEN-010** | Yosys Open-Source Synthesis Gate Check for STCR Pipeline | DEBT-009 | #37 | MEDIUM | High (Hardware Synthesis Conformance) | Medium (RTL AST Verification) | None | v0.4.1 | OPEN_REQUIRED |
| **OPEN-011** | Newcomer Contribution Path & Onboarding Documentation | Community | #19 | LOW | Low (Community Growth) | Low | None | v0.4.1 | OPEN_OPTIONAL |
