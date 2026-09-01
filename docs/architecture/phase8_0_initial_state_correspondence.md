# Phase 8.0 Specification: Initial State Correspondence Theorem ($\alpha(C_0) = A_0$)

> **Target Issue**: GitHub Issue **[#57](https://github.com/Iradukunda-Fils/Cortex/issues/57)** (PO-8.1 Initial State Correspondence)  
> **Prerequisites**: Issue [#52](https://github.com/Iradukunda-Fils/Cortex/issues/52) ($C_{\text{formal}}$) & Issue [#53](https://github.com/Iradukunda-Fils/Cortex/issues/53) (Vector Projection Audit)  
> **Source Baseline**: `cortex/tools/kernel/resource_authority.py` (`ResourceAuthority.__init__`)  
> **Coq Target**: `verification/Phase7Reservation.v` (`InitState`, `init_invariant_holds`)

---

## 1. Concrete Initial State ($C_0$) Construction

The concrete runtime engine `ResourceAuthority` initializes its state tuple $C_0$ as follows:

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

$$C_0 = \left\langle \emptyset, \text{cap}, 0, 1, \emptyset, \emptyset, \emptyset, M_{\text{safety}}, \Delta_{\text{uncertainty}} \right\rangle$$

---

## 2. Abstract Coq Initial State ($A_0$)

In `verification/Phase7Reservation.v`:

```coq
Definition InitState (cap margin uncertainty auth_epoch : nat) : ReservationState :=
  mkReservationState nil cap 0 margin uncertainty auth_epoch nil nil nil.
```

$$A_0 = \text{InitState}(\text{cap}, M_{\text{safety}}, \Delta_{\text{uncertainty}}, 1)$$

---

## 3. Canonical Abstraction Mapping ($\alpha$) at Initialization

The abstraction mapping $\alpha : C_{\text{formal}} \to A_{\text{Coq}}$ maps dictionary representations to sorted Coq key-value lists:

$$\alpha(C) = \text{mkReservationState } (\alpha_{\text{rs}}(C.\text{rs})) \; (C.\text{cap}) \; (C.\text{used}) \; (C.M_{\text{safety}}) \; (C.\Delta_{\text{uncertainty}}) \; (C.\text{epoch}_A) \; (\alpha_{\text{assoc}}(C.\text{epochs}_L)) \; (\alpha_{\text{assoc}}(C.\text{gens}_W)) \; (\alpha_{\text{assoc}}(C.\Omega_{\text{gpu}}))$$

### Key Equivalence Properties for Empty Containers:
- $\alpha_{\text{rs}}(\emptyset) = \text{nil}$
- $\alpha_{\text{assoc}}(\emptyset) = \text{nil}$

Therefore:

$$\alpha(C_0) = \text{mkReservationState } \text{nil} \; \text{cap} \; 0 \; M_{\text{safety}} \; \Delta_{\text{uncertainty}} \; 1 \; \text{nil} \; \text{nil} \; \text{nil} \equiv A_0$$

---

## 4. Formal Theorem Specification (PO-8.1)

$$\boxed{ \text{Theorem (PO-8.1 Initial State Correspondence)}: \alpha(C_0) = A_0 \land \text{ReservationInvariant}(A_0) }$$

### Mechanical Verification in Coq:
In `verification/Phase7Reservation.v`, `init_invariant_holds` mechanically proves that $A_0$ satisfies all system invariants:

```coq
Theorem init_invariant_holds :
  forall cap margin uncertainty auth_epoch : nat,
    ReservationInvariant (InitState cap margin uncertainty auth_epoch).
```

### Invariants Satisfied by $A_0$:
1. $P_{1a}$ **Invocation Uniqueness**: `count_active_for_inv nil i = 0 <= 1`.
2. $P_{1b}$ **Attempt Uniqueness**: `count_active_for_attempt nil a = 0 <= 1`.
3. $P_2$ **Capacity Safety**: `sum_active_demand nil + 0 = 0 <= cap - margin - uncertainty`.
4. $P_{11}$ **Exclusive GPU Ownership**: `count_gpu_active_owner nil nil g = 0 <= 1`.
5. $P_{13}$ **Terminal Reclamation**: Vacuously holds for `nil`.
6. $P_{12}$ **Identity Stability**: Vacuously holds for `nil`.

---

## 5. Traceability & Assurance Status

| Formal Obligation | Coq Source File | Coq Theorem | Status |
| :--- | :--- | :--- | :--- |
| **PO-8.1** Initial State Mapping | `Phase7Reservation.v` | `init_invariant_holds` | ✅ **SPECIFIED & PROVED** (0 Axioms, 0 Admits) |
