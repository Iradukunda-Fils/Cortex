# Cortex Reference Sample: Secure External Effect Plugin

**REFERENCE EXAMPLE — IMPLEMENTED FEATURES ONLY**

> **"How do I build real plugins that use Cortex's current capabilities safely in an event-driven DAG?"**

This reference application demonstrates a 2-plugin event-driven DAG running through Cortex's
Gateway authorization boundary. It runs completely offline using a local deterministic API server fixture.

---

## 2-Plugin Event DAG Architecture

```
                                  CORTEX CONTROL PLANE
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │                            IntentEvent (Workflow Trigger)                              │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │  Plugin 1: RecordServicePlugin (plugins/record_plugin/tasks.py)                       │
  │  - Requires capability: api:records                                                    │
  │  - Submits EffectRequest(lookup) → Gateway → LocalProcessMCPAdapter → Evidence          │
  │  - Publishes: CommandIssuedEvent                                                       │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │  Plugin 2: AuditPlugin (plugins/audit_plugin/tasks.py)                                 │
  │  - Requires capability: api:audit                                                      │
  │  - Submits EffectRequest(log) → Gateway → LocalProcessMCPAdapter → Evidence            │
  │  - Publishes: VerificationResultEvent                                                  │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

**Key Invariants Demonstrated:**

$$\boxed{ \text{Plugin Intent} \neq \text{Authority} \neq \text{Physical Enforcement} \neq \text{External Execution} }$$

---

## Security Boundary Pipeline

```
        ┌──────────────────────────┐
        │     Untrusted Plugin     │
        │  (Record/Audit Plugin)   │
        │                          │
        │  Intent + EffectRequest  │
        └────────────┬─────────────┘
                     │  Plugin supplies ONLY:
                     │    - invocation_id
                     │    - capability + operation (intent)
                     │    - arguments (payload)
                     │    - lease_epoch + worker_generation
                     │
                     │  Plugin NEVER supplies:
                     │    - idempotency key
                     │    - effect classification
                     │    - credentials
                     ▼
        ┌──────────────────────────┐
        │ Gateway Authorization    │
        │       Gate (Gate B)      │
        │                          │
        │ 1. Reservation Fencing   │
        │ 2. Capability Grant      │
        │ 3. Effect Classification │
        │ 4. HMAC-SHA256 Key       │
        │ 5. Adapter Context       │
        └────────────┬─────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │   Credential Broker      │
        │   (Vault-Side Only)      │
        │                          │
        │ Injects credentials      │
        │ AFTER authorization —    │
        │ NEVER sent to worker     │
        └────────────┬─────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │  LocalProcessMCPAdapter  │
        │  (JSON-RPC 2.0 / stdio)  │
        └────────────┬─────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │  Local Deterministic     │
        │   API Server (fixture)   │
        └────────────┬─────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │  Reconciliation Engine   │
        │  + CAS Evidence Store    │
        │  + Replay Protection     │
        └────────────┬─────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │    EffectOutcome         │
        │  (sanitized — no creds)  │
        └──────────────────────────┘
```

---

## Demonstrated Capabilities & Security Scenarios

| # | Scenario | Expected Result | API |
|:--|:---------|:----------------|:----|
| 1 | Authorized record lookup | `EFFECT_CONFIRMED` + evidence | `EffectRequest` → `EffectExecutionPipeline.execute()` |
| 2 | Authorized record store | `EFFECT_CONFIRMED` | Same pipeline |
| 3 | Ungranted capability | `CapabilityDeniedError` | Gateway rejects `api:admin` |
| 4 | Stale lease epoch | `EffectFencingError` | Gateway rejects epoch=3 (valid=10) |
| 5 | Duplicate/replayed effect | Cached `EFFECT_CONFIRMED` (no re-execution) | `EffectResultStore` replay cache |
| 6 | Failed external service | `EFFECT_NOT_APPLIED` + error_message | Adapter returns JSON-RPC error |
| 7 | Credential isolation | Vault secret absent from `EffectOutcome` | `CredentialBroker` scoped |
| 8 | CAS evidence integrity | SHA-256 content-addressed storage | `ContentAddressableStore` |
| 9 | CAS cross-invocation denied | `CASAccessDeniedError` | Owner-scoped CAS access |
| 10 | Malformed response | `EFFECT_NOT_APPLIED` or `UNKNOWN_EFFECT` | Adapter JSON parse defense |
| 11 | AuditPlugin effect | `EFFECT_CONFIRMED` via `api:audit` | Gateway capability check |
| 12 | 2-Plugin DAG chain | `COMPLETED` workflow | `CortexClient.run_workflow()` pub/sub fan-out |

---

## Directory Structure

```
examples/secure_external_effect_plugin/
├── cortex.yaml                    # Project manifest
├── README.md                      # This documentation
├── __init__.py
├── main.py                        # Runnable demo entry point
├── fixtures/
│   ├── __init__.py
│   └── local_api_server.py        # Deterministic JSON-RPC stdio server
├── plugins/
│   ├── __init__.py
│   ├── record_plugin/
│   │   ├── __init__.py
│   │   └── tasks.py               # RecordServicePlugin
│   └── audit_plugin/
│       ├── __init__.py
│       └── tasks.py               # AuditPlugin
└── tests/
    ├── __init__.py
    └── test_reference_plugin.py   # 14-test verification suite
```

---

## Running

### Run the Main Demonstration
```bash
python -m examples.secure_external_effect_plugin.main
```

### Run Test Suite
```bash
pytest examples/secure_external_effect_plugin/tests/ -v
```
