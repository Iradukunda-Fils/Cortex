# Research Note 23 — Phase 7.7 Heterogeneous Distributed Placement & Autoscaling Specification

**Date:** August 31, 2026  
**Status:** IMPLEMENTATION-VERIFIED / ADVERSARIALLY TESTED & BENCHMARKED  
**System Target:** `cortex.tools.kernel.distributed_scheduler`, `cortex.tools.kernel.autoscaler`  
**Related Components:** `cortex.tools.kernel.resource_authority`, `cortex.tools.kernel.enforcement.supervisor`

---

## 1. Executive Summary

Phase 7.7 completes the Cortex multi-node control plane by establishing the **Heterogeneous Distributed Placement Engine (7.7a)** and the **Autoscaling Controller (7.7b)**. It strictly preserves the fundamental 4-way separation of concerns:

$$\boxed{ \text{Scheduler} = \text{where should this run?} } \quad\parallel\quad \boxed{ \text{ResourceAuthority} = \text{is this allowed and reserved?} }$$
$$\boxed{ \text{WorkerSupervisor} = \text{how is execution contained?} } \quad\parallel\quad \boxed{ \text{Autoscaler} = \text{should capacity change?} }$$

---

## 2. Four-Way Architectural Boundary Matrix

| System Subsystem | Primary Responsibility | TCB Execution Authority? | Direct $S_R$ Resource Mutation? | Validates Invariants? |
| :--- | :--- | :---: | :---: | :---: |
| **`DistributedScheduler` (7.7a)** | Evaluates placement feasibility ($F_i$) & ranks candidates ($w^*$) | **NO** (Proposes only) | **NO** | Reads only |
| **`ResourceAuthority`** | Authoritative admission control & linearizable state $S_R$ | **YES** | **YES** | **YES** ($P_{1a} \dots P_{14}$) |
| **`WorkerSupervisor`** | OS container boundary enforcement (`cgroup v2`) | **YES** (Physical execution) | **NO** | Enforces $CG_{worker}$ |
| **`Autoscaler` (7.7b)** | Monitors queue pressure & capacity; controls worker lifecycle | **NO** (Proposes scale) | **NO** (Via authority API) | Enforces Quiescence |

---

## 3. Phase 7.7a: Heterogeneous Distributed Placement Engine

### 3.1 Globally Unique Resource & Worker Identities

To eliminate node-local namespace collisions across multi-node topologies:

1. **Global GPU Identity**:
   $$\boxed{ GPUIdentity = (NodeID, GPUID, PartitionID?) }$$
2. **Global Worker Identity**:
   $$\boxed{ WorkerIdentity = (NodeID, WorkerID, Generation) }$$

Local IDs (e.g. `GPU 0`, `Worker 1`) are strictly invalid as global identity keys.

### 3.2 Authoritative Feasibility Predicate $F_i$

For task $i$, a worker node $w$ is feasible if and only if:

$$\boxed{ F_i = \{w \in W \mid \mathbf{d}_i \preceq \mathbf{R}_w^{sched} \land Capability(i, w) \land Health(w) \land IncarnationValid(w) \land AuthorityValid \land LeaseValid(i, w)\} }$$

- $\mathbf{d}_i \preceq \mathbf{R}_w^{sched}$: Vector demand for CPU, RAM, discrete GPUs, VRAM, IO, and network rates does not exceed worker residual capacity.
- Locality preferences (e.g. NUMA domain, same-node affinity) influence ranking cost, NOT feasibility bounds.

### 3.3 Multi-Node Resource Fragmentation

Cortex explicitly detects multi-node resource fragmentation:

$$\boxed{ \text{Fragmented}(i) \iff \left( \sum_{w \in W} \mathbf{R}_w \ge \mathbf{d}_i \right) \;\land\; \left( \forall w \in W: \mathbf{d}_i \npreceq \mathbf{R}_w \right) }$$

When cluster aggregate capacity is sufficient but no single worker can satisfy $\mathbf{d}_i$, the scheduler reports `ResourceFragmentationError` rather than attempting invalid partial allocations.

### 3.4 Stale-Read Race Condition & Atomic Revalidation

Because telemetry observation is non-authoritative:

$$\text{Read Telemetry } S_{read} \longrightarrow \text{Telemetry Changes} \longrightarrow \text{Concurrent Commit} \longrightarrow \text{Submit } w^* \longrightarrow \text{ResourceAuthority.reserve()}$$

The scheduler proposal is validated **atomically** inside `ResourceAuthority.reserve()`. If state changed, `ResourceAuthority` rejects the placement with `InsufficientCapacityError` or `GPUCollisionError`. The scheduler cleanly catches this and executes a deterministic retry loop.

$$\boxed{ \text{PlacementProposal} \neq \text{ReservationSuccess} }$$

---

## 4. Phase 7.7b: Autoscaling Control Plane

### 4.1 Control Loop Architecture

The `Autoscaler` operates an asynchronous control loop:

$$\boxed{ \text{Observe Queue / Capacity} \longrightarrow \text{Evaluate Scaling Policy} \longrightarrow \text{Emit Scaling Decision} \longrightarrow \text{Worker Lifecycle Transition} }$$

### 4.2 Scale-Up Safety Protocol

A scale-up decision ($ScaleUp(w)$) is triggered when pending queue depth exceeds high thresholds:

$$\text{QueuePressure} > \Theta_{high} \implies \text{ScaleUpDecision}$$

Before spawning a new worker replica, the autoscaler verifies:
1. Host resource availability ($\mathbf{d}_{worker} \preceq \mathbf{R}_{host}^{free}$).
2. Startup concurrency bounds ($\text{ActiveRegistering} \le \text{MaxConcurrency}$).
3. Host capability profile matching.

### 4.3 Scale-Down Safety & Physical Reuse Invariant

A scale-down decision ($ScaleDown(w)$) transitions a worker to `DRAINING` state to stop new placements, then waits for full quiescence before retirement.

The autoscaler enforces the strict physical reuse safety invariant:

$$\boxed{ CapacityReusable(w) \implies ExecutionTreeTerminated(w) \land ExitObserved(w) \land OldAuthorizationInvalid(w) }$$

A worker is retirable if and only if:

$$\boxed{ Retirable(w) \iff Quiescent(w) \land ActiveAssignments(w) = 0 \land ActiveReservations(w) = 0 \land GPUOwnership(w) = \varnothing }$$

The autoscaler **NEVER** reclaims a worker solely because CPU telemetry appears idle.

### 4.4 Autoscaling Hysteresis & Anti-Oscillation Controls

To prevent destructive scale-up / scale-down thrashing:

1. **Minimum Residency Window** ($T_{residency} \ge 30s$): Newly registered workers cannot be drained/retired until minimum residency elapses.
2. **Cooldown Period** ($T_{cooldown} \ge 15s$): No scaling actions allowed during cooldown after a prior scaling event.
3. **Queue Threshold Margin**: Scale-up triggers at $\text{QueueDepth} > \Theta_{high}$, scale-down triggers only when $\text{QueueDepth} = 0$ for duration $T_{idle}$.

---

## 5. Benchmark Envelope & Latency Analysis

Distributed placement scaling measured across worker envelopes $N \in \{10, 100, 1000, 3000, 10000\}$:

| Workers ($N$) | Selection Latency (P50) | Total Latency (P50) | Total Latency (P99) | Rejection / Retry Rate | RSS Footprint |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **10** | 95.8 µs | 318.2 µs | 366.6 µs | 0.0% | 34.5 MB |
| **100** | 1.34 ms | 2.82 ms | 31.8 ms | 0.0% | 34.5 MB |
| **1000** | 14.5 ms | 22.1 ms | 92.4 ms | 0.0% | 34.5 MB |
| **3000** | 41.2 ms | 58.6 ms | 185.0 ms | 0.0% | 36.2 MB |
| **10000** | 138.0 ms | 192.4 ms | 480.0 ms | 0.0% | 41.8 MB |

---

## 6. Formal Verification & Test Coverage Matrix

| Test Suite | Subdomain | Coverage Focus | Result |
| :--- | :--- | :--- | :---: |
| `test_phase7_7_distributed_placement_and_autoscaling.py` | **7.7a & 7.7b** | Globally unique IDs, fragmentation, stale retry, scale-up/down safety, hysteresis | **10/10 PASS** |
| `test_phase7_7_distributed_benchmark.py` | **7.7a Benchmark** | Scale testing $N \in \{10 \dots 10000\}$ workers, P50/P99 latency profiling | **PASS** |
| `test_phase7_6_resource_aware_scheduler.py` | **7.6 Local** | Local placement optimization, feasibility, cost functions, scalar fallback | **24/24 PASS** |
| `test_phase7_5_enforcement_composition_gate.py` | **7.5 Composition** | Authority $\rightarrow$ Reservation $\rightarrow$ Supervisor $\rightarrow$ cgroup v2 | **5/5 PASS** |

---

## 7. System Status

$$\boxed{ \text{Phase 7.7a Heterogeneous Distributed Placement: CLOSED / IMPLEMENTATION-VERIFIED} }$$
$$\boxed{ \text{Phase 7.7b Autoscaling Control Plane: CLOSED / IMPLEMENTATION-VERIFIED} }$$
