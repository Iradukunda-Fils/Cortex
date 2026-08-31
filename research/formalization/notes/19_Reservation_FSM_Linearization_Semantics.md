# Research Note 19: Reservation State Machine & Linearization Semantics

> **Governance Status**: `NORMATIVE RESEARCH SPECIFICATION`  
> **Baseline Version**: `v1.6.0-VERIFIED`  
> **Date**: August 26, 2026  
> **Repository SHA**: `9ad95fd` (`main`)  
> **Master Directive**: `PHASE 7.1 — RESERVATION FSM & LINEARIZATION SEMANTICS DIRECTIVE`  
> **Operational System Classification**:  
> $$\boxed{ \text{Phase 5/6 Scalar Load Balancer = Proven Operational Baseline} }$$  
> $$\boxed{ \text{Phase 7.0/7.1 Resource Authority = Authorized Research \& Formalization Target} }$$  
> $$\boxed{ \text{Phase 7.6 Resource-Aware Scheduler = STRICTLY BLOCKED by 7.1--7.5} }$$

---

## 1. Governance & Proof Status Matrix

| Layer | Governance Status | Formal Verification Status | Implementation Status |
| :--- | :--- | :--- | :--- |
| **Scalar Load Balancer** | `PROVEN BASELINE` | `FORMALLY VERIFIED` (`Phase5Simulation.v`) | `IMPLEMENTED & ENFORCED` |
| **Phase 7.0 Specification** | `RESEARCH SPECIFICATION` | `ARCHITECTURALLY SPECIFIED` | `DOCUMENTED` |
| **Phase 7.1 FSM & Linearization** | `AUTHORIZED RESEARCH` | `FORMAL SEMANTICS SPECIFIED` | `DESIGN AUDITED` |
| **Phase 7.2 Coq Safety Model** | `BLOCKED BY 7.1` | `UNPROVEN` | `NOT STARTED` |
| **Phase 7.3 Python Refinement** | `BLOCKED BY 7.2` | `UNPROVEN` | `NOT STARTED` |
| **Phase 7.4 Enforcement Mapping** | `BLOCKED BY 7.3` | `UNPROVEN` | `RESEARCH MAPPING` |
| **Phase 7.5 TLA+ Model** | `BLOCKED BY 7.4` | `UNPROVEN` | `NOT STARTED` |
| **Phase 7.6 Vector Scheduler** | `STRICTLY BLOCKED` | `UNPROVEN` | `NOT STARTED` |

---

## 2. Authoritative Reservation State ($S_R$)

The minimal authoritative reservation state $S_R$ is defined independently of any runtime execution engine:

$$\boxed{ S_R = \langle R,\ U,\ Q_R,\ E_A,\ E_L,\ G,\ D \rangle }$$

Where:
- $R$: Set of active reservation objects $R = \{ r_1, r_2, \dots \}$.
- $U$: Resource accounting state vector across domains $\mathcal{R}$.
- $Q_R$: Quarantine and recovery reservation state.
- $E_A, E_L, G$: Monotonic fencing tokens (Authority epoch, Lease epoch, Worker generation).
- $D$: Persisted WAL log prefix.

All external telemetry metrics, capability index maps, and capacity snapshots are strictly derived functions:

$$\boxed{ Derived_R = f(S_R) }$$

---

## 3. Reservation State Machine Transitions & Invariants

```
                      RESERVATION STATE MACHINE & TRANSITIONS
                                         │
                                    [Intent Created]
                                         │
                                         ▼
                                      PENDING
                                         │
                       ┌─────────────────┴─────────────────┐
                       │ Activate(r)                       │ Expire(r) / Revoke(r)
                       ▼                                   ▼
                    ACTIVE                              EXPIRED / REVOKED
                       │                                   │ (Reserved_r = 0)
            ┌──────────┴──────────┐                        └──────────────┐
            │ Release(r)          │ Expire(r) / Revoke(r)                 │
            ▼                     ▼                                       ▼
         RELEASED              EXPIRED / REVOKED                  RECLAIMED STATE
      (Reserved_r = 0)       (Reserved_r = 0)
```

### Transition Operators
$$\{ Reserve(r), \quad Activate(r), \quad Release(r), \quad Expire(r), \quad Revoke(r), \quad Recover(r) \}$$

### Core Safety Invariants
1. **Ownership Invariant**:
   $$\boxed{ Active(r) \implies ExactlyOne(I, A, W, E_A, E_L, G) }$$

2. **Terminal Zero Invariant**:
   $$\boxed{ Terminal(r) \in \{ \text{RELEASED}, \text{EXPIRED}, \text{REVOKED} \} \implies Reserved_r = 0 }$$

3. **Authoritative Capacity Bound Invariant**:
   $$\boxed{ \sum_{r \in ActiveReservations} d_{r, k} + Used_k \le Capacity_k - M^{\text{safety}}_k - E^{\text{uncertainty}}_k \quad \forall k \in \mathcal{R} }$$

---

## 4. Abstract Linearization Semantics ($LP(op)$)

To maintain proof portability across Python, Go, Rust, or native implementations, linearization is defined abstractly without tying the formal model to a specific Python concurrency primitive (such as `RLock` or CAS):

$$\boxed{ LP(op) = \text{the unique abstract instant at which } S_R \text{ undergoes atomic state transition} }$$

$$\boxed{ \forall op_1, op_2,\quad op_1 \neq op_2 \implies LP(op_1) \neq LP(op_2) }$$

Every valid state transition satisfies:

$$\boxed{ Invariant(S_R) \land Pre(S_R, op) \implies Invariant(op(S_R)) }$$

---

## 5. Composite Resource Domain Algebra ($\mathcal{R}$)

Resource types are defined as a formal product space with distinct algebraic composition operators:

$$\mathcal{R} = \mathcal{R}_{\text{additive}} \times \mathcal{R}_{\text{rate}} \times \mathcal{R}_{\text{discrete}}$$

$$\mathbf{R} = (R_{\text{cpu}}, R_{\text{mem}}, R_{\text{gpu}}, R_{\text{vram}}, R_{\text{io}}, R_{\text{net}}, R_{\text{fd}}, R_{\text{thread}}, R_{\text{storage}})^T$$

- **Additive Domain ($\mathcal{R}_{\text{additive}}$)**: Arithmetic addition ($+$). Memory/VRAM bytes, CPU quotas.
- **Rate Domain ($\mathcal{R}_{\text{rate}}$)**: Token rate addition ($+$). IOPS, Network bandwidth.
- **Discrete Partitioning Domain ($\mathcal{R}_{\text{discrete}}$)**: Discrete vector indexing. Physical GPU device allocation ($GPU_0, GPU_1$).

Component-wise vector ordering $\mathbf{x} \preceq \mathbf{y}$ governs placement feasibility:

$$\boxed{ Feasible(i, w) \iff \mathbf{d}_i \preceq \mathbf{R}_w^{\text{sched}} }$$

---

## 6. Architectural Synchronization Trade-off Audit

Synchronization mechanisms evaluated against the Master Quality Axiom:

$$\boxed{ \text{Safety} > \text{Proof Complexity} > \text{Resource Bounds} > \text{Determinism} > \text{Scalability} > \text{Performance} }$$

| Strategy | Safety Impact | Proof Complexity | Determinism | Scalability | Final Audit Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Atomic Global Lock** | High (Complete linearizability) | Low (Single state transition) | High (Deterministic order) | Low (Contention at 10k/s) | **SELECTED BASELINE** for Control Plane $S_R$ |
| **Per-Worker Locks** | Medium (Cross-worker races) | High (Deadlock invariants) | Medium | Medium | **REJECTED** (High proof complexity) |
| **Sharded Authority** | Low (Split-brain risks) | Extremely High | Low | High | **REJECTED** (Violates Single Authority) |
| **CAS / Lock-Free** | High (Optimistic retry) | High (ABA & livelock proofs) | Low (Variable latency) | High | **REJECTED** (Livelock risk under load) |

---

## 7. Concrete Refinement Target ($R(C_{\text{Python}}, A_{\text{Coq}})$)

Phase 7.3 will establish an explicit forward simulation refinement relation between concrete Python code $C_{\text{Python}}$ (`resource_authority.py`) and abstract Coq model $A_{\text{Coq}}$ (`Phase7Reservation.v`):

$$\boxed{ \forall s_c, s_a,\quad R(s_c, s_a) \land Step(s_c, a, s'_c) \implies \exists s'_a,\ Step(s_a, a, s'_a) \land R(s'_c, s'_a) }$$

---

## 8. Authoritative Dependency Chain (7.1 $\rightarrow$ 7.6)

$$\text{7.1 Reservation FSM + Linearization}$$
$$\downarrow$$
$$\text{7.2 Resource Algebra + Coq Safety Model (`Phase7Reservation.v`)}$$
$$\downarrow$$
$$\text{7.3 Python Resource Authority + Concrete Refinement } R(C_{\text{Python}}, A_{\text{Coq}})$$
$$\downarrow$$
$$\text{7.4 OS/GPU/Runtime Enforcement Mapping Research (cgroups, CUDA stream fences)}$$
$$\downarrow$$
$$\text{7.5 TLA+ Distributed Reservation Model (`Phase7DistributedReservation.tla`)}$$
$$\downarrow$$
$$\text{7.6 Resource-Aware Scheduler (`ResourceAwareScheduler` --- STRICTLY BLOCKED)}$$
