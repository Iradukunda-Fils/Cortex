# Cortex Systems Engineering & Architectural Q&A Reference Guide

Welcome to the **Cortex Systems Engineering & Architecture Guide**. This document provides an exhaustive, low-level technical reference for systems engineers, kernel developers, security auditors, and polyglot plugin contributors.

---

## Table of Contents
1. [Low-Level IPC Architecture & Socket Mechanics](#1-low-level-ipc-architecture--socket-mechanics)
2. [Process Sandboxing & Linux Kernel Security](#2-process-sandboxing--linux-kernel-security)
3. [Crash Semantics & Fail-Closed Safety State Machine](#3-crash-semantics--fail-closed-safety-state-machine)
4. [Polyglot Execution & Multi-Language Worker Architecture](#4-polyglot-execution--multi-language-worker-architecture)
5. [Scaling Architecture for 50+ Concurrent Plugins](#5-scaling-architecture-for-50-concurrent-plugins)
6. [Autonomous Systems, ML Acceleration & GPU Zero-Copy DMA](#6-autonomous-systems-ml-acceleration--gpu-zero-copy-dma)
7. [Comprehensive Systems Engineering Q&A](#7-comprehensive-systems-engineering-qa)

---

## 1. Low-Level IPC Architecture & Socket Mechanics

Cortex avoids TCP sockets, HTTP servers, or shared network interfaces for inter-process communication (IPC) to eliminate network stack overhead, TCP handshake latency, port collision risks, and remote exfiltration vectors.

### UNIX Socketpair Mechanics (`AF_UNIX`, `SOCK_STREAM`)
- **Parent-Child Socketpair**: The Host Gateway creates an un-named socket pair in kernel space via `os.socketpair(AF_UNIX, SOCK_STREAM)` prior to spawning worker child processes.
- **Pre-Opened File Descriptor (`FD 3`)**: The child worker inherits the socket on **File Descriptor 3 (`FD 3`)**. The worker needs zero filesystem or network permissions to open sockets at runtime.
- **Bi-Directional Full-Duplex Streaming**: Gateway and Worker communicate asynchronously via Layer 2 binary framed streams over `FD 3`.

```
+------------------------------------+                  +------------------------------------+
|            HOST GATEWAY            |                  |          SANDBOXED WORKER          |
|      (Master Authority Broker)     |                  |       (Isolated Runtime Code)      |
+------------------------------------+                  +------------------------------------+
                  │                                                       │
                  │              UNIX Socketpair (AF_UNIX)                │
                  ├───────────────────────────────────────────────────────┤
                  │   [FD: Parent Socket] <=========> [FD 3: Child Socket]│
```

### Layer 2 Binary Frame Specification (11-Byte Header)

All data moving across `FD 3` is wrapped in standard Layer 2 binary headers:

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Magic Byte 'C' (0x43)       |   Magic Byte 'X' (0x58)       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Version (0x01)| FrameType(0x01)|       Payload Length N       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|             Sequence Monotonicity Counter (3 Bytes)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                     CBE Serialized Body (N Bytes)             +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

---

## 2. Process Sandboxing & Linux Kernel Security

Cortex enforces zero-trust execution boundaries using native Linux kernel primitives:

### 1. Linux Namespace Isolation (`clone` / `unshare`)
- **`CLONE_NEWPID`**: Process table isolation. Worker runs as `PID 1` inside its private namespace. When `PID 1` terminates, all child subprocesses are reaped automatically by the kernel.
- **`CLONE_NEWNET`**: Network namespace isolation. Worker has zero loopback, TCP, UDP, or raw socket devices.
- **`CLONE_NEWNS`**: Mount namespace isolation. Worker views a read-only root mount with zero write access to host system directories.

### 2. Syscall Filtering (`seccomp-bpf`)
Worker execution is bound by a strict `seccomp-bpf` filter policy:
- **Blocked Syscalls**: `execve`, `ptrace`, `mmap` (with `PROT_EXEC`), `bind`, `connect`, `open` (on `/dev/*` nodes).
- **Violation Outcome**: Immediate kernel termination (`SIGSYS` / `SIGKILL`).

### 3. Capability-Based Token Authorization
Workers cannot invoke actions directly. All requests require a `Capability` token (e.g. `Capability("actuator:write")`) signed by the Host Gateway's hardware epoch controller (`HEC`).

---

## 3. Crash Semantics & Fail-Closed Safety State Machine

When a worker process crashes (e.g., SIGSEGV, Out-of-Memory, unhandled runtime exception):

```
                                  WORKER PROCESS FAILS / CRASHES
                                                │
                                                ▼
                             HOST GATEWAY INTERCEPTION (SIGCHLD / EOF)
                                                │
       ┌────────────────────────────────────────┴────────────────────────────────────────┐
       │                                                                                 │
       ▼                                                                                 ▼
[Pre-Actuation Crash]                                             [Post-Actuation Crash]
- Worker died BEFORE command dispatch.                            - Command dispatched, but worker died
- Single-use token invalidated.                                     before receiving completion telemetry.
- Zero physical side-effects.                                     - Event store logs `Verdict.INDETERMINATE`.
- Status: `FAILED_PRE_ACTUATION`                                  - Host Gateway triggers Hardware Safe-Stop.
```

### 3.1 Worker Auto-Respawn & State Catch-up
1. **SIGCHLD & Socket EOF Interception**: The Gateway detects worker PID termination and socket disconnect on `FD 3`.
2. **Token Invalidation**: Active single-use tokens assigned to the dead PID are invalidated immediately.
3. **Evidence Log**: Appends a `Verdict.INDETERMINATE` evidence flag to `EventStore`.
4. **Respawn & Re-sync**: Gateway launches a replacement sandboxed worker process, establishes a new socketpair `FD 3`, and replays state from `EventStore` to resynchronize the worker.

### 3.2 Race Condition & Concurrency Prevention
To prevent race conditions across concurrent workers:
- **Monotonic Frame Counter ($Seq_n = Seq_{n-1} + 1$)**: Header sequence counter prevents out-of-order execution or duplicate packet injection.
- **Hardware Epoch Monotonicity (`reg_hec`)**: State updates require an incrementing hardware epoch. Stale epoch updates ($Epoch_{recv} \le Epoch_{curr}$) are rejected at the hardware register layer.
- **Single-Writer Gateway Event Bus**: All events from concurrent workers commit sequentially on a single-threaded atomic Gateway event pipeline.
- **Single-Use Ephemeral Tokens**: Action tokens are single-use (`nonce` bound). Concurrent attempts to execute the same token result in `EXPIRED_OR_DUPLICATE_TOKEN` rejection for all but the first transaction.

---

## 4. Polyglot Execution & Multi-Language Worker Architecture

Cortex plugins can be written in **any programming language** (Python, C, Rust, Go, Java, TypeScript, Zig, C#).

### Universal 3-Primitive Language SDK Blueprint
To support ANY language natively, an SDK requires only 3 primitives:
1. **FD 3 Socket Reader/Writer**: Access to inherited POSIX File Descriptor `3`.
2. **Layer 2 Header Codec**: 11-byte binary header packer/unpacker (Big-Endian integer conversion).
3. **CBE Payload Codec**: Serializer/parser for Cortex Binary Encoding (CBE).

```
                            HOST GATEWAY (Python / Rust)
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        │ IPC (FD 3)                     │ IPC (FD 3)                     │ IPC (FD 3)
        ▼                                ▼                                ▼
+---------------+                +---------------+                +---------------+
| PYTHON WORKER |                |  RUST WORKER  |                |   GO WORKER   |
| (Orchestration|                | (High-Speed   |                | (Concurrent   |
|  & AI Logic)  |                | Control Loop) |                | Network/Data) |
+---------------+                +---------------+                +---------------+
```

---

## 5. Scaling Architecture for 50+ Concurrent Plugins

To scale to 50+ plugins without memory exhaustion:

1. **Capability Co-location (Grouped Workers)**: Plugins sharing privilege domains are co-located into shared worker processes, reducing 50 worker processes to 3–5 grouped containers (~120 MB RAM total).
2. **Worker Pool Instances**: For high-throughput plugins, the Gateway Pool Manager spawns multiple sandboxed worker instances (`SecureWorkerPoolManager`), balancing task events across active instance sockets (`FD 3`).
3. **Linux `epoll` $O(1)$ Multiplexing**: The Host Gateway manages all worker sockets on an asynchronous, non-blocking `epoll` reactor thread.
4. **0.0% Idle CPU Overhead**: Worker event loops waiting for data on `FD 3` via `read()` or `recv()` are suspended in kernel space (`TASK_INTERRUPTIBLE`), using **0.0% CPU** while idle.

---

## 6. Autonomous Systems, ML Acceleration & GPU Zero-Copy DMA

For real-time autonomous systems (robotics, self-driving vehicles, drone control):

### Scoped GPU Passthrough
ML perception workers are granted scoped `/dev/nvidia0` device nodes via `cgroups v2` whitelisting while maintaining `CLONE_NEWNET` isolation.

### Zero-Copy Shared Memory Frame Polling (`/dev/shm` + CUDA DMA)
Camera drivers capture 4K/60FPS video directly into POSIX Shared Memory (`/dev/shm`). The Gateway forwards only an 11-byte frame pointer containing memory offsets over `FD 3`. The GPU worker maps shared memory directly into CUDA VRAM (`cudaHostRegister`), achieving **zero CPU memory copy overhead**.

### Coq-Verified Deterministic Safety Boundary
All ML model outputs must pass through a machine-checked Safety Verifier (Coq `GateF_F4c_VerifierSpec.v`) before reaching physical actuators. If an ML model hallucinates a command violating kinematic bounds, the Safety Verifier rejects the step and engages safe braking.

---

## 7. Comprehensive Systems Engineering Q&A

### Q1: Why use UNIX socketpairs instead of gRPC or TCP?
**A:** gRPC and TCP introduce network stack overhead, TCP handshakes, port allocation conflicts, and potential remote network exploitation. UNIX socketpairs (`AF_UNIX`) run entirely in kernel memory with zero network stack footprint and pre-opened file descriptors.

### Q2: How does CBE differ from JSON or Protocol Buffers?
**A:** JSON allows key re-ordering (`{"a":1,"b":2}` vs `{"b":2,"a":1}`) and non-canonical float formats, resulting in inconsistent SHA-256 hashes across different language runtimes. CBE enforces byte-lexicographical key sorting, UTF-8 NFC Unicode normalization, and IEEE-754 canonical hex float representation (`D` tag), ensuring 100% bit-identical cryptographic hashes across C, Rust, Go, Java, Python, and TypeScript.

### Q3: Can a compromised worker read files from the host system?
**A:** No. Workers run inside isolated mount (`CLONE_NEWNS`) and PID (`CLONE_NEWPID`) namespaces with read-only root mounts and `seccomp-bpf` syscall filters blocking `open()` calls on host devices.

### Q4: How does Cortex handle external network API or Database calls from sandboxed workers?
**A:** Workers emit a `SignedIntent` event over `FD 3` requesting an external call (e.g. `mcp:call_tool` or HTTP request). The Host Gateway verifies the plugin's `Capability`, executes the network request out-of-band, and returns the result to the worker over `FD 3`.

### Q5: How do 50+ idle workers affect system CPU usage?
**A:** Idle workers consume 0.0% CPU. When a worker calls `read(3, ...)` on an empty socket buffer, the Linux kernel suspends the thread (`TASK_INTERRUPTIBLE`). The thread wakes up only when the Gateway writes bytes into the socket buffer.
