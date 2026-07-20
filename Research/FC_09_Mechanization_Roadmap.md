# FC-09: Interactive Theorem Prover (ITP) Mechanization Roadmap
**Phase:** FORMAL MODEL SKELTON MECHANIZATION
**Status:** ACTIVE (Roadmapped Proof Development)

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

---

## 3. Concrete Coq/Rocq Mechanization Architecture
We have constructed a deep-embedded, compilable verification suite in the Cortex namespace:

*   **`AuthorityModel.v`**: Defines the carrier types and classes for authority preorders.
*   **`World.v`**: Formalizes the `World` tuple, proves the Kripke accessibility preorder (`world_accessible_preorder`), and proves `valid_cap_monotone`.
*   **`Semantics.v`**: Implements deep-embedded expressions (`e_var`, `e_val`, `e_invoke`, `e_fork`) and lists the fuel-decrementing step relation `step_m` where fresh capability execution preserves the token expression `e_invoke c` on trace outputs.
*   **`LogicalRelation.v`**: Defines list-lookup typing context validation and the spatiotemporal execution relation `E_w`.
*   **`FTLR.v`**: Defines the deep inductive typing rules (`typing`) and proves the syntax-directed induction cases of the Fundamental Theorem of Logical Relations.
*   **`Substitution.v`**: Houses the **active proof engineering boundary** of the mechanization. Implements the De Bruijn index shifting algebra (`ge_dec`, `shift`) and declares context weakening (`context_weakening`), value relation monotonicity (`V_w_monotonicity`), env validity monotonicity (`env_valid_monotonicity`), and semantic substitution (`semantic_substitution_preserves_typing`) as admitted.
*   **`Soundness.v`**: Synthesizes type safety, composing `fundamental_theorem` with complete mediation under `unified_soundness` to verify operational provenance safety.

---

## 4. Verification Step Progression

| Step | Phase | Goal | Target Implementation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **01** | **Base Syntax & Semantics** | Define operational layer small-steps | Split monitored transition rules in `Semantics.v`. | **Completed** |
| **02** | **Kripke Frame Setup** | Establish world accessibility | Implement the world configuration in `World.v`. | **Completed** |
| **03** | **Logical Relation Design** | Mechanize value and trace relations | Construct definitions for $V_w$ and $E_w$ in `LogicalRelation.v`. | **Completed** |
| **04** | **ITP proof layout / skeleton** | Structural induction over typing | Implement typing rules and proof goals in `FTLR.v`. | **Completed** |
| **05** | **Soundness Composition** | Synthesize complete mediation safety | Compose FTLR lemma and complete mediation in `Soundness.v`. | **Completed** |
| **06** | **Active Proof Engineering** | Complete structural substitution | Discharge the 4 admitted lemmas in `Substitution.v`. | **ACTIVE** |

---

## 5. Peer-Reviewed Publication Framing
By maintaining semantic transparency about the verification boundaries, the paper presents a falsifiable mechanization progress roadmap:

*   **Spatiotemporal World Model**: *"Formally specified Kripke frame mapping authority contraction to step-index decay."*
*   **Core Operational Monitor**: *"Axiomatized trace-refinement monitor providing a foundational blueprint for complete mediation."*
*   **Logical Relations Loop**: *"A deep-embedded syntax skeleton establishing the structural continuity of the Fundamental Theorem."*
*   **Mechanization Progress**: *"Core semantic structures established; proof of the underlying semantic substitution engine matches context weakening and index-shifting algebra and is under construction (`Substitution.v`)."*
