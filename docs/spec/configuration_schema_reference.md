# Cortex Canonical Configuration Schema Reference

**Version:** `v1.0.0`  
**Schema Identifier ($id):** `https://cortex.security/schemas/v1/configuration.schema.json`  
**Status:** NORMATIVE SPECIFICATION  
**Scope:** Control Plane, Gateway Dispatcher, & Worker Replica Desired State Configuration  

---

## 1. Governance & Source of Truth Hierarchy

This document defines the authoritative, normative configuration schema for the Cortex Control Plane and Execution Engine. Configuration resolution follows a strict single-directional authority hierarchy:

```
    JSON Schema ($id: https://cortex.security/schemas/v1/configuration.schema.json)
                                   ↓
                  Canonical Configuration Reference
                                   ↓
                   Resolver / DesiredConfig Engine
                                   ↓
      Adapters & Loaders (Manifest YAML / CLI / ENV / Control Plane API)
```

> [!IMPORTANT]
> **Namespace Authority:** All official Cortex schema definitions belong strictly to the `https://cortex.security/schemas/...` URI domain. Schema URIs under `cortex.dev` or unverified external domains are forbidden in production deployments.

---

## 2. Configuration Processing & Materialization Lifecycle

To guarantee deterministic, fail-closed validation, configuration input payloads MUST be processed according to the following 10-stage sequential pipeline:

```
  [1] PARSE INPUT PAYLOAD (JSON/YAML)
           ↓
  [2] DEFAULT MATERIALIZATION (Apply normative schema default values)
           ↓
  [3] SCHEMA VALIDATION (Validate structure against canonical JSON Schema)
           ↓
  [4] SEMANTIC VALIDATION (Cross-field constraints, e.g. min_replicas <= max_replicas)
           ↓
  [5] SECURITY CEILING ENFORCEMENT (Clamp to host non-degradable ceiling)
           ↓
  [6] VOCABULARY NORMALIZATION (Translate legacy aliases to snake_case)
           ↓
  [7] CANONICAL ENCODING (CBE / Sorted UTF-8 key-value pairs)
           ↓
  [8] SHA-256 DIGEST COMPUTATION (Compute 64-char hex config_hash)
           ↓
  [9] IMMUTABLE SNAPSHOT CREATION (Bind config_hash to DesiredConfig)
           ↓
 [10] GENERATION BINDING (Assign monotonic config_generation = N + 1)
```

---

## 3. Canonical JSON Schema (`v1.0.0`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://cortex.security/schemas/v1/configuration.schema.json",
  "title": "CortexDesiredConfiguration",
  "description": "Normative schema for Cortex Control Plane desired execution state. Excludes derived identity metadata (config_hash, config_generation).",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "gateway",
    "replica_group",
    "sandbox",
    "resource_limits"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["1.0.0"]
    },
    "gateway": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "max_queue_depth",
        "max_worker_inflight",
        "queue_timeout_sec",
        "dispatch_deadline_sec",
        "selection_policy",
        "journal_path",
        "fsync_policy"
      ],
      "properties": {
        "max_queue_depth": {
          "type": "integer",
          "minimum": 1,
          "maximum": 10000,
          "default": 1000,
          "description": "Maximum aggregate queued invocations across all replica groups before ERR_QUEUE_FULL"
        },
        "max_worker_inflight": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100,
          "default": 10,
          "description": "Maximum concurrent inflight invocations assigned per ready worker instance"
        },
        "queue_timeout_sec": {
          "type": "number",
          "minimum": 0.1,
          "maximum": 300.0,
          "default": 30.0,
          "description": "Timeout in seconds before queued invocation raises ERR_QUEUE_TIMEOUT"
        },
        "dispatch_deadline_sec": {
          "type": "number",
          "minimum": 0.1,
          "maximum": 60.0,
          "default": 5.0,
          "description": "Maximum seconds allowed to execute atomic dispatch pipeline"
        },
        "selection_policy": {
          "type": "string",
          "enum": ["least_inflight_deterministic", "round_robin_deterministic"],
          "default": "least_inflight_deterministic",
          "description": "Algorithm used by RoutingPolicy for worker selection"
        },
        "journal_path": {
          "type": "string",
          "pattern": "^/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9._-]+$",
          "default": "/var/log/cortex/invocation_journal.jsonl",
          "description": "Absolute filesystem path to append-only JSON-lines invocation state journal"
        },
        "fsync_policy": {
          "type": "string",
          "enum": ["always", "batch", "never"],
          "default": "always",
          "description": "Fsync discipline for persistent ledger journal writes"
        }
      }
    },
    "replica_group": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "group_id",
        "min_replicas",
        "max_replicas",
        "drain_deadline_sec"
      ],
      "properties": {
        "group_id": {
          "type": "string",
          "pattern": "^[a-z0-9_-]+$",
          "description": "Unique alphanumeric ReplicaGroup identifier"
        },
        "min_replicas": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1000,
          "default": 1
        },
        "max_replicas": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1000,
          "default": 10
        },
        "drain_deadline_sec": {
          "type": "number",
          "minimum": 1.0,
          "maximum": 300.0,
          "default": 30.0,
          "description": "Seconds allowed for graceful worker drain before forced SIGKILL"
        }
      }
    },
    "sandbox": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "profile_name",
        "required_capabilities",
        "allowed_syscalls",
        "landlock_paths",
        "read_only_root",
        "allowed_write_paths"
      ],
      "properties": {
        "profile_name": {
          "type": "string",
          "enum": ["Profile_A_Linux_Strict"],
          "description": "Isolation profile name. Permissive/Development profiles MUST NOT be used in production schemas."
        },
        "required_capabilities": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[a-z0-9_-]+\\.[a-z0-9._-]+$"
          },
          "uniqueItems": true,
          "description": "Explicit capability identifiers (format: namespace.action)"
        },
        "allowed_syscalls": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9_]+$"
          },
          "uniqueItems": true,
          "description": "Whitelist of allowed Linux system call names for Seccomp filter"
        },
        "landlock_paths": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9._-]*$"
          },
          "uniqueItems": true,
          "description": "Filesystem path boundaries restricted by Landlock ABI"
        },
        "read_only_root": {
          "type": "boolean",
          "default": true,
          "description": "Enforce read-only root filesystem mounting"
        },
        "allowed_write_paths": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^/tmp/sandbox_[a-zA-Z0-9_-]+$"
          },
          "default": ["/tmp/sandbox_default"],
          "uniqueItems": true,
          "description": "Strictly restricted write path boundaries inside worker mount namespace"
        }
      }
    },
    "resource_limits": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "memory_limit_mb",
        "cpu_quota_percent"
      ],
      "properties": {
        "memory_limit_mb": {
          "type": "integer",
          "minimum": 64,
          "maximum": 32768,
          "default": 512,
          "description": "Cgroups v2 hard memory ceiling in megabytes per worker"
        },
        "cpu_quota_percent": {
          "type": "integer",
          "minimum": 10,
          "maximum": 1600,
          "default": 100,
          "description": "CPU quota allocation percentage per worker"
        }
      }
    }
  }
}
```

---

## 4. Semantic Validation Rules (Post-Schema Checks)

Schema structural validation MUST be followed by semantic cross-field validation rules:

1. **Replica Bounds Constraint:** `replica_group.min_replicas <= replica_group.max_replicas`. Violation raises `SemanticValidationError("min_replicas cannot exceed max_replicas")`.
2. **Strict Write Path Isolation:** `allowed_write_paths` MUST NOT overlap with system execution directories (`/bin`, `/sbin`, `/usr`, `/etc`, `/lib`, `/proc`, `/sys`). All write paths MUST begin with `/tmp/sandbox_`.
3. **Capability Format Validation:** All strings in `required_capabilities` MUST conform to namespace notation (`<domain>.<action>`). Wildcard capabilities (`*`) are strictly prohibited.
4. **Security Ceiling Non-Degradation:** If `sandbox.profile_name` is omitted or altered, it defaults to `Profile_A_Linux_Strict`.

---

## 5. Separation of Desired Config vs Derived Identity

To prevent clients from forging identity hashes or generation counters, input documents contain ONLY `DesiredConfig`. Derived identity is created exclusively by the Gateway TCB:

```python
@dataclass(frozen=True)
class DesiredConfig:
    schema_version: str
    gateway: GatewayConfig
    replica_group: ReplicaGroupConfig
    sandbox: SandboxConfig
    resource_limits: ResourceLimitsConfig

@dataclass(frozen=True)
class DerivedConfigurationIdentity:
    config_hash: str          # SHA-256 of CBE-encoded DesiredConfig
    config_generation: int    # Monotonic generation counter (N + 1)
    snapshot_timestamp: float # Monotonic creation time
    desired_config: DesiredConfig
```
