# 04: Literature Taxonomy
**Status:** LOCKED  

## Purpose
Map 20 foundational computer science disciplines relevant to the research domain, identifying their theoretical primitives, core guarantees, and boundary limitations.

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

---

## Discipline Profiles

### 1. Capability Security
*   **Core Guarantee:** Confinement and ambient authority elimination. An execution context can only interact with resources for which it explicitly holds a capability reference. References cannot be forged.
*   **Boundary Limitation:** Captures invocation mechanics but does not internally model the causal relationship between a dynamic operational artifact and the justification context.

### 2. Programming Languages (PL)
*   **Core Guarantee:** Type safety, memory safety, and effect tracking. Linear and affine type systems enforce single-use or scoped-use semantics. Effect systems and ownership models prevent unauthorized resource access at the language level.
*   **Boundary Limitation:** Static type-level guarantees constrain code as written. They do not extend to runtime-generated intermediate operational artifacts ($\mathcal{A}$) produced by an interpreter or execution engine consuming non-deterministic user inputs.

### 3. Delegated Authorization
*   **Core Guarantee:** Cryptographic attenuation. A principal can trustworthily delegate a subset of its authority downstream via append-only programmatic constraints. Delegation is offline-verifiable.
*   **Boundary Limitation:** Tokens assert permissibility of a class of actions, not the causal binding of specific operational elements to a specific execution trace.

### 4. Authorization Engines
*   **Core Guarantee:** High-throughput evaluation of dynamic entity-to-entity relationship graphs and policy logic, yielding permission decisions at query time.
*   **Boundary Limitation:** Engines return transient allow/deny decisions. They do not sign decisions, preserve execution lineage, or produce independent, offline-verifiable artifacts that tie an executed action directly to the generation path of its inputs.

### 5. Data Provenance
*   **Core Guarantee:** Abstract graph-based models (W3C PROV-DM) providing a vocabulary for describing entities, activities, and agents involved in data derivation. Platform-independent lineage representation.
*   **Boundary Limitation:** Descriptive vocabulary only. Does not provide enforcement, interception, or active verification mechanisms.

### 6. Whole-System Provenance
*   **Core Guarantee:** OS-kernel-level interception of all state changes via security module hooks (LSM). Generates append-only directed acyclic graphs tracing every process, file, and socket interaction back to initialization.
*   **Boundary Limitation:** Observation granularity is bounded by the system-call interface. User-space application logic (including dynamic interpreter configurations and intermediate query plans) operates as a black box to the kernel interceptor.

### 7. Systemic Accountability
*   **Core Guarantee:** Secure, non-repudiable attribution of network or system actions to identified principals, using tamper-evident logs and distributed fault detection mechanisms.
*   **Boundary Limitation:** Accountability systems bind actions to identities, not to the intermediate plans or operational artifacts that generated the action parameters.

### 8. Distributed Transactions
*   **Core Guarantee:** Linearizability and fault tolerance. Multi-node state transactions transition atomically and predictably despite arbitrary network partitions.
*   **Boundary Limitation:** Transaction protocols ensure state consistency, not authorization consistency. Authorization metadata is treated as arbitrary payload.

### 9. Workflow Systems
*   **Core Guarantee:** Orchestration continuity. Preserves local execution state across infrastructure crashes using event-sourcing histories. Deterministic replay of execution sequences.
*   **Boundary Limitation:** Workflow coordinators record that execution steps occurred and in what order, but do not validate that parameters crossing step boundaries were bound to delegation constraints.

### 10. Formal Methods
*   **Core Guarantee:** Mathematical modeling of system behavior using process calculi, temporal logics, and state machine specifications. Enables reasoning about concurrency, liveness, and safety properties at design time.
*   **Boundary Limitation:** Models describe and constrain system behavior at design time. They do not provide structures to trace dynamic runtime operational artifacts to delegated authority contexts.

### 11. Formal Verification
*   **Core Guarantee:** Mathematical proofs of system correctness properties, functional specification conformance, and security proofs.
*   **Boundary Limitation:** Verification applies to statically defined system models. Non-deterministic compilation and translation engines introduce state spaces that may exceed viable verification boundaries.

### 12. Information Flow Control
*   **Core Guarantee:** Enforces that data classified at a given confidentiality or integrity level cannot flow to unauthorized sinks. Prevents covert channel leaks.
*   **Boundary Limitation:** IFC tracks data flow direction and classification labels but does not model delegation attenuation or the semantic relationship between an authority grant and the parameters of a specific effect.

### 13. Trusted Computing
*   **Core Guarantee:** Cryptographic hardware-enforced runtime trust. A trusted execution environment can attest that specific code ran in an isolated enclave, producing signed measurements.
*   **Boundary Limitation:** Hardware attestation proves that code-as-compiled executed within an enclave, but does not structurally bind intermediate operational artifacts ($\mathcal{A}$) to the delegation lineage.

### 14. Language-Based Security
*   **Core Guarantee:** Enforces semantic information integrity through type-system-level non-interference, robust declassification policies, and proof-carrying code.
*   **Boundary Limitation:** Static type-level guarantees constrain code as compiled. They do not extend to dynamically loaded runtime modules or execution trajectories derived at runtime that were not present at compile time.

### 15. Operational Semantics
*   **Core Guarantee:** Provides a rigorous, mathematical account of what it means to execute a program. Structural Operational Semantics (SOS) defines exactly which states a program may transition through for any given input.
*   **Boundary Limitation:** Operational semantics defines the transition relation of a fixed language or program. It cannot natively express the constraint that an intermediate operational artifact ($\mathcal{A}$) — where the program is itself generated from inputs — must preserve an externally delegated obligation.

### 16. Program Logics
*   **Core Guarantee:** Provides formal tools (Hoare triples, Separation Logic, Refinement Calculi) to prove that a program satisfies a specification expressed as pre- and post-conditions.
*   **Boundary Limitation:** All established program logics require the program statement to be known and fixed at proof time. When the program statement is itself an intermediate plan ($\mathcal{P}$) derived dynamically at runtime, the standard triple $\{P\} \, C \, \{Q\}$ becomes undefined until $C$ is known — at which point the execution has already occurred.

### 17. Static Analysis
*   **Core Guarantee:** Soundly infers invariants about all possible program executions without running the program. Abstract Interpretation provides a sound over-approximation of program behavior; type-driven effect systems infer resource usage statically.
*   **Boundary Limitation:** Static analysis operates over a fixed program text or control-flow graph. When the graph itself is derived at runtime, static analysis cannot track invariants through that derivation boundary without requiring the compilation steps be fully pre-enumerable.

### 18. Proof-Producing Computation
*   **Core Guarantee:** Generates machine-checkable validation certificates alongside structural computational outputs (e.g., proof-producing SMT/SAT solvers, certified abstract interpreters, logical frameworks like LF/Twelf, and Coq/Lean proof terms).
*   **Boundary Limitation:** Emitted certificates ($\pi$) operate on internal domain properties. They lack semantic features to link back to a delegation boundary ($\Lambda$) representing upstream human intent or coarse authority boundary rights under an adversarial model.

### 19. Secure Compilation
*   **Core Guarantee:** Formally establishes that specific security properties and hyperproperties (e.g., Robust Safety Preservation, Robust Hyperproperty Preservation, and Fully Abstract Compilation) survive when control is passed into an adversarial context or intermediate translation envelope.
*   **Boundary Limitation:** Typically targets compiling static source-level programs to lower-level targets safely. It does not model execution environments whose explicit runtime task is to dynamically generate and execute brand new, arbitrary query plans or workflows based on incoming delegation objects ($\Lambda$).

### 20. Algebraic & Rewriting Frameworks
*   **Core Guarantee:** Provides rigorous structural tools to model executable language semantics and logical structures across three distinct research traditions:
    *   **Institution Theory (Goguen & Burstall):** Abstract model-theoretic logicians studying the structural mappings between completely distinct logical systems.
    *   **Rewriting Logic (Meseguer / Maude):** Concurrent, non-deterministic system modeling based on the continuous rewriting of equational state terms.
    *   **Executable Semantics Frameworks (Roșu / K Framework):** Configuration-driven operational systems optimizing complete programming language definitions into mathematical engines via matching logic.
*   **Boundary Limitation:** Captures structural transitions of the interpreter or rewrite framework. It lacks semantic support to naturally propagate and verify delegated authority obligations through the intermediate operational artifacts generated by rewrite steps.
