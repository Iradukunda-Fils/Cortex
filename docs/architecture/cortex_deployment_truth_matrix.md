# Cortex Deployment Truth Matrix & Environment Envelope

> **Release Baseline**: `v0.7.0rc1` | **HEAD**: `c7ad74f117fc6e484eb2b5e13a1582002e400756`  
> **Containment Subsystem**: Linux Landlock LSM, cgroups v2, NetNS, seccomp

---

## 1. Operating Environment Matrix

| Environment Tier | Required Kernel | Physical Containment Controls Active | Network Isolation | Fail-Closed Policy | Supported Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Development (Host)** | Linux / macOS | Simulated cgroups / Fallback | Loopback / Mock | Warn & Degrade | Supported for Dev |
| **CI / Automated Test** | Linux >= 5.4 | Mock cgroups / Landlock optional | Namespace unshare | Standard | Supported for CI |
| **Unprivileged Production** | Linux >= 5.13 | Landlock LSM + `PR_SET_NO_NEW_PRIVS` | NetNS `CLONE_NEWNET` | Fail-Closed (`ExecutionRejected`) | **Tier 1 Production** |
| **Privileged Production** | Linux >= 5.13 | Landlock LSM + cgroups v2 | Dedicated NetNS | Fail-Closed (`ExecutionRejected`) | **Tier 1 Production** |
| **Containerized (Docker/K8s)**| Linux Host >= 5.13| Mounted `/sys/fs/cgroup` + Landlock | Container NetNS | Fail-Closed (`ExecutionRejected`) | **Tier 1 Production** |

---

## 2. Low-Level Kernel Dependencies

For full production-grade physical enforcement, the host kernel must satisfy:

1. **Linux Landlock LSM (Kernel >= 5.13)**: Restricts filesystem access for untrusted worker processes. Requires `PR_SET_NO_NEW_PRIVS` pre-requisite.
2. **Linux cgroups v2 (`/sys/fs/cgroup`)**: Unified control group hierarchy for memory ceiling (`memory.max`), CPU accounting (`cpu.stat`), and process ID bounds (`pids.max`).
3. **Network Namespaces (`CLONE_NEWNET`)**: Unshares host network stack, isolating worker processes to loopback (`127.0.0.1`) or private interfaces.
4. **File Descriptor Sanitation (`close_range`)**: Kernel syscall (`SYS_close_range`, Linux >= 5.9) to close all non-standard FDs > 3, binding the worker IPC socket pair exclusively to FD 3.

---

## 3. Physical Containment & Degradation Rules

Cortex enforces the **Atomic Uncontained Startup Prevention Rule**:

```
If contract.require_physical_enforcement == True AND cgroup_v2 == UNAVAILABLE:
    => Execution REJECTED (Fail-Closed)

If contract.require_network_isolation == True AND netns == UNAVAILABLE:
    => Execution REJECTED (Fail-Closed)
```

In development or CI environments where `require_physical_enforcement=False`, `WorkerSupervisor` logs a warning and degrades gracefully to process-level isolation without kernel containment.
