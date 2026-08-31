# Research Note 18: Heterogeneous Resource-Vector Architecture & Cortex Resource Authority

> **Governance Status**: `NORMATIVE RESEARCH SPECIFICATION`  
> **Baseline Version**: `v1.6.0-VERIFIED`  
> **Date**: August 26, 2026  
> **Repository SHA**: `9ad95fd` (`main`)  
> **Master Directive**: `PHASE 7.0 — RESOURCE AUTHORITY FORMALIZATION GATE DIRECTIVE`  
> **Operational System Classification**:  
> $$\boxed{ \text{Phase 5/6 Scalar Load Balancer = Proven Operational Baseline} }$$  
> $$\boxed{ \text{Phase 7 Resource Authority = Formal Architecture Target} }$$  
> $$\boxed{ \text{Resource-Aware Scheduler = Future Phase 7.6 Layered Implementation} }$$

---

## 1. Subsystem Implementation & Formal Proof Status Matrix

| Subsystem Component | Implementation Status | Formal Verification Status | Runtime Status | Baseline Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Scalar Load Balancer ($C_w \in \mathbb{N}$)** | `IMPLEMENTED` | `FORMALLY VERIFIED` | `RUNTIME-ENFORCED` | `Phase5Simulation.v` (0 Axioms, 0 Admits) |
| **Derived Capability Index ($Index[c]$)** | `IMPLEMENTED` | `FORMALLY VERIFIED` | `RUNTIME-ENFORCED` | Invariant $I_9$ (`test_phase6_kernel_gate.py`) |
| **Versioned Snapshot Read View** | `IMPLEMENTED` | `EMPIRICALLY MEASURED` | `RUNTIME-ENFORCED` | `02_Scheduler_Benchmark_Results.md` (2.0–2.5x gain) |
| **Resource-Vector Mathematics ($\mathbf{R}_w, \mathbf{d}_i$)**| `SPECIFIED` | `SPECIFIED` | `RESEARCH SPECIFICATION` | `Research Note 18` |
| **Atomic Reservation Semantics** | `SPECIFIED` | `SPECIFIED` | `RESEARCH SPECIFICATION` | `Research Note 18` |
| **Cortex Resource Authority Engine** | `ARCHITECTURALLY SPECIFIED`| `UNPROVEN` | `UNPROVEN` | Phase 7.0 Formalization Gate |
| **Concrete Python Reservation Refinement** | `NOT YET IMPLEMENTED` | `UNPROVEN` | `UNPROVEN` | Phase 7.3 Formal Proof Target |
| **Distributed Vector Reservation** | `NOT YET IMPLEMENTED` | `UNPROVEN` | `UNPROVEN` | Phase 7.5 TLA+ Model Target |

---

## 2. Minimal Authoritative Reservation State ($S_R$)

To prevent derived telemetry caches, GPU statistics, indexes, or schedulability snapshots from accidentally becoming alternate authorities, Cortex defines the minimal authoritative reservation state $S_R$:

$$\boxed{ S_R = \langle R,\ U,\ Q_R,\ E_A,\ E_L,\ G,\ D \rangle }$$

Where:
- $R$: Set of active reservations $R = \{ r_1, r_2, \dots \}$.
- $U$: Authoritative resource usage & accounting state.
- $Q_R$: Reservation quarantine and recovery state.
- $E_A$: Monotonic authority epoch.
- $E_L$: Monotonic lease epoch.
- $G$: Worker generation incarnation counters.
- $D$: Persisted WAL durable state prefix.

All telemetry views, index maps, and capacity snapshots are strictly derived functions:

$$\boxed{ Derived_R = f(S_R) }$$

---

## 3. Total Order Linearization Point ($LP(Reserve)$) & Invariants

Reservation allocation occurs via a single atomic linearization operation $Reserve(i, w, \mathbf{d}_i)$ with linearization point $LP(Reserve)$:

$$LP(Reserve) = \text{atomic compare-and-commit of authoritative reservation state } S_R$$

$$\boxed{ \forall r_1, r_2,\quad r_1 \neq r_2 \implies LP(r_1) \neq LP(r_2) }$$

### Authoritative Capacity Bound Invariant
For every resource class $k$:

$$\boxed{ \sum_{r \in ActiveReservations} d_{r, k} + Used_k \le Capacity_k - M^{\text{safety}}_k - E^{\text{uncertainty}}_k }$$

### Stale Fencing Rejection Rule
$$\boxed{ (E_A, E_L, G_w) \neq (E_A^{\text{active}}, E_L^{\text{active}}, G_w^{\text{active}}) \implies Commit(r) = \text{REJECT} }$$

---

## 4. Distinction: Observation vs. Authority vs. Enforcement vs. Execution

$$\boxed{ \text{Hardware} \rightarrow \text{Observation} \rightarrow \text{Authority} \rightarrow \text{Reservation} \rightarrow \text{Enforcement} \rightarrow \text{Execution} }$$

```
                               RESOURCE PIPELINE DECOUPLING
                                            │
    1. Telemetry          `/proc/stat`, NVML, cgroups (Physical Substrate)
                                            │ (Telemetry -> Observation)
    2. Observation        Sampled Telemetry Metrics (Non-Authoritative)
                                            │ (Authority -> Reservation)
    3. Authority          Cortex Control Plane S_A, S_R (Canonical State Truth)
                                            │ (Reserved -> Enforcement)
    4. Reservation        Atomic State Transition Reserve(i, w, d_i)
                                            │ (Enforcement -> Physical Constraint)
    5. Enforcement        cgroup limits, CPU quota, FD limits, CUDA stream fences
                                            │ (Substrate -> Execution)
    6. Execution          Substrate Task Runners (Go, Rust, WASM, Native)
```

Tripartite usage relation:

$$\boxed{ Reserved \rightarrow Enforcement \rightarrow ObservedUsage }$$

---

## 5. Durable WAL Recovery Chain

On restart after failure, Cortex reconstructs authoritative state $S_R$ directly from the durable log prefix without trusting stale physical telemetry:

$$\boxed{ WAL \rightarrow Replay \rightarrow S_R \rightarrow Derived_R = f(S_R) }$$

---

## 6. Parallel Layered Architecture Coexistence

```
                            CORTEX CONTROL AUTHORITY
                                       │
                     ┌─────────────────┴─────────────────┐
                     │                                   │
            Existing Scalar LB               Cortex Resource Authority
             (Phase 5/6 Baseline)             (Phase 7.0 Vector Architecture)
                     │                                   │
              capability/index                   vector + reservation
                     │                                   │
                     └─────────────────┬─────────────────┘
                                       │
                               Placement Decision
                                       │
                     ┌─────────────────┼─────────────────┐
                     ▼                 ▼                 ▼
                 Go Transport      Rust Sandbox     Native / GPU
```

---

## 7. Authoritative Proof Obligations Matrix ($P_1 \dots P_{10}$)

| Proof ID | Theorem Name | Governing Formal Target | Verification Statement |
| :--- | :--- | :--- | :--- |
| **$P_1$** | `ReservationUniqueness` | Coq (`Phase7Reservation.v`) | $\forall i, \text{InvocationID}(i) \implies \#ActiveReservation(i) \le 1$ |
| **$P_2$** | `ResourceCapacitySafety` | Coq (`Phase7Reservation.v`) | $\sum_i Reservation_{i,r} \oplus_r Used_r \preceq Capacity_r$ |
| **$P_3$** | `ReservationConservation` | Coq (`Phase7Reservation.v`) | $StateTransition \implies ResourceInvariant(S'_R)$ |
| **$P_4$** | `ReservationReleaseSafety` | Coq (`Phase7Reservation.v`) | $Release(i) \implies Reserved'_r = Reserved_r - \mathbf{d}_{i,r}$ |
| **$P_5$** | `ExpiryReclamationSafety` | Coq (`Phase7Reservation.v`) | $Expired(r) \implies r \notin ActiveReservations \land Reserved'_r = 0$ |
| **$P_6$** | `AuthorityFencing` | Coq (`Phase7Reservation.v`) | $Authority(r) \neq E_A \implies Commit(r) = \text{REJECT}$ |
| **$P_7$** | `IncarnationFencing` | Coq & TLA+ | Stale worker incarnation $G_w \neq G_{\text{active}}$ cannot commit reservation |
| **$P_8$** | `TelemetryConservativeBound` | Coq (`Phase7Reservation.v`) | $E_r^{\text{uncertainty}} \ge \epsilon_r + \Delta_{\max} \cdot \left|\frac{dReal}{dt}\right|_{\max} \implies C^{\text{sched}}_r \le C^{\text{real}}_r$ |
| **$P_9$** | `PlacementFeasibility` | Coq (`Phase7Reservation.v`) | $Placement(i) = w \implies \mathbf{d}_i \preceq \mathbf{R}_w^{\text{sched}}$ |
| **$P_{10}$** | `DurableReservationReplay` | Coq & WAL Replay | $\boxed{ Replay(ValidPrefix(D)) = S'_{\text{reservation}} \land Invariant(S'_{\text{reservation}}) }$ |

---

## 8. Phase 7 Phase Structure & Execution Roadmap

$$\boxed{ \text{Phase 7.0 — Resource Authority Formalization Gate} }$$

$$\boxed{ \text{Resource Algebra} \rightarrow \text{Reservation FSM} \rightarrow \text{Linearization} \rightarrow \text{Coq Proof} \rightarrow \text{Concrete Refinement} \rightarrow \text{Enforcement} \rightarrow \text{Stress} \rightarrow \text{TLA+ Model} }$$

### Issue Hierarchy (Phase 7.0–7.6)
- **Phase 7.0**: Resource Algebra Specification (`Research Note 18`)
- **Phase 7.1**: Reservation State Machine & Linearization Semantics
- **Phase 7.2**: Reservation Coq Safety Model (`Phase7Reservation.v`)
- **Phase 7.3**: Concrete Python Reservation Refinement (`resource_authority.py`)
- **Phase 7.4**: Runtime Resource Enforcement Mapping (cgroups, CUDA stream fences)
- **Phase 7.5**: Distributed Reservation TLA+ Model (`Phase7DistributedReservation.tla`)
- **Phase 7.6**: Resource-Aware Scheduler (`ResourceAwareScheduler` — **STRICTLY BLOCKED by 7.0–7.5**)
