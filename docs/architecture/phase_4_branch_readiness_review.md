# Phase 4 Branch Readiness Review

**Reviewer Role:** Principal Systems Architect & Low-Level Distributed Systems Engineer  
**Target Branch:** `feature/phase-4-routing-dispatch`  
**GitHub Pull Request:** `#26` (`feat(replica): implement Phase 4 Routing & Dispatch Subsystem (RD-1..RD-24)`)  
**Base Revision:** `v0.3.0` (`723b32f` / `9130291`)  
**Audit Date:** 2026-08-21  
**Status:** **BLOCKED (CONFIGURATION GOVERNANCE & SCHEMA STANDARDIZATION REQUIRED)**  

---

## 1. Scope

This document provides a clean-room architectural readiness review of the **Cortex Phase 4 Routing & Dispatch Subsystem** branch (`feature/phase-4-routing-dispatch`). The scope encompasses:
- Reconstructing the system architecture from existing repository code and formal specifications.
- Auditing the PR diff against the frozen Phase 1–3 baseline and approved Phase 4 specification.
- Inspecting security boundaries, IPC isolation, linearizable lease fencing, and state domain concurrency controls.
- Reviewing configuration lifecycle, hash generation, hot-reload semantics, and schema standardization.
- Executing the complete canonical verification pipeline (`scripts/verify.sh`).
- Mapping all Phase 4 invariants against the Cortex formal assurance taxonomy and baseline gates (Gate G, H, I, J, F4a, F4b, F4c, L1/L2).
- Recording an audit trail (`Original State → Finding → Evidence → Decision → Remediation → Re-Test → Final Status`).

---

## 2. Branch / PR Inventory

### Branch & Pull Request Metadata
- **Branch:** `feature/phase-4-routing-dispatch`
- **GitHub Pull Request:** `#26` (`feat(replica): implement Phase 4 Routing & Dispatch Subsystem (RD-1..RD-24)`)
- **Merge Base Commit:** `9130291f48d614c84aa3aff5e1b13b9467e5b9b1` (`bump(version): set version to 0.3.0rc1`)
- **Merged Baseline Head:** `723b32f` (`v0.3.0` release baseline)
- **Head Commit:** `9402198` (`docs(architecture): add Phase 4 readiness review and configuration standardization audit artifacts`)

### Key File Changes Summary
| Category | File Path | Description |
| :--- | :--- | :--- |
| **Kernel Replica** | `cortex/tools/kernel/replica/__init__.py` | Module initialization & exports |
| **Kernel Replica** | `cortex/tools/kernel/replica/identity.py` | `ExecutionIdentity` vs `OwnershipIdentity` separation |
| **Kernel Replica** | `cortex/tools/kernel/replica/lease.py` | `LeaseManager` single-lock atomic revalidation & fencing |
| **Kernel Replica** | `cortex/tools/kernel/replica/ledger.py` | `InvocationStateLedger` journal persistence & crash recovery classifier |
| **Kernel Replica** | `cortex/tools/kernel/replica/lifecycle.py` | `WorkerLifecycleTracker` drain & quiescence state machine |
| **Kernel Replica** | `cortex/tools/kernel/replica/router.py` | `CandidateResolver`, `RoutingPolicy`, `GatewayDispatcher`, `StateDomainKey` |
| **Assurance** | `cortex_assurance_manifest.json` | Registration of `CLAIM-PHASE-4-ROUTING` under `IMPLEMENTATION_CERTIFIED` |
| **Tests** | `tests/conformance/test_replica_phase_4.py` | Conformance suite covering 24 verification gates (`RD-1` to `RD-24`) |
| **Tests** | `tests/conformance/test_replica_phases_1_to_3.py` | Conformance suite covering 18 replica scaling gates (`RS-1` to `RS-18`) |
| **Specifications** | `docs/architecture/phase_4_routing_and_dispatch_specification.md` | Normative routing & dispatch specification |
| **Specifications** | `docs/architecture/configuration_and_control_plane_specification.md` | Control plane & configuration lifecycle specification |
| **Specifications** | `docs/architecture/replica_scaling_specification.md` | Worker pool scaling & lease fencing specification |
| **Audits** | `docs/architecture/phase_4_branch_readiness_review.md` | Phase 4 branch readiness audit document |
| **Audits** | `docs/architecture/configuration_standardization_audit.md` | Configuration standardization audit document |
| **Audits** | `docs/architecture/configuration_schema_reference.md` | Canonical configuration schema reference (`v1.0.0`) |

---

## 3. Architecture Reconstruction

The Cortex kernel subsystem implements a spatiotemporal authority and semantic verification framework designed for high-concurrency, zero-trust execution. Phase 4 introduces the **Gateway Control Plane Routing & Dispatch Subsystem**, which bridges client intent processing with isolated sandboxed worker replicas.

```
+-----------------------------------------------------------------------------------+
|                              TCB GATEWAY AUTHORITY                                |
|                                                                                   |
|  +--------------------+    +--------------------+    +-------------------------+  |
|  | CandidateResolver  | -> |   RoutingPolicy    | -> |    LeaseManager         |  |
|  | (Unprivileged      |    | (Least-Inflight    |    | (Single-Lock Atomic     |  |
|  |  Snapshot Filter)  |    |  + Deterministic)  |    |  Revalidation & Grant)  |  |
|  +--------------------+    +--------------------+    +-------------------------+  |
|                                                                   |               |
|  +--------------------------------------------------+             v               |
|  |            InvocationStateLedger                 |   +--------------------+    |
|  | (Append-Only JSONL Journal + Crash Classifier)   |   | OwnershipIdentity  |    |
|  +--------------------------------------------------+   | (Epoch-Bound Lease)|    |
|                                                         +--------------------+    |
+-------------------------------------------------------------------|---------------|
                                                                    v
                                                     +------------------------------+
                                                     | Sandboxed Worker Replicas    |
                                                     | (Profile A: Linux Seccomp /  |
                                                     |  Landlock / Namespaces)      |
                                                     +------------------------------+
```

---

## 4. Engineering Assessment & Governance Status

```
Component                       Status
------------------------------------------------------------
Routing Architecture            GOOD
Lease Fencing                   GOOD
Recovery Boundaries             GOOD
Persistence Journal             GOOD
Canonical Verification Stack    PASSED (6/6 Gates, 333/333 Tests)
Configuration Audit             GOOD
Canonical Vocabulary            STANDARDIZED (19/19 Fields)
Canonical JSON Schema           UPDATED ($id: https://cortex.security/...)
Security Field Precedence       SPECIFIED (Category-level rules)
Generation / Hash Lifecycle     FORMALIZED
Monotonic Rollback Semantics    FORMALIZED (Gen N+1 with old payload)
Schema ↔ Implementation Parity  PENDING CODE-LEVEL RESOLVER BINDING
```

---

## 5. Assurance Matrix

Every Phase 4 invariant is mapped to the existing Cortex assurance taxonomy:

| Invariant / Property | Claim ID / Spec Ref | Scope / Boundary | Assurance Classification | Status | Silent Invalidation Check |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Spatial Attenuation & Capability Monotonicity** | `CLAIM-F2-F3-AUTHORITY-MODEL` | Coq Model (`AuthorityModel.v`) | `FORMALLY VERIFIED` | LOCKED | **Gate G / H Intact** (No privilege escalation) |
| **Causal Monotonicity & Parent Chains** | `CLAIM-F4A-EVIDENCE-MODEL` | Coq Evidence Model (`GateF_F4`) | `FORMALLY VERIFIED` | LOCKED | **F4a Intact** (Causal links preserved) |
| **Digest Representation Identity** | `CLAIM-F4B-DIGEST-ALIGNMENT` | Coq Concrete Crypto (`GateF_F4b`) | `BOUNDED REFINEMENT` | LOCKED | **F4b Intact** (SHA-256 digest mapping preserved) |
| **Iterative Graph Decision Spec** | `CLAIM-F4C-VERIFIER-MODEL` | Coq Verifier Spec (`GateF_F4c`) | `FORMALLY VERIFIED` | LOCKED | **F4c Intact** (Graph verification spec unmodified) |
| **Evidence Bundle Profile V1** | `CLAIM-F4C-DOMAIN-V1` | JSON Schema Profile V1 | `BOUNDED REFINEMENT` | LOCKED | **Gate J Intact** (Schema compatibility preserved) |
| **Verifier CLI Equivalence** | `CLAIM-F4C-VERIFIER-BRIDGE` | Tested Golden Corpus (5/5) | `EMPIRICALLY TESTED` | OPEN | **Gate J Intact** (Verifier CLI passes test corpus) |
| **CBE Binary Encoding Parity** | `CLAIM-CBE-CONCRETE-REFINEMENT` | Coq / Py / Rust / Go | `BOUNDED REFINEMENT` | REFINEMENT_TESTED | **Gate H Intact** (Cross-runtime CBE wire parity) |
| **Supervisor Side-Effect Trapping** | `CLAIM-GATE-G-SUPERVISOR` | Profile A Linux Sandbox | `IMPLEMENTATION-CERTIFIED` | LOCKED | **Gate G Intact** (Seccomp/Landlock isolation enforced) |
| **Intent-Actuation Parity** | `CLAIM-GATE-H-PARITY` | Profile A IPC Framing | `IMPLEMENTATION-CERTIFIED` | LOCKED | **Gate H Intact** (Bit-for-bit frame parity maintained) |
| **Rolling State Monotonicity** | `CLAIM-GATE-I-WITNESS` | IPC State Witness Chain | `IMPLEMENTATION-CERTIFIED` | LOCKED | **Gate I Intact** (Causal witness chain maintained) |
| **Standalone Verifier Gate** | `CLAIM-GATE-J-VERIFIER` | Gate J Independent Verifier | `IMPLEMENTATION-CERTIFIED` | LOCKED | **Gate J Intact** (Independent verification passes) |
| **STCR Pipeline Safety** | `CLAIM-HARDWARE-L1-L2-MODEL` | Coq Stuttering Model (`GateL1`) | `FORMALLY VERIFIED` | LOCKED | **L1/L2 Intact** (Hardware behavioral model unchanged) |
| **STCR RTL Trace Bridge** | `CLAIM-HARDWARE-L1-L2-TRACE` | SystemVerilog RTL (`cortex_stcr`) | `BOUNDED REFINEMENT` | TRACE_VERIFIED | **L1/L2 Intact** (Verilated trace bridge passes) |
| **Phase 4 Unprivileged Routing** | `CLAIM-PHASE-4-ROUTING` | `router.py`, `lease.py`, `ledger.py` | `IMPLEMENTATION-CERTIFIED` | VERIFIED | **Phase 4 Gate (RD-1..RD-24)** Single Gateway Domain |

---

## 6. Findings & Remediations Log

| Finding ID | Title | Severity | Remediation Action | Verification | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FIND-P4-001** | Lockfile Out of Sync | `HIGH` | Aligned `pyproject.toml` version to `0.3.0` and updated `uv.lock` via `uv lock` | `./scripts/verify.sh` Gate 1 PASS | **REMEDIATED** |
| **FIND-P4-002** | Dogfood Harness Test Failure | `HIGH` | Merged `main` commit `0a80136` allowing version set `{"0.2.0", "0.3.0rc1", "0.3.0"}` | 333/333 unittest PASS | **REMEDIATED** |
| **FIND-P4-003** | Configuration Naming Aliases | `MEDIUM` | Produced `configuration_schema_reference.md` (`v1.0.0`) and normalization table | `docs_audit.py` PASS | **REMEDIATED** |
| **FIND-P4-004** | Exception-Safe Lock Cleanup | `MEDIUM` | Confirmed `GatewayDispatcher` lock management safety | Conformance test RD-24 PASS | **REMEDIATED** |
| **FIND-P4-005** | Branch Version Sync | `LOW` | Merged `main` into `feature/phase-4-routing-dispatch` (`4145416`) | Clean git tree & test pass | **REMEDIATED** |
| **FIND-P4-006** | Schema Namespace Divergence | `HIGH` | Corrected `$id` to `https://cortex.security/schemas/v1/configuration.schema.json` | Schema audit PASS | **REMEDIATED** |
| **FIND-P4-007** | Audit vs Schema Coverage Gap | `HIGH` | Expanded JSON Schema to cover all 19 audit configuration parameters | Parity audit PASS | **REMEDIATED** |
| **FIND-P4-008** | Security Field Protection | `HIGH` | Defined category-level precedence matrix restricting security/identity overrides | Governance audit PASS | **REMEDIATED** |
| **FIND-P4-009** | Rollback Generation Monotonicity | `MEDIUM` | Formally specified rollback as $N+1$ generation with historical payload | Architecture audit PASS | **REMEDIATED** |

---

## 7. Merge Decision

### Current Decision: **BLOCKED**

> [!CAUTION]
> **MERGE POSTURE:** While the routing architecture, lease manager, journal persistence, and core test suite (`RD-1..RD-24`) are implementation-certified, Phase 4 readiness requires full control-plane configuration determinism and code-level schema ↔ resolver parity.
> The branch remains **BLOCKED** from merging into `main` pending final implementation binding of the canonical configuration resolver.

### Required Criteria to Unblock:
1. **Canonical Schema Validation:** Confirm Python resolver validates inputs against `https://cortex.security/schemas/v1/configuration.schema.json`.
2. **Security Field Lockout:** Verify CLI/ENV parsers reject overrides for `sandbox.profile_name`, `required_capabilities`, `journal_path`, and `group_id`.
3. **Monotonic Rollback Test:** Add test verifying configuration rollback increments generation counter ($N+1$).
4. **Final Verification Pass:** Re-execute `./scripts/verify.sh` with 100% pass across all 6 gates.
