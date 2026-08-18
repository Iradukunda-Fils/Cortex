# FC-04: Adversarial Falsification & Complete Mediation
**Phase:** FORMAL MODEL CONSTRUCTION
**Status:** ACTIVE

## 1. Purpose and Scope
This document formalizes the Monitored Transition Monotonicity assumption and evaluates the Specialized Composed Relation ($\mathcal{R}_{\text{target}}$) against adversarial configurations. By attempting to falsify the safety of our framework using a crafted capability-escalation artifact ($\mathcal{A}^*$), we derive the necessary and sufficient runtime conditions under which our formal model is robust.

This active testing establishes the structural requirements for the underlying enactment engine hosting untrusted code under the parameter $c_{\text{arbitrary\_dev}}$.

---

## 2. Monitored Transition Monotonicity Assumption
To ground our inductive proofs and ensure Kripke world stability, we parameterize our operational engine with the following structural constraint:

> ### Assumption (Monitored Transition Monotonicity)
> For all semantic Kripke worlds $w = (\Lambda, m, n)$ and $w' = (\Lambda', m', n')$ such that $w' \sqsubseteq w$, if an operational artifact can step along a monitored path under the refined world:
> $$(\Sigma, \Lambda', m', \mathcal{A}) \xrightarrow{g}_m (\Sigma', \Lambda'', m'', \mathcal{A}')$$
> Then there must exist a corresponding transition under the unrefined world:
> $$(\Sigma, \Lambda, m, \mathcal{A}) \xrightarrow{g}_m (\Sigma', \bar{\Lambda}, \bar{m}, \mathcal{A}')$$
> Such that the resulting states preserve relational containment:
> $$\Lambda'' \preceq \bar{\Lambda} \quad \text{and} \quad m'' \rightsquigarrow \bar{m}$$

This condition formalizes **Complete Mediation Consistency**: narrowing the active authority context or advancing the monitor state must not expose raw execution behaviors that were absent in a more permissive state.

---

## 3. Construction of the Capability-Escalation Artifact ($\mathcal{A}^*$)
We construct an explicit, adversarial capability-escalation artifact $\mathcal{A}^* = \langle \mathcal{A}_{\text{valid}}, \mathcal{A}_{\text{hidden}}, \chi \rangle$ designed to test the robustness of $\mathcal{R}_{\text{target}}$ against ambient authority leaks.

### 3.1 The Structural Components
Let the initial system authority be constrained to a read-only configuration: $\Lambda = \{c_r\}$, where $c_r$ is a valid read capability token. The target resource is protected by a separate write capability token $c_w \notin \Lambda$.

*   **The Surface Artifact ($\mathcal{A}_{\text{valid}}$):** A piece of code that compiles down to a benign invocation:
    $$\mathcal{A}_{\text{valid}} \triangleq \text{invoke}(c_r) \cdot \text{return}(\text{data})$$
*   **The Hidden Payload ($\mathcal{A}_{\text{hidden}}$):** An inline routine utilizing an unmonitored raw pointer offset or ambient system trap to manufacture $c_w$ directly from memory configurations:
    $$\mathcal{A}_{\text{hidden}} \triangleq \text{inject\_forge}(c_w) \cdot \text{invoke}(c_w) \cdot \text{write}(\text{resource}, \text{malicious\_payload})$$
*   **The Trigger Condition ($\chi$):** A dynamic runtime condition (e.g., matching a specific clock cycle or stack allocation layout):
    $$\chi \triangleq (\text{cycle\_count} > \text{0xFFF})$$

### 3.2 Operational Step Breakdown
During the verification phase, $\mathcal{A}^*$ successfully yields $\mathcal{A}_{\text{valid}}$ under static derivation pipelines ($c_{\text{derive\_impl}}$). During early enactment steps, execution proceeds down the monitored path:
$$(\Sigma, \{c_r\}, m, \mathcal{A}^*) \xrightarrow{\text{invoke}(c_r)}_m (\Sigma', \{c_r\}, m', \mathcal{A}_{\text{valid}})$$

This transition is completely admissible under $\llbracket \text{Allowed} \rrbracket_{(\Lambda, m, n)}$ because $c_r \in \Lambda$. However, once the trigger condition $\chi$ is met, the artifact branches into its hidden variant without invoking the standard monitor hook:
$$(\Sigma', \{c_r\}, m', \mathcal{A}_{\text{valid}}) \xrightarrow{\chi} (\Sigma', \{c_r\}, m', \mathcal{A}_{\text{hidden}})$$

The critical escalation step attempts to execute:
$$(\Sigma', \{c_r\}, m', \mathcal{A}_{\text{hidden}}) \xrightarrow{g}_{\text{bad}} (\Sigma'', \{c_r\}, m', e_{\text{leak}})$$
where $e_{\text{leak}} = \text{write}(\text{resource}, \text{malicious\_payload})$.

---

## 4. Stress-Testing the Composed Relation
We evaluate $\mathcal{A}^*$ against the composed target relation $\mathcal{R}_{\text{target}}(\Lambda, \mathcal{A}^*, \tau, e)$ using our adversarial isolation property:

```text
                                [ Enactment of A* ]
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
     [ Engine Bypasses Monitor ]                      [ Complete Mediation Holds ]
      ➔ g_bad occurs unchecked                         ➔ g_bad captured by engine
                 │                                               │
                 ▼                                               ▼
   e_leak emitted outside ➔ g_m                     Transition fails / trace aborted
  (Result: R_target is UNSOUND)                    (Result: R_target is ROBUST)
```

### Case A: Enactment Engine Bypasses Complete Mediation
If the concrete execution environment permits $\xrightarrow{g}_{\text{bad}}$ to alter the state $\Sigma''$ without executing the monitor update sequence $\xrightarrow{g}_m$, then:
*   The historical trace records $\tau = \text{invoke}(c_r) \cdot \chi$.
*   The terminal effect $e_{\text{leak}}$ is emitted.

Because $\xrightarrow{g}_{\text{bad}}$ does not match any valid step quantified by the inductive case of $\llbracket \text{Allowed} \rrbracket$, the logical relation vacuously evaluates to true up to the point of the monitor bypass.
If this occurs, $\mathcal{R}_{\text{target}}(\Lambda, \mathcal{A}^*, \tau, e_{\text{leak}})$ evaluates to true, yet $e_{\text{leak}} \notin \text{Allowed}(\Lambda)$. **The model is falsified (Unsound).**

### Case B: Enactment Engine Enforces Boundary Mediation
If the execution environment enforces complete mediation at the binary or virtual machine layer, then any attempt to execute $\xrightarrow{g}_{\text{bad}}$ without an explicit monitor state transition is trapped. The engine either:
1.  **Injects a monitor fault**, mapping the step back into the monitored relation:
    $$(\Sigma', \{c_r\}, m', \mathcal{A}_{\text{hidden}}) \xrightarrow{\text{fault}}_m (\Sigma', \{c_r\}, m_{\text{abort}}, \emptyset)$$
2.  **Aborts execution entirely**, preventing the emission of $e_{\text{leak}}$, yielding $e = \text{idle} \in \text{Allowed}(\Lambda)$.

In this scenario, the artifact fails to satisfy the relational premises, or its leaked effect is successfully contained within $\text{Allowed}(\Lambda)$. **The model is robust.**

---

## 5. Architectural Synthesis

### The Complete Mediation Criterion
The composed relation $\mathcal{R}_{\text{target}}$ is structurally sound if and only if the concrete execution environment exposes no raw operational transitions capable of producing an effect $e \notin \text{idle}$ that cannot be mapped directly into a monitored transition step $\xrightarrow{g}_m$.

This conclusion shifts our research focus to a concrete implementation goal: we must ensure the runtime layer guarantees that the unmonitored transition relation is functionally empty:
$$\to_{\text{bad}} \; = \emptyset$$
for all externally observable effects.
