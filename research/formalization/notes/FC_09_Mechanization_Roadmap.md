# FC-09: Interactive Theorem Prover (ITP) Mechanization Roadmap
**Phase:** FORMAL MODEL MECHANIZATION — ZERO-AXIOM CERTIFICATION
**Status:** COMPLETE (Fully Closed Core & Sub-Systems)

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

### Contravariant Capability Decay & Monotonicity
A critical formal property of the spatiotemporal Kripke frame is that capability validity (`valid_cap`) is intentionally non-monotone under forward world evolution ($w \sqsubseteq w'$). Because world transitions model both spatial authority contraction ($\Lambda' \subseteq \Lambda$) and temporal epoch advancement ($\nu \le \nu'$), forward evolution can explicitly revoke or expire capabilities.

We formalized this contravariant property in our development (proving `valid_cap_monotone` in `World.v` unconditionally):
$$\text{If } w \sqsubseteq w', \text{ then } \mathtt{valid\_cap}(c, w') \implies \mathtt{valid\_cap}(c, w)$$
For typing and execution, value interpretation monotonicity ($\mathcal{V}_w \sqsubseteq \mathcal{V}_{w'}$) is maintained because expired or revoked terms safely transition to trapped operations (`e_val 0`) at runtime in `step_m`, preventing execution failures without requiring artificial capability persistence.

---

## 3. Concrete Coq/Rocq Mechanization Architecture
We have constructed a deep-embedded, compilable verification suite in the Cortex namespace:

*   **`AuthorityModel.v`**: Defines the carrier types and classes for authority preorders. **Fully proved.**
*   **`World.v`**: Formalizes the `World` tuple, proves the Kripke accessibility preorder (`world_accessible_preorder`), and proves contravariant capability decay (`valid_cap_monotone`). **Fully proved.**
*   **`Semantics.v`**: Implements deep-embedded expressions (`e_var`, `e_val`, `e_invoke`, `e_fork`) and lists the fuel-decrementing step relation `step_m` where fresh capability execution preserves the token expression `e_invoke c` on trace outputs. **Fully proved.**
*   **`LogicalRelation.v`**: Defines list-lookup typing context validation and the spatiotemporal execution relation `E_w`. **Fully proved.**
*   **`FTLR.v`**: Defines the deep inductive typing rules (`typing`) and proves the syntax-directed induction cases of the Fundamental Theorem of Logical Relations. **Fully proved.**
*   **`Substitution.v`**: Implements De Bruijn index shifting algebra (`ge_dec`, `shift`) and proves all structural lemmas: context weakening (`context_weakening`) and semantic substitution (`semantic_substitution_preserves_typing`). **Fully proved.**
*   **`Soundness.v`**: Synthesizes type safety, composing `fundamental_theorem` with complete mediation under `unified_soundness` to verify operational provenance safety. **Fully proved.**

---

## 4. Verified Architectural Dependency Hierarchy

The Rocq/Coq development is 100% closed under the global context. Both core safety and structural sub-systems are verified with **zero axioms** and **zero admitted lemmas**.

### 4.1 Core Soundness Pipeline
The following modules constitute the primary semantic safety path:
*   `World.v` → `Semantics.v` → `LogicalRelation.v` → `FTLR.v` → `Soundness.v`

This pipeline establishes the Kripke world structure, monitored operational semantics, logical relations, the Fundamental Theorem of Logical Relations (`fundamental_theorem`), and the top-level soundness theorem (`unified_soundness`).

`unified_soundness` inversion avoids open-term substitution lemmas by executing directly over the closed, substituted term configuration `subst_env γ e`.

### 4.2 Substitution Infrastructure
The following module provides structural typing proofs for context mutations:
*   `Substitution.v` → `context_weakening`, `semantic_substitution_preserves_typing`

These lemmas are verified unconditionally using the De Bruijn index shifting algebra and the FTLR.

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
```

**Interpretation**: All key results and structural sub-systems are 100% axiom-free and verified under the standard global context.

---

## 5. Verification Step Progression

| Step | Phase | Goal | Target Implementation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **01** | **Base Syntax & Semantics** | Define operational layer small-steps | Split monitored transition rules in `Semantics.v`. | **Completed** |
| **02** | **Kripke Frame Setup** | Establish world accessibility | Implement the world configuration in `World.v`. | **Completed** |
| **03** | **Logical Relation Design** | Mechanize value and trace relations | Construct definitions for $V_w$ and $E_w$ in `LogicalRelation.v`. | **Completed** |
| **04** | **ITP proof layout / skeleton** | Structural induction over typing | Implement typing rules and proof goals in `FTLR.v`. | **Completed** |
| **05** | **Soundness Composition** | Synthesize complete mediation safety | Compose FTLR lemma and complete mediation in `Soundness.v`. | **Completed** |
| **06** | **Proof Finalization** | Complete structural weakening & sub | Proved weakening and substitution in `Substitution.v` with zero admissions. | **Completed** |

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
grep -rn "Axiom" *.v      → Exit code 1 (zero matches)
```

---

## 7. Peer-Reviewed Publication Framing

*"We have fully mechanized the spatiotemporal logical-relation framework and soundness proof in Rocq/Coq. A direct kernel audit (Print Assumptions) confirms that all key results—including the Fundamental Theorem of Logical Relations (fundamental_theorem), top-level soundness (unified_soundness), De Bruijn context weakening (context_weakening), and semantic substitution (semantic_substitution_preserves_typing)—are verified with zero axioms and zero admitted lemmas, fully closed under the global context.*

*The framework handles the contravariant nature of spatiotemporal capability decay (spatial revocation and temporal epoch expiration) by proving that validity is contravariantly preserved under world accessibility (valid_cap_monotone), while semantic value monotonicity is maintained through runtime operational trapping of expired capabilities in the monitored reduction system."*
