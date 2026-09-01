# CORTEX — WORKER/IPC ARCHITECTURE & LIVE GITHUB BACKLOG RECONCILIATION

**Document Identifier:** `CORTEX-RECONCILIATION-2026-V1`  
**Classification:** Canonical Backlog & Architectural Alignment Specification  
**Target Subsystems:** Worker Runtime, CBE Streaming Transport, ObjectRef Data Plane, External Adapters, Issue Backlog  
**Audit Date:** August 23, 2026  

---

## 1. CURRENT WORKER EXECUTION MODEL

- **Implementation Reality:** `IMPLEMENTATION-VERIFIED` (Synchronous / Process-Blocking).
- **Execution Substrate:** Individual Python worker plugin instances (`cortex/plugin.py`) execute single-threaded synchronous event handlers (`on_event()`).
- **Isolation Boundary:** Process-level isolation via Linux namespaces, Landlock path restrictions (`landlock_paths`), and seccomp syscall whitelisting (`Profile_A_Linux_Strict` in `config_resolver.py`).
- **Concurrency Mechanism:** Individual worker processes handle 1 active job at a time. System-level concurrency is achieved strictly through **bounded worker replica scaling** (`ReplicaGroupConfig`) and Gateway least-inflight candidate scheduling (`router.py:156`).

---

## 2. CURRENT CBE STREAMING TRANSPORT MODEL

- **Implementation Reality:** `IMPLEMENTATION-VERIFIED` & `FORMALLY PROVEN` (Coq `CBESpec.v`).
- **Layer 2 Wire Format:** Fixed 11-byte binary header (`Magic b"CF"` + 1B `Type` + 4B `Sequence` + 4B `PayloadLen`) followed by Layer 1 CBE binary payload AST.
- **Protocol-Derived Memory Bound:**  
  $$C_{\text{decoder}} \le N_{\text{max\_buffered\_frames}} \times (\text{MAX\_FRAME\_SIZE} + \text{HEADER\_SIZE}) + \text{MARGIN}_{\text{overhead}}$$
  - $N_{\text{max\_buffered\_frames}} = 1$: $C_{\text{decoder}}^{(1)} = 16,842,763 \text{ bytes} \approx 16.0625 \text{ MiB}$.
- **Security Scope Distinction:**  
  *CBE Layer 2 transport provides bounded framing, payload length validation, and in-session sequence ordering. Cryptographic data integrity, authentication, authorization, and cross-session replay resistance are provided strictly by higher layers (`SignedIntent` SHA-256 digest chains and monotonic `LeaseEpoch` fencing in `LeaseManager`).*

---

## 3. CURRENT OBJECT & DATA PLANE MODEL

- **Implementation Reality:** `IMPLEMENTATION-VERIFIED` ($\le 16\text{ MiB}$) & `DESIGNED ONLY` ($> 16\text{ MiB}$).
- **In-Line Payload Threshold:** Payloads $\le 16\text{ MiB}$ transit in-line over CBE binary streams.
- **Out-of-Band Handle (`ObjectRef`):** Payloads $> 16\text{ MiB}$ MUST use the canonical content-addressed handle abstraction:
  ```python
  @dataclass(frozen=True)
  class ObjectRef:
      provider: str             # "local_fs", "posix", "s3", "minio", "db_blob"
      namespace: str            # Bucket / storage namespace
      object_id: str            # Object path or key
      version: str              # Object version / ETag
      content_hash: str         # Hex SHA-256 digest ("sha256:...")
      size_bytes: int           # Exact byte length
      media_type: str           # Canonical MIME type
      provenance: str           # Originating ClientInvocationID
      authorization_scope: str  # Capability claim / token
  ```
- **Shared Object Write Safety:** Enforced via Gateway `StateDomainKey` locks (`router.py:288`), isolated temporary staging (`/tmp/sandbox_*`), and atomic file replacement (`os.replace`) with parent directory `fsync` (`ledger.py:354`).

---

## 4. CURRENT EXTERNAL INTEGRATION MODEL

- **Implementation Reality:** `NOT IMPLEMENTED` (Designed as Gateway Services / Worker Capabilities).
- **Security Policy:** External integrations (S3, PostgreSQL/MySQL, SMTP email, HTTP APIs, MCP tool servers) MUST NOT execute directly inside unprivileged worker sandboxes. They execute through Gateway TCB Adapter Services adhering to the normative `ExternalEffectContract` (`docs/architecture/external_adapter_architecture.md`).
- **Retry Barrier:** Automatic retries for `NON_IDEMPOTENT_WRITE` external side effects are strictly forbidden. Failed non-idempotent invocations transition directly to terminal `INDETERMINATE` state in `InvocationStateLedger` (`ledger.py:278`).

---

## 5. CURRENT WORKFLOW ORCHESTRATION MODEL

- **Implementation Reality:** `DESIGNED ONLY` (Transient Event Bus Active).
- **Event Bus Behavior:** Workers publish events via `PluginContext.publish()`; Gateway dispatches events to registered event consumers (`consumes_events`).
- **Durability Limit:** Multi-step workflow state transitions do NOT persist across full Gateway process restarts. Persistent multi-step DAG workflow orchestration is explicitly classified as a **future architectural capability**.

---

## 6. CURRENT SCALING MODEL & BOTTLENECK ANALYSIS

| Scaling Range | Component | Complexity Class | Bottleneck Profile & Mitigation |
| :--- | :--- | :---: | :--- |
| **10 Workers** | Registry & Routing | $O(1)$ | Zero measurable bottleneck; linear scaling. |
| **100 Workers** | Candidate Selection | $O(N \log N)$ | Sorting candidate inflight scores; negligible overhead. |
| **1,000 Workers** | Lease Acquisition | $O(1)$ lock | Python GIL contention on `LeaseManager` single lock (`lease.py`). |
| **10,000 Workers** | Socket Descriptors | $O(N)$ connections | OS `ulimit -n` file descriptor ceiling; requires socket pooling. |

---

## 7. EXISTING GITHUB ISSUE COVERAGE

The live GitHub repository audit (`Iradukunda-Fils/Cortex`) verified 32 total issues and 8 pull requests:

| Issue ID | Title / Subsystem | Status | Audit Classification |
| :--- | :--- | :---: | :--- |
| **#19** | `community: create newcomer documentation` | OPEN | `COMMUNITY` / `DOCUMENTATION` |
| **#23** | `security: external security review and P0-P13 checklist` | OPEN | `SECURITY_BLOCKER` |
| **#30** | `fix(config): Align environment resolution with config resolver` | CLOSED | `ALREADY_IMPLEMENTED` (Verified) |
| **#31** | `feat(ledger): Implement snapshot model and memory compaction` | CLOSED | `ALREADY_IMPLEMENTED` (Verified) |
| **#32** | `proof(formal): Formalize GatewayDispatcher linearizability in Coq` | OPEN | `STILL_REQUIRED` / `FORMAL_ASSURANCE` |
| **#33** | `security(sandbox): Finalize Profile B WASM sandbox profile` | OPEN | `STILL_REQUIRED` / `SECURITY_BLOCKER` |
| **#34** | `feat(phase-5): Implement single-gateway dynamic load balancer` | OPEN | `PREMATURE` (Reprioritized behind #41, #42, #43) |
| **#35** | `docs(audit): Resolve 222 repository audit debt items` | OPEN | `STILL_REQUIRED` / `DOCUMENTATION` (Updated) |
| **#36** | `test(verifier): Construct independent verifier CLI test suite` | OPEN | `STILL_REQUIRED` / `SECURITY_BLOCKER` |
| **#37** | `ci(hardware): Integrate Yosys open-source synthesis gate check` | OPEN | `HARDWARE` / `PERFORMANCE` |

---

## 8. CONSOLIDATED PRE-PHASE 5 BACKLOG, RESEARCH & COQ PROOF OBLIGATIONS

To ensure that implementation, research documentation, and formal machine verification proceed in lockstep, every Pre-Phase 5 backlog deliverable is explicitly mapped to its research reference, implementation target, and formal Coq proof obligation:

| Issue ID | Deliverable Module | Research Specification Reference | Code Target | Coq Proof Obligation (`verification/*.v`) | Target Milestone |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **#41** | **CBE Decoder Memory Bounds** | `docs/architecture/cbe_transport_architecture.md` | `cortex/cbe/streaming.py` | `CBESpec.v`: `cbe_stream_buffer_bounded_safety` | `v0.4.1-experimental` (P0) |
| **#42** | **ObjectRef Data Plane & Locators** | `docs/architecture/object_transfer_and_shared_resource_model.md` | `cortex/tools/kernel/object_ref.py` | `GateF_F4_EvidenceRefinement.v`: `object_ref_hash_integrity` | `v0.5.0-experimental` (P1) |
| **#43** | **`ResourceContract` & Context** | `docs/architecture/external_adapter_architecture.md` | `cortex/tools/kernel/adapter_contract.py` | `Phase4RoutingRefinement.v`: `rd_f1_eligibility_safety` | `v0.5.0-experimental` (P1) |
| **#44** | **Gateway HMAC Idempotency** | `docs/architecture/cortex_system_architecture_specification.md` | `cortex/tools/kernel/idempotency.py` | `GateL1_EpochMonotonicity.v`: `hmac_idempotency_monotonic_epoch` | `v0.5.0-experimental` (P1) |
| **#45** | **Effect Reconciliation Machine** | `docs/architecture/worker_execution_model.md` | `cortex/tools/kernel/reconciliation.py` | `Phase4RoutingRefinement.v`: `rd_f6_unadmitted_durable_safety` | `v0.5.0-experimental` (P1) |

---

### Detailed Scope & Coq Proof Mapping per Issue:

#### 1. Issue #41: `feat(cbe): Enforce protocol-derived decoder memory bounds and stream buffer protection`
- **Research Spec:** Section 2 of `docs/architecture/cbe_transport_architecture.md` & `cortex_system_architecture_specification.md`.
- **Implementation Scope:** Enforce $C_{\text{decoder}}^{(1)} \le 16,842,763 \text{ bytes}$ limit in `StreamDecoder.feed()`.
- **Coq Proof Obligation:** Verify in `CBESpec.v` that for any sequence of input frames, memory overhead remains strictly bounded by $N_{\text{buffered}} \times (\text{MaxPayload} + \text{Header}) + \text{Margin}$.

#### 2. Issue #42: `feat(storage): Implement canonical ObjectRef Data Plane, Opaque Locators, and BoundedChunkReader`
- **Research Spec:** `docs/architecture/object_transfer_and_shared_resource_model.md`.
- **Implementation Scope:** `ObjectRef`, `DataPlaneResolver`, opaque `PhysicalLocatorHandle` tokens, `BoundedChunkReader` ($\le 64\,\text{KiB}$ chunk guard), and SHA-256 byte-stream verification.
- **Coq Proof Obligation:** Formally prove in `GateF_F4_EvidenceRefinement.v` that data plane resolution cannot produce physical locator handles without a valid capability and lease token.

#### 3. Issue #43: `feat(adapters): Define canonical ResourceContract, AdapterExecutionContext, and Ephemeral Lineage`
- **Research Spec:** `docs/architecture/external_adapter_architecture.md`.
- **Implementation Scope:** `ResourceContract` trait, `AdapterExecutionContext` JSON schema (`https://schemas.cortex.internal/v1/adapter-execution-context.json`), `EffectPayload` ($\le 64\,\text{KiB}$), `EvidencePayload` ($\le 4\,\text{KiB}$), and `CorrelationLineage` struct.
- **Coq Proof Obligation:** Extend `Phase4RoutingRefinement.v` (`rd_f1_eligibility_safety`) to prove zero credential leakage across sandboxed worker process boundaries.

#### 4. Issue #44: `feat(gateway): Implement Authoritative Gateway HMAC Idempotency Engine and LeaseEpoch Fencing`
- **Research Spec:** Section 2 of `docs/architecture/cortex_system_architecture_specification.md`.
- **Implementation Scope:** Gateway HMAC-SHA256 key derivation ($K_{\text{idempotency}}$), `LeaseEpoch` revalidation, and retry attempt progression ($a_{n+1} \neq a_n, \text{Epoch}_{n+1} > \text{Epoch}_n$).
- **Coq Proof Obligation:** Prove in `GateL1_EpochMonotonicity.v` that retried executions maintain identical idempotency keys while strictly advancing lease epochs.

#### 5. Issue #45: `feat(reconciliation): Implement Effect Reconciliation Engine and Layered Quarantine Machine`
- **Research Spec:** Section 4 of `docs/architecture/cortex_system_architecture_specification.md`.
- **Implementation Scope:** State machine transitioning `UNKNOWN_EFFECT` to `INDETERMINATE`, Layer 1 verification probes (`EFFECT_CONFIRMED`, `EFFECT_NOT_APPLIED`, `EFFECT_PARTIALLY_APPLIED`), and Layer 2 `QuarantineScope` isolation.
- **Coq Proof Obligation:** Prove in `Phase4RoutingRefinement.v` (`rd_f6_unadmitted_durable_safety`) that non-idempotent operations in `INDETERMINATE` state cannot undergo automatic re-actuation.

---

## 9. CONSOLIDATED REVISED DEPENDENCY GRAPH

```
                          ┌──────────────────────────────────────────────────────────┐
                          │   Issue #41: CBE Protocol-Derived Decoder Memory Bound   │
                          │   (Research Spec: cbe_transport_architecture.md)         │
                          │   (Coq Formal Proof: CBESpec.v)                          │
                          └────────────────────────────┬─────────────────────────────┘
                                                       │
                                 ┌─────────────────────┴─────────────────────┐
                                 ▼                                           ▼
       ┌──────────────────────────────────────────────────┐ ┌──────────────────────────────────────────────────┐
       │ Issue #42: ObjectRef Data Plane & Opaque Locators│ │ Issue #43: ResourceContract & Ephemeral Context │
       │ (Research Spec: object_transfer_model.md)        │ │ (Research Spec: external_adapter_architecture.md)│
       │ (Coq Formal Proof: GateF_F4_EvidenceRefinement.v)│ │ (Coq Formal Proof: Phase4RoutingRefinement.v)   │
       └──────────────────────────────────────────────────┘ └─────────────────────────┬────────────────────────┘
                                                                                      │
                                                                                      ▼
                                                            ┌──────────────────────────────────────────────────┐
                                                            │ Issue #44: Gateway HMAC Idempotency & Fencing    │
                                                            │ (Research Spec: system_architecture_spec.md)     │
                                                            │ (Coq Formal Proof: GateL1_EpochMonotonicity.v)   │
                                                            └─────────────────────────┬────────────────────────┘
                                                                                      │
                                                                                      ▼
                                                            ┌──────────────────────────────────────────────────┐
                                                            │ Issue #45: Effect Reconciliation & Quarantine    │
                                                            │ (Research Spec: worker_execution_model.md)       │
                                                            │ (Coq Formal Proof: Phase4RoutingRefinement.v)   │
                                                            └─────────────────────────┬────────────────────────┘
                                                                                      │
                                                                                      ▼
                                                            ┌──────────────────────────────────────────────────┐
                                                            │ Issue #34: Phase 5 Dynamic Load Balancer Engine  │
                                                            │ (Release Target: v0.5.0-experimental | P2 Feature)│
                                                            └──────────────────────────────────────────────────┘
```

---

## 10. FINAL DECISION & SINGLE NEXT IMPLEMENTATION TARGET

> [!IMPORTANT]
> **SINGLE NEXT ENGINEERING IMPLEMENTATION TARGET:**
>
> **Issue #41: `feat(cbe): Enforce protocol-derived decoder memory bounds and stream buffer protection`**
>
> **Rationale:**
> 1. **Security Impact:** Enforcing the protocol-derived memory bound $C_{\text{decoder}}^{(1)} \le 16,842,763 \text{ bytes}$ eliminates the open socket stream buffer memory accumulation vulnerability identified in the audit.
> 2. **Architectural Dependency:** Issue #41 is the immediate P0 prerequisite blocking all subsequent data-plane work (#42 ObjectRef) and adapter work (#43 ResourceContract).
> 3. **Verification Readiness:** The Layer 2 `StreamDecoder` state machine (`cortex/cbe/streaming.py`) is fully implemented and tested (347/347 green tests), allowing immediate, clean, evidence-driven implementation and verification.

---
