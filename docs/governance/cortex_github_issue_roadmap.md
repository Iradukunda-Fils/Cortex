# Cortex Master GitHub Issue Roadmap (v1.6.0-VERIFIED)

> **Governance Status**: `NORMATIVE GITHUB ISSUE ROADMAP & DEPENDENCY SPECIFICATION`  
> **Baseline Version**: `v1.6.0-VERIFIED`  
> **Repository SHA**: `9ad95fd` (`main`)  
> **Total Open Remote Issues**: 7 Open Issues  
> **Master Principle**: $\boxed{\text{Safety} > \text{Formal Assurance} > \text{Resource Bounds} > \text{Determinism} > \text{Scalability} > \text{Performance}}$  
> **Open Issues Priority Ranking**: $\boxed{ \#23 > \#33 > \#36 > \#32 > \#35 > \#37 > \#19 }$

---

## 1. Master Architectural Baseline & Production Assurance Gate

```
                      v1.6.0-VERIFIED ARCHITECTURAL BASELINE
                                        │
                                        ▼
                  Issue #41: CBE Protocol Decoder Memory Bound (CLOSED_VALID)
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
   Issue #42: ObjectRef Data Plane               Issue #43: ResourceContract
   (CLOSED_VALID)                                (CLOSED_VALID)
                         │                             │
                         └──────────────┬──────────────┘
                                        ▼
                  Issue #44: Gateway HMAC Idempotency & Fencing (CLOSED_VALID)
                                        │
                                        ▼
                  Issue #45: Effect Reconciliation Engine (CLOSED_VALID)
                                        │
                                        ▼
                  Issue #34: Phase 5 Dynamic Load Balancer (CLOSED_VALID)
                                        │
                                        ▼
                  Issue #46: Phase 5 Coq Model & Abstract Safety (CLOSED_VALID)
                                        │
                                        ▼
                  Issue #47: Phase 5 Concrete Simulation Refinement (CLOSED_VALID)
                                        │
                                        ▼
                  Issue #48: Phase 6 Durable WAL Coq Model (CLOSED_VALID)
                                        │
                                        ▼
                  Issue #49: TLA+ Distributed Authority Model (CLOSED_VALID)
                                        │
                                        ▼
                  Issue #50: Scheduler Optimization & Benchmarks (CLOSED_VALID)


                         PRODUCTION ASSURANCE GATE
                                     │
                        ┌────────────┴─────────────┐
                        │                          │
                   Formal Safety              Runtime Safety
                        │                          │
                    Coq / TLA+               Fuzz / Stress
                        │                          │
                        └────────────┬─────────────┘
                                     │
                               Security Review (#23)
                                     │
                               Sandbox Review (#33)
                                     │
                                Resource Audit
                                     │
                               Production Gate


AUTHORIZED NEXT EXECUTION SEQUENCE:
$$\boxed{ \#23 / \#33 / \#36 \rightarrow \#32 \rightarrow \text{resource-model hardening} \rightarrow \text{scheduler read/write research} \rightarrow \text{10k/100k profiling} \rightarrow \text{scheduler redesign} }$$

Community Track:       Issue #19 (Create Newcomer Documentation) [OPEN]
```

---

## 2. Machine-Readable Issue Dependency Specifications

### Issue #41: CBE Protocol-Derived Decoder Memory Bound
- **Status**: `CLOSED_VALID`
- **Priority**: P0 Security Blocker
- **Depends-On**: Baseline release `main` (`00deade`)
- **Blocks**: Issue #42, Issue #43, `v0.4.1-experimental`
- **Release Target**: `v0.4.1-experimental`
- **Research Spec**: `docs/architecture/cbe_transport_architecture.md`
- **Coq Formal Proof**: `CBESpec.v` (`cbe_stream_buffer_bounded_safety`)
- **Commit Evidence**: `df0fa55`

### Issue #42: Canonical ObjectRef Data Plane & Opaque Locators
- **Status**: `CLOSED_VALID`
- **Priority**: P1 Target
- **Depends-On**: Issue #41
- **Blocks**: Data plane large object streaming
- **Parallel-With**: Issue #43
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/object_transfer_and_shared_resource_model.md`
- **Coq Formal Proof**: `GateF_F4_EvidenceRefinement.v` (`object_ref_hash_integrity`)
- **Commit Evidence**: `8be0531`

### Issue #43: Canonical ResourceContract & Ephemeral Context
- **Status**: `CLOSED_VALID`
- **Priority**: P1 Target
- **Depends-On**: Issue #41
- **Blocks**: Issue #44
- **Parallel-With**: Issue #42
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/external_adapter_architecture.md`
- **Coq Formal Proof**: `Phase4RoutingRefinement.v` (`rd_f1_eligibility_safety`)
- **Commit Evidence**: `df0fa55`

### Issue #44: Authoritative Gateway HMAC Idempotency Engine
- **Status**: `CLOSED_VALID`
- **Priority**: P1 Target
- **Depends-On**: Issue #43
- **Blocks**: Issue #45
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/cortex_system_architecture_specification.md`
- **Coq Formal Proof**: `GateL1_EpochMonotonicity.v` (`hmac_idempotency_monotonic_epoch`)
- **Commit Evidence**: `df0fa55`

### Issue #45: Effect Reconciliation Engine & Layered Quarantine
- **Status**: `CLOSED_VALID`
- **Priority**: P1 Target
- **Depends-On**: Issue #44
- **Blocks**: Issue #34 (Phase 5 Load Balancer)
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/worker_execution_model.md`
- **Coq Formal Proof**: `Phase4RoutingRefinement.v` (`rd_f6_unadmitted_durable_safety`)
- **Commit Evidence**: `6277eba`

### Issue #34: Single-Gateway Dynamic Load Balancer Engine (`load_balancer.py`)
- **Status**: `CLOSED_VALID`
- **Priority**: P2 Feature
- **Depends-On**: Issue #45
- **Blocks**: Scale & Performance Suite
- **Release Target**: `v0.5.0-experimental`
- **Commit Evidence**: `ad44242`

---

## 4. Phase 7 Issue Dependency Hierarchy (7.0–7.6)

```
                            PHASE 7 DEPENDENCY HIERARCHY
                                         │
        Phase 7.0: Resource Algebra Specification (Research Note 18) [SPECIFIED]
                                         │
                                         ▼
        Phase 7.1: Reservation FSM & Linearization (Research Note 19) [AUDITED]
                                         │
                                         ▼
        Phase 7.2: Reservation Coq Safety Model (Phase7Reservation.v) [BLOCKED]
                                         │
                                         ▼
        Phase 7.3: Python Resource Authority & Refinement R(C, A) [BLOCKED]
                                         │
                                         ▼
        Phase 7.4: OS/GPU Runtime Enforcement Mapping Research [BLOCKED]
                                         │
                                         ▼
        Phase 7.5: Distributed Reservation TLA+ Model [BLOCKED]
                                         │
                                         ▼
        Phase 7.6: Resource-Aware Scheduler Engine [STRICTLY BLOCKED]
```

- **Phase 7.0**: `Resource Algebra Specification` — Normative specification in `Research Note 18`.
- **Phase 7.1**: `Reservation FSM & Linearization Semantics` — Normative semantics in `Research Note 19`.
- **Phase 7.2**: `Reservation Coq Safety Model` — Abstract Coq proofs (`Phase7Reservation.v`) for $P_1 \dots P_{10}$.
- **Phase 7.3**: `Concrete Python Reservation Refinement` — Concrete `resource_authority.py` satisfying $R(C_{\text{Python}}, A_{\text{Coq}})$.
- **Phase 7.4**: `OS/GPU/Runtime Enforcement Mapping Research` — Research mapping for candidate enforcement mechanisms (cgroups, CUDA stream fences, rlimits).
- **Phase 7.5**: `Distributed Reservation TLA+ Model` — TLA+ specification (`Phase7DistributedReservation.tla`) proving distributed reservation safety under network partitions.
- **Phase 7.6**: `Resource-Aware Scheduler` — Heterogeneous vector scheduler implementation (**STRICTLY BLOCKED by 7.0–7.5 gate completion**).

