# 08: Evaluation Relations
**Status:** LOCKED  

## Purpose
Examine how operational, denotational, structural, and trace semantics model runtime execution pathways when processing non-deterministic input streams. Formally partition and disambiguate how intermediate operational artifacts are modeled to prevent proof confusion.

## Dependencies
*   [02_Domain_Model.md](02_Domain_Model.md)

---

## 1. Disambiguation of Operational Artifacts

When an execution engine processes dynamic inputs to execute actions, several computer science concepts (traces, trees, plans) are often conflated. The abstract **Operational Artifact ($\mathcal{A}$)** serves to unify these forms under a single semantic domain:

```
  [ Input Stream (I) ] 
         │
         ▼ (Evaluation pass under state Σ and context Λ)
  ┌────────────────────────────────────────────────────────┐
  │         Operational Artifacts (A)                      │
  │  1. Derivation Tree ──► Inductive inference proof      │
  │  2. Execution Trace ──► Micro-state history transition │
  │  3. Execution Plan  ──► Resource / Action Blueprint    │
  └────────────────────────────────────────────────────────┘
         │
         ▼ (Enactment pass)
  [ Terminal Action (e) ]
```

### 1.1 Derivation Tree
*   **Definition:** The formal, meta-logical proof object composed of a tree of inference rules demonstrating that the execution engine accurately followed its language or operational rules to translate input stream $I$.
*   **Role:** Verifies evaluation fidelity—proving that the engine did not violate semantic rules during evaluation.

### 1.2 Execution Trace
*   **Definition:** The linear or branching sequential history of intermediate state transitions ($\sigma_0 \xrightarrow{a_0} \sigma_1 \to \dots \to \sigma_n$) executed by the underlying abstract or concrete machine during the evaluation run.
*   **Role:** Captures the structural profile of the execution path, including register states, heap allocations, and control-flow jumps.

### 1.3 Execution Plan (or Workflow DAG)
*   **Definition:** The intermediate structural artifact emitted by the evaluation process (such as a JIT-compiled basic block, a database query plan, or a distributed workflow DAG) which is subsequently consumed by an enforcement engine to induce real-world state shifts.
*   **Role:** Acts as the blueprint for the final, irreversible action.

---

## 2. Evaluation Paradigms Comparison

We trace how classic operational semantics frameworks model these parameters when translating inputs to effects:

$$\frac{\Sigma; \Lambda \vdash I \Downarrow \mathcal{A} \quad \quad \Sigma \vdash \text{enact}(\mathcal{A}) \Downarrow e}{\Sigma; \Lambda \vdash I \Longrightarrow e}$$

### 2.1 Big-Step Semantics (Natural Semantics)
*   **Model:** Evaluates expressions directly to final values: $\langle \Sigma, I \rangle \Downarrow \langle \Sigma', v \rangle$.
*   **Implication for $H_0$:** Compresses the intermediate state transition sequence. The derivation tree is explicitly represented as the proof tree, but the transition history is hidden inside the nested induction. It provides no mechanism to observe runtime logic deviations before execution completes.

### 2.2 Small-Step Semantics (Structural Operational Semantics)
*   **Model:** Exposes every individual state reduction: $\langle \Sigma, I \rangle \to \langle \Sigma', I' \rangle$.
*   **Implication for $H_0$:** Exposes the execution trace step-by-step. While this allows fine-grained trace monitoring, it does not naturally relate intermediate configurations to the coarse, high-level delegation boundary ($\Lambda$) without carrying type refinements or tags throughout every transition rule.

### 2.3 Trace Semantics
*   **Model:** Defines the meaning of a program as the set of all its possible execution traces.
*   **Implication for $H_0$:** Useful for verifying safety properties across infinite runs. However, trace semantics traditionally assume a fixed program text whose possible trace set is known at analysis time, failing to cover environments where the program or plan itself is generated dynamically at runtime based on incoming parameters.
