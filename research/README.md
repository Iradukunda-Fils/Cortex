# Cortex Research & Empirical Benchmarks Index

This directory contains theoretical formalization notes, Coq/RTL proof artifacts, empirical research synthesis documents, benchmark measurements, crash semantics reports, and experimental spike findings.

---

## Research Synchronization Requirement

> **Mandatory Agent Guideline**: For every critical subsystem implementation, formalization, refactor, benchmark, or architectural decision, inspect `research/` before beginning work and update the relevant research artifact afterward. Do not create a new research document when an existing artifact can be extended. Research documents must describe the current implementation reality, mathematical assumptions, alternatives considered, performance/resource implications, and unresolved questions. They must never claim proof or scalability beyond the evidence actually available. Negative findings are valuable and must be recorded to prevent future work from re-evaluating dead ends.
> 
> **Historical Preservation Rule**: Never overwrite a research conclusion merely because a new implementation is preferred. Preserve the old conclusion as historical evidence when it explains why an alternative was rejected, and update the active conclusion with the new evidence. This maintains a durable, auditable chain of engineering reasoning.

---

## Directory Navigation Taxonomy

```
research/
├── formalization/                     # Formal Proofs & Theoretical Research
│   ├── notes/                         # Coq, RTL, mathematical foundation papers (01_Methodology .. 20_Phase7_Resource_Authority_Coq_Specification)
│   └── artifacts/                     # Canonical binary test programs & phase trace logs (phase1_5, phase2)
├── synthesis/                         # Overall Architectural Research Syntheses
│   ├── v0.3_research_synthesis.md     # Synthesis of Issues #10-#13 Research Findings
│   └── architecture_gate_synthesis.json
├── recovery/                          # Crash Semantics & Recovery Evidence Research
│   ├── v0.3_process_and_recovery_synthesis.md
│   ├── recovery_and_side_effects.md
│   ├── crash_semantics_report.json
│   └── recovery_semantics_report.json
├── telemetry/                         # Runtime Performance & Telemetry Benchmark Data
│   └── telemetry_research_report.json
└── fault-tolerance/                  # Timeout, Cancellation & Sandbox Intercept Research
    └── timeout_cancellation_report.json
```

---

## Active Canonical Governance Disposition

- **Issue #46**: `CLOSED` — Phase 5 abstract model proven (`Phase5LoadBalancerRefinement.v` - 0 Axioms, 0 Admits).
- **Issue #47**: `CLOSED` — Concrete Python $\to$ Coq refinement simulation gate closed (`Phase5Simulation.v` & `issue_47_refinement_closure_evidence_matrix.md`).
- **Issue #48**: `CLOSED` — Durable WAL formal safety proven (`Phase6WALSafety.v` - 0 Axioms, 0 Admits).
- **Issue #49**: `CLOSED` — Phase 6 TLA+ Distributed Authority model checking gate closed (`Phase6DistributedAuthority.tla` - 1,862,685 states checked over $\mathcal{B}_{explored}$).
- **Issue #50**: `CLOSED` — Baseline Scheduler Concurrency Profiling & Versioned Snapshot Read View optimization completed (`02_Scheduler_Benchmark_Results.md` - 2.0x-2.5x throughput gain under high contention).
- **Issue #51**: `LOCAL_TASK_VERIFIED` — Verification Infrastructure Resource Containment & Host Stability Audit (`verify_controller.py` & `17_Verification_Resource_Containment.md`).

---

## Active Research Principles & Models

### 1. Multi-Dimensional Scheduler Cost Model
Scheduler performance is not evaluated as a simple 1D scalar $O(N) \to O(1)$. It is modeled as a multi-dimensional function:

$$\boxed{ \text{SchedulerCost} = f( |W|, |W_c|, \text{Concurrency}, \text{Contention}, \text{Topology}, \text{ResourceVector}, \text{Churn}, \text{QueueDepth}, \text{CacheLocality} ) }$$

### 2. Read-Mostly Snapshot Architecture ($S_A \to V_k = f(S_A)$)
To preserve machine-checked formal safety proofs, authoritative kernel state mutations are strictly isolated from candidate read view snapshots:

$$\boxed{ S_A \xrightarrow{\text{Serialized Writes}} V_k = f(S_A) \xrightarrow{\text{Lock-Free Snapshot}} \text{Concurrent Readers} }$$

Any worker allocation decision derived from $V_k$ must be validated against $S_A$ during atomic commit:

$$\text{Candidate} \xrightarrow{\text{Validate against } S_A} \text{Commit}$$

### 3. Universal Resource Control Philosophy
Every execution subsystem must enforce five mandatory resource control properties:

$$\boxed{ \text{Bound} + \text{Admission} + \text{Backpressure} + \text{Recovery} + \text{Telemetry} }$$




