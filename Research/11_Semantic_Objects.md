# 11: Semantic Objects
**Status:** LOCKED

## 1. Purpose and Scope
This document establishes the structural ontology for the entire research program. Before conducting comparative literature surveys across distinct computer science disciplines, we must establish a rigorous, uniform vocabulary to describe the underlying mathematics.

Different research communities—ranging from language design to database engines and systems engineering—frequently use the same words to mean different things, or use distinct terminology to describe structurally similar mathematical objects. This document serves as a descriptive reference rather than an evaluative critique. It establishes a neutral, standardized classification framework to prevent the accidental conflation of distinct semantic layers during subsequent literature analysis.

## 2. Foundational Vocabulary
To maintain complete methodological neutrality and precision, we define the foundational components of our semantic ontology. These terms act as the common language for all subsequent survey modules.

*   **Semantic Domain:** A formal mathematical space or structure (such as a set, a partially ordered set/poset, a lattice, a category, or an inductive universe) that defines the valid bounds and structural laws for all entities residing within it.
*   **Semantic Object:** A discrete mathematical entity or element that inhabits a specific semantic domain (e.g., a specific state $\sigma$ within a state space $\Sigma$, or a distinct derivation tree $\mathcal{D}$ within an inductive system).
*   **Semantic Relation:** A mathematical relationship established between two or more semantic objects (e.g., a transition relation $\to$, a simulation relation $\sim$, or a logical entailment $\vdash$).
*   **Semantic Property:** A high-level predicate, property, or invariant that holds over semantic relations or sets of traces (e.g., type safety, non-interference, robust property preservation, or admissibility).
*   **Judgment:** A formal assertion within a specific deductive system that states a particular semantic relation or property holds true under given assumptions (e.g., the typing judgment $\Gamma \vdash e : \tau$).
*   **Environment / Context:** A semantic object containing ambient information, bounds, variables, or mappings that parameterize evaluation, derivation, or enforcement procedures (e.g., variable environments $\rho$, heap states $h$, or an abstract delegation context $\Lambda$).

### The Four-Layer Conceptual Stratification
To ensure absolute clarity, every framework evaluated in this research program must be deconstructed into four distinct layers:

$$\text{Semantic Domain} \longrightarrow \text{Semantic Object} \longrightarrow \text{Semantic Relation} \longrightarrow \text{Semantic Property}$$

*   **Layer 1: Semantic Domains** (What mathematical spaces exist?)
*   **Layer 2: Semantic Objects** (What entities inhabit those spaces?)
*   **Layer 3: Semantic Relations** (How are those objects related?)
*   **Layer 4: Semantic Properties** (What high-level invariants or predicates hold over those relations?)

## 3. Cross-Disciplinary Domain/Object Matrix
The following matrix maps the exact mathematical spaces and primary entities manipulated across the different computer science traditions under survey.

| Semantics Community | Layer 1: Semantic Domain (Space) | Layer 2: Primary Semantic Object | Layer 3: Representative Semantic Relation | Layer 4: Primary Semantic Property |
| --- | --- | --- | --- | --- |
| **Structural Operational Semantics** | Inductive rule universes over language syntax | Derivation Tree ($\mathcal{D}$) | Evaluation transition relation ($\Downarrow$) | Subject Reduction (Type Preservation) |
| **Abstract Machines** | Product space of registers, stacks, and memory heaps | Machine State Configuration ($c$) | Small-step state reduction ($c \to c'$) | Determinism / Progress |
| **Trace Semantics** | Languages over execution event alphabets ($\Sigma^{\infty}$) | Sequential or Branching Trace ($\tau$) | Prefix closure, trace inclusion ($\tau_1 \subseteq \tau_2$) | Safety and Liveness Hyperproperties |
| **Program Logics (Hoare / Separation)** | First-order logic lattices over valuations or spatial resources | State Assertion Formula ($P, Q$), Spatial Heap Predicate ($\phi$) | Logical entailment ($\vdash$), Frame rule composition ($\ast$) | Partial / Total Program Correctness |
| **Capability Systems** | Directed reference graphs over protection domains | Capability Reference Edge ($c$) | Graph reachability, capability invocation | Confinement, Principle of Least Privilege |
| **Authorization Logics** | Inductive modal deductive universes | Logical Statement Judgment ($K \text{ says } \phi$) | Logical derivation / context extension | Delegation Monotonicity / Soundness |
| **Data & System Provenance** | Ancestral dependency spaces | Directed Acyclic Graph ($G$) | Causal ancestry relationship ($\xrightarrow{\text{causal}}$) | Auditability, Lineage Integrity |
| **Information Flow Control** | Security clearance lattices | Labeled State Variable ($x_L$) | Information flow dependency bounds | Non-Interference |
| **Secure Compilation** | Contextual interaction and behavioral spaces | Context Pair ($\text{Ctx}_T, \text{Ctx}_S$), Execution trace fragments | Contextual equivalence ($\approx$), Simulation relations | Robust Safety / Hyperproperty Preservation |
| **Proof-Carrying Code** | Dependently typed $\lambda$-calculus spaces | Proof Term Object ($M$), Typing Witness | Proof verification, type checking | Safety Invariant Compliance |
| **Rewriting Logic & Executable Semantics** | Equational algebraic equivalence classes ($T_{\Sigma, E}$) | Equational State Term ($t$) | Concurrent rewriting sequence ($t \xrightarrow{\ast} t'$) | Confluence, Coherence |
| **Runtime Verification** | Automata or temporal logic variant spaces | Enforcement Monitor State, Temporal Trace Monitor | Monitor tracking step reduction ($\sigma \xrightarrow{a} \sigma'$) | Online Trace Compliance / Shield Invariants |

## 4. The "Operational Artifact" Survey Abstraction
For the purposes of this survey, we introduce the term **Operational Artifact ($\mathcal{A}$)** as a neutral, high-level survey abstraction.

> **Definitional Caveat:**
> The term *Operational Artifact* is employed purely as a descriptive convenience within this literature review to encompass intermediate entities that are produced by an execution procedure and subsequently interpreted to influence externally observable behavior. This designation is a structural placeholder to allow comparison across fields; it is not a claim that all such intermediate entities (e.g., a SQL physical query plan, a K Framework configuration term, a distributed task DAG, or a Coq proof witness) are mathematically identical, isomorphic, or reducible to one another.

Within our abstracted structural framework, an Operational Artifact $\mathcal{A}$ interfaces with the system components through the following lifecycle roles:

*   **Inputs:** Primary elements provided to the system from external domains, typically comprising a non-deterministic input stream ($I$), an ambient starting state ($\Sigma$), and a Delegation Context ($\Lambda$) which abstractly constrains permissible behavior.
*   **Intermediate Artifacts:** The category inhabited by the Operational Artifact ($\mathcal{A}$). It is the concrete payload generated by a system's internal Derivation Procedure ($\xrightarrow{\text{derive}}$).
*   **Observations:** The intermediate operational steps, state traces ($\tau$), or structural alterations that are exposed to an external environment or adversary during evaluation.
*   **Effects:** The terminal, irreversible actions ($e \in E_{\text{irreversible}}$) generated through the system's Enforcement Procedure ($\xrightarrow{\text{enact}}$).
*   **Proof Objects:** Meta-logical certificates or typing witnesses generated alongside or embedded inside $\mathcal{A}$ to prove that the proposed enactment matches the structural parameters specified by the language or framework rules.

## 5. Cross-Disciplinary Structural Crosswalk
While different computing paradigms maintain independent vocabularies, they frequently manipulate concepts with clear structural or functional commonalities. This crosswalk provides an initial semantic mapping to guide our cross-field evaluations.

*   **Delegation Constraints vs. Types:** A Delegation Context ($\Lambda$) functions structurally like a dynamic, open-world Refinement Type or Effect Capability. Where a traditional type system limits variable values to valid structural operations, a delegation system restricts execution entities to valid authority parameters.
*   **Query/Workflow Plans vs. Derivation Trees:** A database physical query plan or a distributed workflow graph operates as a macroscopic Operational Derivation Tree. Instead of directing small-step AST evaluations, it directs large-scale resource actions, yet both function as an intermediate blueprint guiding enforcement engines.
*   **Reference Monitors vs. Runtime Monitors:** A capability-based reference monitor and an execution assurance Runtime Verification Monitor are functional duals. The reference monitor evaluates whether a requested action is structurally allowed by the presence of a token *before* execution, whereas the runtime verification monitor continuously analyzes the trace ($\tau$) *during* execution to detect or suppress out-of-bounds transitions.

## 6. Open Conceptual Questions
The following structural mappings remain explicitly open and will form the core focus of the cross-disciplinary literature surveys:

*   Can the structural relationship between a Delegation Context ($\Lambda$) and an Operational Artifact ($\mathcal{A}$) be formally captured as a standard membership or refinement relation ($\mathcal{A} \in \text{Adm}(\Lambda)$), or does it necessitate a state-dependent modal logic constraint?
*   Under what exact observation models does the preservation of an authority constraint collapse into a standard trace safety property, and under what observation models does it inherently require a relational hyperproperty?
*   How do different semantic communities handle the potential for the execution environment itself to mutate the delegation state ($\Lambda_t \to \Lambda_{t+1}$) during active enactment without breaking non-interference or type safety guarantees?
