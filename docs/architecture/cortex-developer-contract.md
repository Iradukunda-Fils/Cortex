# Cortex Developer Contract Specification

**Normative Document Version**: v2.0.0-FINAL  
**Target Audience**: Application Developers, Infrastructure Engineers, Subsystem Authors  
**Core Principle**:

$$\boxed{ \text{Cortex should make the safe path easy, not expose the entire safety machinery to ordinary developers.} }$$

---

## 1. Abstraction Boundary & Public Contract

The Cortex Public Developer Contract cleanly separates **Application Intent** from **Kernel Safety Machinery**.

```text
Application Developer
        │
        ▼  Level 1 / Level 2 API (@cortex.task)
┌───────────────────────────────────────────────────────────┐
│               Cortex Application Layer                    │
└──────────────────────────────┬────────────────────────────┘
                               │  Declarative Spec / Intent
                               ▼
┌───────────────────────────────────────────────────────────┐
│                 Cortex Safety Kernel                      │
│                                                           │
│  • Resource Authority      • Physical Hardware Discovery  │
│  • Lease Epoch Fencing     • Dynamic Load Balancer        │
│  • Scale-Down Quiescence   • WAL Recovery & Replay        │
│  • Coq Machine Proofs      • TLA+ Distributed Fencing     │
└───────────────────────────────────────────────────────────┘
```

### Export Control Boundary
The public contract explicitly **hides** internal kernel mechanics. Wildcard imports are disabled via `__all__ = []` in the kernel modules, acting as a public export declaration to discourage internal module usage. The public developer API surface is frozen at exactly 23 symbols in `cortex.__all__`.

---

## 2. Progressive Disclosure API Levels

Cortex provides three distinct API levels tailored to different developer roles:

### Level 1 — Simple Application API

For standard application tasks without hardware constraints:

```python
import cortex

@cortex.task
def send_email(recipient: str, subject: str, body: str):
    # Application logic here
    pass
```

*Default Behavior (IMPLEMENTED DEFAULT)*: Automatically discovers host capacity, applies baseline limits of `1 CPU core` and `512 MiB RAM`, reserves capacity, and executes on an active worker.

---

### Level 2 — Resource-Aware API

For workloads with specific hardware or performance requirements:

```python
import cortex

@cortex.task(
    resources={
        "cpu": "4",
        "memory": "8GiB",
        "gpu": 1,
        "vram": "12GiB",
    },
    timeout=60.0,
    retries=3,
)
def run_model_inference(prompt: str):
    # Model inference logic
    pass
```

*Default Behavior (IMPLEMENTED DEFAULT)*: Timeout defaults to `60.0` seconds and retries default to `3`. Resource unit strings are normalized to base integers (`4000 millicores`, `8,589,934,592 bytes`, `12,884,901,888 bytes`).

---

### Level 3 — Expert / Kernel Integration API

Reserved exclusively for kernel infrastructure developers:

```python
# [INTERNAL KERNEL PSEUDOCODE - NOT PUBLIC SDK]
# Low-level Kernel Infrastructure API (Internal Kernel Subsystem)
# Direct reservation linearizable transition executed inside kernel processes:
# authority = ResourceAuthority(...)
rec = authority.reserve(
    res_id=1, res_inv=101, res_att=1, res_worker=2, res_demand=100,
    authority_epoch=1, lease_epoch=1, worker_generation=1, gpu_id=0
)
```

---

## 3. Physical Resource Discovery vs. Policy Overrides

Cortex enforces the principle:

$$\boxed{ \text{Unknown physical capacity} \neq \text{arbitrary default capacity} }$$

When unconfigured, Cortex automatically interrogates physical OS hardware and Linux cgroups (`os.cpu_count()`, `/sys/fs/cgroup/cpu.max`, `/proc/meminfo`). Arbitrary defaults are used only for safety policies, never for pretending to know host hardware limits.

---

## 4. Execution & Failure Guarantees

| Scenario | Developer-Visible Behavior | Kernel Machinery Underneath |
| :--- | :--- | :--- |
| **Normal Task Run** | Returns result cleanly | Reserve $\to$ Lease $\to$ Place $\to$ Execute $\to$ Release |
| **Worker Failure** | Task is automatically retried | Failure detected $\to$ Lease invalidated $\to$ Fenced $\to$ Reassigned |
| **Resource Contention** | Task waits or backpressures | Capacity safety check ($P_2$) delays placement |
| **Scale-Down** | Zero disruption to active tasks | Drain $\to$ Quiesce $\to$ Reclaim $\to$ Fence $\to$ Retire |
| **Node Crash / Restart** | State recovered automatically | WAL replay isolating terminal records ($P_{10}$) |

---

## 5. Developer Contract Invariants

$$\boxed{ \text{Developer Policy} \subseteq \text{Cortex Safety Constraints} }$$

Application developers can configure resource demands, timeouts, and retry policies. They **cannot** bypass capacity safety, disable lease fencing, override exclusive GPU ownership, or ignore recovery guarantees.

---

## 6. Assurance & Refinement Classifications

The Cortex Developer Contract distinguishes between:
1. **Coq Mathematical Models (`PROVEN`)**: Formally proven properties of state transitions ($S_R$).
2. **Python Implementation (`IMPLEMENTED / RUNTIME-VERIFIED`)**: Concrete executable code, verified by unit and integration tests.
3. **Refinement Model (`UNPROVEN / OPEN`)**: The formal refinement mapping ($Python \to Coq$), which remains unproven.

Phase 8.0 explicitly targets machine-checked refinement proofs for:
- **Phase 4 routing refinement (Issue #32)** ($R_{\text{Phase4}}(C_{\text{Python}}, A_{\text{Coq}})$) — **`UNPROVEN / OPEN`**
- **Phase 7 ResourceAuthority reservation refinement** ($R_{\text{Phase7}}(C_{\text{Python}}, A_{\text{Coq}})$) — **`UNPROVEN / OPEN`**

Tests do not substitute for formal refinement proofs. The active objective of Phase 8 is verification of these simulation refinement theorems.
