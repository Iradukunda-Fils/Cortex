# Cortex Full System Architecture Audit

> **Audit Type**: Full-System Architecture, Security, Scalability & Maintainability Audit  
> **Repository Baseline**: Ground-Truth Codebase Inspection & Verification (474 Passed Tests)  
> **Governance Invariant**: $\text{Evidence Strength} \ge \text{Documentation Claim Strength}$  
> **Current Architectural Boundary**: $\text{Cortex Today} = \text{Single-Host Control Plane} + \text{Local Worker Execution}$  

---

## Executive Summary & System Reconstruction

Cortex is an architectural control plane and worker execution framework designed for high-assurance task scheduling, resource containment, durable state management, and plugin execution on a single physical host.

This audit reconstructs the real implementation of Cortex directly from repository source code, execution traces, test suites, formal models, and performance benchmarks.

### Core System Blueprint

```
                                  PUBLIC API / SDK
               ┌─────────────────────────────────────────────────────┐
               │ CortexClient | Task Decorator | Declarative Config  │
               └──────────────────────────┬──────────────────────────┘
                                          │
                                          ▼
                                   GATEWAY KERNEL
               ┌─────────────────────────────────────────────────────┐
               │                                                     │
               │  ┌───────────────────────┐ ┌──────────────────────┐  │
               │  │  ConfigResolver       │ │ IdempotencyLedger    │  │
               │  │  (Schema, Normalizer) │ │ (Deduplication)      │  │
               │  └───────────┬───────────┘ └──────────┬───────────┘  │
               │              │                        │              │
               │              ▼                        ▼              │
               │  ┌───────────────────────────────────────────────┐  │
               │  │      ProductionDynamicLoadBalancer            │  │
               │  │  (CapabilityIndex, LeaseEpoch, Quarantines)   │  │
               │  └───────────┬───────────┴────────────┘  │
               │              │                        │              │
               │              ▼                        ▼              │
               │  ┌───────────────────────┐ ┌──────────────────────┐  │
               │  │  ResourceAuthority    │ │ WriteAheadLog (WAL)  │  │
               │  │  (Vector Allocations) │ │ (CRC32, fsync)       │  │
               │  └───────────┬───────────┘ └──────────┬───────────┘  │
               │              │                        │              │
               └──────────────┼────────────────────────┼──────────────┘
                              │                        │
                              ▼                        ▼
                       PHYSICAL CONTAINMENT     IPC & TRANSPORT
               ┌──────────────────────┐ ┌──────────────────────┐
               │ ExecutionEnforcer    │ │ CBE Binary Protocol  │
               │ (cgroups v2 / Sudo)  │ │ (Framing, Serialization)
               └──────────────────────┘ └──────────────────────┘
```

---

## 1. Subsystem Architecture Analysis

### A. Load Balancing & Capability Scheduling (`load_balancer.py`)
- **Implementation**: `ProductionDynamicLoadBalancer` maintains an inverted index of worker capabilities (`CapabilityIndex`).
- **Synchronization**: Protected by a single `threading.RLock` (`self._lock`).
- **Selection Semantics**: `select_target_worker` evaluates candidates in capability set $W_c$. Supports point-in-time Snapshot Read View ($V = f(S_A)$) to allow unlocked candidate evaluation, followed by locked assignment (`assign_execution`).
- **Lease Fencing**: Worker leases tracked via monotonic `LeaseEpoch` ($e \to e + 1$). Stale epoch commit attempts are rejected with `ERR_STALE_LEASE_EPOCH`.

### B. Resource Authority & Containment (`resource_authority.py`, `enforcement/`)
- **Vector Allocation**: Tracks CPU (millicores), RAM (MB), GPU (count), VRAM (MB), IOPS, and FDs.
- **State Lifecycle**: $\text{Observation} \rightarrow \text{Authority} \rightarrow \text{Reservation} \rightarrow \text{Enforcement} \rightarrow \text{Execution} \rightarrow \text{Observation} \rightarrow \text{Release}$.
- **Physical Containment**: Integrates with Linux `cgroups v2` via `/sys/fs/cgroup/cortex`. Falls back to `ProcessDriver` or unconstrained process execution when cgroups v2 or root privileges are unavailable.

### C. Write-Ahead Log & Idempotency (`durable_state.py`, `idempotency.py`)
- **Durable Persistence**: `WriteAheadLog` appends CRC32-framed binary records (`0x434F5254`) with immediate `os.fsync()`. Tail corruption is detected via CRC32 validation and truncated during recovery.
- **Deduplication**: `InvocationLedger` prevents duplicate task actuation based on `idempotency_key`. Supports compaction and TTL expiration.

### D. Declarative Configuration Resolver (`config_resolver.py`)
- **Precedence Hierarchy**: `CLI Flags` > `Environment Variables` > `Config File (YAML/JSON)` > `Defaults`.
- **Field-Class Normalization**: Identifiers normalized to ASCII snake_case; human text to Unicode NFC; sets to sorted unique lists.
- **Persistence**: Atomic file writes via tempfile + `fsync` + `os.replace`.

### E. Polyglot & CBE Transport Architecture (`cbe/`, `cortex-go/`)
- **CBE Protocol**: Binary wire framing with fixed 8-byte headers, magic bytes, and payload type tagging.
- **Cross-Language Bindings**: Go implementation in `cortex-go/`, Python implementation in `cortex/cbe/`, RTL Verilog verification in `rtl/`.

---

## 2. Invariant Verification Matrix

| Invariant ID | Name | Description | Verification Status | Source Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **$I_1$** | Capacity Safety | Total reserved resources $\le$ Host capacity | `RUNTIME-VERIFIED` | `test_phase7_resource_authority.py` |
| **$I_2$** | Monotonic Lease Epoch | LeaseEpoch strictly increases per worker re-assignment within single-host boundary | `PROVEN` & `RUNTIME-VERIFIED` | `test_load_balancer.py`, `cortex_reservation_safety.v` |
| **$I_3$** | Capability Bound | Worker executed tasks $\subseteq$ Declared worker capabilities | `RUNTIME-VERIFIED` | `test_v020_capability_enforcement.py` |
| **$I_4$** | CRC32 Framing Integrity | WAL frame payloads must match 32-bit CRC | `ADVERSARIALLY-TESTED` | `test_phase6_wal_adversarial_gate.py` |
| **$I_5$** | Atomic Config Generation | Config updates increment generation atomically via fsync | `RUNTIME-VERIFIED` | `test_cli_env_precedence.py` |
| **$I_6$** | Idempotent Actuation | Task with identical `idempotency_key` executes at most once | `ADVERSARIALLY-TESTED` | `test_idempotency_engine.py` |
| **$I_7$** | Fail-Closed Containment | Physical enforcement failure rejects task under strict mode | `RUNTIME-VERIFIED` | `test_execution_enforcement.py` |
| **$I_8$** | Worker Quarantine Isolation | Quarantined workers receive zero new task assignments | `RUNTIME-VERIFIED` | `test_load_balancer_hardening_gate.py` |
| **$I_9$** | Index Consistency | `CapabilityIndex` matches registered worker capability sets | `RUNTIME-VERIFIED` | `test_scheduler_benchmark.py` |
| **$I_{10}$**| Tail Corruption Recovery | Corrupted WAL tails are truncated without losing prior frames | `ADVERSARIALLY-TESTED` | `test_phase6_durable_state.py` |
| **$I_{11}$**| Single Commit Owner | Exactly one worker holds authoritative lease per invocation | `MODEL-CHECKED` | `verification/tla/LeaseFencing.tla` |
| **$I_{12}$**| Bounded Queue Backpressure | Admissions shed or reject when max_queue_depth reached | `RUNTIME-VERIFIED` | `test_developer_executable_contract.py` |

---

## 3. Subsystem Architecture Verdict Matrix

| Area / Subsystem | Ground-Truth Verdict | Architectural Rationale & Evidence |
| :--- | :--- | :--- |
| **Public API Architecture** | **Strong** | Clean progressive disclosure surface (`CortexClient`, `@task`). |
| **Authority Separation** | **Strong** | Clear separation between Gateway TCB ownership and worker runtimes. |
| **Resource Reservation Model** | **Strong Foundation** | Precise multi-resource vector budgets ($\text{CPU}, \text{RAM}, \text{GPU}, \text{VRAM}, \text{IOPS}, \text{FDs}$). |
| **WAL Architecture** | **Strong but Scope-Bounded** | Record/replay safety demonstrated via CRC32 + fsync + tail truncation; full durability depends on end-to-end transaction boundary. |
| **Worker Lifecycle** | **Strong Foundation** | Explicit FSM transitions (`READY` $\to$ `DRAINING` $\to$ `QUIESCED` $\to$ `TERMINATING`). |
| **Capability Indexing** | **Effective Optimization** | Solves $O(N)$ candidate selection scan by maintaining inverted $W_c$ index. |
| **Physical Enforcement** | **Established for Current Slice, Incomplete Overall** | cgroups v2 implemented on Linux root; falls back to unconstrained process execution on non-root/macOS. |
| **Automatic Autoscaling** | **Not Yet Implemented** | Policy dataclasses exist, but no background dynamic controller loop exists. |
| **Distributed Authority** | **Future Architecture** | Operates strictly as single-host control plane today; Raft consensus is un-implemented. |
| **Scheduler Concurrency** | **Current Major Research Bottleneck** | Authoritative mutation locking introduces lock wait wall ($T_{wait}$) at scale. |
| **Reservation Expiration** | **Known $O(N)$ Scalability Issue** | `expire_reservations()` scans active reservations linearly under lock. |
| **Rust/Go Gateway Migration** | **Premature Until Further Evidence** | Changing language before isolating the authority serialization bottleneck risks porting the same lock bottleneck. |
| **100-Year Maintainability** | **Promising Architecture, Not Demonstrated** | Good single-host foundation, but long-term multi-decade evolution requires empirical research validation. |
