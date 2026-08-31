# Cortex Resource Safety Matrix

> **Lifecycle Formula**: $Observation \rightarrow Authority \rightarrow Reservation \rightarrow Enforcement \rightarrow Execution \rightarrow Observation \rightarrow Release$  
> **Normative Boundary**: Every system resource MUST satisfy: $Bound + Admission + Backpressure + Recovery + Telemetry$.  

---

## 1. Resource Lifecycle Matrix

| Resource | Observation Mechanism | Authority Engine | Reservation Model | Physical Enforcement | Admission & Backpressure Boundary | Failure Recovery | $X \to \infty$ Protection |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CPU (mcores)** | `ResourceAuthority` tracking | `ResourceAuthority` budget check | `VectorResourceSpec` reservation | Linux `cgroups v2` (`cpu.max`) | Reject allocation if total CPU requested > available | Auto-release on task completion or timeout | Enforced upper bound on total host core allocation |
| **RAM (MB)** | `ResourceAuthority` tracking | `ResourceAuthority` budget check | `VectorResourceSpec` reservation | Linux `cgroups v2` (`memory.max`) | Reject allocation if total memory requested > budget | OOM kill by Linux kernel; worker quarantined | Fail-closed under strict mode; OOM limit prevents host exhaustion |
| **GPU / VRAM** | GPU device index tracking | `ResourceAuthority` budget check | Device index reservation set | Device assignment isolation | Reject allocation if requested GPU count > host GPUs | Release reservation on worker termination | Exclusive GPU index tracking prevents double allocation |
| **File Descriptors**| Host OS FD check | Gateway process spawner | FD limit check per process | OS `ulimit -n` & explicit `close_fds=True` | Socket pool size cap | Explicit FD cleanup in `finally` blocks | `test_v021_security_audit` verifies zero socket leaks |
| **Task Queue Depth**| In-memory queue counter | `ProductionDynamicLoadBalancer` | Bounded queue buffer | `max_queue_depth` limit | Return `BackpressureError` (`ERR_QUEUE_FULL`) | Dropped/shed requests return immediate error | Queue cap prevents RAM growth under burst traffic |
| **WAL Storage** | Disk usage check | `WriteAheadLog` engine | Sequential log segment allocation | Segment size threshold | Log rotation & compaction | Truncate corrupted tail on crash recovery | Ledger compaction purges stale log entries |
| **Idempotency Keys**| Invocation ledger count | `InvocationLedger` | In-memory key tracking | `max_ledger_capacity` threshold | Evict oldest keys when capacity exceeded | Retention TTL purge loop | Compaction prevents unbounded dictionary expansion |

---

## 2. Exhaustion Risk & Protection Audit ($X \to \infty$)

### Risk 1: Worker Registration Churn
- **Path**: $N_{workers} \to \infty$ due to frequent worker restarts generating unique worker IDs without pruning metrics.
- **Protection**: `max_quarantine_records` limits quarantine list size. Metrics dictionaries must be garbage-collected upon `RETIRED` state transition.

### Risk 2: Task Backpressure Shedding
- **Path**: Task queue accumulation under worker pool saturation.
- **Protection**: `max_queue_depth` triggers immediate backpressure rejection (`ERR_QUEUE_FULL`), enforcing $O(1)$ memory ceiling.

### Risk 3: Un-compacted WAL Accumulation
- **Path**: Append-only log growing indefinitely on disk.
- **Protection**: Compaction protocol snapshotting valid state and truncating old WAL frames.
