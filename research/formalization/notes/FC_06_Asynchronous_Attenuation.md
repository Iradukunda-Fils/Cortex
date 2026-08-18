# FC-06: Asynchronous Attenuation & Spatiotemporal Preorders
**Phase:** FORMAL MODEL CONSTRUCTION
**Status:** ACTIVE

## 1. Purpose and Scope
This document formalizes the mechanisms required to address the dynamic authority attenuation challenge. In real-world systems, authority transitions are not instantaneous across all execution contexts due to asynchronous execution loops, register caching, and compiler-level optimizations. 

To prevent stale-authority attacks—where an artifact actions a capability permitted in a past execution state but revoked in the current one—we expand our Kripke Kripke frame from a purely spatial containment model into a directed **spatiotemporal coordinate system** by introducing versioned authority epochs.

---

## 2. The Epoch-Indexed Kripke World Structure
We introduce a versioned authority epoch to guarantee that active capabilities are tracked temporally. Let a Kripke world $w$ be defined as the quadruple:
$$w = (\Lambda, m, n, \nu) \in \mathcal{W}$$

Where:
*   $\Lambda \in \mathbb{A}$ is the current restrictive authority set.
*   $m \in \text{MonState}$ is the internal configuration of the reference monitor.
*   $n \in \mathbb{N}$ represents the step-index (measuring remaining computational steps to guard against recursion/loops).
*   $\nu \in \mathbb{N}$ represents the strictly increasing authority epoch version.

The revised accessibility relation $\sqsubseteq$ on $\mathcal{W}$ formalizes the dual-axis evolution of spatial authority containment and temporal progress:
$$w' \sqsubseteq w \iff \left(\Lambda' \preceq \Lambda\right) \land \left(m \rightsquigarrow m'\right) \land \left(n' \le n\right) \land \left(\nu' \ge \nu\right)$$

> ### Note on Reflexivity
> To ensure $\sqsubseteq$ remains a valid preorder (reflexive and transitive), we relax strict inequalities ($<$ and $>$) to partial orders ($\le$ and $\ge$) for the base accessibility relation. Strict epoch progression ($\nu' > \nu$) is enforced specifically by attenuation transition steps rather than static world stability.

---

## 3. The Epoch-Indexed, Step-Indexed Logical Relation
We construct the semantic logical relation over expressions/artifacts $\mathcal{A}$ and observations under the spatiotemporal world $w$.

### 3.1 Value Relation ($\mathcal{V}_w$)
A capability token $c$ is logically valid in world $w$ if it belongs to the active authority set and its structural validity condition matches or spans the current epoch:
$$\mathcal{V}_{(\Lambda, m, n, \nu)}(c) \iff c \in \Lambda \land \forall w' \sqsubseteq (\Lambda, m, n, \nu). \quad c \in \text{Valid}(\Lambda', \nu')$$

### 3.2 Expression / Trace Relation ($\mathcal{E}_w$)
An operational artifact $\mathcal{A}$ resides within the logical relation $\mathcal{E}_w$ if, for all future accessible worlds, an execution step producing a non-idle effect is structurally bounded by both step-index validity and epoch freshness:

$$\mathcal{E}_{(\Lambda, m, n, \nu)}(\mathcal{A}) \iff \forall k < n. \quad \forall w' \sqsubseteq (\Lambda, m, n, \nu) \text{ s.t. } w'.n = k. \quad \forall \Sigma, \Sigma', m', m'', e.$$
$$\left( (\Sigma, \Lambda', m', \mathcal{A}) \xrightarrow{g} (\Sigma', \Lambda'', m'', e) \land e \neq \text{idle} \right) \implies \exists \tau_m. \quad \left( \tau_m \vdash_{\nu'} e \land e \in \llbracket \text{Allowed} \rrbracket_{w'} \right)$$

---

## 4. Theorem 2: Preservation of World Monotonicity
We prove that our spatiotemporal expansion does not collapse the logical framework by demonstrating that validity within the logical relation is stable under world transition steps.

### Theorem Statement
$$\forall w, w' \in \mathcal{W}. \quad w' \sqsubseteq w \implies \mathcal{E}_w(\mathcal{A}) \subseteq \mathcal{E}_{w'}(\mathcal{A})$$

### Formal Proof
Let $w = (\Lambda, m, n, \nu)$ and $w' = (\Lambda', m', n', \nu')$ be two worlds such that $w' \sqsubseteq w$. By definition of the accessibility relation, this implies:
1.  $\Lambda' \preceq \Lambda$ (Authority Contraction)
2.  $m \rightsquigarrow m'$ (Monitor State Evolution)
3.  $n' \le n$ (Step-Index Decrement)
4.  $\nu' \ge \nu$ (Epoch Advancement)

Assume $\mathcal{A} \in \mathcal{E}_w$. We must show that $\mathcal{A} \in \mathcal{E}_{w'}$. To verify this, we pick an arbitrary future world $w'' \sqsubseteq w'$ with a step-index $k < n'$.

Since $\sqsubseteq$ is transitive, we have:
$$w'' \sqsubseteq w' \land w' \sqsubseteq w \implies w'' \sqsubseteq w$$

Furthermore, because $w'' \sqsubseteq w'$, its step-index satisfies $w''.n = k < n'$. Given that $n' \le n$, it follows directly that $k < n$.

We now examine a concrete execution step taken in this future world $w''$:
$$(\Sigma, \Lambda'', m'', \mathcal{A}) \xrightarrow{g} (\Sigma', \Lambda''', m''', e) \quad \text{with } e \neq \text{idle}$$

Because $w'' \sqsubseteq w$ and $w''.n < n$, we can immediately instantiate the assumption $\mathcal{A} \in \mathcal{E}_w$ with respect to the world $w''$. This instantiation yields two critical structural witnesses:
1.  A monitored provenance trace matching the target epoch: $\tau_m \vdash_{\nu''} e$
2.  Semantic effect safety: $e \in \llbracket \text{Allowed} \rrbracket_{w''}$

These match the precise conditions required to satisfy $\mathcal{A} \in \mathcal{E}_{w'}$. Therefore, by universal generalization over all accessible sub-worlds, $\mathcal{A} \in \mathcal{E}_{w'}$. Monotonicity holds uniformly across both the restriction and temporal axes.

$\blacksquare$

---

## 5. Operational Resolution of the Stale-Authority Attack
The framework structurally neutralizes the cached capability vulnerability through the epoch coordination mechanism:

```text
       Epoch v_1 (Authorized)                  Epoch v_2 (Attenuated)
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│ World w_1: Λ_1 = {c_r, c_w}           │ │ World w_2: Λ_2 = {c_r}                │
│                                       │ │                                       │
│  Artifact caches c_w                  │ │  Artifact attempts invocation:        │
│  Valid(Λ_1, v_1) = TRUE               │ │  invoke(c_w) at epoch v_2             │
└───────────────────┬───────────────────┘ └───────────────────┬───────────────────┘
                    │                                         │
                    ▼                                         ▼
         [Monitor Validation]                      [Monitor Validation]
      c_w ∈ Λ_1 ∧ v_1 == v_1                     c_w ∉ Λ_2 ∧ v_2 > v_1
      ┌─────────────┴─────────────┐              ┌─────────────┴─────────────┐
      │ Allowed: Trace Proceed    │              │ Rejected: e = idle        │
      └───────────────────────────┘              └───────────────────────────┘
```

When $\mathcal{A}$ attempts to execute the stale write capability at epoch $\nu_2$, the monitor evaluates the operation against the current execution world state $w_2$. Because $\nu_2 > \nu_1$, the freshness condition in $\text{Valid}(\Lambda_2, \nu_2)$ fails completely since $c_w \notin \Lambda_2$. 

The step is instantly forced to evaluate as an unobservable internal configuration change ($e = \text{idle}$), blocking any external write effect $e_{\text{write}}$ from spilling into the environment.
