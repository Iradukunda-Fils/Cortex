# 10: Semantic Relations
**Status:** LOCKED

## 1. Purpose and Scope
This document surveys the mathematical relations used to analyze, verify, and prove equivalence or preservation properties across computer science formalisms. Operating as the mathematical center of this repository, this module draws directly from the ontologies of `11_Semantic_Objects.md`, the attacker metrics of `12_Threat_Model.md`, the operational models of `08_Evaluation_Relations.md`, and the authority/assurance taxonomies of `09_Authority_Semantics.md` and `13_Runtime_Assurance.md`.

Rather than treating "preservation" as an isolated phenomenon, this document conducts a comprehensive literature survey of the broader universe of Semantic Relations. We catalog how different programming language and formal methods communities prove that properties, behaviors, or resource configurations survive transformations across abstract execution boundaries. The objective is to map out existing relational tools to determine whether any surveyed structure already captures the propagation of authority constraints across untrusted derivation interfaces.

## 2. A Taxonomy of Semantic Relations
To organize the extensive formal literature, we classify semantic relations into six primary structural families based on their mathematical form:

```text
                         [ SEMANTIC RELATIONS ]
                                   │
     ┌───────────────┬─────────────┼─────────────┬───────────────┐
     ▼               ▼             ▼             ▼               ▼
[ Equivalence ] [ Simulation ] [ Refinement ] [ Logical Rel. ] [ Preservation ]
  ├── Contextual  ├── Forward    ├── Data       ├── Kripke       ├── Structural
  └── Bisimulation└── Backward   └── Context    └── Step-Indexed └── Hyperproperty
```

*   **Equivalence Relations:** Symmetric, reflexive, and transitive relations establishing that two semantic terms or systems exhibit identical observable behavior under all valid perturbations.
*   **Simulation Relations:** Directional mappings between transition systems that establish how steps taken by a source system can be matched by a target system.
*   **Refinement Relations:** Mappings that show a concrete system restricts the non-deterministic behaviors of an abstract specification while preserving its safety properties.
*   **Logical Relations:** Type-indexed relational frameworks that define equivalence by induction on the structure of types, extensively utilized for higher-order languages.
*   **Preservation Relations:** Invariant assertions demonstrating that specific properties (e.g., types, effects, or security configurations) remain stable under evaluation steps or structural lowering.
*   **Correspondence Relations:** Macro-level synthesis relations asserting that an entire framework execution pipeline (e.g., a compiler or query optimizer) faithfully preserves source intents within a target landscape.

## 3. Simulation and Equivalence Relations
When comparing transition systems, the literature relies on structural simulations to track execution traces:

*   **Forward Simulation:** Establishes that if an abstract system takes a step, a concrete system can mirror that transition. Let $S$ be the source state and $T$ be the target state. A relation $R$ is a forward simulation if:
    $$\forall s, s', t. \quad (s, t) \in R \land s \to_S s' \implies \exists t'. \quad t \to_T^* t' \land (s', t') \in R$$
*   **Backward Simulation:** Proves that if a target system takes a step, it must correspond to a valid historical path in the source system. Crucial for verifying non-deterministic systems where choices are deferred.
*   **Bisimulation** (Milner 1980, Park 1981): A symmetric simulation where two systems mutually simulate each other step-for-step, establishing strict behavioral equivalence.
*   **Stuttering and Lock-Step Variants:** Lock-step requires an exact 1:1 match of execution steps. Stuttering simulations (Milner 1989) permit one system to take multiple internal, unobservable steps ($\tau$-transitions) before matching the other's state change.
*   **Contextual Equivalence:** Two terms are contextually equivalent ($M \approx_{\text{ctx}} N$) if they yield identical observable outcomes when plugged into any valid program context $C[\cdot]$.

## 4. Refinement Relations
Refinement calculus transforms an abstract, declarative specification into a concrete executable implementation through step-by-step constraint narrowing.

*   **Data Refinement** (Hoare 1972): Mappings that translate abstract mathematical data types (e.g., sets) into concrete machine data structures (e.g., bit arrays) while preserving operations.
*   **Behavioral Refinement:** Establishes that the set of observable execution traces of a concrete system ($\text{Traces}(C)$) is a strict subset of the traces permitted by an abstract specification ($\text{Traces}(A)$):
    $$\text{Traces}(C) \subseteq \text{Traces}(A)$$
*   **Context Refinement:** Used extensively in secure compilation to demonstrate that a target program does not introduce new behaviors or vulnerabilities when exposed to arbitrary target language contexts that lack source-level equivalents.

## 5. Logical Relations
Logical relations interpret equivalence based on type structures rather than tracking raw state transitions directly.

*   **Parametricity** (Reynolds 1983): Proves that polymorphic programs must behave uniformly regardless of the concrete data types passed to them, enabling representation independence theorems.
*   **Kripke Logical Relations:** Extends traditional logical relations to stateful or imperative languages by indexing the relation over a Kripke world or accessibility model ($w$) that represents the evolution of memory layouts or environment variants.
*   **Step-Indexed Logical Relations** (Appel and McAllester 2001): Resolves circularity issues encountered when modeling higher-order mutable stores by indexing the relation over a natural number $n$, representing the number of execution steps remaining for validation:
    $$(M, N) \in \llbracket \tau \rrbracket_n$$

## 6. Preservation Relations and Hyperproperties
Preservation properties guarantee that an invariant holds stable across execution transitions or transformations. We classify these targets based on what they preserve:

### 6.1 Structural & Type Preservation
*   **Subject Reduction:** The foundation of modern syntactic type safety proofs (Wright and Felleisen 1994). It establishes that if a well-typed term steps, its type is invariant:
    $$\Gamma \vdash e : \tau \land e \to e' \implies \Gamma \vdash e' : \tau$$
*   **Progress:** Complements subject reduction by proving a well-typed term is never stuck: it is either a terminal value or can take a step.

### 6.2 Property and Hyperproperty Preservation
*   **Trace Safety Properties:** Properties verifiable by inspecting single execution traces independently (e.g., "the program never accesses unallocated memory").
*   **Hyperproperties** (Clarkson and Schneider 2010): Properties that cannot be verified by looking at a single trace, defined instead as sets of sets of traces. Non-interference is a classic hyperproperty requiring the comparison of multiple execution traces side-by-side.
*   **Robust Hyperproperty Preservation (RHP):** The gold standard in secure compilation. It asserts that a hyperproperty $\mathcal{H}$ holds robustly for a source program $P$ under all source contexts if and only if its compiled variant $\llbracket P \rrbracket$ preserves that hyperproperty under all target contexts:
    $$\forall C_T. \quad \text{Traces}(C_T[\llbracket P \rrbracket]) \in \mathcal{H}$$

## 7. The Comprehensive Preservation Target Matrix
To trace how different properties map onto these formal frameworks, we construct a unified reference landscape of literature targets:

| Preservation Target | Classic Structural Theorem | Primary Mathematical Engine | Focus Domain |
| --- | --- | --- | --- |
| **Semantic / Typing** | Subject Reduction / Progress | Inductive Type Derivations | PL Type Safety |
| **Behavioral** | Backward / Forward Simulation| Bisimulation / Trace Inclusion | Compiler Correctness |
| **Authority** | Capability Confinement | Take-Grant Graphs / Spatial Logics | O-Cap Systems |
| **Resource** | Substructural Frame Elimination | Partial Commutative Monoids | Separation Logic |
| **Information Flow**| Non-Interference | Robust Hyperproperty Mappings | Information Security |
| **Temporal Safety** | Trace Inclusion | LTL / Büchi Automata Monotonicity | Runtime Verification |

## 8. The Authority-Specific Relation Gap
By cross-referencing our complete catalog of semantic relations, a critical structural limitation across existing formal methods literature becomes evident:

> **The Core Relational Disconnect:**
> *   **Compiler Correctness** and Simulation relations ($\approx$) assume a trusted derivation engine. They focus on proving that target behaviors match source behaviors under the assumption that the transformation process itself is correct.
> *   **Secure Compilation** and Robust Preservation frameworks analyze untrusted target contexts ($C_T$), but they still assume the compiler itself is trusted. They do not evaluate a pipeline where the intermediate operational artifact $\mathcal{A}$ is produced by an unverified or adversarial source ($c_{\text{derive\_impl}}$).
> *   **Authorization Logics** and O-Cap Confinement models provide clean methods to reason about authority state shifts ($\Lambda_t \to \Lambda_{t+1}$), but they lack the relational tools to tie these proofs down to unverified intermediate artifacts ($\mathcal{A}$) passing through optimized enforcement engines ($\xrightarrow{\text{enact}}$).

Consequently, there is no standardized, pre-existing semantic relation in the literature that natively captures the preservation of dynamic authority constraints under a condition where an untrusted operational artifact $\mathcal{A}$ is evaluated by a decoupled enactment engine.

## 9. Open Conceptual Questions Feeding the Correspondence Survey
The architectural conclusions of this relational survey define three precise vectors that must be resolved in our final comparative synthesis:

*   Can the interaction between a dynamic authority context ($\Lambda_t$) and an untrusted operational artifact ($\mathcal{A}$) be naturally expressed as a step-indexed logical relation, where the step-index $n$ bounds both execution steps and delegation lifetimes?
*   Does proving authority confinement across a decoupled interface require a full relational hyperproperty mapping, or can it be reduced to a behavioral trace refinement property by tracking the monitor state ($m$) as part of a simulation?
*   What structural definition must a new relation possess to prove that an enactment engine operating under an Artifact observer projection ($\mathcal{O}_{\text{art}}$) remains safe when executing an artifact whose derivation proof witness ($\pi$) has been stripped or modified by an adversary?
