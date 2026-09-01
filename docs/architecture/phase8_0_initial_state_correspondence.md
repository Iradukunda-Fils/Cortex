# Phase 8.0 Specification: Initial State Correspondence Theorem ($\alpha(C_0) = A_0$)

> **Target Issue**: GitHub Issue **[#57](https://github.com/Iradukunda-Fils/Cortex/issues/57)** (PO-8.1 Initial State Correspondence)  
> **Prerequisites**: Issue [#52](https://github.com/Iradukunda-Fils/Cortex/issues/52) ($C_{\text{formal}}$) & Issue [#53](https://github.com/Iradukunda-Fils/Cortex/issues/53) (Vector Projection Audit)  
> **Source Baseline**: `cortex/tools/kernel/resource_authority.py` (`ResourceAuthority.__init__`)  
> **Coq Target**: `verification/Phase7Reservation.v` (`InitState`, `init_invariant_holds`)  
> **Assurance Taxonomy Status**: `MODEL-CHECKED / IMPLEMENTED` (`verification/Phase8ResourceAuthorityConcrete.v` `initial_state_refinement`, 0 Axioms, 0 Admits)

---

## 1. Concrete Initial State ($C_{\text{Python},0}$) Construction

The concrete runtime engine `ResourceAuthority` initializes its state tuple $C_{\text{Python},0}$ as follows:

```python
class ResourceAuthority:
    def __init__(
        self,
        max_capacity: int = 10000,
        safety_margin: float = 0.05,
        telemetry_uncertainty: float = 0.02,
    ):
        self._capacity = max_capacity
        self._used_capacity = 0
        self._reservations = {}
        self._authority_epoch = 1
        self._lease_epochs = {}
        self._gpu_owners = {}
        self._worker_generations = {}
        self._safety_margin = int(max_capacity * safety_margin)
        self._telemetry_uncertainty = int(max_capacity * telemetry_uncertainty)
```

In $C_{\text{formal}}$ notation:

$$C_{\text{Python},0} = \left\langle \emptyset, \text{cap}, 0, 1, \emptyset, \emptyset, \emptyset, M_{\text{safety}}, \Delta_{\text{uncertainty}} \right\rangle$$

---

## 2. Abstract Coq Initial State ($A_{\text{Coq},0}$)

In `verification/Phase7Reservation.v`:

```coq
Definition InitState (cap margin uncertainty auth_epoch : nat) : ReservationState :=
  mkReservationState nil cap 0 margin uncertainty auth_epoch nil nil nil.
```

$$A_{\text{Coq},0} = \text{InitState}(\text{cap}, M_{\text{safety}}, \Delta_{\text{uncertainty}}, 1)$$

---

## 3. Concrete Initial State Refinement Theorem (`initial_state_refinement` — PROVEN in Coq)

In `verification/Phase8ResourceAuthorityConcrete.v`:

```coq
Theorem initial_state_refinement : forall (cap margin uncertainty auth_epoch : nat),
  alpha_state (mkConcreteState nil cap 0 margin uncertainty auth_epoch nil nil nil) =
  InitState cap margin uncertainty auth_epoch /\
  ReservationInvariant (alpha_state (mkConcreteState nil cap 0 margin uncertainty auth_epoch nil nil nil)).
```

$$\boxed{ \alpha(C_{\text{formal},0}) = A_{\text{Coq},0} \land \text{ReservationInvariant}(\alpha(C_{\text{formal},0})) }$$

---

## 4. Traceability & Assurance Status

| Obligation | Target Artifact | Assurance Label | Verification Command / Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| Abstract $A_{\text{Coq},0}$ Invariant Safety | `verification/Phase7Reservation.v` | `MODEL-CHECKED` | `coqchk -R . Cortex Phase7Reservation` (`init_invariant_holds`) | ✅ `PROVEN` |
| Concrete Initial State Refinement ($\alpha(C_0) = A_0 \land \text{Inv}(\alpha(C_0))$) | `verification/Phase8ResourceAuthorityConcrete.v` | `MODEL-CHECKED` | `coqchk -R . Cortex Cortex.Phase8ResourceAuthorityConcrete` (`initial_state_refinement`) | ✅ `PROVEN / CLOSED` |

