# Cortex Configuration Reference

**Normative Document Version**: v1.0.0-FINAL  
**Reference Schema**: `cortex/schemas/v1/configuration.schema.json`  
**Configuration Resolver**: `cortex/tools/kernel/config_resolver.py`

---

## 1. Desired Configuration Overview

Cortex uses a canonical configuration structure to define gateway parameters, replica group sizes, sandbox profiles, and resource limits. The configuration is validated against a strict JSON Schema (Draft 2020-12) and normalized to guarantee deterministic, reproducible state.

---

## 2. Canonical Configuration Templates

### 📋 YAML Template (`cortex.yaml`)
```yaml
schema_version: "1.0.0"

gateway:
  max_queue_depth: 1000
  max_worker_inflight: 10
  queue_timeout_sec: 30.0
  dispatch_deadline_sec: 5.0
  selection_policy: "least_inflight_deterministic"
  journal_path: "/var/log/cortex/invocation_journal.jsonl"
  fsync_policy: "always"

replica_group:
  group_id: "default_group"
  min_replicas: 1
  max_replicas: 10
  drain_deadline_sec: 30.0

sandbox:
  profile_name: "Profile_A_Linux_Strict"
  required_capabilities:
    - "host.read"
    - "host.write"
  allowed_syscalls:
    - "clock_gettime"
    - "exit"
    - "futex"
    - "read"
    - "write"
  landlock_paths:
    - "/tmp"
    - "/var/log"
  read_only_root: true
  allowed_write_paths:
    - "/tmp/sandbox_default"

resource_limits:
  memory_limit_mb: 512
  cpu_quota_percent: 100
```

### 📋 JSON Template (`cortex.json`)
```json
{
  "schema_version": "1.0.0",
  "gateway": {
    "max_queue_depth": 1000,
    "max_worker_inflight": 10,
    "queue_timeout_sec": 30.0,
    "dispatch_deadline_sec": 5.0,
    "selection_policy": "least_inflight_deterministic",
    "journal_path": "/var/log/cortex/invocation_journal.jsonl",
    "fsync_policy": "always"
  },
  "replica_group": {
    "group_id": "default_group",
    "min_replicas": 1,
    "max_replicas": 10,
    "drain_deadline_sec": 30.0
  },
  "sandbox": {
    "profile_name": "Profile_A_Linux_Strict",
    "required_capabilities": [
      "host.read",
      "host.write"
    ],
    "allowed_syscalls": [
      "clock_gettime",
      "exit",
      "futex",
      "read",
      "write"
    ],
    "landlock_paths": [
      "/tmp",
      "/var/log"
    ],
    "read_only_root": true,
    "allowed_write_paths": [
      "/tmp/sandbox_default"
    ]
  },
  "resource_limits": {
    "memory_limit_mb": 512,
    "cpu_quota_percent": 100
  }
}
```

---

## 3. Configuration Fields Specification

### 3.1 Gateway Parameters (`gateway`)
*   **`max_queue_depth`** (Integer, Default: `1000`): Maximum aggregate queued invocations across all replica groups. Excess causes queue overflow errors.
*   **`max_worker_inflight`** (Integer, Default: `10`): Maximum concurrent task executions allowed on a single worker.
*   **`queue_timeout_sec`** (Number, Default: `30.0`): Max seconds an invocation can remain in the queue before timing out.
*   **`dispatch_deadline_sec`** (Number, Default: `5.0`): Maximum time allowed for executing the placement and lease checks.
*   **`selection_policy`** (String, Default: `"least_inflight_deterministic"`): Algorithm used for picking workers. Supported: `"least_inflight_deterministic"`, `"round_robin_deterministic"`.
*   **`journal_path`** (String, Default: `"/var/log/cortex/invocation_journal.jsonl"`): Absolute path to the persistent WAL ledger journal.
*   **`fsync_policy`** (String, Default: `"always"`): Disk sync policy for durability. Supported: `"always"`, `"batch"`, `"never"`.

### 3.2 Replica Group Configuration (`replica_group`)
*   **`group_id`** (String): Unique identifier pattern (`^[a-z0-9_-]+$`).
*   **`min_replicas`** (Integer, Default: `1`): Minimum active workers maintained.
*   **`max_replicas`** (Integer, Default: `10`): Maximum worker scaling ceiling.
*   **`drain_deadline_sec`** (Number, Default: `30.0`): Grace period in seconds given to draining workers before forced teardown.

### 3.3 Sandbox Profile Configuration (`sandbox`)
*   **`profile_name`** (String): Mandatory profile name. In production, must be `"Profile_A_Linux_Strict"`.
*   **`required_capabilities`** (Array of Strings): Explicit capability tokens using dot notation (e.g. `"host.read"`).
*   **`allowed_syscalls`** (Array of Strings): Whitelisted Linux syscall names permitted by Seccomp filter.
*   **`landlock_paths`** (Array of Strings): Filesystem path boundaries restricted by Landlock.
*   **`read_only_root`** (Boolean, Default: `true`): Enforce read-only mounting of the root filesystem.
*   **`allowed_write_paths`** (Array of Strings): Permitted write boundaries inside the worker namespace (e.g. `"/tmp/sandbox_default"`).

### 3.4 Resource Limits (`resource_limits`)
*   **`memory_limit_mb`** (Integer, Default: `512`): Hard memory ceiling in megabytes per worker (enforced via cgroups v2 `memory.max`).
*   **`cpu_quota_percent`** (Integer, Default: `100`): CPU quota percentage per worker (enforced via cgroups v2 `cpu.max` CFS period/quota).
