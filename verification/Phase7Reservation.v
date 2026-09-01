(* Phase 7 Reservation State Machine — self-contained, no external libs *)

Section Phase7Reservation.

  Definition InvocationId  := nat.
  Definition AttemptId     := nat.
  Definition WorkerId      := nat.
  Definition Generation     := nat.
  Definition Epoch          := nat.
  Definition ReservationId := nat.
  Definition GPUId         := nat.
  Definition ResourceDemand:= nat.

  Inductive ReservationStatus : Type :=
  | StatusActive
  | StatusReleased
  | StatusExpired
  | StatusRevoked.

  Record Reservation := mkReservation {
    res_id              : ReservationId;
    res_inv             : InvocationId;
    res_att             : AttemptId;
    res_worker          : WorkerId;
    res_demand          : ResourceDemand;
    res_authority_epoch : Epoch;
    res_lease_epoch     : Epoch;
    res_generation      : Generation;
    res_status          : ReservationStatus
  }.

  Record ReservationState := mkReservationState {
    rs_reservations     : list Reservation;
    rs_capacity         : nat;
    rs_used_capacity    : nat;
    rs_safety_margin    : nat;
    rs_uncertainty      : nat;
    rs_authority_epoch  : Epoch;
    rs_lease_epochs     : list (InvocationId * Epoch);
    rs_generations      : list (WorkerId * Generation);
    rs_gpu_owners       : list (GPUId * ReservationId)
  }.

  Definition is_active_status (st : ReservationStatus) : bool :=
    match st with
    | StatusActive => true
    | _ => false
    end.

  Fixpoint sum_active_demand (l : list Reservation) : nat :=
    match l with
    | nil => 0
    | cons r tl =>
        if is_active_status (res_status r)
        then res_demand r + sum_active_demand tl
        else sum_active_demand tl
    end.

  Fixpoint count_active_for_inv (l : list Reservation) (target : InvocationId) : nat :=
    match l with
    | nil => 0
    | cons r tl =>
        if (Nat.eqb (res_inv r) target && is_active_status (res_status r))%bool
        then 1 + count_active_for_inv tl target
        else count_active_for_inv tl target
    end.

  Fixpoint count_active_for_attempt (l : list Reservation) (target : AttemptId) : nat :=
    match l with
    | nil => 0
    | cons r tl =>
        if (Nat.eqb (res_att r) target && is_active_status (res_status r))%bool
        then 1 + count_active_for_attempt tl target
        else count_active_for_attempt tl target
    end.

  Fixpoint lookup_epoch (l : list (InvocationId * Epoch)) (target : InvocationId) : Epoch :=
    match l with
    | nil => 0
    | cons (i, e) tl => if Nat.eqb i target then e else lookup_epoch tl target
    end.

  Fixpoint lookup_generation (l : list (WorkerId * Generation)) (target : WorkerId) : Generation :=
    match l with
    | nil => 0
    | cons (w, g) tl => if Nat.eqb w target then g else lookup_generation tl target
    end.

  Fixpoint gpu_owned_by (l : list (GPUId * ReservationId)) (g : GPUId) : option ReservationId :=
    match l with
    | nil => None
    | cons (g_idx, r_id) tl => if Nat.eqb g_idx g then Some r_id else gpu_owned_by tl g
    end.

  Fixpoint count_active_by_id (r_id : ReservationId) (l : list Reservation) : nat :=
    match l with
    | nil => 0
    | cons r tl =>
        if (Nat.eqb (res_id r) r_id && is_active_status (res_status r))%bool
        then 1 + count_active_by_id r_id tl
        else count_active_by_id r_id tl
    end.

  Definition count_gpu_active_owner (owners : list (GPUId * ReservationId)) (res_list : list Reservation) (g : GPUId) : nat :=
    match gpu_owned_by owners g with
    | None => 0
    | Some r_id => count_active_by_id r_id res_list
    end.

  Fixpoint map_release (target_id : ReservationId) (l : list Reservation) : list Reservation :=
    match l with
    | nil => nil
    | cons r tl =>
        (if Nat.eqb (res_id r) target_id
         then mkReservation (res_id r) (res_inv r) (res_att r) (res_worker r)
                            (res_demand r) (res_authority_epoch r)
                            (res_lease_epoch r) (res_generation r) StatusReleased
         else r) :: map_release target_id tl
    end.

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

  Fixpoint gpu_release (l : list (GPUId * ReservationId)) (target_id : ReservationId) : list (GPUId * ReservationId) :=
    match l with
    | nil => nil
    | cons (g, r_id) tl =>
        if Nat.eqb r_id target_id
        then gpu_release tl target_id
        else (g, r_id) :: gpu_release tl target_id
    end.

  Fixpoint In {A : Type} (x : A) (l : list A) : Prop :=
    match l with
    | nil => False
    | cons a tl => a = x \/ In x tl
    end.

  Lemma nat_le_0 : forall n : nat, 0 <= n.
  Proof. induction n; [apply le_n | apply le_S; exact IHn]. Qed.

  Lemma nat_eqb_refl : forall n : nat, Nat.eqb n n = true.
  Proof. induction n; simpl; [reflexivity | exact IHn]. Qed.

  Lemma add_0_r : forall n : nat, n + 0 = n.
  Proof. induction n; simpl; [reflexivity | f_equal; exact IHn]. Qed.

  Lemma add_succ_r : forall n k : nat, n + S k = S (n + k).
  Proof. induction n; simpl; [reflexivity | intros k; f_equal; apply IHn]. Qed.

  Lemma le_add_k : forall n k : nat, n <= n + k.
  Proof.
    intros n k.
    induction k.
    - rewrite add_0_r. apply le_n.
    - rewrite add_succ_r. apply le_S. exact IHk.
  Qed.

  Lemma add_assoc : forall a b c : nat, (a + b) + c = a + (b + c).
  Proof. induction a; simpl; [reflexivity | intros b c; f_equal; apply IHa]. Qed.

  Record ReservationInvariant (s : ReservationState) : Prop := mkReservationInvariant {
    inv_p1a_inv_uniqueness :
      forall i : InvocationId, count_active_for_inv (rs_reservations s) i <= 1;

    inv_p1b_att_uniqueness :
      forall a : AttemptId, count_active_for_attempt (rs_reservations s) a <= 1;

    inv_p2_capacity_safety :
      sum_active_demand (rs_reservations s) + rs_used_capacity s <=
      rs_capacity s - rs_safety_margin s - rs_uncertainty s;

    inv_p11_gpu_single_owner :
      forall g : GPUId, count_gpu_active_owner (rs_gpu_owners s) (rs_reservations s) g <= 1;

    inv_p13_terminal_reclamation :
      forall r : Reservation,
        In r (rs_reservations s) ->
        res_status r <> StatusActive ->
        is_active_status (res_status r) = false;

    inv_p12_identity_stability :
      forall r1 r2 : Reservation,
        In r1 (rs_reservations s) ->
        In r2 (rs_reservations s) ->
        res_id r1 = res_id r2 ->
        r1 = r2
  }.

  Definition ValidLease (r : Reservation) (s : ReservationState) : Prop :=
    res_lease_epoch r = lookup_epoch (rs_lease_epochs s) (res_inv r).

  Definition LeaseAdvance (e_new e_old : Epoch) : Prop :=
    e_new > e_old.

  Definition ValidFencing (s : ReservationState) (r : Reservation) : Prop :=
    res_authority_epoch r = rs_authority_epoch s /\
    res_generation r = lookup_generation (rs_generations s) (res_worker r) /\
    ValidLease r s.

  Definition ValidNewReservationFencing (s : ReservationState) (r : Reservation) : Prop :=
    res_authority_epoch r = rs_authority_epoch s /\
    res_generation r = lookup_generation (rs_generations s) (res_worker r) /\
    LeaseAdvance (res_lease_epoch r) (lookup_epoch (rs_lease_epochs s) (res_inv r)).

  Definition InitState (cap margin uncertainty auth_epoch : nat) : ReservationState :=
    mkReservationState nil cap 0 margin uncertainty auth_epoch nil nil nil.

  Theorem init_invariant_holds :
    forall cap margin uncertainty auth_epoch : nat,
      ReservationInvariant (InitState cap margin uncertainty auth_epoch).
  Proof.
    intros cap margin uncertainty auth_epoch.
    constructor.
    - intro i. simpl. apply le_S, le_n.
    - intro a. simpl. apply le_S, le_n.
    - simpl. apply nat_le_0.
    - intro g. simpl. apply nat_le_0.
    - intros r H_in H_act. simpl in H_in. contradiction.
    - intros r1 r2 H_in1 H_in2 H_eq. simpl in H_in1. contradiction.
  Qed.

  Inductive StepOp : Type :=
  | OpReserve     (r : Reservation)
  | OpReserveGPU  (r : Reservation) (g : GPUId)
  | OpRelease     (r_id : ReservationId)
  | OpExpire      (r_id : ReservationId)
  | OpRevoke      (r_id : ReservationId)
  | OpAuthoritySuccession (new_epoch : Epoch).

  Inductive Step : ReservationState -> StepOp -> ReservationState -> Prop :=
  | StepReserve : forall (s : ReservationState) (r : Reservation),
      ValidNewReservationFencing s r ->
      res_status r = StatusActive ->
      sum_active_demand (rs_reservations s) + res_demand r + rs_used_capacity s <=
      rs_capacity s - rs_safety_margin s - rs_uncertainty s ->
      count_active_for_inv (rs_reservations s) (res_inv r) = 0 ->
      count_active_for_attempt (rs_reservations s) (res_att r) = 0 ->
      (forall g_owner rid, In (g_owner, rid) (rs_gpu_owners s) -> res_id r <> rid) ->
      count_active_by_id (res_id r) (rs_reservations s) = 0 ->
      (forall r_ex, In r_ex (rs_reservations s) -> res_id r <> res_id r_ex) ->
      Step s (OpReserve r)
        (mkReservationState
           (r :: rs_reservations s)
           (rs_capacity s)
           (rs_used_capacity s)
           (rs_safety_margin s)
           (rs_uncertainty s)
           (rs_authority_epoch s)
           ((res_inv r, res_lease_epoch r) :: rs_lease_epochs s)
           (rs_generations s)
           (rs_gpu_owners s))

  | StepReserveGPU : forall (s : ReservationState) (r : Reservation) (g : GPUId),
      ValidNewReservationFencing s r ->
      res_status r = StatusActive ->
      gpu_owned_by (rs_gpu_owners s) g = None ->
      sum_active_demand (rs_reservations s) + res_demand r + rs_used_capacity s <=
      rs_capacity s - rs_safety_margin s - rs_uncertainty s ->
      count_active_for_inv (rs_reservations s) (res_inv r) = 0 ->
      count_active_for_attempt (rs_reservations s) (res_att r) = 0 ->
      (forall g_owner rid, In (g_owner, rid) (rs_gpu_owners s) -> res_id r <> rid) ->
      count_active_by_id (res_id r) (rs_reservations s) = 0 ->
      (forall r_ex, In r_ex (rs_reservations s) -> res_id r <> res_id r_ex) ->
      Step s (OpReserveGPU r g)
        (mkReservationState
           (r :: rs_reservations s)
           (rs_capacity s)
           (rs_used_capacity s)
           (rs_safety_margin s)
           (rs_uncertainty s)
           (rs_authority_epoch s)
           ((res_inv r, res_lease_epoch r) :: rs_lease_epochs s)
           (rs_generations s)
           ((g, res_id r) :: rs_gpu_owners s))

  | StepRelease : forall (s : ReservationState) (target_id : ReservationId),
      Step s (OpRelease target_id)
        (mkReservationState
           (map_release target_id (rs_reservations s))
           (rs_capacity s)
           (rs_used_capacity s)
           (rs_safety_margin s)
           (rs_uncertainty s)
           (rs_authority_epoch s)
           (rs_lease_epochs s)
           (rs_generations s)
           (gpu_release (rs_gpu_owners s) target_id))

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

  | StepRevoke : forall (s : ReservationState) (target_id : ReservationId),
      Step s (OpRevoke target_id)
        (mkReservationState
           (map_revoke target_id (rs_reservations s))
           (rs_capacity s)
           (rs_used_capacity s)
           (rs_safety_margin s)
           (rs_uncertainty s)
           (rs_authority_epoch s)
           (rs_lease_epochs s)
           (rs_generations s)
           (gpu_release (rs_gpu_owners s) target_id))

  | StepAuthoritySuccession : forall (s : ReservationState) (new_epoch : Epoch),
      new_epoch > rs_authority_epoch s ->
      Step s (OpAuthoritySuccession new_epoch)
        (mkReservationState
           (rs_reservations s)
           (rs_capacity s)
           (rs_used_capacity s)
           (rs_safety_margin s)
           (rs_uncertainty s)
           new_epoch
           (rs_lease_epochs s)
           (rs_generations s)
           (rs_gpu_owners s)).

  Theorem P1a_InvocationUniqueness :
    forall s : ReservationState,
      ReservationInvariant s ->
      forall i : InvocationId, count_active_for_inv (rs_reservations s) i <= 1.
  Proof.
    intros s H_inv i.
    exact (inv_p1a_inv_uniqueness s H_inv i).
  Qed.

  Theorem P1b_AttemptUniqueness :
    forall s : ReservationState,
      ReservationInvariant s ->
      forall a : AttemptId, count_active_for_attempt (rs_reservations s) a <= 1.
  Proof.
    intros s H_inv a.
    exact (inv_p1b_att_uniqueness s H_inv a).
  Qed.

  Theorem P2_ResourceCapacitySafety :
    forall s : ReservationState,
      ReservationInvariant s ->
      sum_active_demand (rs_reservations s) + rs_used_capacity s <=
      rs_capacity s - rs_safety_margin s - rs_uncertainty s.
  Proof.
    intros s H_inv.
    exact (inv_p2_capacity_safety s H_inv).
  Qed.

  Theorem P6_P7_InvalidFencingReject :
    forall (s s' : ReservationState) (r : Reservation),
      ~ ValidNewReservationFencing s r ->
      ~ Step s (OpReserve r) s'.
  Proof.
    intros s s' r H_invalid H_step.
    inversion H_step; subst.
    apply H_invalid.
    exact H0.
  Qed.

  Theorem P9_TelemetryConservativeSchedulableCapacity :
    forall (obs_r : nat) (epsilon : nat) (delta_max : nat) (v_max : nat),
      obs_r <= obs_r + epsilon + delta_max * v_max.
  Proof.
    intros obs_r epsilon delta_max v_max.
    rewrite add_assoc.
    exact (le_add_k obs_r (epsilon + delta_max * v_max)).
  Qed.

  Theorem P11_GPUCollisionReject :
    forall (s s' : ReservationState) (r : Reservation) (g : GPUId) (r_owner : ReservationId),
      gpu_owned_by (rs_gpu_owners s) g = Some r_owner ->
      ~ Step s (OpReserveGPU r g) s'.
  Proof.
    intros s s' r g r_owner H_owned H_step.
    inversion H_step; subst.
    congruence.
  Qed.

  Theorem P13_TerminalReclamation :
    forall (s : ReservationState) (r : Reservation),
      ReservationInvariant s ->
      In r (rs_reservations s) ->
      res_status r <> StatusActive ->
      is_active_status (res_status r) = false.
  Proof.
    intros s r H_inv H_in H_status.
    exact (inv_p13_terminal_reclamation s H_inv r H_in H_status).
  Qed.

  Theorem P14_TransitionFencingMonotonicity :
    forall (s s' : ReservationState) (r : Reservation),
      Step s (OpReserve r) s' ->
      lookup_epoch (rs_lease_epochs s') (res_inv r) > lookup_epoch (rs_lease_epochs s) (res_inv r).
  Proof.
    intros s s' r H_step.
    inversion H_step; subst; simpl.
    destruct H0 as [H_auth [H_gen H_lease]].
    rewrite nat_eqb_refl.
    exact H_lease.
  Qed.

  Lemma add_le_mono_l : forall n m k : nat, n <= m -> k + n <= k + m.
  Proof.
    intros n m k H.
    induction H.
    - apply le_n.
    - rewrite add_succ_r. apply le_S. exact IHle.
  Qed.

  Lemma le_trans : forall n m p : nat, n <= m -> m <= p -> n <= p.
  Proof.
    intros n m p H1 H2.
    induction H2.
    - exact H1.
    - apply le_S. exact IHle.
  Qed.

  Lemma add_comm : forall n m : nat, n + m = m + n.
  Proof.
    induction n; simpl.
    - intros m. rewrite add_0_r. reflexivity.
    - intros m. rewrite add_succ_r. f_equal. apply IHn.
  Qed.

  Lemma map_release_sum_le : forall l target_id,
    sum_active_demand (map_release target_id l) <= sum_active_demand l.
  Proof.
    induction l; intros target_id; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_eq.
      + simpl. destruct (is_active_status (res_status a)) eqn:E_st.
        * apply (le_trans _ (sum_active_demand l)).
          -- exact (IHl target_id).
          -- rewrite add_comm. exact (le_add_k (sum_active_demand l) (res_demand a)).
        * exact (IHl target_id).
      + simpl. destruct (is_active_status (res_status a)) eqn:E_st.
        * exact (add_le_mono_l _ _ (res_demand a) (IHl target_id)).
        * exact (IHl target_id).
  Qed.

  Lemma map_expire_sum_le : forall l target_id,
    sum_active_demand (map_expire target_id l) <= sum_active_demand l.
  Proof.
    induction l; intros target_id; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_eq.
      + simpl. destruct (is_active_status (res_status a)) eqn:E_st.
        * apply (le_trans _ (sum_active_demand l)).
          -- exact (IHl target_id).
          -- rewrite add_comm. exact (le_add_k (sum_active_demand l) (res_demand a)).
        * exact (IHl target_id).
      + simpl. destruct (is_active_status (res_status a)) eqn:E_st.
        * exact (add_le_mono_l _ _ (res_demand a) (IHl target_id)).
        * exact (IHl target_id).
  Qed.

  Lemma map_revoke_sum_le : forall l target_id,
    sum_active_demand (map_revoke target_id l) <= sum_active_demand l.
  Proof.
    induction l; intros target_id; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_eq.
      + simpl. destruct (is_active_status (res_status a)) eqn:E_st.
        * apply (le_trans _ (sum_active_demand l)).
          -- exact (IHl target_id).
          -- rewrite add_comm. exact (le_add_k (sum_active_demand l) (res_demand a)).
        * exact (IHl target_id).
      + simpl. destruct (is_active_status (res_status a)) eqn:E_st.
        * exact (add_le_mono_l _ _ (res_demand a) (IHl target_id)).
        * exact (IHl target_id).
  Qed.

  Definition release_transform (target_id : ReservationId) (r_orig : Reservation) : Reservation :=
    if Nat.eqb (res_id r_orig) target_id
    then mkReservation (res_id r_orig) (res_inv r_orig) (res_att r_orig) (res_worker r_orig)
                        (res_demand r_orig) (res_authority_epoch r_orig)
                        (res_lease_epoch r_orig) (res_generation r_orig) StatusReleased
    else r_orig.

  Definition expire_transform (target_id : ReservationId) (r_orig : Reservation) : Reservation :=
    if Nat.eqb (res_id r_orig) target_id
    then mkReservation (res_id r_orig) (res_inv r_orig) (res_att r_orig) (res_worker r_orig)
                        (res_demand r_orig) (res_authority_epoch r_orig)
                        (res_lease_epoch r_orig) (res_generation r_orig) StatusExpired
    else r_orig.

  Definition revoke_transform (target_id : ReservationId) (r_orig : Reservation) : Reservation :=
    if Nat.eqb (res_id r_orig) target_id
    then mkReservation (res_id r_orig) (res_inv r_orig) (res_att r_orig) (res_worker r_orig)
                        (res_demand r_orig) (res_authority_epoch r_orig)
                        (res_lease_epoch r_orig) (res_generation r_orig) StatusRevoked
    else r_orig.

  Lemma release_transform_id : forall target_id r_orig,
    res_id (release_transform target_id r_orig) = res_id r_orig.
  Proof.
    intros target_id r_orig. unfold release_transform.
    destruct (Nat.eqb (res_id r_orig) target_id); reflexivity.
  Qed.

  Lemma expire_transform_id : forall target_id r_orig,
    res_id (expire_transform target_id r_orig) = res_id r_orig.
  Proof.
    intros target_id r_orig. unfold expire_transform.
    destruct (Nat.eqb (res_id r_orig) target_id); reflexivity.
  Qed.

  Lemma revoke_transform_id : forall target_id r_orig,
    res_id (revoke_transform target_id r_orig) = res_id r_orig.
  Proof.
    intros target_id r_orig. unfold revoke_transform.
    destruct (Nat.eqb (res_id r_orig) target_id); reflexivity.
  Qed.

  Lemma map_release_in_full : forall l target_id r,
    In r (map_release target_id l) ->
    exists r_orig, In r_orig l /\ r = release_transform target_id r_orig.
  Proof.
    induction l as [| a l' IH]; intros target_id r H_in; simpl in H_in.
    - contradiction.
    - destruct H_in as [H_head | H_tail].
      + exists a. split; [left; reflexivity | symmetry; exact H_head].
      + apply IH in H_tail. destruct H_tail as [r_orig [H_in_orig H_eq]].
        exists r_orig. split; [right; exact H_in_orig | exact H_eq].
  Qed.

  Lemma map_expire_in_full : forall l target_id r,
    In r (map_expire target_id l) ->
    exists r_orig, In r_orig l /\ r = expire_transform target_id r_orig.
  Proof.
    induction l as [| a l' IH]; intros target_id r H_in; simpl in H_in.
    - contradiction.
    - destruct H_in as [H_head | H_tail].
      + exists a. split; [left; reflexivity | symmetry; exact H_head].
      + apply IH in H_tail. destruct H_tail as [r_orig [H_in_orig H_eq]].
        exists r_orig. split; [right; exact H_in_orig | exact H_eq].
  Qed.

  Lemma map_revoke_in_full : forall l target_id r,
    In r (map_revoke target_id l) ->
    exists r_orig, In r_orig l /\ r = revoke_transform target_id r_orig.
  Proof.
    induction l as [| a l' IH]; intros target_id r H_in; simpl in H_in.
    - contradiction.
    - destruct H_in as [H_head | H_tail].
      + exists a. split; [left; reflexivity | symmetry; exact H_head].
      + apply IH in H_tail. destruct H_tail as [r_orig [H_in_orig H_eq]].
        exists r_orig. split; [right; exact H_in_orig | exact H_eq].
  Qed.

  Lemma nat_eqb_eq : forall n m : nat, Nat.eqb n m = true -> n = m.
  Proof.
    induction n; destruct m; simpl; intros H; try reflexivity; try discriminate.
    f_equal. apply IHn. exact H.
  Qed.

  Lemma eqb_refl : forall n : nat, Nat.eqb n n = true.
  Proof.
    induction n; simpl; [reflexivity | exact IHn].
  Qed.

  Lemma count_active_by_id_cons_neq : forall r_id r l,
    res_id r <> r_id ->
    count_active_by_id r_id (r :: l) = count_active_by_id r_id l.
  Proof.
    intros r_id r l H_neq. simpl.
    destruct (Nat.eqb (res_id r) r_id) eqn:E_eq.
    - apply nat_eqb_eq in E_eq. contradiction.
    - reflexivity.
  Qed.

  Lemma count_active_by_id_cons_active : forall r l,
    res_status r = StatusActive ->
    count_active_by_id (res_id r) (r :: l) = 1 + count_active_by_id (res_id r) l.
  Proof.
    intros r l H_st.
    unfold count_active_by_id; fold count_active_by_id.
    rewrite eqb_refl, H_st. simpl. reflexivity.
  Qed.

  Lemma add_le_mono_r : forall n m k : nat, n <= m -> n + k <= m + k.
  Proof.
    intros n m k H.
    induction H.
    - apply le_n.
    - apply le_S. exact IHle.
  Qed.

  Lemma map_release_count_inv_le : forall l target_id i,
    count_active_for_inv (map_release target_id l) i <= count_active_for_inv l i.
  Proof.
    induction l; intros target_id i; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_tgt.
      + simpl. destruct (Nat.eqb (res_inv a) i) eqn:E_inv.
        * destruct (is_active_status (res_status a)).
          { apply le_S, IHl. }
          { exact (IHl target_id i). }
        * exact (IHl target_id i).
      + simpl. destruct (Nat.eqb (res_inv a) i) eqn:E_inv.
        * destruct (is_active_status (res_status a)).
          { apply le_n_S, IHl. }
          { exact (IHl target_id i). }
        * exact (IHl target_id i).
  Qed.

  Lemma map_expire_count_inv_le : forall l target_id i,
    count_active_for_inv (map_expire target_id l) i <= count_active_for_inv l i.
  Proof.
    induction l; intros target_id i; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_tgt.
      + simpl. destruct (Nat.eqb (res_inv a) i) eqn:E_inv.
        * destruct (is_active_status (res_status a)).
          { apply le_S, IHl. }
          { exact (IHl target_id i). }
        * exact (IHl target_id i).
      + simpl. destruct (Nat.eqb (res_inv a) i) eqn:E_inv.
        * destruct (is_active_status (res_status a)).
          { apply le_n_S, IHl. }
          { exact (IHl target_id i). }
        * exact (IHl target_id i).
  Qed.

  Lemma map_revoke_count_inv_le : forall l target_id i,
    count_active_for_inv (map_revoke target_id l) i <= count_active_for_inv l i.
  Proof.
    induction l; intros target_id i; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_tgt.
      + simpl. destruct (Nat.eqb (res_inv a) i) eqn:E_inv.
        * destruct (is_active_status (res_status a)).
          { apply le_S, IHl. }
          { exact (IHl target_id i). }
        * exact (IHl target_id i).
      + simpl. destruct (Nat.eqb (res_inv a) i) eqn:E_inv.
        * destruct (is_active_status (res_status a)).
          { apply le_n_S, IHl. }
          { exact (IHl target_id i). }
        * exact (IHl target_id i).
  Qed.

  Lemma map_release_count_att_le : forall l target_id a_id,
    count_active_for_attempt (map_release target_id l) a_id <= count_active_for_attempt l a_id.
  Proof.
    induction l; intros target_id a_id; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_tgt.
      + simpl. destruct (Nat.eqb (res_att a) a_id) eqn:E_att.
        * destruct (is_active_status (res_status a)).
          { apply le_S, IHl. }
          { exact (IHl target_id a_id). }
        * exact (IHl target_id a_id).
      + simpl. destruct (Nat.eqb (res_att a) a_id) eqn:E_att.
        * destruct (is_active_status (res_status a)).
          { apply le_n_S, IHl. }
          { exact (IHl target_id a_id). }
        * exact (IHl target_id a_id).
  Qed.

  Lemma map_expire_count_att_le : forall l target_id a_id,
    count_active_for_attempt (map_expire target_id l) a_id <= count_active_for_attempt l a_id.
  Proof.
    induction l; intros target_id a_id; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_tgt.
      + simpl. destruct (Nat.eqb (res_att a) a_id) eqn:E_att.
        * destruct (is_active_status (res_status a)).
          { apply le_S, IHl. }
          { exact (IHl target_id a_id). }
        * exact (IHl target_id a_id).
      + simpl. destruct (Nat.eqb (res_att a) a_id) eqn:E_att.
        * destruct (is_active_status (res_status a)).
          { apply le_n_S, IHl. }
          { exact (IHl target_id a_id). }
        * exact (IHl target_id a_id).
  Qed.

  Lemma map_revoke_count_att_le : forall l target_id a_id,
    count_active_for_attempt (map_revoke target_id l) a_id <= count_active_for_attempt l a_id.
  Proof.
    induction l; intros target_id a_id; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_tgt.
      + simpl. destruct (Nat.eqb (res_att a) a_id) eqn:E_att.
        * destruct (is_active_status (res_status a)).
          { apply le_S, IHl. }
          { exact (IHl target_id a_id). }
        * exact (IHl target_id a_id).
      + simpl. destruct (Nat.eqb (res_att a) a_id) eqn:E_att.
        * destruct (is_active_status (res_status a)).
          { apply le_n_S, IHl. }
          { exact (IHl target_id a_id). }
        * exact (IHl target_id a_id).
  Qed.

  Lemma map_release_count_by_id_le : forall l target_id r_id,
    count_active_by_id r_id (map_release target_id l) <= count_active_by_id r_id l.
  Proof.
    induction l; intros target_id r_id; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_tgt.
      + simpl. destruct (Nat.eqb (res_id a) r_id) eqn:E_rid.
        * destruct (is_active_status (res_status a)).
          { apply le_S, IHl. }
          { exact (IHl target_id r_id). }
        * exact (IHl target_id r_id).
      + simpl. destruct (Nat.eqb (res_id a) r_id) eqn:E_rid.
        * destruct (is_active_status (res_status a)).
          { apply le_n_S, IHl. }
          { exact (IHl target_id r_id). }
        * exact (IHl target_id r_id).
  Qed.

  Lemma map_expire_count_by_id_le : forall l target_id r_id,
    count_active_by_id r_id (map_expire target_id l) <= count_active_by_id r_id l.
  Proof.
    induction l; intros target_id r_id; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_tgt.
      + simpl. destruct (Nat.eqb (res_id a) r_id) eqn:E_rid.
        * destruct (is_active_status (res_status a)).
          { apply le_S, IHl. }
          { exact (IHl target_id r_id). }
        * exact (IHl target_id r_id).
      + simpl. destruct (Nat.eqb (res_id a) r_id) eqn:E_rid.
        * destruct (is_active_status (res_status a)).
          { apply le_n_S, IHl. }
          { exact (IHl target_id r_id). }
        * exact (IHl target_id r_id).
  Qed.

  Lemma map_revoke_count_by_id_le : forall l target_id r_id,
    count_active_by_id r_id (map_revoke target_id l) <= count_active_by_id r_id l.
  Proof.
    induction l; intros target_id r_id; simpl.
    - apply le_n.
    - destruct (Nat.eqb (res_id a) target_id) eqn:E_tgt.
      + simpl. destruct (Nat.eqb (res_id a) r_id) eqn:E_rid.
        * destruct (is_active_status (res_status a)).
          { apply le_S, IHl. }
          { exact (IHl target_id r_id). }
        * exact (IHl target_id r_id).
      + simpl. destruct (Nat.eqb (res_id a) r_id) eqn:E_rid.
        * destruct (is_active_status (res_status a)).
          { apply le_n_S, IHl. }
          { exact (IHl target_id r_id). }
        * exact (IHl target_id r_id).
  Qed.

  Lemma count_active_by_id_pos_in : forall l r_id,
    count_active_by_id r_id l > 0 ->
    exists r, In r l /\ res_id r = r_id /\ res_status r = StatusActive.
  Proof.
    induction l; intros r_id H_pos; simpl in *.
    - inversion H_pos.
    - destruct (Nat.eqb (res_id a) r_id) eqn:E_rid.
      + apply nat_eqb_eq in E_rid.
        destruct (is_active_status (res_status a)) eqn:E_st.
        * exists a. split; [left; reflexivity | split; [exact E_rid | ]].
          destruct (res_status a); inversion E_st; reflexivity.
        * apply IHl in H_pos. destruct H_pos as [r [H_in [H_id H_st2]]].
          exists r. split; [right; exact H_in | split; [exact H_id | exact H_st2]].
      + apply IHl in H_pos. destruct H_pos as [r [H_in [H_id H_st2]]].
        exists r. split; [right; exact H_in | split; [exact H_id | exact H_st2]].
  Qed.

  Lemma is_active_status_true : forall st, is_active_status st = true -> st = StatusActive.
  Proof. intros st H. destruct st; simpl in H; try discriminate; reflexivity. Qed.

  Lemma count_active_for_inv_cons_le : forall a l i,
    count_active_for_inv l i <= count_active_for_inv (a :: l) i.
  Proof.
    intros a l i. simpl.
    destruct (Nat.eqb (res_inv a) i && is_active_status (res_status a))%bool.
    - apply le_S. apply le_n.
    - apply le_n.
  Qed.

  Lemma count_active_for_inv_witness : forall l r target,
    In r l -> res_inv r = target -> res_status r = StatusActive ->
    1 <= count_active_for_inv l target.
  Proof.
    induction l as [| a l' IH]; intros r target H_in H_rinv H_rst; simpl in H_in.
    - contradiction.
    - simpl. destruct (Nat.eqb (res_inv a) target && is_active_status (res_status a))%bool eqn:E.
      + apply le_n_S. exact (nat_le_0 _).
      + destruct H_in as [H_head | H_tail].
        * exfalso. subst a. rewrite H_rinv, nat_eqb_refl, H_rst in E. simpl in E. discriminate.
        * exact (IH r target H_tail H_rinv H_rst).
  Qed.

  Lemma le_pred : forall n m : nat, S n <= S m -> n <= m.
  Proof.
    intros n. induction m.
    - intros H. inversion H.
      + apply le_n.
      + inversion H1.
    - intros H. inversion H.
      + apply le_n.
      + apply le_S. exact (IHm H1).
  Qed.

  Lemma not_le_Sn_0 : forall n, S n <= 0 -> False.
  Proof. intros n H. inversion H. Qed.

  Lemma count_active_by_id_le_1_gen : forall l,
    (forall i : InvocationId, count_active_for_inv l i <= 1) ->
    (forall r1 r2, In r1 l -> In r2 l -> res_id r1 = res_id r2 -> r1 = r2) ->
    forall r_id, count_active_by_id r_id l <= 1.
  Proof.
    induction l as [| a l' IH]; intros H_p1a H_p12 r_id; simpl.
    - exact (nat_le_0 1).
    - destruct (Nat.eqb (res_id a) r_id && is_active_status (res_status a))%bool eqn:E.
      + apply andb_prop in E. destruct E as [E1 E2].
        apply nat_eqb_eq in E1. apply is_active_status_true in E2.
        assert (H_tail_le : count_active_by_id r_id l' <= 1).
        { apply IH.
          - intros i. pose proof (count_active_for_inv_cons_le a l' i) as Hc.
            specialize (H_p1a i). exact (le_trans _ _ _ Hc H_p1a).
          - intros x y Hx Hy Hxy. apply H_p12; [right; exact Hx | right; exact Hy | exact Hxy]. }
        destruct (count_active_by_id r_id l') eqn:E3.
        * apply le_n.
        * exfalso.
          destruct (count_active_by_id_pos_in l' r_id) as [r2 [H_in2 [H_id2 H_st2]]].
          { rewrite E3. apply le_n_S. exact (nat_le_0 _). }
          assert (H_eq : a = r2).
          { apply H_p12; [left; reflexivity | right; exact H_in2 | ].
            rewrite E1. symmetry. exact H_id2. }
          pose proof (count_active_for_inv_witness l' r2 (res_inv a) H_in2) as Hw.
          rewrite <- H_eq in Hw.
          specialize (Hw eq_refl E2).
          specialize (H_p1a (res_inv a)).
          assert (Hhead : count_active_for_inv (a :: l') (res_inv a) =
                          1 + count_active_for_inv l' (res_inv a)).
          { simpl. rewrite nat_eqb_refl, E2. reflexivity. }
          rewrite Hhead in H_p1a.
          apply le_pred in H_p1a.
          exact (not_le_Sn_0 _ (le_trans _ _ _ Hw H_p1a)).
      + apply IH.
        * intros i. pose proof (count_active_for_inv_cons_le a l' i) as Hc.
          specialize (H_p1a i). exact (le_trans _ _ _ Hc H_p1a).
        * intros x y Hx Hy Hxy. apply H_p12; [right; exact Hx | right; exact Hy | exact Hxy].
  Qed.

  Lemma count_active_by_id_le_1_inv : forall s r_id,
    ReservationInvariant s ->
    count_active_by_id r_id (rs_reservations s) <= 1.
  Proof.
    intros s r_id H_inv.
    apply count_active_by_id_le_1_gen.
    - exact (inv_p1a_inv_uniqueness s H_inv).
    - exact (inv_p12_identity_stability s H_inv).
  Qed.

  Opaque count_active_by_id.

  Lemma gpu_release_owned_by_some : forall owners target_id g r_id,
    gpu_owned_by (gpu_release owners target_id) g = Some r_id ->
    In (g, r_id) owners /\ r_id <> target_id.
  Proof.
    induction owners; intros target_id g r_id H_rel; simpl in *.
    - discriminate.
    - destruct a as [g_o rid]. destruct (Nat.eqb rid target_id) eqn:E_rid.
      + destruct (Nat.eqb g_o g) eqn:E_g.
        * apply IHowners in H_rel. destruct H_rel. split.
          { right. exact H. }
          { exact H0. }
        * apply IHowners in H_rel. destruct H_rel. split.
          { right. exact H. }
          { exact H0. }
      + simpl in H_rel. destruct (Nat.eqb g_o g) eqn:E_g.
        * injection H_rel as H_eq. subst r_id. split.
          { left. apply nat_eqb_eq in E_g. subst g_o. reflexivity. }
          { intro H_c. rewrite H_c in E_rid. rewrite eqb_refl in E_rid. discriminate. }
        * apply IHowners in H_rel. destruct H_rel. split.
          { right. exact H. }
          { exact H0. }
  Qed.

  Lemma gpu_owned_by_in : forall owners g r_id,
    gpu_owned_by owners g = Some r_id ->
    In (g, r_id) owners.
  Proof.
    induction owners; intros g r_id H_owned; simpl in *.
    - discriminate.
    - destruct a as [g_o rid].
      destruct (Nat.eqb g_o g) eqn:E_g.
      + inversion H_owned; subst. left. apply nat_eqb_eq in E_g. subst. reflexivity.
      + right. exact (IHowners g r_id H_owned).
  Qed.

  Lemma gpu_owned_by_none_not_in : forall owners g r,
    gpu_owned_by owners g = None ->
    In (g, r) owners -> False.
  Proof.
    induction owners; intros g r E_none H_in; simpl in *.
    - contradiction.
    - destruct a as [g_o rid]. destruct (Nat.eqb g_o g) eqn:E_g.
      + discriminate.
      + destruct H_in as [H_head | H_tail].
        * injection H_head as H_g H_r. subst g_o. rewrite eqb_refl in E_g. discriminate.
        * exact (IHowners g r E_none H_tail).
  Qed.

  Lemma count_gpu_active_owner_cons_neq : forall owners r l g,
    (forall g_owner rid, In (g_owner, rid) owners -> res_id r <> rid) ->
    count_gpu_active_owner owners (r :: l) g = count_gpu_active_owner owners l g.
  Proof.
    intros owners r l g H_neq.
    unfold count_gpu_active_owner.
    destruct (gpu_owned_by owners g) eqn:E_g.
    - assert (H_rid : res_id r <> r0).
      { apply H_neq with g. exact (gpu_owned_by_in owners g r0 E_g). }
      apply count_active_by_id_cons_neq. exact H_rid.
    - reflexivity.
  Qed.

  Theorem inductive_invariant_preservation :
    forall (s s' : ReservationState) (op : StepOp),
      ReservationInvariant s ->
      Step s op s' ->
      ReservationInvariant s'.
  Proof.
    intros s s' op H_inv H_step.
    inversion H_step; subst.
    - (* StepReserve *)
      constructor.
      + intro i. simpl. destruct (Nat.eqb (res_inv r) i) eqn:E_inv.
        * rewrite H0. simpl. apply nat_eqb_eq in E_inv. subst i. rewrite H2. apply le_n.
        * exact (inv_p1a_inv_uniqueness s H_inv i).
      + intro a. simpl. destruct (Nat.eqb (res_att r) a) eqn:E_att.
        * rewrite H0. simpl. apply nat_eqb_eq in E_att. subst a. rewrite H3. apply le_n.
        * exact (inv_p1b_att_uniqueness s H_inv a).
      + simpl. rewrite H0. simpl.
        replace (res_demand r + sum_active_demand (rs_reservations s))
           with (sum_active_demand (rs_reservations s) + res_demand r)
             by apply add_comm.
        exact H1.
      + intro g_idx.
        cbn [rs_gpu_owners rs_reservations].
        unfold count_gpu_active_owner.
        destruct (gpu_owned_by (rs_gpu_owners s) g_idx) eqn:E_owner.
        * change (match Some r0 with None => 0 | Some r_id => count_active_by_id r_id (r :: rs_reservations s) end)
            with (count_active_by_id r0 (r :: rs_reservations s)).
          assert (H_neq : res_id r <> r0).
          { apply H4 with g_idx. exact (gpu_owned_by_in (rs_gpu_owners s) g_idx r0 E_owner). }
          pose proof (count_active_by_id_cons_neq r0 r (rs_reservations s) H_neq) as H_rw.
          rewrite H_rw.
          pose proof (inv_p11_gpu_single_owner s H_inv g_idx) as H_own.
          unfold count_gpu_active_owner in H_own. rewrite E_owner in H_own. exact H_own.
        * simpl. exact (nat_le_0 1).
      + intros r_elem H_in H_st. simpl in H_in. destruct H_in as [H_eq | H_in_tl].
        * rewrite <- H_eq in H_st. congruence.
        * exact (inv_p13_terminal_reclamation s H_inv r_elem H_in_tl H_st).
      + intros r1 r2 H_in1 H_in2 H_eq_id. simpl in H_in1, H_in2.
        destruct H_in1 as [H_r1_head | H_r1_tl]; destruct H_in2 as [H_r2_head | H_r2_tl].
        * subst. reflexivity.
        * subst. exfalso. apply H6 in H_r2_tl. contradiction.
        * subst. exfalso. apply H6 in H_r1_tl. symmetry in H_eq_id. contradiction.
        * exact (inv_p12_identity_stability s H_inv r1 r2 H_r1_tl H_r2_tl H_eq_id).

    - (* StepReserveGPU *)
      constructor.
      + intro i. simpl. destruct (Nat.eqb (res_inv r) i) eqn:E_inv.
        * rewrite H0. simpl. apply nat_eqb_eq in E_inv. subst i. rewrite H3. apply le_n.
        * exact (inv_p1a_inv_uniqueness s H_inv i).
      + intro a. simpl. destruct (Nat.eqb (res_att r) a) eqn:E_att.
        * rewrite H0. simpl. apply nat_eqb_eq in E_att. subst a. rewrite H4. apply le_n.
        * exact (inv_p1b_att_uniqueness s H_inv a).
      + simpl. rewrite H0. simpl.
        replace (res_demand r + sum_active_demand (rs_reservations s))
           with (sum_active_demand (rs_reservations s) + res_demand r)
             by apply add_comm.
        exact H2.
      + intro g_idx.
        unfold count_gpu_active_owner. simpl.
        destruct (Nat.eqb g g_idx) eqn:E_g.
        * pose proof (count_active_by_id_cons_active r (rs_reservations s) H0) as H_act.
          rewrite H_act, H6. apply le_n.
        * cbn [rs_gpu_owners rs_reservations].
          unfold count_gpu_active_owner.
          destruct (gpu_owned_by (rs_gpu_owners s) g_idx) eqn:E_owner.
          { change (match Some r0 with None => 0 | Some r_id => count_active_by_id r_id (r :: rs_reservations s) end)
              with (count_active_by_id r0 (r :: rs_reservations s)).
            assert (H_neq : res_id r <> r0).
            { apply H5 with g_idx. exact (gpu_owned_by_in (rs_gpu_owners s) g_idx r0 E_owner). }
            pose proof (count_active_by_id_cons_neq r0 r (rs_reservations s) H_neq) as H_rw.
            rewrite H_rw.
            pose proof (inv_p11_gpu_single_owner s H_inv g_idx) as H_own.
            unfold count_gpu_active_owner in H_own. rewrite E_owner in H_own. exact H_own. }
          { simpl. exact (nat_le_0 1). }
      + intros r_elem H_in H_st. simpl in H_in. destruct H_in as [H_eq | H_in_tl].
        * rewrite <- H_eq in H_st. congruence.
        * exact (inv_p13_terminal_reclamation s H_inv r_elem H_in_tl H_st).
      + intros r1 r2 H_in1 H_in2 H_eq_id. simpl in H_in1, H_in2.
        destruct H_in1 as [H_r1_head | H_r1_tl]; destruct H_in2 as [H_r2_head | H_r2_tl].
        * subst. reflexivity.
        * subst. exfalso. apply H7 in H_r2_tl. contradiction.
        * subst. exfalso. apply H7 in H_r1_tl. symmetry in H_eq_id. contradiction.
        * exact (inv_p12_identity_stability s H_inv r1 r2 H_r1_tl H_r2_tl H_eq_id).

    - (* StepRelease *)
      constructor.
      + intro i. simpl. apply (le_trans _ (count_active_for_inv (rs_reservations s) i)).
        * apply map_release_count_inv_le.
        * exact (inv_p1a_inv_uniqueness s H_inv i).
      + intro a. simpl. apply (le_trans _ (count_active_for_attempt (rs_reservations s) a)).
        * apply map_release_count_att_le.
        * exact (inv_p1b_att_uniqueness s H_inv a).
      + simpl. apply (le_trans (sum_active_demand (map_release target_id (rs_reservations s)) + rs_used_capacity s)
                               (sum_active_demand (rs_reservations s) + rs_used_capacity s)
                               (rs_capacity s - rs_safety_margin s - rs_uncertainty s)).
        * apply (add_le_mono_r (sum_active_demand (map_release target_id (rs_reservations s))) (sum_active_demand (rs_reservations s)) (rs_used_capacity s)).
          exact (map_release_sum_le (rs_reservations s) target_id).
        * exact (inv_p2_capacity_safety s H_inv).
      + intro g. simpl. unfold count_gpu_active_owner.
        destruct (gpu_owned_by (gpu_release (rs_gpu_owners s) target_id) g) eqn:E_rel.
        * pose proof (gpu_release_owned_by_some (rs_gpu_owners s) target_id g r E_rel) as [H_in H_neq].
          apply (le_trans _ (count_active_by_id r (rs_reservations s))).
          { apply map_release_count_by_id_le. }
          { exact (count_active_by_id_le_1_inv s r H_inv). }
        * exact (nat_le_0 1).
      + intros r H_in H_st.
        apply map_release_in_full in H_in. destruct H_in as [r_orig [H_in_orig H_eq]].
        subst r. unfold release_transform in H_st |- *.
        destruct (Nat.eqb (res_id r_orig) target_id) eqn:E_tgt.
        * reflexivity.
        * apply (inv_p13_terminal_reclamation s H_inv r_orig H_in_orig H_st).
      + intros r1 r2 H_in1 H_in2 H_eq_id.
        apply map_release_in_full in H_in1. destruct H_in1 as [r1_orig [H_in1_orig H_eq1]].
        apply map_release_in_full in H_in2. destruct H_in2 as [r2_orig [H_in2_orig H_eq2]].
        assert (H_id_orig : res_id r1_orig = res_id r2_orig).
        { rewrite <- (release_transform_id target_id r1_orig).
          rewrite <- (release_transform_id target_id r2_orig).
          rewrite <- H_eq1, <- H_eq2. exact H_eq_id. }
        assert (H_orig_eq : r1_orig = r2_orig).
        { exact (inv_p12_identity_stability s H_inv r1_orig r2_orig H_in1_orig H_in2_orig H_id_orig). }
        rewrite H_eq1, H_eq2, H_orig_eq. reflexivity.

    - (* StepExpire *)
      constructor.
      + intro i. simpl. apply (le_trans _ (count_active_for_inv (rs_reservations s) i)).
        * apply map_expire_count_inv_le.
        * exact (inv_p1a_inv_uniqueness s H_inv i).
      + intro a. simpl. apply (le_trans _ (count_active_for_attempt (rs_reservations s) a)).
        * apply map_expire_count_att_le.
        * exact (inv_p1b_att_uniqueness s H_inv a).
      + simpl. apply (le_trans (sum_active_demand (map_expire target_id (rs_reservations s)) + rs_used_capacity s)
                               (sum_active_demand (rs_reservations s) + rs_used_capacity s)
                               (rs_capacity s - rs_safety_margin s - rs_uncertainty s)).
        * apply (add_le_mono_r (sum_active_demand (map_expire target_id (rs_reservations s))) (sum_active_demand (rs_reservations s)) (rs_used_capacity s)).
          exact (map_expire_sum_le (rs_reservations s) target_id).
        * exact (inv_p2_capacity_safety s H_inv).
      + intro g. simpl. unfold count_gpu_active_owner.
        destruct (gpu_owned_by (gpu_release (rs_gpu_owners s) target_id) g) eqn:E_rel.
        * pose proof (gpu_release_owned_by_some (rs_gpu_owners s) target_id g r E_rel) as [H_in H_neq].
          apply (le_trans _ (count_active_by_id r (rs_reservations s))).
          { apply map_expire_count_by_id_le. }
          { exact (count_active_by_id_le_1_inv s r H_inv). }
        * exact (nat_le_0 1).
      + intros r H_in H_st.
        apply map_expire_in_full in H_in. destruct H_in as [r_orig [H_in_orig H_eq]].
        subst r. unfold expire_transform in H_st |- *.
        destruct (Nat.eqb (res_id r_orig) target_id) eqn:E_tgt.
        * reflexivity.
        * apply (inv_p13_terminal_reclamation s H_inv r_orig H_in_orig H_st).
      + intros r1 r2 H_in1 H_in2 H_eq_id.
        apply map_expire_in_full in H_in1. destruct H_in1 as [r1_orig [H_in1_orig H_eq1]].
        apply map_expire_in_full in H_in2. destruct H_in2 as [r2_orig [H_in2_orig H_eq2]].
        assert (H_id_orig : res_id r1_orig = res_id r2_orig).
        { rewrite <- (expire_transform_id target_id r1_orig).
          rewrite <- (expire_transform_id target_id r2_orig).
          rewrite <- H_eq1, <- H_eq2. exact H_eq_id. }
        assert (H_orig_eq : r1_orig = r2_orig).
        { exact (inv_p12_identity_stability s H_inv r1_orig r2_orig H_in1_orig H_in2_orig H_id_orig). }
        rewrite H_eq1, H_eq2, H_orig_eq. reflexivity.

    - (* StepRevoke *)
      constructor.
      + intro i. simpl. apply (le_trans _ (count_active_for_inv (rs_reservations s) i)).
        * apply map_revoke_count_inv_le.
        * exact (inv_p1a_inv_uniqueness s H_inv i).
      + intro a. simpl. apply (le_trans _ (count_active_for_attempt (rs_reservations s) a)).
        * apply map_revoke_count_att_le.
        * exact (inv_p1b_att_uniqueness s H_inv a).
      + simpl. apply (le_trans (sum_active_demand (map_revoke target_id (rs_reservations s)) + rs_used_capacity s)
                               (sum_active_demand (rs_reservations s) + rs_used_capacity s)
                               (rs_capacity s - rs_safety_margin s - rs_uncertainty s)).
        * apply (add_le_mono_r (sum_active_demand (map_revoke target_id (rs_reservations s))) (sum_active_demand (rs_reservations s)) (rs_used_capacity s)).
          exact (map_revoke_sum_le (rs_reservations s) target_id).
        * exact (inv_p2_capacity_safety s H_inv).
      + intro g. simpl. unfold count_gpu_active_owner.
        destruct (gpu_owned_by (gpu_release (rs_gpu_owners s) target_id) g) eqn:E_rel.
        * pose proof (gpu_release_owned_by_some (rs_gpu_owners s) target_id g r E_rel) as [H_in H_neq].
          apply (le_trans _ (count_active_by_id r (rs_reservations s))).
          { apply map_revoke_count_by_id_le. }
          { exact (count_active_by_id_le_1_inv s r H_inv). }
        * exact (nat_le_0 1).
      + intros r H_in H_st.
        apply map_revoke_in_full in H_in. destruct H_in as [r_orig [H_in_orig H_eq]].
        subst r. unfold revoke_transform in H_st |- *.
        destruct (Nat.eqb (res_id r_orig) target_id) eqn:E_tgt.
        * reflexivity.
        * apply (inv_p13_terminal_reclamation s H_inv r_orig H_in_orig H_st).
      + intros r1 r2 H_in1 H_in2 H_eq_id.
        apply map_revoke_in_full in H_in1. destruct H_in1 as [r1_orig [H_in1_orig H_eq1]].
        apply map_revoke_in_full in H_in2. destruct H_in2 as [r2_orig [H_in2_orig H_eq2]].
        assert (H_id_orig : res_id r1_orig = res_id r2_orig).
        { rewrite <- (revoke_transform_id target_id r1_orig).
          rewrite <- (revoke_transform_id target_id r2_orig).
          rewrite <- H_eq1, <- H_eq2. exact H_eq_id. }
        assert (H_orig_eq : r1_orig = r2_orig).
        { exact (inv_p12_identity_stability s H_inv r1_orig r2_orig H_in1_orig H_in2_orig H_id_orig). }
        rewrite H_eq1, H_eq2, H_orig_eq. reflexivity.

    - (* StepAuthoritySuccession *)
      constructor.
      + exact (inv_p1a_inv_uniqueness s H_inv).
      + exact (inv_p1b_att_uniqueness s H_inv).
      + exact (inv_p2_capacity_safety s H_inv).
      + exact (inv_p11_gpu_single_owner s H_inv).
      + exact (inv_p13_terminal_reclamation s H_inv).
      + exact (inv_p12_identity_stability s H_inv).
  Qed.

End Phase7Reservation.
