# Cortex Experimental Release Lifecycle & Governance Plan

> **Governance Status**: `NORMATIVE RELEASE PLAN`  
> **Current Baseline Release Tag**: `v0.4.0-experimental` (`v0.4.0rc1`)  
> **Commit SHA**: `012b0950968e`  
> **Branch State**: `feature/phase-4-routing-dispatch` (Phase 4 code present & integrated)  
> **Assurance Manifest SHA-256**: `d748ec7a5f52eabfbe703e057b5b9d41f37636695453df05b2fa201c881ccf56`  
> **System Status**: `CONTROLLED_EXPERIMENTAL`  

---

## 1. Release Philosophy & Immutable Release Binding Rules

Cortex enforces an explicit experimental release lifecycle:

1. **Research & Engineering Baseline**: `v0.x` releases establish reproducible research baselines. A release tag does NOT imply production readiness.
2. **Mandatory Immutable Release Binding**: Every experimental release baseline MUST be bound to a complete, machine-verifiable release tuple:
   - **Release Tag**: e.g., `v0.4.0-experimental` (`v0.4.0rc1`)
   - **Commit SHA**: e.g., `012b0950968e`
   - **Branch State**: `feature/phase-4-routing-dispatch` (Phase 4 code present & integrated)
   - **Assurance Manifest SHA-256**: `d748ec7a5f52eabfbe703e057b5b9d41f37636695453df05b2fa201c881ccf56`
   - **Certification Counts**: Machine-derived test totals (333 Python tests, 136 integrated checks, 41 Rust tests, 1 Go package / 14 frames, 17 RTL cycle assertions / 12 bridge tests)
   - **Formal Proof Inventory**: 28 Coq `.v` source files, 26 compiled `.vo` artifacts, 0 admitted proofs, 0 axioms, 1 uninterpreted parameter (`sha256_bytes`)
   - **Schema Version**: `cortex/schemas/v1/configuration.schema.json` Draft 2020-12
   - **Toolchain Fingerprint**: Python 3.13/3.14, Rust 1.70+, Go 1.20+, Coq 8.16+, Verilator 5.0+
   - **Evidence Package**: Locked in `artifacts/release_candidates/v0.4.0-experimental/`
3. **No Silent Reconciliations**: Future releases must build on prior release evidence. Architectural changes must be evaluated against the existing assurance baseline.
4. **Fail-Closed Progression**: Promotion to the next version target requires 100% pass rates across Python, Rust, Go, Coq, and documentation audit runners.

---

## 2. Release Progression & Master Dependency Sequence

```
  Current Experimental Baseline: v0.4.0-experimental (Commit: 012b0950968e)
                                ↓
      P0 Release Blockers: DEBT-003 Config Resolver & DEBT-002 Ledger Persistence
                                ↓
                 v0.4.1-experimental Release
                                ↓
      Formal Refinement (DEBT-001) & Gate J Verifier Fuzzing (DEBT-007)
                                ↓
     Phase 5 Single-Gateway Load Balancing & Verification (LB-1..14)
                                ↓
                 v0.5.0-experimental Release
                                ↓
         Scale Validation & Pre-Warmed Bounded Worker Pools
                                ↓
                 v0.5.1-experimental Release
                                ↓
      Phase 6 Multi-Gateway Distributed Consensus & Federation
                                ↓
                 v0.6.0-experimental Release
                                ↓
       Phase 7 Hardware STCR FPGA Acceleration & RISC-V Target
                                ↓
                 v0.7.0-experimental Release
                                ↓
      Production Certification (Closure of P0–P13 Checklist)
                                ↓
                  v1.0.0 Enterprise Release
```

---

## 3. Detailed Version Target Specifications

### Baseline: `v0.4.0-experimental` (`v0.4.0rc1`)
- **Status**: `RELEASED BASELINE CANDIDATE`
- **Commit SHA**: `012b0950968e`
- **Assurance Manifest SHA-256**: `d748ec7a5f52eabfbe703e057b5b9d41f37636695453df05b2fa201c881ccf56`
- **Scope**: Phase 4 Gateway Routing & Lease Security Kernel. Single-gateway TCB authority model. Candidate resolution, `LEAST_INFLIGHT` routing, single-grant lease revalidation, state domain mutual exclusion fencing. Phase 4 code IS contained in this commit forming the Phase 4 baseline.
- **Evidence Package**: 333 Python tests PASS, 136 integrated checks PASS, 41 Rust tests PASS, Go package PASS (14 frames), 17 RTL cycle assertions PASS (12 bridge tests), 28 Coq modules clean (0 Admitted, 0 Axioms, `coqchk` PASS).

---

### Target: `v0.4.1-experimental` (Hardening & P0 Debt Closure)
- **Status**: `PLANNED`
- **Target Scope**: Reconcile ENV variable precedence with schema validation (`DEBT-003`, P0 Release Blocker); implement `InvocationLedger` snapshot model (`DEBT-002`, P0); clean up documentation audit warnings (`DEBT-005`).
- **Required Verification**:
  - `python tools/release/readiness.py` returning `PASS`.
  - Zero schema validation bypasses on environment variables.
  - Snapshot equation assertion $\text{Verify}(H_{\text{checkpoint}}, \text{trace}_{\text{after}})$ preserving causal chain continuity.
- **Release Artifacts**: Updated `cortex_assurance_manifest.json`, PyPI release `cortex-runtime 0.4.1`.

---

### Target: `v0.5.0-experimental` (Formal Refinement & Phase 5 Load Balancing)
- **Status**: `PLANNED`
- **Target Scope**: Formal concrete-to-Coq simulation refinement (`DEBT-001`); Gate J verifier property fuzzing (`DEBT-007`); single-gateway dynamic soft placement optimization (`load_balancer.py`) with full verification of gates `LB-1` through `LB-14`.
- **Blocked Features**: Multi-gateway consensus and cross-node leasing strictly deferred to Phase 6.
- **Required Assurance Evidence**:
  - Concrete-to-Coq forward simulation proof module compiled clean with 0 `Admitted` proofs.
  - Implementation of `cortex/tools/kernel/replica/load_balancer.py`.
  - Pass rate of 100% on `tests/conformance/test_replica_phase_5.py` (LB-1..LB-14).
  - Proof that telemetry loss triggers fail-closed fallback to Phase 4 `LEAST_INFLIGHT` safety semantics (`LB-13`).

---

### Target: `v0.6.0-experimental` (Phase 6 Multi-Gateway Federation)
- **Status**: `DEFERRED`
- **Target Scope**: Multi-node gateway cluster federation, Raft consensus-backed distributed lease manager, cross-gateway witness ordering.

---

### Target: `v0.7.0-experimental` (Phase 7 Hardware STCR Acceleration)
- **Status**: `DEFERRED`
- **Target Scope**: Hardware-enforced spatio-temporal capability checking on FPGA / RISC-V targets. Synthesizability gate (`DEBT-006`) verified via Yosys.

---

## 4. Historical Evidence & Rollback Strategy

1. **Immutability of Evidence**: Every release tag commits an immutable evidence bundle into `artifacts/release_candidates/vX.Y.Z-experimental/` containing:
   - `cortex_assurance_manifest.json`
   - `coq_print_assumptions_audit.json`
   - `audit_results.log`
   - `verification_closure_matrix.md`
2. **Rollback Strategy**: If a regression is discovered in a release candidate, the candidate tag is marked `DEPRECATED` and a corrective patch release (`v0.X.Y+1`) is cut. No release tag is ever overwritten or re-used.
