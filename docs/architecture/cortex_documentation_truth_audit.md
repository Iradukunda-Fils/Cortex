# Cortex Documentation Truth & Baseline Inventory Audit

> **Release Baseline**: `v0.7.0rc1` | **Baseline Type**: Hardened Pre-Release Candidate  
> **Post-Audit Fixes**: CBE Allocation Defense, Process Group Signal Termination, CAS Evidence Ownership Fix  
> **Branch**: `feat/external-effects-subsystem` | **Audit Date**: 2026-09-04

---

## 1. Executive Summary

This audit establishes the formal documentation baseline for the Cortex platform. Every architectural claim, formal proof count, test metric, and configuration reference has been reconciled against the actual source code, test suites, formal verification modules, and kernel binaries.

---

## 2. Repository Metadata Baseline

| Property | Actual Value | Evidence Source |
| :--- | :--- | :--- |
| **Branch** | `feat/external-effects-subsystem` | `git status` |
| **Version (Python)** | `0.7.0rc1` | `pyproject.toml` |
| **Version (Rust)** | `0.1.0` | `cortex-emulator/Cargo.toml` |
| **Release Tag Target** | `v0.7.0rc1` | Post-Audit Release Identity |
| **Coq Verification Modules** | 29 `.v` source modules | `verification/*.v` |
| **Conformance Tests** | 222 passing tests | `tests/conformance` |
| **Audited Source Baseline** | `Audited Source == Tested Source == Built Artifact == Tagged Release` | Immutable Baseline Invariant |

---

## 3. Comprehensive Documentation Inventory & Classification

All repository documentation has been inventoried and classified into five authority tiers:

### 3.1. AUTHORITATIVE
Documents that represent active, verified contracts of the system:
* `docs/architecture/cortex_system_architecture_current.md`
* `docs/architecture/cortex-developer-contract.md`
* `docs/architecture/cbe_transport_architecture.md`
* `docs/architecture/external_adapter_architecture.md`
* `docs/architecture/gate_a_physical_execution_isolation.md`
* `docs/architecture/resource-authority.md`
* `docs/release/v0.7.0rc2_release_manifest.md`
* `pyproject.toml`

### 3.2. REFERENCE
Technical specifications and structural references:
* `docs/architecture/canonical-serialization.md`
* `docs/architecture/invocation_ledger_compaction_design.md`
* `docs/architecture/object_transfer_and_shared_resource_model.md`
* `docs/architecture/replica_scaling_specification.md`
* `docs/architecture/threat_model.md`
* `docs/spec/*`
* `cortex_assurance_manifest.json`

### 3.3. HISTORICAL
Milestones, retrospective audits, and historical logs:
* `docs/history/*`
* `docs/release/v0.3.0-experimental.md`
* `docs/operations/v0.2-dogfood-report.md`
* `master_plan.md`

### 3.4. EXPERIMENTAL / EVIDENCE-GATED
Research papers and unbenchmarked proposals:
* `research/*`
* `docs/architecture/cortex_scalability_envelope.md` (*reclassified from authoritative*)

### 3.5. DEPRECATED / CONFLICTING
Superceded documents containing stale numbers or inaccurate polyglot claims:
* Historical claims of "10 Coq formal proof invariants pass" (*superseded by 29 Coq proof modules*).
* Claims of "in-process native multi-language plugins" (*superseded by Python-only `BasePlugin` native interface*).

---

## 4. Documentation-to-Code Claim Tracing Matrix (Refined Evidence Taxonomy)

| Architectural Feature / Claim | Claim Level | Detailed Evidence Taxonomy | Evidence Reference |
| :--- | :--- | :--- | :--- |
| **CortexClient API** | High-level orchestration | `Code Implemented` + `Runtime Verified` | `cortex/client.py` |
| **ResourceAuthority** | Capacity admission & vector accounting | `Coq Model Proven` + `Concrete Implementation Tested` + `Refinement Proven` | `cortex/tools/kernel/resource_authority.py`, `verification/Phase8ResourceAuthorityConcrete.v` |
| **GatewayAuthorizationGate** | HMAC fencing & capability check | `Coq Model Proven` + `Concrete Implementation Tested` | `cortex/tools/kernel/effect_gateway.py`, `verification/GateF_F2_1_RestrictCap.v` |
| **WorkerSupervisor** | Process spawning, cgroup v2 & netns | `Code Implemented` + `Runtime Verified` (Kernel Verified when unshare/cgroup permissions exist) | `cortex/tools/kernel/enforcement/supervisor.py` |
| **Profile A Landlock Sandbox** | Linux Landlock LSM & 2-stage PID 1 fork | `Code Implemented in Rust` + `Runtime Verified in Rust Tests` (Profile A Emulator Path) | `cortex-emulator/src/sandbox.rs` |
| **EffectExecutionPipeline** | 8-stage effect execution chain | `Code Implemented` + `Runtime Verified` | `cortex/tools/kernel/effect_runtime.py` |
| **ResourceContract Adapters** | Decoupled adapter execution | `Code Implemented` + `Runtime Verified` | `cortex/tools/kernel/adapter_contract.py`, `cortex/tools/kernel/adapters/mcp_adapter.py` |
| **ContentAddressableStore (CAS)** | SHA-256 evidence spooling & owner check | `Code Implemented` + `Runtime Verified` (Authoritative Pipeline Ownership) | `cortex/tools/kernel/effect_runtime.py` |
| **WAL & Crash Recovery** | Persistent write-ahead log & recovery | `Coq Model Proven` + `Concrete Implementation Tested` | `verification/Phase6WALSafety.v`, `cortex/tools/kernel/replica/ledger.py` |
| **Canonical Binary Encoding (CBE)** | Tagged binary serialization & NFC check | `Coq Spec Model Proven` + `Python/Go/Rust Implementations Tested` + `Cross-Lang Conformance Tested` | `cortex/cbe/*`, `cortex-go/cbe/*`, `cortex-emulator/src/cbe.rs` |

---

## 5. Summary of Corrected Contradictions & Audit Fixes

1. **RC Identity Baseline Reconciled**: Audit discovered low-level security and correctness defects in `v0.7.0rc1`. Fixes were applied to form the hardened `v0.7.0rc2` release candidate identity.
2. **Evidence Taxonomy Refined**: Replaced broad labels like "VERIFIED IN KERNEL" with explicit 4-tier taxonomy (`Code Implemented`, `Runtime Verified`, `Kernel Verified`, `Deployment Path Guaranteed`).
3. **Coq Proof Hierarchy Refined**: Explicitly separated `Coq Model Proven`, `Concrete Implementation Tested`, and `Concrete-to-Model Refinement Proven`.
4. **CBE Multi-Language Taxonomy Refined**: Separated formal CBE spec proof from language-specific decoders (Python, Go, Rust) and cross-language conformance suite.
5. **Bounded Metric Definitions**: Reclassified performance and memory metrics to `Measured Benchmark Envelope` (e.g., `467.39 B/effect under benchmark workload`).
