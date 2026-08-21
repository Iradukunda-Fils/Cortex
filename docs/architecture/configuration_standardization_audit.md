# Cortex Configuration Standardization & Control Plane Audit

**Reviewer Role:** Principal Systems Architect & Low-Level Distributed Systems Engineer  
**Scope:** Phase 4 Control Plane Configuration Infrastructure & Worker Execution Substrate  
**Status:** IMPLEMENTATION AUDITED & CANONICALIZED  
**Audit Date:** 2026-08-21  

---

## Architectural Pipeline Principle

In the Cortex Control Plane architecture, configuration is treated as **system policy and execution substrate**. To prevent misconfigurations, security ceiling breaches, or runtime TOCTOU race conditions, configuration processing follows a strict 12-stage linear pipeline:

```
[CONFIG SOURCE]
      ↓
  [RESOLVE]
      ↓
  [VALIDATE]
      ↓
[SECURITY CEILING]
      ↓
  [NORMALIZE]
      ↓
 [CANONICALIZE]
      ↓
    [HASH]
      ↓
[IMMUTABLE SNAPSHOT]
      ↓
[CONFIG GENERATION]
      ↓
 [DESIRED STATE]
      ↓
  [RECONCILER]
      ↓
 [OBSERVED STATE]
```

> [!IMPORTANT]
> **Hot-Path Invariant:** Configuration resolution, schema validation, and SHA-256 canonical hashing MUST execute **ONCE** at gateway initialization or configuration reload. An invocation NEVER parses or canonicalizes configuration; it references an already-validated, immutable configuration snapshot (`ExecutionIdentity.config_generation` + `config_hash`).

---

## A. Configuration Source Matrix

Cortex accepts configuration inputs from 5 distinct sources:

| Source ID | Source Type | Location / Primitive | Format / Protocol | Security Context |
| :--- | :--- | :--- | :--- | :--- |
| **SRC-1** | System Defaults | Internal code defaults | Built-in immutable dataclasses | Trusted Base |
| **SRC-2** | File System Config | `/etc/cortex/cortex.yaml`, `./manifest.yaml` | YAML 1.2 / JSON | Host Filesystem (0600) |
| **SRC-3** | Environment Vars | `CORTEX_*` env prefix | String / UTF-8 | Host Environment |
| **SRC-4** | CLI Arguments | `cortex` CLI flags | Argparse / Text | Invoking User Shell |
| **SRC-5** | Control Plane API | Gateway API endpoint | CBE Canonical Framing | Dynamic Control Plane |

---

## B. Field Classification Matrix

All configuration parameters are strictly classified into 4 functional tiers:

| Field Category | Primary Parameters | Security Scope | Mutation Semantics |
| :--- | :--- | :--- | :--- |
| **Sandbox & Isolation** | `sandbox_profile`, `allowed_syscalls`, `landlock_paths`, `read_only_root` | Host Security Ceiling | Immutable without Drain |
| **Resource Limits** | `max_worker_inflight`, `max_queue_depth`, `memory_limit_mb`, `cpu_quota` | Resource Boundedness | Hot Reloadable via Generation |
| **Routing & Dispatch** | `selection_policy`, `queue_timeout_sec`, `dispatch_deadline_sec` | Execution Control | Hot Reloadable via Generation |
| **Identity & Ledger** | `group_id`, `journal_path`, `fsync_policy` | TCB Durability | Immutable Snapshot |

---

## C. Precedence Matrix

When configuration parameters overlap across multiple sources, precedence is strictly evaluated in descending order (highest priority first):

```
1. CLI Arguments (SRC-4)                  [HIGHEST PRECEDENCE]
2. Environment Variables (SRC-3)
3. Manifest / Control File (SRC-2)
4. System Default Fallbacks (SRC-1)       [LOWEST PRECEDENCE]
```

> [!WARNING]
> **Security Ceiling Rule:** Security ceiling boundaries (`SECURITY CEILING`) override user-specified CLI flags or manifest parameters if the requested privileges exceed host security ceilings (e.g. attempting to grant unauthorized syscalls or raw device access).

---

## D. Mutability Matrix

Runtime mutability semantics for every configuration field are classified as follows:

| Field Name | Hot Reloadable? | Existing Workers Action | New Workers Action | Requires New Generation? | Requires Worker Drain? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `max_worker_inflight` | Yes | Retain old limit until re-registered | Use new limit | Yes (`gen+1`) | No |
| `queue_timeout_sec` | Yes | In-flight queued invocations retain old timeout | New invocations use new timeout | Yes (`gen+1`) | No |
| `max_queue_depth` | Yes | Applies immediately to queue admission | Applies immediately | Yes (`gen+1`) | No |
| `sandbox_profile` | No | Retain old profile | Refused until drained | Yes (`gen+1`) | **Yes (Full Drain)** |
| `required_capabilities`| No | Retain old envelope | Refused until drained | Yes (`gen+1`) | **Yes (Full Drain)** |
| `journal_path` | No | Retain active file descriptor | Open new journal | Yes (`gen+1`) | **Yes (Full Drain)** |

---

## E. Security-Ceiling Matrix

The TCB enforces non-degradable security ceilings that restrict worker capabilities regardless of source values:

| Security Domain | Host Ceiling | Manifest / CLI Request | Resolved State | Enforcement Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **Syscall Filtering** | Profile A Seccomp (Denied: `ptrace`, `kexec`, `reboot`) | Requested `ptrace` | **DENIED & REJECTED** | Seccomp BPF Filter |
| **Filesystem Access** | Read-only root, Write: `/tmp/sandbox_*` | Requested Write: `/etc` | **DENIED & REJECTED** | Landlock ABI / Chroot |
| **Network Access** | Host loopback isolated namespace | Requested raw socket | **DENIED & REJECTED** | `CLONE_NEWNET` Namespace |
| **Memory Ceiling** | Hard ceiling: 512 MB per worker | Requested: 4096 MB | **CLAMPED to 512 MB** | Cgroups v2 `memory.max` |

---

## F. Schema / Version Matrix

- **Canonical Schema:** `docs/architecture/configuration_schema_reference.md`
- **Schema Versioning:** Strict `v1.0.0` semantic versioning.
- **Backward Compatibility:** Schema parsers MUST reject unknown or duplicate fields in strict mode (`extra = "forbid"`), preventing configuration injection attacks.

---

## G. Generation & Hash Lifecycle

1. **Resolution & Normalization:** All inputs are merged, normalized to `snake_case`, and converted into canonical sorted key-value structures.
2. **Canonical Serialization:** Configuration is serialized using Canonical Binary Encoding (CBE) or canonical sorted JSON.
3. **SHA-256 Digest:** A 256-bit SHA-256 hash (`config_hash`) is computed over the canonical byte stream.
4. **Generation Increment:** `config_generation` increments by 1 for every modification to the normalized configuration payload.
5. **Worker Attestation:** Worker replicas attest their `config_generation` and `config_hash` during registration.

```python
# Canonical Generation Lifecycle
canonical_bytes = cbe_encode(sort_keys(normalized_config))
config_hash = hashlib.sha256(canonical_bytes).hexdigest()
config_generation = previous_generation + 1
snapshot = ImmutableConfigSnapshot(generation=config_generation, hash=config_hash, payload=normalized_config)
```

---

## H. Rollout / Rollback Model

- **Desired vs Observed State Reconciliation:**
  - The Gateway reconciler continuously compares `ObservedState(worker)` against `DesiredState(config_generation)`.
  - When `config_generation` updates, workers with outdated generations transition from `READY` to `DRAINING`.
- **Atomic Rollback:** Rollback to a previous configuration snapshot re-activates the prior `config_hash` and `config_generation`, triggering immediate re-drain of incompatible workers.

---

## I. Default-Value Audit

All system defaults are audited for safe fail-closed operation:

| Component | Parameter | Default Value | Safety Rationale |
| :--- | :--- | :--- | :--- |
| `GatewayDispatcher` | `max_queue_depth` | `1000` | Prevents unbounded memory growth on backpressure |
| `GatewayDispatcher` | `max_worker_inflight` | `10` | Prevents worker overload and GIL/CPU starvation |
| `GatewayDispatcher` | `queue_timeout_sec` | `30.0` | Bounds queued latency prior to `ERR_QUEUE_TIMEOUT` |
| `GatewayDispatcher` | `dispatch_deadline_sec` | `5.0` | Prevents head-of-line blocking on dispatch stall |
| `WorkerLifecycleTracker`| `drain_deadline_sec` | `30.0` | Bounds graceful worker drain before forced SIGKILL |

---

## J. Resource-Limit Audit

Resource limits are strictly bounded to maintain deterministic system performance:

| Resource | Hard Limit | Soft Limit | Failure Mode |
| :--- | :--- | :--- | :--- |
| **Gateway Invocations Queue** | 1,000 requests | 800 requests | `QueueFullError` (Exit Code 1) |
| **Worker Inflight Concurrency** | 10 per worker | 8 per worker | Excluded from `CandidateResolver` |
| **State Domain Locks** | 10,000 active keys | 5,000 active keys | `ValueError` (Lock Conflict) |
| **Journal File Compaction** | 50,000 lines | 10,000 lines | Automatic atomic snapshot compaction |

---

## K. Configuration Drift Model

Configuration drift occurs when a running worker process mutates its local state or when environment variables change out-of-band:
- **Detection Mechanism:** The Gateway `CandidateResolver` verifies `w.config_generation == active_config_gen` and `w.config_hash == active_config_hash` on every dispatch.
- **Drift Remediation:** If a worker reports a mismatched hash, it is instantly excluded from candidate resolution (`RD-2`, `RD-3`) and queued for termination.

---

## L. Secret Separation Review

- **Zero Secrets in Configuration:** Passwords, API keys, and bearer tokens are strictly forbidden from configuration files and manifest payloads.
- **Identity Isolation (RD-22):** `WorkerRef`, `CandidateResolver`, and `RoutingPolicy` contain zero secret keys or access tokens. Authentication occurs strictly at the TCB boundary via IPC Unix socket credentials.

---

## M. Configuration Naming Consistency Review

Audit of existing codebase configuration naming conventions:

### Vocabulary Normalization Table

| Deprecated / Non-Standard Name | Canonical Vocabulary Name | Domain | Action Taken |
| :--- | :--- | :--- | :--- |
| `queue_timeout_seconds` | `queue_timeout_sec` | Dispatcher | Standardized to `queue_timeout_sec` |
| `max_inflight` | `max_worker_inflight` | Worker Pool | Standardized to `max_worker_inflight` |
| `configGen` (camelCase) | `config_generation` | Replica | Converted to `snake_case` |
| `configHash` (camelCase) | `config_hash` | Replica | Converted to `snake_case` |
| `sandboxHash` | `sandbox_profile_hash` | Security | Standardized to `sandbox_profile_hash` |
| `capHash` | `capability_envelope_hash` | Security | Standardized to `capability_envelope_hash` |

---

## N. Findings

#### FIND-CFG-001: Aliased Timeout & Limit Parameter Names
- **Classification:** `MEDIUM`
- **Finding:** Inconsistent naming between CLI flags (`--queue-timeout`), documentation (`queue_timeout_seconds`), and kernel Python code (`queue_timeout_sec`).
- **Impact:** Potential developer confusion during configuration file authoring.
- **Required Remediation:** Adopt `docs/architecture/configuration_schema_reference.md` as the sole normative specification; add backward-compatible alias translation in CLI parser.
- **Status:** OPEN

#### FIND-CFG-002: In-Memory Uncanonicalized Environment Overrides
- **Classification:** `LOW`
- **Finding:** Environment variable parser did not sort keys before SHA-256 hash calculation in legacy utility scripts.
- **Impact:** Different environment variable order produced different config hashes for identical semantic configurations.
- **Required Remediation:** Enforce canonical key sorting (`sort_keys()`) prior to SHA-256 hashing.
- **Status:** OPEN
