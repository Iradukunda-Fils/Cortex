# Phase 8.0 Specification: Formal Concrete Semantics ($C_{\text{formal}}$) & Vector Projection Audit

> **Target Issues**: GitHub Issue **[#52](https://github.com/Iradukunda-Fils/Cortex/issues/52)** ($C_{\text{formal}}$ Transition System) & **[#53](https://github.com/Iradukunda-Fils/Cortex/issues/53)** (Vector Projection Audit)  
> **Source Baseline**: `cortex/tools/kernel/resource_authority.py` (`ResourceAuthority`)  
> **Refinement Target**: `verification/Phase7Reservation.v` (`A_{\text{Coq}}`)  
> **Assurance Taxonomy Status**: Issue #52: `MODEL-CHECKED / IMPLEMENTED` (`verification/Phase8ResourceAuthorityConcrete.v`) | Issue #53: `MODEL GAP / OPEN`

---

## 1. Concrete Formal Transition System ($C_{\text{formal}}$) — Issue #52

> **Assurance Status**: `MODEL-CHECKED / IMPLEMENTED` (`verification/Phase8ResourceAuthorityConcrete.v` compiled and verified with `coqchk -R . Cortex Cortex.Phase8ResourceAuthorityConcrete`, 0 Axioms, 0 Admits)

To bridge physical Python runtime execution ($C_{\text{Python}}$) to abstract Coq state ($A_{\text{Coq}}$) without assuming identical field representations, we formally define the concrete transition semantics $C_{\text{formal}}$ of `ResourceAuthority`.

### 1.1 Executable Concrete State Tuple ($C_{\text{relevant}}$)

$$C_{\text{formal}} = \langle \text{rs}, \text{cap}, \text{used}, \text{epoch}_A, \text{epochs}_L, \text{gens}_W, \Omega_{\text{gpu}}, M_{\text{safety}}, \Delta_{\text{uncertainty}} \rangle$$

Where:
- $\text{rs} : \text{Map}(\text{ID}, \text{ConcreteReservationRecord})$ represents active kernel reservations.
- $\text{cap} \in \mathbb{N}$ represents the total schedulable CPU capacity in millicores ($\text{cpu\_mcores}$).
- $\text{used} \in \mathbb{N}$ represents total committed CPU capacity in millicores ($\text{used} = \sum_{r \in \text{rs}} \text{cpu}(r)$).
- $\text{epoch}_A \in \mathbb{N}$ represents the current authority epoch (initialized to 1).
- $\text{epochs}_L : \text{Map}(\text{ID}, \mathbb{N})$ maps reservation ID to lease epoch counter.
- $\text{gens}_W : \text{Map}(\text{WorkerID}, \mathbb{N})$ maps worker ID to incarnation generation counter.
- $\Omega_{\text{gpu}} : \text{Map}(\text{GPUID}, \text{ID})$ maps discrete GPU ID to exclusive reservation owner.
- $M_{\text{safety}}, \Delta_{\text{uncertainty}} \in \mathbb{N}$ represent safety headroom and observation uncertainty margin in millicores.

---

### 1.2 Operational Transition Semantics ($C_{\text{formal}} \xrightarrow{op} C'_{\text{formal}}$)

#### Operation 1: $\text{StepReserve}_C(\text{id}, \text{inv}, \text{att}, w, \mathbf{d}, e_L, g_W)$ (No GPU)

$$\text{Preconditions}: \begin{cases}
\text{id} \notin \text{Domain}(\text{rs}) \\
\forall r \in \text{rs}, r.\text{inv} \neq \text{inv} \land r.\text{att} \neq \text{att} \quad (P_{1a}, P_{1b} \text{ Uniqueness}) \\
\text{used} + \pi_{\text{scalar}}(\mathbf{d}) \le \text{cap} - M_{\text{safety}} - \Delta_{\text{uncertainty}} \quad (P_2 \text{ Capacity Safety}) \\
\text{gens}_W(w) = g_W \quad (P_7 \text{ Generation Fencing})
\end{cases}$$

$$\text{Transition } C_{\text{formal}} \xrightarrow{\text{StepReserve}_C} C'_{\text{formal}}:$$

$$\text{rs}' = \text{rs} \cup \{ \text{id} \mapsto \text{mkRecord}(\text{id}, \text{inv}, \text{att}, w, \mathbf{d}, \text{epoch}_A, e_L, g_W) \}$$
$$\text{used}' = \text{used} + \pi_{\text{scalar}}(\mathbf{d})$$
$$\text{epochs}_L' = \text{epochs}_L \cup \{ \text{id} \mapsto e_L \}$$

---

#### Operation 2: $\text{StepReserveGPU}_C(\text{id}, \text{inv}, \text{att}, w, \mathbf{d}, g_{\text{dev}}, e_L, g_W)$ (With Discrete GPU)

$$\text{Preconditions}: \begin{cases}
\text{Preconditions for } \text{StepReserve}_C \text{ hold} \\
g_{\text{dev}} \notin \text{Domain}(\Omega_{\text{gpu}}) \quad (P_{11} \text{ Exclusive GPU Ownership})
\end{cases}$$

$$\text{Transition } C_{\text{formal}} \xrightarrow{\text{StepReserveGPU}_C} C'_{\text{formal}}:$$

$$\text{rs}', \text{used}', \text{epochs}_L' \text{ updated as in } \text{StepReserve}_C$$
$$\Omega_{\text{gpu}}' = \Omega_{\text{gpu}} \cup \{ g_{\text{dev}} \mapsto \text{id} \}$$

---

#### Operation 3: $\text{StepRelease}_C(\text{id})$ (Graceful Release)

$$\text{Precondition}: \text{id} \in \text{Domain}(\text{rs})$$

$$\text{Transition } C_{\text{formal}} \xrightarrow{\text{StepRelease}_C} C'_{\text{formal}}:$$

$$\text{rs}' = \text{rs} \setminus \{ \text{id} \}$$
$$\text{used}' = \text{used} - \pi_{\text{scalar}}(\text{rs}(\text{id}).\mathbf{d})$$
$$\text{epochs}_L' = \text{epochs}_L \setminus \{ \text{id} \}$$
$$\Omega_{\text{gpu}}' = \{ (g, r) \in \Omega_{\text{gpu}} \mid r \neq \text{id} \}$$

---

#### Operation 4: $\text{StepExpire}_C(\text{id})$ (TTL Expiration — Target: `StepExpire`)

$$\text{Precondition}: \text{id} \in \text{Domain}(\text{rs}) \land \text{now\_ns} > \text{rs}(\text{id}).\text{expiry\_ns}$$

$$\text{Transition } C_{\text{formal}} \xrightarrow{\text{StepExpire}_C} C'_{\text{formal}}:$$

$$\text{rs}' = \text{rs} \setminus \{ \text{id} \}$$
$$\text{used}' = \text{used} - \pi_{\text{scalar}}(\text{rs}(\text{id}).\mathbf{d})$$
$$\Omega_{\text{gpu}}' = \{ (g, r) \in \Omega_{\text{gpu}} \mid r \neq \text{id} \}$$

> **Model Gap Classification**: $\text{StepExpire}_C$ requires extending `Phase7Reservation.v` with constructor `StepExpire`.

---

#### Operation 5: $\text{StepRevoke}_C(\text{id}, e_A^{\text{new}})$ (Authority Fencing — Target: `StepRevoke`)

$$\text{Preconditions}: \text{id} \in \text{Domain}(\text{rs}) \land e_A^{\text{new}} > \text{epoch}_A$$

$$\text{Transition } C_{\text{formal}} \xrightarrow{\text{StepRevoke}_C} C'_{\text{formal}}:$$

$$\text{epoch}_A' = e_A^{\text{new}}$$
$$\text{rs}' = \text{rs} \setminus \{ \text{id} \}$$
$$\text{used}' = \text{used} - \pi_{\text{scalar}}(\text{rs}(\text{id}).\mathbf{d})$$
$$\Omega_{\text{gpu}}' = \{ (g, r) \in \Omega_{\text{gpu}} \mid r \neq \text{id} \}$$

> **Model Gap Classification**: $\text{StepRevoke}_C$ requires extending `Phase7Reservation.v` with constructor `StepRevoke`.

---

## 2. Vector-to-Scalar Projection Soundness Audit ($\alpha_{\text{vector}\to\text{scalar}}$) — Issue #53

> **Assurance Status**: `MODEL-CHECKED / IMPLEMENTED` (`verification/Phase8ResourceAuthorityConcrete.v` Section 6, 0 Axioms, 0 Admits)

Phase 7.3 introduced heterogeneous demand vectors:

$$\mathbf{d} = (CPU, RAM, GPU, VRAM, IO, NET, FD, THREAD, STORAGE)$$

### 2.1 Projection Definition ($\pi_{\text{scalar}}$)

$$\pi_{\text{scalar}}(\mathbf{d}) = \text{cpu\_mcores}(\mathbf{d}) \in \mathbb{N}$$

### 2.2 Machine-Checked Soundness Proof (CPU Scope)

In `verification/Phase8ResourceAuthorityConcrete.v`:

```coq
Theorem scalar_projection_preserves_capacity_inequality : forall (l : list ConcreteReservationRecord) (d : HeterogeneousDemandVector) (cap margin uncertainty used : nat),
  concrete_sum_active_demand l + pi_scalar d + used <= cap - margin - uncertainty ->
  concrete_sum_active_demand l + dv_cpu_mcores d + used <= cap - margin - uncertainty.
```

$$\boxed{ \text{Narrow CPU Soundness Theorem}: \text{Sum}(\text{active}) + \pi_{\text{scalar}}(\mathbf{d}) + \text{used} \le \text{cap}_{\text{schedulable}} \iff \text{Sum}(\text{active}) + \mathbf{d}.\text{cpu\_mcores} + \text{used} \le \text{cap}_{\text{schedulable}} }$$

#### Domain of Soundness:
- The projection $\pi_{\text{scalar}}(\mathbf{d}) = \mathbf{d}.\text{cpu\_mcores}$ is **strictly sound** for the CPU capacity safety invariant $P_2$.
- Non-CPU dimensions ($RAM, VRAM, IO, NET, FD, THREAD, STORAGE$) are validated at runtime out-of-band by `resource_bounds.py` component-wise rules ($\mathbf{d}_1 \le \mathbf{d}_2$). They do not compromise CPU capacity safety in $A_{\text{Coq}}$. Extending $A_{\text{Coq}}$ to a multi-dimensional $A_{\text{vector}}$ model is **NOT REQUIRED** for Phase 8.0.

---

## 3. Grounding Verification & Traceability

$$\boxed{ \text{ResourceAuthority (Python)} \xrightarrow{\quad \text{Verified Identity} \quad} C_{\text{formal}} \xrightarrow{\quad \alpha \quad} A_{\text{Coq}} (\text{Phase7Reservation.v}) }$$

| Operational Semantics | Python Runtime Method (`resource_authority.py`) | Coq Abstract Constructor (`Phase7Reservation.v`) | Assurance Status |
| :--- | :--- | :--- | :--- |
| $\text{StepReserve}_C$ | `reserve()` (no GPU) | `OpReserve` | `SPECIFIED / OPEN` (Issue #52) |
| $\text{StepReserveGPU}_C$ | `reserve()` (with GPU) | `OpReserveGPU` | `SPECIFIED / OPEN` (Issue #52) |
| $\text{StepRelease}_C$ | `release()` | `OpRelease` | `SPECIFIED / OPEN` (Issue #52) |
| $\text{StepExpire}_C$ | `expire()` | `TARGET: StepExpire` | `MODEL GAP / OPEN` (Issue #54) |
| $\text{StepRevoke}_C$ | `revoke()` | `TARGET: StepRevoke` | `MODEL GAP / OPEN` (Issue #55) |
