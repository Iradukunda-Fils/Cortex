# Cortex Future Implementation Roadmap

> **Governance Status**: `NORMATIVE FUTURE IMPLEMENTATION PLAN`  
> **Baseline Release**: `v0.4.0-experimental` (Commit `012b0950968e`)  
> **Target Horizon**: Phase A through Phase F  

---

## 1. Master Dependency & Implementation Sequence

Roadmap execution follows strict dependency and assurance readiness rather than immediate feature coding:

```
                  v0.4.0 Baseline Seal (Commit 012b0950968e)
                                     ↓
          DEBT-003 Configuration Resolver (P0 Release Blocker)
                                     ↓
     DEBT-002 Ledger Persistence & Snapshot Model (High-Risk Architectural Change)
                                     ↓
            DEBT-001 Concrete ↔ Coq Refinement Simulation Bridge
                                     ↓
           DEBT-007 Gate J Independent Verifier Fuzzing Hardening
                                     ↓
                  DEBT-004 Gate G Sandbox Profile Hardening
                                     ↓
             Phase 5 Single-Gateway Dynamic Load Balancing Engine
                                     ↓
                     Scale & Performance Validation Suite
                                     ↓
               Next Experimental Release Tag (v0.5.0-experimental)
```

---

## 2. PHASE A — HARDENING & STABILIZATION (Target Release: `v0.4.1-experimental`)

### Feature A.1: Configuration Environment Variable Precedence Alignment (P0 Release Blocker)
- **Problem**: Environment variables currently read directly in python code bypass strict Draft 2020-12 schema validation (`DEBT-003`). Because configuration resolution sets security ceilings and sandbox profiles, closing `DEBT-003` is a P0 release blocker.
- **Why Cortex Needs It**: Prevents invalid runtime configurations from corrupting worker initialization or bypassing security ceilings.
- **Architectural Dependency**: `cortex/schemas/v1/configuration.schema.json` & `cortex/tools/cli/`.
- **Security Impact**: Security settings (like max worker bounds or sandbox profiles) are strictly validated before acceptance into TCB state.
- **Formal Verification Impact**: Aligns concrete runtime config state with Coq `RD-F3` config generation/hash fencing theorems.
- **Implementation Complexity**: Low (2-3 engineering days).
- **Expected Performance Impact**: Negligible (evaluated once at boot/reconciliation).
- **Operational Impact**: Eliminates silent fallback defaults; logs clear schema error diagnostics on invalid ENV vars.
- **Required Tests**: `tests/kernel/test_cli_env_precedence.py` (covering 15 boundary test cases).
- **Required Documentation**: Update `docs/guides/cortex-configuration.md`.
- **Release Target**: `v0.4.1-experimental`
- **Blocking Dependencies**: None.

### Feature A.2: Invocation Ledger Persistence, Snapshot Model & Memory Compaction
- **Problem**: `InvocationLedger` stores all historical invocation records in RAM indefinitely (`DEBT-002`). Compacting historical records is a high-risk persistence change, not merely a performance optimization.
- **Why Cortex Needs It**: Enables long-running host gateway processes without memory exhaustion while maintaining logical history $\neq$ physical storage representation.
- **Architectural Dependency**: `cortex/tools/kernel/replica/ledger.py`.
- **Security Impact**: Preserves tamper-evident causal witness hashes via snapshot equation:
  $$\text{Verify}(H_{\text{checkpoint}}, \text{trace}_{\text{after}})$$
  preserving causal chain continuity without deleting logical checkpoints.
- **Formal Verification Impact**: Proves that log pruning preserves rolling SHA-256 state chain monotonicity (`GateF_F4`).
- **Implementation Complexity**: Medium (4-5 engineering days).
- **Expected Performance Impact**: Reduces host RAM footprint by 85% under sustained load.
- **Operational Impact**: Adds configurable `ledger_snapshot_interval` and disk journal rotation.
- **Required Tests**: `tests/conformance/test_replica_ledger_compaction.py`.
- **Required Documentation**: Update `docs/architecture/recovery-and-state.md`.
- **Release Target**: `v0.4.1-experimental`
- **Blocking Dependencies**: Feature A.1.

---

## 3. PHASE B — CONTROL PLANE & PHASE 5 LOAD BALANCING (Target Release: `v0.5.0-experimental`)

### Feature B.1: Concrete-to-Coq Control Plane Refinement Simulation Bridge (DEBT-001)
- **Problem**: Abstract Coq proofs (`Phase4RoutingRefinement.v`) and concrete Python implementations are currently linked empirically (`DEBT-001`).
- **Why Cortex Needs It**: Formally proves that the concrete Python control plane refines the Coq safety kernel.
- **Architectural Dependency**: `verification/Phase4RoutingRefinement.v`.
- **Security Impact**: Highest-value formal verification work; eliminates semantic drift between proof and code.
- **Formal Verification Impact**: Establishes concrete-to-Coq forward simulation refinement:
  $$R(C, M) \land C \to C' \implies \exists M'. M \to^* M' \land R(C', M')$$
- **Implementation Complexity**: High (8-10 engineering days).
- **Expected Performance Impact**: Zero runtime overhead.
- **Required Tests**: Coq compilation (`coqc`) and `coqchk` verification.
- **Release Target**: `v0.5.0-experimental`
- **Blocking Dependencies**: Completion of Phase A hardening.

### Feature B.2: Gate J Verifier Property-Based Fuzzing Engine (DEBT-007)
- **Problem**: The offline evidence verifier is tested against 5 golden bundles, which is insufficient for hostile evidence graphs (`DEBT-007`).
- **Why Cortex Needs It**: Hardens Gate J verifier against adversarial topology attacks.
- **Architectural Dependency**: `cortex/tools/cortex_verifier.py`.
- **Security Impact**: Asserts verifier robustness across 13 adversarial classes: valid, truncated, reordered, duplicated, forked, cyclic, oversized, malformed CBE, unknown schema, invalid signature, invalid root, unknown anchor, resource exhaustion.
- **Formal Verification Impact**: Empirically confirms verifier domain equivalence.
- **Implementation Complexity**: Medium (4-5 engineering days).
- **Expected Performance Impact**: Zero runtime overhead.
- **Required Tests**: Fuzzing suite passing 1,000+ synthetic graph topologies with deterministic verdicts (`VALID`, `INVALID`, `INDETERMINATE`).
- **Release Target**: `v0.5.0-experimental`
- **Blocking Dependencies**: Feature B.1.

### Feature B.3: Single-Gateway Dynamic Load Balancer Engine (`load_balancer.py`)
- **Problem**: Phase 4 router uses static baseline `LEAST_INFLIGHT` placement without soft metric evaluation.
- **Why Cortex Needs It**: Enables dynamic placement based on inflight count, latency EWMA, and caching affinity (`docs/architecture/phase_5_load_balancing_specification.md`).
- **Architectural Dependency**: `cortex/tools/kernel/replica/router.py`, `CandidateResolver`.
- **Security Impact**: Non-authoritative (`Invariant 5.1`); telemetry metrics act strictly as untrusted hints.
- **Formal Verification Impact**: Maps to Coq non-authoritative router refinement (`RD-F5`).
- **Implementation Complexity**: High (8-10 engineering days).
- **Expected Performance Impact**: Decreases average invocation latency by 35% under non-uniform workloads.
- **Operational Impact**: Introduces configurable policies (`LEAST_INFLIGHT`, `WEIGHTED_LEAST_INFLIGHT`, `STATE_AFFINITY`).
- **Required Tests**: Full implementation of test suite `tests/conformance/test_replica_phase_5.py` verifying gates `LB-1` through `LB-14`.
- **Release Target**: `v0.5.0-experimental`
- **Blocking Dependencies**: Feature B.1, Feature B.2, and Phase 4 merge to `main`.

---

## 4. PHASE C — SCALING & REPLICA LIFECYCLE (Target Release: `v0.5.1-experimental`)

### Feature C.1: Dynamic Worker Warm-Pool Allocation & Bounded Autoscaling
- **Problem**: Cold-starting sandboxed worker processes adds start-up latency per worker.
- **Why Cortex Needs It**: Accelerates response times for dynamic burst workloads while maintaining deterministic bounds.
- **Architectural Dependency**: `cortex/tools/kernel/replica/lifecycle.py`.
- **Security Impact**: Autoscaling policy: Unbounded or authority-expanding autoscaling is strictly prohibited. Bounded autoscaling with strict operational constraints (`min_replicas`, `max_replicas`, `scale_up_threshold`, `scale_down_threshold`, `cooldown`, `rate_limits`) is deterministic and allowed.
- **Formal Verification Impact**: Proves capability attenuation during stage transitions (`AuthorityModel.v`).
- **Implementation Complexity**: High (6-8 engineering days).
- **Expected Performance Impact**: Reduces burst invocation latency from 18ms to 1.2ms.
- **Required Tests**: `tests/conformance/test_replica_warm_pool.py`.
- **Release Target**: `v0.5.1-experimental`
- **Blocking Dependencies**: Feature B.3.

---

## 5. PHASE D — DISTRIBUTED SYSTEMS & FEDERATION (Target Release: `v0.6.0-experimental`)

### Feature D.1: Multi-Gateway Raft Consensus & Distributed Lease Fencing (Phase 6)
- **Problem**: Single gateway authority limits system scale to one physical host.
- **Why Cortex Needs It**: Enables multi-node federation, fault-tolerant host gateway clustering, and cross-node state domain fencing.
- **Architectural Dependency**: New `cortex-federation` Go/Rust module, `LeaseManager`.
- **Security Impact**: Distributed lease fencing prevents split-brain capability escalation across gateway nodes.
- **Formal Verification Impact**: Requires new TLA+/Coq formal consensus proofs for multi-gateway lease safety.
- **Implementation Complexity**: Critical / Very High (20-25 engineering days).
- **Release Target**: `v0.6.0-experimental`
- **Blocking Dependencies**: Completion of Phase 5 (`v0.5.0-experimental`).

---

## 6. PHASE E — HARDWARE & RISC-V INTEGRATION (Target Release: `v0.7.0-experimental`)

### Feature E.1: FPGA Synthesis & RISC-V Capability Pipeline Coprocessor (Phase 7)
- **Problem**: Software emulation of STCR capability bounds checks adds CPU cycle overhead.
- **Why Cortex Needs It**: Delivers hardware-enforced capability checking for ultra-low latency execution. Yosys synthesis gate (`DEBT-006`) proves synthesizability ($\text{RTL} \to \text{synthesizable}$) as a distinct evidence class from formal semantics refinement.
- **Architectural Dependency**: `rtl/cortex_stcr_pipeline.sv`, Verilator harness.
- **Security Impact**: Hardware-enforced spatial and temporal capability boundaries directly in CPU pipeline.
- **Implementation Complexity**: Very High (15-20 engineering days).
- **Release Target**: `v0.7.0-experimental`
- **Blocking Dependencies**: `DEBT-006` resolution (Yosys synthesis verification).

---

## 7. PHASE F — ECOSYSTEM & ENTERPRISE INTEGRATION (Target Release: `v1.0.0`)

### Feature F.1: gRPC/HTTP Control Plane API & Enterprise Policy Engine
- **Problem**: External control systems currently interact with Cortex solely via CLI or direct Python API bindings.
- **Why Cortex Needs It**: Provides standardized remote control-plane management for enterprise orchestration platforms.
- **Architectural Dependency**: `cortex/tools/cli/`, OpenAPI / Protobuf schemas.
- **Security Impact**: TLS 1.3 mutual authentication (mTLS) with role-based access control (RBAC).
- **Implementation Complexity**: Medium (8-10 engineering days).
- **Release Target**: `v1.0.0`
- **Blocking Dependencies**: Completion of Phase 6 & P0–P13 production checklist.
