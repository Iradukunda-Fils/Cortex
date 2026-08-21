# Cortex Configuration Guide

This guide provides concrete YAML and JSON examples for configuring the Cortex Gateway and Plugin Deployments. It explains all configuration keys, structural validations, and security limits to ensure developers and operators can configure Cortex securely and deterministically.

---

## 1. Cortex Gateway Configuration (`cortex.yaml` / `cortex.json`)

The Gateway configuration defines the system-wide execution parameters, sandbox profile definitions, and local database settings.

### 📋 YAML Example (`cortex.yaml`)
```yaml
schema_version: "0.4.0"
gateway_id: "gateway-primary-01"
state_directory: "./.runtime/gateway_state"

database:
  db_path: "./.runtime/gateway_state/ledger[.]db"
  wal_mode: true
  sync_on_commit: true

sandbox_profiles:
  - name: "strict-zero-trust"
    clone_newpid: true
    clone_newnet: true
    clone_newns: true
    seccomp_bpf_enabled: true
    allowed_fds: [0, 1, 2, 3]

  - name: "development-audit"
    clone_newpid: true
    clone_newnet: false # Allow localhost communication for testing
    clone_newns: true
    seccomp_bpf_enabled: true
    allowed_fds: [0, 1, 2, 3]
```

### 📋 JSON Example (`cortex.json`)
```json
{
  "schema_version": "0.4.0",
  "gateway_id": "gateway-primary-01",
  "state_directory": "./.runtime/gateway_state",
  "database": {
    "db_path": "./.runtime/gateway_state/ledger[.]db",
    "wal_mode": true,
    "sync_on_commit": true
  },
  "sandbox_profiles": [
    {
      "name": "strict-zero-trust",
      "clone_newpid": true,
      "clone_newnet": true,
      "clone_newns": true,
      "seccomp_bpf_enabled": true,
      "allowed_fds": [0, 1, 2, 3]
    },
    {
      "name": "development-audit",
      "clone_newpid": true,
      "clone_newnet": false,
      "clone_newns": true,
      "seccomp_bpf_enabled": true,
      "allowed_fds": [0, 1, 2, 3]
    }
  ]
}
```

---

## 2. Plugin Deployment Configuration (`deployment.yaml` / `deployment.json`)

A Plugin Deployment configuration defines replica counts, capabilities, resource allocation, and lifecycle limits for a specific plugin group.

### 📋 YAML Example (`deployment.yaml`)
```yaml
schema_version: "0.4.0"
plugin_id: "repository-auditor"
entrypoint: "examples/repo_auditor/main.py"

scaling:
  min_replicas: 2
  max_replicas: 5
  max_queue_depth: 100

security:
  sandbox_profile: "strict-zero-trust"
  capability_ceiling:
    - "fs:read"
    - "exec:git"
    - "exec:pytest"
    - "workflow.plan.create"
    - "workflow.command.issue"

resources:
  cpu_limit: "1.5"
  memory_limit_mb: 512
  storage_limit_mb: 1024

routing:
  load_policy: "least-inflight"
  backpressure_strategy: "retry-backoff"
  advisory_balancing: true

lifecycle:
  drain_deadline_sec: 30
  heartbeat_interval_sec: 5
  unhealthy_threshold: 3
```

### 📋 JSON Example (`deployment.json`)
```json
{
  "schema_version": "0.4.0",
  "plugin_id": "repository-auditor",
  "entrypoint": "examples/repo_auditor/main.py",
  "scaling": {
    "min_replicas": 2,
    "max_replicas": 5,
    "max_queue_depth": 100
  },
  "security": {
    "sandbox_profile": "strict-zero-trust",
    "capability_ceiling": [
      "fs:read",
      "exec:git",
      "exec:pytest",
      "workflow.plan.create",
      "workflow.command.issue"
    ]
  },
  "resources": {
    "cpu_limit": "1.5",
    "memory_limit_mb": 512,
    "storage_limit_mb": 1024
  },
  "routing": {
    "load_policy": "least-inflight",
    "backpressure_strategy": "retry-backoff",
    "advisory_balancing": true
  },
  "lifecycle": {
    "drain_deadline_sec": 30,
    "heartbeat_interval_sec": 5,
    "unhealthy_threshold": 3
  }
}
```

---

## 3. Field Explanations

### 3.1 Metadata & Schema Settings
* **`schema_version`** (String): Strict SemVer constraint. Must match `0.4.0`.
* **`plugin_id`** (String): Unique identifier matching the registered plugin manifest.
* **`entrypoint`** (String): Path to the executable binary or script executed in the sandboxed worker.

### 3.2 Scaling Class
* **`min_replicas`** (Integer): The minimum number of healthy, active worker processes.
* **`max_replicas`** (Integer): The ceiling limit of active worker processes allowed under load.
* **`max_queue_depth`** (Integer): Maximum depth of the per-group FIFO buffer before incoming requests trigger backpressure.

### 3.3 Security Class
* **`sandbox_profile`** (String): Target profile name defined in the Gateway configuration.
* **`capability_ceiling`** (Array of Strings): The maximum allowed list of capabilities. If a plugin's manifest requests a capability outside this list, registration will fail immediately (`CapabilityCeilingViolation`).

### 3.4 Resources Class
* **`cpu_limit`** (String): Max fraction of physical cores (e.g., `"1.5"`).
* **`memory_limit_mb`** (Integer): RAM ceiling in Megabytes. Exceeding triggers standard Out-Of-Memory (OOM) termination.
* **`storage_limit_mb`** (Integer): Disk quota allocated to ephemeral directories.

### 3.5 Advisory Routing Class
* **`load_policy`** (String): Target routing algorithm (e.g., `"least-inflight"`).
* **`advisory_balancing`** (Boolean): When `true`, enables soft metric scores for Phase 5 balancing. Does not bypass hard safety limits.

### 3.6 Lifecycle Class
* **`drain_deadline_sec`** (Integer): Maximum time allowed for active workloads to finish before a worker is reaped.
* **`heartbeat_interval_sec`** (Integer): Rate at which health checks are reported back to the Gateway.
