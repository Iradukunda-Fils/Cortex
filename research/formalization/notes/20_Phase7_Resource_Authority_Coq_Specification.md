# Research Note 20: Phase 7.2 Resource Authority Coq Design Specification & Proof Obligations

> **Governance Status**: `NORMATIVE RESEARCH SPECIFICATION`  
> **Baseline Version**: `v1.6.0-VERIFIED`  
> **Date**: August 26, 2026  
> **Repository SHA**: `9ad95fd` (`main`)  
> **Master Directive**: `PHASE 7.2 — COQ RESOURCE AUTHORITY DESIGN SPECIFICATION DIRECTIVE`  
> **Operational System Classification**:  
> $$\boxed{ \text{Phase 5/6 Scalar Load Balancer = Proven Operational Baseline} }$$  
> $$\boxed{ \text{Phase 7.2 Coq Model = Proof Specification Target (`Phase7Reservation.v`)} }$$  
> $$\boxed{ \text{Phase 7.3 Python Refinement = BLOCKED BY 7.2} }$$  
> $$\boxed{ \text{Phase 7.6 Resource-Aware Scheduler = STRICTLY BLOCKED BY 7.1--7.5} }$$

---

## 1. Coq Formal Model Domain & State Definition

The Coq formal model (`Phase7Reservation.v`) models the abstract mathematical contract of the **Cortex Resource Authority**, independently of any Python, Go, Rust, or C-FFI runtime implementation details.

### Minimal State Record (`Record ReservationState`)
```coq
Record ReservationState : Type := {
  active_reservations : list Reservation;
  resource_accounting : ResourceAccountingVector;
  quarantine_state    : QuarantineMap;
  authority_epoch     : Nat;
  lease_epoch         : Map InvocationID Nat;
  worker_generation   : Map WorkerID Nat;
  durable_log_prefix  : List LogFrame
}.
```

$$\boxed{ S_R = \langle R,\ U,\ Q_R,\ E_A,\ E_L,\ G,\ D \rangle }, \qquad Derived_R = f(S_R)$$

---

## 2. Refined Resource Admissibility Predicates

The resource domain $\mathcal{R}$ is formalized as a three-sorted product space $\mathcal{R} = \mathcal{R}_{\text{additive}} \times \mathcal{R}_{\text{rate}} \times \mathcal{R}_{\text{discrete}}$ with explicit time-windowed admissibility:

$$\boxed{ (\mathbf{d}_i, \mathbf{R}_w, t) \models Feasible }$$

### 1. Additive Domain ($r \in \mathcal{R}_{\text{additive}}$)
Memory bytes, VRAM bytes, CPU quota:
$$d_{i, r} \le C_r - U_r$$

### 2. Rate-Based Domain ($r \in \mathcal{R}_{\text{rate}}$)
Storage IOPS, Network bandwidth:
$$\lambda_{i, r} + \Lambda_r^{\text{used}} \le \Lambda_r^{\text{capacity}}$$

### 3. Discrete Partitioning Domain ($g \in \mathcal{R}_{\text{discrete}}$)
GPU physical device indices ($GPU_0, GPU_1$):
$$Owner: GPU\_ID \rightharpoonup ReservationID$$
$$Owner(g) = r \implies \text{ExactlyOne}(r)$$
$$Reserve(r, g) \implies Owner'(g) = r$$
Governed by a discrete device matching/ownership relation rather than scalar arithmetic addition.

---

## 3. Abstract Step Relation (`Inductive ReservationStep`)

Transitions over authoritative state $S_R \xrightarrow{op} S'_R$:

$$\{ Reserve(r), \quad Activate(r), \quad Release(r), \quad Expire(r), \quad Revoke(r), \quad Recover(r) \}$$

### Abstract Linearization Instant ($LP(op)$)
$$\boxed{ LP(op) = \text{the unique abstract instant at which } S_R \text{ undergoes state transition} }$$

$$\boxed{ \forall op_1, op_2,\quad op_1 \neq op_2 \implies LP(op_1) \neq LP(op_2) }$$

---

## 4. Inductive State Invariant & 14 Proof Obligations ($P_1 \dots P_{14}$)

### Inductive Invariant Preservation Theorem
$$\boxed{ Init(S_R) \implies Inv(S_R) }$$
$$\boxed{ Inv(S_R) \land Step(S_R, S'_R) \implies Inv(S'_R) }$$

| Theorem ID | Theorem Identifier | Coq Formal Target | Mathematical Verification Statement |
| :--- | :--- | :--- | :--- |
| **$P_1$** | `ReservationUniqueness` | `Phase7Reservation.v` | $\forall i, \text{InvocationID}(i) \implies \#ActiveReservation(i) \le 1$ |
| **$P_2$** | `ResourceCapacitySafety` | `Phase7Reservation.v` | $\sum_i Reservation_{i,r} \oplus_r Used_r \preceq Capacity_r$ |
| **$P_3$** | `ReservationConservation` | `Phase7Reservation.v` | $StateTransition \implies ResourceInvariant(S'_R)$ |
| **$P_4$** | `ReservationReleaseSafety` | `Phase7Reservation.v` | $Release(i) \implies Reserved'_r = Reserved_r - \mathbf{d}_{i,r}$ |
| **$P_5$** | `ExpiryReclamationSafety` | `Phase7Reservation.v` | $Expired(r) \implies r \notin ActiveReservations \land Reserved'_r = 0$ |
| **$P_6$** | `AuthorityFencing` | `Phase7Reservation.v` | $Authority(r) \neq E_A \implies Commit(r) = \text{REJECT}$ |
| **$P_7$** | `IncarnationFencing` | `Phase7Reservation.v` | Stale worker incarnation $G_w \neq G_{\text{active}}$ cannot commit reservation |
| **$P_8$** | `PlacementFeasibility` | `Phase7Reservation.v` | $Placement(i) = w \implies (\mathbf{d}_i, \mathbf{R}_w, t) \models Feasible$ |
| **$P_9$** | `TelemetryConservativeBound` | `Phase7Reservation.v` | $E_r^{\text{uncertainty}} \ge \epsilon_r + \Delta_{\max} \cdot \left|\frac{dReal}{dt}\right|_{\max} \implies C^{\text{sched}}_r \le C^{\text{real}}_r$ |
| **$P_{10}$** | `DurableReservationReplay` | `Phase7Reservation.v` | $\boxed{ Replay(ValidPrefix(D)) = S'_{\text{reservation}} \land Invariant(S'_{\text{reservation}}) }$ |
| **$P_{11}$** | `ReservationNonOverlap` | `Phase7Reservation.v` | $\boxed{ r_1 \neq r_2 \land Active(r_1) \land Active(r_2) \implies Compatible(d_{r_1}, d_{r_2}) }$ |
| **$P_{12}$** | `ReservationIdentityStability`| `Phase7Reservation.v` | $\boxed{ Active(r) \implies ID(r) = \text{constant} }$ |
| **$P_{13}$** | `TerminalReclamation` | `Phase7Reservation.v` | $\boxed{ Terminal(r) \implies Reserved(r) = 0 }$ |
| **$P_{14}$** | `FencingMonotonicity` | `Phase7Reservation.v` | Transition-Specific: $\text{Reserve/Reassign: } e'_L(i) > e_L(i); \quad \text{Authority: } e'_A > e_A; \quad \text{Terminal: } e'_A=e_A, e'_L=e_L$ |


---

## 5. Conceptual Subsystem Dependency Graph

```
                  7.1 Semantics (Research Notes 18 & 19)
                                    │
                                    ▼
           7.2 Coq Safety Model (Phase7Reservation.v Specification)
                                    │
                                    ▼
       7.3 Python Refinement (resource_authority.py R(C_Python, A_Coq))
                                    │
                                    ▼
           7.4 OS/GPU Runtime Enforcement Mapping Research
                                    ├──────────────────────────────┐
                                    ▼                              ▼
              7.5 TLA+ Distributed Model    Resource Stress Testing
                                    └──────────────┬───────────────┘
                                                   ▼
                       7.6 Resource-Aware Scheduler (STRICTLY BLOCKED)
```

---

## 6. Mathematical Correspondence Gate

Before writing any Python code for `resource_authority.py`, the system must satisfy the 4-way correspondence gate:

$$\boxed{ \text{Research 18} \leftrightarrow \text{Research 19} \leftrightarrow \text{Research 20 (Coq Definitions)} \leftrightarrow \text{Proof Obligations } (P_1 \dots P_{14}) }$$
