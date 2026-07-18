# 01: Research Methodology
**Status:** LOCKED  

## 1. Epistemological Framework

This research program operates via Adversarial Falsification and Elimination. Rather than attempting to prove the validity of a pre-conceptualized security architecture, the program dedicates its entire execution trajectory to validating the Null Hypothesis: that a rigorous composition of existing computer science disciplines completely resolves the safety boundaries of runtime decision attribution.

We utilize DSRP (Distinguishing Systems, Boundaries, Relationships, and Perspectives) to continuously map out where semantic boundaries shift when moving from static correspondence relations to runtime synthesis processes.

---

## 2. The Strict Semantic Inversion Stopping Rule

To prevent conceptual creep and confirmation bias, this methodology binds the research program to a strict, mandatory stopping rule.

**Mandatory Constraining Rule:** A new semantic primitive or structural obligation SHALL NOT be introduced into this research program unless **all** of the following conditions are simultaneously met:

1.  No existing semantic discipline or combination thereof fully satisfies the identified obligation under the stated threat model and assumptions.
2.  The obligation explicitly survives rigorous adversarial composition analysis against the strongest representative baselines in the literature.
3.  The obligation cannot be mathematically or logically expressed as a structural refinement of an existing primitive.
4.  The obligation is mathematically required to preserve at least one previously defined foundational safety property.

**Termination Clause:** If at any point a composition of existing standards satisfies these conditions, the research program immediately terminates its exploratory phase and pivots exclusively to compiling implementation and reference guidance for those existing standards.

---

## 3. Vocabulary Discipline

All foundational documents reason using explicit, uncompromised English terms. Mathematical shorthand notation is entirely prohibited until a symbol is earned via repetitive structural density across multiple composition evaluations. Premature formalization is treated as a form of confirmation bias.

---

## 4. The Status of the Target Architecture

The name "Cortex" is completely scrubbed from the active research vocabulary. It is no longer an asset, a layer, an SDK, or an item under design. It functions strictly as a non-normative conceptual placeholder representing: the hypothetical semantic layer that would only exist if adversarial analysis exhaustively proves that no existing composition of computer science disciplines satisfies the domain's required safety properties.

---

## 5. Research Question 0: Baseline Semantic Correspondence Survey

> **Mandatory Prerequisite.** Before any system-level composition is evaluated, the research program must establish that the proof obligation identified in $H_0$ is not simply a renamed version of a correspondence already fully proven by an existing discipline. This survey is the formal baseline for all subsequent adversarial evaluations.

### Research Question 0 Statement

For each major discipline in the history of computer science that claims to express or enforce a "correspondence" between program behavior and a specification, identify:
1.  The **specific correspondence relation** it verifies.
2.  The **precise mathematical or logical expression** of that relation.
3.  The **formal boundary** at which it fails to cover $H_0$ — i.e., where proof-obligation preservation across a delegation boundary with a runtime synthesis process falls outside the discipline's scope.

### The Landscape of Known Semantic Correspondences

| Semantic Discipline | Core Correspondence Relation Verified | Core Logical Expression | Foundational Boundary / Why it falls short of $H_0$ |
| --- | --- | --- | --- |
| **Program Logics (Hoare Logic)** | Pre/Post-condition Compliance: The final state satisfies a structural predicate if the initial state satisfied the precondition. | $\{P\} \, c \, \{Q\}$ | Assumes a fixed, statically known program statement $c$. It cannot naturally express proof preservation when $c$ is synthesized at runtime via a non-fixed evaluation relation. |
| **Refinement Calculus** | Specification Refinement: A concrete implementation narrows the non-determinism of an abstract specification. | $S \sqsubseteq C$ | Operates as a compile-time or derivation-time proof. It does not track or carry proof obligations across a dynamic delegation boundary where execution layers adapt at runtime. |
| **Information Flow Control (IFC)** | Non-Interference: High-integrity or confidential outputs depend strictly on authorized inputs. | $(s_1 \approx_L s_2) \implies (\llbracket c \rrbracket s_1 \approx_L \llbracket c \rrbracket s_2)$ | Focuses entirely on data taint and source isolation. It cannot verify or express whether the meaning or logical validity of a runtime-synthesized action matches an authorized intent. |
| **Capability Systems** | Action Entitlement: An execution context holds an explicit, unforgeable reference token permitting an operation. | $\text{Invoke}(e) \iff \text{token} \in \text{Context}$ | Purely access-oriented and parameter-blind. It evaluates whether an entrypoint can be called, completely ignoring the causal rationale behind why the parameters were chosen. |
| **Data & Whole-System Provenance** | Causal Lineage Derivation: An output data artifact or OS state was derived from a directed acyclic graph of ancestral events. | $\text{DerivedFrom}(\text{Artifact}_\text{out}, \text{Artifact}_\text{in})$ | Strictly observational and post-facto. It tracks history but lacks an inline, semantic proof enforcement system to block actions whose synthesis pathways violate a delegated constraint. |
| **Temporal Logic** | Trace Invariance: Every execution trace satisfies a set of linear or branching temporal properties over time. | $\mathcal{M}, s \models \Box\phi$ | Verifies global execution paths against fixed structural rules (liveness, safety). It does not evaluate proof-obligation inheritance across a boundary of delegated authority constraints. |
| **Separation Logic** | Heap Ownership Preservation: A localized program block transforms a pointer space without inducing out-of-band heap side effects. | $\{P * Q\} \, c \, \{P' * Q\}$ | Bounded strictly to memory geography and spatial resources. It cannot model the logical alignment of dynamic runtime decision trajectories. |
| **Proof-Carrying Code (PCC)** | Safety Invariant Adherence: A compiled binary payload carries an explicit, easily checkable proof of safety compliance. | $\text{CheckProof}(\text{Binary}, \text{SafetyPolicy}) \equiv \text{True}$ | Typically targets memory safety, control-flow integrity, or fixed resource bounds at the binary machine boundary. It does not natively trace the semantic correctness of multi-conditional runtime logic synthesis. |

### Survey Finding

No surveyed discipline defines, expresses, or enforces the correspondence relation described in $H_0$: that the evaluation relation governing a runtime synthesis process must preserve the proof obligation delegated to it from an external authority boundary. This gap is not a naming ambiguity—it is a structural absence in the landscape of known semantic correspondences.

---
