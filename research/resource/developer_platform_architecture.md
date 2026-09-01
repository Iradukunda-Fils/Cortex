# Cortex Developer Platform Executable-Truth Architecture & Contract Matrix

**Classification**: RESEARCH & SPECIFICATION AUDIT  
**Normative Status**: ACTIVE DEVELOPER-PLATFORM BASELINE  
**Core Directive**:

$$\boxed{ \text{Implemented} \neq \text{Documented} \neq \text{Tested} \neq \text{Formally Proven} \neq \text{Production Supported} }$$

---

## 1. Authoritative Test Count & Verification Reconciliation

To reconcile previous variations (412, 436, 439, 444), the exact workspace-wide test suite command was executed against the repository:

- **Verification Command**: `uv run python3 -m unittest discover -s tests`
- **Execution Timestamp**: 2026-08-28T10:35:11Z
- **Total Test Cases Executed**: **437 Tests**
- **Failed Cases**: **0**
- **Skipped Cases**: **0**
- **Execution Status**: `OK (Exit code: 0)`

### Suite Distribution Breakdown

| Subsystem / Test Path | Test Count | Description / Coverage Scope |
| :--- | :--- | :--- |
| `tests/kernel` | **79** | Phase 7 Resource Authority, Progressive Disclosure API, FSM transitions |
| `tests/unit` | **180** | Core kernel actors, graph resolution, event store, schema resolution |
| `tests/integration` | **150** | Multi-replica worker gateway, seccomp sandbox, CLI workflow replay |
| `tests/regression` | **28** | Public API boundary freeze (`cortex.__all__`), docs snippet imports |
| **Workspace Total** | **437** | **100% Passing Workspace Suite** |

*Historical Discrepancy Reconciliation*: Earlier test runner invocations targeted specific sub-directories (e.g., `tests/kernel` alone = 79, `tests/unit` + `tests/integration` = 330, `tests/regression` = 28) or executed prior to Phase 7.3 task API addition. The single authoritative count for the repository is **437 tests**.

### Formal Verification Machine-Checked Audit
- **Profile**: `python3 verification/verify_controller.py verify-coq`
- **Result**: `PASSED`
- **Axioms**: **0**
- **Admits**: **0**

---

## 2. Boundary of Engineering & Formal Invariant Claims

We enforce the distinction between **Model-Bounded Formal Verification** and **Universal Physical Guarantees**:

$$\boxed{ \text{All modeled state transitions satisfy specified formal invariants } P_1 \text{ through } P_{14} }$$

- **Modeled Formal Guarantees**: Under the formal state machine model (`Phase7Reservation.v`), the kernel proves invariant preservation for invocation uniqueness ($P_{1a}$), attempt uniqueness ($P_{1b}$), capacity safety ($P_2$), worker fencing ($P_7$), terminal reclamation ($P_{13}$), and epoch advancement ($P_{14}$).
- **Unmodeled Physical Boundary**: Cortex does **not** claim protection against unmodeled physical host failures (kernel panics, physical hardware corruption, uncooperative OS process killing, or hypervisor resets).

---

## 3. Python Encapsulation Mechanics

In Python, language primitives do not enforce hard memory access protection. Therefore:

$$\boxed{ \text{Public Cortex APIs expose authoritative mutation operations only through controlled kernel interfaces} }$$

- **Enforcement Mechanisms**:
  1. State structures use private naming conventions (`_reservations`, `_retired_tombstones`, `_gpu_owners`).
  2. Public properties return read-only views (`@property def rs_reservations(self)`).
  3. State transitions occur exclusively through reentrant lock-guarded atomic methods (`ResourceAuthority.reserve()`, `release()`, `revoke()`) under `threading.RLock`.

---

## 4. Public Export Boundary (`__all__`)

$$\boxed{ \texttt{\_\_all\_\_} = \text{public export declaration} }$$

`cortex.__all__` contains exactly **23 public symbols** (`BaseEvent`, `BasePlugin`, `CortexClient`, `task`, `TaskSpecification`, etc.). It serves as an explicit export contract for wildcard imports. Internal package boundaries (`cortex.tools.*`) are enforced by:
- Packaging structure (`__all__ = []` in internal subpackages).
- Automated documentation snippet import linters (`test_v020_docs_snippets.py`).
- Static type checking (`Pyrefly` / `basedpyright`).

---

## 5. Logical GPU Ownership vs. Physical GPU Isolation

$$\boxed{ \text{Logical GPU Ownership } (P_{11}) } \quad \neq \quad \boxed{ \text{Physical GPU Isolation} }$$

- **Logical GPU Ownership ($P_{11}$)**: **SUPPORTED & RUNTIME ENFORCED** in `ResourceAuthority._gpu_owners`. Ensures that no two active reservations can hold logical claim over the same GPU device ID within kernel accounting.
- **Physical GPU Isolation**: **PROPOSED / PHASE 7.4**. Physical process isolation (NVIDIA MIG, CUDA MPS, cgroups v2 `devices.allow`) is governed by the host OS runtime and driver layer, scheduled for Phase 7.4.

---

## 6. Capability Sandbox Assurance & Manifest Distinction

### Plugin vs. Manifest: Structural & Architectural Distinction

$$\boxed{ \text{Plugin (Runtime Instance)} \quad \neq \quad \text{Manifest (Declarative Contract \& Security Policy)} }$$

| Dimension | **Manifest** (`manifest.yml` / `manifest.json`) | **Plugin** (`c_fast_math`, `PluginRegistration`) |
| :--- | :--- | :--- |
| **Nature** | Static declarative YAML/JSON configuration file | Live executable binary/code & sandboxed runtime actor |
| **Lifecycle Stage** | Parse time & capability negotiation | Execution time (in-memory process / IPC handle) |
| **Contents** | Metadata (`name`, `version`), required/forbidden capabilities, security boundaries | Compiled C/C++/Rust shared libraries, Python `@cortex.task` functions |
| **Role in Safety** | Evaluated by `CapabilityNegotiator` prior to execution | Executing code strictly isolated by granted handles |
| **Standard File** | `manifest.yml` (Plugin level) / `cortex.yaml` (App level) | `plugins/<plugin_name>/` directory structure |

---

| Capability / Resource | Declaration Form | Runtime Authorization | OS Enforcement | Status Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Network Outbound** | `manifest.yml` (`network.outbound`) | `CapabilitySandbox.validate()` | Intercepted via Gateway IPC | **RUNTIME ENFORCED** |
| **FileSystem Write** | `manifest.yml` (`storage.write`) | Path confinement check | Process directory restriction | **RUNTIME ENFORCED** |
| **GPU Compute** | `manifest.yml` (`gpu.compute`) | Logical device assignment ($P_{11}$) | Driver permissions (Phase 7.4) | **LOGICAL ENFORCED / PHYSICAL PROPOSED** |
| **Syscall Filtering** | `manifest.yml` (`system.exec`) | Sandbox Capability Manifest | Linux `seccomp` profile | **PARTIALLY ENFORCED** |

---

## 7. Task Invocation & Workflow Semantics

When `@cortex.task` is called:

```python
raw_doc = fetch_document(doc_id)
analysis = extract_entities(raw_doc)
```

1. **Level 1 / Level 2 Task Execution**: Synchronous local function composition within the caller's process context. It evaluates resource specifications, normalizes units, logs execution under the local authority, and returns results.
2. **Level 3 Distributed Workflow Execution**: Multi-node, distributed execution across isolated worker nodes uses `CortexClient.run_workflow()` and `ProductionDynamicLoadBalancer.assign_execution()`, generating explicit `InvocationID`, `AttemptID`, and WAL entries.

---

## 8. Autoscaling Classification

- **Worker Lifecycle State Machine**: **SUPPORTED & VERIFIED** (`REGISTERING` $\to$ `ACTIVE` $\to$ `DRAINING` $\to$ `QUIESCENT` $\to$ `FENCED` $\to$ `RETIRED`).
- **Autoscaling Policy Controller**: **PROPOSED / EXPERIMENTAL**. The underlying state machine supports draining and retirement, while background automated scaling metrics loops remain experimental.

---

## 9. Executable Application Templates & Polyglot Integration

Cortex supports multi-language native plugins (Python, C, C++, and Rust) to combine developer productivity with low-level systems performance:

- **Executable Template 1**: `examples/minimal_app/` (Python default application).
- **Executable Template 2**: `examples/polyglot_compute_app/` (C, C++, Rust, Python native integration).

### Why Polyglot Native Plugins in Cortex?

| Language | Plugin Example | Core Benefit | Cortex Sandbox Role |
| :--- | :--- | :--- | :--- |
| **Python** | `tasks.py` | Rapid application development, Level 1/2 API | Intent declaration & task composition |
| **C** | `c_fast_math` | Sub-microsecond latency, zero GC pauses, direct L1/L2 cache locality | Low-latency math execution |
| **C++** | `cpp_tensor_engine` | AVX-512 SIMD vectorization, C++20 template metaprogramming | Vectorized tensor & risk processing |
| **Rust** | `rust_secure_checksum` | Compile-time memory safety (zero buffer overflows / use-after-free) | Memory-safe token hash & verification |

---

## 10. Developer Contract Matrix

| Feature Name | Public API Surface | Declarative Form | Verified Default | Runtime Behavior | Test Evidence | Formal Model | Support Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Level 1 Task** | `@cortex.task` | None | Default CPU/RAM | Auto-governed execution | `test_progressive_disclosure_api.py` | Phase 7 FSM | **SUPPORTED** |
| **Level 2 Task** | `@cortex.task(resources=...)` | `resources={"cpu": "4", ...}` | User declared | String unit normalization | `test_progressive_disclosure_api.py` | $P_2$ Capacity Safety | **SUPPORTED** |
| **Unit Normalization** | `parse_resource_unit()` | `"4GiB"`, `"2500m"`, `"16cores"` | SI base unit | Millicore / byte integer mapping | `test_progressive_disclosure_api.py` | Spec Note 21 | **SUPPORTED** |
| **Hardware Discovery** | `ResourceAuthority()` | `cortex.yaml` | Hardware discovery | Interrogates cgroups / `/proc/meminfo` | `test_progressive_disclosure_api.py` | Hardware baseline | **SUPPORTED** |
| **Exclusive GPU** | `resources={"gpu": 1}` | `gpu: 1` | Device ID allocation | Rejects duplicate device claim | `test_phase7_resource_authority.py` | $P_{11}$ GPU Ownership | **RUNTIME ENFORCED** |
| **Capability Sandbox** | `CortexClient.register_plugin()` | `plugin.yaml` | Explicit manifest | Rejects unlisted capabilities | `test_capability_sandbox.py` | Capability Security | **RUNTIME ENFORCED** |
| **Worker Quiescence** | `ResourceAuthority.scale_down_drain()` | Scaling policy | Manual / Controller | Drain $\to$ Quiesce $\to$ Fence $\to$ Retire | `test_phase7_resource_authority.py` | $P_7, P_{13}$ Fencing | **SUPPORTED** |
| **Gate A Cgroups** | `WorkerSupervisor` / `CgroupResourceEnforcer` | `resources=...` | cpu/memory/pids limits | OS cgroup boundary | `test_execution_enforcement_stress.py` | — | **IMPLEMENTED / ADVERSARIALLY-TESTED** |
| **Autoscaling Loop** | `cortex.yaml` (`scaling:`) | Autoscale policy | Threshold config | Metric-driven scale up/down | Prototype | Experimental | **PROPOSED** |
