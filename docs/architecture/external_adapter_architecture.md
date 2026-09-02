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

## 5. CODEBASE DIRECTORY STRUCTURE & MODULE RESPONSIBILITIES

Contributors modifying or extending the External Effects Subsystem must adhere to the following directory layout:

```
cortex/tools/kernel/
├── adapter_contract.py        # Core contracts: AdapterExecutionContext, EffectPayload, EvidencePayload, AdapterOutcome
├── effect_gateway.py          # GatewayAuthorizationGate (PEP), EffectRequest, zero-credential worker schema
├── effect_runtime.py          # CredentialBroker (host vault resolution), isolated stdio process runner
├── effect_wal.py              # Crash-safe binary CWAL engine (CRC32, atomic fsync, LSN allocation)
├── gateway_reconciliation.py  # GatewayReconciliationEngine (Dual-epoch fencing, SHA-256 CrossGatewayClaimLock, QUARANTINED recovery, COMMITTED replay)
└── adapters/
    └── mcp_adapter.py         # Stdio MCP Client adapter wrapping local tool servers under ResourceContract

tests/
├── kernel/
│   ├── test_mcp_adapter_vertical_slice.py # Sub-Gate B.1 Local Composition tests
│   └── test_b3_restart_fencing.py          # Sub-Gate B.3.0 Restart Fencing adversarial tests
├── benchmarks/
│   └── test_b3_throughput_benchmarks.py   # Sub-Gate B.3.1 Empirical IOPS & Latency Benchmark Suite
└── fixtures/
    └── local_mcp_server.py                # Standalone stdio JSON-RPC MCP server test fixture
```

---

## 6. FENCED EXECUTION, WAL DURABILITY & CRASH RECOVERY (SUB-GATE B.3.0)

### 6.1 Dual-Epoch Fencing ($P12_{\text{epoch}}$)
Every external effect execution request must pass strict fencing against active Gateway state:
$$\text{LeaseEpoch}_{\text{request}} = \text{LeaseEpoch}_{\text{active}} \quad \land \quad \text{AuthorityEpoch}_{\text{request}} = \text{AuthorityEpoch}_{\text{active}}$$
Any epoch mismatch raises `StaleEpochError` immediately, preventing zombie or post-failover execution.

### 6.2 Cross-Process Execution Mutex ($P12_{\text{cross-process}}$)
Processes sharing the same host prevent duplicate in-flight actuation using `CrossGatewayClaimLock`.
- Lock Path Sanitization: `Path("/tmp/cortex_effect_claims/" + SHA256(effect_key) + ".lock")`
- Uses non-blocking OS file locks (`fcntl.flock(LOCK_EX | LOCK_NB)`).
- Enforces $\forall k, \, |\text{ActiveExternalExecutions}(k)| \le 1$ across all local processes.

### 6.3 Write-Ahead Logging & fsync Barriers ($P6_{\text{durable}}$)
State transitions follow binary `CWAL` framing:
`[Magic b"CWAL"][Length 4b][CRC32 4b][SeqNo 8b][Payload JSON bytes...]`

Dispatches follow the mandatory disk sync sequence:
$$\text{Persist}(\text{ADMITTED}) \xrightarrow{\text{fsync}} \text{Persist}(\text{ACTUATING}) \xrightarrow{\text{fsync}} \text{Dispatch} \xrightarrow{\text{Persist}(\text{COMMITTED})} \xrightarrow{\text{fsync}}$$

### 6.4 Recovery & Quarantine Semantics ($P9_{\text{recovery}}$)
During Gateway restart:
- Unresolved `EFFECT_ACTUATING` logs are converted to `EFFECT_QUARANTINED`.
- Replaying a quarantined key returns `ExecutionStatus.UNKNOWN_EFFECT` with an explicit quarantine error message.
- **Zero Blind Retries**: Automatic execution is strictly blocked for quarantined keys.

---

## 7. EMPIRICAL BENCHMARKS & GOVERNANCE (SUB-GATE B.3.1)

Empirical performance evaluation (`tests/benchmarks/test_b3_throughput_benchmarks.py`):
- **Single-Threaded Throughput**: ~1,650 ops/sec ($P_{50} = 0.191$ ms, $P_{95} = 3.541$ ms, $P_{99} = 7.751$ ms)
- **Concurrency Scaling ($C \in \{1 \dots 16\}$)**: Up to 2,244 ops/sec under 16 concurrent worker threads.
- **Governance Decision**: `NO CHANGE REQUIRED` — Empirical data proves local `CWAL` easily fulfills operational constraints without distributed databases or sharding.

---

## 8. SUB-GATE ROADMAP STATUS & CONTRIBUTOR GUIDELINES

$$\boxed{ \text{Gate B.1 (CLOSED)} \rightarrow \text{Gate B.3 (CLOSED)} \rightarrow \text{Gate B.2 (CLOSED)} \rightarrow \text{Gate B.4 (NEXT ACTIVE)} }$$

1. **Gate B.1 (CLOSED)**: Local MCP Composition & Authorization.
2. **Gate B.3 (CLOSED)**: Local Restart & Cross-Process Fencing (`B.3 = CLOSED — LOCAL RESTART / CROSS-PROCESS FENCING`).
3. **Gate B.2 (CLOSED)**: Physical Network Isolation via Linux `ip netns` (`B.2 = CLOSED — PHYSICAL DEFAULT-DENY NETWORK ISOLATION`).
4. **Gate B.4 (NEXT ACTIVE)**: Landlock Kernel Enforcement in Rust `sandbox.rs`.
5. **Gate B.3.4 (DEFERRED)**: Cross-Node Distributed Ownership.

### Contributor Checklist for PRs:
- [ ] Run Pyright type checker: `pyright cortex/tools/kernel/` (Must maintain 0 errors).
- [ ] Run Sub-Gate B.2 test suite: `python3 -m unittest tests/kernel/test_b2_network_isolation.py` (12/12 pass).
- [ ] Run Sub-Gate B.3 test suite: `python3 -m unittest tests/kernel/test_b3_restart_fencing.py`
- [ ] Run Sub-Gate B.1 test suite: `python3 -m unittest tests/kernel/test_mcp_adapter_vertical_slice.py`
- [ ] Ensure all lockfile path derivations use `hashlib.sha256(effect_key.encode("utf-8")).hexdigest()`.
- [ ] Ensure `EffectWALEngine.append_record` performs LSN allocation inside `fcntl.flock`.


