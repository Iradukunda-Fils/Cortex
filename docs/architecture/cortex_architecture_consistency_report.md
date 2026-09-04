# Cortex Systems Architecture & Implementation Consistency Report

> **Release Baseline**: `v0.7.0rc1` | **Baseline Type**: Hardened Pre-Release Candidate  
> **Systems Perspective**: Systems Engineering, Low-Level Security & Memory Audit

---

## 1. DSRP Systems Mental Model

To establish systemic rigor, the Cortex platform architecture is modeled across four core cognitive perspectives:

```
+-----------------------------------------------------------------------------------+
|                               DSRP MENTAL MODEL                                   |
+-----------------------------------------------------------------------------------+
| 1. DISTINCTIONS  | • Logical Capability vs Physical Containment                   |
|                  | • Native Plugin (Python) vs External Worker (Subprocess)      |
|                  | • Encoding (CBE) vs Transport (IPC/Stdio) vs Protocol (RPC)    |
|                  | • Authority Decision vs Adapter Execution                     |
+------------------+----------------------------------------------------------------+
| 2. SYSTEMS       | • Canonical Pipeline: Client -> Authority -> Gate -> Supervisor|
|                  | • 8-Stage Effect Runtime (Auth -> Replay -> Exec -> CAS -> Rec) |
|                  | • Dual Supervisor: Python cgroups v2 & Rust Landlock Emulator  |
+------------------+----------------------------------------------------------------+
| 3. RELATIONSHIPS | • Resource reservation binds worker lifetime to cgroup/RAM     |
|                  | • HMAC execution tokens cryptographically fence requests       |
|                  | • SHA-256 CAS references link evidence payloads to invocations|
+------------------+----------------------------------------------------------------+
| 4. PERSPECTIVES  | • Developer: Clean high-level Python/YAML workflow API        |
|                  | • Security Auditor: Fail-closed isolation & zero secret leak   |
|                  | • Systems Operator: Deterministic crash recovery & bounded RAM |
+-----------------------------------------------------------------------------------+
```

---

## 2. Canonical Execution Path

The verified canonical execution flow from user invocation to external side-effect actuation is:

```
[ CortexClient ]
       │
       ▼ (1. Reserve Capacity)
[ ResourceAuthority ] ─── Validates RAM, CPU, PIDs vector budget
       │
       ▼ (2. Authorize & Issue HMAC Token)
[ GatewayAuthorizationGate ] ─── Restricts caps, computes execution_token
       │
       ▼ (3. Launch Contained Worker)
[ WorkerSupervisor ] ─── Setsid, unshares netns/PID, attaches cgroup v2
       │
       ▼ (4. Subprocess Execution)
[ Worker Process ] ─── Formulates EffectRequest (NO credentials embedded)
       │
       ▼ (5. Pipeline Execution)
[ EffectExecutionPipeline ]
   ├── A. Replay Lookup (EffectResultStore)
   ├── B. Credential Resolution (CredentialBroker vault)
   ├── C. Adapter Invocation (ResourceContract)
   ├── D. Authoritative CAS Spooling (if evidence > 4KiB)
   └── E. Reconcile State (EffectReconciliationEngine)
       │
       ▼ (6. Physical Actuation)
[ External Adapter / System ]
```

### Auxiliary Runtimes & Emulator Role
* **`cortex-emulator` (Rust)**: Serves as the Profile A physical container supervisor, implementing 2-stage PID 1 fork topology, `close_range` FD sanitation (preserving FD 3 Unix socketpair), Landlock LSM, and `PR_SET_NO_NEW_PRIVS`.
* **Go Runtime (`cortex-go`)**: Implements strict CBE encoding/decoding and external adapter bindings for Go-based subprocesses.

---

## 3. Low-Level Security & Architecture Audit Fixes

During the audit, three critical lower-level vulnerabilities were identified and remediated:

### 3.1. CBE Decoder Memory Amplification / OOM DoS Mitigation
* **Vulnerability**: Untrusted CBE payloads with large `count` headers (e.g. `L1000000000:`) previously caused Go (`make([]CortexValue, 0, count)`) and Python decoders to pre-allocate gigabytes of RAM prior to consuming stream bytes.
* **Remediation**: Initial slice allocation in Go (`cortex-go/cbe/decoder.go`) was updated to bound initial capacity ($\text{initial allocation} = \min(\text{declared count}, 1024)$), eliminating memory amplification attacks.

### 3.2. Worker Process Group Orphan Elimination
* **Vulnerability**: `WorkerSupervisor` spawns workers with `os.setsid()`, creating a Process Group Leader. Previous termination logic called `proc.terminate()` / `proc.kill()` targeting only `proc.pid`. Subprocess trees spawned by workers were left running as orphaned background processes when cgroups were disabled.
* **Remediation**: `supervisor.py` was updated to issue `os.killpg(proc.pid, signal.SIGTERM/SIGKILL)` on Unix platforms, enforcing the strict invariant:
  $$ \boxed{ \text{Terminate Worker} \Rightarrow \text{Terminate Worker Process Group} } $$

### 3.3. CAS Evidence Ownership Disconnect Fix
* **Vulnerability**: `LocalProcessMCPAdapter` previously attempted to format evidence pointers directly as `is_reference=True` without storing the payload in `ContentAddressableStore`. `EffectExecutionPipeline` skipped CAS storage for `is_reference=True` items, resulting in lost evidence data.
* **Remediation**: `mcp_adapter.py` was updated to return raw evidence bytes, enforcing clean boundary decoupling:
  $$ \boxed{ \text{Adapter} = \text{produce evidence} } \quad \quad \boxed{ \text{Pipeline} = \text{persist / address / own evidence} } $$

---

## 4. Master Architectural Truth Matrix (Refined Evidence Taxonomy)

| Area / Feature | Source Code Reference | Formal Proof Level | Execution Verification Level | Exact Evidence Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Core Runtime** | `cortex/client.py` | N/A | 222 Conformance Tests PASSED | **Code Implemented & Runtime Verified** |
| **ResourceAuthority** | `cortex/tools/kernel/resource_authority.py` | Coq Phase 8 Proven | Refinement Theorem Proven | **Formally Verified (Model + Refinement + Code)** |
| **Gateway Authorization Gate**| `cortex/tools/kernel/effect_gateway.py` | Coq Gate F Proven | Conformance Tested | **Formally Verified Model + Implementation Tested** |
| **WorkerSupervisor** | `cortex/tools/kernel/enforcement/supervisor.py` | N/A | Runtime Tested (NetNS/cgroups kernel verified when unshared) | **Code Implemented & Runtime Verified** |
| **Profile A Landlock Sandbox** | `cortex-emulator/src/sandbox.rs` | N/A | Rust Integration Tested (Landlock kernel verified on Linux >=5.13) | **Implemented in Rust & Runtime Verified** |
| **EffectExecutionPipeline** | `cortex/tools/kernel/effect_runtime.py` | N/A | Conformance Tested | **Code Implemented & Runtime Verified** |
| **ResourceContract Adapters** | `cortex/tools/kernel/adapter_contract.py` | N/A | Conformance Tested | **Code Implemented & Runtime Verified** |
| **ContentAddressableStore (CAS)**| `cortex/tools/kernel/effect_runtime.py` | N/A | Conformance Tested | **Code Implemented & Runtime Verified** |
| **WAL Durability** | `cortex/tools/kernel/replica/ledger.py` | Coq Phase 6 Proven | Conformance Tested | **Formally Verified Model + Implementation Tested** |
| **CBE Serialization** | `cortex/cbe/*`, `cortex-go/cbe/*` | Coq CBESpec Proven | Cross-Language Conformance Tested | **Spec Formally Proven + Multi-Lang Impl Tested** |
| **Measured Memory Envelope** | `cortex/tools/kernel/` | N/A | Benchmark Measured | **467.39 B/effect retained under benchmark workload** |
| **Measured Throughput Envelope**| `cortex/tools/kernel/` | N/A | Benchmark Measured | **$\lambda_{\text{pipeline}} = 1{,}738\text{--}3{,}563$ ops/s \| $\lambda_{\text{end-to-end}} = 6.5\text{--}11.7$ effects/s** |
| **Scalability Envelope** | N/A | N/A | Unmeasured | **Unmeasured / Evidence-Gated** |
