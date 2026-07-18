# Adversarial Systems Research: Delegated Authority & Semantic Verification

This repository houses a rigorous, peer-reviewed adversarial falsification program for autonomous systems. The primary function of this research is to validate the **Working Hypothesis ($H_{\text{prop}}$)** (formerly $H_0$):

> **Does an existing semantic preservation relation characterize when the externally observable effects of an execution remain within the authority constraints delegated to that execution under the stated threat model?**
>
> *We posit this may be expressible as a relational hyperproperty over operational traces, but leave its classification strictly open pending empirical literature analysis.*

If the adversarial analysis reveals that a composition of existing CS frameworks satisfies all safety properties under $H_{\text{prop}}$, no new semantic layer is required. If the analysis exposes an irreducible semantic gap, that gap defines the formal requirements for a new candidate specification.

---

## 🏛️ Repository Architecture

To maintain absolute scientific neutrality and avoid confirmation bias, the repository follows a structured thirteen-file sequential research pipeline under `Research/`:

```text
Research/
├── 01_Methodology.md         <-- Operational rules & Semantic Inversion Stopping Rule (LOCKED)
├── 02_Domain_Model.md        <-- Boundaries, mutability, and Safety Properties (LOCKED)
├── 03_Terminology.md         <-- Formal glossary grounded in CS primitives (LOCKED)
├── 04_Literature_Taxonomy.md <-- The 21 intersecting computer science disciplines (LOCKED)
├── 05_Composition_Analysis.md <-- Standardized analytical testing matrix (ACTIVE - CC-05+ FROZEN)
├── 06_Research_Log.md        <-- Cumulative evidence registry (ACTIVE)
├── 07_Correspondence_Survey.md <-- What relations exist; Admissibility mapping (LOCKED)
├── 08_Evaluation_Relations.md   <-- How procedures and operational artifacts are modeled (LOCKED)
├── 09_Delegation_Semantics.md   <-- How authority behaves during derivation/enactment (LOCKED)
├── 10_Preservation_Relations.md <-- Taxonomy of theorems, simulations, and logical relations (LOCKED)
├── 11_Semantic_Objects.md       <-- Mapping mathematical domains to primary objects (LOCKED)
├── 12_Threat_Model.md           <-- Normalizing adversarial and observation models (LOCKED)
└── 13_Runtime_Assurance.md      <-- Trace monitoring, compliance, and enforcement metrics (LOCKED)
```

---

## 🛡️ The Safety Properties Catalog

Every composition is evaluated against four orthogonal, non-overlapping safety properties under the **Generalized Semantic Transition Relation ($\Sigma; \Lambda \vdash I \Longrightarrow e$)** mapping input streams ($I$) to terminal target actions ($e$) through intermediate **Operational Artifacts ($\mathcal{A}$)**:

$$\frac{\Sigma; \Lambda \vdash I \xrightarrow{\text{derive}} \mathcal{A} \quad \quad \mathcal{A} \in \text{Adm}(\Lambda) \quad \quad \Sigma; \Lambda \vdash \mathcal{A} \xrightarrow{\text{enact}} e}{\Sigma; \Lambda \vdash I \Longrightarrow e}$$

*   **P1 — Authority Soundness:** Bounded authority must be delegable and attenuable across downstream context shifts such that a principal cannot execute or delegate permissions beyond its initial envelope.
*   **P2 — Execution Integrity:** The byte-level parameter state of an executed action must remain structurally unaltered between the generation boundary and the interface enforcement perimeters under the stated threat model. *(Environmental Assumption)*
*   **P3 — Semantic Consequence Preservation:** Every externally observable, irreversible effect must be demonstrably and traceably derivable from the active delegation constraints: $\Sigma \models \text{Preserves}(\Lambda, e)$.
*   **P4 — Independent Verifiability (Rectified):** An external, post-facto verifier must be capable of establishing the validity of P3 without trusting the execution runtime beyond the boundaries of an explicitly declared Trusted Computing Base (TCB).

---

## 🔬 Literature Taxonomy (21 Disciplines)

The program maps system interactions across 21 distinct computer science areas:
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
15. **Operational Semantics** (Structural Operational Semantics, Evaluation Relations)
16. **Program Logics** (Hoare Logic, Separation Logic, Refinement Calculi)
17. **Static Analysis** (Abstract Interpretation, Monadic Effects)
18. **Proof-Producing Computation** (SMT Solvers, Certified Abstract Interpretation)
19. **Secure Compilation** (Robust Safety/Hyperproperty Preservation)
20. **Algebraic & Rewriting Frameworks** (Institution Theory, Maude, K Framework)
21. **Runtime Verification** (Online Trace Compliance & Enforcement Monitors)

---

## 📊 Evaluation Status Matrix

Due to findings in CC-01 and CC-04, all downstream composition checks are frozen while Research Question 0's core mapping (Surveys 07–13) is completed.

| ID | Composition Structure | P1 | P2 | P3 | P4 | Verdict / Current Status |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| **CC-01** | Whole-System Provenance + Capability Security | **✓** | **✓** | **✗** | **✗** | **Complete (Partially Covered)** |
| **CC-04** | Capability Security + Program Logics | **✓** | **✓** | **~** | **✗** | **Complete (Partially Covered)** |
| **CC-05** | Language-Based Security + Trusted Computing | - | - | - | - | **FROZEN** |
| **CC-08** | Runtime Verification + Capability Security | - | - | - | - | **FROZEN** |

*Legend: **✓** (Success)  |  **✗** (Failed)  |  **~** (Partial Success)  |  **-** (Not yet evaluated / Frozen)*

---

## 🛠️ Repository Administration & Rules

1. **LOCKED State:** Foundational survey and model documents are frozen once complete to maintain strict control over confirmation bias. The repository is actively engaged in empirical survey generation.
2. **No Marketing Syntax:** Language must remain strictly technical, quantitative, and neutral.
