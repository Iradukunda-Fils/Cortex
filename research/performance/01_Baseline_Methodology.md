# Research Note 01: Baseline Performance & Measurement Methodology

## Executive Summary
This document establishes the experimental design, measurement metrics, workload generation strategy, and governance rules for **Issue #50 (Baseline System Profiling)**.

Before any optimization ($O(1)$ P2C, sharded state, RCU, Go/Rust acceleration, zero-copy FFI) is proposed or evaluated, Cortex requires a rigorous empirical baseline $B_{current}(N)$ of the existing unoptimized Python kernel.

---

## 1. Governance & Refinement Preservation Rules

### Rule 1: Measurement Before Redesign
No structural or algorithmic changes may be made to `cortex.tools.kernel.load_balancer` until $B_{current}(N)$ is fully measured across $N \in \{10, 100, 1,000, 10,000\}$ workers/invocations.

### Rule 2: Re-Refinement Invalidation Gate
For every candidate optimization $O_i$, we evaluate:
$$\Delta T_i\text{ (latency)},\quad \Delta M_i\text{ (memory)},\quad \Delta C_i\text{ (complexity)}$$
If $O_i$ modifies the authoritative state representation or transition system:
$$\boxed{ \Delta(\text{authoritative state}) \implies R(C, A)\text{ invalidated} \implies \text{re-refinement required} }$$
Re-refinement requires updating `Phase5LoadBalancerRefinement.v` and `Phase5Simulation.v` to maintain machine-checked safety certificates.

### Rule 3: Trade-off Evaluation Hierarchy
When evaluating optimizations, Cortex enforces the following decision hierarchy:
$$\boxed{ \text{Safety} > \text{Proof Complexity} > \text{Memory} > \text{Determinism} > \text{Scalability} > \text{Latency} > \text{Throughput} }$$

---

## 2. Mathematical Latency Decomposition

Whole-system scheduling latency $T_{schedule}$ is decomposed as follows:

$$T_{schedule} = T_{lock} + T_{eligibility} + T_{selection} + T_{mutation} + T_{serialization} + T_{WAL} + T_{IPC}$$

Where:
- $T_{lock}$: Lock acquisition wait time and RLock contention duration.
- $T_{eligibility}$: Capability, quarantine, and state filter evaluation latency.
- $T_{selection}$: Score calculation and dynamic worker ranking time.
- $T_{mutation}$: State transition, assignment insertion, and lease epoch update latency.
- $T_{serialization}$: Assignment payload packing/framing latency.
- $T_{WAL}$: Frame CRC32 calculation, append, and atomic `fsync` persistence time.
- $T_{IPC}$: Unix domain socket / IPC channel transport overhead.

---

## 3. Measured Metric Taxonomy

For each workload scale $N \in \{10, 100, 1,000, 10,000\}$, the benchmark harness captures:

| Metric Category | Specific Metrics Recorded | Purpose |
|---|---|---|
| **Latency Distribution** | P50, P95, P99, P99.9, Max (microseconds) | Characterizes tail behavior under load |
| **Throughput** | Ops/sec, Assignments/sec, Commits/sec | Measures raw scheduling capacity |
| **Concurrency Bottlenecks** | Lock wait time, Lock hold time (nanoseconds) | Identifies GIL / RLock serialization bottlenecks |
| **Compute & Memory Cost** | CPU % utilization, RSS (MB), Heap allocations | Quantifies resource growth with scale $N$ |
| **Kernel & OS Pressure** | Voluntary/involuntary context switches, Syscalls | Tracks OS kernel boundary overhead |
| **Persistence Latency** | WAL append time, `fsync` duration | Measures disk/durability write latency |
| **IPC Boundary Overhead** | Socket write/read roundtrip latency | Isolates runtime communication overhead |

---

## 4. Phase 50 Gate Structure

- **#50.a — Measurement Harness**: Construct `tests/performance/test_scheduler_benchmark.py` with synthetic workload generators, high-resolution timers (`time.perf_counter_ns`), memory tracking (`tracemalloc`), and thread contention hooks.
- **#50.b — Baseline Python Kernel**: Execute benchmark harness against unoptimized `ProductionDynamicLoadBalancer`.
- **#50.c — Runtime/Substrate Profiling**: Benchmark existing IPC and WAL persistence paths under load.
- **#50.d — Optimization Decision Gate**: Analyze bottleneck bottleneck distribution and evaluate candidate optimizations against the trade-off hierarchy.
