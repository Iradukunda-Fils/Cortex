# Cortex Canonical Configuration Schema Reference

**Version:** `v1.0.0`  
**Status:** NORMATIVE SPECIFICATION  
**Scope:** Control Plane, Gateway Dispatcher, & Worker Replica Configuration  

---

## 1. Overview

This document defines the **Canonical Configuration Schema** for the Cortex Control Plane and Execution Engine. All configuration files (`manifest.yaml`, `cortex.yaml`), environment overrides, and CLI options MUST conform to the parameter names, types, and constraints specified in this reference.

---

## 2. Canonical JSON Schema (`v1.0.0`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://cortex.dev/schemas/v1/configuration.schema.json",
  "title": "CortexCanonicalConfiguration",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "gateway",
    "replica_group",
    "sandbox"
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
        "dispatch_deadline_sec"
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
        "journal_path": {
          "type": "string",
          "default": "/var/log/cortex/invocation_journal.jsonl",
          "description": "Path to append-only JSON-lines invocation state journal"
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
          "default": 1
        },
        "max_replicas": {
          "type": "integer",
          "minimum": 1,
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
        "required_capabilities"
      ],
      "properties": {
        "profile_name": {
          "type": "string",
          "enum": ["Profile_A_Linux_Strict", "Profile_B_Development_Permissive"]
        },
        "required_capabilities": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },
        "read_only_root": {
          "type": "boolean",
          "default": true
        },
        "allowed_write_paths": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "default": ["/tmp"]
        }
      }
    }
  }
}
```

---

## 3. Canonical Environment Variable Mapping

Environment variable overrides map directly to schema properties using the `CORTEX_` prefix and upper-case `snake_case`:

| Environment Variable | Canonical Configuration Path | Data Type | Default Value |
| :--- | :--- | :--- | :--- |
| `CORTEX_MAX_QUEUE_DEPTH` | `gateway.max_queue_depth` | Integer | `1000` |
| `CORTEX_MAX_WORKER_INFLIGHT` | `gateway.max_worker_inflight` | Integer | `10` |
| `CORTEX_QUEUE_TIMEOUT_SEC` | `gateway.queue_timeout_sec` | Float | `30.0` |
| `CORTEX_DISPATCH_DEADLINE_SEC`| `gateway.dispatch_deadline_sec`| Float | `5.0` |
| `CORTEX_JOURNAL_PATH` | `gateway.journal_path` | String | `/var/log/cortex/invocation_journal.jsonl` |
| `CORTEX_DRAIN_DEADLINE_SEC` | `replica_group.drain_deadline_sec`| Float | `30.0` |

---

## 4. Normalization Rules

1. **Snake Case:** All field names MUST be formatted in lowercase `snake_case`. CamelCase keys (`queueTimeoutSec`) MUST be normalized during schema parsing.
2. **Timeout Suffix:** All time durations MUST specify units explicitly via `_sec` suffix.
3. **No Unrecognized Keys:** Configuration parsers MUST reject unrecognized keys with `ManifestError` or `ValueError` (strict schema mode).
