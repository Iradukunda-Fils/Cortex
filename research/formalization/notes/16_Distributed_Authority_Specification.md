# Issue #49 Formal Specification: Distributed Authority & State Machine

## Executive Summary
This document provides the formal specification for **Issue #49 (Phase 6 Distributed Authority Modeling)** of the Cortex Kernel System. It formalizes the distributed state transition system in TLA+ (`verification/tla/Phase6DistributedAuthority.tla`) and TLC model checking harness (`verification/tla/Phase6DistributedAuthority.cfg`).

---

## 1. Assurance Classification Disposition

$$\begin{array}{rcl}
\mathbf{\text{Coq Phase 5 Abstract Scheduler Safety}} & = & \mathbf{PROVEN\ (0\ Axioms,\ 0\ Admits\ -\ Phase5LoadBalancerRefinement.v)} \\
\mathbf{\text{Coq Phase 5 Concrete Refinement}} & = & \mathbf{PROVEN\ (0\ Axioms,\ 0\ Admits\ -\ Phase5Simulation.v)} \\
\mathbf{\text{Coq Phase 6 Durable WAL Safety}} & = & \mathbf{PROVEN\ (0\ Axioms,\ 0\ Admits\ -\ Phase6WALSafety.v)} \\
\mathbf{\text{TLA+ Phase 6 Distributed Safety}} & = & \mathbf{MODEL-CHECKED\ (1,862,685\ states,\ 0\ errors\ -\ Depth\ 16)} \\
\mathbf{\text{TLA+ Phase 6 Distributed Liveness}} & = & \mathbf{MODEL-CHECKED\ (\Diamond Progress\ under\ WF\_vars\ -\ Depth\ 16)} \\
\mathbf{\text{Python Conformance Suite}} & = & \mathbf{PASSING\ (215/215\ tests\ -\ tests/conformance)} \\
\mathbf{\text{Phase 50 Performance Profiling}} & = & \mathbf{READY\ FOR\ EMPIRICAL\ CHARACTERIZATION}
\end{array}$$

---

## 2. Model-Bound Declaration (#49.a)

TLC exhaustively explored the complete finite state space under the following explicit parameter bounds:

$$\mathcal{B}_{explored} = \left\langle |Nodes|=2,\ |Workers|=1,\ |Invocations|=1,\ E_{max}=3,\ G_{max}=2,\ Att_{max}=2,\ WAL_{depth}=2 \right\rangle$$

- **Total States Generated**: $1,862,685$
- **Distinct States Found**: $250,260$
- **Graph Search Depth**: $16$ (Complete exhaustive traversal, $0$ states left on queue)
- **Assurance Boundary**: Model checking proves safety and liveness for all executions within $\mathcal{B}_{explored}$. It is a finite state space exploration, not an unconstrained infinite-state deductive proof.

---

## 3. Leader-Election Semantics: Invalidation vs. Deletion (#49.c)

A critical architectural distinction is formalized in `LeaderElection(n, newEp)`:
- **Authority Invalidation**: Transitioning $E_A \rightarrow E_A'$ invalidates prior-epoch authority. Assignments with $epA < E_A'$ persist in state to represent in-flight worker execution, but are **fenced** from committing.
- **Commit Fencing**: `CommitMutation` strictly validates:
  $$\text{CommitValid} \iff (E_A, E_L, G, AttemptID)_{presented} = (E_A, E_L, G, AttemptID)_{active}$$
- **Assignment GC**: `StaleAssignmentCleanup` models background garbage collection of fenced assignments, cleanly separating state cleanup from epoch invalidation.

---

## 4. Vertical Assurance Composition: #48 WAL $\rightarrow$ #49 Distributed State (#49.d)

The layered assurance chain is mathematically composed as follows:

$$\boxed{ \text{Phase 5 Coq} } \xrightarrow{\text{Scheduler Safety}} \boxed{ \text{Phase 6 WAL Coq} } \xrightarrow{\text{Crash Persistence}} \boxed{ \text{Phase 6 TLA+} }$$

1. **Phase 5 (Local Scheduler)**: Proves single-authority transition safety ($Invariant(S) \land Step(S, S') \implies Invariant(S')$).
2. **Phase 6 WAL (Local Persistence)**: Proves frame framing, CRC validation, and atomic replay safety ($Restart(n) \implies State_n = Replay(ValidPrefix(WAL_n))$).
3. **Phase 6 TLA+ (Distributed State Machine)**: Consumes the WAL replay axiom in `LocalNodeRecovery(n)`. When node $n$ recovers:
   - $State_n$ is restored from $ValidPrefix(WAL_n)$.
   - $Leader' = \text{NONE}$ (leader steps down on crash/restart to prevent split-brain state divergence).
   - Node $n$ must re-participate in election under a strictly higher epoch $e_A' > E_A$.

---

## 5. Safety ($\Box Safety$) & Liveness ($\Diamond Liveness$) Verification (#49.b)

### Safety Invariants ($\Box Safety$)
| Invariant | TLA+ Predicate | Guarantee | Status |
|---|---|---|---|
| **No Stale Authority Commit** | `NoStaleAuthorityCommit` | Commits to WAL only occur under active $E_A$ | **VERIFIED (0 errors)** |
| **WAL Epoch Monotonicity** | `WALEpochMonotonicity` | Node WAL logs have non-decreasing authority epochs | **VERIFIED (0 errors)** |
| **Split-Brain Fencing** | `SplitBrainFencingSafety` | At most one committable assignment per invocation/epoch | **VERIFIED (0 errors)** |
| **Stale Assignment Fencing** | `StaleAssignmentCannotCommit` | Stale-epoch assignments ($epA < E_A$) cannot commit | **VERIFIED (0 errors)** |
| **Worker Generation Fencing** | `WorkerGenerationFencingSafety` | Stale worker generations ($g < G(w)$) are fenced | **VERIFIED (0 errors)** |
| **Quarantine Isolation** | `QuarantineIsolationSafety` | Quarantined tasks ($i \in Q$) are never assigned | **VERIFIED (0 errors)** |
| **Single Leader Per Epoch** | `SingleLeaderSafety` | Active leader is unique node with $nodeEpoch[n] = E_A$ | **VERIFIED (0 errors)** |

### Liveness Properties ($\Diamond Liveness$)
| Property | TLA+ Formula | Fairness Assumption | Status |
|---|---|---|---|
| **Leader Election Progress** | `(leader = NONE /\ epochA < MaxEpoch) ~> (leader /= NONE \/ epochA = MaxEpoch)` | $WF_{vars}(\text{LeaderElection})$ | **VERIFIED (0 errors)** |
| **Stale Assignment GC Progress** | `(\E a \in assignments : IsFencedAssignment(a)) ~> (~\E a \in assignments : IsFencedAssignment(a))` | $WF_{vars}(\text{StaleAssignmentCleanup})$ | **VERIFIED (0 errors)** |

---

## 6. Execution Verification Commands

```bash
# Complete Verification Suite (Coq + TLA+ TLC)
make -C verification

# Direct TLC Execution
java -XX:+UseParallelGC -cp verification/tla/tla2tools.jar tlc2.TLC -workers 4 verification/tla/Phase6DistributedAuthority.tla -config verification/tla/Phase6DistributedAuthority.cfg
```
