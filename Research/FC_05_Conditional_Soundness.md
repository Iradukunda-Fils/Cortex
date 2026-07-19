# FC-05: Conditional Soundness & Provenance Logic
**Phase:** FORMAL MODEL CONSTRUCTION
**Status:** ACTIVE

## 1. Purpose and Scope
This document formalizes the boundary where logical verification meets concrete system enforcement. Moving beyond ideal enforcement models, we establish the **Conditional Soundness Theorem**, construct the **Monitored Provenance Logic**, and map the decision tree that separates logical unsafeness from boundary violations. 

By replacing the absolute restriction of an empty unmonitored transition relation ($\xrightarrow{g}_{\text{bad}} = \emptyset$) with an **Effect-Silent Trace Restriction**, we allow for hardware and systems engineering optimizations (e.g., JIT compilation, GC, register caching) while ensuring complete behavioral soundness.

---

## 2. Formal Preliminaries & The Revised Invariants
Let $\Sigma \in \text{State}$ denote the concrete execution state, $\Lambda \in \mathbb{A}$ represent the active authority bounds in the restriction-monotone preorder $(\mathbb{A}, \preceq, \oplus, \mathbf{0})$, $m \in \text{MonState}$ be the internal reference monitor state, and $\mathcal{A}$ be the operational artifact. 

We distinguish between:
*   $\xrightarrow{g}_m$: The **monitored transition relation** representing steps checked and validated by the reference monitor.
*   $\xrightarrow{g}$: The **concrete execution relation** representing all transitions taken by the underlying execution container.

Each execution step emits some effect $e \in \text{Effects}$. We designate $e = \text{idle}$ as the internal, computationally unobservable effect mapping to arbitrary non-authority-relevant transformations.

> ### Definition 1 (Revised Complete Mediation Criterion)
> An execution environment satisfies Complete Mediation if and only if every concrete transition capable of producing an externally observable, authority-relevant effect is structurally mediated by the monitored transition relation:
> $$\forall \Sigma, \Sigma', \Lambda, \Lambda', m, m', \mathcal{A}, e. \quad \left( (\Sigma, \Lambda, m, \mathcal{A}) \xrightarrow{g} (\Sigma', \Lambda', m', e) \land e \neq \text{idle} \right) \implies (\Sigma, \Lambda, m, \mathcal{A}) \xrightarrow{g}_m (\Sigma', \Lambda', m', e)$$

> ### Definition 2 (Monitored Provenance Judgment)
> Let $\tau_m$ be a monitored execution trace consisting exclusively of steps valid under $\xrightarrow{g}_m$. The provenance judgment $\tau_m \vdash e$ establishes that the externally observable effect $e$ possesses a verified, unbroken chain of monitored derivations mapping directly back to the initial authority context $\Lambda_0$:
> $$\frac{e = \text{idle}}{\tau_m \vdash \text{idle}} \qquad \frac{(\Sigma_0, \Lambda_0, m_0, \mathcal{A}) \xrightarrow{g_1}_m \dots \xrightarrow{g_k}_m (\Sigma_k, \Lambda_k, m_k, e) \quad e \in \llbracket \text{Allowed} \rrbracket_{w_k}}{\tau_m \vdash e}$$

---

## 3. The Conditional Soundness Theorem
The composed relation $\mathcal{R}_{\text{target}}$ does not operate in an execution vacuum; its soundness is fundamentally dependent on the containment bounds of the enactment environment.

> ### Theorem 1 (Conditional Soundness of the Composed Relation)
> **Assume:**
> 1.  *Monitored Transition Monotonicity:* If $(\Sigma, \Lambda, m, \mathcal{A}) \xrightarrow{g}_m (\Sigma', \Lambda', m', e)$, then for any world $w = (\Lambda, m, n)$, the step preserves accessibility rules such that $w' \sqsubseteq w$.
> 2.  *World Monotonicity:* $\forall w, w'. \quad w' \sqsubseteq w \implies \llbracket \text{Allowed} \rrbracket_w \subseteq \llbracket \text{Allowed} \rrbracket_{w'}$.
> 3.  *Complete Mediation:* The environment satisfies the Revised Complete Mediation Criterion (Definition 1).
> 
> **Then:**
> For every operational artifact $\mathcal{A}$, concrete execution trace $\tau$, and terminal effect $e$:
> $$\mathcal{R}_{\text{target}}(\Lambda, \mathcal{A}, \tau, e) \implies \exists \tau_m. \quad \left( \tau_m \vdash e \land e \in \text{Allowed}(\Lambda) \right)$$

### Proof (Sketch by Induction on Trace Length)
We evaluate the trace length $k$ producing the terminal effect $e$.

*   **Case 1 ($e = \text{idle}$):**
    By Definition 1, a concrete transition producing no external effect ($e = \text{idle}$) is permitted to bypass $\xrightarrow{g}_m$ without violating the complete mediation premise. Applying the base case of Definition 2, the provenance judgment $\tau_m \vdash \text{idle}$ holds trivially.
*   **Case 2 ($e \neq \text{idle}$):**
    Suppose the concrete execution trace takes a step that violates the monitor transition system, such that $g \notin \xrightarrow{g}_m$.
    By Definition 1 (Complete Mediation), since $g$ is not mediated by $\xrightarrow{g}_m$, this transition cannot produce an effect $e \neq \text{idle}$.
    Thus, if an authority-relevant effect $e \neq \text{idle}$ is emitted, the step must have been mediated by $\xrightarrow{g}_m$.
    
    By Monitored Transition Monotonicity and the induction hypothesis, each mediated step preserves accessibility, maintaining $w_k \sqsubseteq w_0$. By World Monotonicity, the semantic containment of the execution state is preserved.
    
    Consequently, we can construct the monitored provenance trace $\tau_m$ entirely from the structural sequence of $\xrightarrow{g}_m$ transitions, yielding $\tau_m \vdash e$. Since $\mathcal{R}_{\text{target}}$ holds, $e \in \text{Allowed}(\Lambda)$ follows directly from the base logical admissibility relation $\llbracket \text{Allowed} \rrbracket_w$.

$\blacksquare$

---

## 4. Resolving the Applicability Boundary
By separating the logical layers, we clarify how the composed framework handles the capability-escalation artifact $\mathcal{A}^*$. An unmonitored escape does not render $\mathcal{R}_{\text{target}}$ true; it causes a **Failure of Applicability**.

```text
                  Concrete Execution Trace (τ)
                               │
                    Does τ bypass the monitor?
                       ───────┬───────
                              │
                      ┌───────┴───────┐
                     Yes              No
                      │               │
                [APPLICABILITY     [EVALUATE RELATION]
                  NON-ALIGNED]        │
                      │            Does e ∈ Allowed(Λ)?
                 Is e = idle?         ──────┬──────
                   ───┬───                  │
                      │             ┌───────┴───────┐
                  ┌───┴───┐        Yes              No
                 Yes      No        │               │
                  │       │     [SOUND]       [LOGICAL
               [SAFE]  [CRITERION              UNSOUNDNESS]
                        VIOLATION]
```

This matrix isolates compliance issues perfectly:
*   **Logical Unsoundness:** Occurs if $\mathcal{R}_{\text{target}}$ evaluates to true, the runtime container perfectly mediates the trace ($g \in \xrightarrow{g}_m$), yet an unauthorized effect $e_{\text{leak}} \notin \text{Allowed}(\Lambda)$ escapes. This points to a bug in the mathematical construction of the logical relation itself.
*   **Failure of Applicability:** Occurs when $\mathcal{A}^*$ executes an unmonitored transition $g_{\text{bad}} \notin \xrightarrow{g}_m$. The preconditions of the composed relation are broken. If the runtime system allows this unmonitored step to yield $e_{\text{leak}} \neq \text{idle}$, the execution environment fails the Complete Mediation Criterion, while the logical relation remains mathematically sound.

---

## 5. The Next Milestone: Dynamic Authority Attenuation
To test the robustness of this provenance-centered foundation, we introduce the next construction challenge: **Dynamic Authority Attenuation**.

Consider a systems environment where an operational artifact is stripped of rights mid-execution (representing a transition from $\Lambda_1$ to $\Lambda_2$ where $\Lambda_2 \prec \Lambda_1$). We model an adversary attempting to leverage asynchronous execution loops or stale cache states to emit an effect permitted under $\Lambda_1$ after the attenuation event to $\Lambda_2$ has completed.

```text
       [State s_1: Λ_1] ───(attenuate)───► [State s_2: Λ_2]
              │                                   │
              ▼ (Async loop / stale cache)        ▼
      [Emit effect local to Λ_1]           [Blocked! ❌]
```

**Next Module (FC-06):** Define the temporal world transition laws required to handle asynchronous attenuation, preventing race-condition authority leaks.
