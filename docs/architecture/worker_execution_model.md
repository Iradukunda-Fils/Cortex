# CORTEX — WORKER EXECUTION, CONCURRENCY & WORKFLOW MODEL SPECIFICATION

**Document Identifier:** `CORTEX-SPEC-WORKER-2026-V1`  
**Classification:** Canonical Runtime Architecture Specification  
**Subsystem:** Worker Runtime, Concurrency Scheduling & Invocation Lifecycles  
**Status:** IMPLEMENTATION-VERIFIED & SPECIFICATION-LOCKED  

---

## 1. WORKER EXECUTION MODEL

> **Normative Model Definition:**  
> *Cortex workers are isolated execution agents. Individual worker plugin instances operate as **synchronous, process-blocking execution agents** per instance. A worker instance handling an invocation is unavailable to process concurrent independent requests until the active invocation handler returns.*

### Single-Worker Isolation vs Async Runtimes:
Cortex deliberately avoids running multi-tenant async request handlers inside a single worker process for untrusted plugin execution. Process-level separation provides strict containment:
```
+-------------------------------------------------------------------+
|  SINGLE WORKER PROCESS ISOLATION MODEL                            |
|                                                                   |
|   Worker Instance A (Process PID 101)  ──>  Single Event Handler  |
|   - Landlock Path Restrict (/tmp/sb_a)       (Synchronous/Blocked) |
|   - Seccomp Syscall Filter                                        |
|   - Zero shared state with Worker B                               |
+-------------------------------------------------------------------+
```

### Substrate Selection Matrix for Workloads:
Rather than forcing all plugins into an `asyncio` runtime, Cortex selects execution substrates based on workload semantics:

| Execution Class | Substrate Mechanism | Isolation Boundary | Concurrency Strategy |
| :--- | :--- | :--- | :--- |
| **CPU-Bound** | Single-Threaded Worker Process | cgroups v2 CPU/PID (Gate A) | Horizontal Replica Scaling |
| **I/O-Bound** | Worker Process + Local Async IO | cgroups v2 CPU/RAM (Gate A) | Gateway Inflight Queueing |
| **Long-Running / Media**| Dedicated Worker Process | cgroups v2 CPU/RAM/PID (Gate A) | Isolated Process + `ObjectRef` |
| **Interactive / PTY** | Gateway PTY Orchestration | TCB Complete Mediation | Virtual Terminal Streams |
| **Streaming Data** | Layer 2 CBE Pipe Buffer | 16 MiB Frame Ceiling | Stream Sockets |

---

## 2. SYSTEM CONCURRENCY & GATEWAY SCHEDULING

System-level concurrency in Cortex is achieved through three coordinated mechanisms:

$$\text{System Concurrency} = \sum_{g \in \text{ReplicaGroups}} \min\left(N_{\text{active\_replicas}}(g) \times \text{max\_worker\_inflight}, \text{max\_queue\_depth}\right)$$

1. **Bounded Worker Replicas:** `ReplicaGroupConfig` sets `min_replicas` and `max_replicas` (e.g., 1 to 10 instances). Independent requests are routed across ready replica processes (`router.py:270`).
2. **Gateway Least-Inflight Scheduling:** `CandidateResolver` and `RoutingPolicy` route new requests to ready worker instances with the minimum `observed_inflight` counter (`router.py:156`).
3. **In-Flight Limits:** Each worker instance is assigned a maximum inflight capacity `max_worker_inflight` (default 10). Excess requests buffer in `GatewayDispatcher` FIFO queues up to `max_queue_depth` (default 1000).

---

## 3. WORKFLOW ORCHESTRATION SEMANTICS

* **Current Implementation Status:** `DESIGNED ONLY` (Transient Event Bus).
* **Behavior:** Worker processes emit events via `PluginContext.publish()`. The Gateway forwards events to active workers whose manifests consume those event types (`consumes_events`).
* **Durability Guarantee:** Multi-step pipeline DAGs do NOT currently persist state across complete Gateway process restarts. Persistent durable workflow DAG orchestration is explicitly classified as a **future architectural capability**, not a current guarantee.

---

## 4. LONG-RUNNING JOB MODEL & RECOVERY BUCKETS

Long-running jobs are handled via an asynchronous state machine tracked in `InvocationStateLedger`:

$$\text{SUBMIT} \longrightarrow \text{QUEUED} \longrightarrow \text{ASSIGNED} \longrightarrow \text{RUNNING} \longrightarrow \text{COMMITTED / INDETERMINATE}$$

### Recovery Bucket Classification on Failure:
If a worker process crashes or drops connection during long-running execution:

1. **`UNADMITTED` / `ADMITTED_UNACTUATED`**: Work was not actuated or state modification did not occur. **Automatic Gateway retry is PERMITTED.**
2. **`ACTUATED_COMMITTED`**: Work was completed and committed under active `LeaseEpoch`. **No retry needed.**
3. **`ACTUATION_UNKNOWN`**: Work was in-flight during non-idempotent operation. Gateway transitions state to `INDETERMINATE` (a formal terminal state). **Automatic retry is STRICTLY FORBIDDEN** to prevent duplicate side effects.

---

## 5. PHYSICAL EXECUTION ENFORCEMENT (GATE A)

Worker processes are physically contained using Linux cgroups v2 enforcement, orchestrated by the `WorkerSupervisor` and `CgroupResourceEnforcer` subsystems:

| Resource | cgroup v2 Controller | Implementation Status |
| :--- | :--- | :--- |
| **CPU** | `cpu.max` (CFS quota/period) | **ADVERSARIALLY-TESTED** |
| **RAM** | `memory.max` | **ADVERSARIALLY-TESTED** |
| **PIDs** | `pids.max` | **ADVERSARIALLY-TESTED** |

The full specification, lifecycle sequence, and safety invariants are documented in:
- `docs/architecture/gate_a_physical_execution_isolation.md`
- Implementation: `cortex/tools/kernel/enforcement/`
- Tests: `tests/kernel/test_execution_enforcement_stress.py`

> **Note:** Seccomp-BPF syscall filtering and Landlock filesystem sandboxing are defined in the configuration schema but are not yet active at the OS enforcement level. They remain classified as **DESIGN ONLY**.
