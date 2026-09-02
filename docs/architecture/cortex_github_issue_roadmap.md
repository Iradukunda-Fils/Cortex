# Cortex Master GitHub Issue Roadmap (v1.8.0-AUDITED)

> **Governance Status**: `NORMATIVE GITHUB ISSUE ROADMAP & DEPENDENCY SPECIFICATION`  
> **Baseline Version**: `v1.8.0-AUDITED`  
> **Repository SHA**: `2e6f4cc` (`main`)  
> **Reconciliation Governance Rule**: $\boxed{ \text{Remote Issue State} \leftrightarrow \text{Repository Truth} \leftrightarrow \text{Business Goal} }$  
> **Classification Taxonomy**: $\boxed{ \text{KEEP} \mid \text{CLOSE} \mid \text{UPDATE} \mid \text{SPLIT} \mid \text{SUPERSEDED} \mid \text{NEW} }$  
> **Core Product Value Proposition**: $\boxed{ \text{Worker has intent} \quad \text{Authority decides} \quad \text{Kernel enforces} \quad \text{Adapter executes} }$

---

## 1. Remote Inventory & Discrepancy Reconciliation

### 1.1 Remote Inventory Verification
- **Total Remote Issue Count**: 49 issues
- **Highest Issue Number**: #58
- **Issue Number Range**: 1..58
- **Missing Issue Numbers (9)**: `#24, #26, #27, #28, #29, #38, #39, #40, #51` (Skipped or PR-converted during GitHub creation)
- **OPEN Issues (4)**: `#19, #23, #35, #37`
- **CLOSED Issues (45)**: `#1..#18, #20..#22, #25, #30..#34, #36, #41..#50, #52..#58`

### 1.2 Open Issue Classification Matrix

| Issue | Title | Classification | Business Value & Acceptance Criterion | Governing Release Target |
| :---: | :--- | :---: | :--- | :---: |
| **#23** | External Security Review & Readiness | **KEEP** | **Current Governing External-Signoff Gate**: Third-party review report + P0-P13 checklist. | `v1.0.0` |
| **#35** | Resolve doc hyperlink & style warnings | **KEEP** | Low-priority documentation hygiene. `docs_audit.py` warning count resolution. | `v0.4.1` |
| **#37** | Yosys synthesis gate for STCR pipeline | **KEEP** | Hardware Assurance Track only. Synthesizability check for FPGA targets. | `v0.6.0-hardware` |
| **#19** | Newcomer contribution path & guides | **KEEP** | Open-source ecosystem adoption. Curate 5 `good first issue` candidates. | `v1.0-open` |

### 1.3 Supersession Architecture Decision: Issue #33
- **Original Scope**: WASM Profile B Sandbox Filters
- **Status**: **SUPERSEDED** (Not completed as WASM C-JIT)
- **Architectural Decision**: Matured to **Native Linux Kernel Containment** (`unshare(CLONE_NEWUSER | CLONE_NEWNET)` + Landlock LSM + `PR_SET_NO_NEW_PRIVS` in `sandbox.rs`).
- **Rationale**: Host-native Linux containerization provides lower latency, direct syscall filtering via Seccomp/Landlock, and physical NetNS default-deny isolation without requiring embedded WASM execution.

### 1.4 Formal Proofs vs. Product/Security Obligations

$$\boxed{\text{Phase 8.0 Machine-Checked Formal Proofs (CLOSED)}} \quad \neq \quad \boxed{\text{External Security Sign-off & Physical Containment Gates (ACTIVE)}}$$

- **Formal Assurance**: $P_1 \dots P_{14}$ resource authority safety invariants and forward simulation ($R(C_{\text{Python}}, A_{\text{Coq}})$) are 100% machine-checked in Coq with 0 axioms and 0 admits.
- **Product & Deployment Assurance**: Issue #23 third-party audit and physical host containment limitations remain active operational deployment boundaries.

---

## 2. Release Progression & Baseline Alignment

| Track / Capability | Introduced In | Current Baseline | Governing Release Target | Release Impact & Role |
| :--- | :---: | :---: | :---: | :--- |
| **OSS Foundation & Governance** | `v0.2.1` | `v0.2.1` | `v0.2.1` (CLOSED) | Apache-2.0, API stability policy. |
| **Developer Experience & Tooling** | `v0.2.x` | `v0.2.x` | `v0.2.x` (CLOSED) | CLI error standardization, SDK import boundaries. |
| **Multi-Process Runtime & Research** | `v0.3.0` | `v0.3.0` | `v0.3.0` (CLOSED) | Process supervisor, runtime telemetry. |
| **Documentation & Style Audit** | `v0.4.1` | `v0.4.1` | `v0.4.1` (OPEN) | Non-fatal doc style warnings (#35). |
| **Load Balancing & WAL Ledger** | `v0.5.0` | `v0.5.0` | `v0.5.0` (CLOSED) | Dynamic load balancer, persistent WAL journal. |
| **Formal Refinement & Proofs** | `v0.6.0` | `v0.6.0` | `v0.6.0` (CLOSED) | Phase 8.0 Coq forward simulation & TLA+ models. |
| **Hardware Track (STCR Pipeline)** | `v0.6.0` | `v0.6.0` | `v0.6.0-hardware` (OPEN) | Yosys synthesis check (#37). |
| **External Effects & Physical Sandbox** | `v0.5.0` | `v0.5.0` | `v0.5.0` (CLOSED) | Physical NetNS + Landlock LSM (Gates B.1–B.4). |
| **External Security Review** | `v1.0.0` | In-Progress | `v1.0.0` (OPEN) | Third-party review & production clearance (#23). |


---

## 2. Machine-Readable Issue Dependency Specifications

### Issue #41: CBE Protocol-Derived Decoder Memory Bound
- **Status**: `CLOSED_VALID`
- **Priority**: P0 Security Blocker
- **Depends-On**: Baseline release `main` (`00deade`)
- **Blocks**: Issue #42, Issue #43, `v0.4.1-experimental`
- **Release Target**: `v0.4.1-experimental`
- **Research Spec**: `docs/architecture/cbe_transport_architecture.md`
- **Coq Formal Proof**: `CBESpec.v` (`cbe_stream_buffer_bounded_safety`)
- **Commit Evidence**: `df0fa55`

### Issue #42: Canonical ObjectRef Data Plane & Opaque Locators
- **Status**: `CLOSED_VALID`
- **Priority**: P1 Target
- **Depends-On**: Issue #41
- **Blocks**: Data plane large object streaming
- **Parallel-With**: Issue #43
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/object_transfer_and_shared_resource_model.md`
- **Coq Formal Proof**: `GateF_F4_EvidenceRefinement.v` (`object_ref_hash_integrity`)
- **Commit Evidence**: `8be0531`

### Issue #43: Canonical ResourceContract & Ephemeral Context
- **Status**: `CLOSED_VALID`
- **Priority**: P1 Target
- **Depends-On**: Issue #41
- **Blocks**: Issue #44
- **Parallel-With**: Issue #42
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/external_adapter_architecture.md`
- **Coq Formal Proof**: `Phase4RoutingRefinement.v` (`rd_f1_eligibility_safety`)
- **Commit Evidence**: `df0fa55`

### Issue #44: Authoritative Gateway HMAC Idempotency Engine
- **Status**: `CLOSED_VALID`
- **Priority**: P1 Target
- **Depends-On**: Issue #43
- **Blocks**: Issue #45
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/cortex_system_architecture_specification.md`
- **Coq Formal Proof**: `GateL1_EpochMonotonicity.v` (`hmac_idempotency_monotonic_epoch`)
- **Commit Evidence**: `df0fa55`

### Issue #45: Effect Reconciliation Engine & Layered Quarantine
- **Status**: `CLOSED_VALID`
- **Priority**: P1 Target
- **Depends-On**: Issue #44
- **Blocks**: Issue #34 (Phase 5 Load Balancer)
- **Release Target**: `v0.5.0-experimental`
- **Research Spec**: `docs/architecture/worker_execution_model.md`
- **Coq Formal Proof**: `Phase4RoutingRefinement.v` (`rd_f6_unadmitted_durable_safety`)
- **Commit Evidence**: `6277eba`

### Issue #34: Single-Gateway Dynamic Load Balancer Engine (`load_balancer.py`)
- **Status**: `CLOSED_VALID`
- **Priority**: P2 Feature
- **Depends-On**: Issue #45
- **Blocks**: Scale & Performance Suite
- **Release Target**: `v0.5.0-experimental`
- **Commit Evidence**: `ad44242`

---

## 4. Phase 7 Issue Dependency Hierarchy (7.0–7.7b) — ALL CLOSED

```
                            PHASE 7 DEPENDENCY HIERARCHY
                                         │
        Phase 7.0: Resource Algebra Specification (Research Note 18) [CLOSED]
                                         │
                                         ▼
        Phase 7.1: Reservation FSM & Linearization (Research Note 19) [CLOSED]
                                         │
                                         ▼
        Phase 7.2: Reservation Coq Safety Model (Phase7Reservation.v) [CLOSED / MACHINE-CHECKED]
                                         │
                                         ▼
        Phase 7.3: Python Resource Authority & Refinement R(C, A) [CLOSED / IMPLEMENTATION-VERIFIED]
                                         │
                                         ▼
        Phase 7.4: TLA+ Distributed Authority Model (6M+ states) [CLOSED / MODEL-CHECKED]
                                         │
                                         ▼
        Phase 7.5: Enforcement Composition Gate [CLOSED / RUNTIME-VERIFIED]
                                         │
                                         ▼
        Phase 7.6: Resource-Aware Scheduler Engine [CLOSED / BENCHMARKED]
                                         │
                                         ▼
        Phase 7.7a: Distributed Placement Model [CLOSED / LOGICAL SIMULATION]
                                         │
                                         ▼
        Phase 7.7b: Autoscaling Policy Engine [CLOSED / ADVERSARIALLY TESTED]
```

---

## 5. Open Issue Classification Audit (v1.7.0-RECONCILED)

> **Classification Taxonomy**: $\boxed{ \text{KEEP} \mid \text{CLOSE} \mid \text{UPDATE} \mid \text{SPLIT} \mid \text{SUPERSEDED} \mid \text{NEW} }$

### Issue #23 — External Security Review & P0-P13 Production Readiness
- **Classification**: **KEEP**
- **Implementation State**: Internal physical containment (Gates B.1–B.4) and formal proofs are complete. Third-party audit not yet engaged.
- **Acceptance Criterion**: Independent third-party security audit sign-off report.
- **Evidence**: 602 tests passing, 0 axioms/admits in Coq, Landlock + NetNS physically enforced.
- **Business Relevance**: Required for public `v1.0.0` release confidence. No self-audit substitutes for external review.
- **Release Impact**: **P0 blocker for `v1.0.0`**. All other work may proceed in parallel.
- **Decision**: $\boxed{\text{KEEP — v1.0.0 production gate, cannot be closed by internal evidence alone.}}$

### Issue #35 — Resolve 228 Documentation Hyperlink/Formatting Warnings
- **Classification**: **KEEP**
- **Implementation State**: `docs_audit.py` reports 228 warnings, 0 failures. All warnings are non-structural (hyperlinks, anchors, formatting).
- **Acceptance Criterion**: `docs_audit.py` returns 0 warnings.
- **Evidence**: Current verification gate passes (`RESULT: PASS`), but warning count is non-zero.
- **Business Relevance**: Developer experience and documentation quality for open-source consumers.
- **Release Impact**: Low priority. Non-blocking for `v0.5.0` or `v1.0.0`.
- **Decision**: $\boxed{\text{KEEP — Low priority documentation hygiene. Target: v0.4.1 backlog.}}$

### Issue #37 — Yosys Synthesis Gate for SystemVerilog STCR Pipeline
- **Classification**: **KEEP**
- **Implementation State**: `rtl/cortex_stcr_pipeline.sv` is Verilator-simulated but lacks Yosys synthesis CI.
- **Acceptance Criterion**: `make synth-check` passes in CI with zero synthesis errors.
- **Evidence**: RTL-to-Coq trace bridge tests pass (`tests/conformance/test_conformance_rtl.py`).
- **Business Relevance**: Required only for physical FPGA/ASIC deployment targets. Non-blocking for software releases.
- **Release Impact**: Hardware assurance track only. Non-blocking for `v0.5.0`, `v0.6.0`, or `v1.0.0`.
- **Decision**: $\boxed{\text{KEEP — Hardware track only. Deferred until FPGA deployment is commercially justified.}}$

### Issue #19 — Newcomer Contribution Path & Onboarding Documentation
- **Classification**: **KEEP**
- **Implementation State**: No good-first-issue curation performed yet.
- **Acceptance Criterion**: At least 5 issues tagged `good first issue` with explicit "How to Solve" instructions.
- **Evidence**: Repository has `CONTRIBUTING.md` but no curated onboarding issues.
- **Business Relevance**: Enables community growth for open-source ecosystem.
- **Release Impact**: Non-blocking. Target: pre-`v1.0` open-source launch.
- **Decision**: $\boxed{\text{KEEP — Community track. Schedule before public v1.0 open-source launch.}}$

---

## 6. Closed Issue Audit — Business Challenge Against Old Assumptions

> **Audit Rule**: Does this closed issue still describe what Cortex actually needed? Was the closure evidence-backed?

| Issue | Title | Closed State | Challenge Result |
| :---: | :--- | :--- | :--- |
| #33 | WASM Profile B Sandbox Filters | `CLOSED` | **SUPERSEDED**: Architecture matured from WASM sandbox to native Linux NetNS + Landlock (Gates B.2/B.4). WASM Profile B remains a future experimental track, not a current requirement. Closure valid — the security sandbox requirement is now satisfied by physical kernel enforcement. |
| #36 | Gate J 13-Class Property-Based Fuzzing | `CLOSED` | **Valid closure**. Adversarial test corpus covers mutation immunity, CBE conformance, and streaming conformance. Full fuzzing engine is a future hardening track, not a current business requirement. |
| #32 | Concrete-to-Coq Forward Simulation | `CLOSED` | **Valid closure**. `Phase8ResourceAuthorityConcrete.v` with 0 axioms/0 admits proves forward simulation $R(C_{Python}, A_{Coq})$. |
| #52–#58 | Phase 8.0 Formal Proof Obligations | `CLOSED` | **Valid closure**. All 7 proof obligations machine-checked in Coq. |
| #34 | Phase 5 Dynamic Load Balancer | `CLOSED` | **Valid closure**. `load_balancer.py` implemented and benchmarked. |
| #46–#50 | Phase 5–7 Formal Models & Benchmarks | `CLOSED` | **Valid closure**. Coq proofs, TLA+ models (6M+ states), and scheduler benchmarks all evidence-backed. |
| #41–#45 | External Effects Pipeline (CBE→ObjectRef→Gateway→Reconciliation) | `CLOSED` | **Valid closure**. Full pipeline implemented, tested, and verified through Gate B.1–B.4 hardening. |

---

## 7. Deferred Work — Evidence-Gated Future Milestones

> **Rule**: Do not create issues simply to make the backlog look comprehensive. Create an issue only when there is a real unresolved requirement, measurable acceptance criterion, and clear owner/release relevance.

| Deferred Item | Measurable Trigger to Activate | Business Question |
| :--- | :--- | :--- |
| **B.2.4: Controlled External Egress** | A plugin requires authorized outbound network to a specific external endpoint (e.g., `api.github.com:443`). | Who needs per-destination egress? Is there a real user requesting MCP-to-internet capability? |
| **B.3.4: Cross-Node Distributed Fencing** | Single-node deployment ceiling is exceeded; multi-node lease coordination is required. | Is there a deployment scenario requiring >1 Gateway node today? B.3.1 benchmarks show NO CHANGE REQUIRED on single node. |
| **Distributed Sharding** | Measured evidence that single-node throughput is insufficient for the target workload. | The scheduler benchmarks show adequate throughput. Do not implement until load testing proves a bottleneck. |
| **WASM Profile B Sandbox** | A use case requires running untrusted code without native Linux kernel isolation (e.g., cloud-hosted multi-tenant without root). | Is there a non-Linux deployment target that cannot use NetNS + Landlock? |
