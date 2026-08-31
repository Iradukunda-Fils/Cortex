# Cortex System Architecture (Ground-Truth Baseline — v0.4.0-experimental)

> **Governance Status**: `NORMATIVE ARCHITECTURAL BASELINE`  
> **Baseline Release Tag**: `v0.4.0-experimental` (`v0.4.0rc1`)  
> **Commit SHA**: `012b0950968e`  
> **Branch State**: `feature/phase-4-routing-dispatch` (Phase 4 code present & integrated)  
> **Assurance Manifest SHA-256**: `d748ec7a5f52eabfbe703e057b5b9d41f37636695453df05b2fa201c881ccf56`  
> **System Status**: `CONTROLLED_EXPERIMENTAL` (Production Blocked pending P0–P13 & Security Audit)  

---

## 1. System Overview

Cortex is a spatiotemporal authority, deterministic execution, and formal verification platform. It enforces cryptographic identity, fine-grained capability containment, causal event traceability, and fail-closed state management across polyglot execution environments (Python, Rust, Go) and custom hardware RTL models (SystemVerilog STCR pipeline).

### Core Architectural Invariants

1. **Complete Mediation (Gate G)**: Every execution request and side effect passes through the Trusted Computing Base (TCB) host supervisor (`CapabilitySandbox`). Unprivileged workers cannot issue unmediated syscalls or file system mutations. Gate G is **`IMPLEMENTATION-CERTIFIED FOR TESTED PROFILE A CONFIGURATION`**.
2. **Authority Fencing (Phase 4)**: Clear separation of roles in request dispatch:
   - **Router** *proposes* worker placement based on eligibility.
   - **LeaseManager** *authorizes* execution by issuing atomic single-grant leases bound to `ConfigGeneration` and `CapabilityToken`.
   - **InvocationLedger** *records* state transitions monotonically.
   - **GatewayDispatcher** *commits* execution and enforces `StateDomainKey` mutual exclusion fencing.
3. **Telemetry Non-Authority**: Telemetry signals (inflight count, CPU/memory usage, latency) are treated as untrusted hints. They NEVER bypass capability checks, lease revalidation, or state domain locks.
4. **Causal Traceability (Gate I/J)**: Every state mutation produces an immutable, SHA-256 rolling-hash-linked event tree verifyable by an offline verifier (`cortex_verifier.py`).
5. **Fail-Closed Safety**: Any configuration mismatch, stale lease, unhandled worker failure, or corrupt telemetry immediately aborts execution and rolls back uncommitted state.
6. **Autoscaling Governance**: Unbounded or authority-expanding autoscaling is strictly prohibited. Bounded autoscaling with strict operational constraints (`min_replicas`, `max_replicas`, `scale_up_threshold`, `scale_down_threshold`, `cooldown`, `rate_limits`) MAY be introduced in future phases without violating bounded determinism.
7. **Physical Execution Enforcement (Gate A)**: Worker processes are physically contained using Linux cgroups v2 (`cpu.max`, `memory.max`, `pids.max`). The `WorkerSupervisor` orchestrates process lifecycle and the `CgroupResourceEnforcer` writes OS limits. Gate A is **`IMPLEMENTED / ADVERSARIALLY-TESTED`**.

---

## 2. Clean-Room Repository Structure

```
Cortex/
├── apps/                               # Scaffolded application workspace
├── artifacts/                          # Build, verification, and release artifacts
│   └── release_candidates/             # Immutable release evidence packages
│       └── v0.4.0-experimental/        # v0.4.0 release evidence bundle
├── bin/                                # Compiled executable binaries
├── contracts/                          # Formal JSON schemas for commit contracts
│   └── commit/
│       └── commit_contract_v1.schema.json
├── cortex/                             # Core Python Kernel & Control Plane Engine
│   ├── cbe/                            # Canonical Binary Encoding (CBE) encoder/decoder
│   ├── schema/                         # Core schema models (events, tokens, contracts)
│   ├── schemas/                        # Draft 2020-12 JSON Schemas for configuration
│   │   └── v1/
│   │       └── configuration.schema.json
│   ├── tools/                          # CLI and internal kernel modules
│   │   ├── cli/                        # CLI parser, runner, scaffolder (`cortex` binary)
│   │   ├── kernel/                     # Kernel runtime engine
│   │   │   ├── replica/                # Phase 4 replica lifecycle, router, lease, ledger
│   │   │   │   ├── identity.py         # Dynamic UUIDv5 instance identity derivation
│   │   │   │   ├── lease.py            # Single-grant lease manager with generation fencing
│   │   │   │   ├── ledger.py           # Monotonic invocation ledger & commit records
│   │   │   │   ├── lifecycle.py        # Replica process supervisor & lifecycle manager
│   │   │   │   └── router.py           # CandidateResolver & CandidateRouter (Least-Inflight)
│   │   │   ├── schema/                 # Kernel-level Pydantic data schemas
│   │   │   ├── services/               # Event store, replay engine, verification bus
│   │   │   ├── enforcement/            # Gate A physical execution enforcement
│   │   │   │   ├── contract.py         # EnforcementContract & SupervisorLifecycleState
│   │   │   │   ├── cgroup.py           # CgroupResourceEnforcer (cgroups v2 interface)
│   │   │   │   └── supervisor.py       # WorkerSupervisor process lifecycle manager
│   │   │   └── transport.py            # Layer 2 framing transport adapters
│   │   ├── verification/               # Verification engine, adapters (Coq, Rust, RTL)
│   │   └── verify.py                   # High-level verification runner
│   └── _telemetry/                     # Telemetry models, benchmark, collector
├── cortex-emulator/                    # High-Performance Rust Execution Engine & STCR Emulator
│   ├── Cargo.toml
│   ├── src/                            # Rust ISA simulator, STCR capability register file, CBE decoder
│   └── tests/                          # Rust CBE & Layer 2 streaming conformance tests
├── cortex-go/                          # Go Concurrency & Transport Adapter
│   ├── adapter/                        # Polyglot stream bridging
│   ├── cbe/                            # Pure-Go zero-dependency CBE codec
│   └── tests/                          # Cross-runtime parity conformance tests
├── docs/                               # Architectural documentation, gate specs, guides
│   ├── architecture/                   # Normative architecture specs & audit registers
│   ├── gate-specs/                     # Gate A–J specifications
│   ├── guides/                         # Configuration & manifest guides
│   └── spec/                           # Protocol & evidence schemas
├── examples/                           # Dogfooding workloads
│   └── repo_auditor/                   # Autonomous Repository Auditor example plugin
├── rtl/                                # Hardware Description Models
│   └── cortex_stcr_pipeline.sv         # SystemVerilog Spatio-Temporal Capability Register pipeline
├── tb/                                 # C++ Verilator testbenches
│   └── tb_top.cpp                      # Differential trace extractor testbench
├── tests/                              # Comprehensive Test & Conformance Suite
│   ├── certification/                  # Golden commit contracts and proof benchmarks
│   ├── conformance/                    # Cross-runtime & Gate A-J conformance suites
│   ├── golden/                         # F4c evidence corpus golden test vectors
│   ├── kernel/                         # Unit tests for CLI, plugin, and kernel engine
│   └── regression/                     # Versioned regression tests (v0.2.0, v0.2.1, Phase 4)
├── tools/                              # Audit & release tools
│   ├── assurance/                      # `docs_audit.py` documentation validator
│   ├── cortex_verifier.py              # Gate F4c / Gate J independent evidence verifier
│   └── release/                        # `readiness.py` release gate certifier
└── verification/                       # Formal Verification Suite (Coq / Rocq)
    ├── AuthorityModel.v                # Coq formal capability authority model
    ├── CBESpec.v                       # Formal specification of CBE serialization
    ├── GateF_*.v                       # Formal refinement & evidence proofs (F0, F1, F2, F3, F4)
    ├── GateL1_*.v                      # Formal hardware epoch monotonicity proofs
    ├── Phase4RoutingRefinement.v       # Formal safety kernel for Phase 4 Gateway Routing
    └── _CoqProject                     # Coq compilation manifest
```

---

## 3. End-to-End System Execution Flow

The real end-to-end execution flow of Cortex follows a strict 14-stage pipeline verified by code:

```
[1] Client / CLI (`cortex workflow run`)
        ↓
[2] Configuration Resolver (`cortex/schemas/v1/configuration.schema.json`)
        ↓
[3] Desired State Canonicalization (`ConfigGeneration` & `ConfigHash` derivation)
        ↓
[4] Reconciliation Loop (`ReplicaLifecycleManager` state check)
        ↓
[5] Replica / Worker Lifecycle (`LifecycleStage.READY` allocation)
        ↓
[6] Candidate Resolver (`CandidateResolver.resolve_candidates()`)
        ↓
[7] Router / Placement Policy (`CandidateRouter.propose_candidate()` - LEAST_INFLIGHT)
        ↓
[8] Lease Manager (`LeaseManager.issue_lease()` - Atomic Generation & Cap Check)
        ↓
[9] Invocation Ledger (`InvocationLedger.record_lease_issuance()`)
        ↓
[10] Worker Sandbox (`CapabilitySandbox` Profile A Seccomp/Landlock/Namespace boundary)
        ↓
[11] Execution / Effect (`IPC Channel` -> Plugin Invocation -> Response)
        ↓
[12] Commit Sequencer (`GatewayDispatcher` -> `StateDomainKey` Lock Release)
        ↓
[13] Witness / Evidence (`CausalWitness` -> SHA-256 Rolling Event Log)
        ↓
[14] Independent Verifier (`cortex_verifier.py` -> Offline Domain D_V1 Graph Audit)
```

---

## 4. Reconciled Machine-Derived Test & Certification Accounting

Every accounting figure in the Cortex repository is machine-derived directly from automated test execution runners:

| Harness / Subsystem | Test Methods | Checks / Assertions | Pass Rate | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Python Unit Tests** (`python -m unittest discover`) | 333 | 1,420+ | 333 / 333 (100%) | `PASS` |
| **Integrated Certification Pipeline** (`run_certification.py`) | N/A (Harness) | 136 | 136 / 136 (100%) | `PASS` |
| **Rust Emulator Unit & Conformance** (`cargo test`) | 41 | 41 | 41 / 41 (100%) | `PASS` |
| **Go Streaming Conformance** (`cortex-go/tests/`) | 1 package | 14 test vector frames | 14 / 14 (100%) | `PASS` |
| **RTL / Verilator Trace Bridge** (`test_conformance_rtl.py` & `tb_top.cpp`) | 12 | 17 cycle-accurate checks | 17 / 17 (100%) | `PASS` |
| **Coq Formal Proof Suite** (`verification/`) | 28 `.v` files, 26 `.vo` compiled | 27 Phase 4 theorems/lemmas | 0 Admitted, 0 Axioms | `coqchk PASS` |
| **Documentation Audit Engine** (`docs_audit.py`) | 8 target spec docs | 307 structural checks | 307 / 307 (222 warnings) | `PASS` |

---

## 5. Trust and Authority Domain Map

```
                  ┌─────────────────────────────────────────┐
                  │              UNTRUSTED                  │
                  │  * Plugin Code & Subprocesses           │
                  │  * CLI / ENV Environment Input          │
                  │  * External Telemetry Hints             │
                  │  * Malformed IPC Payloads               │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼ (Seccomp / Landlock / Socket Isolation)
                  ┌─────────────────────────────────────────┐
                  │            SEMI-TRUSTED                 │
                  │  * Candidate Router Proposals           │
                  │  * Telemetry Inflight Metrics           │
                  │  * Worker Health Heartbeats             │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼ (Atomic Locks & Validation)
                  ┌─────────────────────────────────────────┐
                  │             TRUSTED (TCB)               │
                  │  * Host Gateway & Dispatcher            │
                  │  * LeaseManager & InvocationLedger      │
                  │  * CapabilitySandbox Supervisor         │
                  │  * Hardware STCR Pipeline (RTL)         │
                  └─────────────────────────────────────────┘
```

---

## 6. Configuration & Control-Plane Architecture

The Cortex configuration model enforces strict immutability through `ConfigGeneration` counter increments and SHA-256 `ConfigHash` derivation. Configuration resolution is part of the control plane's security boundary. Resolving environment variable overrides through `ConfigResolver` (`DEBT-003`) is a P0 release blocker.

---

## 7. Formal Verification Architecture (Coq Baseline)

The formal baseline consists of 28 Coq source files (`.v`), compiled into 26 `.vo` artifacts. Verification is verified clean with `coqchk -R . Cortex`.

### Primary Formal Refinement Target (DEBT-001)
The primary formal target following the Phase 4 safety kernel is establishing a concrete-to-Coq forward simulation refinement relation:
$$R(C, M) \land C \to C' \implies \exists M'. M \to^* M' \land R(C', M')$$

---

## 8. Security & Sandbox Boundary Architecture (Gate G Profile A)

Gate G provides worker process isolation using Linux kernel primitives:
- **Namespaces**: `CLONE_NEWPID`, `CLONE_NEWNS`, `CLONE_NEWIPC`, `CLONE_NEWNET` (disabling host network access).
- **Seccomp-BPF**: Fail-closed syscall filter.
- **Landlock LSM**: Restricts filesystem access.
- **`no_new_privs`**: Enforced via `prctl(PR_SET_NO_NEW_PRIVS, 1)`.
- **FD Hygiene**: `close_range(3, ~0U, 0)`.

**Certified Boundary Wording**: Gate G is **`IMPLEMENTATION-CERTIFIED FOR TESTED PROFILE A CONFIGURATION`**. Universal complete mediation remains reserved for full formal simulation refinement proofs.

---

## 9. Hardware & Hardware/Software Co-Design Architecture

The hardware layer implements a Spatio-Temporal Capability Register (STCR) pipeline in SystemVerilog (`rtl/cortex_stcr_pipeline.sv`). Synthesis verification via Yosys (`DEBT-006`) proves synthesizability ($\text{RTL} \to \text{synthesizable}$), which is maintained as an independent evidence class from formal semantics refinement.

---

## 10. Summary Governance Verdict

```
========================================================================
                   CORTEX RELEASE READINESS REPORT                      
========================================================================
Release Baseline Tag:  v0.4.0-experimental (v0.4.0rc1)
Commit SHA:            012b0950968e
Manifest SHA-256:      d748ec7a5f52eabfbe703e057b5b9d41f37636695453df05b2fa201c881ccf56
Current Governance:    CONTROLLED_EXPERIMENTAL
Production Status:     BLOCKED (Pending P0–P13 & Security Audit)

[RECONCILED MACHINE-DERIVED TEST SUMMARY]
  - Python Unit Tests:            333/333 PASS (1,420+ assertions)
  - Integrated Certification:     136/136 PASS
  - Rust Emulator Tests:          41/41 PASS
  - Go Conformance Suite:         1/1 PASS (14 vector frames)
  - RTL Verilator Trace Bridge:   12/12 PASS (17 cycle assertions)
  - Coq Formal Verification:      28 Modules, 0 Admitted, 0 Axioms (coqchk PASS)
  - Documentation Audit Engine:   307/307 PASS (222 Warnings)
========================================================================
```

---

## 11. Frozen Public Developer Contract & Governance Invariants

### A. Architectural Posture: Frozen Interface / Evolving Kernel
The public developer API, application progressive disclosure spectrum, reference examples, and documentation rules are **SPECIFICATION-LOCKED & FROZEN**. Internal kernel infrastructure (scheduling algorithms, physical OS enforcement, vector resource management, and hardware adapters) continues evolving beneath the public API.

```
                 FROZEN PUBLIC SURFACE
        ┌─────────────────────────────────────┐
        │ Public Cortex SDK (@cortex.task)    │
        │ Reference Developer Examples        │
        │ 3-Level Progressive Disclosure API  │
        │ Documentation & Governance Rules    │
        └──────────────────┬──────────────────┘
                           │
                           ▼
                 EVOLVING KERNEL SUBSTRATE
        ┌─────────────────────────────────────┐
        │ Resource Authority & Lease Engine   │
        │ Worker Supervisor & Process Lifecycle│
        │ Cgroup / OS Enforcement Adapters    │
        │ Vector Resource Accounting          │
        │ Autoscaling & Distributed Runtime   │
        └─────────────────────────────────────┘
```

### B. Core Governance Invariants

1. **Complexity Absorption Invariant**:
   $$\boxed{ \text{Developer API Complexity} \ll \text{Cortex Internal Safety Complexity} }$$
2. **Explicit Evidence Requirement**:
   $$\boxed{ \text{Public API} = \text{simple} \quad\land\quad \text{Internal Architecture} = \text{complex} \quad\land\quad \text{Evidence} = \text{explicit} }$$
3. **Executable Documentation Rule**:
   $$\boxed{ \text{Examples} \longleftrightarrow \text{Public API} \longleftrightarrow \text{Tests} \longleftrightarrow \text{Documentation} }$$
4. **Mandatory 6-Stage Feature Gate Sequence**:
   $$\boxed{ \text{Design} \longrightarrow \text{Implementation} \longrightarrow \text{Executable Tests} \longrightarrow \text{Evidence} \longrightarrow \text{Documentation} \longrightarrow \text{Public API Decision} }$$
5. **Formal Model Distinction**:
   $$\boxed{ \text{Coq Abstract Proof} \neq \text{Automatic Proof of Python Implementation} }$$
   Abstract Coq proofs apply to formal specification models; concrete Python code requires explicit refinement proofs before claiming formal correctness.

