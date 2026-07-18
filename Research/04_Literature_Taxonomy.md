# 04: Literature Taxonomy
**Status:** LOCKED  

## Purpose
Map 21 foundational computer science disciplines relevant to the research domain, identifying their theoretical primitives, core guarantees, and boundary limitations.

## Dependencies
*   [03_Terminology.md](03_Terminology.md)

---

## Literature Taxonomy Matrix

| No. | Semantic Discipline | Primary Theoretical Focus | Landmark Literature Baselines |
| --- | --- | --- | --- |
| 1 | **Capability Security** | Access Control & Object Confinement | Dennis & Van Horn (1966), KeyKOS, E Language |
| 2 | **Programming Languages (PL)** | Type Safety, Execution Effects, & Memory | Linear/Affine Types, Effect Systems, Rust Ownership |
| 3 | **Delegated Authorization** | Attenuated Authority Propagation | SPKI/SDSI (RFC 2693), Macaroons (2014), Biscuit |
| 4 | **Authorization Engines** | Relational & Logic Policy Evaluation | Google Zanzibar (2019), AWS Cedar, OPA |
| 5 | **Data Provenance** | Graph-based Abstract Lineage Models | W3C PROV-DM, Open Provenance Model (OPM) |
| 6 | **Whole-System Provenance** | OS-Kernel & Storage Level Interception | PASS (Muniswamy-Reddy), SPADE, CamFlow |
| 7 | **Systemic Accountability** | Secure Audit & Non-Repudiation Layers | Network Accountability (Feamster), PeerReview |
| 8 | **Distributed Transactions** | Multi-Node Atomicity & Consistency | 2-Phase Commit, Sagas, Write-Ahead Logging (WAL) |
| 9 | **Workflow Systems** | Long-Running Orchestration Durability | Temporal, Cadence, Event Sourcing |
| 10 | **Formal Methods** | Modeling System Logic & Calculi | Process Calculi (π-calculus), Temporal Logic |
| 11 | **Formal Verification** | Mathematical Correctness Proofs | seL4 Verification, TLA+ Specs |
| 12 | **Information Flow Control** | Non-Interference, Integrity Boundaries | Decentralized IFC (Myers & Liskov), Asbestos |
| 13 | **Trusted Computing** | Cryptographic Hardware Isolation | TPM, Intel SGX, AMD SEV, ARM CCA, Attestation |
| 14 | **Language-Based Security** | Semantic Information Integrity | Non-interference, Robust Declassification, Proof-Carrying Code |
| 15 | **Operational Semantics** | What execution formally means | Structural Operational Semantics (SOS), Evaluation Relations (Plotkin, Felleisen) |
| 16 | **Program Logics** | What properties can be formally proven | Hoare Logic, Separation Logic, Refinement Calculi (Dijkstra) |
| 17 | **Static Analysis** | What invariants can be soundly inferred | Abstract Interpretation (Cousot), Type-Driven Monadic Effects |
| 18 | **Proof-Producing Computation** | Validation Certificate Generation | Certified Abstract Interpretation, Solvers, LF, Twelf, Coq/Lean proof terms |
| 19 | **Secure Compilation** | Verification Property Preservation | Robust Safety/Hyperproperty Preservation, Full Abstraction |
| 20 | **Algebraic & Rewriting Frameworks** | Executable Language Semantics | Goguen & Burstall (Institutions), Meseguer (Maude), Roșu (K Framework) |
| 21 | **Runtime Verification** | Online Trace Compliance | Ligatti, Bauer et al. (Enforcement Monitors), Shield Synthesis |

---

## Discipline Profiles

### 1-20. [Profiles 1 to 20 maintain their previous boundaries]
*(Detailed capability and formal logic profiles omitted for brevity here but refer to the standard taxonomy classifications from earlier rounds).*

### 21. Runtime Verification
*   **Core Guarantee:** Monitoring active execution traces against formal specifications or temporal logics (LTL/MTL) during active execution. Enforcement monitors (shields) can observe, delay, suppress, or modify actions to ensure the trace satisfies a target mathematical property.
*   **Boundary Limitation:** Runtime Verification accurately bounds executing traces to predetermined mathematical safety envelopes. However, it assumes the monitor's configuration envelope and specifications are strictly defined for the executing host context. It does not organically bind the derivation of newly synthesized, intermediate Operational Artifacts ($\mathcal{A}$) back to an externally delegated, non-local cryptographic constraint token ($\Lambda$) bridging multi-domain logic.
