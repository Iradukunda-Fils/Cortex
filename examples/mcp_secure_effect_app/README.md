# Cortex MCP Secure External Effect Application (`mcp_secure_effect_app`)

**Canonical 5-Plugin Reference Application for Emergent Pub/Sub Event Fan-Out & Gateway-Mediated Side-Effects**

This reference application demonstrates how sandboxed Cortex plugins request external side-effects safely through the Cortex Control Plane while demonstrating **1-to-Many Pub/Sub Event Fan-Out**: a single event published by one plugin is consumed concurrently by multiple independent plugins to trigger adaptive self-healing workflows without centralized coupling.

---

## 1-to-Many Pub/Sub Event Fan-Out Architecture

$$\boxed{ \text{DriverTelemetryEvent} \quad \Longrightarrow \quad \begin{cases} \text{MitigationPlugin (mcp:mitigate)} & \rightarrow \text{Rebalance Resources} \\ \text{NotificationPlugin (mcp:notify)} & \rightarrow \text{Send Ops Alert} \end{cases} }$$

1. **`IngestionPlugin` (`mcp:echo`)**: Ingests telemetry via Gateway MCP stdio echo service and emits `CommandIssuedEvent`.
2. **`AnalyticsPlugin` (`mcp:report`)**: Processes analytics payload via Gateway MCP generate_report service (>4KiB auto-spooled to CAS), detects telemetry anomaly, and emits `DriverTelemetryEvent` (`anomaly_detected: True`).
3. **`MitigationPlugin` (`mcp:mitigate`) & `NotificationPlugin` (`mcp:notify`)**: Both plugins consume `DriverTelemetryEvent` **concurrently**:
   - `MitigationPlugin` executes Gateway MCP resource rebalance and emits `PlanGeneratedEvent`.
   - `NotificationPlugin` dispatches emergency alert notification and emits `CommandIssuedEvent`.
4. **`AuditPlugin` (`mcp:audit`)**: Audits complete emergent lineage and emits `VerificationResultEvent` (`rule_id: "EMERGENT_MITIGATION_VERIFIED"`).

---

## Included Plugins

| Plugin Name | Manifest Capabilities | Consumed Event | Produced Event | Role & Execution Flow |
| :--- | :--- | :--- | :--- | :--- |
| **`ingestion_plugin`** | `["mcp:echo"]` | `IntentEvent` | `CommandIssuedEvent` | Ingests external event payloads safely via Gateway-mediated MCP echo service |
| **`analytics_plugin`** | `["mcp:report"]` | `CommandIssuedEvent` | `DriverTelemetryEvent` | Generates analytical report payloads; auto-spools evidence >4KiB to CAS; flags anomaly |
| **`mitigation_plugin`** | `["mcp:mitigate"]` | `DriverTelemetryEvent` | `PlanGeneratedEvent` | **Fan-Out Consumer 1**: Reacts autonomously to telemetry anomaly and executes Gateway resource rebalance |
| **`notification_plugin`** | `["mcp:notify"]` | `DriverTelemetryEvent` | `CommandIssuedEvent` | **Fan-Out Consumer 2**: Dispatches emergency operational alert concurrently upon telemetry anomaly |
| **`audit_plugin`** | `["mcp:audit"]` | `PlanGeneratedEvent` | `VerificationResultEvent` | Verifies execution lineage, policy compliance, and audit log generation |

---

## Emergent Control Plane Architecture

```
                                  CORTEX CONTROL PLANE
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                             5 Sandboxed Autonomous Plugins                             │
 │  [IngestionPlugin]    [AnalyticsPlugin]     [MitigationPlugin]   [NotificationPlugin]  │
 │   (mcp:echo)           (mcp:report)          (mcp:mitigate)       (mcp:notify)       │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                          Gateway Authorization Gate (Gate B)                           │
 │   - Capability Grant Validation & Sandboxing                                          │
 │   - Lease Epoch & Worker Incarnation Fencing                                           │
 │   - Gateway-Driven Authoritative Effect Classification                                │
 │   - HMAC-SHA256 Idempotency Key Derivation                                             │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                    Credential Broker Vault & Pipeline Execution                        │
 │   - Inject Vault Credentials into Adapter Execution Context                            │
 │   - Auto-Spool Large Evidence (>4KiB) to CAS                                           │
 │   - Classification-Gated Failure Recovery                                              │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                        LocalProcessMCPAdapter (Stdio Subprocess)                       │
 │   - JSON-RPC 2.0 over Stdio                                                            │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
examples/mcp_secure_effect_app/
├── cortex.yaml                         # Project manifest configuration
├── README.md                           # Architectural reference guide
├── __init__.py                         # Package marker
├── main.py                             # Runnable reference entry point
├── fixtures/
│   ├── __init__.py
│   └── local_mcp_service.py            # Stdio JSON-RPC MCP service fixture
├── plugins/
│   ├── __init__.py
│   ├── ingestion_plugin/ (manifest.yml & tasks.py)
│   ├── analytics_plugin/ (manifest.yml & tasks.py)
│   ├── mitigation_plugin/ (manifest.yml & tasks.py)
│   ├── notification_plugin/ (manifest.yml & tasks.py)
│   └── audit_plugin/ (manifest.yml & tasks.py)
└── tests/
    ├── __init__.py
    └── test_secure_effect_app.py      # Comprehensive integration test suite
```

---

## Running the Sample Application & Tests

### Run Main Demonstration Script
```bash
python -m examples.mcp_secure_effect_app.main
```

### Run Integration Test Suite
```bash
pytest examples/mcp_secure_effect_app.tests
```
