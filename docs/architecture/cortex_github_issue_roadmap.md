# Cortex Master GitHub Issue Roadmap

> **Governance Status**: `NORMATIVE GITHUB ISSUE BACKLOG`  
> **Baseline Release Tag**: `v0.4.0-experimental` (`v0.4.0rc1`)  
> **Release Commit SHA**: `012b0950968e`  
> **Current `main` SHA**: `00deade`  
> **Assurance Manifest SHA-256**: `d748ec7a5f52eabfbe703e057b5b9d41f37636695453df05b2fa201c881ccf56`  
> **Total Open Remote Issues**: 12 Open Issues (11 Technical / Architectural, 1 Community Onboarding)  
> **Total Open PRs**: 0 (PR #27 merged into `main`)  

---

## 1. Master Multi-Track Execution Architecture & DAG

```
                      v0.4.0 EXPERIMENTAL BASELINE (Commit 012b0950968e)
                                       │
                                       ▼
                   Configuration Precedence (Issue #30) [P0 BLOCKER]
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼ (SOFT-SEQUENCING)
              Ledger Snapshot (#31)         Coq Refinement (#32)
              [P0 INTEGRITY BLOCKER]        [PARALLEL FORMAL]
                        │                             │
                        └──────────────┬──────────────┘
                                       ▼
                         Phase 5 Load Balancer (#34)
                                       │
                                       ▼
                            Scale & Performance Suite
                                       │
                                       ▼
                          v0.5.0-experimental RELEASE



PARALLEL ASSURANCE TRACKS (Non-Blocking for Phase 5 Implementation)
─────────────────────────────────────────────────────────────────────────────
Security Fuzzing Track:    Issue #36 (Gate J 13-Class Fuzzing Engine)
Formal Assurance Track:    Issue #21 (F4c Universal Coq Equivalence)
Hardware Assurance Track:  Issue #22 (SV<->Coq Extraction) + Issue #37 (Yosys Synthesis)
Future Profile Track:      Issue #33 (WASM Sandbox Profile B)
Engineering Hygiene Track: Issue #35 (Docs Audit Warning Cleanup)
```

---

## 2. Machine-Readable Issue Dependency Specifications

### Issue #30: Configuration Precedence (`DEBT-003`)
- **Depends-On**: Baseline release tag `v0.4.0-experimental` (`012b0950968e`)
- **Blocks**: Issue #34 (Phase 5 Load Balancer Engine)
- **Soft-Sequence**: Issue #31 (Ledger Compaction)
- **Parallel-With**: Issues #35, #36, #37
- **Release-Required-For**: `v0.4.1-experimental` & `v0.5.0-experimental`
- **GitHub Link**: [#30](https://github.com/Iradukunda-Fils/Cortex/issues/30)

### Issue #31: InvocationLedger Snapshot Model (`DEBT-002`)
- **Depends-On**: Baseline `v0.4.0`
- **Blocks**: `v0.4.1-experimental` Release Sign-off
- **Soft-Sequence**: Issue #30
- **Parallel-With**: Issues #32, #34 (Does not block Phase 5 coding)
- **Release-Required-For**: `v0.4.1-experimental` & `v0.5.0-experimental`
- **GitHub Link**: [#31](https://github.com/Iradukunda-Fils/Cortex/issues/31)

### Issue #32: Concrete-to-Coq Forward Simulation Refinement (`DEBT-001`)
- **Depends-On**: Baseline `v0.4.0`
- **Blocks**: `v0.5.0-experimental` Formal Assurance Sign-off
- **Soft-Sequence**: Issue #30
- **Parallel-With**: Issue #34 (Coding proceeds in parallel with formal proof)
- **Release-Required-For**: `v0.5.0-experimental`
- **GitHub Link**: [#32](https://github.com/Iradukunda-Fils/Cortex/issues/32)

### Issue #34: Single-Gateway Dynamic Load Balancer Engine (`load_balancer.py`)
- **Depends-On**: Issue #30, PR #27 Merged (`00deade`)
- **Blocks**: Scale & Performance Suite, `v0.5.0-experimental`
- **Soft-Sequence**: Issues #31, #32
- **Parallel-With**: Issues #21, #22, #33, #35, #36, #37
- **Release-Required-For**: `v0.5.0-experimental`
- **GitHub Link**: [#34](https://github.com/Iradukunda-Fils/Cortex/issues/34)

### Issue #36: Gate J 13-Class Property Fuzzing Engine
- **Depends-On**: None
- **Blocks**: Gate J Security Sign-off
- **Soft-Sequence**: None
- **Parallel-With**: Issues #30, #31, #32, #34
- **Release-Required-For**: Security Track (`v0.5.0-experimental`)
- **GitHub Link**: [#36](https://github.com/Iradukunda-Fils/Cortex/issues/36)

### Issue #21: F4c Verifier Domain Universal Equivalence Coq Proof
- **Depends-On**: None
- **Blocks**: Formal Equivalence Sign-off
- **Soft-Sequence**: None
- **Parallel-With**: Issues #30, #31, #32, #34
- **Release-Required-For**: Formal Track (`v0.5.0-experimental`)
- **GitHub Link**: [#21](https://github.com/Iradukunda-Fils/Cortex/issues/21)

### Issue #33: WASM Sandbox Profile B Certification Suite (`DEBT-004`)
- **Depends-On**: None
- **Blocks**: WASM Execution Profile
- **Soft-Sequence**: None
- **Parallel-With**: Issues #30, #31, #32, #34
- **Release-Required-For**: Future Profile Track (Non-blocking for Phase 5)
- **GitHub Link**: [#33](https://github.com/Iradukunda-Fils/Cortex/issues/33)

### Issue #22: SystemVerilog RTL Step Extraction Coq Proof
- **Depends-On**: None
- **Blocks**: RTL Refinement Sign-off
- **Soft-Sequence**: None
- **Parallel-With**: Issues #30, #31, #34, #37
- **Release-Required-For**: Hardware Track (`v0.6.0-experimental`)
- **GitHub Link**: [#22](https://github.com/Iradukunda-Fils/Cortex/issues/22)

### Issue #37: SystemVerilog STCR Pipeline Yosys Synthesis Gate (`DEBT-006`)
- **Depends-On**: None
- **Blocks**: FPGA Synthesizability Gate
- **Soft-Sequence**: None
- **Parallel-With**: Issues #22, #30, #34
- **Release-Required-For**: Hardware Track (`v0.6.0-experimental`)
- **GitHub Link**: [#37](https://github.com/Iradukunda-Fils/Cortex/issues/37)

### Issue #35: Documentation Audit Warning Cleanup (`DEBT-005`)
- **Depends-On**: None
- **Blocks**: Documentation Warning Metric
- **Soft-Sequence**: None
- **Parallel-With**: All Issues
- **Release-Required-For**: Engineering Hygiene (`v0.4.1-experimental`)
- **GitHub Link**: [#35](https://github.com/Iradukunda-Fils/Cortex/issues/35)

---

## 3. Pull Request Status

- **PR #27**: `docs(design): Phase 5 Load-Balancing Policy Specification`  
  - State: **`MERGED`** into `main` (Squashed commit `00deade`)  
  - Open PRs Remaining: **0**
