# Cortex API and Plugin Contract Status

> **Release Baseline**: `v0.7.0rc1` | **HEAD**: `c7ad74f117fc6e484eb2b5e13a1582002e400756`  
> **Contract Boundary**: `BasePlugin` vs `WorkerSupervisor` vs `ResourceContract`

---

## 1. Governing Principles & Boundaries

The Cortex plugin architecture is strictly governed by the foundational invariant:

$$ \boxed{\text{Authority Decides}} \quad \text{and} \quad \boxed{\text{Adapter Executes}} $$

To eliminate ambiguity in polyglot development, the repository enforces clear boundaries between three distinct concepts:

```
+---------------------------------------------------------------------------------------+
|                              CORTEX PLUGIN BOUNDARIES                                 |
+---------------------------------------------------------------------------------------+
| 1. NATIVE PLUGIN       | Python in-process class inheriting from BasePlugin.           |
|                        | Executes inside the main event loop; capability-gated.        |
+------------------------+--------------------------------------------------------------+
| 2. EXTERNAL WORKER     | Subprocess running in an isolated container/cgroup boundary.  |
|                        | Communicates via stdio/socket using CBE frames.               |
+------------------------+--------------------------------------------------------------+
| 3. RESOURCE ADAPTER    | Low-level driver implementing ResourceContract interface.    |
|                        | Executes pre-authorized external effects; NO policy logic.    |
+---------------------------------------------------------------------------------------+
```

---

## 2. Polyglot Support Matrix & Language Tiering

Language compatibility in Cortex is formally classified into supported tiers based on repository evidence:

| Language | Native Plugin (`BasePlugin`) | External Worker Subprocess | Adapter Boundary (`ResourceContract`) | Support Status |
| :--- | :--- | :--- | :--- | :--- |
| **Python 3.10+** | **Tier 1 (Supported)** | **Tier 1 (Supported)** | **Tier 1 (Supported)** | Full Production Surface |
| **Go 1.20+** | *Not Supported* | **Tier 1 (Supported)** | **Tier 1 (Supported via `cortex-go`)**| Subprocess / Adapter RPC |
| **Rust 2021** | *Not Supported* | **Tier 1 (Supported)** | **Tier 1 (Supported via `cortex-emulator`)**| Supervisor / Subprocess |
| **C / C++** | *Not Supported* | **Tier 2 (Experimental)** | **Tier 2 (Experimental via stdio)** | Subprocess Boundary Only |

> [!IMPORTANT]
> Polyglot native in-process shared objects (`.so` / `.dll`) are **NOT** supported as native Cortex plugins. All non-Python extensions must operate across process boundaries via standard IO or Unix domain sockets utilizing CBE serialization.

---

## 3. Adapter Contract & Lifecycle Verification

Every external effect adapter must implement the `ResourceContract` interface:

```
   Intent Event
        │
        ▼
   [ GatewayAuthorizationGate ] ─── Validates capabilities & issues HMAC token
        │
        ▼
   [ Execution Context ] ─── Contains idempotency_key & invocation_id
        │
        ▼
   [ Adapter Execution ] ─── ResourceContract.execute_effect(ctx, payload)
        │
        ▼
   [ Effect Outcome ] ─── Returns status (EFFECT_CONFIRMED, UNKNOWN_EFFECT, etc.)
        │
        ▼
   [ Reconciliation Engine ] ─── Classification-gated state transition
```

### Decoupling Rules Verified in Code
1. **No Policy Evaluation**: Adapters never evaluate capability rules or authorization policies.
2. **No Idempotency Derivation**: Idempotency keys are computed exclusively by `GatewayAuthorizationGate`.
3. **No Secret Storage**: Credentials are resolved gateway-side by `CredentialBroker` and are never exposed to worker code.
4. **No Retry Authority**: Adapters report execution status; retry decisions belong exclusively to `EffectReconciliationEngine`.

---

## 4. Reference Plugin Implementation

The standard reference external effect plugin baseline is located in `examples/secure_external_effect_plugin/`. It includes:
* Manifest definition (`cortex.yaml`) specifying required capabilities and consumed events.
* Dedicated audit and record plugins (`audit_plugin`, `record_plugin`).
* Test harness (`test_reference_plugin.py`) validating both authorized execution and negative security violations.
