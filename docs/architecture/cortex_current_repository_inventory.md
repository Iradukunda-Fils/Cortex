# Cortex Current Repository Inventory
**Authoritative Clean-Room Physical & Logical Asset Catalogue**  
**Date:** August 22, 2026  
**Repository Baseline SHA:** `db5fd1a` / `00deade` (main: `00deade`)  
**Package Version:** `v0.4.0rc1` (cortex-runtime `0.4.0`)

---

## Executive Summary

This inventory documents the physical and logical structure of the Cortex repository, establishing the trust domain, authority level, runtime role, verification evidence, test coverage, release relevance, and operational status for every component.

---

## 1. Python Kernel Subsystem (`cortex/`)

| Path | Purpose | Trust Domain | Authority Level | Runtime Role | Verification Evidence | Tests | Release Relevance | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `cortex/cbe/` | CBE (Canonical Binary Encoding) deterministic encoder, decoder, normalizer, streaming protocol | TCB (Core Ingestion) | Level 0 | Low-level serialization & canonical hash generation | Gate F Coq (`CBESpec.v`), golden vectors | `tests/test_cbe.py`, `tests/test_streaming.py` | v0.2.0, v0.3.0, v0.4.0 | IMPLEMENTED / PRODUCTION-READY |
| `cortex/tools/kernel/config_resolver.py` | ConfigResolver: ENV/CLI/YAML field-class normalization, precedence resolution, hash generation | TCB (Control Plane) | Level 1 | Multi-source configuration resolution & generation minting | Precedence audit, fsync rename semantics | `tests/kernel/test_cli_env_precedence.py` | v0.4.0 (Issue #30) | IMPLEMENTED-VERIFIED (PR #38) |
| `cortex/tools/kernel/config_admission.py` | ConfigAdmissionEngine: crash-safe generation increments, generation hash fencing | TCB (Control Plane) | Level 1 | Atomic configuration admission and fencing | RD-F3, RD-F4 Coq proofs | `tests/conformance/test_replica_phase_4.py` | v0.4.0 | IMPLEMENTED-VERIFIED |
| `cortex/tools/kernel/replica_manager.py` | CandidateResolver & Worker Lifecycle Supervision (spawn, health, drain, terminate) | TCB (Host Kernel) | Level 1 | Worker pool supervision & state transition tracking | RD-F1, RD-F2, RD-F10 Coq proofs | `tests/conformance/test_replica_phase_4.py` | v0.4.0 | IMPLEMENTED-VERIFIED |
| `cortex/tools/kernel/router.py` | Gateway Router: candidate evaluation, capability containment, load-aware routing | TCB (Gateway) | Level 1 | Non-authoritative worker selection & dispatch planning | RD-F5 Coq proof | `tests/conformance/test_replica_phase_4.py` | v0.4.0 | IMPLEMENTED-VERIFIED |
| `cortex/tools/kernel/lease_manager.py` | LeaseManager: lease minting, state-domain key fencing, generation/hash revalidation | TCB (Gateway) | Level 1 | Spatiotemporal execution lease enforcement | RD-F3, RD-F4, RD-F9, RD-F15 Coq proofs | `tests/conformance/test_replica_phase_4.py` | v0.4.0 | IMPLEMENTED-VERIFIED |
| `cortex/tools/kernel/replica/ledger.py` | InvocationStateLedger: execution state tracking, single-commitment, compaction, recovery classification | TCB (Control Plane) | Level 1 | Durable journal, atomic snapshot compaction & double-actuation prevention | RD-F6, RD-F7, RD-F11..F14 Coq proofs, `test_invocation_ledger_compaction.py` | `tests/kernel/test_invocation_ledger_compaction.py` | v0.4.0, v0.4.1 | IMPLEMENTATION-VERIFIED (Issue #31 Complete) |
| `cortex/tools/kernel/gateway.py` | GatewayDispatcher: complete mediation boundary, token validation, actuation dispatch | TCB (Host Gateway) | Level 1 | Actuation fence & witness token generation | Gate H (21/21), Gate I (7/7) | `tests/conformance/test_gate_h_actuation_boundary.py` | v0.4.0 | IMPLEMENTED-VERIFIED |
| `cortex/tools/kernel/sandbox.py` | WASM / Container sandbox abstraction, process isolation, seccomp filters | Isolated Worker Domain | Level 2 | Sandboxed worker execution environment | Gate G (15/15) isolation tests | `tests/conformance/test_gate_g_adversarial.py` | v0.3.0, v0.4.0 | IMPLEMENTED (Profile B Issue #33 OPEN) |
| `cortex/client.py` | Client API: intent creation, token minting, side-effect submission | Untrusted / Client Domain | Level 3 | Application SDK for Cortex interaction | SDK surface tests | `tests/kernel/test_public_api.py` | v0.2.0, v0.4.0 | IMPLEMENTED / STABLE |
| `cortex/plugin.py` | Plugin SDK: host integration, plugin manifest loading, event routing | Untrusted / Plugin Domain | Level 2 | Plugin lifecycle & callback execution | Import boundary suite | `tests/kernel/test_plugin_contract.py` | v0.2.0, v0.3.0 | IMPLEMENTED / STABLE |
| `cortex/_telemetry/` | Operational telemetry collector, benchmark harnesses, metric models | Host Observability | Level 2 | Metric aggregation & execution profiling | Telemetry regression suite | `tests/regression/test_v020_telemetry_internal.py` | v0.3.0 | IMPLEMENTED / STABLE |
| `cortex/_research/` | Research synthesis, crash semantics characterization, recovery profiling | Research Domain | N/A | Operational evidence generation for v0.3/v0.4 | Operational synthesis reports | `tests/regression/test_v020_crash_semantics.py` | v0.3.0 | COMPLETE / HISTORICAL |

---

## 2. Go Transport Adapter (`cortex-go/`)

| Path | Purpose | Trust Domain | Authority Level | Runtime Role | Verification Evidence | Tests | Release Relevance | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `cortex-go/cbe/` | High-throughput Go CBE encoder/decoder/streaming parser | TCB (Ingestion Layer) | Level 1 | Layer 2 binary framing & stream demuxing | Cross-language equivalence with Python CBE | `cortex-go/tests/streaming_test.go` | v0.3.0 | IMPLEMENTED-VERIFIED |
| `cortex-go/adapter/` | IPC protocol adapter, gRPC/unix-socket bridge | Host Transport | Level 1 | Low-latency socket transport | Conformance suite bridge | `cortex-go/tests/conformance_test.go` | v0.3.0 | IMPLEMENTED-VERIFIED |
| `cortex-go/cmd/gate-e-adapter/` | Binary executable CLI for Go framing adapter | Host Transport | Level 1 | CLI entrypoint for transport daemon | Conformance bridge | `tests/conformance/test_adapter_mutations.py` | v0.3.0 | IMPLEMENTED-VERIFIED |

---

## 3. SystemVerilog STCR Hardware Subsystem (`rtl/`)

| Path | Purpose | Trust Domain | Authority Level | Runtime Role | Verification Evidence | Tests | Release Relevance | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rtl/cortex_stcr_pipeline.sv` | Spatio-Temporal Capability Register (STCR) hardware pipeline logic | Hardware TCB | Level 0 | Hardware-enforced epoch monotonicity & capability traps | `DelegationChainRTL.v` Coq proof, Gate L1/L2 | `tests/conformance/test_conformance_rtl.py` | v0.4.0 | IMPLEMENTED (Yosys Check Issue #37 OPEN) |

---

## 4. Formal Verification Subsystem (`verification/`)

| Path | Purpose | Trust Domain | Authority Level | Runtime Role | Verification Evidence | Tests | Release Relevance | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `verification/AuthorityModel.v` | Core authority logic, capability algebra, delegation semantics | Formal Spec | Level 0 | Core mathematical specification of authority | 0 axioms, 0 admitted, closed context | `tests/conformance/test_conformance_coq.py` | v0.3.0, v0.4.0 | CERTIFIED |
| `verification/Phase4RoutingRefinement.v` | Phase 4 Routing & Dispatch formal refinement (RD-F1..RD-F17) | Formal Spec | Level 0 | Formal proof of Phase 4 safety invariants | 23 theorems, 4 helper lemmas, 0 admitted | `verify_coq_assumptions.py` | v0.4.0 | CERTIFIED (100% Closed Context) |
| `verification/CBESpec.v` | Coq formal model of Canonical Binary Encoding | Formal Spec | Level 0 | CBE serialization soundness specification | Proved determinism & totality | `tests/conformance/test_f4c_totality_determinism.py` | v0.3.0 | CERTIFIED |
| `verification/DelegationChainRTL.v` | Formal mapping between Coq authority model & SystemVerilog RTL STCR | Formal Spec | Level 0 | Hardware-software co-verification boundary | Proved RTL step equivalence | `tests/conformance/test_conformance_rtl.py` | v0.4.0 | IMPLEMENTED (Issue #22 OPEN for universal proof) |

---

## 5. Verification Tools & Test Infrastructure (`tools/`, `tests/`)

| Path | Purpose | Trust Domain | Authority Level | Runtime Role | Verification Evidence | Tests | Release Relevance | Current Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `tools/cortex_verifier.py` | Independent Gate J verifier engine (out-of-band evidence bundle checker) | Verification Domain | Level 3 | Standalone audit tool for evidence bundles | Gate J 12/12 scenarios | `tests/conformance/test_gate_j_independent_verifier.py` | v0.3.0, v0.4.0 | IMPLEMENTED-VERIFIED |
| `tools/assurance/docs_audit.py` | Markdown link integrity, documentation warnings, ADR cross-ref checker | Dev Tooling | N/A | Static documentation audit script | 222 warnings flagged | `python3 tools/assurance/docs_audit.py` | v0.4.0 | IMPLEMENTED (Issue #35 OPEN) |
| `tests/conformance/run_certification.py` | Master certification pipeline (136 automated conformance checks) | Verification Engine | Level 3 | Automated release gate & assurance harness | 136/136 checks passing | Executes full suite | v0.2.0..v0.4.0 | IMPLEMENTED-VERIFIED (100% Pass) |
| `tests/` (341 test cases) | Pytest regression, kernel, conformance, and SDK test suite | Verification Engine | Level 3 | Continuous integration regression safety net | 341/341 tests passing | Executes full suite | v0.2.0..v0.4.0 | IMPLEMENTED-VERIFIED (100% Pass) |

---

## 6. Project Manifests & Configuration Files

| Path | Purpose | Trust Domain | Release Relevance | Current Status |
| :--- | :--- | :--- | :--- | :--- |
| `pyproject.toml` | Build specification, package metadata, dependencies | Build / Packaging | v0.4.0 (`0.4.0`) | VERIFIED |
| `cortex_assurance_manifest.json` | Machine-readable assurance baseline & theorem count ledger | Assurance Management | v0.4.0 | VERIFIED |
| `docs/architecture/assurance_manifest_v1.schema.json` | JSON Schema for Cortex assurance manifests | Assurance Management | v0.4.0 | VERIFIED |
