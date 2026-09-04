# Cortex Low-Level Asynchronous Component Communication Topology

> **Document Version**: `1.0.0` | **Target Architecture**: `v0.7.0rc1`  
> **Classification**: Normative Systems Engineering Specification | **Transport Protocol**: CBE Wire Grammar Over Stdio / IPC

---

## 1. Executive Overview

Cortex provides a zero-trust, spatiotemporally governed execution framework for autonomous workflows and microservices. To achieve physical isolation without sacrificing asynchronous execution performance, Cortex decouples the **Control & Governance Plane** from the **Low-Level Plugin Execution Plane** via non-blocking IPC framing and Canonical Binary Encoding (CBE).

$$\boxed{\textbf{Authority Decides}} \quad \Longleftrightarrow \quad \boxed{\textbf{Asynchronous Worker Executes}}$$

---

## 2. Comprehensive System Component Topology (Mermaid Diagram)

```mermaid
sequenceDiagram
    autonumber
    participant App as Application / CortexClient
    participant RA as ResourceAuthority (WAL / Placement)
    participant GW as GatewayAuthorizationGate
    participant Sup as WorkerSupervisor (cgroups v2 / Landlock)
    participant Worker as Isolated Subprocess Worker
    participant Adapt as LocalProcessMCPAdapter / Plugin
    participant Pipeline as EffectExecutionPipeline
    participant CAS as ContentAddressableStore

    Note over App, CAS: Phase 1: Capacity Reservation & HMAC Capability Token Issue
    App->>RA: reserve_capacity(RAM, CPU, PIDs)
    RA-->>App: ReservationGranted(reservation_id, vector_limits)
    App->>GW: authorize_intent(SignedIntent, reservation_id)
    GW-->>App: ExecutionToken(HMAC_signature, capability_mask)

    Note over App, Worker: Phase 2: Process Spawn & Containment Setup
    App->>Sup: spawn_worker(ExecutionToken, manifest)
    Sup->>Sup: os.setsid() + unshare(CLONE_NEWNET) + apply_cgroup_limits()
    Sup->>Worker: exec(worker_binary)

    Note over Worker, Adapt: Phase 3: Asynchronous Stdio / IPC CBE Transport
    Worker->>Adapt: CBE Stream Frame (EffectRequest: op, args) [stdio/socket]
    Note over Adapt: Process tool call & generate output
    
    alt Payload <= 4KiB (Inline Evidence)
        Adapt-->>Worker: CBE Stream Frame (Inline Data, is_reference=False)
    else Payload > 4KiB (Authoritative Spooling)
        Adapt->>CAS: put(result_bytes, owner_id=invocation_id)
        CAS-->>Adapt: ObjectRef("sha256:<hash>")
        Adapt-->>Worker: CBE Stream Frame (Data="sha256:<hash>", is_reference=True)
    end

    Note over Worker, Pipeline: Phase 4: State Reconciliation & Witness Journaling
    Worker->>Pipeline: reconcile_effect(EffectOutcome, ExecutionToken)
    Pipeline->>RA: commit_effect_and_release(reservation_id)
    Pipeline-->>App: EffectConfirmed(evidence, witness_hash)
```

---

## 3. Detailed Component Interaction Architecture

```mermaid
graph TD
    subgraph Control_Plane ["1. Governance & Control Plane"]
        Client["CortexClient"]
        RA["ResourceAuthority<br/>(WAL / Vector Allocation)"]
        GW["GatewayAuthorizationGate<br/>(HMAC Execution Token)"]
    end

    subgraph Process_Containment ["2. Physical Containment Sandbox"]
        Sup["WorkerSupervisor<br/>(os.setsid / killpg)"]
        cgroups["cgroups v2<br/>(RAM/CPU Ceiling)"]
        Landlock["Landlock LSM<br/>(FS Restriction)"]
        NetNS["NetNS<br/>(CLONE_NEWNET Isolation)"]
    end

    subgraph Execution_Subsystem ["3. Low-Level Asynchronous Execution"]
        Worker["Isolated Worker Process"]
        Adapter["LocalProcessMCPAdapter<br/>(Async Stdio / Socket Driver)"]
        Plugin["External Plugin / Subprocess"]
    end

    subgraph Persistence_Authority ["4. Evidence & Result Authority"]
        Pipeline["EffectExecutionPipeline"]
        CAS["ContentAddressableStore<br/>(SHA-256 Object Ref Store)"]
        WAL["Write-Ahead Log<br/>(Tamper-Evident Journal)"]
    end

    Client -->|1. Reserve Capacity| RA
    Client -->|2. Request Token| GW
    Client -->|3. Spawn Worker| Sup
    Sup -->|Attach Limits| cgroups
    Sup -->|Sandbox System Calls| Landlock
    Sup -->|Isolate Network| NetNS
    Sup -->|Execute Subprocess| Worker
    Worker <-->|Asynchronous CBE Framing| Adapter
    Adapter <-->|Stdio / IPC Stream| Plugin
    Adapter -->|Spool > 4KiB Evidence| CAS
    Worker -->|Submit Effect Result| Pipeline
    Pipeline -->|Record Transaction| WAL
    Pipeline -->|Release Reservation| RA
```

---

## 4. Low-Level Asynchronous Communication Mechanics

### A. Framing Protocol & Wire Grammar
Lower-level plugin transport uses **Canonical Binary Encoding (CBE)** framing over non-blocking standard I/O streams (`stdin` / `stdout`) or Unix domain sockets.

$$\text{Frame Layout} = \underbrace{\text{Magic Header (4B)}}_{\texttt{0x43 0x42 0x45 0x31}} \,||\, \underbrace{\text{Frame Length (4B)}}_{\text{Big-Endian uint32}} \,||\, \underbrace{\text{Payload Bytes (Var)}}{CBE(\text{EffectRequest / Outcome})} \,||\, \underbrace{\text{CRC32 (4B)}}_{\text{Checksum}}$$

### B. Asynchronous Non-Blocking Event Loop
1. **Multiplexed I/O**: The `LocalProcessMCPAdapter` uses an asynchronous event loop (`asyncio` reader/writer streams) to pipeline multiple concurrent requests over a single subprocess channel without head-of-line blocking.
2. **Correlation Headers**: Every `EffectRequest` frame carries a unique `request_id: UUID128` and `invocation_id: UUID128`, allowing response frames to be matched asynchronously out-of-order.

### C. Large Evidence Boundary Contract
* **Inline Threshold ($\le 4\text{KiB}$)**: Small results are framed directly inside `EvidencePayload(data=raw_bytes, is_reference=False)` for minimum latency.
* **Content Addressable Storage ($> 4\text{KiB}$)**: Payloads exceeding $4096\text{ bytes}$ are spooled directly into `ContentAddressableStore` using `sha256:<hash>` keying scoped by `owner_id=ctx.invocation_id`. The returned frame contains only `EvidencePayload(data="sha256:<hash>", is_reference=True)`.

---

## 5. Synchronous vs. Asynchronous Communication Matrix

Cortex explicitly segregates **Synchronous Governance** from **Asynchronous Execution**:

| Component Boundary | Sync / Async Mode | Rationale & Mechanism |
| :--- | :---: | :--- |
| **Admission & Reservation** (`ResourceAuthority`) | **SYNCHRONOUS** | Pre-execution safety cannot be eventual. Vector limits (RAM/CPU) are locked synchronously in `WAL` before process spawn. |
| **Capability Authorization** (`GatewayAuthorizationGate`) | **SYNCHRONOUS** | HMAC execution tokens must be verified and signed synchronously to ensure fail-closed security. |
| **Worker Subprocess Execution** (`WorkerSupervisor`) | **ASYNCHRONOUS** | Processes are spawned asynchronously; stdin/stdout pipes are managed via non-blocking `asyncio` event loops. |
| **Plugin IPC Transport** (`LocalProcessMCPAdapter`) | **ASYNCHRONOUS** | CBE stream frames use correlation IDs (`request_id`, `invocation_id`) to multiplex multiple tool calls without blocking. |
| **Evidence CAS Spooling** (`ContentAddressableStore`) | **ASYNCHRONOUS** | Payload writes $> 4\text{KiB}$ occur asynchronously to prevent thread blocking during I/O persistence. |
| **Effect Reconciliation & Journaling** (`EffectExecutionPipeline`) | **ASYNCHRONOUS** | Outcome state changes and witness chain updates are committed asynchronously upon stream completion. |

---

## 6. Real-Time Machine Learning & Computer Vision Streaming Architecture

High-throughput, low-latency workloads (e.g. 60 FPS 1080p/4K video streams, PyTorch/TensorRT inference, GPU tensor buffers) are handled efficiently in Cortex via a **Decoupled Data-Plane & Zero-Copy Reference Architecture**:

```
                       REAL-TIME COMPUTER VISION STREAMING TOPOLOGY

[ Video Camera / RTSP Stream ]
              │ (Raw Video Frames)
              ▼
[ Worker Process (ONNX / TensorRT) ] ─── Shared Memory IPC (shm / FD) ───► [ ContentAddressableStore ]
              │                                                              (Zero-Copy Frame Buffer)
              │ (CBE Metadata Stream: bounding_box, confidence, class_id)
              ▼
[ LocalProcessMCPAdapter ] ─── Async Non-Blocking Pipe ───► [ Cortex Control Plane ]
```

### Key Engineering Invariants for Real-Time ML:
1. **GPU Vector Capacity Reservation (`ResourceAuthority`)**:
   Before spawning ML workers, `ResourceAuthority` synchronously reserves GPU VRAM (`vram_mib`) and compute units (`gpu_count`). This guarantees that concurrent vision models (e.g. YOLOv8, Segment Anything) do not trigger CUDA Out-Of-Memory (OOM) driver crashes.
2. **Zero-Copy Frame Offloading**:
   Raw image/tensor buffers exceed the $4\text{KiB}$ inline evidence ceiling. Workers write frame buffers directly to shared memory (`/dev/shm` or Unix file descriptors) or CAS, returning lightweight `ObjectRef("sha256:<hash>")` references over the CBE stream pipe.
3. **Asynchronous Metadata Pipelining**:
   Detection boxes, tracking vectors, and inference classification results are serialized into lightweight CBE metadata frames and pushed asynchronously without blocking frame capture loops.
4. **Fault-Isolated Subprocess Boundaries**:
   Heavy native C++/CUDA dependencies (PyTorch, TensorRT, OpenCV) execute inside sandboxed subprocesses created by `WorkerSupervisor`. A C++ segfault or CUDA error terminates only the isolated worker process group (`os.killpg`), leaving the host control plane fully operational.

---

## 7. Reliability & Process Group Fencing Invariants

1. **Process Group Teardown**: `WorkerSupervisor` calls `os.setsid()` during subprocess creation to establish a distinct process group. On termination or timeout, `os.killpg(proc.pid, SIGTERM/SIGKILL)` is executed to guarantee zero orphan process accumulation.
2. **Bounded Allocation Defense**: Go and Python CBE decoders enforce pre-allocation ceilings ($\min(\text{declared\_count}, 1024)$) to prevent OOM denial-of-service attacks from untrusted framing streams.
3. **Fence-Out Stale Incarnations**: The `EffectExecutionPipeline` rejects duplicate or delayed response frames from dead worker incarnations by verifying monotonic epoch counters against `ResourceAuthority`.
