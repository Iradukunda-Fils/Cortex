# 05: Composition Analysis
**Status:** Active — Downstream compositions (CC-05+) frozen pending completion of Research Question 0 deep semantic baseline surveys.

## Purpose
Subject the Null Hypothesis to adversarial testing using the four Safety Properties (P1–P4) and the Evaluation Relation ($\Sigma; \Lambda \vdash I \Longrightarrow e$) against candidate compositions drawn from the 19-discipline taxonomy.

## Dependencies
*   [01_Methodology.md](01_Methodology.md) — LOCKED
*   [02_Domain_Model.md](02_Domain_Model.md) — LOCKED
*   [03_Terminology.md](03_Terminology.md) — LOCKED
*   [04_Literature_Taxonomy.md](04_Literature_Taxonomy.md) — LOCKED
*   [07_Correspondence_Survey.md](07_Correspondence_Survey.md) — LOCKED

---

## Evaluation Pipeline

We evaluate how each candidate composition handles the Evaluation Relation mapping inputs ($I$) to operational derivation artifacts ($\langle \mathcal{D}, \tau, \mathcal{P} \rangle$) and target actions ($e$) under adversarial conditions:

```
                      [ Evaluation Relation (I ⟹ e) ]
                                     │
       ┌─────────────────────────────┴─────────────────────────────┐
       ▼                                                           ▼
 [ Intent / Delegation (Λ) ] ──► [ Derivation (D, τ, P) ] ──► [ Irreversible Action (e) ]
```

Each composition is audited against the Safety Properties catalog:
*   **P1 — Authority Soundness:** Delegated authority must remain bounded and attenuable.
*   **P2 — Execution Integrity:** Byte-level parameter state must remain unmodified. *(Environmental baseline — not primary research focus)*
*   **P3 — Semantic Consequence Preservation:** Every irreversible effect must be demonstrably derivable from active delegation constraints under the evaluation semantics: $\Sigma \models \text{Preserves}(\Lambda, e)$.
*   **P4 — Independent Verifiability (Rectified):** Post-facto audit of P3 must be possible without trusting the execution runtime beyond an explicitly declared TCB.

---

## CC-01: Whole-System Provenance + Capability Security

**Composition Identifier:** CC-01

**Evaluated Semantic Disciplines:** Whole-System Provenance (6) + Capability Security (1)

**Representative System Setup:** A hardened Unix-like environment isolating runtime evaluation processes inside capability mode descriptors (e.g., Capsicum), with asynchronous, secure kernel-level telemetry captured continuously via Linux Security Module (LSM) hooks (e.g., CamFlow).

**Observation Model:** OS-kernel system call boundary interception.

### 1. The Realized Structural Proof Gap

Under the multi-domain scenario of a Distributed DBMS Query Optimizer:
1. The optimizer ingests an input stream ($I$), evaluating dynamic relational statistics to derive an execution trace and plan ($\mathcal{P}$) targeting an irreversible deletion action ($e$).
2. An adversary executes a user-space memory exploit within the query optimizer's runtime heap after the execution plan has finished derivation but before the capability interface call is dispatched.
3. The parameter vector is altered to clear a production database space.
4. The execution process invokes its local capability descriptor. Because the descriptor only evaluates coarse entitlement ("Does this task have permission to touch this storage sector?"), the execution passes.
5. The kernel provenance subsystem (CamFlow) captures the transaction at the LSM interface.

```
[ User-Space Optimizer ] ─── Input (I) ───► Derivation (D, τ, P) ───► [ Exploited / Mutated Payload ]
                                                                                │
                                                                                ▼
[ OS LSM Boundary ]      ─── (Confinement Check OK) ─────────────────────────► Action (e)
                                                                                │
                                                                                ▼
[ CamFlow Kernel Hook ]  ─── Captures: Task(X) -> Writes -> Device(Y) ──────────┘
```

### 2. Safety Properties Matrix

| Safety Property | Status | Precise Technical Failure Point |
| --- | --- | --- |
| **P1: Authority Soundness** | **SUCCESS** | The capability boundary successfully limits the maximum accessible scope of the process. |
| **P2: Execution Integrity** | **SUCCESS** | Hardened OS memory isolation blocks out-of-band external tampering with target process memory. |
| **P3: Semantic Consequence Preservation** | **FAILED** | CamFlow's observation model captures operating-system events rather than semantic evaluation relations. It cannot establish whether the emitted operation is a valid semantic consequence of delegation constraints: $\Sigma \models \text{Preserves}(\Lambda, e)$ fails. |
| **P4: Independent Verifiability** | **FAILED** | The inner derivation elements ($\mathcal{D}, \tau, \mathcal{P}$) are entirely opaque to the LSM observation boundary. An external auditor cannot verify structural validity without trusting the user-space runtime. |

### 3. Confidence Verdict

**Partially Covered.** Authority soundness and execution integrity are satisfied. Semantic consequence preservation and independent verifiability remain completely unresolved.

---

## CC-04: Capability Security + Program Logics (Dependently Typed Execution)

**Composition Identifier:** CC-04

**Evaluated Semantic Disciplines:** Capability Security (1) + Program Logics (16)

**Representative System Setup:** An application runtime engineered using a strict Monadic Effect System and Refinement Types (e.g., F* or Idris), running inside an object-capability isolated process wrapper.

### 1. Semantic Coverage

This composition addresses the problem through Program Logics. By leveraging refinement types, the compiler mathematically enforces that any function capable of producing an external, irreversible effect must carry a type-level witness proving it was derived safely from its inputs.

Under the Infrastructure Orchestration scenario, a function mapping Kubernetes scheduling parameters to an irreversible `TeardownNode()` call must present a compile-time proof that the target node satisfies all safety policies.

### 2. Operational Assumptions

*   **Static Equivalence:** The complete policy domain, input taxonomy, and invariant constraints must be fully decidable at compile time.
*   **Homogeneous Runtime Domain:** The language environment must maintain an uninterrupted monopoly over the execution lifecycle. Any out-of-band dynamic assembly loading, FFI calls, or external untyped interpretations break the type refinement model.

### 3. The Absolute Adversarial Vector (The Dynamic Interpretation Bypass)

Because the platform cannot recompile itself for every user input, it must run a user-space interpreter inside the dependently typed engine to process dynamic, user-submitted execution workflows.

1.  The host engine is compiled with flawless, mathematically sound refinement types.
2.  At runtime, the host engine ingests an input stream representing an infrastructure deployment template.
3.  An adversary crafts an input template that exploits a logical flaw in the user-space interpreter's evaluation routine.
4.  The interpreter generates an execution instruction to delete a production node cluster.
5.  The host engine receives this instruction from its internal interpreter block. The parameter satisfies the refinement check at the language level — the type system verifies that the interpreter generated the output, but cannot verify the correctness of the dynamic derivation trajectory inside the interpreter's virtual space.

### 4. Addressing the "Verified Interpreter" Objection

A typical objection is: *"Simply use a verified interpreter (e.g., CompCert, CakeML, or a certified compiler)."*

This objection is formally bypassed by the following structural argument:

A formally verified interpreter guarantees a strict evaluation relation:
$$\text{Interpreter}(Program, Input) \equiv \text{Semantics}(Program, Input)$$

This proves the interpreter faithfully executes the language rules. However:

> A verified interpreter does **not** prove that the derived program's strategy choices are a valid semantic consequence ($\Sigma \models \text{Preserves}(\Lambda, e)$) of the original delegation constraints.

Even if the interpreter executes its instruction-decoding with complete semantic correctness and no memory bugs, it remains incapable of proving that its runtime derivation trajectory preserved the proof obligation delegated to it by the host system. The type system evaluates the interpreter's wrapper; it cannot natively bind the synthesized program's dynamic strategy to the external authority envelope.

This is a **structural absence** which exists because classical Operational Semantics (15) and Program Logics (16) do not model delegated authority propagation.

### 5. Safety Properties Matrix

| Safety Property | Status | Precise Technical Failure Point |
| --- | --- | --- |
| **P1: Authority Soundness** | **SUCCESS** | Managed by the object-capability process shell. |
| **P2: Execution Integrity** | **SUCCESS** | Guaranteed by the memory safety invariants of the dependently typed language. |
| **P3: Semantic Consequence Preservation** | **PARTIAL** | Satisfied for all native compiled code pathways. Failed for nested dynamic runtime interpretations — verified interpreter does not bind the derived program's strategy to the delegation envelope. |
| **P4: Independent Verifiability** | **FAILED** | A post-facto verifier cannot prove that the generated target parameter was a valid semantic consequence of the original delegation policy without inspecting the interpreter's internal derivation state, which is not preserved as an immutable external witness. |

### 6. Confidence Verdict

**Partially Covered.**

---

## Candidate Compositions (Status)

All architectural composition checks remain strictly locked pending the completion of the baseline surveys.

| ID | Evaluated Disciplines | Status |
| --- | --- | --- |
| **CC-01** | Whole-System Provenance (6) + Capability Security (1) | **Complete — Partially Covered** |
| **CC-04** | Capability Security (1) + Program Logics (16) | **Complete — Partially Covered** |
| CC-05 | Language-Based Security (14) + Trusted Computing (13) | **FROZEN** |
| CC-06 | Program Logics (16) + Trusted Computing (13) + Systemic Accountability (7) | **FROZEN** |
| CC-07 | Secure Compilation (19) + Capability Security (1) | **FROZEN** |
