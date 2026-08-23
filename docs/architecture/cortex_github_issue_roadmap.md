# Cortex Master GitHub Issue Roadmap (v1.5.0-FROZEN)

> **Governance Status**: `NORMATIVE GITHUB ISSUE ROADMAP & DEPENDENCY SPECIFICATION`  
> **Baseline Version**: `v1.5.0-FROZEN`  
> **Repository SHA**: `00deade` (`main`)  
> **Total Open Remote Issues**: 13 Open Issues  
> **Regression Test Suite**: 347/347 Passed (100% Green)  

---

## 1. Master Pre-Phase 5 & Phase 5 Dependency DAG

```
                      v1.5.0-FROZEN ARCHITECTURAL BASELINE
                                        │
                                        ▼
                  Issue #41: CBE Protocol-Derived Decoder Memory Bound
                  (Release Target: v0.4.1-experimental | P0 Security Blocker)
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
   Issue #42: ObjectRef Data Plane & Locators    Issue #43: ResourceContract & Ephemeral Context
   (Release Target: v0.5.0-experimental | P1)   (Release Target: v0.5.0-experimental | P1)
                         │                             │
                         └──────────────┬──────────────┘
                                        ▼
                  Issue #44: Gateway HMAC Idempotency & LeaseEpoch Fencing
                  (Release Target: v0.5.0-experimental | P1 Target)
                                        │
                                        ▼
                  Issue #45: Effect Reconciliation & Quarantine Engine
                  (Release Target: v0.5.0-experimental | P1 Target)
                                        │
                                        ▼
                  Issue #34: Phase 5 Dynamic Load Balancer Engine
                  (Release Target: v0.5.0-experimental | P2 Feature)


PARALLEL FORMAL & ASSURANCE TRACKS (Non-Blocking for Pre-Phase 5 Core Execution)
─────────────────────────────────────────────────────────────────────────────────────────────
Formal Proof Track:    Issue #32 (Coq Forward Simulation Refinement)
Security Fuzzing Track: Issue #36 (Gate J Independent Verifier Test Suite)
Hardware Track:         Issue #37 (SystemVerilog Yosys Synthesis Gate)
Sandbox Profile Track:  Issue #33 (Profile B WASM Sandbox Profile)
Engineering Hygiene:   Issue #35 (Resolve Repository Audit Debt Items)
Community Track:       Issue #19 (Create Newcomer Documentation)
```

---

## 2. Machine-Readable Issue Dependency Specifications

### Issue #41: CBE Protocol-Derived Decoder Memory Bound
- **Status**: `OPEN` (Immediate Implementation Target)
- **Priority**: P0 Security Blocker
- **Depends-On**: Baseline release `main` (`00deade`)
- **Blocks**: Issue #42, Issue #43, `v0.4.1-experimental`
- **Release Target**: `v0.4.1-experimental`
- **Research Spec**: `docs/architecture/cbe_transport_architecture.md`
- **Coq Formal Proof**: `CBESpec.v` (`cbe_stream_buffer_bounded_safety`)
- **GitHub Link**: [#41](https://github.com/Iradukunda-Fils/Cortex/issues/41)

### Issue #42: Canonical ObjectRef Data Plane & Opaque Locators
- **Status**: `OPEN`
- **Priority**: P1 Target
- **Depends-On**: Issue #41
- **Blocks**: Data plane large object streaming
- **Parallel-With**: Issue #43
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/object_transfer_and_shared_resource_model.md`
- **Coq Formal Proof**: `GateF_F4_EvidenceRefinement.v` (`object_ref_hash_integrity`)
- **GitHub Link**: [#42](https://github.com/Iradukunda-Fils/Cortex/issues/42)

### Issue #43: Canonical ResourceContract & Ephemeral Context
- **Status**: `OPEN`
- **Priority**: P1 Target
- **Depends-On**: Issue #41
- **Blocks**: Issue #44
- **Parallel-With**: Issue #42
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/external_adapter_architecture.md`
- **Coq Formal Proof**: `Phase4RoutingRefinement.v` (`rd_f1_eligibility_safety`)
- **GitHub Link**: [#43](https://github.com/Iradukunda-Fils/Cortex/issues/43)

### Issue #44: Authoritative Gateway HMAC Idempotency Engine
- **Status**: `OPEN`
- **Priority**: P1 Target
- **Depends-On**: Issue #43
- **Blocks**: Issue #45
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/cortex_system_architecture_specification.md`
- **Coq Formal Proof**: `GateL1_EpochMonotonicity.v` (`hmac_idempotency_monotonic_epoch`)
- **GitHub Link**: [#44](https://github.com/Iradukunda-Fils/Cortex/issues/44)

### Issue #45: Effect Reconciliation Engine & Layered Quarantine
- **Status**: `OPEN`
- **Priority**: P1 Target
- **Depends-On**: Issue #44
- **Blocks**: Issue #34 (Phase 5 Load Balancer)
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/worker_execution_model.md`
- **Coq Formal Proof**: `Phase4RoutingRefinement.v` (`rd_f6_unadmitted_durable_safety`)
- **GitHub Link**: [#45](https://github.com/Iradukunda-Fils/Cortex/issues/45)

### Issue #34: Single-Gateway Dynamic Load Balancer Engine (`load_balancer.py`)
- **Status**: `OPEN` (Reprioritized behind Pre-Phase 5)
- **Priority**: P2 Feature
- **Depends-On**: Issue #45
- **Blocks**: Scale & Performance Suite
- **Release Target**: `v0.5.0-experimental`
- **GitHub Link**: [#34](https://github.com/Iradukunda-Fils/Cortex/issues/34)

---

## 3. Parallel Formal & Assurance Tracks

| Issue ID | Subsystem Track | Scope | Target Release |
| :--- | :--- | :--- | :---: |
| **#32** | Formal Proof Track | GatewayDispatcher Linearizability in Coq (`Phase4RoutingRefinement.v`) | `v0.5.0-experimental` |
| **#36** | Security Verification | Independent Verifier CLI Test Suite & Fuzzing | `v0.5.0-experimental` |
| **#37** | Hardware Gate | SystemVerilog STCR Pipeline Yosys Synthesis Gate | `v0.6.0-experimental` |
| **#33** | Sandbox Profile | Profile B WASM Sandbox Profile Certification | `v0.6.0-experimental` |
| **#35** | Engineering Hygiene | Resolve repository documentation warning debt items | `v0.4.1-experimental` |
| **#23** | Security Review | External Security Review & P0-P13 Checklist Verification | `v0.5.0-experimental` |
| **#19** | Community Onboarding| Newcomer documentation & developer quickstart | `v0.4.1-experimental` |
