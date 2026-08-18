# FC-03: Composed Relation & Monotonicity Proof
**Phase:** FORMAL MODEL CONSTRUCTION
**Status:** ACTIVE

## 1. Purpose and Scope
This document formalizes the composed target relation $R_{\text{target}}$ and proves the foundational monotonicity properties of the step-indexed Kripke logic. By showing that authorization containment is preserved under world refinements, we prove that our framework maintains semantic consistency even as authority bounds are dynamically attenuated, revoked, or consumed under execution.

Additionally, this module institutes the adversarial validation framework, defining the interface for testing malformed operational artifacts $\mathcal{A}^*$ designed to bypass the safety monitor.

## 2. The Composed Target Relation ($R_{\text{target}}$)
To bridge the gap between abstract state-space constraints and concrete execution traces, we compose our semantic predicates into a unified target judgment.

### Definition (The Composed Target Relation)
Let $\Lambda_0 \in A$ be an authority configuration, $\mathcal{A}$ be an operational artifact, $\tau$ be an execution trace, and $e$ be a terminal effect. The composed target relation $R_{\text{target}}(\Lambda_0, \mathcal{A}, \tau, e)$ holds if and only if it is definitionally equivalent to trace evaluation under the spatiotemporal logical relation:

$$R_{\text{target}}(\Lambda_0, \mathcal{A}, \tau, e) \triangleq \exists w_0 \in \mathcal{W} \text{ s.t. } w_0.\Lambda = \Lambda_0 \land \mathcal{A} \in \mathcal{E}_{w_0} \llbracket \tau \rrbracket \land \tau \rightsquigarrow e$$

Where:
*   $\mathcal{E}_{w_0} \llbracket \tau \rrbracket$ guarantees step-indexed spatiotemporal containment over all monitored transition steps.
*   $\tau \rightsquigarrow e$ represents the concrete operational trace evaluation stepping to terminal effect $e$.


---

## 3. Proof of the Fundamental Monotonicity Lemma
Before introducing mutated or malformed artifacts into the enactment engine, we must prove that the step-indexed logic $\llbracket \text{Allowed} \rrbracket_{w}$ is stable under world refinement.

### Lemma (World Monotonicity)
If $w' \sqsubseteq w$ and $(\mathcal{A}, \tau, e) \in \llbracket \text{Allowed} \rrbracket_{w}$, then $(\mathcal{A}, \tau, e) \in \llbracket \text{Allowed} \rrbracket_{w'}$.

### Proof by Induction
Let Kripke worlds $w = (\Lambda, m, n)$ and $w' = (\Lambda', m', n')$. By the definition of world compatibility ($w' \sqsubseteq w$), we must satisfy:
1.  $\Lambda' \preceq \Lambda$ (Authority Restriction)
2.  $m \rightsquigarrow m'$ (Monitor Progression)
3.  $n' \leq n$ (Step-index Decay)

We proceed by induction on the step index $n'$ of the future world $w'$.

#### Base Case: $n' = 0$
By the semantic definition of the zero-step world clause:
$$(\mathcal{A}, \tau, e) \in \llbracket \text{Allowed} \rrbracket_{(\Lambda', m', 0)} \iff \tau = \epsilon \land e = \text{idle}$$
This holds identically regardless of the structure of $\Lambda'$ or $m'$, satisfying the base case vacuously.

#### Inductive Step: Assume true for $n' - 1$, prove for $n' > 0$
Assume $(\mathcal{A}, \tau, e) \in \llbracket \text{Allowed} \rrbracket_w$. Because $n' \leq n$ and $n' > 0$, it follows that $n > 0$. Thus, the positive-step world clause applies to $w$.

Let the operational artifact $\mathcal{A}$ take an arbitrary monitored step under the refined world state:
$$(\Sigma, \Lambda', m', \mathcal{A}) \xrightarrow{g}_m (\Sigma', \Lambda'', m'', \mathcal{A}')$$

By the structural definition of our runtime assurance mechanism, any step permissible under a restricted authority configuration $\Lambda'$ and a progressed monitor $m'$ is a valid sub-behavior of the larger configuration $\Lambda$ at state $m$. Thus, there exists a corresponding step in the unrefined world:
$$(\Sigma, \Lambda, m, \mathcal{A}) \xrightarrow{g}_m (\Sigma', \bar{\Lambda}, \bar{m}, \mathcal{A}')$$

Applying the inductive definition of $\llbracket \text{Allowed} \rrbracket_{(\Lambda, m, n)}$ to this step, there exists a next world $w_{\text{next}} = (\bar{\Lambda}, \bar{m}, n - 1)$ such that $w_{\text{next}} \sqsubseteq w$, and:
$$(\mathcal{A}', \tau', e') \in \llbracket \text{Allowed} \rrbracket_{(\bar{\Lambda}, \bar{m}, n - 1)}$$

To apply the induction hypothesis, we must construct a next world for the refined path:
$$w'_{\text{next}} = (\Lambda'', m'', n' - 1)$$
and show $w'_{\text{next}} \sqsubseteq w_{\text{next}}$. We verify the three structural criteria:
*   **Authority:** Since $\Lambda' \preceq \Lambda$ and transitions are compositionally monotonic, the localized step preserves the restriction boundary: $\Lambda'' \preceq \bar{\Lambda}$.
*   **Monitor:** By monitor progression consistency, $m' \rightsquigarrow m''$ preserves the path relative to the unrefined progression: $\bar{m} \rightsquigarrow m''$.
*   **Step Index:** Since $n' \leq n$, it follows that $n' - 1 \leq n - 1$.

Therefore, $w'_{\text{next}} \sqsubseteq w_{\text{next}}$ holds. By the induction hypothesis, since $(\mathcal{A}', \tau', e') \in \llbracket \text{Allowed} \rrbracket_{w_{\text{next}}}$, it must hold that:
$$(\mathcal{A}', \tau', e') \in \llbracket \text{Allowed} \rrbracket_{w'_{\text{next}}}$$

By matching all cases (including specialized branches for effect-carrying steps $\xrightarrow{e}_m$ and capability invocations $\xrightarrow{\text{invoke}(c)}_m$), every future execution step from $w'$ maps safely into an allowed behavior within the decayed step budget.

$\blacksquare$ Monotonicity is preserved.

---

## 4. Adversarial Falsification Setup
With $R_{\text{target}}$ defined and the Monotonicity Lemma proven, we are ready to introduce the adversarial testing harness. We define a Malformed Artifact $\mathcal{A}^*$ as an operational construct designed to break the containment invariant by attempting an unmonitored transition $\xrightarrow{g}_{\text{bad}}$ that bypasses $\xrightarrow{g}_m$.

```text
                 [Initial World w = (Λ, m, n)]
                              │
               ┌──────────────┴──────────────┐
               │                             │
    Monitored Step (➔ g)_m       Malformed Leak (➔ g)_bad
               │                             │
               ▼                             ▼
       [World w' ⊑ w]               [Bypassed Monitor!]
  (Admissible & Constrained)      (Invariant Violated ❌)
```

The objective of our verification harness is to prove that if such an unmonitored transition is attempted:
$$\forall \tau, e. \quad (\mathcal{A}^*, \tau, e) \notin R_{\text{target}}(\Lambda, \mathcal{A}^*, \tau, e)$$
thus ensuring the relation remains unsatisifable under bypass compromises.

**Next Module (FC-04):** Construct the structural layout of the adversarial artifact $\mathcal{A}^*$ and execute falsification analysis to evaluate monitor completeness bounds.
