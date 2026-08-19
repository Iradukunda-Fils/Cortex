# Phase 5 Load-Balancing Policy Specification

> **Subsystem Target**: Phase 5 Load-Balancing & Resource Optimization  
> **Governance Status**: `DESIGN REVIEW ONLY` (Implementation strictly blocked)  
> **Pre-requisite Baseline**: Phase 4 Routing & Dispatch (PR #26) — Single-Gateway tested domain (`333/333 PASS`)

---

## 1. Architectural Principles & Invariants

To maintain safety and isolation across worker pools, the Load-Balancing subsystem is strictly limited to **soft placement optimization** and is explicitly prohibited from exercising execution authority.

### Invariant 5.1: Non-Authoritative Load Balancer
The Load Balancer acts as a *placement advisory engine*. It holds zero bearer tokens, has no TCB mutation access, and cannot bypass the Phase 4 candidate filtering or LeaseManager revalidation logic.

### Placement Pipeline Flow
```text
  State/Metric Ingestion
            │
            ▼
  Load-Balancing Policy  ──► Proposes Candidate preference
            │
            ▼
   Phase 4 Router        ──► Rechecks Hard Eligibility constraints
            │
            ▼
    LeaseManager         ──► Linearizable Single-Lock Revalidation
            │
            ▼
   Gateway Dispatcher    ──► Execution / Witness Logging
```

---

## 2. Mathematical Load Model (Phase 5A)

Rather than blending capability checks and resource utilization metrics into a single fuzzy score, Cortex strictly separates **Hard Eligibility Constraints** from **Soft Optimization Metrics**.

### 2.1 Hard Eligibility Constraints ($HardConstraints(W, I)$)
A worker replica $W$ is eligible for an invocation $I$ if and only if all the following boolean constraints evaluate to `true`:
$$HardConstraints(W, I) \equiv (Stage(W) == READY) \land (Gen(W) == TargetGen) \land (ProfileMatch(W)) \land (CapCompatible(W, I)) \land (Inflight(W) < Limit(W))$$

We define the set of eligible candidates for invocation $I$ as:
$$Candidates(W, I) = \{ W \mid HardConstraints(W, I) \}$$

### 2.2 Soft Optimization Metrics
Only after $Candidates(W, I)$ is resolved can the load balancer evaluate soft metrics to rank the candidates.
* $I(W)$: Active inflight count (number of non-terminal invocations assigned to $W$).
* $Q(W)$: Bounded queue waiting duration for the worker's queue group.
* $L(W)$: Exponentially Weighted Moving Average (EWMA) of execution latency for worker $W$.
* $Aff(W, I)$: State-domain locality flag. $Aff(W, I) = 1$ if the target `StateDomainKey` of $I$ is warm in worker $W$'s local cache; else $0$.
* $U_{cpu}(W), U_{mem}(W)$: Normalized system utilization metrics reported via telemetry.

### 2.3 Optimization Objective Selection
The load balancer selects the optimal candidate by minimizing the active policy's scoring function:
$$Select(Candidates) = \arg\min_{W \in Candidates} PolicyScore(W)$$

---

## 3. Allowed Optimization Policies

Cortex limits the load model to three deterministic optimization policies to prevent non-reproducible routing behaviors.

### 3.1 `LEAST_INFLIGHT`
Selects the worker with the lowest active inflight count to spread concurrency evenly:
$$PolicyScore_{LEAST\_INFLIGHT}(W) = I(W)$$

### 3.2 `WEIGHTED_LEAST_INFLIGHT`
Balances active inflight count against latency and queue wait time to prevent routing tasks to slow or degraded replicas:
$$PolicyScore_{WEIGHTED\_LEAST\_INFLIGHT}(W) = I(W) \cdot \alpha + L(W) \cdot \beta + Q(W) \cdot \gamma$$
*(where $\alpha, \beta, \gamma$ are policy-defined non-negative scaling weights)*

### 3.3 `STATE_AFFINITY`
Prioritizes routing tasks to workers that already hold the state key warm in memory, minimizing serialization overhead while strictly adhering to `StateDomainKey` mutual exclusion:
$$PolicyScore_{STATE\_AFFINITY}(W) = I(W) - \eta \cdot Aff(W, I)$$
*(where $\eta$ is the locality preference offset weight)*

---

## 4. Overload, Failure & Drain Semantics

### 4.1 Overload Mitigation
When all workers in $Candidates(W, I)$ are saturated ($Inflight(W) \ge Limit(W)$) or no compatible candidate exists:
1. The request enters the per-`group_id` FIFO queue.
2. If the queue depth exceeds $QueueCeiling$, the dispatcher immediately rejects the request with `ERR_QUEUE_FULL`.
3. Auto-scaling is **strictly blocked**; the system never dynamically allocates resources to absorb load spikes.

### 4.2 Graceful Draining & Eviction
When a worker replica is set to a draining stage (e.g., prior to updates or scaling down):
1. The worker is immediately removed from $Candidates(W, I)$ for all new incoming invocations.
2. The system allows already assigned inflight invocations to execute until completion.
3. Once inflight count reaches zero, the worker transitions to `STOPPED`.

### 4.3 Policy Versioning & Rollout Fencing
To prevent split-brain routing where different Gateway nodes route tasks using inconsistent policies, the active load balancing configuration is bound by:
* `LoadPolicyGeneration`: Monotonically increasing configuration version.
* `LoadPolicyHash`: SHA-256 hash of the routing parameters.
Any mismatch between policy configurations across Gateways triggers an immediate policy synchronization block.

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
| **LB-7** | **Config Rollout Leak Guard** | Assert that during a configuration rollout, work is routed strictly to workers matching the target `ConfigGeneration`. |
| **LB-8** | **Capability Exclusion** | Prove that a capability-incompatible worker is rejected at the eligibility filter stage and never reaches the metric ranking phase. |
| **LB-9** | **Saturated Bounded Overflow** | Verify that when all workers are fully saturated, incoming requests trigger deterministic queue buffering and eventual `ERR_QUEUE_FULL` rejection. |
| **LB-10** | **Metric Staleness Guard** | Assert that stale telemetry metrics (e.g., delayed CPU usage updates) cannot bypass LeaseManager's atomic revalidation checks. |
| **LB-11** | **Routing Trace Reproducibility** | Verify that all routing decisions, soft scores, and final selections are logged to `RoutingDecisionEvent` for replay auditing. |
| **LB-12** | **Policy Isolation** | Assert that changes to `LoadPolicyGeneration` reject any active routing proposals generated under a previous policy version. |
| **LB-13** | **Fail-Closed to Phase 4 Semantics** | Prove that if telemetry metrics are lost or corrupt, the load balancer falls back to Phase 4 baseline safety semantics (Least-Inflight). |
| **LB-14** | **Metric Poisoning Immunity** | Verify that compromised or artificially manipulated telemetry metrics cannot steer work onto an ineligible worker. |
