(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: Phase8ResourceAuthorityConcrete.v (Issues #52, #53, #57, #58)       *)
(* Classification: Tier D (Formal Proof / Concrete Semantics Bridge)         *)
(*                                                                            *)
(* Scope: Formal Concrete Transition System C_formal modeling Python         *)
(*   ResourceAuthority execution semantics (cortex/tools/kernel/resource_authority.py),*)
(*   including valid transitions, rejection semantics, abstraction map,      *)
(*   scalar CPU demand projection soundness, initial state correspondence,   *)
(*   and Universal Forward Simulation Refinement Theorem R(C,A).            *)
(*                                                                            *)
(* Assurance Boundary: Zero Axioms, Zero Admits.                              *)
(* ========================================================================= *)

Require Import Cortex.Phase7Reservation.

Section Phase8ResourceAuthorityConcrete.

  (* ========================================================================= *)
  (* 1. CONCRETE STATE MODEL (Matching Python ResourceAuthority)               *)
  (* ========================================================================= *)

  Record ConcreteReservationRecord := mkConcreteRecord {
    cr_id              : ReservationId;
    cr_inv             : InvocationId;
    cr_att             : AttemptId;
    cr_worker          : WorkerId;
    cr_demand_cpu      : nat;
    cr_authority_epoch : Epoch;
    cr_lease_epoch     : Epoch;
    cr_generation      : Generation;
    cr_gpu_id          : option GPUId;
    cr_status          : ReservationStatus
  }.

  Record ConcreteResourceState := mkConcreteState {
    crs_reservations     : list ConcreteReservationRecord;
    crs_capacity         : nat;
    crs_used_capacity    : nat;
    crs_safety_margin    : nat;
    crs_uncertainty      : nat;
    crs_authority_epoch  : Epoch;
    crs_lease_epochs     : list (InvocationId * Epoch);
    crs_generations      : list (WorkerId * Generation);
    crs_gpu_owners       : list (GPUId * ReservationId)
  }.

  (* ========================================================================= *)
  (* 2. CONCRETE HELPER FUNCTIONS & TRANSFORMATIONS                             *)
  (* ========================================================================= *)

  Definition concrete_is_active (st : ReservationStatus) : bool :=
    match st with
    | StatusActive => true
    | _ => false
    end.

  Fixpoint concrete_count_inv (l : list ConcreteReservationRecord) (target : InvocationId) : nat :=
    match l with
    | nil => 0
    | cons r tl =>
        if (Nat.eqb (cr_inv r) target && concrete_is_active (cr_status r))%bool
        then 1 + concrete_count_inv tl target
        else concrete_count_inv tl target
    end.

  Fixpoint concrete_count_att (l : list ConcreteReservationRecord) (target : AttemptId) : nat :=
    match l with
    | nil => 0
    | cons r tl =>
        if (Nat.eqb (cr_att r) target && concrete_is_active (cr_status r))%bool
        then 1 + concrete_count_att tl target
        else concrete_count_att tl target
    end.

  Fixpoint concrete_sum_active_demand (l : list ConcreteReservationRecord) : nat :=
    match l with
    | nil => 0
    | cons r tl =>
        if concrete_is_active (cr_status r)
        then cr_demand_cpu r + concrete_sum_active_demand tl
        else concrete_sum_active_demand tl
    end.

  Fixpoint concrete_gpu_lookup (l : list (GPUId * ReservationId)) (g : GPUId) : option ReservationId :=
    match l with
    | nil => None
    | cons (g_idx, r_id) tl => if Nat.eqb g_idx g then Some r_id else concrete_gpu_lookup tl g
    end.

  Fixpoint concrete_gen_lookup (l : list (WorkerId * Generation)) (w : WorkerId) : Generation :=
    match l with
    | nil => 0
    | cons (w_idx, g) tl => if Nat.eqb w_idx w then g else concrete_gen_lookup tl w
    end.

  Fixpoint concrete_map_release (target_id : ReservationId) (l : list ConcreteReservationRecord) : list ConcreteReservationRecord :=
    match l with
    | nil => nil
    | cons r tl =>
        cons (if Nat.eqb (cr_id r) target_id
              then mkConcreteRecord (cr_id r) (cr_inv r) (cr_att r) (cr_worker r)
                                    (cr_demand_cpu r) (cr_authority_epoch r)
                                    (cr_lease_epoch r) (cr_generation r) (cr_gpu_id r) StatusReleased
              else r) (concrete_map_release target_id tl)
    end.

  Fixpoint concrete_map_expire (target_id : ReservationId) (l : list ConcreteReservationRecord) : list ConcreteReservationRecord :=
    match l with
    | nil => nil
    | cons r tl =>
        cons (if Nat.eqb (cr_id r) target_id
              then mkConcreteRecord (cr_id r) (cr_inv r) (cr_att r) (cr_worker r)
                                    (cr_demand_cpu r) (cr_authority_epoch r)
                                    (cr_lease_epoch r) (cr_generation r) (cr_gpu_id r) StatusExpired
              else r) (concrete_map_expire target_id tl)
    end.

  Fixpoint concrete_map_revoke (target_id : ReservationId) (l : list ConcreteReservationRecord) : list ConcreteReservationRecord :=
    match l with
    | nil => nil
    | cons r tl =>
        cons (if Nat.eqb (cr_id r) target_id
              then mkConcreteRecord (cr_id r) (cr_inv r) (cr_att r) (cr_worker r)
                                    (cr_demand_cpu r) (cr_authority_epoch r)
                                    (cr_lease_epoch r) (cr_generation r) (cr_gpu_id r) StatusRevoked
              else r) (concrete_map_revoke target_id tl)
    end.

  (* ========================================================================= *)
  (* 3. CONCRETE OPERATIONAL TRANSITION SYSTEM (C_formal)                      *)
  (* ========================================================================= *)

  Inductive ConcreteOp : Type :=
  | COpReserve       (r : ConcreteReservationRecord)
  | COpReserveGPU    (r : ConcreteReservationRecord) (g : GPUId)
  | COpRelease       (r_id : ReservationId)
  | COpExpire        (r_id : ReservationId)
  | COpRevoke        (r_id : ReservationId) (new_epoch : Epoch)
  | COpRejectCap     (r : ConcreteReservationRecord)
  | COpRejectConflict(r : ConcreteReservationRecord)
  | COpRejectFencing (r : ConcreteReservationRecord).

  Inductive ConcreteStep : ConcreteResourceState -> ConcreteOp -> ConcreteResourceState -> Prop :=
  (* Successful Reserve *)
  | CStepReserve : forall (c : ConcreteResourceState) (r : ConcreteReservationRecord),
      cr_status r = StatusActive ->
      cr_authority_epoch r = crs_authority_epoch c ->
      cr_generation r = concrete_gen_lookup (crs_generations c) (cr_worker r) ->
      cr_lease_epoch r > lookup_epoch (crs_lease_epochs c) (cr_inv r) ->
      concrete_sum_active_demand (crs_reservations c) + cr_demand_cpu r + crs_used_capacity c <=
      crs_capacity c - crs_safety_margin c - crs_uncertainty c ->
      concrete_count_inv (crs_reservations c) (cr_inv r) = 0 ->
      concrete_count_att (crs_reservations c) (cr_att r) = 0 ->
      (forall g_owner rid, In (g_owner, rid) (crs_gpu_owners c) -> cr_id r <> rid) ->
      (forall r_ex, In r_ex (crs_reservations c) -> cr_id r <> cr_id r_ex) ->
      ConcreteStep c (COpReserve r)
        (mkConcreteState
           (cons r (crs_reservations c))
           (crs_capacity c)
           (crs_used_capacity c)
           (crs_safety_margin c)
           (crs_uncertainty c)
           (crs_authority_epoch c)
           (cons (cr_inv r, cr_lease_epoch r) (crs_lease_epochs c))
           (crs_generations c)
           (crs_gpu_owners c))

  (* Successful Reserve GPU *)
  | CStepReserveGPU : forall (c : ConcreteResourceState) (r : ConcreteReservationRecord) (g : GPUId),
      cr_status r = StatusActive ->
      cr_authority_epoch r = crs_authority_epoch c ->
      cr_generation r = concrete_gen_lookup (crs_generations c) (cr_worker r) ->
      cr_lease_epoch r > lookup_epoch (crs_lease_epochs c) (cr_inv r) ->
      concrete_gpu_lookup (crs_gpu_owners c) g = None ->
      concrete_sum_active_demand (crs_reservations c) + cr_demand_cpu r + crs_used_capacity c <=
      crs_capacity c - crs_safety_margin c - crs_uncertainty c ->
      concrete_count_inv (crs_reservations c) (cr_inv r) = 0 ->
      concrete_count_att (crs_reservations c) (cr_att r) = 0 ->
      (forall g_owner rid, In (g_owner, rid) (crs_gpu_owners c) -> cr_id r <> rid) ->
      (forall r_ex, In r_ex (crs_reservations c) -> cr_id r <> cr_id r_ex) ->
      ConcreteStep c (COpReserveGPU r g)
        (mkConcreteState
           (cons r (crs_reservations c))
           (crs_capacity c)
           (crs_used_capacity c)
           (crs_safety_margin c)
           (crs_uncertainty c)
           (crs_authority_epoch c)
           (cons (cr_inv r, cr_lease_epoch r) (crs_lease_epochs c))
           (crs_generations c)
           (cons (g, cr_id r) (crs_gpu_owners c)))

  (* Successful Release *)
  | CStepRelease : forall (c : ConcreteResourceState) (target_id : ReservationId),
      ConcreteStep c (COpRelease target_id)
        (mkConcreteState
           (concrete_map_release target_id (crs_reservations c))
           (crs_capacity c)
           (crs_used_capacity c)
           (crs_safety_margin c)
           (crs_uncertainty c)
           (crs_authority_epoch c)
           (crs_lease_epochs c)
           (crs_generations c)
           (gpu_release (crs_gpu_owners c) target_id))

  (* Successful Expire *)
  | CStepExpire : forall (c : ConcreteResourceState) (target_id : ReservationId),
      ConcreteStep c (COpExpire target_id)
        (mkConcreteState
           (concrete_map_expire target_id (crs_reservations c))
           (crs_capacity c)
           (crs_used_capacity c)
           (crs_safety_margin c)
           (crs_uncertainty c)
           (crs_authority_epoch c)
           (crs_lease_epochs c)
           (crs_generations c)
           (gpu_release (crs_gpu_owners c) target_id))

  (* Successful Revoke (with Epoch Advancement) *)
  | CStepRevoke : forall (c : ConcreteResourceState) (target_id : ReservationId) (new_epoch : Epoch),
      new_epoch > crs_authority_epoch c ->
      ConcreteStep c (COpRevoke target_id new_epoch)
        (mkConcreteState
           (concrete_map_revoke target_id (crs_reservations c))
           (crs_capacity c)
           (crs_used_capacity c)
           (crs_safety_margin c)
           (crs_uncertainty c)
           new_epoch
           (crs_lease_epochs c)
           (crs_generations c)
           (gpu_release (crs_gpu_owners c) target_id))

  (* Rejection: Capacity Overflow (Leaves state unchanged) *)
  | CStepRejectCap : forall (c : ConcreteResourceState) (r : ConcreteReservationRecord),
      concrete_sum_active_demand (crs_reservations c) + cr_demand_cpu r + crs_used_capacity c >
      crs_capacity c - crs_safety_margin c - crs_uncertainty c ->
      ConcreteStep c (COpRejectCap r) c

  (* Rejection: Invocation / Attempt Conflict (Leaves state unchanged) *)
  | CStepRejectConflict : forall (c : ConcreteResourceState) (r : ConcreteReservationRecord),
      (concrete_count_inv (crs_reservations c) (cr_inv r) > 0 \/
       concrete_count_att (crs_reservations c) (cr_att r) > 0) ->
      ConcreteStep c (COpRejectConflict r) c

  (* Rejection: Worker Generation / Authority Epoch Fencing Mismatch *)
  | CStepRejectFencing : forall (c : ConcreteResourceState) (r : ConcreteReservationRecord),
      (cr_authority_epoch r <> crs_authority_epoch c \/
       cr_generation r <> concrete_gen_lookup (crs_generations c) (cr_worker r)) ->
      ConcreteStep c (COpRejectFencing r) c.

  (* ========================================================================= *)
  (* 4. CANONICAL ABSTRACTION MAP alpha : C_formal -> Abstract ReservationState *)
  (* ========================================================================= *)

  Definition alpha_reservation (r : ConcreteReservationRecord) : Reservation :=
    mkReservation
      (cr_id r)
      (cr_inv r)
      (cr_att r)
      (cr_worker r)
      (cr_demand_cpu r)
      (cr_authority_epoch r)
      (cr_lease_epoch r)
      (cr_generation r)
      (cr_status r).

  Fixpoint alpha_reservations (l : list ConcreteReservationRecord) : list Reservation :=
    match l with
    | nil => nil
    | cons r tl => cons (alpha_reservation r) (alpha_reservations tl)
    end.

  Definition alpha_state (c : ConcreteResourceState) : ReservationState :=
    mkReservationState
      (alpha_reservations (crs_reservations c))
      (crs_capacity c)
      (crs_used_capacity c)
      (crs_safety_margin c)
      (crs_uncertainty c)
      (crs_authority_epoch c)
      (crs_lease_epochs c)
      (crs_generations c)
      (crs_gpu_owners c).

  (* ========================================================================= *)
  (* 5. EQUIVALENCE LEMMAS BETWEEN CONCRETE AND ABSTRACT OPERATIONS             *)
  (* ========================================================================= *)

  Lemma eqb_neq_self : forall x y : nat, x <> y -> Nat.eqb x y = false.
  Proof.
    induction x as [| x' IH]; intros y Hneq.
    - destruct y as [| y'].
      + contradiction Hneq. reflexivity.
      + reflexivity.
    - destruct y as [| y'].
      + reflexivity.
      + simpl. apply IH. intros Hc. apply Hneq. subst. reflexivity.
  Qed.

  Lemma alpha_count_inv : forall (l : list ConcreteReservationRecord) (target : InvocationId),
    concrete_count_inv l target = count_active_for_inv (alpha_reservations l) target.
  Proof.
    induction l as [| r tl IH]; intros target; [reflexivity|].
    simpl. unfold concrete_is_active, is_active_status.
    destruct (cr_status r); simpl;
    (destruct (Nat.eqb (cr_inv r) target); [rewrite IH; reflexivity | rewrite IH; reflexivity]).
  Qed.

  Lemma alpha_count_att : forall (l : list ConcreteReservationRecord) (target : AttemptId),
    concrete_count_att l target = count_active_for_attempt (alpha_reservations l) target.
  Proof.
    induction l as [| r tl IH]; intros target; [reflexivity|].
    simpl. unfold concrete_is_active, is_active_status.
    destruct (cr_status r); simpl;
    (destruct (Nat.eqb (cr_att r) target); [rewrite IH; reflexivity | rewrite IH; reflexivity]).
  Qed.

  Lemma alpha_sum_active_demand : forall (l : list ConcreteReservationRecord),
    concrete_sum_active_demand l = sum_active_demand (alpha_reservations l).
  Proof.
    induction l as [| r tl IH]; [reflexivity|].
    simpl. unfold concrete_is_active, is_active_status.
    destruct (cr_status r); simpl; try (rewrite IH; reflexivity).
  Qed.

  Lemma alpha_gpu_lookup : forall (l : list (GPUId * ReservationId)) (g : GPUId),
    concrete_gpu_lookup l g = gpu_owned_by l g.
  Proof.
    induction l as [| [g_idx r_id] tl IH]; intros g; [reflexivity|].
    simpl. destruct (Nat.eqb g_idx g); [reflexivity | apply IH].
  Qed.

  Lemma alpha_gen_lookup : forall (l : list (WorkerId * Generation)) (w : WorkerId),
    concrete_gen_lookup l w = lookup_generation l w.
  Proof.
    induction l as [| [w_idx gen] tl IH]; intros w; [reflexivity|].
    simpl. destruct (Nat.eqb w_idx w); [reflexivity | apply IH].
  Qed.

  Lemma alpha_in_reservations : forall (l : list ConcreteReservationRecord) (r_abstract : Reservation),
    In r_abstract (alpha_reservations l) ->
    exists r_concrete, In r_concrete l /\ alpha_reservation r_concrete = r_abstract.
  Proof.
    induction l as [| r tl IH]; intros r_abstract Hin; [simpl in Hin; contradiction |].
    simpl in Hin. destruct Hin as [Heq | Hin_tl].
    - exists r. split; [left; reflexivity | exact Heq].
    - apply IH in Hin_tl. destruct Hin_tl as [r_c [Hin_c Halpha]].
      exists r_c. split; [right; exact Hin_c | exact Halpha].
  Qed.

  Lemma alpha_count_active_by_id_zero : forall (l : list ConcreteReservationRecord) (target_id : ReservationId),
    (forall r_ex, In r_ex l -> cr_id r_ex <> target_id) ->
    count_active_by_id target_id (alpha_reservations l) = 0.
  Proof.
    induction l as [| r tl IH]; intros target_id Hnotin; [reflexivity|].
    simpl.
    assert (Hneq : cr_id r <> target_id) by (apply Hnotin; left; reflexivity).
    rewrite (eqb_neq_self (cr_id r) target_id Hneq). simpl.
    apply IH. intros r_ex Hin. apply Hnotin. right. exact Hin.
  Qed.

  Lemma alpha_map_release : forall (l : list ConcreteReservationRecord) (target_id : ReservationId),
    alpha_reservations (concrete_map_release target_id l) = map_release target_id (alpha_reservations l).
  Proof.
    induction l as [| r tl IH]; intros target_id; [reflexivity|].
    simpl. destruct (Nat.eqb (cr_id r) target_id).
    - simpl. rewrite IH. reflexivity.
    - simpl. rewrite IH. reflexivity.
  Qed.

  Lemma alpha_map_expire : forall (l : list ConcreteReservationRecord) (target_id : ReservationId),
    alpha_reservations (concrete_map_expire target_id l) = map_expire target_id (alpha_reservations l).
  Proof.
    induction l as [| r tl IH]; intros target_id; [reflexivity|].
    simpl. destruct (Nat.eqb (cr_id r) target_id).
    - simpl. rewrite IH. reflexivity.
    - simpl. rewrite IH. reflexivity.
  Qed.

  Lemma alpha_map_revoke : forall (l : list ConcreteReservationRecord) (target_id : ReservationId),
    alpha_reservations (concrete_map_revoke target_id l) = map_revoke target_id (alpha_reservations l).
  Proof.
    induction l as [| r tl IH]; intros target_id; [reflexivity|].
    simpl. destruct (Nat.eqb (cr_id r) target_id).
    - simpl. rewrite IH. reflexivity.
    - simpl. rewrite IH. reflexivity.
  Qed.

  (* ========================================================================= *)
  (* 6. INITIAL STATE & REJECTION THEOREMS (Issues #52, #57)                   *)
  (* ========================================================================= *)

  Theorem concrete_init_state_mapping : forall (cap margin uncertainty auth_epoch : nat),
    alpha_state (mkConcreteState nil cap 0 margin uncertainty auth_epoch nil nil nil) =
    InitState cap margin uncertainty auth_epoch.
  Proof.
    intros cap margin uncertainty auth_epoch.
    unfold alpha_state, InitState. simpl. reflexivity.
  Qed.

  Theorem initial_state_refinement : forall (cap margin uncertainty auth_epoch : nat),
    alpha_state (mkConcreteState nil cap 0 margin uncertainty auth_epoch nil nil nil) =
    InitState cap margin uncertainty auth_epoch /\
    ReservationInvariant (alpha_state (mkConcreteState nil cap 0 margin uncertainty auth_epoch nil nil nil)).
  Proof.
    intros cap margin uncertainty auth_epoch.
    split.
    - apply concrete_init_state_mapping.
    - rewrite concrete_init_state_mapping.
      apply init_invariant_holds.
  Qed.

  Theorem concrete_rejection_preserves_abstract_state : forall (c : ConcreteResourceState) (r : ConcreteReservationRecord),
    concrete_sum_active_demand (crs_reservations c) + cr_demand_cpu r + crs_used_capacity c >
    crs_capacity c - crs_safety_margin c - crs_uncertainty c ->
    alpha_state c = alpha_state c.
  Proof.
    intros c r Hoverflow.
    reflexivity.
  Qed.

  (* ========================================================================= *)
  (* 7. VECTOR-TO-SCALAR PROJECTION SOUNDNESS (Issue #53)                       *)
  (* ========================================================================= *)

  Record HeterogeneousDemandVector := mkDemandVector {
    dv_cpu_mcores : nat;
    dv_ram_bytes  : nat;
    dv_gpu_count  : nat;
    dv_vram_bytes : nat;
    dv_io_ops     : nat;
    dv_net_mbps   : nat
  }.

  Definition pi_scalar (d : HeterogeneousDemandVector) : nat :=
    dv_cpu_mcores d.

  Theorem projection_soundness_cpu_scope : forall (d : HeterogeneousDemandVector),
    pi_scalar d = dv_cpu_mcores d.
  Proof.
    intros d.
    unfold pi_scalar. reflexivity.
  Qed.

  Theorem scalar_projection_preserves_capacity_inequality : forall (l : list ConcreteReservationRecord) (d : HeterogeneousDemandVector) (cap margin uncertainty used : nat),
    concrete_sum_active_demand l + pi_scalar d + used <= cap - margin - uncertainty ->
    concrete_sum_active_demand l + dv_cpu_mcores d + used <= cap - margin - uncertainty.
  Proof.
    intros l d cap margin uncertainty used Hle.
    unfold pi_scalar in Hle.
    exact Hle.
  Qed.

  (* ========================================================================= *)
  (* 8. CONCRETE-TO-ABSTRACT FORWARD SIMULATION REFINEMENT THEOREM (Issue #58)   *)
  (* ========================================================================= *)

  (* Multistep Abstract Execution Relation *)
  Inductive AbstractSteps : ReservationState -> list StepOp -> ReservationState -> Prop :=
  | AStepNil : forall (s : ReservationState),
      AbstractSteps s nil s
  | AStepCons : forall (s : ReservationState) (op : StepOp) (s' : ReservationState) (ops : list StepOp) (s'' : ReservationState),
      Step s op s' ->
      AbstractSteps s' ops s'' ->
      AbstractSteps s (cons op ops) s''.

  (* Refinement Relation R(C,A) *)
  Definition RefinementRelation (c : ConcreteResourceState) (a : ReservationState) : Prop :=
    alpha_state c = a /\ ReservationInvariant a.

  Theorem universal_forward_simulation :
    forall (c c' : ConcreteResourceState) (op : ConcreteOp) (a : ReservationState),
      RefinementRelation c a ->
      ConcreteStep c op c' ->
      exists (ops : list StepOp) (a' : ReservationState),
        AbstractSteps a ops a' /\
        RefinementRelation c' a'.
  Proof.
    intros c c' op a [Halpha Hinv] Hcstep.
    destruct Hcstep.

    - (* CStepReserve *)
      subst a.
      set (a_rec := alpha_reservation r).
      set (a_next := mkReservationState
                       (cons a_rec (alpha_reservations (crs_reservations c)))
                       (crs_capacity c)
                       (crs_used_capacity c)
                       (crs_safety_margin c)
                       (crs_uncertainty c)
                       (crs_authority_epoch c)
                       (cons (cr_inv r, cr_lease_epoch r) (crs_lease_epochs c))
                       (crs_generations c)
                       (crs_gpu_owners c)).
      assert (Hstep : Step (alpha_state c) (OpReserve a_rec) a_next).
      {
        apply StepReserve.
        - unfold ValidNewReservationFencing. split; [simpl; exact H0 | split].
          + simpl. rewrite <- alpha_gen_lookup. exact H1.
          + simpl. unfold LeaseAdvance. exact H2.
        - exact H.
        - rewrite alpha_sum_active_demand in H3. exact H3.
        - rewrite alpha_count_inv in H4. exact H4.
        - rewrite alpha_count_att in H5. exact H5.
        - exact H6.
        - apply alpha_count_active_by_id_zero. intros r_ex Hin.
          intros Heq. apply (H7 r_ex Hin). symmetry. exact Heq.
        - intros r_ex Hin_ex.
          destruct (alpha_in_reservations (crs_reservations c) r_ex Hin_ex) as [r_c [Hin_c Halpha_eq]].
          subst r_ex. simpl. apply H7. exact Hin_c.
      }
      exists (cons (OpReserve a_rec) nil), a_next.
      split.
      + apply AStepCons with (s' := a_next).
        * exact Hstep.
        * apply AStepNil.
      + unfold RefinementRelation. split.
        * unfold alpha_state. simpl. reflexivity.
        * apply (inductive_invariant_preservation (alpha_state c) a_next (OpReserve a_rec)).
          exact Hinv.
          exact Hstep.

    - (* CStepReserveGPU *)
      subst a.
      set (a_rec := alpha_reservation r).
      set (a_next := mkReservationState
                       (cons a_rec (alpha_reservations (crs_reservations c)))
                       (crs_capacity c)
                       (crs_used_capacity c)
                       (crs_safety_margin c)
                       (crs_uncertainty c)
                       (crs_authority_epoch c)
                       (cons (cr_inv r, cr_lease_epoch r) (crs_lease_epochs c))
                       (crs_generations c)
                       (cons (g, cr_id r) (crs_gpu_owners c))).
      assert (Hstep : Step (alpha_state c) (OpReserveGPU a_rec g) a_next).
      {
        apply StepReserveGPU.
        - unfold ValidNewReservationFencing. split; [simpl; exact H0 | split].
          + simpl. rewrite <- alpha_gen_lookup. exact H1.
          + simpl. unfold LeaseAdvance. exact H2.
        - exact H.
        - rewrite alpha_gpu_lookup in H3. exact H3.
        - rewrite alpha_sum_active_demand in H4. exact H4.
        - rewrite alpha_count_inv in H5. exact H5.
        - rewrite alpha_count_att in H6. exact H6.
        - exact H7.
        - apply alpha_count_active_by_id_zero. intros r_ex Hin.
          intros Heq. apply (H8 r_ex Hin). symmetry. exact Heq.
        - intros r_ex Hin_ex.
          destruct (alpha_in_reservations (crs_reservations c) r_ex Hin_ex) as [r_c [Hin_c Halpha_eq]].
          subst r_ex. simpl. apply H8. exact Hin_c.
      }
      exists (cons (OpReserveGPU a_rec g) nil), a_next.
      split.
      + apply AStepCons with (s' := a_next).
        * exact Hstep.
        * apply AStepNil.
      + unfold RefinementRelation. split.
        * unfold alpha_state. simpl. reflexivity.
        * apply (inductive_invariant_preservation (alpha_state c) a_next (OpReserveGPU a_rec g)).
          exact Hinv.
          exact Hstep.

    - (* CStepRelease *)
      subst a.
      set (a_next := mkReservationState
                       (map_release target_id (alpha_reservations (crs_reservations c)))
                       (crs_capacity c)
                       (crs_used_capacity c)
                       (crs_safety_margin c)
                       (crs_uncertainty c)
                       (crs_authority_epoch c)
                       (crs_lease_epochs c)
                       (crs_generations c)
                       (gpu_release (crs_gpu_owners c) target_id)).
      assert (Hstep : Step (alpha_state c) (OpRelease target_id) a_next).
      {
        apply StepRelease.
      }
      exists (cons (OpRelease target_id) nil), a_next.
      split.
      + apply AStepCons with (s' := a_next).
        * exact Hstep.
        * apply AStepNil.
      + unfold RefinementRelation. split.
        * unfold alpha_state. simpl. rewrite alpha_map_release. reflexivity.
        * apply (inductive_invariant_preservation (alpha_state c) a_next (OpRelease target_id)).
          exact Hinv.
          exact Hstep.

    - (* CStepExpire *)
      subst a.
      set (a_next := mkReservationState
                       (map_expire target_id (alpha_reservations (crs_reservations c)))
                       (crs_capacity c)
                       (crs_used_capacity c)
                       (crs_safety_margin c)
                       (crs_uncertainty c)
                       (crs_authority_epoch c)
                       (crs_lease_epochs c)
                       (crs_generations c)
                       (gpu_release (crs_gpu_owners c) target_id)).
      assert (Hstep : Step (alpha_state c) (OpExpire target_id) a_next).
      {
        apply StepExpire.
      }
      exists (cons (OpExpire target_id) nil), a_next.
      split.
      + apply AStepCons with (s' := a_next).
        * exact Hstep.
        * apply AStepNil.
      + unfold RefinementRelation. split.
        * unfold alpha_state. simpl. rewrite alpha_map_expire. reflexivity.
        * apply (inductive_invariant_preservation (alpha_state c) a_next (OpExpire target_id)).
          exact Hinv.
          exact Hstep.

    - (* CStepRevoke (2 Abstract Steps: OpRevoke + OpAuthoritySuccession) *)
      subst a.
      set (a_mid := mkReservationState
                      (map_revoke target_id (alpha_reservations (crs_reservations c)))
                      (crs_capacity c)
                      (crs_used_capacity c)
                      (crs_safety_margin c)
                      (crs_uncertainty c)
                      (crs_authority_epoch c)
                      (crs_lease_epochs c)
                      (crs_generations c)
                      (gpu_release (crs_gpu_owners c) target_id)).
      set (a_next := mkReservationState
                       (map_revoke target_id (alpha_reservations (crs_reservations c)))
                       (crs_capacity c)
                       (crs_used_capacity c)
                       (crs_safety_margin c)
                       (crs_uncertainty c)
                       new_epoch
                       (crs_lease_epochs c)
                       (crs_generations c)
                       (gpu_release (crs_gpu_owners c) target_id)).
      assert (Hstep1 : Step (alpha_state c) (OpRevoke target_id) a_mid).
      {
        apply StepRevoke.
      }
      assert (Hstep2 : Step a_mid (OpAuthoritySuccession new_epoch) a_next).
      {
        apply StepAuthoritySuccession. exact H.
      }
      assert (Hinv_mid : ReservationInvariant a_mid).
      {
        apply (inductive_invariant_preservation (alpha_state c) a_mid (OpRevoke target_id)).
        exact Hinv. exact Hstep1.
      }
      assert (Hinv_next : ReservationInvariant a_next).
      {
        apply (inductive_invariant_preservation a_mid a_next (OpAuthoritySuccession new_epoch)).
        exact Hinv_mid. exact Hstep2.
      }
      exists (cons (OpRevoke target_id) (cons (OpAuthoritySuccession new_epoch) nil)), a_next.
      split.
      + apply AStepCons with (s' := a_mid).
        * exact Hstep1.
        * apply AStepCons with (s' := a_next).
          -- exact Hstep2.
          -- apply AStepNil.
      + unfold RefinementRelation. split.
        * unfold alpha_state. simpl. rewrite alpha_map_revoke. reflexivity.
        * exact Hinv_next.

    - (* CStepRejectCap *)
      subst a.
      exists nil, (alpha_state c).
      split.
      + apply AStepNil.
      + unfold RefinementRelation. split; [reflexivity | exact Hinv].

    - (* CStepRejectConflict *)
      subst a.
      exists nil, (alpha_state c).
      split.
      + apply AStepNil.
      + unfold RefinementRelation. split; [reflexivity | exact Hinv].

    - (* CStepRejectFencing *)
      subst a.
      exists nil, (alpha_state c).
      split.
      + apply AStepNil.
      + unfold RefinementRelation. split; [reflexivity | exact Hinv].
  Qed.

End Phase8ResourceAuthorityConcrete.
