# 02: Domain Model
**Status:** LOCKED  

## Purpose
Define the system boundaries, threat model, safety properties catalog, operational semantics modeling, and multi-system adversarial scenarios that bound the research program.

## Dependencies
*   [01_Methodology.md](01_Methodology.md)

---

## 1. The Primary Research Hypothesis (Refined)

> **$H_0$ (Refined):** Can an execution semantics preserve a proof obligation across a delegation boundary when an externally observable, irreversible effect is generated via a runtime derivation process whose **evaluation relation is not fixed before execution**?

The deliberate sharpening: the term "dynamic" is replaced with "runtime derivation process whose evaluation relation is not fixed before execution."

**Conditional Outcome:**
*   **If $H_0$ is validated:** A composition of existing CS frameworks satisfies all safety properties. No new semantic layer is required. The program terminates and pivots to implementation guidance.
*   **If $H_0$ is falsified:** The analysis exposes an irreducible semantic gap—a correspondence relation that no surveyed discipline can express or enforce, validating the necessity of a dedicated semantic boundary.

---

## 2. Classifying "Runtime Derivation" (The Structural Distinctions)

To prevent reviewers from trivializing the problem by assuming a fixed execution pathway, we explicitly catalog the four cases of system mutability:

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
    Synthesized Trajectory (T)                          Synthesized Inner Trace (T)
          │                                                   │
          ▼                                                   ▼
    Irreversible Action (e)                             Irreversible Action (e)
```

*   **Case A (Code Mutation):** The program code text or binary blueprint itself changes at runtime via primitives like `eval()`, dynamic plugin loading, or out-of-band JIT code generation.
*   **Case B (State Mutation / Data-Driven):** The program logic is fixed and statically verified. Only the state and runtime inputs fluctuate ($I \rightarrow \text{Fixed State Machine} \rightarrow e$).
*   **Case C (Dynamic Semantic Translation):** The foundational evaluation semantics change or emerge dynamically. The host environment passes inputs into an engine that translates or compiles those inputs into an unfixed, intermediate Domain-Specific Language (DSL), an abstract execution plan, or a multi-conditional routing tree ($T$) before dispatching the final action ($e$).
*   **Case D (Policy Mutation):** The evaluator and interpreter remain completely unchanged; only the external delegation constraints or access control rules evolve.

**Scope Selection:** This research program isolates **Case C** and **Case B when nested within dynamic user-space interpretation** (e.g., a verified query planner executing an unfixed, synthesized query trace). The core problem is that even if the outer interpreter framework is fully verified, the inner strategy choice or synthesized execution trajectory ($T$) is not bound to the proof obligation inherited at the delegation boundary.

---

## 3. Formal Operational Semantics of the Derivation Space

We model the runtime derivation process using the formal language of Structural Operational Semantics (SOS). We represent the generation of an irreversible effect as a Derivation Tree.

The core evaluation relation mapping inputs ($I$) to target actions ($e$) under environment state $\Sigma$ and delegation context $\Lambda$ is defined by the following rule:

$$\frac{\Sigma; \Lambda \vdash I \Downarrow \langle \mathcal{D}, \tau, \mathcal{P} \rangle \quad \quad \Sigma \vdash \text{enact}(\mathcal{P}) \Downarrow e}{\Sigma; \Lambda \vdash I \Longrightarrow e}$$

Where:
*   $\mathbf{\Sigma}$ represents the global environmental state.
*   $\mathbf{\Lambda}$ represents the active delegation context containing the explicit constraints.
*   $\mathbf{I}$ is the non-deterministic input stream.
*   $\mathbf{\mathcal{D}}$ is the **Derivation Tree**: The formal, meta-logical proof object composed of a tree of inference rules demonstrating that the execution engine accurately followed its language or operational semantics to translate input stream $I$.
*   $\mathbf{\tau}$ is the **Operational Trace**: The linear or branching sequential history of intermediate micro-state transitions executed by the underlying abstract or concrete machine during evaluation.
*   $\mathbf{\mathcal{P}}$ is the **Execution Plan**: The intermediate structural artifact emitted by the derivation process (such as a JIT-compiled basic block, a distributed workflow sequence, or a database query execution plan) which is subsequently consumed by an enforcement engine to induce real-world state shifts.
*   $\mathbf{e}$ is the terminal **Target Action Tuple** ($\langle \text{op}, \text{args} \rangle \in E_{\text{irreversible}}$).

Our question is: *Can the operational rules governing $\Sigma; \Lambda \vdash I \Downarrow \langle \mathcal{D}, \tau, \mathcal{P} \rangle$ guarantee or structurally prove that the resulting action $e$ preserves the original semantic intent of $\Lambda$ without trusting the runtime engine?*

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
| **P2** | **Execution Integrity** | The byte-level parameter state of an executed action must remain structurally unaltered between the generation boundary and the interface enforcement perimeter under the stated threat model. | Enclave memory isolation, single-copy buffers, verified compilation |
| **P3** | **Semantic Consequence Preservation** | Every externally observable, irreversible effect must be demonstrably and traceably derivable from the active delegation constraints under the evaluation semantics: $\Sigma \models \text{Preserves}(\Lambda, e)$ | **No known complete solution** |
| **P4** | **Independent Verifiability (Rectified)** | An external, post-facto verifier must be capable of establishing the validity of P3 without trusting the execution runtime beyond the boundaries of an explicitly declared **Trusted Computing Base (TCB)**. | **No known complete solution** |

> **Satisfaction Relation ($\Sigma \models \text{Preserves}(\Lambda, e)$):** The environment $\Sigma$ guarantees that the terminal target action $e$ sits strictly within the semantic envelope authorized by the delegated proof obligation $\Lambda$, regardless of the intermediate runtime derivation path ($T = \langle \mathcal{D}, \tau, \mathcal{P} \rangle$) taken.

> **Note on P2:** Execution Integrity is an environmental assumption. The active research focus is entirely on **P3 and P4**.
