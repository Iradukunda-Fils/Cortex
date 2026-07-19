# FC-09: Interactive Theorem Prover (ITP) Mechanization Roadmap
**Phase:** FORMAL MODEL CONSTRUCTION
**Status:** ACTIVE

## 1. Purpose and Scope
This document details the **Formal Mechanization Roadmap** to translate our spatiotemporal semantic architecture into a machine-checked reality in interactive theorem provers (ITPs) like Coq or Lean. 

By leveraging the **Iris** concurrent separation logic framework, we define a modular mapping from the algebraic authority preorder to formal cameras, instantiate step-indexing via built-in step-indexed predicates, represent versioned authority epochs via monotonic counters, and lay a systematic path to compile-time proof verification.

---

## 2. Concrete ITP Mechanization Architecture
To translate our four-layer spatiotemporal proof stack into Coq/Lean, we map the mathematical configurations directly to Iris algebraic structures:

### Layer 1: The Algebraic Preorder (Type to Canonical Structure)
*   **Mathematical Concept:** Preorder $\mathbb{A} = (A, \preceq, \oplus, \mathbf{0})$ with authority restriction.
*   **ITP Strategy:** We encode the carrier type $A$ as a Coq `Record` or `Structure` equipped with:
    *   An associative and commutative operator `op : A -> A -> A`.
    *   An identity element `zero : A`.
    *   A decidable preorder relation `le : A -> A -> Prop` accompanied by checked proofs of reflexivity, transitivity, and monotonicity relative to `op` (i.e., $x \preceq y \implies x \oplus z \preceq y \oplus z$).

### Layer 2: The Spatiotemporal World (Ghost State camera integration)
*   **Mathematical Concept:** $w = (\Lambda, m, n, \nu) \in \mathcal{W}$ where access demands $\nu' \ge \nu$.
*   **ITP Strategy:**
    1.  **Step-indexing ($n$):** Handled natively by leveraging Iris's built-in step-indexed logic (`uPred`).
    2.  **Authority Mapping ($\Lambda$):** Represented as an authoritative resource fragment using the Iris Ghost State camera mechanism (`authR`).
    3.  **Epoch Model ($\nu$):** Encoded via a monotonic counter camera, where possessing a ghost token for epoch version $\nu$ acts as a lower-bound witness, guaranteeing via Iris invariant rules that the global epoch state can never decay below $\nu$.

### Layer 3: Epoch Freshness Validation
*   **Mathematical Concept:** $\text{Valid}(c, \Lambda, \nu) \iff c \in \Lambda \land \nu \le \nu_c$
*   **ITP Strategy:** Decided via an inductive boolean returning proposition (`Inductive` or `Fixpoint`). Expressing freshness checks as decidable functions allows Coq/Lean to automatically simplify execution paths during monitored step evaluations using the assistant's computation engine (e.g., `simpl` or `decide` tactics).

---

## 3. Mechanical Proof Layout & Ghost State Invariants
To prove the Unified Spatiotemporal Soundness Theorem, the execution container's Complete Mediation property is formalized as a global state invariant ($I_{\text{monitor}}$) allocated in the Iris namespace throughout the trace lifespan:

$$I_{\text{monitor}} \triangleq \exists \Sigma, \Lambda, m, \nu. \quad \text{OwnGhost}(\Lambda, \nu) \land \left( \forall e \neq \text{idle}. \; \text{TraceStep}(\Sigma, e) \implies \text{MonitoredStep}(\Sigma, \Lambda, m, \nu, e) \right)$$

When an untrusted artifact executes under this environment:
*   **Verified Artifacts:** The user applies the mechanized FTLR lemma. The proof witness $\pi$ unfolds into an Iris path resource, showing that the program satisfies its step-indexed specification.
*   **Revocation/Attenuation Actions:** The administrative thread updates the global state invariant by writing a new restricted authority set $\Lambda_{\text{final}}$ and incrementing the ghost epoch token to $\nu_{\text{final}}$. 
*   **Bypass Prevention:** Because the monitor invariant holds the authoritative state, any concurrent thread trying to utilize a cached capability token with a stale version $\nu_c < \nu_{\text{final}}$ will trigger a logical contradiction during evaluation, forcing execution into the safe $e = \text{idle}$ path.

---

## 4. Verification Step Progression

| Step | Phase | Goal | Target Implementation |
| :--- | :--- | :--- | :--- |
| **01** | **Base Syntax & Semantics** | Define operational layer small-steps | Split transition rules into concrete execution ($\xrightarrow{g}$) and reference monitor actions ($\xrightarrow{g}_m$). |
| **02** | **Kripke Frame Setup** | Establish world accessibility | Implement the four-part world configuration in the proof assistant. Prove transitivity and reflexivity lemmas for $\sqsubseteq$. |
| **03** | **Logical Relation Design** | Mechanize value and trace relations | Construct definitions for $\mathcal{V}_w$ and $\mathcal{E}_w$. Use well-founded induction to prove step-indexed recursion safety. |
| **04** | **FTLR Lemma Induction** | Direct syntax-directed proof checks | Execute structural induction over syntax-directed derivation rules (alloc, invoke, fork) to prove semantic conformance. |
| **05** | **Soundness Closure** | Verify Theorem 3 | Bind FTLR output to the reference monitor invariant ($I_{\text{monitor}}$) to extract verified monitored trace provenance. |

---

## 5. Concrete Publication Baseline
The mathematical definitions, threat modeling paradigms, and soundness boundaries have converged into a complete, publishable research blueprint:

```text
                  [ Verification Proof Stack ]
                  
     Layer 4:  Unified Soundness Theorem (Theorem 3)
                            ▲
                            │ Verified via Complete Mediation
     Layer 3:  Fundamental Theorem (FTLR)
                            ▲
                            │ Proven via Spatiotemporal Monotonicity
     Layer 2:  Logical Relation (E_w ⟦ τ ⟧)
                            ▲
                            │ Governed by Preorder Axes
     Layer 1:  Kripke Worlds (Λ, m, n, ν) with w' ⊑ w
```

The theoretical construction phase is officially complete and closed. The architecture successfully isolates the execution vulnerabilities of arbitrary device contexts, rendering stale-authority exploitation a provable semantic impossibility. The project is ready to transition to code line entry inside the interactive theorem prover.
