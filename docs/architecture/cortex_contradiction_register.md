# Cortex Repository Contradiction & Truth Reconciliation Register

> **Governance Principle**: Reconcile claims against repository reality.  
> **Source Order**: Ground-Truth Code > Test Harness > Benchmarks > Formal Proofs > Documentation.  

---

## 1. Contradiction & Misalignment Matrix

| Item ID | Domain / Scope | Documentation / Research Claim | Repository Reality (Code / Tests) | Reconciled Status | Action Item |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MIS-01** | Worker Autoscaling | "Cortex supports automatic real-time autoscaling driven by queue pressure feedback." | `cortex.schema.scaling` defines policy types and `ReplicaManager` provides manual `scale_up`/`scale_down` methods, but **NO background feedback controller loop exists**. | `SPECIFIED` / `DESIGN-ONLY` | Update documentation to clarify autoscaling is manual/imperative until dynamic controller loop is implemented. |
| **MIS-02** | Multi-Node Clustering | "Cortex Gateway provides distributed multi-node leader election and Raft-based distributed state replication." | Cortex currently runs as a **single-host Gateway TCB process** managing worker processes via local sockets/IPC. Distributed consensus specs exist in `docs/architecture/` but are not implemented in Python core. | `DESIGN-ONLY` | Explicitly label multi-node cluster specs as Future Roadmap items in docs. |
| **MIS-03** | Formal Proof Scope | "Cortex core algorithms are 100% formally proven end-to-end." | Coq proofs in `contracts/` prove **abstract state machine properties** (reservation safety, lease fencing invariants), but do NOT refine into C/Python AST or executable bytecode. | `ABSTRACT-PROVEN` (Not Concrete Code Proof) | Reconcile assurance labels: Distinguish abstract Coq proofs from runtime Python test verification. |
| **MIS-04** | Physical Containment | "All Cortex workers execute inside isolated cgroups v2 containers." | Under `strict_mode=True`, `RequiredPhysicalEnforcement \land Unavailable \Rightarrow ExecutionRejected`. Unconstrained subprocess fallback is strictly a developer convenience path for non-strict environments (`strict_mode=False`) and is NEVER equivalent to physical containment. | `DEGRADED-FALLBACK` (Dev Only) | Explicitly document strict vs non-strict physical containment policy. |
| **MIS-05** | Polyglot Verification | "RTL hardware decoders execute binary CBE streams in production." | RTL SystemVerilog modules in `rtl/` are validated via Verilator tests in `test_conformance_rtl.py`, but **production Python execution uses `cbe/` Python parser**. | `PROTOTYPE` / `SIMULATED` | Clarify that RTL models are hardware design prototypes, not active runtime schedulers. |

---

## 2. Document Truth Invariant Enforcement

To enforce the fundamental invariant:
$$\text{Evidence Strength} \ge \text{Documentation Claim Strength}$$

Every architectural specification document in `docs/architecture/` must maintain explicit Governance Status badges:
- `IMPLEMENTED` & `RUNTIME-VERIFIED` (Backed by passing pytest execution)
- `ADVERSARIALLY-TESTED` (Backed by fault injection / bitflip test suites)
- `EMPIRICALLY-MEASURED` (Backed by performance benchmark scripts)
- `ABSTRACT-PROVEN` (Backed by Coq/Rocq `.v` formal proofs)
- `SPECIFIED` / `DESIGN-ONLY` (Architectural proposal without executable code)
