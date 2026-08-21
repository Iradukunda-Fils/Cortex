# Phase 5 Load-Balancing Policy Specification

> **Subsystem Target**: Phase 5 Single-Gateway Load-Balancing & Resource Optimization  
> **Governance Status**: `APPROVED DESIGN ONLY` (Implementation strictly blocked until Phase 4 merges into `main`)  
> **Pre-requisite Baseline**: Phase 4 Routing & Dispatch (PR #26) — Single-Gateway tested domain (`333/333 PASS`)  

---

## 1. Architectural Scope & Core Principles

To maintain zero-trust security and isolation across worker pools, the Phase 5 Load-Balancing subsystem is strictly limited to **single-gateway soft placement optimization** and is explicitly prohibited from exercising execution authority.

### Invariant 5.1: Non-Authoritative Load Balancer
The Load Balancer acts as a *placement advisory engine*. It holds zero bearer tokens, has no TCB mutation access, and cannot bypass Phase 4 candidate filtering or LeaseManager revalidation logic.

### Invariant 5.2: Telemetry as Untrusted Optimization Hint
Worker-reported telemetry (active inflight count, system memory/CPU usage, local cache affinity) is treated as **untrusted optimization hints**. Telemetry metrics MAY influence soft score placement, but can NEVER authorize execution, override capability checks, or bypass state domain lock fencing.

### Invariant 5.3: Non-Negotiable Priority Hierarchy
Every routing placement decision MUST enforce the following strict priority hierarchy:

```
        [1] HARD SECURITY CONSTRAINTS (Seccomp, Landlock, ConfigGen, Caps)
                       ↓
        [2] STATE CONSISTENCY RULES (StateDomainKey serialization, Leases)
                       ↓
        [3] RESOURCE CONSTRAINTS (Cgroups memory ceilings, CPU quotas)
                       ↓
        [4] SOFT PLACEMENT OPTIMIZATION (Inflight count, Latency, Affinity)
                       ↓
        [5] DETERMINISTIC TIE BREAKING (Instance ID lexicographical sort)
```

### Invariant 5.4: Separation of Multi-Gateway Federation
Phase 5 is strictly bounded to the **Single-Gateway Authority Domain**. Multi-Gateway consensus, distributed lease fencing, cross-gateway witness ordering, and split-brain resolution are explicitly separated into **Phase 6: Multi-Gateway Federation & Distributed Consensus**.

---

## 2. Mathematical Load Model (Phase 5A)

Cortex strictly separates **Hard Eligibility Constraints** from **Soft Optimization Metrics**.

### 2.1 Hard Eligibility Constraints ($HardConstraints(W, I)$)
A worker replica $W$ is eligible for an invocation $I$ if and only if all the following boolean constraints evaluate to `true`:
$$HardConstraints(W, I) \equiv (Stage(W) == READY) \land (Gen(W) == TargetGen) \land (ProfileMatch(W)) \land (CapCompatible(W, I)) \land (Inflight(W) < Limit(W))$$

The eligible candidate set for invocation $I$ is:
$$Candidates(W, I) = \{ W \mid HardConstraints(W, I) \}$$

### 2.2 Soft Optimization Metrics
Only after $Candidates(W, I)$ is resolved can the load balancer evaluate soft metrics to rank candidates.
* $I(W)$: Active inflight count (number of non-terminal invocations assigned to $W$).
* $Q(W)$: Bounded queue waiting duration for the worker's queue group.
* $L(W)$: Exponentially Weighted Moving Average (EWMA) of execution latency for worker $W$.
* $Aff(W, I)$: State-domain locality hint. $Aff(W, I) = 1$ if the target `StateDomainKey` of $I$ is warm in worker $W$'s local cache; else $0$.

### 2.3 Optimization Objective Selection
The load balancer selects the optimal candidate by minimizing the active policy's scoring function:
$$Select(Candidates) = \arg\min_{W \in Candidates} PolicyScore(W)$$

If multiple candidates yield identical minimum scores, ties are resolved deterministically using lexicographical comparison of worker `instance_id`.

---

## 3. Allowed Optimization Policies

Cortex limits the load model to three deterministic optimization policies:

### 3.1 `LEAST_INFLIGHT` (Default Baseline)
Selects the worker with the lowest active inflight count to spread concurrency evenly:
$$PolicyScore_{LEAST\_INFLIGHT}(W) = I(W)$$

### 3.2 `WEIGHTED_LEAST_INFLIGHT`
Balances active inflight count against latency and queue wait time:
$$PolicyScore_{WEIGHTED\_LEAST\_INFLIGHT}(W) = I(W) \cdot \alpha + L(W) \cdot \beta + Q(W) \cdot \gamma$$
*(where $\alpha, \beta, \gamma$ are policy-defined non-negative scaling weights)*

### 3.3 `STATE_AFFINITY`
Prioritizes routing tasks to workers that hold the state key warm in memory:
$$PolicyScore_{STATE\_AFFINITY}(W) = I(W) - \eta \cdot Aff(W, I)$$
*(where $\eta$ is the locality preference offset weight)*

> [!IMPORTANT]
> **Locality Safety:** `STATE_AFFINITY` affects placement preference ONLY. It MUST NOT bypass downstream `StateDomainKey` mutual exclusion fencing in the `GatewayDispatcher`.

---

## 4. Overload, Failure & Drain Semantics

### 4.1 Overload Mitigation
When all workers in $Candidates(W, I)$ are saturated or no compatible candidate exists:
1. The request enters the per-`group_id` FIFO queue.
2. If the queue depth exceeds `max_queue_depth`, the dispatcher immediately rejects the request with `ERR_QUEUE_FULL`.
3. Auto-scaling is **strictly blocked**; the system never dynamically allocates resources to absorb load spikes.

### 4.2 Graceful Draining & Eviction
When a worker replica transitions to `DRAINING`:
1. The worker is immediately removed from $Candidates(W, I)$ for all new incoming invocations (`LB-6`).
2. Assigned inflight invocations execute until completion.
3. Once inflight count reaches zero, the worker transitions to `STOPPED`.

### 4.3 Fail-Closed Degradation
If telemetry streams are lost, corrupted, or delayed beyond `telemetry_timeout_sec`:
1. The load balancer drops soft metric optimization (`LB-13`).
2. Placement automatically degrades to Phase 4 baseline routing (`LEAST_INFLIGHT`).

---

## 5. Phase 5 Verification Audit Matrix (LB-1 through LB-14)

| Gate ID | Target Boundary / Safety Requirement | Verification Test Vector |
| :--- | :--- | :--- |
| **LB-1** | **Constraint Primacy** | Assert that a worker with a perfect soft load score but failing any hard eligibility constraint (e.g., config mismatch) is never selected. |
| **LB-2** | **Determinism Under Identical Load** | Verify that given identical load metrics and candidate sets, the policy selection remains deterministic (no random tie-breaking). |
| **LB-3** | **Starvation Prevention** | Assert that sustained high-priority or state-affinity load does not indefinitely starve lower-priority queue items. |
| **LB-4** | **FIFO Consistency** | Prove that FIFO queue ordering is preserved at the dispatcher when load-balancing score evaluations are executed. |
| **LB-5** | **Affinity Lock Safety** | Assert that routing based on `STATE_AFFINITY` does not violate downstream `StateDomainKey` mutual exclusion fencing. |
| **LB-6** | **Draining Exclusion** | Verify that a worker replica in `DRAINING` stage receives zero new proposals, regardless of load metric advantages. |
| **LB-7** | **Config Rollout Leak Guard** | Assert that during a configuration rollout, work is routed strictly to workers matching target `ConfigGeneration`. |
| **LB-8** | **Capability Exclusion** | Prove that a capability-incompatible worker is rejected at the eligibility filter stage and never reaches metric ranking. |
| **LB-9** | **Saturated Bounded Overflow** | Verify that when all workers are fully saturated, incoming requests trigger deterministic queue buffering and eventual `ERR_QUEUE_FULL` rejection. |
| **LB-10** | **Metric Staleness Guard** | Assert that stale telemetry metrics cannot bypass LeaseManager's atomic revalidation checks. |
| **LB-11** | **Routing Trace Reproducibility** | Verify that all routing decisions, soft scores, and final selections are logged to `RoutingDecisionEvent` for replay auditing. |
| **LB-12** | **Policy Isolation** | Assert that changes to `LoadPolicyGeneration` reject any active routing proposals generated under a previous policy version. |
| **LB-13** | **Fail-Closed Baseline Fallback** | Prove that if telemetry metrics are lost or corrupt, the load balancer falls back to Phase 4 baseline safety semantics (`LEAST_INFLIGHT`). |
| **LB-14** | **Metric Poisoning Immunity** | Verify that compromised or artificially manipulated telemetry metrics cannot steer work onto an ineligible worker. |

---

## 6. Phase 5 Governance & Readiness Matrix

| Governance Dimension | Current Status | Blocking Dependencies | Target Reconciliations |
| :--- | :--- | :--- | :--- |
| **Specification** | `APPROVED DESIGN ONLY` | None | Fully specified |
| **Phase 4 Pre-requisite** | `BLOCKED (PR #26)` | Config Resolver Binding | Must merge into `main` before Phase 5 code |
| **Implementation** | `STRICTLY BLOCKED` | Phase 4 Merge | `cortex/tools/kernel/replica/load_balancer.py` |
| **Verification Suite** | `SPECIFIED (LB-1..LB-14)` | Implementation | `tests/conformance/test_replica_phase_5.py` |
| **Multi-Gateway Federation**| `SEPARATED TO PHASE 6` | Phase 5 Completion | Multi-gateway Raft consensus & distributed leases |
