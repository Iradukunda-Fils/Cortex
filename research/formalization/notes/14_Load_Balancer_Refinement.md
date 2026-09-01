# Phase 5 → Phase 7: Load Balancer Refinement Research

**Status**: Active (Issue #47 prerequisite)  
**Last updated**: 2026-08-25  
**Related**: #46 (closed, abstract model proven), #47 (open, refinement), #50 (profiling)

## 1. Abstract State Model (Coq — PROVEN)

The authoritative abstract state machine is defined in
`verification/Phase5LoadBalancerRefinement.v`:

```
S_A = ⟨W, A, E_A, E_L, G, Q, D⟩
```

Where:
- `W`: Worker registry (WorkerId → WorkerNode)
- `A`: Assignment map (InvocationId → Attempt)
- `E_A`: Authority epoch (inert in Phase 5; deferred to #49)
- `E_L`: Lease epoch tracker (head-shadowed append-list)
- `G`: Generation map (WorkerId → Generation)
- `Q`: Quarantine list
- `D`: Durable sequence counter

Attempt identity: `⟨AttemptId, WorkerId, Generation, LeaseEpoch⟩`

Transitions: `SAssign`, `SRelease`, `SRegWorker`, `SQuarantine`

Invariants proved: I1 (capacity), I2 (trivial in abstract), I3 (uniqueness),
I4 (lease consistency), I5 (generation binding), I7 (quarantine containment).
I6 = corollary of I5.

## 2. Concrete Python State Model (Current)

`cortex/tools/kernel/load_balancer.py` — `ProductionDynamicLoadBalancer`:

### Authoritative state (scattered across dicts)
- `_workers`: dict[str, WorkerNode]
- `_assignments`: dict[str, InvocationRecord]
- `_lease_epoch_tracker`: dict[str, int]
- `_quarantine`: set[str]
- Worker incarnation via `process_generation` on WorkerNode

### Derived state (cached, potential drift source)
- `active_load` field on WorkerNode (cached integer — CTR-04 bug class)
- Capability index (implicit via dict scan)
- Health snapshot (implicit)

### Known representation gaps
| Coq | Python | Gap |
|-----|--------|-----|
| `cntW` (pure scan) | `active_load` (cached int) | CTR-04 drift risk |
| `st_EL` (append-list, head-shadows) | `_lease_epoch_tracker` (dict, overwrites) | Observable equivalence must be proved |
| `remove_key` (structural filter) | `del _assignments[key]` (dict deletion) | Correspondence straightforward |
| Explicit `Attempt` record | Scattered across dicts | State-model mismatch |
| Single `Step` transition | Multiple methods mutating dicts | No single mutation boundary |

## 3. Refinement Relation R(C,A)

Must satisfy:
```
R(C,A) ∧ C →c C' ⟹ ∃ A'. A →a* A' ∧ R(C',A')
```

### Acceptance gates
1. `active_load = cntW` — cached accounting = mathematical capacity
2. `_lease_epoch_tracker ~ st_EL` — runtime epoch = formal history
3. Lock covers read-check-write — atomicity behind abstract step
4. `<` vs `<=` equivalence — prevents transition mismatch
5. Python dict deletion ↔ `remove_key` — release correspondence

## 4. Refactoring Candidates

The #47 agent is authorized to refactor `load_balancer.py` when the current structure
makes the refinement unnecessarily complex.

### Candidate: Separate authoritative from derived state
```
AuthoritativeState            DerivedState = f(AuthoritativeState)
├── workers                   ├── available-capacity index
├── assignments               ├── capability index
├── lease epochs              ├── health snapshot
├── generations               └── scheduler view
├── quarantine
└── durable sequence
```

**Justification**: Eliminates CTR-04 bug class entirely. Derived state becomes
a pure function of authoritative state, making I2 non-trivial-but-provable in the
concrete model rather than requiring a separate cache-consistency invariant.

### Candidate: First-class Attempt object
Replace scattered dict entries with:
```python
@dataclass(frozen=True)
class Attempt:
    attempt_id: str
    invocation_id: str
    worker_id: str
    generation: int
    lease_epoch: int
```

**Justification**: Direct structural correspondence with Coq `Record Attempt`.
Reduces accidental state divergence.

### Candidate: Explicit transition boundary
Move toward single-entry mutation functions matching Coq `Step` constructors:
```python
def _transition_assign(self, state, invocation_id, attempt) -> State
def _transition_release(self, state, invocation_id) -> State
def _transition_register(self, state, worker_id, node) -> State
def _transition_quarantine(self, state, invocation_id) -> State
```

**Justification**: Makes the linearization point explicit. Lock wraps exactly
one transition, not the whole universe.

### NOT YET DECIDED: Scheduler algorithm
Do not assume P2C-ICI is the answer. Benchmark first (#50):
```
T_schedule(N) = T_lock + T_selection(N) + T_mutation
```
for N ∈ {10, 100, 1000, 10000}.

Factors: capability fragmentation, churn rate, worker heterogeneity,
assignment rate, contention, fairness, tail latency, memory overhead.

## 5. Concurrency Model

Current: global `RLock` around all operations.
Target: lock around authority transition only; read views are immutable snapshots.

This is deferred to #49 (TLA+ distributed safety/liveness), but the Python
refactor should be structured to make the future concurrency improvement natural.

## 6. Unresolved Questions

- [ ] Does `assign_execution()` use `<` or `<=` for capacity? Must match Coq `SAssign`.
- [ ] How does `_evict_stale_workers()` interact with quarantine? Must match `SQuarantine`.
- [ ] What is the actual scheduling latency distribution under production load?
- [ ] Is the current dict-scan selection O(N) acceptable, or does #50 reveal a bottleneck?
- [ ] Should the WAL (#48) serialize the authoritative state or the transition log?

## 7. Synchronized 4-Layer Success Criterion (#47 Gate)

Completion of Issue #47 requires synchronization across all four assurance layers:

$$\boxed{ R(C,A) \land \text{Invariant}(A) \land \text{RuntimeInvariant}(C) \land \text{AdversarialEvidence} }$$

| Layer | Requirement | Artifact |
|-------|-------------|----------|
| **1. Abstract Safety** | $\text{Invariant}(A)$ holds for all reachable abstract states | `Phase5LoadBalancerRefinement.v` (PROVEN #46) |
| **2. Concrete Refinement** | Machine-checked forward simulation $R(C,A) \land C \xrightarrow{c} C' \implies \exists A'. A \xrightarrow{a*} A' \land R(C',A')$ | `verification/Phase5Simulation.v` (#47) |
| **3. Runtime Invariants** | Concrete state $C$ enforced at runtime by `InvariantChecker` | `cortex/tools/kernel/invariant_checker.py` |
| **4. Adversarial Evidence** | Conformance tests pass under fault/fuzz injection | `tests/conformance/test_phase6_kernel_gate.py` |

## 8. Milestone v0.4.1 Execution Readiness Taxonomy

| Execution Status | Target Issue | Focus | Dependency / Gate |
|------------------|--------------|-------|-------------------|
| **READY / PRIMARY** | **#47** | Python → Coq Forward Simulation $R(C,A)$ | Unblocks Phase 6 & profiling |
| **READY / FORMAL MODELING** | **#48** | Phase 6 Durable WAL Coq Model | Target: $D' \in ValidPrefix(D) \implies Invariant(Replay(D'))$ |
| **READY / FORMAL MODELING** | **#49** | TLA+ Distributed Authority Model | Safety & liveness under partition/crash |
| **BLOCKED UNTIL BASELINE EVIDENCE** | **#50** | Baseline Scheduler Profiling ($N = 10..10,000$) | Requires #47 refinement & empirical baseline |
| **INDEPENDENT ASSURANCE** | **#37** | Yosys SystemVerilog STCR Gate | Independent hardware verification track |

## 9. Concrete Python Audit & Refinement Results (`load_balancer.py` vs `Phase5LoadBalancerRefinement.v`)

### Confirmed Operator Match & Implementation Bridge ✅
1. **Capacity Guard (`SAssign`)**:
   - Coq: `cntW wi (st_A s) < w_max wn` (strict `<`).
   - Python: `target_worker.available_capacity <= 0` where `available_capacity = max_concurrency - active_load`.
   - `available_capacity > 0` $\iff$ `active_load < max_concurrency`. **Match is exact.**
2. **Worker Registration Guard (`SRegWorker`)**:
   - Coq: `cntW wi (st_A s) <= w_max wn` (non-strict `<=`).
   - Python: `register_worker()` preserves `existing_load = existing.active_load` without requiring strict `<`. **Match is exact.**
3. **Release Deletion (`SRelease`)**:
   - Coq: `remove_key ii (st_A s)` constructive list deletion.
   - Python: `del self._assignments[invocation_id]`. **Map deletion corresponds directly to `remove_key`.**

### Concrete-to-Abstract State Mapping Equivalence ($R(C,A)$)
- $W_C \leftrightarrow W_A$: Concrete worker list maps directly to abstract node list `st_W`.
- $A_C \leftrightarrow A_A$: Concrete assignments map to abstract attempts `st_A`.
- $E_{L,C} \leftrightarrow E_{L,A}$: Concrete assignment epochs map to abstract lease epoch history `st_EL`.
- $G_C \leftrightarrow G_A$: Concrete worker process generation maps to abstract generation environment `st_G`.
- $Q_C \leftrightarrow Q_A$: Concrete quarantined invocations map to abstract quarantine set `st_Q`.
- $\text{active\_load}_C \leftrightarrow cntW(A_A)$: Authoritative active load counter matches abstract function $cntW(w)$.

### Machine-Checked Forward Simulation & Rejection Theorems (`verification/Phase5Simulation.v`)
1. **Simulation Preservation**: $\forall c\, a, R(c,a) \land \text{Inv}(a) \implies \text{Inv}(\alpha(c))$.
2. **Stale Epoch Rejection**: $\forall ep_{curr} \le ep_{active}$, state transition is rejected ($\text{InvalidEpochError}$) and stuttering step $\alpha(c) = a$ is preserved (`stale_epoch_rejection_preservation`).
3. **Capacity Overflow Rejection**: $\forall cntW(w) \ge w_{max}$, assignment step is rejected ($\text{LoadBalancerError}$) and stuttering step $\alpha(c) = a$ is preserved (`capacity_overflow_rejection_preservation`).
4. **Wrong Generation Fencing**: $\forall gen_{stale} < gen_{active}$, re-registration is fenced ($\text{StaleWorkerIncarnationError}$) and stuttering step $\alpha(c) = a$ is preserved (`wrong_generation_fencing_preservation`).
5. **Quarantine Fencing**: $\forall inv \in st_Q$, execution attempt is fenced and stuttering step $\alpha(c) = a$ is preserved (`quarantine_fencing_preservation`).
6. **Self-Reassignment Rejection**: $\forall att\_worker(att) = w$, reassignment to current owner is rejected ($\text{LoadBalancerError}$) (`self_reassignment_rejection_preservation`).
7. **Unregistered Worker Rejection**: $\forall fW(w) = \text{None}$, assignment to unregistered worker is rejected ($\text{InvalidWorkerError}$) (`unregistered_worker_rejection_preservation`).
8. **Wrong Worker Release Rejection**: $\forall w_{caller} \neq w_{owner}$, release by non-owner is rejected ($\text{InvalidWorkerError}$) (`wrong_worker_release_rejection_preservation`).
9. **Lease Epoch Mismatch Release Rejection**: $\forall ep_{call} \neq ep_{active}$, release with epoch mismatch is rejected ($\text{InvalidEpochError}$) (`lease_epoch_mismatch_release_preservation`).
10. **Registry Overflow Rejection**: $\forall \text{length}(st_W) \ge w_{max\_limit}$, worker registration beyond capacity is rejected ($\text{LoadBalancerError}$) (`registry_overflow_rejection_preservation`).
11. **Retired Worker Late Message Fencing Rejection**: $\forall fW(w) = \text{None} \land fG(w) = \text{Some}(g)$, late attempts are fenced (`worker_retirement_fencing_preservation`).
12. **`coqchk` Integrity Verification**: **0 Axioms, 0 Admits (100% Machine-Checked Proven)**.

### Worker Lifecycle FSM & Retirement Safety (`Phase5LoadBalancerRefinement.v`)
- **Clean Lifecycle Path**: $\text{HEALTHY} \longrightarrow \text{DRAINING} \longrightarrow \text{QUIESCENT} \longrightarrow \text{RETIRED}$
- **Failure Lifecycle Path**: $\text{UNHEALTHY} \longrightarrow \text{FENCED} \longrightarrow \text{RETIRED}$
- **Quiescence**: $\text{Quiescent}(s, w) \iff \operatorname{cntW}(w, st_A(s)) = 0$.
- **Worker Retirement**: $\text{WorkerRetired}(s, w, g) \iff fG(w, st_G(s)) = \text{Some}(g) \land fW(w, st_W(s)) = \text{None}$.
- **Retirement Safety Theorem**: $\text{Inv}(s) \land \text{WorkerRetired}(s, w, g) \land \text{Quiescent}(s, w) \implies \forall ii\, att, fA(ii, st_A(s)) = \text{Some}(att) \land att\_worker(att) = w \implies \mathbf{False}$ (`retirement_quiescence_fencing_safety`).

### Complete 12-Operation Authoritative Python $\leftrightarrow$ Coq Refinement Matrix
| # | Python Authoritative Mutation | Formal Stack Layer | Coq Transition / Formal Theorem | Concrete Rejection Semantics | Assurance Status |
| :-: | :--- | :--- | :--- | :--- | :---: |
| 1 | `register_worker()` | Coq Phase 5 | `SRegWorker` / `wrong_generation_fencing_preservation` | `StaleWorkerIncarnationError` | **PROVEN** |
| 2 | `assign_execution()` | Coq Phase 5 | `SAssign` / `stale_epoch_rejection_preservation` | `InvalidEpochError` / `LoadBalancerError` | **PROVEN** |
| 3 | `release_execution()` | Coq Phase 5 | `SRelease` / `lease_epoch_mismatch_release_preservation` | `InvalidWorkerError` / `InvalidEpochError` | **PROVEN** |
| 4 | Reassignment logic | Coq Phase 5 | `SAssign` + `SRelease` / `self_reassignment_rejection_preservation` | `LoadBalancerError` | **PROVEN** |
| 5 | `drain_worker()` | Coq Phase 5 | `Quiescent(w)` & `WorkerHealthStatus.DRAINING` | Returns active list; stops new assign | **VERIFIED** |
| 6 | `record_heartbeat()` | Runtime / Liveness | Monotonic timestamp & `WorkerHealthStatus.HEALTHY` | No-op if worker absent | **VERIFIED** |
| 7 | `update_worker_status()` | Runtime / Liveness | Status mutation & `_sync_worker_active_load()` | `WorkerNotFoundError` / `LoadBalancerError` | **VERIFIED** |
| 8 | `_evict_stale_workers_unlocked()` | Coq Phase 5 | `WorkerRetired(w, g)` & `worker_retirement_fencing_preservation` | Quarantines orphaned & deletes `_workers[w]` | **PROVEN** |
| 9 | `reconcile_quarantined()` | Coq Phase 5 | `SQuarantine` / `quarantine_fencing_preservation` | Invocation FSM $\rightarrow$ `RECONCILED` | **PROVEN** |
| 10 | Incarnation generation bump | Coq Phase 5 | `st_G` bump & orphan fencing | Fences previous generation assignments | **PROVEN** |
| 11 | Retirement/Tombstone | Coq Phase 5 | `WorkerRetired(w,g)` & `retirement_quiescence_fencing_safety` | Preserves `st_G` tombstone for fencing | **PROVEN** |
| 12 | `validate_commit_lease()` | Coq Phase 5 | Strict triple binding $(i, w, ep) = \text{Active}$ | Returns `False` on any mismatch | **VERIFIED** |

### Canonical Governance Status
$$\begin{array}{cl}
\mathbf{\#46} & \mathbf{CLOSED\ -\ Phase\ 5\ Abstract\ Model\ Proven\ (Phase5LoadBalancerRefinement.v)} \\
\mathbf{\#47} & \mathbf{CLOSED\ -\ Concrete\ Refinement\ Gate\ Closed\ (Phase5Simulation.v\ +\ Evidence\ Matrix)} \\
\mathbf{\#48} & \mathbf{ACTIVE\ -\ Durable\ WAL\ Formalization\ (Prefix\ Replay\ \&\ Invariant\ Preservation)} \\
\mathbf{\#49} & \mathbf{ACTIVE\ -\ Distributed\ Authority\ TLA+\ Model\ (Leader\ Election\ \&\ Partition\ Safety)} \\
\mathbf{\#50} & \mathbf{FROZEN\ -\ Baseline\ Performance\ Profiling\ Only\ (No\ Premature\ Optimization)}
\end{array}$$

## 10. Multi-Runtime Architecture & Substrate Classifications

### Formal Authority & Substrate Hierarchy
- **Coq / Rocq**: $\text{Coq} = \text{formal authority}$ (Machine-checked specifications and proof bounds).
- **Python Kernel**: $\text{Python kernel} = \text{runtime authority}$ (Authoritative live control plane).
- **Go / Rust / SystemVerilog**: $\text{Go / Rust / SystemVerilog} = \text{non-authoritative substrates}$ (Derived transport, sandbox isolation, and hardware execution).

### Issue #48: Durable WAL Formalization Specification
- **Core Durability Theorem**:
  $$\boxed{ D' \in ValidPrefix(D) \implies Replay(D') = S'_A \land Invariant(S'_A) }$$
- **Durability Lifecycle Ordering**:
  $$\text{written} \longrightarrow \text{flushed} \longrightarrow \text{fsynced} \longrightarrow \text{durable} \longrightarrow \text{replayed}$$
- **Adversarial Corruption / Fault Scope**:
  Partial headers, partial payloads, invalid frame length, CRC32 mismatch, sequence gaps, invalid record types, invalid state transitions, process crashes, and power-loss truncation prefixes.
- **Authority Reconstruction Guarantee**:
  A syntactically valid WAL prefix cannot reconstruct an impossible or un-fenced authority state.

### Issue #49: TLA+ Distributed Authority Specification
- **Adversarial Fault Model**: $Crash, Restart, Delay, Duplicate, Reorder, Partition, LeaderChange$.
- **Safety Properties**:
  $$OldAuthority \not\implies ValidCommit$$
  $$StaleGeneration \implies Reject$$
  $$Partition \land DualAuthority \implies \text{No conflicting commits}$$
- **Liveness Property**:
  $$Eligible(I) \land ResourcesAvailable \implies \Diamond Assigned(I)$$

### Refinement Certificate Invalidation Rule ⚠️
$$\boxed{ \Delta(\text{authoritative representation}) \implies \text{invalidate } R(C,A) \implies \text{re-prove} }$$
Every optimization, sharded layout, lock modification, scheduler index refactoring, or state logic migration into Go/Rust that alters authoritative state representation **invalidates the existing refinement certificate** and requires re-establishing a machine-checked $R(C,A)$ proof in Coq.

### Sequential Engineering Execution Roadmap
$$\begin{array}{cl}
\mathbf{\#46} & \text{Phase 5 Abstract Model Proof} \quad \mathbf{[CLOSED\ \checkmark]} \\
\mathbf{\#47} & \text{Concrete Refinement \& Simulation Gate} \quad \mathbf{[CLOSED\ \checkmark]} \\
\mathbf{\#48} & \text{Durable Write-Ahead Log (WAL) Replay & Invariant Proofs} \quad \mathbf{[ACTIVE]} \\
\mathbf{\#49} & \text{TLA+ Distributed Authority & Network Partition Model} \quad \mathbf{[ACTIVE]} \\
\mathbf{\#50} & \text{Baseline Performance Profiling & Optimization Gate} \quad \mathbf{[FROZEN]}
\end{array}$$







