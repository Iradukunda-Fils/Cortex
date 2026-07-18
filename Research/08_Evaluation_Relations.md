# 08: Evaluation Relations
**Status:** LOCKED  

## Purpose
Examine how operational, denotational, and trace semantics model runtime derivation pathways when processing non-deterministic input streams. Formally partition and disambiguate the intermediate runtime derivation artifacts to prevent proof confusion.

## Dependencies
*   [02_Domain_Model.md](02_Domain_Model.md)

---

## 1. Disambiguation of Runtime Derivation Artifacts

When an execution engine processes dynamic inputs to execute actions, several computer science concepts (traces, trees, plans) are often conflated under the name "trace." We establish a rigid partition:

```
  [ Input Stream (I) ] 
         │
         ▼ (Evaluation pass under state Σ and context Λ)
  ┌─────────────────────────────────────────────────────────┐
  │         Runtime Derivation Result                       │
  │  1. Derivation Tree (D) ──► Inference/Correctness Proof │
  │  2. Operational Trace (τ) ──► Micro-state history        │
  │  3. Execution Plan (P)  ──► Planned action commands     │
  └─────────────────────────────────────────────────────────┘
         │
         ▼ (Enactment pass)
  [ Terminal Action (e) ]
```

### 1.1 The Derivation Tree ($\mathcal{D}$)
*   **Definition:** The formal, meta-logical proof object composed of a tree of inference rules demonstrating that the execution engine accurately followed its language or operational rules to translate input stream $I$.
*   **Role:** Verifies evaluation fidelity—proving that the engine did not violate semantics rules during execution evaluation.

### 1.2 The Operational Trace ($\tau$)
*   **Definition:** The linear or branching sequential history of intermediate micro-state transitions ($\sigma_0 \to \sigma_1 \to \dots \to \sigma_n$) executed by the underlying abstract or concrete machine during the evaluation run.
*   **Role:** Captures the structural profile of the execution path, including register states, heap allocations, and control-flow jumps.

### 1.3 The Execution Plan ($\mathcal{P}$)
*   **Definition:** The intermediate structural artifact emitted by the derivation process (such as a JIT-compiled basic block, a distributed workflow sequence, or a database query execution plan) which is subsequently consumed by an enforcement engine to induce real-world state shifts.
*   **Role:** Acts as the blueprint for the final, irreversible action.

---

## 2. Evaluation Paradigms Comparison

We trace how the classic operational semantics frameworks express these boundaries under non-deterministic inputs:

### 2.1 Big-Step Semantics (Natural Semantics)
*   **Model:** Evaluates expressions directly to final values: $\langle \Sigma, I \rangle \Downarrow \langle \Sigma', v \rangle$.
*   **Implication for $H_0$:** Compresses the intermediate state transition sequence. The derivation tree ($\mathcal{D}$) is explicitly represented as the proof tree, but the operational trace ($\tau$) is hidden inside the nested induction. It provides no mechanism to observe runtime logic deviations before execution completes.

### 2.2 Small-Step Semantics (Structural Operational Semantics)
*   **Model:** Exposes every individual state reduction: $\langle \Sigma, I \rangle \to \langle \Sigma', I' \rangle$.
*   **Implication for $H_0$:** Exposes the operational trace ($\tau$) step-by-step. While this allows fine-grained trace monitoring, it does not naturally relate intermediate states to the coarse, high-level delegation boundary ($\Lambda$) without carrying type refinements or tags throughout every transition rule.

### 2.3 Trace Semantics
*   **Model:** Defines the meaning of a program as the set of all its possible execution traces (often used in reactive systems or concurrency models).
*   **Implication for $H_0$:** Useful for verifying safety properties across infinite runs (e.g., liveness, secure information flow). However, trace semantics traditionally assume a fixed program text whose possible trace set is known at analysis time, failing to cover runtime derivation engines.
