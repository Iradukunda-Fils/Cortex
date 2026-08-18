# FC-01: Authority Preorder & Kripke World Structure
**Phase:** FORMAL MODEL CONSTRUCTION
**Status:** ACTIVE

## 1. Purpose and Scope
This document initiates the Formal Construction phase of the research program. Having completed the descriptive literature survey (Documents 07–13), we now transition from mapping the landscape to engineering the bridge.

The objective of this module is to formalize the algebraic structure governing authority configurations ($\Lambda$) and to define the Kripke world structure $w = (\Lambda, m, n)$ that serves as the foundation for the composed relation $R_{\text{target}}$.

To ensure the Kripke world is universally applicable across the diverse authority paradigms cataloged in `09_Authority_Semantics.md`, we define the authority order $\Lambda' \preceq \Lambda$ not as a specific implementation (e.g., set-subset) but as an **Algebraic Authority Preorder**. This allows us to unify models—such as O-Caps (possession-based) and Linear Logic (resource-based)—under a single formal interface.

## 2. The Authority Preorder

### Definition (Authority Preorder)
An Authority Preorder is a structure $\mathbb{A} = (A, \preceq, \oplus, \mathbf{0})$, where:

*   $A$ is the set of possible authority configurations.
*   $\preceq$ is a partial order (the **restriction order**).
*   $\oplus : A \times A \to A$ is a composition operator (associative, commutative, with identity $\mathbf{0}$).
*   $\mathbf{0} \in A$ is the element of minimal authority (the "nothing" permission).

### 2.1 Axiomatic Requirements
For this structure to satisfy our monotonicity invariant ($\text{Authority}(w') \subseteq \text{Authority}(w)$) and support the transitions identified in `09_Authority_Semantics.md`, it must satisfy the following axioms:

> **Axiom 1: Compositional Monotonicity**
> The order $\preceq$ must be congruent with $\oplus$. This ensures that combining permissions preserves refinement:
> $$\forall a, b, c \in A. \quad a \preceq b \implies (a \oplus c) \preceq (b \oplus c)$$
> This allows us to prove properties about sub-fragments of authority without knowing the full system state.

> **Axiom 2: Identity Consistency**
> The identity $\mathbf{0}$ represents the lack of actionable authority. It must be the bottom of the preorder:
> $$\forall a \in A. \quad \mathbf{0} \preceq a$$

> **Axiom 3: The Conservation Property**
> Total authority in the system is not created out of thin air, but conserved through interactions. For any transition $\Lambda' \preceq \Lambda$:
> $$\text{Authority}(\Lambda) = \text{Authority}(\Lambda') \oplus \text{Authority}(\text{Residual})$$
> where $\text{Residual}$ represents the "spent" authority.

## 3. Formal Authority Operations
Using this algebra, we map the informal operations from `09_Authority_Semantics.md` to formal state-transition functions that guarantee $\Lambda' \preceq \Lambda$:

| Operation | Formal Definition | Proof Obligation |
| --- | --- | --- |
| **Attenuation** | $\text{attenuate}(\Lambda, c) = \Lambda \setminus \{c\}$ | $(\Lambda \setminus \{c\}) \preceq \Lambda$ |
| **Revocation** | $\text{revoke}(\Lambda, p) = \Lambda \setminus \{p\}$ | $(\Lambda \setminus \{p\}) \preceq \Lambda$ |
| **Consumption** | $\text{consume}(\Lambda, r) = \Lambda \ominus r$ | $(\Lambda \ominus r) \preceq \Lambda$ |
| **Borrowing** | $\text{borrow}(\Lambda, b) = \Lambda_{\text{owned}} \oplus \text{temp}(b)$ | $(\Lambda_{\text{owned}} \oplus \text{temp}(b)) \preceq \Lambda$ |

> **Note:** $\ominus$ denotes the partial subtraction operator, defined if and only if $r \preceq \Lambda$.

## 4. Categorical Mappings (Proof of Generality)
To confirm this algebra is sufficiently abstract, we verify that the primary models from `09_Authority_Semantics.md` are instances of this structure:

### Instance A: Object Capabilities (O-Caps)
*   $A$: Power set of reference edges $\mathcal{P}(\mathcal{E})$.
*   $\preceq$: Subset relation ($\subseteq$).
*   $\oplus$: Set union ($\cup$).
*   **Axiom Check:** Set union is monotonic with respect to subset inclusion; O-Cap attenuation corresponds to removing elements from the reference set. **Valid.**

### Instance B: Linear/Affine Systems (Separation Logic)
*   $A$: Partial Commutative Monoid (PCM).
*   $\preceq$: Defined via composition: $a \preceq b \iff \exists c. \; a \oplus c = b$.
*   $\oplus$: The disjoint combination ($\ast$).
*   **Axiom Check:** Compositional monotonicity is the fundamental property of separation logic (the Frame Rule). **Valid.**

## 5. The Kripke World Structure

### Definition (Kripke World)
A Kripke world is a triple:
$$w = (\Lambda, m, n) \in \text{Worlds} = A \times \text{Monitor} \times \mathbb{N}$$

Where:
*   $\Lambda \in A$ is the current authority configuration drawn from the Authority Preorder.
*   $m \in \text{Monitor}$ is the current state of the runtime enforcement automaton (as defined in `13_Runtime_Assurance.md`).
*   $n \in \mathbb{N}$ is the step-index bounding the remaining execution steps available for validation.

### Definition (World Compatibility / Accessibility Relation)
A world transition $w \sqsubseteq w'$ (where $w = (\Lambda, m, n)$ and $w' = (\Lambda', m', n')$) is **well-formed** if and only if:

1.  $\Lambda' \preceq \Lambda$ — **Authority Restriction:** the successor world possesses no more authority than the predecessor.
2.  $m \rightsquigarrow m'$ — **Monitor Progression:** the monitor state advances according to a valid transition of the enforcement automaton.
3.  $n' \leq n$ — **Step-Index Decay:** the remaining execution budget strictly does not increase.

### Monotonicity Interface Theorem
> **Theorem FC-01.1 (Authority Preservation):**
> For any execution trace $\tau$ generated by an artifact $\mathcal{A}$ under a monitor $m$, if the initial authority is $\Lambda$ and the terminal authority is $\Lambda'$, then the execution is sound if and only if $\Lambda' \preceq \Lambda$.

## 6. Summary of Constructed Components
At the conclusion of this module, we have formally established:

| Component | Mathematical Object | Definition |
| --- | --- | --- |
| **Authority Space** | $\mathbb{A} = (A, \preceq, \oplus, \mathbf{0})$ | Algebraic Authority Preorder |
| **World Structure** | $w = (\Lambda, m, n)$ | Kripke World Triple |
| **Accessibility** | $w \sqsubseteq w'$ | 3-point compatibility interface |
| **Monotonicity** | $\Lambda' \preceq \Lambda$ | Authority Restriction invariant |

## 7. Next Construction Step: The Logical Relation
We have now established the structural "world" ($\Lambda$) and the rules for its evolution. We have all components for the logical relation:

*   **Semantic Domain:** $w \in \text{Worlds} = A \times \text{Monitor} \times \mathbb{N}$
*   **Accessibility:** $w \sqsubseteq w'$ defined by the 3-point interface.
*   **Monotonicity:** $\Lambda' \preceq \Lambda$.

We are now prepared to define the step-indexed logical relation $\llbracket \tau \rrbracket_w$. This will be the "heart" of the composed relation $R_{\text{target}}$.

**Next Module (FC-02):** Define the inductive cases for the logical relation, specifically for effect-carrying artifacts $\mathcal{A}$ and capability-passing invocations.
