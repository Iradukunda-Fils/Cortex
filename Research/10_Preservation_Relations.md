# 10: Preservation Relations
**Status:** LOCKED  

## Purpose
Exhaustively catalog and taxonomize major preservation theorems spanning programming languages, verified compilers, secure compilation, and security architectures. Establish the precise relation between our target predicate ($\Sigma \models \text{Preserves}(\Lambda, e)$) and established properties.

## Dependencies
*   [02_Domain_Model.md](02_Domain_Model.md)
*   [07_Correspondence_Survey.md](07_Correspondence_Survey.md)

---

## 1. Classification Methodology

To prevent semantic conflation, every preservation theorem class in this taxonomy is classified across four strict dimensions:
1.  **Object Preserved**: The logical structure, invariant, type, or property that remains invariant.
2.  **Foundational Relation**: The mathematical or logical equation/reduction relation validating the preservation.
3.  **Proof Style**: The primary proof technique employed in the literature (e.g., structural induction, simulation, back-translation).
4.  **Core Environmental Assumptions**: The systemic baseline requirements assumed (e.g., closed world, compiler correctness, platform isolation).

---

## 2. Expanded Taxonomy of Preservation Theorems

### 2.1 Type Preservation (Subject Reduction)
*   **Object Preserved**: Static Type Invariant ($\tau$).
*   **Foundational Relation**: $e : \tau \wedge e \to e' \implies e' : \tau$.
*   **Proof Style**: Structural induction over term derivation trees and evaluation step reductions.
*   **Core Environmental Assumptions**: Closed system semantics; type-safety of all language primitives; absence of untyped memory writes, arbitrary FFI calls, or JIT assembly injection.

### 2.2 Semantic Preservation (Compiler Correctness)
*   **Object Preserved**: Execution semantics / observable behaviors of a source program.
*   **Foundational Relation**: $\text{beh}(\llbracket P \rrbracket_T) \subseteq \text{beh}(P_S)$ (where $\text{beh}$ captures traces of inputs/outputs).
*   **Proof Style**: Stepwise simulation relations (forward/backward simulation proofs) between source and target abstract machine configurations.
*   **Core Environmental Assumptions**: Whole-program translation; non-adversarial target environment (the compiled output is run in an environment that behaves strictly as defined by the target architecture).

### 2.3 Behavioral Refinement Preservation
*   **Object Preserved**: Abstract specifications / state invariants.
*   **Foundational Relation**: Concrete Trace $\sqsubseteq$ Specification Trace (under a state mapper $\alpha$).
*   **Proof Style**: Data refinement verification; inductive proof of simulation relations between abstract and concrete state transition steps.
*   **Core Environmental Assumptions**: Deterministic behavior or bounded non-determinism of the environment; complete pre-definability of the state mapping relations.

### 2.4 Observational / Contextual Equivalence
*   **Object Preserved**: Semantic indistinguishability of terms under arbitrary contexts.
*   **Foundational Relation**: $P_1 \approx_{ctx} P_2 \iff \forall C, C[P_1] \Downarrow \iff C[P_2] \Downarrow$.
*   **Proof Style**: Logical relations, bisimulation games, or coinductive proof maps.
*   **Core Environmental Assumptions**: Restricting the context $C$ to standard, well-typed language contexts; absence of out-of-band context capabilities or platform exploits.

### 2.5 Hyperproperty Preservation (Robust Hyperproperty Preservation - RHP)
*   **Object Preserved**: Sets of execution traces (e.g., non-leakage, security hyperproperties).
*   **Foundational Relation**: Trace set containment under arbitrary contextual configurations.
*   **Proof Style**: Contextual simulation games or back-translation of target counterexamples back to the source.
*   **Core Environmental Assumptions**: Target-level contexts cannot bypass hardware or compiler memory segment boundaries.

### 2.6 Security Preservation (Robust Safety Preservation - RSP)
*   **Object Preserved**: Source-level safety properties ($\phi$).
*   **Foundational Relation**: $\forall \text{Ctx}_{\text{Target}}, \exists \text{Ctx}_{\text{Source}}$ such that target safety violation implies source safety violation.
*   **Proof Style**: Back-translation of target-level contexts to source-level contexts, or simulation relations.
*   **Core Environmental Assumptions**: The target execution context cannot violate the core isolation primitives (e.g., memory safety or execution alignment) promised by the target platform architecture.

### 2.7 Information Flow Preservation (Non-Interference)
*   **Object Preserved**: Low-equivalence trace indistinguishability.
*   **Foundational Relation**: $s_1 \approx_L s_2 \implies \text{eval}(s_1) \approx_L \text{eval}(s_2)$.
*   **Proof Style**: Relational structural induction or type-directed information tracking (relational Hoare logic).
*   **Core Environmental Assumptions**: Deterministic evaluation semantics or bounded probabilistic non-determinism; absence of structural timing or microarchitectural side-channels.

### 2.8 Capability / Confinement Preservation
*   **Object Preserved**: Capability graph reachability boundary (non-leakage of references).
*   **Foundational Relation**: $R \in \text{Reach}(G_t) \implies R \in \text{Reach}(G_{t_0}) \cup \text{Created}(G_{t_0, t})$.
*   **Proof Style**: Inductive path checking over capability transfer operations and graph transition systems.
*   **Core Environmental Assumptions**: Unforgeability of capabilities; reference evaluation boundary cannot be bypassed by operating system bugs or physical memory attacks.

### 2.9 Invariant / Assertion Preservation
*   **Object Preserved**: Loop invariants or Hoare preconditions.
*   **Foundational Relation**: $\{P\} \, C \, \{Q\}$ where $P$ is preserved across execution transitions of program statement $C$.
*   **Proof Style**: Deductive proof using verification condition generators (VCGs) and solver assertions.
*   **Core Environmental Assumptions**: Fixed program code $C$ at proof time; absence of self-modifying code or runtime-synthesized execution statements.

---

## 3. Position of the Target Predicate

Comparing our target predicate:

$$\Sigma \models \text{Preserves}(\Lambda, e)$$

We analyze how it relates to these categories:
1.  **Divergence from Type Preservation**: Subject reduction guarantees that terms remain well-typed. It is structurally blind to downstream authority bounds ($\Lambda$) inherited by compiled or interpreted plans.
2.  **Divergence from Robust Safety Preservation (RSP)**: RSP ensures that target-level contexts cannot violate safety properties verified at the source. This assumes a fixed program. Our target relation assumes the program or execution strategy is dynamically translated into an intermediate operational artifact ($\mathcal{A}$) consuming non-deterministic inputs at runtime.
3.  **Divergence from Invariant Preservation**: Standard invariant preservation requires knowing the state transition instructions statically. It cannot model situations where the operational steps are dynamically generated by an evaluation engine (Case C mutability) operating under user-influenced parameters.

Therefore, **Semantic Consequence Preservation** remains a distinct semantic property—it represents the preservation of a delegated authority obligation ($\Lambda$) across the evaluation and enactment of a dynamically generated operational artifact ($\mathcal{A}$) under an adversarial execution model.
