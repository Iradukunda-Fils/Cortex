# FC-02: Step-Indexed Logical Relation for Authority & Enactment
**Phase:** FORMAL MODEL CONSTRUCTION
**Status:** ACTIVE

## 1. Purpose and Scope
This document constructs the step-indexed Kripke logical relation designed to bridge the gap between untrusted operational artifacts $\mathcal{A}$ and dynamic authority configurations $\Lambda$. Built directly upon the mathematical foundations established in `FC-01: Authority Preorder & Kripke World Structure`, this module defines the inductive cases for the relation, focusing specifically on:

1.  **Capability/Authority Passing Values:** How unforgeable references and delegation tokens are semantically constrained.
2.  **Effect-Carrying Computations:** How execution steps containing side-effects are bounded by the Kripke world context $w = (\Lambda, m, n)$.

By constructing this relation without assuming a trusted compiler or type-checker, we satisfy the constraints of the threat model ($c_{\text{arbitrary\_dev}}$), ensuring robustness in the presence of unverified operational artifacts.

## 2. Relational Setup & Types
Since our primary interest is authority propagation rather than a specific language syntax, we parameterize the logical relation over a generalized semantic type system containing:
*   **Capabilities ($\text{Cap}(\alpha)$):** Types representing authorization tokens or references to invoke capabilities parameterized by action bounds $\alpha$.
*   **Computations ($T \, ! \, \epsilon$):** Types representing evaluation terms that yield a result of type $T$ while producing observable side-effects bounded by the set $\epsilon$.

Our logical relation is split into a **Value Relation** ($\mathcal{V}_w\llbracket \tau \rrbracket$) mapping values to semantic behaviors under world $w$, and a **Computation Relation** ($\mathcal{E}_w\llbracket T \, ! \, \epsilon \rrbracket$) mapping operational configurations to permitted execution traces.

For all definitions, let $w = (\Lambda, m, n) \in \text{Worlds}$ be a Kripke world, and let $w' = (\Lambda', m', n') \sqsupseteq w$ represent a compatible future world where $\Lambda' \preceq \Lambda$, $m \rightsquigarrow m'$, and $n' \leq n$.

## 3. The Value Relation ($\mathcal{V}_w\llbracket \tau \rrbracket$)
The value relation specifies how semantic values are constrained, indexed by the typing structure and the active Kripke world:

### 3.1 Base Values
For standard inert data types (e.g., integers, booleans), the relation is world-independent:
$$\mathcal{V}_{(\Lambda, m, n)}\llbracket \text{Base} \rrbracket = \{ v \mid v \text{ is a literal value} \}$$

### 3.2 Dynamic Capabilities and Reference Monotonicity
A capability value $v$ is a valid member of type $\text{Cap}(\alpha)$ if it authorizes only actions that are bounded by the active preorder state $\Lambda$. Crucially, to support the Kripke world expansion, this definition must hold monotonically across all future accessible worlds:

$$\mathcal{V}_{(\Lambda, m, n)}\llbracket \text{Cap}(\alpha) \rrbracket = \left\{ v \mid \forall w' \sqsupseteq (\Lambda, m, n). \quad \text{Access}(v) \preceq \Lambda' \land \text{Actions}(v) \subseteq \alpha \right\}$$

Where:
*   $\text{Access}(v)$ is the algebraic authority bound required to reference or invoke $v$.
*   $\text{Actions}(v)$ maps the capability handle to its permitted operational side-effects.

This monotonic quantification ensures that if a capability is valid in the current world, it remains safe to pass and use in any attenuated or revoked future world.

## 4. The Computation Relation ($\mathcal{E}_w\llbracket T \, ! \, \epsilon \rrbracket$)
The computation relation governs operational configurations stepping through the enactment loop. Because we operate under the attacker model $c_{\text{arbitrary\_dev}}$, we cannot assume that the intermediate operational artifact $\mathcal{A}$ has been vetted by compile-time rules. 

Instead, the computation relation is defined semantically. A configuration $C = (\Sigma, \mathcal{A})$ is in the relation for $n$ steps if its execution either halts safely without violating the active monitor, or takes a trace step preserving the Kripke world invariants.

### Formal Inductive Definition
We define $(\Sigma, \mathcal{A}) \in \mathcal{E}_{(\Lambda, m, n)}\llbracket T \, ! \, \epsilon \rrbracket$ by induction on the step-index $n$:

1.  **Zero Steps ($n = 0$):**
    All configurations are trivially safe for zero steps:
    $$\mathcal{E}_{(\Lambda, m, 0)}\llbracket T \, ! \, \epsilon \rrbracket = \text{Configurations}$$

2.  **Non-Zero Steps ($n > 0$):**
    A configuration $(\Sigma, \mathcal{A}) \in \mathcal{E}_{(\Lambda, m, n)}\llbracket T \, ! \, \epsilon \rrbracket$ if and only if one of the following holds:
    *   **Termination:** The enactment engine halts in a success state, returning a terminal value $v$ and executing no further effects:
        $$(\Sigma, \mathcal{A}) \xrightarrow{\text{enact}}^* (\Sigma_{\text{term}}, \text{val } v) \implies v \in \mathcal{V}_{(\Lambda, m, n)}\llbracket T \rrbracket$$
    *   **Enactment Step Progression:** The configuration takes a single operational step, generating trace event $e$ and producing a new configuration $(\Sigma', \mathcal{A}')$:
        $$(\Sigma, \mathcal{A}) \xrightarrow{\text{enact}} (\Sigma', \mathcal{A}') \quad \text{emitting } e$$
        For this step to be relationally valid, there must exist a successor Kripke world $w' = (\Lambda', m', n-1) \sqsupseteq (\Lambda, m, n)$ such that:
        1.  **Effect Monotonicity:** $e \in \epsilon$ (the effect is within the specified boundary).
        2.  **Monitor Compliance:** The monitor transition evaluates successfully:
            $$\delta_M(m, e) = m' \neq \bot$$
        3.  **Authority Attenuation:** The successor authority $\Lambda'$ accounts for any consumption or delegation triggered during the step:
            $$\Lambda' \preceq \Lambda \quad \text{and} \quad \Lambda \text{ is updated according to the operation rules in FC-01}$$
        4.  **Inductive Continuation:** The remaining computation is safe for the remaining execution budget:
            $$(\Sigma', \mathcal{A}') \in \mathcal{E}_{w'}\llbracket T \, ! \, \epsilon \rrbracket$$

## 5. Inductive Case for Capability Invocations
When a capability $v \in \mathcal{V}_w\llbracket \text{Cap}(\alpha) \rrbracket$ is invoked with argument $u$, the enactment engine executes a nested transition. We model this via a function-type construction:

$$\mathcal{V}_{(\Lambda, m, n)}\llbracket \text{Cap}(\alpha) \to (T \, ! \, \epsilon) \rrbracket = \left\{ f \mid \forall w' \sqsupseteq (\Lambda, m, n). \; \forall u \in \mathcal{V}_{w'}\llbracket \text{Cap}(\alpha) \rrbracket. \quad (f \cdot u) \in \mathcal{E}_{w'}\llbracket T \, ! \, \epsilon \cup \alpha \rrbracket \right\}$$

This formulation ensures that the lateral effects of invoking a capability cannot exceed the union of the capability's declared actions ($\alpha$) and the computation's global effect bounds ($\epsilon$).

## 6. Treatment of the Attacker Capability $c_{\text{arbitrary\_dev}}$
Under the adversary model $c_{\text{arbitrary\_dev}}$, raw operational artifacts injected by an attacker will fail to satisfy the inductive step progression since they may trigger illegal transitions $\delta_M(m, e) = \bot$. 

The logical relation handles this by enforcing that any artifact $\mathcal{A}^*$ which successfully executes under a monitor $m$ is relationally equivalent to a safe execution path. If the monitor prevents the step, the relation trivially rejects the execution trace, preventing it from satisfying the premise of $R_{\text{target}}$.

## 7. Next Construction Step: The Composed Relation
With the step-indexed logical relation $\llbracket \tau \rrbracket_w$ formulated, we can now assemble the complete, composed relation $R_{\text{target}}(\Lambda_t, \mathcal{A}, \tau, e)$ that binds:
1.  The initial authority context $\Lambda_t$.
2.  The untrusted artifact $\mathcal{A}$ under evaluation.
3.  The trace history $\tau$.
4.  The terminal effect output $e$.

**Next Module (FC-03):** Formulate the composed relation and state the Core Preservation Theorem proving that the relation holds under unverified artifact modifications.
