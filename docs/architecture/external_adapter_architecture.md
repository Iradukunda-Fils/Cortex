# CORTEX — EXTERNAL EFFECT ADAPTER CONTRACT SPECIFICATION

**Document Identifier:** `CORTEX-SPEC-ADAPTER-2026-V1.5`  
**Classification:** Canonical Integration Architecture Specification  
**Subsystem:** External Adapters, Side-Effect Classification & Credential Isolation  
**Status:** ARCHITECTURE-LOCKED & FROZEN (v1.5.0-FROZEN)  
**Canonical Schema Namespace:** `https://schemas.cortex.internal/v1`

---

## 1. EXTERNAL ADAPTER ARCHITECTURE & SECURITY BOUNDARY

External integrations (S3, PostgreSQL, SMTP email, HTTP APIs, MCP tool servers) MUST NOT execute directly inside unprivileged worker sandboxes or decide policy. They act strictly as **effect ports** through Gateway-managed Adapter Services:

```
[ Unprivileged Worker Sandbox ]
              │
      (CBE Stream Request)
              │
              ▼
[ Gateway Control Plane TCB / PEP ]  <─── Secret Vault & Policy Engine
              │
    (Authorized Intent, Epoch & Ephemeral Context)
              │
              ▼
[ Gateway External Adapter Service ]  ───> [ External System / Resource ]
  (S3 / Postgres / SMTP / MCP)               (S3 Bucket / DB / Mail)
```

---

## 2. CANONICAL ADAPTER EXECUTION CONTEXT & KEY DERIVATION

Adapters **MUST NOT** derive idempotency keys independently. The Gateway computes the canonical `IdempotencyKey` once during authorization via:

$$K_{\text{idempotency}} = \text{HMAC-SHA256}\Big(S_{\text{domain\_secret}}, \, \text{InvocationID} \parallel \text{CanonicalPayload} \parallel \text{ResourceID} \parallel \text{OperationType} \parallel \text{ContractVersion}\Big)$$

### Ephemeral Execution Context Schema (`AdapterExecutionContext`):
```json
{
  "$schema": "https://schemas.cortex.internal/v1/adapter-execution-context.json",
  "invocation_id": "inv_01J8X9A0000000000000000001",
  "execution_attempt_id": "att_01J8X9A0000000000000000002",
  "adapter_request_id": "req_01J8X9A0000000000000000003",
  "capability": "resource.object.write",
  "resource_identifier": "res_s3_primary_bucket",
  "lease_epoch": 1043,
  "deadline_unix_ms": 1756000000000,
  "idempotency_key": "k_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "state_domain_key": "domain_media_processing"
}
```

---

## 3. SIDE-EFFECT CLASSIFICATION & RETRY SEMANTICS

| Side-Effect Category | Operational Examples | Idempotent? | Monotonic Retry Rules | Failure State Assignment |
| :--- | :--- | :---: | :--- | :--- |
| **`READ_ONLY`** | S3 GetObject, SQL SELECT, KV Get | YES | New attempt ($a_{n+1}$, $\text{Epoch}_{n+1}$) | `RETRY_SAFE` |
| **`IDEMPOTENT_WRITE`** | S3 PutObject (Content-Addressed), KV Set | YES | New attempt ($a_{n+1}$, $\text{Epoch}_{n+1}$) | `RETRY_SAFE` |
| **`IDEMPOTENT_WITH_KEY`** | Charge Payment, REST API | YES | New attempt ($a_{n+1}$, $\text{Epoch}_{n+1}$) preserving `IdempotencyKey` | `RETRY_SAFE` |
| **`NON_IDEMPOTENT_WRITE`**| Send Email, DB Log Append | NO | **Strictly blocked on failure** | **`INDETERMINATE`** |
| **`EXPLICIT_TRANSACTION`** | Verified 2PC Protocol | YES | Rollback + New attempt ($a_{n+1}$, $\text{Epoch}_{n+1}$) | `RETRY_SAFE` |
| **`UNKNOWN_EFFECT`** | External MCP Tool Call | NO | **Strictly blocked on failure** | **`INDETERMINATE`** |

### Monotonic Retry Invariant:
$$\text{Retry}(I, a_n, \text{Epoch}_n) \implies a_{n+1} \neq a_n \quad \land \quad \text{Epoch}_{n+1} > \text{Epoch}_n \quad \land \quad \text{IdempotencyKey}(a_{n+1}) = \text{IdempotencyKey}(a_n)$$

---

## 4. MEMORY-BOUNDED EVIDENCE PAYLOADS & RECONCILIATION

1. **Inline Evidence Cap:** Direct outcome evidence returning over the control channel is capped at **4 KiB** (`MAX_INLINE_EVIDENCE_BYTES = 4096`). Larger payloads MUST be written to the data plane and returned as an `EvidenceRef` wrapping an `ObjectRef`.
2. **Layered Reconciliation for `INDETERMINATE`:** When an operation yields `UNKNOWN_EFFECT` for non-idempotent operations:
   - Automated verification probes (Metadata HEAD check, provider status query) run first.
   - If inconclusive, a targeted scope quarantine (`QuarantineScope` $\subseteq$ `StateDomain`) locks only the affected resource/invocation, allowing unrelated operations in the domain to proceed safely.

---
