# 02: Domain Model
**Status:** LOCKED  

## Purpose
Define the system boundaries, threat model, safety properties catalog, operational semantics modeling, and multi-system adversarial scenarios that bound the research program.

## Dependencies
*   [01_Methodology.md](01_Methodology.md)

---

## 1. The Primary Research Hypothesis and Working Proposition ($H_{\text{prop}}$)

> **The Primary Research Hypothesis ($H_0$):** Does an existing semantic preservation relation characterize when the externally observable effects of an execution remain within the authority constraints delegated to that execution under the stated threat model?

By rephrasing the research question using standard programming languages and compiler semantics terminology, the hypothesis is made directly testable against the formal literature without collapsing into arguments about implementation variability.

> **Working Hypothesis ($H_{\text{prop}}$):** The desired correspondence appears to require reasoning over families of executions parameterized by delegated constraints, suggesting—but not yet establishing—that it may be expressible as a relational hyperproperty over operational traces.

**Conditional Outcome:**
*   **If $H_0$ is validated:** A composition of existing CS frameworks satisfies all safety properties. No new semantic layer is required. The program terminates and pivots to implementation guidance.
*   **If $H_0$ is falsified:** The analysis exposes an irreducible semantic gap—a correspondence relation that no surveyed discipline can express or enforce, validating the necessity of a dedicated semantic boundary formalizing $H_{\text{prop}}$.

---

## 2. Classifying Operational Mutability (The Structural Distinctions)

To prevent reviewers from assuming a fixed execution pathway, we catalog the four cases of system mutability:

```text
  [Case A: Structural Code Mutation]     [Case B: Fixed State Transition]
    eval() / Dynamic Plugin Loading         Input (I) ──► Fixed Program ──► Effect (e)

  ─────────────────────────────────────────────────────────────────────────────
  THIS RESEARCH PROGRAM TARGETS:
  ─────────────────────────────────────────────────────────────────────────────
  [Case C: Dynamic Semantic Translation]  [Case B Nested inside Verified Interpreter]
    DSL / Dynamic Translation Logic         Input (I) ──► [ Verified Interpreter ]
          │                                                   │ (Faithful Execution)
          ▼                                                   ▼
     Operational Artifact (A)                            Operational Artifact (A)
          │                                                   │
          ▼                                                   ▼
    Irreversible Action (e)                             Irreversible Action (e)
```

*   **Case A (Code Mutation):** The program code text or binary blueprint itself changes at runtime via primitives like `eval()`, dynamic plugin loading, or out-of-band JIT code generation.
*   **Case B (State Mutation / Data-Driven):** The program logic is fixed and statically verified. Only the state and runtime inputs fluctuate ($I \rightarrow \text{Fixed State Machine} \rightarrow e$).
*   **Case C (Dynamic Semantic Translation):** The foundational evaluation semantics change or emerge dynamically. The host environment passes inputs into an engine that translates or compiles those inputs into an intermediate Domain-Specific Language (DSL), an execution plan, or a multi-conditional routing tree—modeled as an abstract **Operational Artifact** ($\mathcal{A}$)—before executing the final action ($e$).
*   **Case D (Policy Mutation):** The evaluator and interpreter remain completely unchanged; only the external delegation constraints or access control rules evolve.

**Scope Selection:** This research program isolates **Case C** and **Case B when nested within dynamic user-space interpretation** (e.g., a verified query planner executing an unfixed, synthesized query trace). The core problem is that even if the outer interpreter framework is fully verified, the intermediate operational artifact ($\mathcal{A}$) is not verified against the delegation context originally inherited at the execution boundary.

---

## 3. Generalized Semantic Transition System

We weaken the definition of **Operational Artifact ($\mathcal{A}$)** to keep it strictly abstract and reusable:
> **Operational Artifact ($\mathcal{A}$):** Anything produced by an execution procedure that is subsequently interpreted to determine externally observable behavior.

To prevent reviewers from claiming our execution model conflates system specifications with concrete engine mechanics, we decouple the translation and execution phases using fully generalized operational procedures that allow continuous enactment checking.

### The Refined Structural Operational Semantics Rule

$$\frac{\Sigma; \Lambda \vdash I \xrightarrow{\text{derive}} \mathcal{A} \quad \quad \Sigma; \Lambda \vdash \mathcal{A} \xrightarrow{\text{enact}} e}{\Sigma; \Lambda \vdash I \Longrightarrow e}$$

Where:
*   $\mathbf{\Sigma}$ represents the global environmental state.
*   $\mathbf{\Lambda}$ represents the abstract **Delegation Context**: A semantic object whose interpretation constrains the admissible externally observable effects of an execution.
*   $\mathbf{I}$ is the incoming input stream.
*   $\mathbf{\mathcal{A}}$ is the generalized **Operational Artifact** (e.g., Evaluation Derivation, Query Plan, Workflow Plan, Scheduling Plan, Proof Object, Optimization Trace, or Execution Graph).
*   **The Derivation Premise ($\xrightarrow{\text{derive}}$):** The abstract derivation procedure processes the input stream $I$ inside the global state $\Sigma$ and under the initial delegation context $\Lambda$ to yield the Operational Artifact $\mathcal{A}$.
*   **The Enactment Premise ($\xrightarrow{\text{enact}}$):** The abstract enforcement procedure maps $\mathcal{A}$ to its terminal irreversible effect $e$, explicitly retaining the semantic option to continuously consult, attenuate, or assert the bounds of $\Lambda$ at any point during execution. Specific implementations that decouple execution entirely from policy checking remain supported as instances where the second premise simply leaves $\Lambda$ unexamined.

### The Operational Artifact Hierarchy

```text
                            [ Operational Artifact (A) ]
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         ▼                               ▼                               ▼
 [ Evaluation Derivation ]         [ Query Plan ]                [ Workflow Plan ]
  - AST to value mappings          - Relational operators tree    - Distributed Task DAG
         │                               │                               │
         ├───────────────────────────────┼───────────────────────────────┤
         ▼                               ▼                               ▼
 [ Scheduling Plan ]               [ Proof Object ]              [ Execution Graph ]
  - Resource & Node mappings       - Type term or LF parsing       - State transition path
```

---

## 4. Multi-System Adversarial Scenarios

Evaluations are applied across four distinct structural domains:

| System Domain | Concrete Execution / Target Parameter Context |
| --- | --- |
| **Distributed DBMS Query Optimizer** | A JIT-compiled SQL execution plan generating dynamic index mutations or high-cost deletes. |
| **Infrastructure Orchestration** | A Kubernetes Autoscaler calculating scheduling migrations that trigger node teardowns. |
| **Autonomous Systems (Robotics)** | A robotic controller translating lidar telemetry paths into physical hardware actions. |
| **Autonomous Medical Execution** | A diagnostic model converting clinical telemetry streams into automated drug administration. |

---

## 5. Safety Properties Catalog (Condensed)

Every candidate composition must be rigidly cross-examined against four orthogonal, non-overlapping properties.

| ID | Safety Property | Definitive Operational Meaning / Satisfaction Relation | Historical Coverage |
| --- | --- | --- | --- |
| **P1** | **Authority Soundness** | Bounded authority must be delegable and attenuable across downstream context shifts such that a principal cannot execute or delegate permissions beyond its initial envelope. | Object-Capabilities, Macaroons, Biscuit, SPKI |
| **P2** | **Execution Integrity** | The byte-level parameter state of an executed action must remain structurally unaltered between the generation boundary and the interface enforcement perimeters under the stated threat model. | Enclave memory isolation, single-copy buffers, verified compilation |
| **P3** | **Semantic Consequence Preservation** | Every externally observable, irreversible effect must be demonstrably and traceably derivable from the active delegation constraints under the evaluation semantics: $\Sigma \models \text{Preserves}(\Lambda, e)$ | **No known complete solution** |
| **P4** | **Independent Verifiability (Rectified)** | An external, post-facto verifier must be capable of establishing the validity of P3 without trusting the execution runtime beyond the boundaries of an explicitly declared **Trusted Computing Base (TCB)**. | **No known complete solution** |

### Mathematical Identity of the Target Predicate

$$\Sigma \models \text{Preserves}(\Lambda, e)$$

> **Mathematical Identity:** The core target predicate $\text{Preserves}(\Lambda, e)$ functions as a **Working Hypothesis ($H_{\text{prop}}$)**, provisionally categorized as a **Relational Hyperproperty over Traces**. It establishes an open, empirically testable semantic satisfaction relation ($\models$) stating that the set of all possible terminal execution paths resulting in an effect $e$ must fit inside a relational envelope parameterized by the initial delegation context $\Lambda$. We retract any premature classification of this as a definitive semantic category pending the completed correspondence survey analysis.
