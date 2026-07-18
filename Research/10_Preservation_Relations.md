# 10: Preservation Relations
**Status:** LOCKED  

## Purpose
Exhaustively catalog and taxonomize major preservation theorems, simulation relations, and logical relations. Establish the precise relation between our working hypothesis ($H_{\text{prop}}$) and established properties, exploring why our problem avoids classification as a standard logical relation.

## Dependencies
*   [02_Domain_Model.md](02_Domain_Model.md)
*   [07_Correspondence_Survey.md](07_Correspondence_Survey.md)

---

## 1. Preservation & Correctness Framework

The formal correctness of computer systems is structurally verified through semantic preservation across evaluation steps or translation passes. We map the literature across this unified framework:

```text
Preservation & Correctness Framework
├── Preservation Theorems
│   ├── Type Preservation (Subject Reduction)
│   ├── Invariant / Assertion Preservation
│   ├── Robust Safety Preservation (RSP)
│   └── Robust Hyperproperty Preservation (RHP)
├── Simulation Relations
│   ├── Forward Simulation
│   ├── Backward Simulation
│   ├── Bisimulation
│   └── Trace Inclusion & Contextual Equivalence
└── Logical Relations
    ├── Kripke Logical Relations (World-Indexed)
    └── Step-Indexed Logical Relations
```

---

## 2. Expanded Taxonomy of Preservation Theorems

To prevent semantic conflation, every preservation theorem class in this taxonomy is classified across four strict dimensions:
1.  **Object Preserved**: The logical structure, invariant, type, or property that remains invariant.
2.  **Foundational Relation**: The mathematical or logical equation/reduction relation validating the preservation.
3.  **Proof Style**: The primary proof technique employed in the literature.
4.  **Core Environmental Assumptions**: The systemic baseline requirements assumed.

### 2.1 Type Preservation (Subject Reduction)
*   **Object Preserved**: Static Type Invariant ($\tau$).
*   **Foundational Relation**: $e : \tau \wedge e \to e' \implies e' : \tau$.
*   **Proof Style**: Structural induction over term derivation trees and evaluation step reductions.
*   **Core Environmental Assumptions**: Closed system semantics; type-safety of all language primitives; absence of untyped memory writes, arbitrary FFI calls, or JIT assembly injection.

### 2.2 Semantic Preservation (Compiler Correctness / Forward Simulation)
*   **Object Preserved**: Execution semantics / observable behaviors of a source program.
*   **Foundational Relation**: $\text{beh}(\llbracket P \rrbracket_T) \subseteq \text{beh}(P_S)$.
*   **Proof Style**: Stepwise simulation relations (forward/backward simulation proofs) establishing strict trace inclusion between abstract and concrete state transition steps.
*   **Core Environmental Assumptions**: Whole-program translation; non-adversarial target environment.

### 2.3 Observational / Contextual Equivalence (Logical Relations)
*   **Object Preserved**: Semantic indistinguishability of terms under arbitrary contexts.
*   **Foundational Relation**: $P_1 \approx_{ctx} P_2 \iff \forall C, C[P_1] \Downarrow \iff C[P_2] \Downarrow$.
*   **Proof Style**: Step-indexed or Kripke logical relations, bisimulation games, or coinductive proof maps.
*   **Core Environmental Assumptions**: Restricting the context $C$ to standard, well-typed language contexts; absence of out-of-band context capabilities.

### 2.4 Hyperproperty Preservation (Robust Hyperproperty Preservation - RHP)
*   **Object Preserved**: Sets of execution traces (e.g., non-leakage, security hyperproperties).
*   **Foundational Relation**: Trace set containment under arbitrary contextual configurations.
*   **Proof Style**: Contextual simulation games or back-translation of target counterexamples back to the source.
*   **Core Environmental Assumptions**: Target-level contexts cannot bypass hardware or compiler memory segment boundaries.

### 2.5 Security Preservation (Robust Safety Preservation - RSP)
*   **Object Preserved**: Source-level safety properties ($\phi$).
*   **Foundational Relation**: $\forall \text{Ctx}_{\text{Target}}, \exists \text{Ctx}_{\text{Source}}$ such that target safety violation implies source safety violation.
*   **Proof Style**: Back-translation of target-level contexts to source-level contexts, or simulation relations.
*   **Core Environmental Assumptions**: The target environment respects core isolation primitives (e.g., memory safety or execution alignment) promised by the platform architecture.

### 2.6 Information Flow Preservation (Non-Interference)
*   **Object Preserved**: Low-equivalence trace indistinguishability.
*   **Foundational Relation**: $s_1 \approx_L s_2 \implies \text{eval}(s_1) \approx_L \text{eval}(s_2)$.
*   **Proof Style**: Relational structural induction or type-directed information tracking (relational Hoare logic).
*   **Core Environmental Assumptions**: Deterministic evaluation semantics or bounded probabilistic non-determinism; absence of microarchitectural side-channels.

### 2.7 Capability / Confinement Preservation
*   **Object Preserved**: Capability graph reachability boundary (non-leakage of references).
*   **Foundational Relation**: $R \in \text{Reach}(G_t) \implies R \in \text{Reach}(G_{t_0}) \cup \text{Created}(G_{t_0, t})$.
*   **Proof Style**: Inductive path checking over capability transfer operations and graph transition systems.
*   **Core Environmental Assumptions**: Unforgeability of capabilities; reference evaluation boundary cannot be bypassed by operating system bugs or physical memory attacks.

### 2.8 Invariant / Assertion Preservation
*   **Object Preserved**: Loop invariants or Hoare preconditions.
*   **Foundational Relation**: $\{P\} \, C \, \{Q\}$ where $P$ is preserved across execution transitions of program statement $C$.
*   **Proof Style**: Deductive proof using verification condition generators (VCGs) and solver assertions.
*   **Core Environmental Assumptions**: Fixed program code $C$ at proof time; absence of self-modifying code or runtime-synthesized execution statements.

---

## 3. Position of the Target Predicate (Working Hypothesis)

Comparing our working proposition ($H_{\text{prop}}$), provisionally modeled as a Relational Hyperproperty over Traces:
$$\Sigma \models \text{Preserves}(\Lambda, e)$$

### 3.1 Unmapped Coverage
1.  **Divergence from Type Preservation**: Subject reduction guarantees that terms remain well-typed. It is structurally blind to downstream authority bounds ($\Lambda$) inherited by compiled or interpreted operational artifacts ($\mathcal{A}$).
2.  **Divergence from Robust Safety Preservation (RSP)**: RSP ensures that target-level contexts cannot violate safety properties verified at the source. This typically assumes a fixed source program. Our proposition assumes the operational artifact ($\mathcal{A}$) is translated and formulated dynamically, consuming non-deterministic inputs at runtime.

### 3.2 The Crucial Inquiry: Why Not a Logical Relation?
We must dedicate sufficient analytical rigor to evaluating whether our core problem can be elegantly subsumed by a Kripke or Step-Indexed Logical Relation. Logical relations are incredibly expressive at handling semantic boundaries (e.g., proving capability safety or compiler correctness across languages).

> **Logical Relations Posture:**
> While logical relations are highly expressive for establishing contextual equivalence or type-directed effect safety, we have not identified a standard formulation that directly models non-local, dynamically propagating delegated authority constraints ($\Lambda$) over multi-domain execution strategies without relying on static typing guarantees.

Since the operational artifact ($\mathcal{A}$) under our threat model operates over unverified intermediate states constructed from adversarial parameters, the standard inductive reliance on well-typedness fails. Therefore, within the scope of $H_{\text{prop}}$, Semantic Consequence Preservation is poised to remain a distinct, unmapped property.
