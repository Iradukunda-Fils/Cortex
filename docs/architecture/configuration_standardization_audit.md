# Cortex Configuration Standardization & Control Plane Audit

**Reviewer Role:** Principal Systems Architect & Low-Level Distributed Systems Engineer  
**Scope:** Phase 4 Control Plane Configuration Infrastructure & Worker Execution Substrate  
**Status:** IMPLEMENTATION AUDITED & CANONICALIZED  
**Audit Date:** 2026-08-21  

---

## Architectural Pipeline Principle

In the Cortex Control Plane architecture, configuration is treated as **system policy and execution substrate**. To prevent misconfigurations, security ceiling breaches, or runtime TOCTOU race conditions, configuration processing follows a strict 10-stage linear pipeline:

```
  [1] PARSE INPUT PAYLOAD (JSON/YAML)
           ↓
  [2] DEFAULT MATERIALIZATION (Apply normative schema default values)
           ↓
  [3] SCHEMA VALIDATION (Validate structure against https://cortex.security/schemas/v1/configuration.schema.json)
           ↓
  [4] SEMANTIC VALIDATION (Cross-field constraints, e.g. 1 <= min_replicas <= max_replicas)
           ↓
  [5] SECURITY CEILING ENFORCEMENT (Clamp to host non-degradable security ceiling)
           ↓
  [6] VOCABULARY NORMALIZATION (Translate legacy aliases to canonical snake_case)
           ↓
  [7] CANONICAL ENCODING (CBE / Sorted UTF-8 key-value pairs)
           ↓
  [8] SHA-256 DIGEST COMPUTATION (Compute 64-char hex config_hash)
           ↓
  [9] IMMUTABLE SNAPSHOT CREATION (Bind config_hash to DesiredConfig)
           ↓
 [10] GENERATION BINDING (Assign monotonic config_generation = N + 1)
```

> [!IMPORTANT]
> **Hot-Path Invariant:** Configuration resolution, schema validation, and SHA-256 canonical hashing MUST execute **ONCE** at gateway initialization or configuration reload. An invocation NEVER parses or canonicalizes configuration; it references an already-validated, immutable configuration snapshot (`ExecutionIdentity.config_generation` + `config_hash`).

---

## A. Formal Configuration Consistency Matrix

Every field across the Cortex configuration surface is mapped below to guarantee total parity across Audit, Schema, CLI, Environment, Runtime, and Security specifications:

| Field Name | Canonical Name | Schema Path | Data Type | Units / Range | Default | Required? | Security Class | CLI Permitted? | Env Permitted? | Runtime Mutable? | Gen Changing? | Drain Req? | Hash Input? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `schema_version` | `schema_version` | `schema_version` | String | Enum (`1.0.0`) | N/A | Yes | Governance | No | No | No | Yes | Yes | Yes |
| `max_queue_depth` | `max_queue_depth` | `gateway.max_queue_depth` | Integer | [1, 10000] | 1000 | Yes | Operational | Yes | Yes | Yes | Yes | No | Yes |
| `max_worker_inflight` | `max_worker_inflight` | `gateway.max_worker_inflight` | Integer | [1, 100] | 10 | Yes | Operational | Yes | Yes | Yes | Yes | No | Yes |
| `queue_timeout_sec` | `queue_timeout_sec` | `gateway.queue_timeout_sec` | Float | [0.1, 300.0] | 30.0 | Yes | Operational | Yes | Yes | Yes | Yes | No | Yes |
| `dispatch_deadline_sec`| `dispatch_deadline_sec`| `gateway.dispatch_deadline_sec`| Float | [0.1, 60.0] | 5.0 | Yes | Operational | Yes | Yes | Yes | Yes | No | Yes |
| `selection_policy` | `selection_policy` | `gateway.selection_policy` | String | Enum | `least_inflight_deterministic` | Yes | Policy | Yes | Yes | Yes | Yes | No | Yes |
| `journal_path` | `journal_path` | `gateway.journal_path` | String | Absolute Path | `/var/log/cortex/invocation_journal.jsonl` | Yes | TCB State | No | No | No | Yes | Yes | Yes |
| `fsync_policy` | `fsync_policy` | `gateway.fsync_policy` | String | Enum (`always`, `batch`, `never`) | `always` | Yes | Durability | No | Yes | No | Yes | Yes | Yes |
| `group_id` | `group_id` | `replica_group.group_id` | String | Regex (`^[a-z0-9_-]+$`) | N/A | Yes | Identity | No | No | No | Yes | Yes | Yes |
| `min_replicas` | `min_replicas` | `replica_group.min_replicas` | Integer | [1, 1000] | 1 | Yes | Scaling | Yes | Yes | Yes | Yes | No | Yes |
| `max_replicas` | `max_replicas` | `replica_group.max_replicas` | Integer | [1, 1000] | 10 | Yes | Scaling | Yes | Yes | Yes | Yes | No | Yes |
| `drain_deadline_sec` | `drain_deadline_sec` | `replica_group.drain_deadline_sec` | Float | [1.0, 300.0] | 30.0 | Yes | Operational | Yes | Yes | Yes | Yes | No | Yes |
| `profile_name` | `profile_name` | `sandbox.profile_name` | String | Enum (`Profile_A_Linux_Strict`) | `Profile_A_Linux_Strict` | Yes | Security Boundary | No | No | No | Yes | Yes | Yes |
| `required_capabilities`| `required_capabilities`| `sandbox.required_capabilities`| Array | Namespace Strings | N/A | Yes | Security Boundary | No | No | No | Yes | Yes | Yes |
| `allowed_syscalls` | `allowed_syscalls` | `sandbox.allowed_syscalls` | Array | Syscall Names | Profile A Default | Yes | Security Boundary | No | No | No | Yes | Yes | Yes |
| `landlock_paths` | `landlock_paths` | `sandbox.landlock_paths` | Array | Absolute Paths | Profile A Default | Yes | Security Boundary | No | No | No | Yes | Yes | Yes |
| `read_only_root` | `read_only_root` | `sandbox.read_only_root` | Boolean | True / False | True | Yes | Security Boundary | No | No | No | Yes | Yes | Yes |
| `allowed_write_paths` | `allowed_write_paths` | `sandbox.allowed_write_paths` | Array | Absolute Paths | `["/tmp/sandbox_default"]` | Yes | Security Boundary | No | No | No | Yes | Yes | Yes |
| `memory_limit_mb` | `memory_limit_mb` | `resource_limits.memory_limit_mb` | Integer | [64, 32768] | 512 | Yes | Resource Ceiling | Yes | Yes | Yes | Yes | Yes | Yes |
| `cpu_quota_percent` | `cpu_quota_percent` | `resource_limits.cpu_quota_percent` | Integer | [10, 1600] | 100 | Yes | Resource Ceiling | Yes | Yes | Yes | Yes | No | Yes |

---

## B. Field-Level Precedence & Security Protection Matrix

To protect security boundaries and identity fields from unauthorized CLI or environment variable manipulation, precedence rules are defined **per field category**:

| Category | Fields | CLI Override Permitted? | ENV Override Permitted? | File / Manifest Permitted? | Host Security Ceiling Override? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Operational Limits** | `max_queue_depth`, `max_worker_inflight`, `queue_timeout_sec`, `dispatch_deadline_sec`, `drain_deadline_sec` | **Yes** | **Yes** | **Yes** | Clamped to Host Ceiling |
| **Scaling & Policy** | `min_replicas`, `max_replicas`, `selection_policy`, `memory_limit_mb`, `cpu_quota_percent` | **Yes** | **Yes** | **Yes** | Clamped to Host Ceiling |
| **Durability & Journal** | `journal_path`, `fsync_policy` | **No** (CLI Rejected) | **Env Only** (fsync) | **Yes** | Fixed by Host TCB |
| **Identity & Group** | `schema_version`, `group_id` | **No** (CLI Rejected) | **No** (ENV Ignored) | **Yes** | Fixed by Manifest |
| **Security Boundaries** | `profile_name`, `required_capabilities`, `allowed_syscalls`, `landlock_paths`, `read_only_root`, `allowed_write_paths` | **No** (CLI Rejected) | **No** (ENV Ignored) | **Yes** (Signed Manifest Only) | **Host Security Ceiling Overrides Manifest** |

---

## C. Monotonic Rollback Generation Semantics

When rolling back to a historical configuration payload, `config_generation` counter MUST remain strictly monotonic to preserve causal auditability:

```
[Generation 17] (Payload A, Hash H_A)
       ↓ (Config Change)
[Generation 18] (Payload B, Hash H_B)
       ↓ (Rollback requested to Payload A)
[Generation 19] (Payload A, Hash H_A)
```

> [!IMPORTANT]
> **Rollback Rule:** A configuration rollback NEVER decrements `config_generation`. It instantiates a NEW monotonic generation ($N+1$) containing the historical configuration payload. Worker replicas evaluate generation monotonicity ($19 > 18$) while verifying that the active config hash matches $H_A$.

---

## D. Security-Ceiling & Path Escalation Safeguards

- **Syscall Boundaries:** Attempts to add forbidden system calls (e.g. `ptrace`, `kexec_load`, `bpf`) in `sandbox.allowed_syscalls` are caught at Stage 5 (`SECURITY CEILING ENFORCEMENT`) and cause immediate payload rejection.
- **Path Escalation Protection:** Write paths in `sandbox.allowed_write_paths` MUST be absolute, normalized, contain no symlinks or `..` traversals, and strictly reside under `/tmp/sandbox_*`.

---

## E. Findings & Resolutions Log

#### FIND-CFG-001: Aliased Timeout & Limit Parameter Names
- **Classification:** `MEDIUM`
- **Resolution:** Standardized on `queue_timeout_sec` and `max_worker_inflight` across all schema reference files and CLI parsers.
- **Status:** REMEDIATED & VERIFIED

#### FIND-CFG-002: Canonical Key Ordering Prior to SHA-256 Hashing
- **Resolution:** Enforced Canonical Binary Encoding (CBE) sorted key-value serialization prior to SHA-256 hash generation.
- **Status:** REMEDIATED & VERIFIED

#### FIND-CFG-003: Schema Namespace Identity Divergence
- **Classification:** `HIGH`
- **Resolution:** Aligned JSON Schema `$id` to `https://cortex.security/schemas/v1/configuration.schema.json`, matching the established Coq/CBE project namespace.
- **Status:** REMEDIATED & VERIFIED

#### FIND-CFG-004: Audit vs Schema Field Coverage Parity
- **Classification:** `HIGH`
- **Resolution:** Expanded JSON Schema to cover all 19 configuration parameters defined in the audit matrix.
- **Status:** REMEDIATED & VERIFIED
