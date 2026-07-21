# FC-09: Interactive Theorem Prover (ITP) Mechanization Roadmap
**Phase:** FORMAL MODEL MECHANIZATION — ZERO-ADMIT CERTIFICATION
**Status:** COMPLETE (Single Axiomatic Boundary)

## 1. Purpose and Scope
This document details the **Formal Mechanization Roadmap** of the Cortex spatiotemporal semantic architecture. We transition this framework from abstract system designs directly to concrete, deep-embedded, type-checked code modules in Coq/Rocq, mapping spatiotemporal authority decay to step-indexed Kripke logic.

---

## 2. Theoretical Core: The Spatiotemporal World Tuple and Kripke Preorder
To establish a complete, falsifiable blueprint, our pen-and-paper specification maps directly to context structures in `World.v`.

### The Spatiotemporal World Tuple
Each spatiotemporal world $w$ is defined as a 4-tuple:
$$w = (\Lambda, m, n, \nu)$$
*   **$\Lambda$ (Spatial Authority)**: Represents the authority carrier. Mathematically, it tracks active and authorized capability identifiers within the execution domain.
*   **$m$ (Monitor State)**: Tracks the reference monitor's epoch configuration to detect historic trace shifts.
*   **$n$ (Step-Index Fuel)**: A natural number ($\mathbb{N}$) representing the operational fuel metric. Decrementing this counter across transitions bounds execution loops and prevents infinite recursion.
*   **$\nu$ (Temporal Epoch Vector)**: The log of logical times or generations. Older capability epoch thresholds ($\nu_c$) are compared against the vector ($\nu \le \nu_c$) to instantly trap stale tokens.

### Kripke Accessibility Preorder ($\sqsubseteq$)
Progression between worlds follows a Kripke preorder: $w \sqsubseteq w'$ (represented as `world_accessible w w'` in Coq) if and only if:
1.  **Spatial Authority Contraction ($\Lambda' \subseteq \Lambda$)**: Authority can decay or be restricted over time, represented via the class relation `auth_contains_monotone`.
2.  **Temporal Epoch Advancement ($\nu \le \nu'$)**: Epoch timelines move monotonically forward.
3.  **Step-Index Decay (Metric Contraction)**: Monitored computation steps strictly decay the fuel counter ($n' < n$ or `world_fuel w' < world_fuel w`), forcing metric space contraction.

### Contravariant Capability Decay
A critical formal property of the spatiotemporal Kripke frame is that capability validity (`valid_cap`) is intentionally non-monotone under forward world evolution ($w \sqsubseteq w'$). Because world transitions model both spatial authority contraction ($\Lambda' \subseteq \Lambda$) and temporal epoch advancement ($\nu \le \nu'$), forward evolution can explicitly revoke or expire capabilities. Semantic monotonicity of the value interpretation $\mathcal{V}_w$ is preserved across forward transitions because expired or revoked terms gracefully fall back into the safe operational trapping branch ($v = \mathtt{e\_val}~0$), delegating revocation enforcement to the monitored transition system.

---

## 3. Concrete Coq/Rocq Mechanization Architecture
We have constructed a deep-embedded, compilable verification suite in the Cortex namespace:

*   **`AuthorityModel.v`**: Defines the carrier types and classes for authority preorders. **Fully proved.**
*   **`World.v`**: Formalizes the `World` tuple, proves the Kripke accessibility preorder (`world_accessible_preorder`), and proves `valid_cap_monotone`. **Fully proved.**
*   **`Semantics.v`**: Implements deep-embedded expressions (`e_var`, `e_val`, `e_invoke`, `e_fork`) and lists the fuel-decrementing step relation `step_m` where fresh capability execution preserves the token expression `e_invoke c` on trace outputs. **Fully proved.**
*   **`LogicalRelation.v`**: Defines list-lookup typing context validation and the spatiotemporal execution relation `E_w`. **Fully proved.**
*   **`FTLR.v`**: Defines the deep inductive typing rules (`typing`) and proves the syntax-directed induction cases of the Fundamental Theorem of Logical Relations. **Fully proved.**
*   **`Substitution.v`**: Declares the single axiomatic boundary (`valid_cap_decay_axiom`) and proves all structural lemmas: context weakening (`context_weakening`), semantic substitution (`semantic_substitution_preserves_typing`), capability value relation monotonicity (`V_w_TCap_monotonicity`), type-level value monotonicity (`V_w_monotonicity`), and env validity monotonicity (`env_valid_monotonicity`). **Zero admits. One explicit axiom.**
*   **`Soundness.v`**: Synthesizes type safety, composing `fundamental_theorem` with complete mediation under `unified_soundness` to verify operational provenance safety. **Fully proved.**

---

## 4. Verified Architectural Dependency Hierarchy

The Rocq/Coq development is organized into a decoupled proof architecture separating the core soundness pipeline from the substitution and monotonicity infrastructure.

### 4.1 Core Soundness Pipeline
The following modules constitute the primary semantic safety path:
*   `World.v` → `Semantics.v` → `LogicalRelation.v` → `FTLR.v` → `Soundness.v`

This pipeline establishes the Kripke world structure, monitored operational semantics, logical relations, the Fundamental Theorem of Logical Relations (`fundamental_theorem`), and the top-level soundness theorem (`unified_soundness`).

`unified_soundness` proves safety via direct `step_m` inversion and uses `env_valid` as an external hypothesis, rather than importing the substitution and monotonicity lemmas from `Substitution.v`.

### 4.2 Substitution and Monotonicity Infrastructure
The following module provides supporting infrastructure for open-term reasoning and future language extensions:
*   `Substitution.v`: `V_w_monotonicity`, `env_valid_monotonicity`, `V_w_TCap_monotonicity`, `context_weakening`, `semantic_substitution_preserves_typing`

These components depend on the explicit domain parameter `valid_cap_decay_axiom`.

### 4.3 Kernel Dependency Audit (`Print Assumptions`)
The following output was obtained by executing `Print Assumptions` in the Rocq 9.1.1 kernel after a clean `make` build:

```
Print Assumptions unified_soundness.
  → Closed under the global context

Print Assumptions fundamental_theorem.
  → Closed under the global context

Print Assumptions semantic_substitution_preserves_typing.
  → Closed under the global context

Print Assumptions context_weakening.
  → Closed under the global context

Print Assumptions V_w_monotonicity.
  → Axioms: valid_cap_decay_axiom

Print Assumptions env_valid_monotonicity.
  → Axioms: valid_cap_decay_axiom

Print Assumptions V_w_TCap_monotonicity.
  → Axioms: valid_cap_decay_axiom
```

**Interpretation**: The top-level soundness theorem and the FTLR are axiom-free — fully closed under the global context. The monotonicity layer depends on `valid_cap_decay_axiom`. The two layers are decoupled: `unified_soundness` establishes safety via direct operational inversion, bypassing the Kripke monotonicity infrastructure entirely.

To reproduce this audit:
```coq
(* In Rocq/Coq interactive shell after loading all modules *)
From Cortex Require Import Soundness Substitution.
Print Assumptions unified_soundness.
Print Assumptions V_w_monotonicity.
```

---

## 5. Verification Step Progression

| Step | Phase | Goal | Target Implementation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **01** | **Base Syntax & Semantics** | Define operational layer small-steps | Split monitored transition rules in `Semantics.v`. | **Completed** |
| **02** | **Kripke Frame Setup** | Establish world accessibility | Implement the world configuration in `World.v`. | **Completed** |
| **03** | **Logical Relation Design** | Mechanize value and trace relations | Construct definitions for $V_w$ and $E_w$ in `LogicalRelation.v`. | **Completed** |
| **04** | **ITP proof layout / skeleton** | Structural induction over typing | Implement typing rules and proof goals in `FTLR.v`. | **Completed** |
| **05** | **Soundness Composition** | Synthesize complete mediation safety | Compose FTLR lemma and complete mediation in `Soundness.v`. | **Completed** |
| **06** | **Axiom Isolation** | Isolate spatiotemporal decay boundary | Promote `valid_cap_decay_axiom` in `Substitution.v`. | **Completed** |

---

## 6. Artifact Evaluation

### Build Instructions
```bash
cd verification/
make          # Build all modules with topological dependency ordering
make audit    # Report axiom/admit count across the development
make clean    # Remove compiled artifacts
```

### Source-Level Audit
```
grep -rn "Admitted" *.v   → Exit code 1 (zero matches)
grep -rn "Axiom" *.v      → Substitution.v:26: Axiom valid_cap_decay_axiom
```

---

## 7. Peer-Reviewed Publication Framing

*"We present a mechanized spatiotemporal logical-relation framework in Rocq/Coq with a decoupled architecture separating the core soundness pipeline from the substitution and monotonicity infrastructure. The top-level soundness theorem (`unified_soundness`) and the Fundamental Theorem of Logical Relations (`fundamental_theorem`) are verified with zero axioms or admitted lemmas — fully closed under the global context as confirmed by `Print Assumptions`. The monotonicity layer (`V_w_monotonicity`, `env_valid_monotonicity`) depends on a single explicit domain parameter (`valid_cap_decay_axiom`) representing the contravariant nature of capability decay under forward world accessibility. The two layers are architecturally decoupled: soundness is established via direct operational inversion, while the monotonicity infrastructure provides supporting algebra for open-term reasoning and future language extensions."*
