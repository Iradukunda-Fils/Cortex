# Cortex Contributor Security Boundaries & Open-Source Governance

**Version:** `v1.1.0`  
**Status:** NORMATIVE GOVERNANCE SPECIFICATION  
**Scope:** Open-Source Contribution Classification, File-Path Security Rules, and Review Hierarchy  

---

## 1. Executive Summary

Cortex is a spatiotemporal authority and semantic verification framework designed for high-concurrency, zero-trust execution. Because security boundaries (Seccomp/Landlock sandboxing, linearizable lease fencing, CBE cryptographic encoding, configuration resolution, and Coq-verified evidence models) are critical to system integrity, open-source contributions MUST strictly adhere to the **Contributor Security Governance Framework**.

This document defines:
1. The 4-tier contribution risk taxonomy.
2. The file-path based change classification matrix.
3. The mandatory ARCHITECTURE-LOCKED protected-area policy.
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
| Scope: Documentation, CLI UX Utilities, Standalone Example Plugins, Test Fixtures |
| Review: 1 Core Maintainer Approval                                                |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| TIER B: MAINTAINER-REVIEWED SYSTEMS (Medium Risk / Control Plane)                 |
| Scope: Configuration Resolver & Schema Engine, Unprivileged Routing, Observability|
| Review: 2 Core Maintainers + Security-Focused Review                              |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| TIER C: SECURITY-REVIEW-REQUIRED (High Risk / Advanced)                           |
| Scope: PyO3 Rust FFI Bindings, Seccomp BPF, Landlock, Recovery, IPC Framing       |
| Review: Core Maintainer + Security Reviewer + Corpus Fuzzing & Sanitizers         |
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

## 4. File-Path Based Change Classification Matrix

To prevent contributors or PR labels from mischaracterizing a security-critical change as a minor issue, review requirements are automatically enforced by **target file paths**:

| Target File Path Pattern | Contribution Domain | Risk Tier | Required Reviewers | Mandatory Assurance & Test Requirements |
| :--- | :--- | :--- | :--- | :--- |
| `docs/**`, `README.md` | Documentation | `Tier A` | 1 Maintainer | `docs_audit.py` PASS |
| `examples/plugins/**` | Example Plugins | `Tier A` | 1 Maintainer | Profile A sandbox compliance |
| `cortex/tools/cli/**` | CLI & UX | `Tier A` | 1 Maintainer | `ruff`, `pyright`, unit test suite |
| `cortex/tools/config/**` | **Configuration Resolver** | **`Tier B`** | **2 Maintainers + Security Review** | **`CFG-01`..`CFG-05` behavioral vectors** |
| `cortex/schemas/v1/**` | Canonical Schema | `Tier B` | 2 Maintainers + Security Review | Schema reference integrity pass |
| `cortex/tools/kernel/replica/router.py` | Unprivileged Router | `Tier B` | 2 Maintainers | `RD-1`..`RD-24` conformance suite |
| `cortex/tools/kernel/replica/load_balancer.py`| Load Balancer | `Tier B` | 2 Maintainers | `LB-1`..`LB-14` conformance suite |
| `cortex/tools/kernel/replica/lease.py` | **Lease Manager** | **`Tier C`** | **Maintainer + Security Reviewer** | **Atomic revalidation & fencing tests** |
| `cortex/tools/kernel/replica/ledger.py` | **State Ledger** | **`Tier C`** | **Maintainer + Security Reviewer** | **Crash recovery classifier tests** |
| `cortex/tools/sandbox/**` | **Sandbox & Seccomp** | **`Tier C`** | **Maintainer + Security Reviewer** | **Gate G Complete Mediation suite** |
| `crates/cortex-cbe-py/**` | **PyO3 Rust FFI** | **`Tier C`** | **Maintainer + Security Reviewer** | **Corpus fuzzing + ASan/UBSan clean pass** |
| `coq/**`, `verification/*.v` | **Coq Formal Proofs** | **`Tier D`** | **Formal Verification Reviewer** | **Coq Proof Assistant compilation** |
| `rtl/**` | **Hardware STCR** | **`Tier D`** | **Hardware / Architect Reviewer** | **Verilated STCR pipeline trace bridge** |

---

## 5. Protected-Area Policy: ARCHITECTURE-LOCKED Subsystems

The following components represent the core authority and verification substrate of Cortex. **Direct PRs modifying these subsystems without prior approved RFCs will be automatically closed:**

```
  [PROTECTED AREA] coq/**                     (Coq Formal Evidence Models)
  [PROTECTED AREA] rtl/**                     (Spatio-Temporal Capability Register RTL)
  [PROTECTED AREA] LeaseManager Authority      (LeaseEpoch Monotonic Fencing Logic)
  [PROTECTED AREA] ExecutionIdentity Tokens    (Gateway TCB Bearer Identity Boundaries)
  [PROTECTED AREA] Gateway Commit Sequencing  (Invocation Journal Fsync & Serialization)
  [PROTECTED AREA] CBE Wire Format Primitives (Canonical Binary Encoding Specification)
```

---

## 6. Specific Subsystem Contributor Guidelines

### 6.1 Configuration Resolution Boundaries
- **Strict Offline Loading:** Configuration schema validation MUST load the repository-pinned schema file locally at `cortex/schemas/v1/configuration.schema.json`.
- **Identity URI Only:** The `$id` string (`https://cortex.security/schemas/v1/configuration.schema.json`) is strictly a canonical URI identity string. Configuration parsers MUST NOT issue HTTP/DNS network requests at runtime.
- **Tier Classification:** Configuration resolution is strictly classified as **Tier B (Security-Sensitive Control Plane)**.

### 6.2 FFI & Foreign Code Boundaries (Rust / PyO3)
- PyO3 Rust FFI contributions cross a critical process memory boundary and are strictly **Tier C Security-Sensitive**.
- All FFI contributions MUST satisfy:
  1. Corpus-guided fuzzing (`cargo fuzz`) using structured malformed CBE generators.
  2. Memory safety verification under AddressSanitizer (ASan) and UndefinedBehaviorSanitizer (UBSan).
  3. Panic-unwind boundary protection (`std::panic::catch_unwind`).
  4. Differential wire-format parity against reference Python, Rust, and Go CBE implementations.
  5. Maximum input size, payload truncation, and memory allocation exhaustion test passes.

### 6.3 Example Plugin Guidelines
- Example plugins MUST demonstrate safe local sandbox workloads (SQLite read-only analysis, in-memory AST refactoring, JSON document transformation).
- Network-heavy workloads (web scrapers, socket fetchers) are strictly prohibited from beginner example suites.

---

## 7. Mixed-PR Tier Inheritance Rule

A pull request that touches files spanning multiple risk tiers MUST be classified at the **highest-risk tier** of any file it modifies. The lower-tier classification of individual files does not reduce the overall review requirement.

**Examples:**

| Files Modified | Individual Tiers | PR Classification |
| :--- | :--- | :--- |
| `docs/**` + `cortex/tools/kernel/replica/lease.py` | Tier A + Tier C | **Tier C** |
| `cortex/tools/cli/**` + `cortex/tools/config/**` | Tier A + Tier B | **Tier B** |
| `examples/plugins/**` + `verification/*.v` | Tier A + Tier D | **Tier D** |

> [!WARNING]
> Contributors MUST NOT split security-critical changes across multiple PRs to circumvent this rule. Any related changes to protected subsystems must be reviewed together.

---

## 8. Formal Verification Boundary (Phase 4+)

Phase 4 introduces the first formally verified Gateway security kernel (`verification/Phase4RoutingRefinement.v`). The following properties are proven in Coq with **0 axioms and 0 admitted proofs**:

| Proof ID | Property | Status |
| :--- | :--- | :--- |
| `RD-F1` | Eligibility Safety: Selected ⇒ Eligible | `FORMALLY_VERIFIED` |
| `RD-F2` | Capability Containment: Λ_I ⊆ Λ_W | `FORMALLY_VERIFIED` |
| `RD-F3` | Config Generation & Hash Fencing | `FORMALLY_VERIFIED` |
| `RD-F4` | Stale Config Lease Rejection | `FORMALLY_VERIFIED` |
| `RD-F5` | Router Non-Authority: Proposal ≠ Authorization | `FORMALLY_VERIFIED` |
| `RD-F6` | UNADMITTED ⇒ ¬Authorized ∧ ¬Actuated | `FORMALLY_VERIFIED` |
| `RD-F7` | Single Commitment & Idempotency | `FORMALLY_VERIFIED` |
| `RD-F8` | Bounded Queue Admission | `FORMALLY_VERIFIED` |
| `RD-F9` | State-Domain Conflict Rejection | `FORMALLY_VERIFIED` |
| `RD-F10` | TOCTOU Revalidation Safety (Offline / Draining / GenDrift) | `FORMALLY_VERIFIED` |

**Relationship to executable tests:**

```
        ABSTRACT PHASE 4 MODEL (Phase4RoutingRefinement.v)
                       │
                       ▼
              Coq Safety Theorems (RD-F1..RD-F10)
                       │
                       ▼
           Python Implementation (router.py, lease.py)
                       │
                       ▼
             RD-1..RD-24 Conformance Tests
                       │
                       ▼
          Race / Crash / Fault Injection Tests
```

Coq proves what the Gateway is allowed to guarantee; executable tests prove the implementation conforms.
