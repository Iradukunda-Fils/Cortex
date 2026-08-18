# 07: Correspondence Survey
**Status:** LOCKED

## 1. Purpose and Scope
This document conducts the final comparative synthesis of the research program. Its purpose is to evaluate whether existing semantic correspondence, simulation, refinement, logical, or preservation relations can fully characterize the following working hypothesis under our normalized threat model:

$$H_{\text{prop}}: \text{Does there exist a semantic relation } R \text{ such that } R(\Lambda_t, \mathcal{A}, \tau, e) \implies (\Sigma, \Lambda_t, e) \models \text{Allowed}?$$

This survey rejects default assumptions of novelty. It establishes a falsifiable methodological pathway: if an existing relation captures this property, the research contribution must be reframed as a specialization, engineering instantiation, or empirical evaluation of that relation.

## 2. The Target Correspondence Relation
To maintain analytical neutrality, we define the target relation in its weakest possible form, avoiding premature commitment to any specific mathematical classification:

$$R_{\text{target}}(\Lambda_t, \mathcal{A}, \tau, e)$$

Where:
*   $\Lambda_t$ is the dynamic authority context at execution time $t$, representing the active delegation boundaries, cryptographic capabilities, and security metadata defined by the system policy.
*   $\mathcal{A}$ is the intermediate operational artifact produced by an untrusted or partially trusted derivation procedure ($c_{\text{derive\_impl}}$).
*   $\tau$ is the execution trace generated during the execution or enactment phase.
*   $e$ is the externally observable terminal effect or state mutation produced by the enactment engine.

The relation must be evaluated under the adversary capability $c_{\text{arbitrary\_dev}}$, where the derivation engine may inject an arbitrary, corrupted, or structurally invalid operational artifact $\mathcal{A}$ into the enactment interface.

## 3. Comparative Correspondence Matrix
We evaluate $R_{\text{target}}$ against the foundational families of semantic relations established in the formal programming languages and verification literature:

| Framework Family | Core Relational Operator | Focus Context | Analytical Boundary |
| --- | --- | --- | --- |
| **Hoare Logic** | $\{P\} \, C \, \{Q\}$ | Total/Partial Correctness | Requires a fixed, static program $C$; cannot model arbitrary artifact substitution. |
| **Refinement Calculus** | $S \sqsubseteq C$ | Correctness by Construction | Assumes a trusted derivation or transformation pipeline from specification to concrete code. |
| **Simulation Relations** | $R(s, t)$ | Operational Transition State | Relates abstract and concrete states, but presupposes structurally valid transition systems. |
| **Logical Relations** | $\llbracket \tau \rrbracket$ | Type-Indexed Behavioral Equivalence | Focuses on structural properties of types rather than binding external authority state to arbitrary artifacts. |
| **Secure Compilation** | $\text{RSP} / \text{RHP}$ | Contextual Property Preservation | Assumes a trusted compiler protecting against adversarial contexts, not adversarial derivation. |
| **Authorization Logics** | $\Gamma \vdash A \text{ says } \phi$ | Static/Dynamic Trust Delegation | Reasons about structural assertions, missing direct hooks to arbitrary operational artifacts. |
| **Runtime Verification** | $\mathcal{E}(\tau) = \tau'$ | Inline/Outline Execution Auditing | Enforces trace properties, but requires full embedding of authority semantics into the monitor state. |

## 4. The Falsification Protocol
To guarantee rigorous evaluation, every framework family is subjected to four distinct criteria to determine if it can cleanly express $R_{\text{target}}$:

*   **Subsumption Test:** Can the surveyed relation encode $R_{\text{target}}$ directly without adding non-standard semantic assumptions?
*   **Reduction Test:** Can $R_{\text{target}}$ be reduced to a known relation by extending the semantic state space with the authority context $\Lambda_t$ and the internal monitor state $m$?
*   **Threat-Model Test:** Does the relation remain valid and meaningful when the adversary capability $c_{\text{arbitrary\_dev}}$ is active?
*   **Observer-Projection Test:** Does the relation survive under the restricted projections $\mathcal{O}_{\text{art}}$ and $\mathcal{O}_{\text{trace}}$ without requiring full $\mathcal{O}_{\text{white}}$ visibility?

## 5. Candidate Reduction Pathways
We explicitly test the three strongest reduction pathways to evaluate if $R_{\text{target}}$ can be expressed using classical machinery.

### 5.1 Reduction to Simulation
We augment the execution state of the transition system to include authority and monitor information, yielding the relational states:
$$R\left((\Sigma, \Lambda_t, m), (\Sigma', \Lambda_t', m')\right)$$

*   **Analysis:** If the enactment engine handles arbitrary inputs safely via defensive runtime monitoring, this relation can be expressed as a standard Forward Simulation. The concrete system, running the untrusted artifact $\mathcal{A}$ under a monitor $m$, simulates a high-level abstract reference monitor that steps through valid policy transitions.
*   **Limitation:** A standard simulation requires that the target transition system remains structurally consistent. Under $c_{\text{arbitrary\_dev}}$, if $\mathcal{A}$ causes an illegal or undefined transition that bypasses the monitor, the simulation relation collapses entirely due to a failure of applicability.

### 5.2 Reduction to Logical Relations
We define a world-indexed relation where the Kripke world $w$ incorporates the current authority state, monitor constraints, and execution steps remaining:
$$w = (\Lambda_t, m, n)$$

*   **Analysis:** This mapping functions effectively if the generation of the operational artifact $\mathcal{A}$ can be typed, or if its evaluation can be indexed by a step-count $n$ to model delegation lifetimes.
*   **Limitation:** Because the derivation engine is untrusted ($c_{\text{arbitrary\_dev}}$), $\mathcal{A}$ does not possess a trusted type derivation. While a step-indexed logical relation can express the behavior of the enactment engine, it faces a failure of expressiveness when attempting to assert correctness properties over the artifact generation step itself.

### 5.3 Reduction to Hyperproperties
We define a set of permissible execution traces parameterized by the active authority context:
$$\mathcal{H}_{\Lambda} = \{\text{Traces}(P) \mid (\Sigma, \Lambda, e) \models \text{Allowed}\}$$

*   **Analysis:** If the security property requires comparing multiple traces—such as ensuring that an adversary cannot deduce cryptographic capability keys across different runs—$R_{\text{target}}$ behaves as a true Hyperproperty.
*   **Limitation:** If the core security goal is simple safety (e.g., "never execute an unapproved effect"), $R_{\text{target}}$ does not require cross-trace analysis. It collapses into a unary trace safety property, making a full hyperproperty framing expressive but functionally redundant.

## 6. Methodological Correction: Applicability vs. Expressiveness
A critical formal distinction must be maintained when evaluating existing verification frameworks under the capability $c_{\text{arbitrary\_dev}}$:

*   **Failure of Applicability:** The existing theorem or relation is theoretically capable of expressing the desired property, but its foundational assumptions are violated. For example, a type preservation theorem cannot be applied to an artifact $\mathcal{A}$ because the adversarial derivation engine bypassed the type-checker. The theorem is structurally sound, but its preconditions are broken.
*   **Failure of Expressiveness:** The theorem or relation can be applied to the system, but its mathematical language cannot encode $R_{\text{target}}$ even when all its premises are satisfied. For example, standard Hoare triple semantics cannot express a property that depends on structural changes across an arbitrary, unmapped artifact substitution.

This distinction ensures the research program survives strict peer review by ensuring we do not mischaracterize a broken precondition as a lack of expressive power in the underlying formalism.

## 7. Strategic Synthesis and Conclusions
Based on our formal evaluation protocol and reduction tests, we arrive at a definitive three-way classification for the target relation:

```text
                  [ EVALUATION OF H_prop ]
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
[ SUBSUMED ]           [ SPECIALIZED ]         [ IRREDUCIBLE ]
  No new machinery.      Constrained extension   Fundamentally new
  Standard framework     of Logical Relations/   semantic structures
  applies directly.      Hyperproperties.        required.
                             │
                             ▼
                 ===> [ CURRENT STATUS ] <===
            Specialized Composed Relation (Working Label)
```

### 7.1 Subsumed
$R_{\text{target}}$ is **not** fully subsumed by standard, out-of-the-box relations (e.g., standard Hoare Logic or basic simulation) because these systems assume a trusted codebase or a fixed program configuration, failing under $c_{\text{arbitrary\_dev}}$.

### 7.2 Specialized Composed Relation (Working Label)
The current evidence suggests that $R_{\text{target}}$ may be expressible as a composed relation built entirely from existing semantic machinery—specifically, a step-indexed Kripke logical relation over dynamic authority worlds, combined with a trace-safety refinement relation over monitored execution traces. The term "Specialized Composed Relation" is therefore used exclusively as a **provisional working label** for this specific composition, not as a claim that a fundamentally new semantic category has been discovered.

The challenge shifts from inventing new mathematical primitives to executing this formal composition rigorously, proving whether it can absorb the structural violations introduced under the adversary capability $c_{\text{arbitrary\_dev}}$.

### 7.3 Irreducible
We **reject** the claim of total irreducibility. The system does not require abandoning established formal methods; rather, it demands the intentional composition of simulation states and dynamic policy contexts to bridge the gap between untrusted artifact derivation and runtime enactment.
