# Cortex MCP Secure External Effect Application (`mcp_secure_effect_app`)

**Canonical 3-Plugin Reference Application for Gateway-Mediated External Side-Effects**

This reference application demonstrates how sandboxed Cortex plugins request external side-effects safely through the Cortex Control Plane using pre-authorized adapter execution, credential isolation, HMAC idempotency derivation, and Content-Addressable Storage (CAS).

---

## Architectural Principle

$$\boxed{ \text{Worker has Intent} \quad \longrightarrow \quad \text{Gateway Authorizes} \quad \longrightarrow \quad \text{Sandbox Enforces} \quad \longrightarrow \quad \text{Adapter Executes} }$$

1. **Sandboxed Plugins**: Express **intent** via unprivileged `EffectRequest` objects. Workers **never** receive credentials, derive idempotency keys, or execute external network sockets directly.
2. **Gateway Authorization Gate (Gate B)**: Evaluates capability grants, lease epoch fencing, resolves authoritative effect classification, and derives HMAC-SHA256 idempotency key.
3. **Credential Broker Vault**: Resolves provider credentials from an isolated vault after authorization succeeds. Credentials are injected directly into the adapter context and never returned to workers.
4. **Local Process MCP Adapter**: Executes pre-authorized tool calls over an isolated stdio JSON-RPC subprocess boundary.
5. **CAS Evidence Spooling**: Spools evidence payloads >4KiB into `ContentAddressableStore`, returning cryptographic hash reference pointers.

---

## Included Plugins

| Plugin Name | Manifest Capabilities | Role & Execution Flow |
| :--- | :--- | :--- |
| **`ingestion_plugin`** | `["mcp:echo"]` | Ingests external event payloads safely via Gateway-mediated MCP echo service |
| **`analytics_plugin`** | `["mcp:report"]` | Generates analytical report payloads; auto-spools evidence >4KiB to CAS |
| **`audit_plugin`** | `["mcp:audit"]` | Verifies execution lineage, policy compliance, and audit log generation |

---

## Control Plane Architecture

```
                       CORTEX CONTROL PLANE
 ┌─────────────────────────────────────────────────────────────────┐
 │                       3 Sandboxed Plugins                       │
 │  [IngestionPlugin]    [AnalyticsPlugin]     [AuditPlugin]       │
 │   (mcp:echo)           (mcp:report)          (mcp:audit)        │
 └────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │               Gateway Authorization Gate (Gate B)               │
 │   - Capability Grant Validation & Negotiation                  │
 │   - Lease Epoch & Worker Incarnation Fencing                    │
 │   - Gateway-Driven Authoritative Effect Classification         │
 │   - HMAC-SHA256 Idempotency Key Derivation                      │
 └────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │         Credential Broker Vault & Pipeline Execution            │
 │   - Inject Vault Credentials into Adapter Execution Context     │
 │   - Auto-Spool Large Evidence (>4KiB) to CAS                    │
 │   - Classification-Gated Failure Recovery                       │
 └────────────────────────────────┬────────────────────────────────┘
                                  │
                                  ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │             LocalProcessMCPAdapter (Stdio Subprocess)           │
 │   - JSON-RPC 2.0 over Stdio                                     │
 └─────────────────────────────────────────────────────────────────┘
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
│   ├── ingestion_plugin/
│   │   ├── __init__.py
│   │   ├── manifest.yml                # Ingestion capability requirements
│   │   └── tasks.py                    # Safe payload ingestion task
│   ├── analytics_plugin/
│   │   ├── __init__.py
│   │   ├── manifest.yml                # Analytics capability requirements
│   │   └── tasks.py                    # Large report generation task
│   └── audit_plugin/
│       ├── __init__.py
│       ├── manifest.yml                # Audit capability requirements
│       └── tasks.py                    # Audit log recording task
└── tests/
    ├── __init__.py
    └── test_secure_effect_app.py      # Integration test suite for all 3 plugins
```

---

## Running the Sample Application & Tests

### Run Main Demonstration Script
```bash
python -m examples.mcp_secure_effect_app.main
```

### Run Integration Test Suite
```bash
pytest examples/mcp_secure_effect_app/tests
```

---

## Verified Security Invariants Demonstrated

| Invariant | Description | Verification Method |
| :--- | :--- | :--- |
| **Credential Isolation** | Provider tokens exist only in `CredentialBroker` vault; never visible to plugins | `test_credential_isolation_vault` |
| **Capability Gate** | Requests for ungranted capabilities are denied at Gateway boundary | `test_ungranted_capability_is_rejected` |
| **Lease Fencing** | Requests with stale lease epochs are rejected before adapter execution | `test_stale_lease_epoch_is_rejected` |
| **CAS Evidence Spooling** | Payloads >4KiB auto-spool to CAS with SHA-256 reference pointers | `test_analytics_plugin_spools_evidence_to_cas` |
