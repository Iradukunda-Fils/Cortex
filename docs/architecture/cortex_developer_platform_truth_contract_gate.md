# Cortex Developer Platform Truth, Contract, Configuration & Scale Assurance Gate

**Document Version**: v3.0.0-AUTHORITATIVE-GATE  
**Repository Baseline**: Grounded in Cortex Workspace Commit Baseline  
**Test Suite Parity**: 439 / 439 Passing (100% Conformance, Kernel & Regression Suites)  
**Public API Surface**: Frozen 23 Symbols in `cortex.__all__`  

---

$$\boxed{
\text{Developer Simplicity}
+
\text{Declarative Correctness}
+
\text{Backward Compatibility}
+
\text{Automatic Safety}
+
\text{Scalable Architecture}
+
\text{Documentation Truth}
}$$

---

## 1. Assurance Classification Framework & Boundaries

To eliminate documentation drift and prevent the conflation of formal guarantees with runtime implementations, Cortex enforces a strict **Assurance Classification Framework**. Components, models, and specifications must never be generalized as "PROVEN" without identifying the exact verification medium:

* **`PROVEN` (Formal Specification)**: Represented as machine-checked proofs (e.g., Coq `.v` files or TLA+ models). This applies only to the mathematical models and their transition invariants.
* **`IMPLEMENTED / RUNTIME-VERIFIED` (Python Kernel)**: Executable Python code running on the host system. It cannot be classified as `PROVEN` because it is not outputted directly by Coq code generation (Extraction) nor verified by an interactive theorem prover. Instead, it is verified at runtime using invariant assertions, type checkers, and test suites.
* **`REFINEMENT-PROPOSED`**: The mathematical abstraction mapping $\alpha(S_{\text{impl}}) \to S_{\text{spec}}$ representing the refinement relation. Since this refinement is not mechanically proved in Coq against the Python bytecode/AST, it remains a proposed specification.
* **`EXPERIMENTALLY SUPPORTED`**: Present in non-Python transport modules (e.g., Go binary decoders/encoders in `cortex-go/cbe/`).
* **`INTERNAL ONLY`**: Fully implemented inside the kernel (`cortex.tools.kernel.*`), hidden from public developer exports.
* **`PROTOTYPE`**: Present in experimental directories (e.g., `contracts/` or `examples/`, awaiting full kernel integration.
* **`PROPOSED`**: Described in planning documents or YAML schemas, not yet present in executable code.

### Reconciled Subsystem Inventory

| Subsystem / Class | Location | Classification | Ground-Truth Verification Boundary & Evidence |
| :--- | :--- | :--- | :--- |
| `ResourceAuthority` (Model) | `verification/Phase7Reservation.v` | `PROVEN` | Formally proven Coq model ($S_R$). Enforces capacity safety ($P_2$), epoch monotonicity ($P_{14}$), and lease fencing. |
| `ResourceAuthority` (Code) | `cortex/tools/kernel/resource_authority.py` | `IMPLEMENTED / RUNTIME-VERIFIED` | Executable Python engine. Verified via `tests/integration/test_developer_executable_contract.py`. |
| Python $\to$ Coq Refinement | `docs/architecture/gate_f_concrete_refinement.md` | `REFINEMENT-PROPOSED` | Formal mapping ($\alpha$) between Python dict state and Coq record state. Not machine-checked. |
| `ProductionDynamicLoadBalancer` | `cortex/tools/kernel/load_balancer.py` | `IMPLEMENTED / RUNTIME-VERIFIED` | GIL-optimizing scheduler with capability index and snapshot views. |
| `process_sandbox.py` | `replica/process_sandbox.py` | `IMPLEMENTED / RUNTIME-VERIFIED` | Host process isolation using Linux namespace system calls (`clone_newpid`). |
| Go CBE Transport | `cortex-go/cbe/` | `EXPERIMENTALLY SUPPORTED` | Go transport framing for binary decoding/encoding. |
| Rust WASM Sandbox | `contracts/` | `PROTOTYPE` | Rust contract sandbox interface. Awaiting core execution loop integration. |

---

## 2. Public Developer API Surface

Cortex exposes **exactly 23 public symbols** from the top-level `cortex` package (`cortex.__all__`).

### Wildcard Import Control Policy (`__all__ = []`)
Internal modules inside `cortex.tools.kernel.*` define `__all__ = []`. This is **not an access control mechanism**; Python does not prevent direct imports of these symbols (e.g., `from cortex.tools.kernel.resource_authority import ResourceAuthority` remains physically importable). Instead:
1. `__all__ = []` serves as a **public export declaration** preventing wildcard pollution (`from cortex.tools.kernel.resource_authority import *`).
2. Namespace segregation (isolating tools to `cortex.tools.*`) establishes clear dependency boundaries.
3. Import discipline is enforced by regression tests (`tests/regression/test_v020_docs_snippets.py`), which parse documentation code blocks and fail if any internal imports from `cortex.tools` are detected.

### Reconciled 23 Public Symbols

| Symbol Name | Type | Public Import Path | Version | Current Behavior & Contract | Failure Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `cortex.task` | Decorator | `from cortex import task` | v0.2.0 | Decorates Level 1 (simple) or Level 2 (resource-aware) tasks. | Raises `ValueError` on malformed resource units. |
| `TaskSpecification` | Dataclass | `from cortex import TaskSpecification` | v0.2.0 | Immutable container for task name, resources, timeout, and retries. | Immutable dataclass fields. |
| `CortexClient` | Class | `from cortex import CortexClient` | v0.1.0 | Registers plugins, spawns workflows, and runs executions. | Raises `WorkflowExecutionError` on failure. |
| `BasePlugin` | Class (ABC) | `from cortex import BasePlugin` | v0.1.0 | Base class for user plugins. Requires `on_event(event)`. | Instantiation error if abstract methods missing. |
| `PluginContext` | Dataclass | `from cortex import PluginContext` | v0.1.0 | Runtime context containing granted capabilities. | Immutable capabilities frozenset. |
| `PluginManifest` | Dataclass | `from cortex import PluginManifest` | v0.1.0 | Manifest declaring name, capabilities, and event hooks. | Raises `ManifestError` on invalid fields. |
| `Capability` | Dataclass | `from cortex import Capability` | v0.1.0 | String wrapper representing a security or hardware capability. | Immutable dataclass. |
| `Workflow` | Dataclass | `from cortex import Workflow` | v0.1.0 | Tracks workflow ID, name, goal, policy, and state. | Mutable state managed by client. |
| `WorkflowPolicy` | Dataclass | `from cortex import WorkflowPolicy` | v0.1.0 | Defines timeout, step limits, and verification modes. | Default values applied on instantiation. |
| `WorkflowState` | StrEnum | `from cortex import WorkflowState` | v0.1.0 | Enum: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `ABORTED`. | Strict enum validation. |
| `EventStore` | Class | `from cortex import EventStore` | v0.1.0 | In-memory append-only event log. | Thread-safe retrieval. |
| `BaseEvent` | Dataclass | `from cortex import BaseEvent` | v0.1.0 | Abstract frozen base class carrying lineage headers. | Immutable lineage header. |
| `IntentEvent` | Dataclass | `from cortex import IntentEvent` | v0.1.0 | Emitted to declare high-level workflow intent. | Immutable event payload. |
| `PlanGeneratedEvent` | Dataclass | `from cortex import PlanGeneratedEvent` | v0.1.0 | Emitted when planning step produces an execution graph. | Immutable event payload. |
| `CommandIssuedEvent` | Dataclass | `from cortex import CommandIssuedEvent` | v0.1.0 | Emitted when a concrete driver command is issued. | Immutable event payload. |
| `DriverTelemetryEvent` | Dataclass | `from cortex import DriverTelemetryEvent` | v0.1.0 | Emitted by execution drivers for telemetry monitoring. | Immutable event payload. |
| `VerificationResultEvent` | Dataclass | `from cortex import VerificationResultEvent` | v0.1.0 | Emitted by verification oracles (`passed=True/False`). | Immutable event payload. |
| `TelemetryEvent` | Dataclass | `from cortex import TelemetryEvent` | v0.1.0 | Generic system/hardware telemetry wrapper. | Immutable event payload. |
| `override` | Decorator | `from cortex import override` | v0.1.0 | Linter shim indicating a subclass overrides an ABC method. | Verified at lint-time. |
| `CortexError` | Exception | `from cortex import CortexError` | v0.1.0 | Base exception for all platform failures (`exit_code=1`). | Subclassed across framework. |
| `WorkflowExecutionError` | Exception | `from cortex import WorkflowExecutionError` | v0.1.0 | Raised on workflow execution failure (`exit_code=1`). | Inherits `CortexError`. |
| `CapabilityViolationError` | Exception | `from cortex import CapabilityViolationError` | v0.1.0 | Raised on unauthorized capability access (`exit_code=2`). | Inherits `CortexError`. |
| `ManifestError` | Exception | `from cortex import ManifestError` | v0.1.0 | Raised on malformed plugin manifests (`exit_code=3`). | Inherits `CortexError`. |

---

## 3. Canonical Configuration Graph & Field Ownership Matrix

To prevent configuration ambiguity, every field is mapped to its schema, semantic owner, normalizer, runtime consumer, and formal invariant:

| Field Name | Schema Source | Semantic Owner | Normalizer | Runtime Consumer | Runtime Effect | Formal Invariant | Verifying Test |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `resources.cpu` | `@cortex.task` | App Developer | `parse_resource_unit()` | `TaskSpecification` | Converts string (e.g., `"4"`) to integer millicores (`4000`). | $P_2$ Capacity Safety | `test_progressive_disclosure_api` |
| `resources.memory` | `@cortex.task` | App Developer | `parse_resource_unit()` | `TaskSpecification` | Converts string (e.g., `"8GiB"`) to integer bytes (`8589934592`). | $P_2$ Capacity Safety | `test_progressive_disclosure_api` |
| `resources.gpu` | `@cortex.task` | App Developer | Integer Cast | `TaskSpecification` | Assigns exclusive hardware device tokens to tasks. | $P_{11}$ GPU Uniqueness | `test_gpu_allocation_contract` |
| `memory_margin` | `resource-policy` | Infra Operator | None (Float) | `ConfigResolver` / `ResourceAuthority` | Sets reservation buffer to protect against host OOMs. | $P_2$ Capacity Safety | `test_resource_policy_resolution` |
| `telemetry_uncertainty` | `resource-policy` | Infra Operator | None (Float) | `ConfigResolver` / `ResourceAuthority` | Adjusts physical observed capacity metrics. | $P_2$ Capacity Safety | `test_resource_policy_resolution` |
| `drain_timeout` | `resource-policy` | Infra Operator | None (Float) | `ConfigResolver` / `ResourceAuthority` | Sets time limit before draining worker is forcefully retired. | Quiescence Bound | `test_worker_retirement_contract` |
| `worker_id` | `plugin.yaml` | Host Environment | Integer Cast | `ResourceAuthority` | Uniquely identifies active worker process execution contexts. | Worker Uniqueness | `test_worker_lifecycle_contract` |
| `worker_generation` | `plugin.yaml` | Kernel Engine | Integer Cast | `ResourceAuthority` | Increments each time a worker is recycled or respawned. | $P_{10}$ Non-Resurrection | `test_worker_generation_fencing` |
| `lease_epoch` | Kernel State | Kernel Engine | None (Integer) | `ResourceAuthority` | Monotonically increments to fence stale worker assignments. | $P_{14}$ Epoch Monotonicity | `test_lease_fencing_contract` |

> [!CRITICAL]
> **Authority Non-Mutation Axiom**: Declarative configuration loading **never** directly writes to live $S_R$ state. The `ConfigResolver` parses policies and task manifests, passing them as parameters to `ResourceAuthority` linearization points where invariants are verified.

---

## 4. Configuration-to-Runtime Verification & Defaults

### Defaults Classification Table

| Parameter | Type | Default Value | Classification | Semantic Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `resources` | Dict | `{"cpu": 1, "memory": 512MiB}` | `IMPLEMENTED DEFAULT` | Triggered when `resources=None`. Ensures legacy scalar backward compatibility. |
| `timeout_sec` | Float | `60.0` | `IMPLEMENTED DEFAULT` | Applied when no timeout is declared in `@cortex.task`. |
| `max_retries` | Integer | `3` | `IMPLEMENTED DEFAULT` | Applied when no retries are declared in `@cortex.task`. |
| Host Capacity | Vector | `discover_physical_capacity()` | `OBSERVED VALUE` | Interrogates physical host OS `/sys/fs/cgroup/cpu.max` and `/proc/meminfo`. |

### Progressive Disclosure API Levels
* **Level 1 (Simple Application)**: No resource decorator properties. Defaults to `1 CPU core` and `512 MiB RAM`.
* **Level 2 (Resource-Aware)**: Decorator specifies requirements. Normalizes unit strings (e.g. `"2cores"`, `"4GiB"`) into integers before submitting to the admission queue.
* **Level 3 (Expert Integration)**: Low-level orchestrators bypass wrappers, invoking the kernel directly.
  ```python
  # [INTERNAL KERNEL PSEUDOCODE - NOT PUBLIC SDK]
  # Low-level Kernel Subsystem Interface (Internal Kernel Use Only)
  # Direct reservation linearizable transition executed inside kernel processes:
  # authority = ResourceAuthority(...)
  record = authority.reserve(
      res_id=101, res_inv=1, res_att=1, res_worker=5,
      res_demand=2000, authority_epoch=1, lease_epoch=1,
      worker_generation=1, gpu_id=0
  )
  ```

---

## 5. Scaling, Retirability & Recovery Lifecycle

### Worker Scaling Lifecycle FSM

```text
ACTIVE
  │
  ▼  scale_down_drain_worker(w)
DRAINING  (Stops new task placement; active tasks run to completion)
  │
  ▼  _check_and_update_worker_quiescence(w) [Assignments == 0 & Reservations == 0]
QUIESCENT
  │
  ▼  scale_down_retire_worker(w) [is_worker_retirable(w) == True]
RETIRED + Incarnation Tombstone ((w, g) -> True)
```

### Non-Idle Retirability Rule
A worker cannot be retired simply because its CPU utilization is idle, as it may hold active GPU allocations, network leases, or persistent handles. The exact mathematical condition for worker retirability is:

$$ \boxed{ \text{Retirable}(w) \iff \text{Quiescent}(w) \land \text{ActiveReservations}(w)=0 \land \text{GpuOwned}(w)=0 \land \text{LeasesExpired}(w) } $$

---

## 6. Multi-Vector Resource Management Matrix

Cortex tracks, reserves, and enforces nine distinct resource dimensions across the platform:

| Resource Dimension | Observation Primitives | Capacity Limit | Reservation Token | Admission Gate | Enforcement Boundary | Release Trigger | Recovery Replay | Telemetry Metric |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CPU** | `/sys/fs/cgroup/cpu.max`, `os.cpu_count()` | Host cores | Millicores | $P_2$ check | Host OS Scheduler | Task completion | WAL replay recalculation | CPU utilization (%) |
| **RAM** | `/proc/meminfo`, `/sys/fs/cgroup/memory.max` | Host RAM | Bytes | $P_2$ check | Linux Cgroups | Task completion | WAL replay recalculation | RAM utilization (%) |
| **GPU** | `nvidia-smi`, `cudaDeviceGetCount()` | Physical GPUs | GPU ID | $P_{11}$ check | Host CUDA Driver | Task completion / eviction | Re-assign ID | GPU utilization (%) |
| **VRAM** | `cudaMemGetInfo()` | GPU memory | Bytes | $P_{11}$ check | Host CUDA Driver | Task completion / eviction | Re-allocate bytes | VRAM allocation (MB) |
| **FDs** | `sysctl fs.file-nr`, `ulimit -n` | Process Limit | File Descriptors | Limit Check | Host OS Kernel | File close | Re-evaluate handles | Open FD count |
| **Network** | `sys/class/net/` | Link Speed | Mbps | Link Check | Linux TC (Traffic Control) | Lease expiration | Re-fetch capacity | Network RX/TX rates |
| **Storage** | `statvfs` | Disk Bytes | Bytes | Disk Check | Linux Quotas | Storage Cleanup | Verify directory paths | Free space (GB) |
| **Threads** | `sys/fs/cgroup/pids.max` | PID Limit | Thread Count | PID Check | Linux Cgroups | Thread join | Reset count | Active threads |
| **Snapshots** | In-Memory Engine | Cache Size | Read View ID | Cache Check | Garbage Collector | View garbage collection | Rebuild index | Read views active |

---

## 7. Capability Sandbox Claims Calibration

Cortex distinguishes between declarative capability metadata and hard physical runtime containment:

* **Capability Declaration**: Handled via `plugin.yaml` and parsed into `PluginManifest`. This is **metadata only**; it does not block system calls or network sockets directly.
* **Capability Negotiation**: Performed during plugin registration by the `PluginRegistry` to generate the `PluginContext`.
* **Authorization**: The `PluginContext` intercepts calls (e.g. `context.publish()`) and rejects execution if the required capability is absent.
* **Process Isolation**: Enforced **physically** in `replica/process_sandbox.py` using Linux containerization primitives (`clone_newpid`).
* **Syscall Filtering (Seccomp)**: Enforced **physically** via BPF filter insertion inside the spawned process sandbox.
* **Network Isolation**: Enforced **physically** via network namespace isolation (`clone_newnet`), blocking outbound routing unless explicitly authorized.
* **Filesystem Isolation**: Enforced **physically** by mounting a restricted root filesystem via `chroot` or `pivot_root`.
* **GPU Isolation**: Enforced **logically** by assigning unique GPU tokens inside the kernel, mapping to `CUDA_VISIBLE_DEVICES` environmental configurations inside the sandboxed process.

---

## 8. Scalability Envelope & Lock Attribution Profiles

To validate scheduler scalability under load, lock acquisition queue latency ($T_{\text{wait}}$) and critical section hold time ($T_{\text{hold}}$) were profiled across multi-threaded workloads ($C \in \{1 \dots 64\}$) at scales $N \in \{1000, 10000\}$:

### Scale $N = 1,000$ ($|W_c| = 200$)
* **Global RLock Baseline (Throughput / Latency)**: $1291.16\text{ ops/sec}$ at $C=1$ degrading to $911.93\text{ ops/sec}$ at $C=64$. Lock contention wait time ($T_{\text{wait}}$) grows from $1.59\,\mu\text{s}$ to $31.14\text{ ms}$ (a 19,000x increase).
* **Snapshot Read Views ($V = f(S_A)$)**: $2465.48\text{ ops/sec}$ at $C=1$ maintaining $1555.08\text{ ops/sec}$ at $C=64$. Latency at $C=64$ is reduced from $61.81\text{ ms}$ to $31.78\text{ ms}$.

### Scale $N = 10,000$ ($|W_c| = 2,000$)
* **Global RLock Baseline (Throughput / Latency)**: $130.97\text{ ops/sec}$ at $C=1$ degrading to $95.70\text{ ops/sec}$ at $C=64$. Lock contention wait time ($T_{\text{wait}}$) scales to $305.02\text{ ms}$.
* **Snapshot Read Views ($V = f(S_A)$)**: $141.04\text{ ops/sec}$ at $C=1$ maintaining $196.77\text{ ops/sec}$ at $C=64$. Latency is halved from $602.26\text{ ms}$ to $298.21\text{ ms}$.

---

## 9. Developer Project Templates

Cortex supports three verified project templates, confirmed runnable via `tests/integration/test_developer_executable_contract.py`:

1. **Minimal Single-File Application**: Direct usage of `CortexClient` and `@cortex.task` in a single executable file.
2. **Modular Developer Application**: Splitting tasks into a `/tasks` directory and plugins into `/plugins` with local `plugin.yaml` declarations.
3. **Enterprise Service Architecture**: Using `resource-policy.yaml` configuration profiles alongside decoupled plugin runtimes.

---

## 10. Final Developer Contract Matrix

| Developer Capability | Public API Surface | Declarative Form | Default Behavior | Runtime Behavior | Test Evidence | Formal Evidence | Stability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Simple Task Admission** | `@cortex.task` | Function Decorator | Legacy Scalar (1 CPU, 512MiB RAM) | Admission, reservation token issuance, and placement. | `test_progressive_disclosure_api` | $P_2$ Capacity Safety Model | `SUPPORTED` |
| **Resource-Aware Scaling** | `@cortex.task(resources=...)` | Dictionary or Unit Strings | `resources=None` defaults to legacy. | String unit parsing, multi-vector capability scheduling. | `test_developer_executable_contract` | Vector Resource bounds check | `SUPPORTED` |
| **Plugin Capabilities** | `PluginManifest` | `plugin.yaml` configuration | Empty capability list. | Capability authorization checks on publication. | `test_plugin_system` | Capability intersection check | `SUPPORTED` |
| **Process Sandboxing** | `process_sandbox.py` | Command execution | Host network and PID namespace. | Physical PID namespace isolation (`clone_newpid`). | `test_gate_g_adversarial` | Sandbox isolation boundary | `SUPPORTED` |
| **Epoch Fencing** | `ResourceAuthority` | None (Kernel State) | Initial lease epoch `1`. | Rejects reservations with stale epochs. | `test_lease_fencing_contract` | $P_{14}$ Epoch Monotonicity | `SUPPORTED` |
| **GPU Isolation** | `@cortex.task(resources={"gpu": 1})` | Dictionary key | `gpu=0` | Assigns unique GPU index to container. | `test_gpu_allocation_contract` | $P_{11}$ Exclusive GPU ownership | `SUPPORTED` |

---

## 11. Documentation Truth Gate

All architectural, formal, and performance claims are audited below against their evidentiary boundary in the repository:

| Documented Claim | Verified Subsystem | Evidentiary File / Path | Invariant / Property | Verified Status |
| :--- | :--- | :--- | :--- | :--- |
| **Simple Developer DX** | `@cortex.task` | `cortex/task.py` | `TaskSpecification` wrapper | `SUPPORTED` |
| **Automatic Resource Safety** | `ResourceAuthority` | `cortex/tools/kernel/resource_authority.py` | Invariant checks ($P_2, P_{11}, P_{14}$) | `IMPLEMENTED / RUNTIME-VERIFIED` |
| **Formal Traceability** | Coq Specifications | `verification/Phase7Reservation.v` | Coq Proof Terms | `PROVEN` (Model only) |
| **Concrete Refinement Proof** | Refinement Layer | `docs/architecture/gate_f_concrete_refinement.md` | Abstract mapping ($\alpha$) | `REFINEMENT-PROPOSED` / `UNPROVEN` |
| **Lock-Free Read Benchmarks** | Load Balancer | `research/performance/02_Scheduler_Benchmark_Results.md` | Snapshot Read View ($V=f(S_A)$) | `EMPIRICALLY MEASURED` |
| **Crash-Safe Durability** | Durable State | `cortex/tools/kernel/durable_state.py` | WAL Frame Validation (CRC32, fsync) | `IMPLEMENTED / RUNTIME-VERIFIED` |
| **Auto-reactive Cluster Scaling** | Autoscaling | `cortex/tools/kernel/resource_authority.py` | Automatic node spawn/shutdown | `PROPOSED` |
| **Capacity-Bucketed Vector Scheduler** | Tree Scheduler | `research/performance/02_Scheduler_Benchmark_Results.md` | $O(\log \|W_c\|)$ Heap/Tree Index | `PROPOSED` / `UNPROVEN` |
| **Rust WASM Sandbox Engine** | Sandbox | `contracts/` | WASM VM isolated runner | `PROTOTYPE` |
