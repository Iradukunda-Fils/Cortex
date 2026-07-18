# Adversarial Systems Research: Delegated Authority & Semantic Verification

This repository houses a rigorous, peer-reviewed adversarial falsification program for autonomous systems. The primary function of this research is to validate the **Null Hypothesis ($H_0$)**:

> **Can existing semantic frameworks express and verify the correspondence between delegated authority and dynamically synthesized irreversible effects under an adversarial execution model?**

If the adversarial analysis succeeds in satisfying all safety properties under $H_0$, no new semantic layer is required. If the analysis reveals an irreducible semantic gap, that gap defines the formal requirements for a new candidate specification.

---

## 🏛️ Repository Architecture

To maintain absolute scientific neutrality and avoid confirmation bias, the repository follows a frozen six-file sequential research pipeline under `Research/`:

```
Research/
├── 01_Methodology.md         <-- Operational rules & Semantic Inversion Stopping Rule (LOCKED)
├── 02_Domain_Model.md        <-- Boundaries, multi-system scenarios, and Safety Properties (LOCKED)
├── 03_Terminology.md         <-- Formal glossary grounded in CS primitives (LOCKED)
├── 04_Literature_Taxonomy.md <-- The 15 intersecting computer science disciplines (LOCKED)
├── 05_Composition_Analysis.md <-- Standardized analytical testing matrix (ACTIVE)
└── 06_Research_Log.md        <-- Cumulative evidence registry (ACTIVE)
```

---

## 🛡️ The Safety Properties Catalog

Every composition is evaluated against four orthogonal, non-overlapping safety properties under the **Evaluation Relation ($I \to T \to e$)** mapping input streams ($I$) through internal trace pathways ($T$) to target actions ($e$):

*   **P1 — Authority Soundness:** Bounded authority must be delegable and attenuable across downstream context shifts such that a principal cannot execute or delegate permissions beyond its initial envelope.
*   **P2 — Execution Integrity:** The byte-level parameter state of an executed action must remain structurally unaltered between the generation boundary and the interface enforcement perimeter under the stated threat model. *(Environmental Assumption)*
*   **P3 — Causal Correspondence:** The execution framework must be capable of demonstrating that the dynamically synthesized target action ($e$) is a valid semantic consequence of the active delegation constraints.
*   **P4 — Independent Verifiability:** An external, post-facto verifier must be capable of establishing the validity of P3 without trusting the integrity of the execution runtime after the action has occurred.

---

## 🔬 Literature Taxonomy (15 Disciplines)

The program maps system interactions across 15 distinct computer science areas:
1. **Capability Security** (Confinement & Ambient Authority Elimination)
2. **Programming Languages** (Type Safety, Scoped-Use Semantics)
3. **Delegated Authorization** (Offline-Verifiable Attenuation)
4. **Authorization Engines** (Relationship Graphs & Relational Logic)
5. **Data Provenance** (Platform-Independent Derived Lineage)
6. **Whole-System Provenance** (Kernel-Level Telemetry Interception)
7. **Systemic Accountability** (Tamper-Evident Non-Repudiation Logs)
8. **Distributed Transactions** (Atomicity & Consistency Guarantees)
9. **Workflow Systems** (Durability & State Checkpointing)
10. **Formal Methods** (Process Calculi & Temporal Logic Modelling)
11. **Formal Verification** (Mathematical Correctness Proofs)
12. **Information Flow Control** (Integrity Boundaries & Labels)
13. **Trusted Computing** (Hardware Enclave Isolation)
14. **Language-Based Security** (Non-Interference & Secure Compilation)
15. **Formal Program Semantics** (Evaluation Relations, Type Refinements, State Transitions)

---

## 📊 Evaluation Status Matrix

| ID | Composition Structure | P1 | P2 | P3 | P4 | Verdict / Current Status |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| **CC-01** | Whole-System Provenance + Capability Security | **✓** | **✓** | **✗** | **✗** | **Complete (Partially Covered)** |
| **CC-04** | Capability Security + Formal Program Semantics | **✓** | **✓** | **~** | **✗** | **Complete (Partially Covered)** |
| **CC-05** | DIFC + Enclave Isolation (Attested Execution) | - | - | - | - | **Next Target (Pending)** |

*Legend: **✓** (Success)  |  **✗** (Failed)  |  **~** (Partial Success)  |  **-** (Not yet evaluated)*

### Core Discovered Patterns
*   **CC-01 Proof Gap:** OS-kernel-level telemetry (CamFlow/LSM) captures file and network transactions at boundaries but struggles to observe or verify the semantic trace relation ($I \to T \to e$) within dynamic user-space engines.
*   **CC-04 Proof Gap:** Compile-time refinement types and monadic separation successfully prove static logic chains, but once dynamic user-space interpreters are introduced to execute custom dynamic templates, the compiler's semantic guarantees do not extend to the virtual execution trace inside the interpreter.

---

## 🛠️ Repository Administration & Rules

1. **LOCKED State:** Foundational documents `01` through `04` are frozen. No conceptual additions or modifications may be introduced out-of-sequence.
2. **RF2119 Compliance:** Strict use of normative keywords (`MUST`, `SHOULD`, `MAY`, `SHALL NOT`).
3. **No Marketing Syntax:** Language must remain strictly technical, quantitative, and neutral.
