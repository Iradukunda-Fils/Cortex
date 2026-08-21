# Cortex Contributor Security Boundaries & Open-Source Governance

**Version:** `v1.0.0`  
**Status:** NORMATIVE GOVERNANCE SPECIFICATION  
**Scope:** Open-Source Contribution Classification, Security Boundaries, and Review Hierarchy  

---

## 1. Executive Summary

Cortex is a spatiotemporal authority and semantic verification framework designed for high-concurrency, zero-trust execution. Because security boundaries (Seccomp/Landlock sandboxing, linearizable lease fencing, CBE cryptographic encoding, and Coq-verified evidence models) are critical to system integrity, open-source contributions MUST strictly adhere to the **Contributor Security Governance Framework**.

This document defines:
1. The 4-tier contribution risk taxonomy.
2. The mandatory Security Surface & Reviewer Matrix.
3. The non-negotiable architectural priority hierarchy.
4. Pre-contribution requirements for security-sensitive subsystems.

---

## 2. Non-Negotiable Architectural Priority Hierarchy

Every pull request, contribution, and placement evaluation in Cortex MUST enforce the following strict priority hierarchy:

```
        [1] HARD SECURITY CONSTRAINTS (Seccomp, Landlock, ConfigGen, Caps)
                       ↓
        [2] STATE CONSISTENCY RULES (StateDomainKey serialization, Leases)
                       ↓
        [3] RESOURCE CONSTRAINTS (Cgroups memory ceilings, CPU quotas)
                       ↓
        [4] SOFT PLACEMENT OPTIMIZATION (Inflight count, Latency, Affinity)
                       ↓
        [5] DETERMINISTIC TIE BREAKING (Instance ID lexicographical sort)
```

> [!CAUTION]
> **Priority Invariant:** Soft placement optimization (Tier 4) or telemetry signals MUST NEVER override, attenuate, or bypass Hard Security Constraints (Tier 1) or State Consistency Rules (Tier 2). Any contribution that violates this hierarchy will be immediately rejected.

---

## 3. Contribution Risk Taxonomy (Tiers A through D)

All proposed repository changes and GitHub Issues are classified into one of 4 contribution risk tiers:

```
+-----------------------------------------------------------------------------------+
| TIER A: COMMUNITY-FRIENDLY (Low Risk)                                             |
| Scope: Documentation, CLI UX, Local Schema Validators, Conformance Test Vectors   |
| Review: Standard Maintainer Code Review                                           |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| TIER B: MAINTAINER-REVIEWED SYSTEMS (Medium Risk)                                 |
| Scope: Unprivileged Routing Policies, Local Queues, Observability, Telemetry      |
| Review: Two Core Maintainer Approvals                                             |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| TIER C: SECURITY-REVIEW-REQUIRED (High Risk / Advanced)                           |
| Scope: PyO3 Rust FFI Bindings, Seccomp BPF, Landlock, Recovery, IPC Framing       |
| Review: Core Maintainer + Security Reviewer + Fuzzing & Sanitizer Audits          |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| TIER D: ARCHITECTURE & RFC-ONLY (Critical Core / Locked)                          |
| Scope: Multi-Gateway Consensus, Lease Authority, Coq Proofs, STCR RTL Pipeline    |
| Review: Formal RFC Proposal + Principal Architect Sign-off                        |
+-----------------------------------------------------------------------------------+
```

---

## 4. Security Surface & Reviewer Matrix

For every GitHub Issue or Pull Request, contributors MUST specify the affected **Security Surface**, **Required Reviewers**, **Allowed File Scope**, and **Mandatory Assurance Gates**:

| Contribution Surface | Risk Tier | Security Surface | Required Reviewers | Allowed File Scope | Mandatory Assurance Gates |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Documentation & Guides** | `Tier A` | `None` | 1 Maintainer | `docs/**`, `README.md` | `docs_audit.py` PASS |
| **CLI & UX Utilities** | `Tier A` | `None` | 1 Maintainer | `cortex/tools/cli/**` | `ruff`, `pyright`, unit tests |
| **Local Config Resolver** | `Tier A` | `Configuration` | 1 Maintainer | `cortex/tools/config/**` | `CFG-01`..`CFG-05` vectors |
| **Example Plugins** | `Tier A` | `None` | 1 Maintainer | `examples/plugins/**` | Profile A sandbox compliance |
| **Unprivileged Routing** | `Tier B` | `Routing` | 2 Maintainers | `cortex/tools/kernel/replica/router.py` | `RD-1`..`RD-24` suite PASS |
| **Load Balancing Policies**| `Tier B` | `Routing` | 2 Maintainers | `cortex/tools/kernel/replica/load_balancer.py` | `LB-1`..`LB-14` suite PASS |
| **Rust CBE FFI Bindings** | `Tier C` | `CBE / Memory` | Maintainer + Security Reviewer | `crates/cortex-cbe-py/**` | Cross-runtime parity + Fuzzing |
| **Sandbox & Seccomp** | `Tier C` | `Sandbox` | Maintainer + Security Reviewer | `cortex/tools/sandbox/**` | Gate G Complete Mediation |
| **Lease & Ledger Core** | `Tier C` | `Lease / Ledger` | Maintainer + Security Reviewer | `cortex/tools/kernel/replica/lease.py`, `ledger.py` | Monotonic epoch & recovery tests |
| **Multi-Gateway Consensus**| `Tier D` | `Consensus` | RFC Review Only | `docs/architecture/rfc_*` | Architecture Board Sign-off |
| **Formal Proofs (Coq)** | `Tier D` | `Formal Proof` | Formal Verification Reviewer | `coq/**` | Coq Proof Assistant Compile |

---

## 5. Security Boundary Guidelines for Specific Contributor Domains

### 5.1 Configuration Resolution Boundaries
- **Local Resolution Only:** Configuration schema validation MUST load repository-pinned schema files locally (`docs/architecture/configuration_schema_reference.md` / `cortex/schemas/v1/configuration.schema.json`).
- **No Runtime Network Requests:** The schema `$id` URI (`https://cortex.security/...`) is strictly a canonical URI identity string. Configuration parsers MUST NOT issue HTTP/DNS network requests at runtime.

### 5.2 FFI & Foreign Code Boundaries (Rust / PyO3)
- Contributions introducing C-FFI or Rust PyO3 bindings cross a critical process memory boundary.
- All FFI implementations MUST include:
  1. Explicit memory ownership and lifetime assertions.
  2. Panic-unwind boundary handling (`std::panic::catch_unwind`) to prevent process termination.
  3. Input length and buffer boundary checks prior to unsafe memory operations.
  4. Fuzzing test harnesses (`cargo fuzz`) demonstrating 0 crashes over $10^7$ iterations.

### 5.3 Example Plugin Guidelines
- Community-contributed example plugins MUST demonstrate **safe sandbox-first workloads**:
  - `SQLite Read-Only Analyzer` (read-only filesystem queries).
  - `AST Formatter & Refactoring Engine` (pure document transformation).
  - `Local Static Code Analyzer` (in-memory data processing).
- Plugins requiring network access, raw sockets, or web scraping MUST NOT be submitted as beginner examples; they belong to Tier C security-reviewed integrations.
