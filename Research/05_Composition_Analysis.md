# 05: Composition Analysis
**Status:** Active  

## Purpose
Subject the Null Hypothesis to adversarial testing using the four condensed Safety Properties (P1 through P4) and the Evaluation Relation (I→T→e) mapping input streams (I) through execution traces (T) to target actions (e) against candidate compositions drawn from the 15-discipline taxonomy.

## Dependencies
*   [01_Methodology.md](01_Methodology.md) — LOCKED
*   [02_Domain_Model.md](02_Domain_Model.md) — LOCKED
*   [03_Terminology.md](03_Terminology.md) — LOCKED
*   [04_Literature_Taxonomy.md](04_Literature_Taxonomy.md) — LOCKED

---

## Evaluation Pipeline

We evaluate how each candidate composition handles the Evaluation Relation (I→T→e) mapping inputs (I) to dynamic trace graphs (T) to target actions (e) under adversarial conditions:

```
                      [ Evaluation Relation (I→T→e) ]
                                     │
       ┌─────────────────────────────┴─────────────────────────────┐
       ▼                                                           ▼
 [ Intent / Delegation ] ────────────► [ Dynamic Trace ] ────────────► [ Irreversible Action ]
```

Each composition is audited against the Safety Properties catalog:
*   **P1 — Authority Soundness:** Delegated authority must remain bounded and attenuable.
*   **P2 — Execution Integrity:** Byte-level parameter states must remain unmodified between generation and enforcement boundaries.
*   **P3 — Causal Correspondence:** Attests that the target action is a valid semantic consequence of delegation constraints.
*   **P4 — Independent Verifiability:** Post-facto audit of the evaluation relation without trusting the active execution runtime.

---

## CC-01: Whole-System Provenance + Capability Security (Revised)

**Composition Identifier:** CC-01

**Evaluated Semantic Disciplines:** Whole-System Provenance (6) + Capability Security (1)

**Representative System Setup:** A hardened Unix-like environment isolating runtime evaluation processes inside capability mode descriptors (e.g., Capsicum), with asynchronous, secure kernel-level telemetry captured continuously via Linux Security Module (LSM) hooks (e.g., CamFlow).

**Observation Model:** OS-kernel system call boundary interception.

### 1. The Realized Structural Proof Gap

Under the multi-domain scenario of a Distributed DBMS Query Optimizer:
1. The optimizer ingests an input stream (I), evaluating dynamic relational statistics to derive an execution trace (T) targeting an irreversible deletion action (e).
2. An adversary executes a user-space memory exploit or logic manipulation within the query optimizer's runtime heap after the execution trace has finished processing but before the capability interface call is dispatched.
3. The parameter vector is altered to clear an invalid target database space.
4. The execution process invokes its local capability descriptor to write to the underlying storage interface. Because the descriptor only evaluates coarse entitlement ("Does this task have permission to touch this storage sector?"), the execution passes.
5. The kernel provenance subsystem (CamFlow) captures the transaction at the LSM interface. 

The data path and observation boundaries are structural:

```
[ User-Space Optimizer ] ─── Input (I) ───► Trace (T) ───► [ Exploited / Mutated Payload ]
                                                                     │
                                                                     ▼
[ OS LSM Boundary ]      ─── (Confinement Check OK) ──────────────► Action (e)
                                                                     │
                                                                     ▼
[ CamFlow Kernel Hook ]  ─── Captures: Task(X) -> Writes -> Device(Y) ┘
```

The capability layer checks rights, not logic. The OS kernel provenance captures that page modification occurred and system calls were executed, but does not capture the semantic relationship between the inputs (I) and the altered trace.

### 2. Evaluating the Redefined Safety Properties Matrix

| Formal Safety Property | Status | Precise Technical Failure Point |
| --- | --- | --- |
| **P1: Authority Soundness** | **SUCCESS** | The capability boundary successfully limits the maximum accessible scope of the process. |
| **P2: Execution Integrity** | **SUCCESS** | Hardened OS memory isolation blocks out-of-band external tampering with target process memory. |
| **P3: Causal Correspondence** | **FAILED** | CamFlow's observation model captures operating-system events rather than semantic evaluation relations. Consequently, it cannot establish whether the emitted operation is a valid consequence of the authority constraints under which the runtime executed. |
| **P4: Independent Verifiability** | **FAILED** | Because the inner execution trace (T) and its evaluation relation to inputs (I) are entirely opaque to the LSM observation boundary, an external auditor cannot verify the structural validity of the action without wholly trusting the integrity of the user-space runtime at the millisecond of execution. |

### 3. Formal Confidence Verdict

**Partially Covered.** (Authority and execution integrity are satisfied; causal correspondence and independent verifiability remain completely unresolved).

---

## CC-04: Capability Security + Formal Program Semantics

**Composition Identifier:** CC-04

**Evaluated Semantic Disciplines:** Capability Security (1) + Formal Program Semantics (15)

**Representative System Setup:** An application runtime engineered using a strict Monadic Effect System and Refinement Types (e.g., an execution environment written in a dependently typed language like F* or Idris), running inside an object-capability isolated process wrapper.

### 1. Semantic Coverage

This composition addresses the problem directly through Evaluation Relations. By leveraging refinement types and monadic isolation, the compiler mathematically enforces that any function capable of producing an external, irreversible effect must carry a type-level witness proving it was derived safely from its inputs.

Under the Infrastructure Orchestration / Autoscaler scenario, a function mapping Kubernetes scheduling parameters to an irreversible `TeardownNode()` call must present a compile-time proof that the target node satisfies all safety policies. The language semantics ensure that the input string cannot bypass the evaluation trace without causing a type-checking error.

### 2. Operational Assumptions

*   **Static Equivalence:** The complete policy domain, input taxonomy, and invariant constraints must be fully decidable at compile time.
*   **Homogeneous Runtime Domain:** The language environment must maintain an uninterrupted monopoly over the execution lifecycle; any out-of-band dynamic assembly loading, foreign function interface (FFI) calls, or external untyped interpretations break the type refinement model.

### 3. The Absolute Adversarial Vector (The Dynamic Interpretation Bypass)

Consider a scenario where the infrastructure platform must process dynamic, user-submitted execution workflows at runtime. Because the platform cannot recompile itself for every user input, it must run a user-space interpreter inside the dependently typed engine.

1.  The host engine is compiled with flawless, mathematically sound refinement types and monadic isolation proofs.
2.  At runtime, the host engine ingests an input stream representing an infrastructure deployment template.
3.  An adversary crafts an input template that exploits a logical flaw in the user-space interpreter's evaluation routine (e.g., an unexpected loop interaction or an unchecked evaluation branch).
4.  The user-space interpreter processes this template and generates an execution instruction to delete a production node cluster.
5.  The host engine receives this instruction from its internal interpreter block. Because the interpreter block itself is a valid, highly trusted typed module within the host language, the parameter satisfies the refinement check at the language level. The type system verifies that the interpreter generated the output, but it cannot statically verify the correctness of the dynamic execution trace that occurred inside the interpreter's virtual space.

### 4. Strategic Attribution Analysis

*   **P1: Authority Soundness:** **SUCCESS.** Managed by the object-capability process shell.
*   **P2: Execution Integrity:** **SUCCESS.** Guaranteed by the memory safety invariants of the dependently typed language.
*   **P3: Causal Correspondence:** **PARTIAL SUCCESS.** Satisfied for all native compiled code pathways; failed for nested dynamic runtime interpretations.
*   **P4: Independent Verifiability:** **FAILED.** Once a dynamic runtime interpreter is introduced, a post-facto verifier cannot prove that the generated target parameter was a valid consequence of the original delegation policy without inspecting the execution trace of the interpreter, which is not preserved as an immutable external witness.

**Residual Obligation:** While formal program semantics can guarantee the causal correctness of static evaluation relations, they fail to maintain an externally verifiable correspondence link when the target parameters are synthesized by a nested, non-deterministic runtime interpreter whose internal execution trace is not bound to the capability boundary.

**Comparable Prior Work:** Proof-Carrying Code (PCC) allows code consumers to safely execute untrusted binaries by verifying attached safety proofs, but it focuses heavily on memory safety and resource bounds rather than validating the semantic intent of dynamically generated operations.

### 5. Confidence Verdict

**Partially Covered.**

---

## Candidate Compositions (Status)

| ID | Evaluated Disciplines | Status |
| --- | --- | --- |
| **CC-01** | **Whole-System Provenance (6) + Capability Security (1)** | **Complete — Partially Covered** |
| **CC-04** | **Capability Security (1) + Formal Program Semantics (15)** | **Complete — Partially Covered** |
| CC-05 | Language-Based Security (14) + Trusted Computing (13) | Pending |
| CC-06 | Formal Verification (11) + Trusted Computing (13) + Workflow Systems (9) | Pending |
| CC-07 | Information Flow Control (12) + Delegated Authorization (3) + Workflow Systems (9) | Pending |
| CC-08 | Formal Methods (10) + Capability Security (1) + Distributed Transactions (8) | Pending |
| CC-09 | Programming Languages (2) + Delegated Authorization (3) + Data Provenance (5) | Pending |
| CC-10 | Systemic Accountability (7) + Trusted Computing (13) + Language-Based Security (14) | Pending |
