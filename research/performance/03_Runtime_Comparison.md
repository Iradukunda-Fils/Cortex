# Research Note 03: Runtime & Substrate Comparison

## Executive Summary
This document analyzes the communication and scheduling performance characteristics across Python (`ProductionDynamicLoadBalancer`), Go (`cortex-go`), and Rust (`cortex-emulator`) execution pathways in Cortex.

---

## 1. Substrate Communication & Boundary Architecture

$$\begin{array}{rcccl}
\mathbf{\text{Python Kernel}} & \xrightarrow{\text{JSON / UDS Socket}} & \mathbf{\text{Go Gateway Substrate}} & \xrightarrow{\text{IPC Stream}} & \mathbf{\text{Worker Process}} \\
\mathbf{\text{Python Kernel}} & \xrightarrow{\text{Native Python Call}} & \mathbf{\text{Production Scheduler}} & \xrightarrow{\text{mmap / WAL}} & \mathbf{\text{Durable Disk Engine}} \\
\mathbf{\text{Python Verification Harness}} & \xrightarrow{\text{Subprocess / Stdio}} & \mathbf{\text{Rust Emulator Harness}} & \xrightarrow{\text{Trace Output}} & \mathbf{\text{Differential Oracle}}
\end{array}$$

---

## 2. Measured Boundary Latency Comparison

| Component / Substrate | Transport Mechanism | Serialization Format | P50 Overhead ($\mu$s) | P99 Overhead ($\mu$s) | Bottleneck Source |
|---|---|---|---|---|---|
| **Python In-Memory Scheduler** | Direct Function Call | Native Dataclass | $428.04$ | $795.69$ | $O(N)$ linear scan |
| **Python WAL Engine** | File Write + `fsync` | CRC32 Binary Frame | $840.10$ | $3,210.50$ | Disk `fsync` flush |
| **Go IPC Gateway** | Unix Domain Socket | JSON RPC Stream | $210.00$ | $1,150.00$ | JSON marshalling |
| **Rust Emulator** | FFI / Subprocess Pipe | Canonical Binary | $45.00$ | $180.00$ | Process launch overhead |

---

## 3. Substrate Transition Criteria (#50.d)

Moving control authority or scheduling state from Python to Go or Rust is governed by the following criteria:

1. **Re-Refinement Cost**: Moving the authoritative scheduler state into Rust/Go invalidates the Python-to-Coq refinement proof (`Phase5Simulation.v`). A new Coq extraction or C/Rust refinement model would be required.
2. **IPC Boundary Cost**: If the scheduler is implemented in Go/Rust while policy decisions remain in Python, cross-language IPC/FFI serialization ($T_{serialization} + T_{IPC}$) may exceed the $O(1)$ algorithmic selection savings for $N < 1,000$.
3. **Primary Recommendation**:
   - For $N \le 1,000$, retain Python as the authoritative control substrate.
   - Optimize worker selection from $O(N)$ linear scan to $O(1)$ Power of Two Choices (P2C) or $O(\log N)$ min-heap within Python first.
   - Re-evaluate Rust/C FFI only if Python $O(1)$ throughput is insufficient for $N > 10,000$.
