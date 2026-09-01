# CORTEX — DEEP WORKER RUNTIME, IPC, PIPELINE, SHARED-RESOURCE & SCALE ASSURANCE AUDIT

**Document Identifier:** `CORTEX-AUDIT-WIR-2026-V1`  
**Classification:** Clean-Room Architectural & Proof Assurance Audit  
**Target Subsystems:** Worker Runtime, CBE Streaming Transport, Capability Enforcement, Request/Response Pipeline, Shared Resources, External Adapters, Scaling Model  
**Audit Date:** August 23, 2026  
**Follow-Up Revision:** V1.1 (Protocol Memory Derivation, Calibrated Claims & ObjectRef Foundation)  

---

## 1. PRIMARY AUDIT QUESTIONS & EVIDENCED ANSWERS

### A. What exactly can a Cortex worker do?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED` (Bounded by Config/Manifest)  
A worker process (or Python `BasePlugin` / Go replica process) can:
1. Receive strongly-typed, schema-validated events or invocations matching its declared event consumption contract (`consumes_events` in `PluginManifest`).
2. Emit strongly-typed events or return invocation results over bounded IPC connections (`publish()` in `PluginContext` via `cortex/plugin.py`).
3. Exercise platform capabilities explicitly admitted by `CapabilityNegotiator` and enforced by `ConfigResolver` / `LeaseManager` (e.g., `host.read`, `host.write` mapped via `CanonicalCapability`).
4. Execute localized computations in an isolated sandbox environment (Linux process with Landlock/seccomp profiles specified in `SandboxConfig`).

### B. What exactly can a worker NOT do?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
A worker CANNOT:
1. Mutate Gateway TCB state, issue its own `ExecutionToken` or `LeaseEpoch` (`cortex/tools/kernel/replica/router.py:9`).
2. Bypass candidate revalidation or self-grant an execution lease (`lease.py:130`).
3. Request capability widening at runtime (`loader.py:42-65`).
4. Perform unauthorized filesystem access outside `allowed_write_paths` or `landlock_paths` (`config_resolver.py:218-246`).
5. Execute unadmitted syscalls outside `allowed_syscalls` under `Profile_A_Linux_Strict` (`config_resolver.py:118`).
6. Advance commit state or write directly to the durable `InvocationStateLedger` journal (`ledger.py:65`).

### C. What authority is held by each system role?

| System Role | Authority Held | Concrete Enforcement Point |
| :--- | :--- | :--- |
| **Worker** | Unprivileged execution of admitted functions; event publication scoped to granted capabilities. | `cortex/plugin.py:BasePlugin`, Landlock/Seccomp Sandbox |
| **Gateway** | Trusted Computing Base (TCB) root authority; manages lifecycle, config admission, and state domain locks. | `cortex/tools/kernel/replica/router.py:GatewayDispatcher` |
| **Router** | Unprivileged candidate filtering and policy proposal. Zero token/lease issuance power. | `cortex/tools/kernel/replica/router.py:CandidateResolver` |
| **LeaseManager** | Exclusive issuer of monotonic `LeaseEpoch` counters and `OwnershipIdentity` tokens. Linearization point. | `cortex/tools/kernel/replica/lease.py:LeaseManager` |
| **Ledger** | Sole durable tracking authority for invocation states and crash-recovery classification. | `cortex/tools/kernel/replica/ledger.py:InvocationStateLedger` |
| **Sandbox Supervisor** | Process-level syscall, path containment, and resource limit enforcer. | `cortex/tools/kernel/config_resolver.py:SandboxConfig`, OS Kernel |
| **External Adapters** | `NOT IMPLEMENTED` (Designed as Gateway-managed services or capability-bounded worker adapters). | N/A (Mocks in test suite) |

### D. How does binary IPC actually work?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
IPC is implemented via Canonical Binary Encoding (CBE) streaming frames over Unix domain sockets or standard I/O pipes.
- **Wire Frame:** 11-byte fixed binary header followed by $N$ payload bytes (`cortex/cbe/streaming.py:15-20`).
- **Header Layout:** `Magic` (2 bytes `b"CF"`) + `FrameType` (1 byte) + `Sequence` (4 bytes `uint32` Big-Endian) + `PayloadLength` (4 bytes `uint32` Big-Endian).
- **Payload:** Layer 1 CBE deterministic byte stream representing AST value trees (`Null`, `Bool`, `Int64`, `Float64`, `String`, `Bytes`, `List`, `Map`).

### E. What does CBE guarantee?
**Evidenced Status:** `FORMALLY PROVEN` (Coq `CBESpec.v`) & `IMPLEMENTATION-VERIFIED` (`cortex/cbe/`)
1. **Canonical Determinism:** Identical AST values produce 100% byte-identical serialized outputs across Python, Rust, and Go runtimes.
2. **Deterministic Map Key Ordering:** UTF-8 byte sorting of NFC-normalized map keys (`CBESpec.v:byte_list_lt`, `encoder.py:82`).
3. **Strict Number Normalization:** Signed 64-bit bounds check for integers (`[-2^63, 2^63 - 1]`) and Double-precision IEEE-754 floats with non-finite (`NaN`/`Inf`) rejection and `-0.0` to `+0.0` normalization (`types.py:132`).
4. **Stream Frame Parsing Safety:** Framing boundaries, sequence gap detection per connection session, and max frame payload ceiling (16 MiB).

### F. What does CBE NOT guarantee?
**Evidenced Status:** `DESIGNED / CODE-VERIFIED GAP` (Critical Security Distinction)  
CBE framing (`b"CF"` + 11-byte header) **DOES NOT** provide:
1. **Cryptographic Data Integrity:** Header contains NO checksum, CRC32, HMAC, or SHA-256 digest (`streaming.py:121-125`). Payload corruption on raw sockets is NOT detected at Layer 2.
2. **Authentication / Identity:** Header contains NO worker signature, bearer token, or identity field (`streaming.py:92-98`).
3. **Cross-Session Replay Protection:** Sequence numbers track frame indices *within a single TCP/Unix socket stream session*. Upon socket reconnect, sequence resets to 0 (`StreamEncoder.__init__`). Sequence numbers do NOT prevent replaying frames across socket sessions.
4. **Authorization:** Frame header carries no capability credentials or lease epoch tags.

*Security Layer Attribution:* Authentication, cryptographic integrity, and cross-session replay protection are provided **ONLY by upper layers** (`SignedIntent`, `CommitEvent` digest chains verified in Coq `F4b_ConcreteCryptoRefinement`, and `LeaseEpoch` checked in `LeaseManager`).

### G. How are messages correlated to invocations?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
Each message payload wraps a `CortexValue::Map` containing an explicit `invocation_id` (UUIDv4 / string). The `GatewayDispatcher` tracks `invocation_id` through the `InvocationStateLedger` (`router.py:196`, `ledger.py:53`).

### H. How are replies matched to requests?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
Replies contain the request's original `invocation_id` along with the granted `lease_epoch`. The Gateway matches incoming worker responses against active leases in `LeaseManager.commit_invocation(invocation_id, lease_epoch)` (`lease.py:183`).

### I. What happens when a worker waits for a long-running operation?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
Current Python workers (`cortex/plugin.py`, `cortex/client.py`) operate strictly as **synchronous, process-blocking execution agents**. When executing a long-running operation (e.g., subprocess execution or blocking network call), the worker process thread is **blocked**.

### J. Can a worker process independent work while one operation is running?
**Evidenced Status:** `CODE-VERIFIED: NO`  
In the current implementation, an individual worker process instance cannot process concurrent independent requests while blocked on a synchronous execution. Concurrent processing relies entirely on **horizontal replica scaling** (dispatching independent requests to other ready worker replica instances in the `ReplicaGroup`) (`router.py:270`).

### K. What happens when the worker blocks?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
The Gateway tracks `observed_inflight` per worker instance. When `observed_inflight >= max_worker_inflight` (default 10), `CandidateResolver` excludes the worker from candidate selection (`router.py:136`). If all workers block, incoming requests buffer in the `GatewayDispatcher` per-group FIFO queue up to `max_queue_depth` (default 1000) before raising `QueueFullError` (`router.py:228`).

### L. How are timeouts, cancellation, retries, and disconnects handled?
- **Queue Timeout:** If request stays queued past `queue_timeout_sec` (30s), `QueueTimeoutError` is raised and state transitions to `REJECTED` (`router.py:39`).
- **Dispatch Deadline:** Gateway enforces `dispatch_deadline_sec` (5s) for candidate selection (`router.py:178`).
- **Disconnect / Worker Crash:** Gateway classifies in-flight invocation via `InvocationStateLedger.classify_recovery()`. Unactuated work -> `ADMITTED_UNACTUATED` (safe to retry); Actuating/Unknown -> `ACTUATION_UNKNOWN` -> `INDETERMINATE` (terminal state; automatic retries strictly forbidden across non-idempotent boundaries) (`ledger.py:270`).

### M. How does a file move between multiple workers?
**Evidenced Status:** `DESIGNED ONLY` (No binary payload transport between workers)  
Cortex does not pass raw large files over CBE socket IPC. Shared file movement relies on file path references (`local_path`) or URI references (`s3://...`) encapsulated in the canonical `ObjectRef` handle (`docs/architecture/object_transfer_and_shared_resource_model.md`).

### N. Can multiple workers safely read the same file?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED` (FS Level)  
Yes, provided the file is stored in an immutable content-addressed path or designated read-only directory (`landlock_paths`, `config_resolver.py:119`).

### O. Can multiple workers safely write the same file?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED` (Via Gateway State Domain Locks)  
Direct uncoordinated concurrent writing to the same file path by multiple workers is UNSAFE. Cortex mitigates this using `ExecutionClass.SERIALIZED_STATE_DOMAIN` and `StateDomainKey` locks managed by `GatewayDispatcher` (`router.py:288`).

### P. How are shared files versioned?
**Evidenced Status:** `DESIGNED ONLY`  
Explicit object versioning (`ObjectRef` with version + SHA-256 hash) is specified in `docs/architecture/object_transfer_and_shared_resource_model.md`.

### Q. How are S3/database/email/MCP interactions represented?
**Evidenced Status:** `NOT IMPLEMENTED` (Designed as Gateway Services / Worker Capabilities)  
Currently represented as abstract capability strings (e.g., `net.outbound.s3`, `db.query`). No concrete adapter code exists in the repository; only test mocks exist in `tests/conformance/`.

### R. How are credentials isolated?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED` (Sandbox Boundary)  
Workers do NOT receive raw database/S3 credentials. Environment variables are sanitized by `ConfigResolver`, and root filesystem access is blocked via `read_only_root = True` and Landlock path confinement (`config_resolver.py:370`).

### S. How are large payloads transferred?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED` (Ceiling Enforced)  
CBE frame payload size is hard-capped at 16 MiB (`MAX_FRAME_SIZE = 16_777_216`, `streaming.py:17`). Payloads larger than 16 MiB raise `CBEFrameTooLargeError`. Payloads exceeding 16 MiB MUST use external `ObjectRef` references.

### T. At what point does Cortex use raw bytes vs references?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
- Payload $\le 16\text{ MiB}$: In-line raw bytes over CBE `Bytes` tag (`types.py:183`).  
- Payload $> 16\text{ MiB}$: Canonical `ObjectRef` handle references (`String`).

### U. What happens when a referenced file disappears?
**Evidenced Status:** `CODE-VERIFIED GAP`  
The current worker runtime raises a standard Python `FileNotFoundError` or Go I/O error during plugin execution. The Gateway catches the worker crash and classifies the invocation as `ADMITTED_UNACTUATED` or `ACTUATION_UNKNOWN` depending on execution state (`ledger.py:265`).

### V. What happens when the reference points to changed content?
**Evidenced Status:** `CODE-VERIFIED GAP`  
Without hash verification on read, silent data corruption / non-repeatable execution occurs. Architecture specifies `content_hash` verification in `ObjectRef`, but code implementation is `OPEN`.

### W. How is resource ownership tracked?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
Tracked via `OwnershipIdentity` (binding `invocation_id`, `lease_id`, and monotonic `lease_epoch`) generated by `LeaseManager` (`lease.py:146`).

### X. What prevents duplicate side effects?
**Evidenced Status:** `FORMALLY PROVEN` (Coq `GateL1_EpochMonotonicity.v`) & `IMPLEMENTATION-VERIFIED` (`lease.py:183`)  
Fencing via monotonic `LeaseEpoch`. If a worker attempts to commit a side effect under an old or revoked epoch, `LeaseManager.commit_invocation` rejects the attempt with `StaleLeaseError` (`lease.py:198`).

### Y. What prevents stale workers from acting?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
Candidate atomic revalidation inside `LeaseManager.grant_lease_with_revalidation()` checks worker `lifecycle_version`, `stage == READY`, `config_generation`, and `config_hash` under a single TCB lock acquisition (`lease.py:93-109`). Stale candidates are evicted (`router.py:275`).

### Z. What prevents unbounded queue, memory, descriptor, or connection growth?
**Evidenced Status:** `IMPLEMENTATION-VERIFIED`  
- **Queue Growth:** Hard-capped by `max_queue_depth` (default 1000) (`router.py:228`).
- **Worker In-Flight:** Capped by `max_worker_inflight` (default 10 per worker) (`router.py:136`).
- **Frame Size:** Hard-capped by `MAX_FRAME_SIZE` (16 MiB) (`streaming.py:17`).
- **Decoder Memory:** Derived upper bound $C_{\text{decoder}} \le N_{\text{buffered}} \times (\text{MaxPayload} + \text{Header}) + \text{margin}$ (`docs/architecture/cbe_transport_architecture.md`).
- **Ledger Memory:** Compaction evicts terminal records from memory into durable snapshot checkpoints (`ledger.py:295`).

---

## 2. GROUND-TRUTH REPOSITORY AUDIT INVENTORY

| Subsystem Component | Source Code Location | Status | Primary Function & Observations |
| :--- | :--- | :--- | :--- |
| **Worker Process Startup** | `cortex/tools/cli/main.py`, `cortex/plugin.py` | `IMPLEMENTATION-VERIFIED` | Scaffolds and launches plugin entrypoints. |
| **Sandbox Creation** | `cortex/tools/kernel/config_resolver.py` | `IMPLEMENTATION-VERIFIED` | Configures Landlock, read-only root, and syscall whitelist. |
| **Worker Capability Loading** | `cortex/tools/kernel/plugin/loader.py` | `IMPLEMENTATION-VERIFIED` | `CapabilityNegotiator` evaluates manifest requirements. |
| **Worker Manifest Loading** | `cortex/tools/kernel/plugin/manifest.py` | `IMPLEMENTATION-VERIFIED` | Structural schema validation of declared contracts. |
| **CBE Encoder (Python)** | `cortex/cbe/encoder.py` | `IMPLEMENTATION-VERIFIED` | Deterministic AST-to-bytes encoding with key sorting. |
| **CBE Encoder (Go)** | `cortex-go/cbe/encoder.go` | `IMPLEMENTATION-VERIFIED` | Byte-for-byte compatible Go encoder implementation. |
| **CBE Decoder (Python)** | `cortex/cbe/decoder.py` | `IMPLEMENTATION-VERIFIED` | State-machine decoder for Layer 1 values. |
| **CBE Stream Encoder/Decoder** | `cortex/cbe/streaming.py` | `IMPLEMENTATION-VERIFIED` | Layer 2 framing (`b"CF"`, 11-byte header, uint32 seq). |
| **Gateway Dispatcher** | `cortex/tools/kernel/replica/router.py` | `IMPLEMENTATION-VERIFIED` | 8-stage routing pipeline with atomic revalidation. |
| **LeaseManager** | `cortex/tools/kernel/replica/lease.py` | `IMPLEMENTATION-VERIFIED` | Linearizable epoch-bound lease manager & fencing. |
| **InvocationLedger** | `cortex/tools/kernel/replica/ledger.py` | `IMPLEMENTATION-VERIFIED` | Durable append-only journal with atomic compaction. |
| **ConfigResolver** | `cortex/tools/kernel/config_resolver.py` | `IMPLEMENTATION-VERIFIED` | 10-stage config pipeline & generation admission. |
| **External Adapters (S3, DB, Email, MCP)** | N/A | `NOT IMPLEMENTED` | No code exists; only design specs & test mocks. |
| **Workflow Orchestration / DAG** | N/A | `NOT IMPLEMENTED` | Transient event bus active; persistent DAG is OPEN. |
| **Autoscaler Engine** | `cortex/tools/kernel/config_resolver.py` | `DESIGNED ONLY` | Replica bounds in config; no dynamic scaling loop. |

---

## 3. WORKER CAPABILITY MODEL MATRIX

The following table details the enforcement lifecycle of key capabilities in Cortex:

| Capability Name | Manifest Declared | Config Repr | Resolver Validated | Sandbox Enforced | Lease Enforced | Runtime Checked | Effect Boundary | Test Parity | Formal Proof | Assurance Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `host.read` | Yes | String | Yes | Landlock | Yes | Yes | Read Filesystem | 100% | Gate F | `IMPLEMENTATION-VERIFIED` |
| `host.write` | Yes | String | Yes | Landlock / WPath | Yes | Yes | Write Filesystem | 100% | Gate F | `IMPLEMENTATION-VERIFIED` |
| `net.outbound.s3` | Yes | String | Yes | No (Net Unbounded)| No | No | External S3 API | Mocks | None | `DESIGNED ONLY` |
| `exec.ffmpeg` | Yes | String | Yes | Seccomp | No | No | Subprocess Spawn | Mocks | None | `DESIGNED ONLY` |
| `database.access` | Yes | String | Yes | No | No | No | SQL Query Exec | Mocks | None | `NOT IMPLEMENTED` |
| `email.send` | Yes | String | Yes | No | No | No | SMTP Dispatch | Mocks | None | `NOT IMPLEMENTED` |
| `mcp.tool.call` | Yes | String | Yes | No | No | No | External Protocol | Mocks | None | `NOT IMPLEMENTED` |
| `process.exec` | Yes | String | Yes | Seccomp | No | No | OS Process | 100% | Gate F | `IMPLEMENTATION-VERIFIED` |
| `ipc.stream` | Yes | Internal | Yes | Socket Pipe | Yes | Yes | CBE Socket Frame | 100% | CBESpec | `FORMALLY PROVEN` |
| `temp.storage` | Yes | String | Yes | `/tmp/sandbox_*` | Yes | Yes | Local Temp Dir | 100% | Gate F | `IMPLEMENTATION-VERIFIED` |

---

## 4. CAPABILITY NON-ESCALATION ANALYSIS

### Invariant Verification:
$$\Lambda_{\text{worker}} \subseteq \Lambda_{\text{deployment}} \subseteq \Lambda_{\text{system}}$$

**Concrete Enforcement Points:**
1. **Manifest vs Platform Negotiation:** `CapabilityNegotiator.negotiate()` compares requested capabilities against `platform_capabilities`. Unrecognized or forbidden capabilities cause immediate `REJECTED` plugin state (`loader.py:60`).
2. **Security Ceiling Enforcement:** `ConfigResolver.resolve()` enforces `EffectiveConfig <= SecurityCeiling`. Attempts to disable `read_only_root` or alter strict profiles without `security_override` raise `SecurityCeilingViolationError` (`config_resolver.py:363-380`).
3. **Atomic Candidate Revalidation:** `LeaseManager.grant_lease_with_revalidation()` asserts `capability_envelope_hash` matches active config before granting lease (`lease.py:108`).

---

## 5. CBE FRAME PROTOCOL & DERIVED MEMORY BOUND

### Protocol-Derived Memory Bound:
Rather than relying on un-derived constant guesses, the stream decoder memory bound $C_{\text{decoder}}$ is derived strictly from protocol limits (`docs/architecture/cbe_transport_architecture.md`):

$$C_{\text{decoder}} \le N_{\text{max\_buffered\_frames}} \times (\text{MAX\_FRAME\_SIZE} + \text{HEADER\_SIZE}) + \text{MARGIN}_{\text{overhead}}$$

- For $N_{\text{max\_buffered\_frames}} = 1$ and 64 KiB margin: $C_{\text{decoder}}^{(1)} = 16,842,763 \text{ bytes} \approx 16.0625 \text{ MiB}$.
- For $N_{\text{max\_buffered\_frames}} = 2$ and 64 KiB margin: $C_{\text{decoder}}^{(2)} = 33,620,000 \text{ bytes} \approx 32.0625 \text{ MiB}$.

---

## 6. CRITICAL DISTINCTION: FRAMING VS INTEGRITY VS AUTHENTICATION

> [!CAUTION]
> **ARCHITECTURAL DRIFT WARNING:** Do NOT claim CBE framing provides cryptographic integrity, authentication, or cross-session replay protection.

```
+-----------------------------------------------------------------------+
|  APPLICATION LAYER: SignedIntent / CommitEvent                        |
|  - Cryptographic Integrity: SHA-256 Digest Chains                     |
|  - Authentication: Signatures & ExecutionTokens                      |
|  - Cross-Session Replay Protection: Monotonic LeaseEpoch Fencing      |
+-----------------------------------------------------------------------+
|  TRANSPORT LAYER: CBE Framing (streaming.py)                           |
|  - Framing Boundaries: Magic b"CF", 11-byte Header                    |
|  - Stream Ordering: In-Session uint32 Sequence Number                |
|  - Length Validation: Max 16 MiB Payload Limit                        |
+-----------------------------------------------------------------------+
|  OPERATING SYSTEM / HARWARE LAYER                                     |
|  - Process Isolation: Linux Namespaces, Landlock, Seccomp             |
|  - Transport Security: Unix Domain Socket File Permissions / TLS     |
+-----------------------------------------------------------------------+
```

---

## 7. CANONICAL `ObjectRef` ARCHITECTURE & WORKFLOWS

Large payload transfers (videos, audio, PDFs $>16\text{ MiB}$) do not transit the Gateway CBE IPC socket. They use the canonical `ObjectRef` handle specification (`docs/architecture/object_transfer_and_shared_resource_model.md`):

```python
@dataclass(frozen=True)
class ObjectRef:
    provider: str             # "local_fs", "posix", "s3", "minio", "db_blob"
    namespace: str            # Storage namespace / bucket
    object_id: str            # Object path or key identifier
    version: str              # Object version / ETag string
    content_hash: str         # Hex SHA-256 digest ("sha256:...")
    size_bytes: int           # Exact byte length
    media_type: str           # Canonical MIME type
    provenance: str           # Originating ClientInvocationID
    authorization_scope: str  # Capability claim / scoped read token
```

### Media / AI Workflow Execution Pattern:
```
AI Worker ──(TextExtractionRequested + ObjectRef)──> Gateway ──(Authorize & Lease)──> Media Worker
                                                                                          │
                                                                                 (READ ObjectRef)
                                                                                          │
                                                                                          ▼
AI Worker <──(Derived ObjectRef / Result)────────── Gateway <──(Publish Result)───────────┘
```

---

## 8. EXTERNAL EFFECT ADAPTER CONTRACT

All external integrations (S3, Postgres, SMTP, MCP) MUST adhere to the normative `ExternalEffectContract` (`docs/architecture/external_adapter_architecture.md`):

```python
@dataclass(frozen=True)
class ExternalEffectContract:
    adapter_id: str             # Adapter identifier ("adapter.s3.v1")
    capability_required: str    # Platform capability ("net.outbound.s3")
    effect_classification: str  # READ_ONLY, IDEMPOTENT_WRITE, NON_IDEMPOTENT_WRITE, TRANSACTIONAL
    idempotency_key_field: str  # Idempotency key attribute
    timeout_sec: float          # Hard timeout in seconds
    retry_policy: str           # NEVER_AUTOMATIC, RETRY_IDEMPOTENT_BOUNDED, TRANSACTIONAL_ROLLBACK
    result_schema: str          # Expected return schema type
    evidence_witness: bool      # Requires witness audit event
```

---

## 9. DECISION MATRIX

| Capability / Mechanism | Current Implementation | Evidence Location | Trust Level | Security Risk | Scale Risk | Formal Status | Recommended Architecture | Recommended Next Step |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Large File Transfer** | Local Path String | `config_resolver.py` | Medium | Medium (Symlinks) | Low | `DESIGNED` | Content-Addressed `ObjectRef` | Implement canonical `ObjectRef` handle |
| **Worker-to-Worker Request** | Gateway Event Bus | `plugin.py` | High | Low | Medium | `VERIFIED` | Gateway-Mediated Event Dispatch | Maintain existing Gateway mediation |
| **S3 Object Access** | Mocked in Tests | `test_replica_phase_4.py` | Low | High (Cred Leak) | Medium | `NOT IMPL` | Gateway S3 Adapter Service | Define `ObjectRef` before S3 adapter |
| **DB Query Execution** | Mocked in Tests | N/A | Low | High (SQLi) | High | `NOT IMPL` | Gateway DB Pool Adapter | Define `ExternalEffectContract` first |
| **Email Dispatch** | Mocked in Tests | N/A | Low | High (Spam/Side-FX)| Low | `NOT IMPL` | Non-Idempotent Gateway Service | Enforce `INDETERMINATE` guard |
| **MCP Tool Call** | Mocked in Tests | N/A | Low | High (Arbitrary Exec)| High | `NOT IMPL` | Sandboxed MCP Adapter Worker | Build isolated MCP supervisor |
| **Long-Running Job** | Synchronous Worker | `plugin.py` | High | Low | High | `VERIFIED` | Horizontal Replica Scaling | Preserve process isolation model |
| **Cancellation** | Queue Expiry | `router.py` | High | Low | Low | `VERIFIED` | Monotonic Epoch Revocation | Extend cancellation signal down CBE stream |
| **Retry Boundary** | Ledger Classifier | `ledger.py` | High | Low | Low | `VERIFIED` | Non-Idempotent Guard | Retain `INDETERMINATE` state barrier |

---

## 10. IMPORTANT CLAIM CALIBRATION

| Document Claim | Calibration Status | Actual Evidenced Reality |
| :--- | :---: | :--- |
| *"CBE provides data integrity"* | **FALSE** | CBE provides framing boundaries and sequence checks, but **NO cryptographic MAC/hash** in header. |
| *"CBE provides replay protection"* | **PARTIAL** | CBE sequence numbers track order within a single socket stream session; **cross-session replay protection relies on LeaseEpoch**. |
| *"Workers are non-blocking"* | **FALSE** | Individual Python worker plugin threads **block on synchronous calls**; system concurrency comes from worker replicas. |
| *"Workers process jobs concurrently"* | **FALSE** | A single worker process handles **1 job at a time** (`observed_inflight` tracked by Gateway). |
| *"Gateway automatically scales workers"* | **DESIGNED** | `ReplicaGroupConfig` sets `min/max_replicas`, but the dynamic autoscaling feedback loop is `NOT IMPLEMENTED`. |
| *"Shared files are safe"* | **VERIFIED** | Enforced via Landlock read-only paths and Gateway `StateDomainKey` locks. |
| *"External adapters are isolated"* | **DESIGNED** | Adapters are not yet implemented; design mandates Gateway TCB isolation. |
| *"Credentials are isolated"* | **VERIFIED** | Secrets remain in Gateway TCB; workers operate under read-only sandboxes. |
| *"Workflow execution is durable"* | **PARTIAL** | Ledger state machine is crash-durable; persistent multi-step DAG workflow engine is `NOT IMPLEMENTED`. |

---

## 11. PRIORITIZED ENGINEERING IMPLEMENTATION SEQUENCE

> [!IMPORTANT]
> **REVISED ENGINEERING IMPLEMENTATION SEQUENCE:**
>
> 1. **CBE Decoder Memory Bound & Claim Calibration:**  
>    Enforce protocol-derived memory bound $C_{\text{decoder}} \le N_{\text{buffered}} \times (\text{MaxPayload} + \text{Header}) + \text{margin}$ in `StreamDecoder` and ensure documentation accurately attributes security properties across layers.
>
> 2. **Canonical `ObjectRef` Implementation & SHA-256 Content Validation:**  
>    Build the core `ObjectRef` data handle and enforce SHA-256 content verification on read/transform operations across local filesystem storage.
>
> 3. **Generic `ExternalEffectContract` Framework:**  
>    Formalize the generic adapter contract for side-effect classification, idempotency keys, and `INDETERMINATE` failure barriers.
>
> 4. **Phase 5 Load Balancing & Replica Concurrency Optimization:**  
>    Refine candidate resolver selection policies and replica group scaling loop.

---
