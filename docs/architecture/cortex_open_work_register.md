# Cortex Open Work Register
**Authoritative Remaining Engineering Obligations & Backlog Ledger**  
**Date:** August 26, 2026  
**Repository Baseline SHA:** `9ad95fd` (`main`)

---

## Authoritative Assurance Hierarchy
$$\boxed{ \text{Safety} > \text{Formal Assurance} > \text{Resource Bounds} > \text{Determinism} > \text{Scalability} > \text{Performance} }$$

---

## Open Work Priority Ranking

$$\boxed{ \#23 > \#33 > \#36 > \#32 > \#35 > \#37 > \#19 }$$

| Priority Rank | Work ID | Description | Source | Issue | Priority | Security Impact | Formal Impact | Target Release | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **OPEN-003** | External Security Review & P0-P13 Production Readiness | Security Plan | #23 | CRITICAL | Critical (Production Sign-off) | High (Full Matrix P1..P4) | `v1.0.0` | `OPEN_REQUIRED` |
| **2** | **OPEN-006** | Finalize WASM Profile B Sandbox Filters & Test Matrix | DEBT-006 | #33 | HIGH | High (Sandbox Isolation) | Medium (Gate G bounds) | `v0.5.0-experimental` | `OPEN_REQUIRED` |
| **3** | **OPEN-009** | Gate J 13-Class Property-Based Fuzzing Engine | DEBT-008 | #36 | HIGH | High (Adversarial Fuzzing) | High (Independent Verifier) | `v0.5.0-experimental` | `OPEN_REQUIRED` |
| **4** | **OPEN-005** | Concrete-to-Coq Forward Simulation Refinement Relation | DEBT-005 | #32 | HIGH | High (Code-to-Proof Soundness) | Critical (Bridge Python -> Coq) | `v0.5.0-experimental` | `OPEN_REQUIRED` |
| **5** | **OPEN-008** | Resolve 222 Hyperlink and Formatting Documentation Warnings | DEBT-007 | #35 | LOW | Low (Developer Experience) | Low (Documentation Integrity) | Backlog | `OPEN_REQUIRED` |
| **6** | **OPEN-010** | Yosys Open-Source Synthesis Gate Check for STCR Pipeline | DEBT-009 | #37 | MEDIUM | High (Hardware Conformance) | Medium (RTL AST Verification) | `v0.5.0-experimental` | `OPEN_REQUIRED` |
| **7** | **OPEN-011** | Newcomer Contribution Path & Onboarding Documentation | Community | #19 | LOW | Low (Community Growth) | Low | Backlog | `OPEN_OPTIONAL` |

---

---

## Universal Resource Control & Vector Reservation Philosophy

Every resource managed or verified within Cortex enforces five control properties:

$$\boxed{ \text{Bound} + \text{Admission} + \text{Backpressure} + \text{Recovery} + \text{Telemetry} }$$

### Schedulable Available Capacity & Telemetry Uncertainty
$$\boxed{ C^{\text{sched}}_r = C^{\text{physical}}_r - U^{\text{observed}}_r - R^{\text{reserved}}_r - M^{\text{safety}}_r - E^{\text{uncertainty}}_r }$$

### Explicit Atomic Reservation Semantics
$$\boxed{ \text{Reservation} = \langle \text{InvocationID}, \text{AttemptID}, \text{WorkerID}, \mathbf{d}_i, \text{AuthorityEpoch}, \text{LeaseEpoch}, \text{Generation}, \text{Expiry} \rangle }$$

$$\boxed{ \mathbf{d}_i \preceq C_w^{\text{sched}} \implies Available'_w = Available_w - \mathbf{d}_i \quad \land \quad Reserved'_w = Reserved_w + \mathbf{d}_i }$$

### Generalized Resource Algebra ($\oplus_r$)
$$\boxed{ Used_r \oplus_r Reserved_r \preceq Capacity_r }$$

---

## Phase 7.0 — Resource Authority Formalization Gate Sequence

Prior to implementing the Phase 7 `ResourceAwareScheduler`, Cortex mandates execution of the formal reservation sequence:

$$\boxed{ \text{Phase 7.0 — Resource Authority Formalization Gate} }$$

$$\boxed{ \text{Resource Algebra} \rightarrow \text{Reservation FSM} \rightarrow \text{Linearization} \rightarrow \text{Coq Proof} \rightarrow \text{Concrete Refinement} \rightarrow \text{Enforcement} \rightarrow \text{Stress} \rightarrow \text{TLA+ Model} }$$

### Minimal Authoritative Reservation State ($S_R$) & Total Order Linearization Point
$$\boxed{ S_R = \langle R,\ U,\ Q_R,\ E_A,\ E_L,\ G,\ D \rangle }, \qquad Derived_R = f(S_R)$$

$$LP(Reserve) = \text{atomic compare-and-commit of authoritative reservation state } S_R$$

$$\boxed{ \forall r_1, r_2,\quad r_1 \neq r_2 \implies LP(r_1) \neq LP(r_2) }$$

$$\boxed{ \sum_{r \in ActiveReservations} d_{r, k} + Used_k \le Capacity_k - M^{\text{safety}}_k - E^{\text{uncertainty}}_k }$$

$$\boxed{ \text{Hardware} \rightarrow \text{Observation} \rightarrow \text{Authority} \rightarrow \text{Reservation} \rightarrow \text{Enforcement} \rightarrow \text{Execution} }$$

### Formal Proof Obligations ($P_1 \dots P_{14}$)
- **$P_1$**: `TwoDimensionalUniqueness` ($\forall i, \text{InvocationID}(i) \implies \#Active(i) \le 1 \land \forall a, \text{AttemptID}(a) \implies \#Active(a) \le 1$)
- **$P_2$**: `ResourceCapacitySafety` ($\sum_i Reservation_{i,r} \oplus_r Used_r \preceq Capacity_r$)
- **$P_3$**: `ReservationConservation` ($StateTransition \implies ResourceInvariant(S'_R)$)
- **$P_4$**: `ReleaseAccountingEquivalence` ($Release(i) \implies Reserved'_r = Reserved_r - \mathbf{d}_{i,r}$)
- **$P_5$**: `ExpiryReclamationSafety` ($Expired(r) \implies r \notin ActiveReservations \land Reserved'_r = 0$)
- **$P_6/P_7$**: `InvalidFencingRejection` ($\neg ValidFencing(s, r) \implies Step(s, OpReserve(r), s') = \text{REJECT}$)
- **$P_8$**: `PlacementFeasibility` ($Placement(i) = w \implies (\mathbf{d}_i, \mathbf{R}_w, t) \models Feasible$)
- **$P_9$**: `TelemetryConservativeBound` ($obs_r \le obs_r + \epsilon_r + \Delta_{\max} V_{\max}$)
- **$P_{10}$**: `DurableReplayNonResurrection` ($\boxed{ Replay(D) = Replay(D) \land Terminal(r) \implies r \notin Active(Replay(D)) }$)
- **$P_{11}$**: `GPUOwnershipSingleOwner` ($\boxed{ \forall g, |\{r : Owner(g)=r \land Active(r)\}| \le 1 }$)
- **$P_{12}$**: `ReservationIdentityStability` ($\boxed{ Active(r) \implies ID(r) = \text{constant} }$)
- **$P_{13}$**: `TerminalReclamation` ($\boxed{ Status(r) \in \{RELEASED, EXPIRED, REVOKED\} \implies DemandContribution(r) = 0 }$)
- **$P_{14}$**: `TransitionFencingMonotonicity` (Transition-Specific: $\text{Reserve: } e'_L(i) > e_L(i); \quad \text{Authority: } e'_A > e_A; \quad \text{Terminal: } e'_A=e_A, e'_L=e_L$)

---

## Phase 7 Phase Structure & Execution Roadmap (7.0–7.6)

- **Phase 7.0**: Resource Algebra Specification (`Research Note 18`) — **CLOSED**
- **Phase 7.1**: Reservation FSM & Linearization Semantics (`Research Note 19`) — **CLOSED**
- **Phase 7.2**: Reservation Coq Safety Model (`Research Note 20` / `Phase7Reservation.v` — **CLOSED / MACHINE-CHECKED PROVEN (0 Axioms, 0 Admits)**)
- **Phase 7.3**: Concrete Heterogeneous Resource Vector Engine (`resource_authority.py` `DemandVector` algebra, unit normalization, Gate A contract derivation — **CLOSED / IMPLEMENTATION-VERIFIED**)
- **Phase 7.3a**: Integration Closure & Physical Reuse Safety Gate (`Research Note 22`, 12-scenario test matrix, Gate A reuse safety equivalence — **CLOSED / ADVERSARIALLY & RUNTIME-VERIFIED**)
- **Phase 7.4**: Distributed Reservation Authority TLA+ Model (`Phase7DistributedReservation.tla`, 6M+ states verified — **CLOSED / MODEL-CHECKED**)
- **Phase 7.5**: Enforcement Composition Gate (`test_phase7_5_enforcement_composition_gate.py`, 5 composition scenarios — **CLOSED / RUNTIME-VERIFIED & ADVERSARIALLY TESTED**)
- **Phase 7.6**: Resource-Aware Scheduler (`ResourceAwareScheduler`, $Feasible(i,w)$ predicate, placement cost optimization, atomic `ResourceAuthority.reserve()` integration, telemetry separation — **CLOSED / RUNTIME-VERIFIED & BENCHMARKED**)
- **Phase 7.7a**: Heterogeneous Distributed Placement Model (`distributed_scheduler.py`, global identities, multi-node fragmentation, locality, stale-read retry — **CLOSED / RUNTIME-VERIFIED & BENCHMARKED (LOGICAL SIMULATION)**)
- **Phase 7.7b**: Autoscaling Policy/Decision Engine (`autoscaler.py`, control loop, scale-up/down safety, quiescence retirable checks, hysteresis — **CLOSED / RUNTIME-VERIFIED & ADVERSARIALLY TESTED**)
- **Phase 8.0**: Formal Machine-Checked Simulation & Refinement Proofs ($Python \rightarrow Coq$) — **ACTIVE NEXT GATE**
  - **Obligation 1**: $R_{\text{Phase4}}(C_{\text{Python}}, A_{\text{Coq}})$ Gateway Refinement (Issue #32) — `PROOF TARGET / OPEN` (Layer 3 Isolated)
  - **Obligation 2**: Formal Concrete Transition Semantics $C_{\text{formal}}$ (Issue #52) — ✅ `MODEL-CHECKED / IMPLEMENTED` (`Phase8ResourceAuthorityConcrete.v`)
  - **Obligation 3**: Vector-to-Scalar Projection Soundness Audit $\alpha_{\text{vector}\to\text{scalar}}$ (Issue #53) — ✅ `MODEL-CHECKED / IMPLEMENTED` (`Phase8ResourceAuthorityConcrete.v` Section 6)
  - **Obligation 4**: `StepExpire` Abstract Transition & Reclamation Model (Issue #54) — `MODEL GAP / OPEN` (`phase8_0_model_extensions_expire_revoke.md`)
  - **Obligation 5**: `StepRevoke` Abstract Transition & Fencing Model (Issue #55) — `MODEL GAP / OPEN` (`phase8_0_model_extensions_expire_revoke.md`)
  - **Obligation 6**: Initial State Correspondence Theorem $\alpha(C_0) = A_0$ (Issue #57) — ✅ `MODEL-CHECKED / IMPLEMENTED` (`Phase8ResourceAuthorityConcrete.v` `initial_state_refinement`)
  - **Obligation 7**: Forward Simulation Step Preservation for Reserve/Release (Issue #58) — `PROOF TARGET / OPEN` (Requires #52, #53, #54, #55, #57)
  - **Obligation 8**: WAL Durable Prefix Refinement Theorem $D'$ (Issue #56) — `PROOF TARGET / OPEN` (Requires #58)

---


## Cortex Resource Authority & System Assurance Ladder

The **Cortex Resource Authority** sits between physical telemetry observation and scheduler consumers:

$$\boxed{ \text{Telemetry} \neq \text{Authority} }$$

### System Assurance Ladder (Current Implementation)

| Layer | Language | Current Role | Assurance |
| :--- | :--- | :--- | :--- |
| Coq (Rocq) | — | Local mathematical safety & conservation laws | Machine-checked (0 axioms, 0 admits) |
| TLA+ | — | Distributed authority, epoch fencing & liveness | Model-checked (6M+ states) |
| Python Kernel | Python | Live authoritative state control plane ($S_A$), plugins, routing, scheduling | Runtime-verified (562 tests) |
| `cortex-go/cbe` | Go | CBE encode/decode codec | Conformance-verified |
| `cortex-go/adapter` | Go | Stateless CBE primitives (Encode, Decode, Hash, UUID) | Implemented |
| `cortex-emulator` | Rust | RISC-V hardware emulator & CBE codec | Implemented |
| Linux / NVML | — | Physical resource observation (non-authoritative) | Telemetry |

### Substrate Capability Classification

| Component | Current Status | What It Does NOT Do |
| :--- | :--- | :--- |
| Go CBE codec | `IMPLEMENTED` | No networking, no plugin routing, no event delivery |
| Go cross-node transport | `OPEN` | Not implemented |
| Go distributed execution | `OPEN` | Not implemented |
| Rust distributed execution | `OPEN` | Not implemented |

### Future Architecture (Not Yet Implemented)

$$\text{Python Authority} \rightarrow \text{Go/Rust Transport Substrate} \rightarrow \text{Execution}$$

---

## External Effects Subsystem Gate Sequence (B.1–B.4)

$$\boxed{ \text{Gate B.1 (CLOSED)} \rightarrow \text{Gate B.3 (CLOSED)} \rightarrow \text{Gate B.2 (CLOSED)} \rightarrow \text{Gate B.4 (CLOSED / RUNTIME-VERIFIED)} }$$

$$\boxed{ \text{Worker has intent} \quad \text{Authority decides} \quad \text{Kernel enforces} \quad \text{Adapter executes} }$$

- **Sub-Gate B.1**: Local MCP Effect Composition & Authorization Gate — **CLOSED (PASS)**
- **Sub-Gate B.3.0**: Local Restart & Cross-Process Fencing (`gateway_reconciliation.py`, `effect_wal.py`) — **CLOSED (LOCAL RESTART / CROSS-PROCESS FENCING)**
- **Sub-Gate B.3.1**: Durability & Throughput Benchmarking — **CLOSED (NO CHANGE REQUIRED / EMPIRICALLY MEASURED)**
- **Sub-Gate B.2**: Physical Network Isolation via Linux `unshare(CLONE_NEWUSER | CLONE_NEWNET)` (`netns.py`, `supervisor.py`) — **CLOSED (PHYSICAL DEFAULT-DENY NETWORK ISOLATION: $NetNS(worker) \neq NetNS(host)$)**
- **Sub-Gate B.4**: Landlock LSM Kernel Enforcement in Rust `sandbox.rs` — **CLOSED (FAIL-CLOSED FILESYSTEM CONTAINMENT & PR_SET_NO_NEW_PRIVS)**
- **Sub-Gate B.2.4**: Controlled External Egress Destination Policy — **FUTURE / DEFERRED**
- **Sub-Gate B.3.4**: Cross-Node Distributed Ownership & Fencing — **FUTURE / DEFERRED**




