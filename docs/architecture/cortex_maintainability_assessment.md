# Cortex Maintainability Assessment & Technical Debt Register

> **Assessment Methodology**: Codebase Static Inspection & Structural Coupling Audit  
> **Target Scope**: `cortex/` Python Core, `cortex/tools/kernel/`, Tests & Interfaces  

---

## 1. Architectural Coupling & Complexity Analysis

```
                                  PUBLIC API LAYER
                                  (cortex/client.py)
                                          │
                                          ▼
                               GATEWAY KERNEL ENGINE
                               (cortex/tools/kernel/)
                  ┌───────────────────────┼───────────────────────┐
                  ▼                       ▼                       ▼
            LoadBalancer          ResourceAuthority        ConfigResolver
             (37.1 KB)               (32.6 KB)               (24.4 KB)
                  │                       │                       │
                  └───────────────────────┼───────────────────────┘
                                          ▼
                               PERSISTENCE & ENFORCEMENT
                     ┌────────────────────┴───────────────────┐
                     ▼                                        ▼
              WriteAheadLog                          ExecutionEnforcer
                (6.6 KB)                                (cgroups v2)
```

### Module Size & Responsibility Matrix

| Subsystem Module | File Path | File Size | Primary Responsibility | Coupling (Fan-In / Fan-Out) | Complexity Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`load_balancer.py`** | `cortex/tools/kernel/load_balancer.py` | 37.1 KB | Worker registration, capability indexing, snapshot selection, leases | High / High | **High** (God Class tendency; combines routing, leases, and capability indexing) |
| **`resource_authority.py`** | `cortex/tools/kernel/resource_authority.py` | 32.6 KB | Vector budgets, reservations, TTL expiration, cgroups linking | High / Medium | **Medium-High** (Multi-resource tracking + containment linking) |
| **`config_resolver.py`** | `cortex/tools/kernel/config_resolver.py` | 24.4 KB | Multi-source resolution, canonicalization, schema validation, disk atomic persistence | Medium / Low | **Low-Medium** (Well-bounded declarative logic) |
| **`durable_state.py`** | `cortex/tools/kernel/durable_state.py` | 6.6 KB | CRC32 WAL framing, recovery, fsync, truncation | Medium / Low | **Low** (Clean single-responsibility module) |
| **`idempotency.py`** | `cortex/tools/kernel/idempotency.py` | 5.7 KB | Deduplication ledger & compaction | Medium / Low | **Low** (Clean encapsulation) |
| **`client.py`** | `cortex/client.py` | 11.6 KB | Public SDK surface & client submission API | High / High | **Low-Medium** (Clean progressive disclosure facade) |

---

## 2. Technical Debt Register

### Debt Item 1: `ProductionDynamicLoadBalancer` Monolithic Scope
- **Description**: `load_balancer.py` contains capability indexing, worker status state machine, lease epoch fencing, snapshot read views, quarantine tracking, and metrics recording in a single 37 KB file.
- **Risk**: Difficult to optimize lock granularity or replace capability indexing without touching lease fencing state.
- **Remediation Plan**: Refactor into three focused components: `WorkerRegistry`, `CapabilityIndex`, and `LeaseFencer`.

### Debt Item 2: Linear Vector Expiration in `ResourceAuthority`
- **Description**: Active reservations are stored in a Python list/dict and iterated sequentially on `expire_reservations()`.
- **Risk**: $O(N)$ execution time under critical section lock during background cleanup cycles.
- **Remediation Plan**: Replace linear scan with an explicit $O(\log N)$ min-heap priority queue ordered by `expiration_timestamp_ms`.

### Debt Item 3: Imperative Replica Draining vs Missing Autoscaling Loop
- **Description**: Replica policy types exist in `cortex.schema.scaling`, but `ReplicaManager` requires explicit imperative `scale_up()` / `scale_down()` calls.
- **Risk**: Operators or higher-level frameworks must build external controller loops to implement actual autoscaling.
- **Remediation Plan**: Implement an explicit `AutoscalingController` background loop with queue depth hysteresis and cooldown windows.

---

## 3. Replaceability & Abstraction Integrity

| Component | Semantic Contract Stable? | Implementation Replaceable Without API Change? | Coupling Bottlenecks |
| :--- | :--- | :--- | :--- |
| **Scheduler / Load Balancer** | Yes | Yes (Abstract `AdapterContract` pattern) | Global `RLock` in worker registry |
| **Resource Authority** | Yes | Yes | Physical `cgroups v2` file handle dependencies |
| **WAL Backend** | Yes | Yes (Binary frame specification strictly typed) | Disk I/O sync latency |
| **CBE Transport** | Yes | Yes (Polyglot wire protocol spec in `cbe/`) | Memory copies during Python bytes unmarshalling |
