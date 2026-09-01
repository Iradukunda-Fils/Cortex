# Cortex Scheduler Concurrency, Authority Scalability & Safe Refactoring Gate

> **Governance Directive**: $\text{Measure} \longrightarrow \text{Inspect} \longrightarrow \text{Model} \longrightarrow \text{Compare} \longrightarrow \text{Plan} \longrightarrow \text{Only then Refactor}$  
> **Core Objective**: Determine the smallest safe architectural change that enables 10×–100× scale while strictly preserving Cortex single-source-of-truth semantics.  
> **North Star Equation**: $\boxed{ \text{One Authority} + \text{Measured Concurrency} + \text{Bounded Resources} + \text{Safe Evolution} + \text{Stable Developer Contract} }$  

---

## 1. Cardinal Governance Rules & Safeguards

### Rule 1: Single Linearizable Authority
$$\boxed{\text{Exactly One Linearizable Authority for } S_A}$$
Multi-master or split-shard authorities that independently commit resource state without a single global linearizability point are explicitly prohibited.

### Rule 2: Strict Physical Containment Boundary
$$\boxed{\text{RequiredPhysicalEnforcement} \land \text{Unavailable} \Longrightarrow \text{ExecutionRejected}}$$
Under `strict_mode=True` or when physical containment is explicitly requested by a task specification, the system fails closed if cgroups v2 is unavailable. Unconstrained subprocess fallback (`strict_mode=False`) is strictly a non-production developer convenience path and is NEVER treated or documented as equivalent to physical containment.

### Rule 3: Safety Over Latency Rule
$$\boxed{\text{No architectural candidate may be selected solely because it reduces latency}}$$
Every candidate must ALSO preserve:
$$\text{Authority} + \text{Capacity Safety} + \text{Fencing} + \text{Recovery} + \text{Determinism} + \text{Resource Bounds}$$
and its migration MUST be fully reversible.

### Rule 4: Benchmark Execution Safety Rule
$$\boxed{\text{Bound} + \text{Admission} + \text{Timeout} + \text{Telemetry} + \text{Cleanup}}$$
Before benchmarking up to scale $N=10^5$, the benchmark harness itself MUST be resource-bounded. No benchmark execution may exhaust host memory or CPU resources merely to measure Cortex scheduler performance.

### Rule 5: Experimental Scale Qualification Rule
$$\boxed{N=10^5 \text{ is an experimental research target, not an assumed supported scale}}$$
Benchmark target scales must never be elevated to supported product guarantees until empirically verified across all environmental boundaries.

### Rule 6: Demonstration Boundary Rule
$$\boxed{\text{Architecturally Plausible} \neq \text{Empirically Demonstrated}}$$
Architectural proposals and theoretical designs are classified as `SPECIFIED` or `DESIGN` and are never documented as verified features without passing execution evidence.

---

## 2. Engineering Refactoring Discipline Workflow

```
[ Current Architecture Baseline ]
               │
               ▼
   [ Instrument Latency Clocks ]
               │
               ▼
   [ Measure Bottleneck Contention ]
               ├── T_GIL (Python Interpreter Lock)
               ├── T_lock-wait (Application RLock)
               ├── T_critical (Work inside Lock)
               ├── T_expiration (Linear Scan)
               ├── T_WAL (Disk fsync)
               └── T_IPC (Process Spawner)
               │
               ▼
   [ Identify Dominant Constraint ]
               │
               ▼
   [ Model Research Candidate ]
               │
               ▼
   [ Check Authority & Refinement Impact ]
               │
               ▼
   [ Prototype Candidate in Isolation ]
               │
               ▼
   [ Benchmark Against Baseline ]
               │
               ▼
   [ Adversarial & Regression Verification ]
               │
               ▼
  [ ONLY THEN MERGE / REFACTOR ]  ──► Or Default to: KEEP CURRENT ARCHITECTURE
```

---

## 3. Repository Truth & Evidence Classification Standards

Every architectural statement, optimization proposal, and benchmark finding must be grounded in repository code and classified using standard assurance levels:

- `PROVEN`: Formally verified via Coq/Rocq `.v` proofs in `contracts/`.
- `MODEL-CHECKED`: Verified via TLA+ specs in `verification/tla/`.
- `RUNTIME-VERIFIED`: Supported by 100% passing execution in `tests/conformance/`, `tests/kernel/`, or `tests/regression/`.
- `ADVERSARIALLY-TESTED`: Validated under fault injection, CRC corruption, or race conditions.
- `EMPIRICALLY-MEASURED`: Measured via benchmark scripts (`tests/performance/test_scheduler_benchmark.py`).
- `SPECIFIED`: Documented normative rules with defined invariants.
- `DESIGN`: Architectural design proposal without executable implementation.
- `PROTOTYPE`: Experimental or hardware design simulation (e.g. Verilator RTL).
- `UNPROVEN`: Speculative optimization claim lacking empirical or formal evidence.
- `NOT-IMPLEMENTED`: Planned phase feature currently absent from repository code.

---

## 4. Inviolable System Invariants

Before evaluating optimization candidates, the following 9 authoritative invariants MUST be preserved:

1. **Single Source of Truth**: Exactly one linearizable authoritative ordering for task-state and reservation mutations.
2. **Atomic Reservation Commit**: Resource budgets reserved and committed atomically under lock; no partial vector allocations.
3. **Capacity Safety**: $\sum \text{Used} + \text{Reserved} \le \text{Capacity}$ across all resource dimensions ($\text{CPU}, \text{RAM}, \text{GPU}, \text{VRAM}, \text{IOPS}, \text{FDs}$).
4. **Lease/Fencing Monotonicity**: Worker reassignments strictly increment `LeaseEpoch` ($e \to e+1$). Stale commit attempts return `ERR_STALE_LEASE_EPOCH`.
5. **Reservation Identity Stability**: Reservation IDs remain immutable throughout state transitions (`REQUESTED` $\to$ `COMMITTED` $\to$ `RELEASED`).
6. **Terminal Reclamation**: All allocated resources returned to pool upon task completion, failure, timeout, or worker death.
7. **Worker Incarnation Safety**: Retired or quarantined workers are barred from task assignments and lease renewals.
8. **Deterministic Failure Semantics**: System fails closed under corrupted WAL frames, stale epochs, or strict enforcement failures.
9. **Reusable Capacity Safety**: Capacity freed by cancellation or expiration is immediately re-allocatable without corruption.

---

## 5. Ground-Truth Scheduler Execution Path Analysis

```
[ Task Intent ]
      │
      ▼
[ 1. Eligibility Check ] ──► ConfigResolver (Capabilities & Constraints)
      │
      ▼
[ 2. Capability Lookup ] ──► CapabilityIndex (Inverted Set W_c Lookup)
      │
      ▼
[ 3. Worker Selection ]  ──► Snapshot Read View (V = f(S_A)) or Locked Selection
      │
      ▼
[ 4. Reservation Check ] ──► ResourceAuthority (Vector Budget Check under lock)
      │
      ▼
[ 5. Mutation Commit ]   ──► LoadBalancer & ResourceAuthority State Update
      │
      ▼
[ 6. Durable Log (WAL) ] ──► WriteAheadLog (CRC32 Frame Append + os.fsync)
      │
      ▼
[ 7. IPC Actuation ]    ──► ExecutionEnforcer (cgroups v2 / Socket IPC Spawner)
```

---

## 6. Latency Component Attribution Equation

To determine the true bottleneck before selecting an architecture, total request latency MUST be decomposed and measured independently:

$$T_{\text{total}} = T_{\text{GIL}} + T_{\text{lock-wait}} + T_{\text{critical}} + T_{\text{eligibility}} + T_{\text{selection}} + T_{\text{reservation}} + T_{\text{expiration}} + T_{\text{WAL}} + T_{\text{IPC}} + T_{\text{other}}$$

- **Scale Grid**: $N \in \{10^2, 10^3, 10^4, 10^5\}$ workers and $C \in \{1, 2, 4, 8, 16, 32, 64\}$ threads.
- **GIL vs RLock Disambiguation**: $T_{\text{GIL}}$ measured via C-extension/sys.setswitchinterval timers to distinguish Python interpreter lock contention from application `RLock` serialization.

---

## 7. Evaluation of Six Concurrency Research Candidates

Every candidate is strictly classified as a $\boxed{\text{RESEARCH CANDIDATE}}$ until empirical evidence justifies adoption:

| Candidate | Architecture Description | Primary Benefit | Key Architectural Risks | Invariant Preservation Status |
| :--- | :--- | :--- | :--- | :--- |
| **Candidate A: Immutable Snapshots / RCU** | Atomic pointer swap of read view $V=f(S_A)$; mutations append to copy-on-write buffer. | Zero lock wait for readers | Copy allocation overhead under high write rate | Preserves $I_1 \dots I_{12}$; requires atomic swap proof. |
| **Candidate B: Single Authoritative Writer + Derived Readers** | Single lock-free ring-buffer thread handles all mutations; reader views derived asynchronously. | Eliminates lock contention ($T_{\text{lock-wait}} \to 0$) | Single-writer throughput ceiling; backpressure management | Preserves Single Source of Truth ($I_1$); zero lock race risk. |
| **Candidate C: Lock Partitioning (Sharded Pools)** | Worker registry partitioned into independent capability shards. | Parallel mutations across disjoint shards | Cross-shard tasks require multi-shard locking; risk of deadlock | High risk of introducing multiple non-linearizable authorities. |
| **Candidate D: Partitioned Resource Authority** | Host vector budget split into independent sub-pools assigned to worker groups. | Local vector budget commits without global lock | Resource fragmentation; re-balancing overhead under burst loads | High risk of capacity under-utilization or allocation imbalance. |
| **Candidate E: Min-Heap Reservation Expiration** | $O(\log N)$ priority queue for TTL cleanup sweeps. | Eliminates $O(N)$ expiration lock hold time | Stale heap entries require soft-deletion cleanup | Targeted optimization; zero impact on core scheduler state $S_A$. |
| **Candidate F: Polyglot Async Core (Rust/Go Gateway)** | Compiled async core binary managing Gateway TCB routing. | Native speed, zero GIL pauses | High FFI serialization overhead; complex memory ownership across C boundary | Premature until Python serialization bottleneck is isolated. |

---

## 8. Mandatory Decision Package Deliverables

Before any scheduler refactoring begins, the research gate MUST produce a comprehensive 15-point **Decision Package**:

1. **Exact Current Bottleneck**: Empirical latency component attribution ($T_{\text{GIL}}, T_{\text{lock-wait}}, T_{\text{critical}}, T_{\text{expiration}}, T_{\text{WAL}}, T_{\text{IPC}}$).
2. **Exact Critical Section Responsible**: Code file, class, method, and lock scope causing serialization.
3. **Complexity at Scale**: Operations complexity at current ($N=1,000$) and experimental ($N=100,000$) scale.
4. **Lock Contention Attribution**: GIL vs application `RLock` vs authoritative mutation serialization.
5. **Reservation Expiration Cost**: Measured lock hold time and throughput impact of `expire_reservations()`.
6. **WAL / IPC Contribution**: Disk sync and process spawner latency overhead.
7. **Memory Growth Model**: Steady-state memory consumption $M(N)$ under worker/reservation churn.
8. **Six Candidate Comparison Matrix**: Objective scoring across Candidates A–F.
9. **Invariant & Refinement Impact**: Impact on state $S_A$, derived views, and Coq/TLA+ proofs.
10. **Recommended Smallest Safe Change**: Minimal safe modification backed by evidence.
11. **Isolated Prototype Design**: Architectural specification of candidate in isolation.
12. **Verification Plan**: Pytest, fault injection, and formal proof verification steps.
13. **Rollback Plan**: Operational procedure to revert changes without state corruption.
14. **Stop Conditions**: Mandatory criteria triggering immediate refactoring halt.
15. **Final Decision**: Explicit verdict choosing `KEEP`, `HARDEN`, `REFACTOR`, `RESEARCH`, or `REPLACE`.

---

## 9. Final Decision Rule

If empirical benchmark evidence does not clearly prove that a research candidate improves scale while preserving 100% of invariant safety with acceptable complexity:

$$\boxed{ \text{KEEP CURRENT ARCHITECTURE} }$$
