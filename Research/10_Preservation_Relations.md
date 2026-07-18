# 10: Preservation Relations
**Status:** LOCKED  

## Purpose
Exhaustively catalog every major preservation theorem in computer science history. Determine if our target relation—Semantic Consequence Preservation—is a completely distinct property or if it can be expressed as a specialized refinement of an established preservation theorem.

## Dependencies
*   [02_Domain_Model.md](02_Domain_Model.md)
*   [07_Correspondence_Survey.md](07_Correspondence_Survey.md)

---

## 1. Taxonomy of Preservation Theorems

We compile and evaluate the classical preservation properties defined by the programming languages, verification, and security research communities.

### Preservation Theorem Mapping Matrix

| Academic Community | Core Theorem Type | Object Formally Preserved Across the Mapping | Primary Open Gap / Divergence from our Target Relation |
| --- | --- | --- | --- |
| **Type Systems** | Type Preservation (Subject Reduction) | Evaluated terms retain their type invariants across step-reductions: $e : \tau \wedge e \to e' \implies e' : \tau$. | Bounded to internal language type-safety; does not model or carry out-of-band delegation invariants through dynamic planning or execution plan synthesis. |
| **Program Logics (Hoare)** | Invariant Preservation | Multi-state loop or execution transitions preserve foundational assertion predicates. | Assumes a statically bound, pre-analyzed program space. Cannot map dynamic runtime-derived executions where the translation engine itself is under adversarial pressure. |
| **Refinement Calculi** | Behavioral Refinement | Concrete operational traces remain a valid subset of allowed abstract behaviors. | Assumes compile-time or static translation paths. Lacks mechanisms to handle dynamic authority context shifts dynamically embedded inside non-deterministic input parameters. |
| **Secure Compilation** | Robust Safety / Hyperproperty Preservation (RSP/RHP) | Source-level safety properties ($\phi$) are preserved against all target-level adversarial contexts ($\text{Context}$): $\text{Target} \sim_{\text{RSP}} \text{Source}$. | Focuses on translating fixed source programs to lower-level binaries safely. It does not model execution environments whose explicit runtime task is to derive and execute brand new, arbitrary query plans or workflows based on incoming delegation objects ($\Lambda$). |
| **Capability Systems** | Confinement & Authority Preservation | Graph reachability metrics guarantee that references can never be leaked to un-delegated principals. | Purely structural and connectivity-focused. It verifies reference boundary traversal but is fundamentally blind to whether the semantic meaning or exact arguments of an operational payload ($e$) reflect the delegated intent. |

---

## 2. Comparing with the Target Predicate

Our target relation represents the preservation of a delegated obligation across a runtime derivation process:

$$\Sigma \models \text{Preserves}(\Lambda, e)$$

Where the terminal target action $e$ is synthesized through an unfixed evaluation trace under the constraints of delegation context $\Lambda$.

*   **Divergence from Type Systems:** Type preservation ensures that reduction steps do not produce ill-typed terms. It is blind to the behavioral correctness of the synthesized execution plans. A query planner can compile a query to a validly typed `Delete` term that deletes the wrong database table: the term is type-safe, but the delegated authority obligation has been violated.
*   **Divergence from Secure Compilation:** Secure compilation (e.g., RSP) guarantees that compiling a program does not introduce vulnerabilities that allow target-level adversaries to violate source-level safety properties. The source program itself is fixed. In our target model, the source program is not fixed—it is dynamic input ($I$) carrying credentials, which is evaluated on-the-fly to derive an execution trace.
*   **Divergence from Hoare Logic Invariant Preservation:** Invariant preservation proves that a loop step preserves a state predicate (e.g., $i \le N$). It requires knowing the program text ($c$) statically. It cannot model proof-obligation inheritance where the program code ($c$) is generated dynamically at runtime by a query planner or interpreter under the influence of adversarial inputs.

## 3. Finding

Semantic Consequence Preservation ($\Sigma \models \text{Preserves}(\Lambda, e)$) is a **distinct property** that cannot be expressed as a direct refinement of type preservation, secure compilation, or capability confinement. The primary gap is that existing theorems require the evaluation relation or program text to be statically fixed before execution begins, failing to express proof-obligation preservation through runtime derivations.
