# CORTEX SYSTEM ARCHITECTURE SPECIFICATION (v1.5.0-FROZEN)

**Status:** 🟢 **FINAL FROZEN NORMATIVE ARCHITECTURE SPECIFICATION**  
**Canonical Schema Namespace:** `https://schemas.cortex.internal/v1`  
**Scope:** Gateway Key Derivation, Opaque Locator Handles, Bounded Data-Plane Streams, Failure & Reconciliation Engine  
**Lifecycle Stage:** Transition to Pre-Phase 5 Core Implementation & Backlog Synchronization  

---

## 1. INVARIANT EQUATIONS & OPERATIONAL RULES

$$\text{Identity} \neq \text{Authorization} \quad \land \quad \text{ObjectRef} \neq \text{Authorization} \quad \land \quad \text{Adapter} \neq \text{Authority}$$

$$\text{PhysicalLocatorHandle} \neq \text{PhysicalStorageTopology}$$

$$\text{Retry}(I, a_n, \text{Epoch}_n) \implies a_{n+1} \neq a_n \quad \land \quad \text{Epoch}_{n+1} > \text{Epoch}_n \quad \land \quad \text{IdempotencyKey}(a_{n+1}) = \text{IdempotencyKey}(a_n)$$

$$\text{UnknownEffect} \land \text{NonIdempotent} \implies \text{State} = \text{INDETERMINATE} \implies \text{QuarantineScope} \subseteq \text{StateDomain}$$

$$\text{Memory}_{\text{verification}} = O(\text{chunk\_size}) \quad \text{where } \text{chunk\_size} \le 64\,\text{KiB (Enforced via BoundedChunkReader)}$$

$$\text{ControlPlaneTraffic} \approx O(\text{Metadata}) \quad \land \quad \text{ControlPayload} \le 64\,\text{KiB}$$

---

## 2. AUTHORITATIVE GATEWAY IDEMPOTENCY DERIVATION & EXECUTION CONTEXT

Adapters **MUST NOT** derive or calculate idempotency keys independently. The Gateway / Control Plane derives the canonical `IdempotencyKey` once during authorization and injects it into the `AdapterExecutionContext`.

```
                    CORTEX CONTROL PLANE / GATEWAY (PEP)
  ┌──────────────────────────────────────────────────────────────────────┐
  │ 1. Compute Key Domain HMAC-SHA256:                                  │
  │    Key = CortexSystemMasterSecret (Or StateDomainSecret)             │
  │    Message = InvocationID || CanonicalPayload || ResourceID || Op   │
  │ 2. Inject derived IdempotencyKey into AdapterExecutionContext        │
  └──────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
                           ADAPTER EXECUTION BOUNDARY
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Consumes AdapterExecutionContext without modifying IdempotencyKey   │
  └──────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
                           ADAPTER PLANE (ResourceContract)
```

### Deterministic Canonical Key Derivation Standard

$$K_{\text{idempotency}} = \text{HMAC-SHA256}\Big(S_{\text{domain\_secret}}, \, \text{InvocationID} \parallel \text{CanonicalPayload} \parallel \text{ResourceID} \parallel \text{OperationType} \parallel \text{ContractVersion}\Big)$$

### Ephemeral Execution Context Schema

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

### Bounded Request Payload & Outcome Contracts

To maintain control-plane buffer limits, execution requests are explicitly split into inline control metadata ($\le 64\,\text{KiB}$) or references to large streaming payloads (`ObjectRef`). Evidence returned over the control plane is similarly capped at $4\,\text{KiB}$.

```rust
pub const MAX_INLINE_PAYLOAD_BYTES: usize = 65_536; // 64 KiB Limit
pub const MAX_INLINE_EVIDENCE_BYTES: usize = 4_096;  // 4 KiB Limit

#[derive(Debug, Clone)]
pub enum EffectPayload {
    Inline(Vec<u8>),      // Fixed-size upper bound (<= 64 KiB)
    Reference(ObjectRef), // Streaming payload deferred to Data Plane
}

#[derive(Debug, Clone)]
pub enum EvidencePayload {
    Inline(Vec<u8>),      // Fixed-size upper bound (<= 4 KiB)
    Reference(ObjectRef), // Large output deferred to Data Plane
}

#[derive(Debug, Clone)]
pub struct CorrelationLineage {
    pub invocation_id: String,
    pub execution_attempt_id: String,
    pub adapter_request_id: String,
}

#[derive(Debug, Clone)]
pub enum AdapterOutcome {
    Success {
        lineage: CorrelationLineage,
        evidence: Option<EvidencePayload>,
    },
    RetryableFailure {
        lineage: CorrelationLineage,
        reason: String,
        backoff_hint_ms: Option<u64>,
    },
    DefinitiveFailure {
        lineage: CorrelationLineage,
        error_code: String,
        reason: String,
    },
    UnknownEffect {
        lineage: CorrelationLineage,
        reason: String,
        attempted_at_ms: u64,
    },
}

pub trait ResourceContract: Send + Sync {
    fn resource_type(&self) -> &'static str;
    fn execute_effect(
        &self, 
        ctx: &AdapterExecutionContext, 
        payload: EffectPayload
    ) -> AdapterOutcome;
}
```

---

## 3. OPAQUE LOCATOR HANDLES & ENFORCED BOUNDED VERIFICATION

`ObjectRef` represents physical storage decoupling. Access resolution operates independently from locator acquisition.

### Opaque PhysicalLocatorHandle Specification

Physical URI paths, storage bucket names, and internal endpoints MUST NEVER be exposed outside the resolver or adapter boundaries. The worker receives an opaque capability token handle.

```json
{
  "$schema": "https://schemas.cortex.internal/v1/physical-locator-handle.json",
  "locator_handle_id": "loc_01H8X9B0000000000000000001",
  "storage_engine_id": "engine_s3_primary",
  "bound_invocation_id": "inv_01J8X9A0000000000000000001",
  "bound_execution_attempt_id": "att_01J8X9A0000000000000000002",
  "access_mode": "READ_ONLY",
  "valid_from_unix_ms": 1756000000000,
  "valid_until_unix_ms": 1756000900000
}
```

### Enforced Bounded Chunk Verification Mechanics

The memory bound ($\le 64\,\text{KiB}$) is enforced using a type-level wrapper `BoundedChunkReader` that halts execution if buffer constraints are breached.

```rust
pub const MAX_VERIFICATION_CHUNK_BYTES: usize = 65_536; // 64 KiB Limit

pub trait ByteStreamReader {
    fn read_chunk(&mut self, buf: &mut [u8]) -> Result<usize, std::io::Error>;
}

pub struct BoundedChunkReader<'a> {
    inner: &'a mut dyn ByteStreamReader,
    max_chunk_size: usize,
}

impl<'a> BoundedChunkReader<'a> {
    pub fn new(inner: &'a mut dyn ByteStreamReader) -> Self {
        Self {
            inner,
            max_chunk_size: MAX_VERIFICATION_CHUNK_BYTES,
        }
    }

    pub fn read_bounded(&mut self, buf: &mut [u8]) -> Result<usize, std::io::Error> {
        if buf.len() > self.max_chunk_size {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                "Buffer exceeds maximum allowed verification chunk size (64 KiB)",
            ));
        }
        self.inner.read_chunk(buf)
    }
}

pub trait DataPlaneResolver: Send + Sync {
    fn resolve_locator_handle(
        &self, 
        auth_ctx: &AdapterExecutionContext, 
        obj_ref: &ObjectRef
    ) -> Result<PhysicalLocatorHandle, AccessDeniedError>;

    fn verify_integrity_stream(
        &self,
        obj_ref: &ObjectRef,
        reader: &mut BoundedChunkReader,
    ) -> Result<bool, IntegrityVerificationError>;
}
```

---

## 4. EXECUTION CLASS SEMANTICS & FAILURE RECOVERY PIPELINE

### Execution Class Definitions

- **`SYNC`**: Caller halts local context waiting for direct execution result. Bounds are enforced via `deadline_unix_ms`.
- **`ASYNC`**: Task outlives immediate request lifecycle; state tracked via transport-neutral execution lifecycle events.
- **`STREAMING`**: Continuous bidirectional data transfer across control boundaries.

### Reconciliation Framework for `INDETERMINATE` States

When an execution returns `UNKNOWN_EFFECT` for non-idempotent operations, the invocation shifts to `INDETERMINATE`. To prevent systemic stalls, reconciliation targets affected sub-resources rather than freezing entire state domains.

```
                    +------------------------------------+
                    |    Outcome: UNKNOWN_EFFECT         |
                    +-----------------+------------------+
                                      |
                                      v
                    +------------------------------------+
                    |      STATE: INDETERMINATE          |
                    |     (Halt Attempt Execution)       |
                    +-----------------+------------------+
                                      |
                                      v
                    +------------------------------------+
                    | Layer 1: Automated Verification    |
                    | Probe (Status API / Head Check)    |
                    +-----------------+------------------+
                                      |
                 +--------------------+--------------------+
                 |                                         |
     Probe Yields Determinism?                  Probe Inconclusive?
                 |                                         |
                 v                                         v
   +---------------------------+             +---------------------------+
   | Map Target Effect Outcome:|             | Layer 2: Targeted         |
   | • EFFECT_CONFIRMED        |             | Scope Quarantine          |
   | • EFFECT_NOT_APPLIED      |             | QuarantineScope ⊆ Domain  |
   | • EFFECT_PARTIALLY_APPLIED|             +-------------+-------------+
   +-------------+-------------+                           |
                 |                                         v
                 v                           +---------------------------+
   +---------------------------+             | Layer 3: Manual Operator  |
   | Update Ledger & Resume    |             | Administrative Escalation |
   +---------------------------+             +---------------------------+
```

---

## 5. PLATFORM TAXONOMY: CORTEX VS. SPECIALIZED TOOLS

| Dimension | Specialized Systems (LLMD, Ray, Kafka, Envoy) | Cortex Execution & Authority Substrate |
| :--- | :--- | :--- |
| **Primary Domain** | High-performance inference, raw byte streaming, network routing. | Bounded, authorized, audit-verifiable agent execution and side-effects. |
| **Authority Model** | Implicit network perimeter trust or simple bearer token validation. | Zero-Trust Control Plane: Capabilities, leases, workload identity, state locks. |
| **Data Plane** | Heavy payload streaming (KV cache, tensors, raw streams). | Metadata-First (`ObjectRef`): Small control envelopes carrying immutable references. |
| **Side-Effect Safety**| Optimizes throughput; no formal actuation boundary or replay proofs. | Pre-actuation fencing, execution lineage, and verifiable recovery. |
| **Integration** | Serves as an **Execution Agent** or **External Resource** under Cortex. | Orchestrates, governs, and gates execution across tools without owning internals. |

---

## 6. CONSOLIDATED PRE-PHASE 5 IMPLEMENTATION BACKLOG

All architectural iterations are closed. The core abstractions are frozen and mapped to four concrete Pre-Phase 5 backlog deliverables:

| Backlog Deliverable | Phase Milestone | Core Architectural Scope | Dependencies |
| :--- | :---: | :--- | :---: |
| **1. ResourceContract & Context** | **Pre-Phase 5** | `ResourceContract` trait, `AdapterExecutionContext`, `EffectPayload` ($\le 64\,\text{KiB}$ limit), `EvidencePayload` ($\le 4\,\text{KiB}$ limit), `CorrelationLineage`. | None |
| **2. Gateway Idempotency Engine** | **Pre-Phase 5** | Gateway HMAC-SHA256 key derivation, `LeaseEpoch` fencing, monotonic attempt progression rules. | ResourceContract |
| **3. Streaming ObjectRef Engine** | **Pre-Phase 5** | `DataPlaneResolver`, `PhysicalLocatorHandle` resolution, `BoundedChunkReader` ($\le 64\,\text{KiB}$ limit), streaming SHA-256 verification. | ResourceContract |
| **4. Effect Reconciliation Engine**| **Pre-Phase 5** | `INDETERMINATE` transition machine, probing interfaces, outcome state mapping (`EFFECT_CONFIRMED`, `EFFECT_NOT_APPLIED`, `EFFECT_PARTIALLY_APPLIED`), `QuarantineScope`. | Gateway Idempotency Engine |
