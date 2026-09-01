# Research Note 17: Verification Resource Containment & Host Stability

## Executive Summary
This document establishes the formal engineering design, empirical resource model, and operational limits for **Issue #51 (Verification Resource Containment & Host Stability Audit)**.

Unrestricted parallel execution of verification tools (such as Java TLC model checking and parallel Coq compilation) can consume excessive system RAM, leading to swap thrashing, system unresponsiveness, or host OOM crashes. This research note codifies the Cortex Verification Resource Controller (`verification/verify_controller.py`) to enforce bounded, deterministic, and host-friendly verification.

---

## 1. Root Cause & Empirical Stage Profile Analysis

Empirical profiling (`verification/verify_resource_profiler.py`) identified the resource consumption across all verification stages:

| Verification Stage | Command / Subsystem | Observed RSS ($RSS_{obs}$) | Reserved Budget ($RSS_{budget}$) | Dominant Resource Vector |
|---|---|---|---|---|
| **Coq Single Module** | `coqc Phase5Simulation.v` | $17.69\text{ MB}$ | $150.00\text{ MB}$ | Process RAM per compiler instance |
| **Coq Full Suite** | `coqc` (All 20 proof modules) | $17.94\text{ MB}$ | $800.00\text{ MB}$ | Parallel process fan-out |
| **Axiom / Admit Audit** | `grep` across `.v` files | $17.94\text{ MB}$ | $50.00\text{ MB}$ | Minimal file I/O |
| **TLA+ TLC Bounded** | `java -Xmx1G ... tlc2.TLC` | **$968.62\text{ MB}$** | $1,200.00\text{ MB}$ | **JVM Heap & Off-Heap Memory** |
| **Python Conformance** | `unittest` (219 tests) | $85.00\text{ MB}$ | $500.00\text{ MB}$ | CPU & memory allocations |
| **Python Benchmark** | `test_scheduler_benchmark` | $65.00\text{ MB}$ | $800.00\text{ MB}$ | Worker/invocation state allocation |

> **Note on $RSS_{obs}$ vs $RSS_{budget}$**: $RSS_{obs}$ represents single-process RSS measured during isolated stage profiling. $RSS_{budget}$ represents the safety reservation ceiling mandated by the Verification Controller to accommodate concurrent process allocations and peak working sets.

---

## 2. Three-Tier Memory Ceilings & Concurrency Admission

The Verification Controller enforces a strict three-tier memory hierarchy:

$$\boxed{ H_{\text{heap}}\ (\text{JVM}) < H_{\text{RSS}}\ (\text{Process Ceiling}) < H_{\text{system-safe}}\ (\text{Host Admission Limit}) }$$

1. **Tier 1: JVM Heap Limit ($H_{\text{heap}}$)**:
   - Fixed `-Xmx1G` for standard TLA+ model checking, `-Xmx2G` for stress model checking.
2. **Tier 2: Process RSS Limit ($H_{\text{RSS}}$)**:
   - Monitored by the resource controller. Kills runaway processes exceeding profile ceiling ($800\text{ MB} \le H_{\text{RSS}} \le 3500\text{ MB}$).
3. **Tier 3: Host Admission Limit ($H_{\text{system-safe}}$)**:
   - Evaluates:
     $$\text{AvailableRAM} - \sum \text{ActiveReservations} - \text{JobBudget} - \text{HostMargin} \ge 0$$
   - Uses file-based reservation locking (`verification/.verify_admission.json`) to prevent concurrent process over-admission.

---

## 3. Staged Verification Profile Taxonomy

To protect host stability while preserving 100% formal assurance, six assurance profiles and one decoupled benchmark profile are supported:

| Profile Target | Command | Required Budget | Max RSS Ceiling | Timeout | Purpose |
|---|---|---|---|---|---|
| `verify-fast` | `make verify-fast` | $500\text{ MB}$ | $800\text{ MB}$ | $60\text{s}$ | Fast developer sanity check |
| `verify-kernel` | `make verify-kernel` | $600\text{ MB}$ | $1,000\text{ MB}$ | $120\text{s}$ | Core load balancer verification |
| `verify-coq` | `make verify-coq` | $800\text{ MB}$ | $1,500\text{ MB}$ | $180\text{s}$ | Full Coq proof suite build |
| `verify-tla-safe` | `make verify-tla-safe` | $1,200\text{ MB}$ | $1,800\text{ MB}$ | $240\text{s}$ | Bounded TLC model checking |
| `verify-full` | `make verify-full` | $1,500\text{ MB}$ | $2,000\text{ MB}$ | $400\text{s}$ | Complete assurance pipeline (No benchmarks) |
| `verify-stress` | `make verify-stress` | $2,500\text{ MB}$ | $3,500\text{ MB}$ | $600\text{s}$ | High-scale model checking |
| `verify-benchmark`| `make verify-benchmark`| $800\text{ MB}$ | $1,500\text{ MB}$ | $180\text{s}$ | Performance measurement (Decoupled) |

---

## 4. Assurance Preservation Invariant

> **Mandatory Rule**: Verification resource bounds MUST NOT weaken mathematical assurance obligations.
- All Coq proof modules (`Phase5Simulation.v`, `Phase6WALSafety.v`) continue to be verified with **0 Axioms, 0 Admits**.
- TLA+ model checking continues to explore the complete state graph ($1,862,685$ states over $\mathcal{B}_{explored}$) with **0 errors**.
- Execution is strictly bounded and sequentialized, failing deterministically with clear diagnostics if memory is insufficient.
