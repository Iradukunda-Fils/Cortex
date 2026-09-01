# Phase 8.0 Specification: Coq Model Gap Extensions (`StepExpire` & `StepRevoke`)

> **Target Issues**: GitHub Issue **[#54](https://github.com/Iradukunda-Fils/Cortex/issues/54)** (`StepExpire`) & **[#55](https://github.com/Iradukunda-Fils/Cortex/issues/55)** (`StepRevoke`)  
> **Prerequisites**: Issue [#52](https://github.com/Iradukunda-Fils/Cortex/issues/52) ($C_{\text{formal}}$) & Issue [#53](https://github.com/Iradukunda-Fils/Cortex/issues/53) (Vector Projection Audit)  
> **Source Baseline**: `cortex/tools/kernel/resource_authority.py` (`expire()`, `revoke()`)  
> **Coq Target File**: `verification/Phase7Reservation.v` (`StepOp`, `Step` inductive relation)

---

## 1. Governance Policy on Operational Non-Collapsing

$$\boxed{ \text{Strict Rule}: \text{Prohibit silently aliasing } Expire \equiv Release \text{ or } Revoke \equiv Release \text{ in Coq} }$$

While `release()`, `expire()`, and `revoke()` all trigger capacity reclamation and GPU owner cleanup, they represent distinct semantic state transitions with different audit logs, WAL frame types, and epoch fencing requirements:

| Dimension | `StepRelease` | `StepExpire` (Issue #54) | `StepRevoke` (Issue #55) |
| :--- | :--- | :--- | :--- |
| **Trigger Source** | Client / Application | Kernel TTL Timer | Epoch Succession / Admin Fencing |
| **Status Transition** | `StatusReleased` | `StatusExpired` | `StatusRevoked` |
| **Epoch Advancement** | None | None | `rs_authority_epoch' > rs_authority_epoch` |
| **WAL Log Frame** | `$WAL\_RELEASE$` | `$WAL\_EXPIRE$` | `$WAL\_REVOKE$` |

---

## 2. Issue #54 Specification — `StepExpire` Model Extension

### 2.1 Concrete Runtime Transition ($\text{StepExpire}_C$)
Executed by `ResourceAuthority.expire(res_id, now_ns)`:

$$\text{Preconditions}: \begin{cases}
\text{res\_id} \in \text{Domain}(\text{rs}) \\
\text{rs}[\text{res\_id}].\text{status} = \text{StatusActive} \\
\text{now\_ns} > \text{rs}[\text{res\_id}].\text{expiry\_ns}
\end{cases}$$

$$\text{Postconditions}: \begin{cases}
\text{rs}' = \text{map\_expire}(\text{res\_id}, \text{rs}) \\
\text{used}' = \text{used} - \pi_{\text{scalar}}(\text{rs}[\text{res\_id}].\mathbf{d}) \\
\Omega_{\text{gpu}}' = \text{gpu\_release}(\Omega_{\text{gpu}}, \text{res\_id})
\end{cases}$$

### 2.2 Coq Constructor Extension (`Phase7Reservation.v`)

```coq
Fixpoint map_expire (target_id : ReservationId) (l : list Reservation) : list Reservation :=
  match l with
  | nil => nil
  | cons r tl =>
      (if Nat.eqb (res_id r) target_id
       then mkReservation (res_id r) (res_inv r) (res_att r) (res_worker r)
                          (res_demand r) (res_authority_epoch r)
                          (res_lease_epoch r) (res_generation r) StatusExpired
       else r) :: map_expire target_id tl
  end.
```

Adding constructor to `Step`:

```coq
  | StepExpire : forall (s : ReservationState) (target_id : ReservationId),
      Step s (OpExpire target_id)
        (mkReservationState
           (map_expire target_id (rs_reservations s))
           (rs_capacity s)
           (rs_used_capacity s)
           (rs_safety_margin s)
           (rs_uncertainty s)
           (rs_authority_epoch s)
           (rs_lease_epochs s)
           (rs_generations s)
           (gpu_release (rs_gpu_owners s) target_id))
```

---

## 3. Issue #55 Specification — `StepRevoke` Model Extension

### 3.1 Concrete Runtime Transition ($\text{StepRevoke}_C$)
Executed by `ResourceAuthority.revoke(res_id, new_epoch)`:

$$\text{Preconditions}: \begin{cases}
\text{res\_id} \in \text{Domain}(\text{rs}) \\
\text{rs}[\text{res\_id}].\text{status} = \text{StatusActive} \\
\text{new\_epoch} > \text{rs\_authority\_epoch}
\end{cases}$$

$$\text{Postconditions}: \begin{cases}
\text{epoch}_A' = \text{new\_epoch} \\
\text{rs}' = \text{map\_revoke}(\text{res\_id}, \text{rs}) \\
\text{used}' = \text{used} - \pi_{\text{scalar}}(\text{rs}[\text{res\_id}].\mathbf{d}) \\
\Omega_{\text{gpu}}' = \text{gpu\_release}(\Omega_{\text{gpu}}, \text{res\_id})
\end{cases}$$

### 3.2 Coq Constructor Extension (`Phase7Reservation.v`)

```coq
Fixpoint map_revoke (target_id : ReservationId) (l : list Reservation) : list Reservation :=
  match l with
  | nil => nil
  | cons r tl =>
      (if Nat.eqb (res_id r) target_id
       then mkReservation (res_id r) (res_inv r) (res_att r) (res_worker r)
                          (res_demand r) (res_authority_epoch r)
                          (res_lease_epoch r) (res_generation r) StatusRevoked
       else r) :: map_revoke target_id tl
  end.
```

Adding constructor to `Step`:

```coq
  | StepRevoke : forall (s : ReservationState) (target_id : ReservationId) (new_epoch : Epoch),
      new_epoch > rs_authority_epoch s ->
      Step s (OpRevoke target_id)
        (mkReservationState
           (map_revoke target_id (rs_reservations s))
           (rs_capacity s)
           (rs_used_capacity s)
           (rs_safety_margin s)
           (rs_uncertainty s)
           new_epoch
           (rs_lease_epochs s)
           (rs_generations s)
           (gpu_release (rs_gpu_owners s) target_id))
```

---

## 4. Preservation of Invariant Theorems

Both `StepExpire` and `StepRevoke` preserve `ReservationInvariant`:

$$\boxed{ \forall s \text{ op } s', \text{Step } s \text{ op } s' \land \text{ReservationInvariant}(s) \implies \text{ReservationInvariant}(s') }$$

Because transitioning status from `StatusActive` to `StatusExpired` or `StatusRevoked`:
1. Reduces `sum_active_demand`, maintaining capacity safety $P_2$.
2. Reduces `count_active_for_inv` and `count_active_for_attempt`, maintaining uniqueness $P_{1a}, P_{1b}$.
3. Releases GPU ownership via `gpu_release`, maintaining GPU uniqueness $P_{11}$.
4. Satisfies terminal reclamation $P_{13}$ (`is_active_status StatusExpired = false`).

---

## 5. Traceability & Backlog Mapping

| Operation | Model Gap Issue | Proposed Extension | Invariant Preservation | Status |
| :--- | :--- | :--- | :--- | :--- |
| `expire()` | **Issue #54** | `OpExpire` / `StepExpire` | `step_preserves_invariant` | ✅ **SPECIFIED** |
| `revoke()` | **Issue #55** | `OpRevoke` / `StepRevoke` | `step_preserves_invariant` | ✅ **SPECIFIED** |
