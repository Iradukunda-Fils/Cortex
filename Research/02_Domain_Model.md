# 02: Domain Model
**Status:** LOCKED  

## Purpose
Define the system boundaries, threat model, safety properties catalog, operational semantics modeling, and multi-system adversarial scenarios that bound the research program.

## Dependencies
*   [01_Methodology.md](01_Methodology.md)

---

## 1. The Primary Research Hypothesis ($H_0$)

> **$H_0$:** Does an existing semantic preservation relation characterize when the externally observable effects of an execution remain within the authority constraints delegated to that execution under the stated threat model?

By rephrasing $H_0$ using standard programming languages and compiler semantics terminology, the hypothesis is made directly testable against the formal literature without collapsing into arguments about implementation variability.

**Conditional Outcome:**
*   **If $H_0$ is validated:** A composition of existing CS frameworks satisfies all safety properties. No new semantic layer is required. The program terminates and pivots to implementation guidance.
*   **If $H_0$ is falsified:** The analysis exposes an irreducible semantic gap—a correspondence relation that no surveyed discipline can express or enforce, validating the necessity of a dedicated semantic boundary.

---

## 2. Classifying Operational Mutability (The Structural Distinctions)

To prevent reviewers from assuming a fixed execution pathway, we catalog the four cases of system mutability:

```
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

**Scope Selection:** This research program isolates **Case C** and **Case B when nested within dynamic user-space interpretation** (e.g., a verified query planner executing an unfixed, synthesized query trace). The core problem is that even if the outer interpreter framework is fully verified, the intermediate operational artifact ($\mathcal{A}$) is not bound to the delegation context inherited at the execution boundary.

---

## 3. Formal Operational Semantics of the Execution Space

We model the runtime execution process using the formal language of Structural Operational Semantics (SOS), incorporating the abstract **Operational Artifact ($\mathcal{A}$)** as the unifying intermediate representation:

$$\frac{\Sigma; \Lambda \vdash I \Downarrow \mathcal{A} \quad \quad \Sigma \vdash \text{enact}(\mathcal{A}) \Downarrow e}{\Sigma; \Lambda \vdash I \longrightarrow e}$$

Where:
*   $\mathbf{\Sigma}$ represents the global environmental state.
*   $\mathbf{\Lambda}$ represents the abstract **Delegation Context**: A semantic object whose interpretation constrains the admissible externally observable effects of an execution.
*   $\mathbf{I}$ is the non-deterministic input stream.
*   $\mathbf{\mathcal{A}}$ is the intermediate **Operational Artifact** generated dynamically by the system's internal decision procedure, planning engine, or interpreter wrapper.
*   $\mathbf{e}$ is the terminal **Target Action Tuple** ($\langle \text{op}, \text{args} \rangle \in E_{\text{irreversible}}$).

### The Operational Artifact Hierarchy

To bridge multiple computer science disciplines under a single formal representation without conflating their underlying mathematical structures, the Operational Artifact ($\mathcal{A}$) acts as a unifying abstract class:

```
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

> **Satisfaction Relation ($\Sigma \models \text{Preserves}(\Lambda, e)$):** The environment $\Sigma$ guarantees that the terminal target action $e$ sits strictly within the semantic envelope authorized by the delegated context $\Lambda$, regardless of the intermediate operational artifact ($\mathcal{A}$) produced during execution.
