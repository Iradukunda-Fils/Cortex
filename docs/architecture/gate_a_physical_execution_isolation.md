# Cortex Gate A Physical Execution Isolation & Resource Enforcement Specification

**Normative Document Version**: v1.0.0-FINAL  
**Implementation Baseline**: `cortex/tools/kernel/enforcement/`  
**Support Status**: `IMPLEMENTED / ADVERSARIALLY-TESTED`  
**Authoritative Proof/Test Baseline**: `tests/kernel/test_execution_enforcement_stress.py` (10/10 PASS)

---

## 1. Executive Summary & Core Principle

Gate A establishes the physical execution boundary between Cortex's logical scheduling decisions and the host Linux operating system. It ensures that worker resource utilization (CPU, memory, PIDs) is strictly governed by physical OS limits, preventing a compromised or defective worker from exhausting host resources or impacting the Gateway control plane.

### The Rule of Isolation

$$\boxed{ \text{Worker Failure} \not\Rightarrow \text{Cortex Control Plane Failure} }$$

To enforce this, Cortex delegates control to a structured execution pipeline that maps declarative resource allocations directly to Linux kernel subsystem configurations.

---

## 2. Enforcement Pipeline Architecture

Execution isolation flows in a strict, unidirectional sequence:

$$\text{ResourceAuthority} \longrightarrow \text{EnforcementContract} \longrightarrow \text{WorkerSupervisor} \longrightarrow \text{CgroupResourceEnforcer} \longrightarrow \text{cgroups v2}$$

1. **ResourceAuthority**: Validates a task's logical resource demand vector and issues a linearizable reservation.
2. **EnforcementContract**: Converts the authorized reservation into concrete physical quantities (CPU millicores, RAM bytes, max PIDs).
3. **WorkerSupervisor**: Controls the process lifecycle of the spawned worker, executing containment setup, membership checks, and teardown.
4. **CgroupResourceEnforcer**: Orchestrates filesystem write operations inside the Linux cgroups directory tree.
5. **cgroups v2**: The host Linux kernel enforces scheduling quotas, memory limits, and PID limits directly at the CPU scheduler and memory manager levels.

---

## 3. Component Responsibility Boundaries

Cortex maintains a strict separation of concerns between state-deciding and state-executing layers:

$$\boxed{ \text{Supervisor Executes; Authority Decides} }$$

### ResourceAuthority
*   **Authorization**: Decides if resource vectors fit within safety bounds.
*   **Capacity Control**: Keeps logical track of active reservations and system margins.
*   **Lease Validity**: Manages epochs and worker fencing records.
*   *Boundary*: ResourceAuthority **never** launches processes or writes to the filesystem.

### WorkerSupervisor
*   **Process Launching**: Spawns worker processes using `subprocess.Popen` inside a new session ID.
*   **Containment Verification**: Verifies that the child process is correctly attached to the designated cgroup before letting it run.
*   **Orchestration & Reclamation**: Implements the multi-stage cleanup and triggers logical reconciliation on the ResourceAuthority.
*   *Boundary*: WorkerSupervisor **never** makes scheduling decision calculations.

### CgroupResourceEnforcer
*   **Hierarchy Management**: Reads and writes cgroups v2 mount points (`/sys/fs/cgroup`).
*   **Limit Allocation**: Configures controller files (`cpu.max`, `memory.max`, `pids.max`).
*   **Membership Management**: Adds process PIDs to `cgroup.procs`.
*   *Boundary*: CgroupResourceEnforcer is stateless and only translates data into system filesystem calls.

---

## 4. Physical Enforcement and Support Matrix

Cortex explicitly separates implemented physical protections from future/design-only capabilities:

| Dimension | Mechanism | Configuration Key | Current Status | Notes / Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **CPU Limit** | cgroups v2 `cpu.max` (CFS Period/Quota) | `cpu_mcores` | **ADVERSARIALLY-TESTED** | Translates millicores to CFS quota. Verified in stress suite. |
| **RAM Limit** | cgroups v2 `memory.max` | `memory_bytes` | **ADVERSARIALLY-TESTED** | Imposes hard limits. Out-of-memory triggers OS OOM-killer. |
| **Task / PID Limit** | cgroups v2 `pids.max` | `pids_max` | **ADVERSARIALLY-TESTED** | Restricts fork-bombing or runaway thread spawning. |
| **GPU / VRAM Isolation** | NVIDIA MIG / cgroups `devices` | `gpu_devices`, `vram_bytes` | **DESIGN ONLY / PHASE 7.4** | Logical device assignment $P_{11}$ is verified; physical isolation is open. |
| **Filesystem Sandboxing** | Linux Landlock LSM | `landlock_paths` | **DESIGN ONLY** | Policy parser exists in config resolver; runtime sandbox is not active. |
| **Syscall Filtering** | Seccomp-BPF | `allowed_syscalls` | **DESIGN ONLY** | Config options defined; kernel filter attachment is unimplemented. |
| **Network Isolation** | Namespace `CLONE_NEWNET` | N/A | **PROPOSED** | Scheduled for next major runtime integration. |

---

## 5. Worker Lifecycle and Reclamation Semantics

To prevent stale resource reuse or reservation leaks, a worker's physical execution tree must be completely torn down before its resources are recycled.

### The Reclamation Sequence

Reclamation follows a strict 7-stage sequence to guarantee safety:

$$\text{Fence} \longrightarrow \text{StopAdmission} \longrightarrow \text{Terminate/Quiesce} \longrightarrow \text{ConfirmExit} \longrightarrow \text{OSReclamation} \longrightarrow \text{LogicalReconciliation} \longrightarrow \text{CgroupCleanup}$$

1. **Fence**: Marks the worker's epoch as stale to reject any new incoming tasks.
2. **StopAdmission**: Blocks placement updates on the worker's logical queue.
3. **Terminate/Quiesce**: Sends `SIGTERM` to the worker process group. If the process is still running after a configurable grace period, escalates to `SIGKILL`.
4. **ConfirmExit**: Waits for the main PID and child PIDs to exit, and collects exit codes.
5. **OSReclamation**: Allows the Linux kernel to clean up dirty process pages and release file descriptors.
6. **LogicalReconciliation**: Signals `ResourceAuthority.release(reservation_id)` to logically return the resource capacity to the pool.
7. **CgroupCleanup**: Deletes the task's cgroup directory. Uses backoff retries to handle kernel-delayed memory cleanup.

### The Safety Invariant

$$\boxed{ \text{CapacityReusable} \implies \text{ExecutionTreeTerminated} \land \text{ExitObserved} \land \text{OldExecutionCannotContinue} }$$

*   Logical release of a reservation must **never** occur prior to the physical verification of process exit.
*   This invariant prevents **capacity-reuse races** where a new worker is launched before the old worker's processes have relinquished physical RAM and CPU cycles.

---

## 6. Fail-Closed Containment Semantics

If the physical security boundary cannot be guaranteed, Cortex executes a fail-closed shutdown to protect the host:

### Startup Failure Policy
If `require_physical_enforcement` is set to `True`:
1. **Environment Check**: If cgroups v2 are missing or permissions are denied, worker startup aborts immediately before spawning any process.
2. **Attachment Failure**: If attaching the spawned process PID to the cgroup's `cgroup.procs` fails, or if process membership verification fails:
    *   The supervisor immediately kills the process (`SIGKILL`).
    *   The cgroup directory is removed.
    *   The supervisor enters the `FAILED_CLOSED` terminal state.
    *   No task execution occurs under uncontained host conditions.

---

## 7. Operational Telemetry and Statistics

The `WorkerSupervisor` dynamically samples real-time resource utilization from cgroups to feed system-level scheduling decisions:
*   `cpu.stat`: Samples `usage_usec` to compute exact CPU utilization.
*   `memory.current`: Monitors real-time memory usage (in bytes).
*   `pids.current`: Counts currently active processes and threads inside the cgroup tree.
