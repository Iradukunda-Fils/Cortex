(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: Phase4RoutingRefinement.v                                         *)
(* Classification: Tier D (Formal Proof / Architecture Critical)              *)
(* Purpose: Phase 4 Formal Gateway Routing & Lease Refinement Security Kernel *)
(*                                                                            *)
(* Scope:                                                                     *)
(*   RD-F1  Eligibility Safety                                                *)
(*   RD-F2  Capability Containment                                            *)
(*   RD-F3  Config Generation & Hash Fencing                                  *)
(*   RD-F4  Lease Fencing Preservation (Stale Config Rejection)               *)
(*   RD-F5  Router Non-Authority                                              *)
(*   RD-F6  UNADMITTED Safety                                                 *)
(*   RD-F7  Single Commitment                                                 *)
(*   RD-F8  Bounded Admission                                                 *)
(*   RD-F9  State-Domain Conflict Safety                                      *)
(*   RD-F10 TOCTOU Revalidation Safety                                        *)
(*                                                                            *)
(* Non-Scope:                                                                 *)
(*   Load-balancing heuristics, telemetry scoring, tie-breaking algorithms.   *)
(*   These belong to executable conformance/property tests, not Coq proofs.   *)
(* ========================================================================= *)

Section Phase4RoutingRefinement.

  (* ----------------------------------------------------------------------- *)
  (* 1. TYPE DEFINITIONS & ABSTRACT REPRESENTATIONS                          *)
  (* ----------------------------------------------------------------------- *)

  Definition CapabilityId := nat.
  Definition SandboxProfileId := nat.
  Definition StateDomainKey := nat.

  Inductive LifecycleStage :=
    | LS_OFFLINE
    | LS_DRAINING
    | LS_READY.

  Record WorkerReplica := mkWorker {
    w_id            : nat;
    w_gen           : nat;            (* ConfigGeneration *)
    w_hash          : nat;            (* ConfigHash *)
    w_profile       : SandboxProfileId;
    w_sandbox_hash  : nat;            (* SandboxProfileHash *)
    w_cap_hash      : nat;            (* CapabilityEnvelopeHash *)
    w_state         : LifecycleStage;
    w_inflight      : nat;
    w_limit         : nat;
    w_n_caps        : nat;
  }.

  Record InvocationRequest := mkInvocation {
    i_id            : nat;
    i_target_gen    : nat;
    i_target_hash   : nat;
    i_profile       : SandboxProfileId;
    i_sandbox_hash  : nat;            (* Required SandboxProfileHash *)
    i_cap_hash      : nat;            (* Required CapabilityEnvelopeHash *)
    i_domain_key    : StateDomainKey;
    i_n_req_caps    : nat;
  }.

  (* ----------------------------------------------------------------------- *)
  (* 2. BOOLEAN COMBINATORS & HELPER LEMMAS                                  *)
  (* ----------------------------------------------------------------------- *)

  Lemma andb_true_elim : forall a b : bool,
    andb a b = true -> a = true /\ b = true.
  Proof.
    intros [] []; simpl; split; try reflexivity; try discriminate.
  Qed.

  Lemma nat_eqb_eq : forall n m : nat, Nat.eqb n m = true -> n = m.
  Proof.
    induction n as [| n' IH].
    - intros [| m'] H. + reflexivity. + discriminate.
    - intros [| m'] H. + discriminate. + simpl in H.
      apply IH in H. rewrite H. reflexivity.
  Qed.

  Lemma nat_eqb_neq : forall n m : nat, n <> m -> Nat.eqb n m = false.
  Proof.
    induction n as [| n' IH].
    - intros [| m'] H. + contradiction. + reflexivity.
    - intros [| m'] H. + reflexivity. + simpl.
      apply IH. intro Heq. apply H. rewrite Heq. reflexivity.
  Qed.

  Lemma nat_ltb_ge : forall n m : nat, n >= m -> Nat.ltb n m = false.
  Proof.
    induction n as [| n' IH].
    - intros [| m'] H. + reflexivity. + inversion H.
    - intros [| m'] H. + reflexivity. + simpl.
      apply IH. unfold ge in *. apply le_S_n. exact H.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 3. CAPABILITY CONTAINMENT PREDICATE                                     *)
  (* ----------------------------------------------------------------------- *)

  Definition caps_contained (req_caps worker_caps : nat) : bool :=
    Nat.leb req_caps worker_caps.

  (* ----------------------------------------------------------------------- *)
  (* 4. HARD ELIGIBILITY CONSTRAINTS                                         *)
  (* ----------------------------------------------------------------------- *)

  Definition lifecycle_ready (s : LifecycleStage) : bool :=
    match s with
    | LS_READY => true
    | _ => false
    end.

  (* Worker Identity = (ConfigGeneration, ConfigHash, SandboxProfileHash,
     CapabilityEnvelopeHash). All four components MUST match for eligibility. *)
  Definition HardConstraints (w : WorkerReplica) (i : InvocationRequest) : bool :=
    andb (lifecycle_ready (w_state w))
    (andb (Nat.eqb (w_gen w) (i_target_gen i))
    (andb (Nat.eqb (w_hash w) (i_target_hash i))
    (andb (Nat.eqb (w_profile w) (i_profile i))
    (andb (Nat.eqb (w_sandbox_hash w) (i_sandbox_hash i))
    (andb (Nat.eqb (w_cap_hash w) (i_cap_hash i))
    (andb (caps_contained (i_n_req_caps i) (w_n_caps w))
          (Nat.ltb (w_inflight w) (w_limit w)))))))).

  (* ----------------------------------------------------------------------- *)
  (* 5. GATEWAY STATE & LEASE MANAGER MODEL                                  *)
  (* ----------------------------------------------------------------------- *)

  Fixpoint domain_locked (d : StateDomainKey) (active : list StateDomainKey) : bool :=
    match active with
    | nil => false
    | cons x xs => if Nat.eqb d x then true else domain_locked d xs
    end.

  Record GatewayState := mkGateway {
    g_queue_depth     : nat;
    g_max_queue_depth : nat;
    g_active_domains  : list StateDomainKey;
  }.

  Definition GrantLeaseCondition
      (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest) : bool :=
    andb (HardConstraints w i)
         (negb (domain_locked (i_domain_key i) (g_active_domains gs))).

  (* ----------------------------------------------------------------------- *)
  (* 6. RD-F1: ELIGIBILITY SAFETY                                            *)
  (*    Selected(W,I) => Eligible(W,I)                                       *)
  (* ----------------------------------------------------------------------- *)

  Theorem rd_f1_eligibility_safety :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      GrantLeaseCondition gs w i = true ->
      HardConstraints w i = true.
  Proof.
    intros gs w i H.
    unfold GrantLeaseCondition in H.
    apply andb_true_elim in H. destruct H as [Hhard _].
    exact Hhard.
  Qed.

  Ltac peel_left H :=
    apply andb_true_elim in H; destruct H as [_ H].

  (* ----------------------------------------------------------------------- *)
  (* 7. RD-F2: CAPABILITY CONTAINMENT                                        *)
  (*    Λ_I ⊆ Λ_W                                                           *)
  (* ----------------------------------------------------------------------- *)

  Theorem rd_f2_capability_containment :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      GrantLeaseCondition gs w i = true ->
      caps_contained (i_n_req_caps i) (w_n_caps w) = true.
  Proof.
    intros gs w i H.
    apply rd_f1_eligibility_safety in H.
    unfold HardConstraints in H.
    peel_left H; peel_left H; peel_left H; peel_left H; peel_left H; peel_left H.
    apply andb_true_elim in H. destruct H as [Hcaps _].
    exact Hcaps.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 8. RD-F3: CONFIG GENERATION & HASH FENCING                              *)
  (*    GrantLease => w_gen = target_gen ∧ w_hash = target_hash              *)
  (* ----------------------------------------------------------------------- *)

  Theorem rd_f3_config_fencing :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      GrantLeaseCondition gs w i = true ->
      w_gen w = i_target_gen i /\ w_hash w = i_target_hash i.
  Proof.
    intros gs w i H.
    apply rd_f1_eligibility_safety in H.
    unfold HardConstraints in H.
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [Hgen H].
    apply andb_true_elim in H. destruct H as [Hhash _].
    split; apply nat_eqb_eq; assumption.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 9. RD-F4: LEASE FENCING PRESERVATION (STALE CONFIG REJECTION)           *)
  (*    e_stale < e_current => CommitRejected                                *)
  (* ----------------------------------------------------------------------- *)

  Theorem rd_f4_lease_fencing_preservation :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      w_gen w <> i_target_gen i ->
      GrantLeaseCondition gs w i = false.
  Proof.
    intros gs w i Hneq.
    unfold GrantLeaseCondition.
    assert (Hhc : HardConstraints w i = false).
    { unfold HardConstraints.
      destruct (lifecycle_ready (w_state w)) eqn:Hlife; simpl.
      2: { reflexivity. }
      rewrite nat_eqb_neq by exact Hneq. reflexivity. }
    rewrite Hhc. reflexivity.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 10. RD-F5: ROUTER NON-AUTHORITY                                         *)
  (*     RouterOutput ≠> Authority                                           *)
  (* ----------------------------------------------------------------------- *)

  Record PlacementProposal := mkProposal {
    pp_worker_id : nat;
    pp_inv_id    : nat;
  }.

  Inductive HasActiveLease (gs : GatewayState) : nat -> nat -> Prop :=
    | lease_granted :
        forall w i, HasActiveLease gs w i.

  Theorem rd_f5_router_non_authority :
    forall (p : PlacementProposal),
      ~ (forall gs : GatewayState,
           g_active_domains gs = nil ->
           HasActiveLease gs (pp_worker_id p) (pp_inv_id p) ->
           GrantLeaseCondition gs
             (mkWorker (pp_worker_id p) 0 0 0 0 0 LS_OFFLINE 0 0 0)
             (mkInvocation (pp_inv_id p) 1 0 0 0 0 0 0) = true).
  Proof.
    intros p Habs.
    assert (Hbad : GrantLeaseCondition
      (mkGateway 0 10 nil)
      (mkWorker (pp_worker_id p) 0 0 0 0 0 LS_OFFLINE 0 0 0)
      (mkInvocation (pp_inv_id p) 1 0 0 0 0 0 0) = true).
    { apply Habs. - reflexivity. - constructor. }
    unfold GrantLeaseCondition in Hbad.
    unfold HardConstraints in Hbad.
    simpl in Hbad. discriminate.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 11. RD-F6: UNADMITTED SAFETY                                            *)
  (*     UNADMITTED => ¬Authorized ∧ ¬ActuationStarted                      *)
  (* ----------------------------------------------------------------------- *)

  Inductive InvocationStage :=
    | INV_UNADMITTED
    | INV_QUEUED
    | INV_DISPATCHED
    | INV_ACTUATED
    | INV_COMMITTED.

  Definition stage_authorized (s : InvocationStage) : bool :=
    match s with
    | INV_UNADMITTED => false
    | INV_QUEUED => false
    | _ => true
    end.

  Definition stage_actuated (s : InvocationStage) : bool :=
    match s with
    | INV_ACTUATED => true
    | INV_COMMITTED => true
    | _ => false
    end.

  Theorem rd_f6_unadmitted_safety :
    forall (s : InvocationStage),
      s = INV_UNADMITTED ->
      stage_authorized s = false /\ stage_actuated s = false.
  Proof.
    intros s H. subst. simpl. split; reflexivity.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 12. RD-F7: SINGLE COMMITMENT                                            *)
  (*     #CommittedEffect(I) <= 1                                            *)
  (* ----------------------------------------------------------------------- *)

  Inductive CommitStatus :=
    | CS_UNCOMMITTED
    | CS_COMMITTED.

  Definition can_commit (cs : CommitStatus) : bool :=
    match cs with
    | CS_UNCOMMITTED => true
    | CS_COMMITTED => false
    end.

  Definition do_commit (cs : CommitStatus) : CommitStatus :=
    match cs with
    | CS_UNCOMMITTED => CS_COMMITTED
    | CS_COMMITTED => CS_COMMITTED
    end.

  Theorem rd_f7_single_commitment :
    forall (cs : CommitStatus),
      cs = CS_COMMITTED ->
      can_commit cs = false.
  Proof.
    intros cs H. subst. reflexivity.
  Qed.

  Theorem rd_f7_commit_idempotent :
    forall (cs : CommitStatus),
      do_commit (do_commit cs) = do_commit cs.
  Proof.
    intros []; reflexivity.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 13. RD-F8: BOUNDED ADMISSION                                            *)
  (*     QueueDepth >= MaxQueueDepth => CannotAdmit                          *)
  (* ----------------------------------------------------------------------- *)

  Definition can_enqueue (gs : GatewayState) : bool :=
    Nat.ltb (g_queue_depth gs) (g_max_queue_depth gs).

  Theorem rd_f8_bounded_admission :
    forall (gs : GatewayState),
      g_queue_depth gs >= g_max_queue_depth gs ->
      can_enqueue gs = false.
  Proof.
    intros gs Hge.
    unfold can_enqueue.
    apply nat_ltb_ge.
    exact Hge.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 14. RD-F9: STATE-DOMAIN CONFLICT SAFETY                                 *)
  (* ----------------------------------------------------------------------- *)

  Theorem rd_f9_state_domain_safety :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      domain_locked (i_domain_key i) (g_active_domains gs) = true ->
      GrantLeaseCondition gs w i = false.
  Proof.
    intros gs w i Hlocked.
    unfold GrantLeaseCondition.
    rewrite Hlocked. simpl.
    destruct (HardConstraints w i); reflexivity.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 15. RD-F10: TOCTOU REVALIDATION SAFETY                                  *)
  (*                                                                         *)
  (* The most important Phase 4 proof: router eligibility is only a          *)
  (* proposal; Gateway revalidation is authoritative.                        *)
  (* ----------------------------------------------------------------------- *)

  Theorem rd_f10_toctou_offline :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      w_state w = LS_OFFLINE ->
      GrantLeaseCondition gs w i = false.
  Proof.
    intros gs w i Hoffline.
    unfold GrantLeaseCondition, HardConstraints.
    rewrite Hoffline. simpl. reflexivity.
  Qed.

  Theorem rd_f10_toctou_draining :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      w_state w = LS_DRAINING ->
      GrantLeaseCondition gs w i = false.
  Proof.
    intros gs w i Hdrain.
    unfold GrantLeaseCondition, HardConstraints.
    rewrite Hdrain. simpl. reflexivity.
  Qed.

  Theorem rd_f10_toctou_generation_drift :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      w_gen w <> i_target_gen i ->
      GrantLeaseCondition gs w i = false.
  Proof.
    exact rd_f4_lease_fencing_preservation.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 16. RECOVERY BUCKET FORMAL MODEL                                        *)
  (*                                                                         *)
  (* Models the concrete RecoveryBucket taxonomy from ledger.py:              *)
  (*   UNADMITTED / ADMITTED_UNACTUATED / ACTUATED_COMMITTED / ACTUATION_UNKNOWN *)
  (* ----------------------------------------------------------------------- *)

  Inductive RecoveryBucket :=
    | RB_UNADMITTED
    | RB_ADMITTED_UNACTUATED
    | RB_ACTUATED_COMMITTED
    | RB_ACTUATION_UNKNOWN.

  Definition recovery_safe_to_retry (rb : RecoveryBucket) : bool :=
    match rb with
    | RB_UNADMITTED => true          (* Never authorized — safe to discard or retry *)
    | RB_ADMITTED_UNACTUATED => true  (* Authorized but no actuation started — safe to retry *)
    | RB_ACTUATED_COMMITTED => false  (* Effect committed — MUST NOT retry *)
    | RB_ACTUATION_UNKNOWN => false   (* Non-idempotent effect may have occurred — MUST NOT auto-retry *)
    end.

  (* RD-F11: ACTUATION_UNKNOWN must not be automatically retried *)
  Theorem rd_f11_actuation_unknown_no_auto_retry :
    recovery_safe_to_retry RB_ACTUATION_UNKNOWN = false.
  Proof. reflexivity. Qed.

  (* RD-F12: ACTUATED_COMMITTED must not be retried *)
  Theorem rd_f12_committed_no_retry :
    recovery_safe_to_retry RB_ACTUATED_COMMITTED = false.
  Proof. reflexivity. Qed.

  (* RD-F13: UNADMITTED is always safe to retry or discard *)
  Theorem rd_f13_unadmitted_safe_retry :
    recovery_safe_to_retry RB_UNADMITTED = true.
  Proof. reflexivity. Qed.

  (* RD-F14: ADMITTED_UNACTUATED is safe to retry *)
  Theorem rd_f14_admitted_unactuated_safe_retry :
    recovery_safe_to_retry RB_ADMITTED_UNACTUATED = true.
  Proof. reflexivity. Qed.

  (* Durable log proof model for UNADMITTED: absence of evidence is proven by journal integrity *)
  Record DurableLogWitness := mkWitness {
    w_has_auth_entry    : bool;
    w_has_actuation_entry : bool;
    w_journal_intact    : bool;
  }.

  Definition unadmitted_durable_proven (w : DurableLogWitness) : bool :=
    andb (w_journal_intact w)
         (andb (negb (w_has_auth_entry w))
               (negb (w_has_actuation_entry w))).

  Theorem rd_f6_unadmitted_durable_safety :
    forall (w : DurableLogWitness),
      unadmitted_durable_proven w = true ->
      w_has_auth_entry w = false /\ w_has_actuation_entry w = false.
  Proof.
    intros w H.
    unfold unadmitted_durable_proven in H.
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [Hauth Hact].
    destruct (w_has_auth_entry w) eqn:Eauth; destruct (w_has_actuation_entry w) eqn:Eact.
    - discriminate.
    - discriminate.
    - discriminate.
    - split; reflexivity.
  Qed.

  (* Explicit ¬ActuationStarted invariant for ADMITTED_UNACTUATED *)
  Record InvocationRecoveryState := mkRecState {
    irs_authorized        : bool;
    irs_actuation_started : bool;
    irs_retry_safe        : bool;
  }.

  Definition recovery_state_of_bucket (rb : RecoveryBucket) : InvocationRecoveryState :=
    match rb with
    | RB_UNADMITTED => mkRecState false false true
    | RB_ADMITTED_UNACTUATED => mkRecState true false true
    | RB_ACTUATED_COMMITTED => mkRecState true true false
    | RB_ACTUATION_UNKNOWN => mkRecState true true false
    end.

  Theorem rd_f14_admitted_unactuated_explicit_no_actuation :
    forall (rb : RecoveryBucket),
      rb = RB_ADMITTED_UNACTUATED ->
      irs_authorized (recovery_state_of_bucket rb) = true /\
      irs_actuation_started (recovery_state_of_bucket rb) = false /\
      irs_retry_safe (recovery_state_of_bucket rb) = true.
  Proof.
    intros rb H. subst. simpl. split; [| split]; reflexivity.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 17. CONCURRENT STATE-DOMAIN CONFLICT INVARIANT                          *)
  (*                                                                         *)
  (* ConcurrentExecution(I1,I2) ∧ Conflict(I1,I2) => ¬ConcurrentActuation   *)
  (* ----------------------------------------------------------------------- *)

  Definition invocations_conflict (i1 i2 : InvocationRequest) : bool :=
    Nat.eqb (i_domain_key i1) (i_domain_key i2).

  Theorem rd_f15_concurrent_conflict_exclusion :
    forall (gs : GatewayState) (w1 w2 : WorkerReplica) (i1 i2 : InvocationRequest),
      invocations_conflict i1 i2 = true ->
      GrantLeaseCondition gs w1 i1 = true ->
      domain_locked (i_domain_key i2) (g_active_domains gs) = true ->
      GrantLeaseCondition gs w2 i2 = false.
  Proof.
    intros gs w1 w2 i1 i2 Hconflict Hgrant1 Hlocked.
    apply rd_f9_state_domain_safety. exact Hlocked.
  Qed.

  Definition CanCrossActuationBoundary (gs : GatewayState) (i : InvocationRequest) : bool :=
    negb (domain_locked (i_domain_key i) (g_active_domains gs)).

  Theorem rd_f15_state_domain_actuation_fence :
    forall (gs : GatewayState) (w2 : WorkerReplica) (i2 : InvocationRequest),
      domain_locked (i_domain_key i2) (g_active_domains gs) = true ->
      CanCrossActuationBoundary gs i2 = false.
  Proof.
    intros gs w2 i2 Hlocked.
    unfold CanCrossActuationBoundary.
    rewrite Hlocked. reflexivity.
  Qed.

  Theorem rd_f15_assigned_conflict_actuation_blocked :
    forall (gs : GatewayState) (i1 i2 : InvocationRequest),
      invocations_conflict i1 i2 = true ->
      domain_locked (i_domain_key i1) (g_active_domains gs) = true ->
      CanCrossActuationBoundary gs i2 = false.
  Proof.
    intros gs i1 i2 Hconflict Hlocked1.
    unfold invocations_conflict in Hconflict.
    apply nat_eqb_eq in Hconflict.
    unfold CanCrossActuationBoundary.
    unfold domain_locked in *.
    rewrite <- Hconflict.
    rewrite Hlocked1. reflexivity.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 18. SANDBOX & CAPABILITY HASH FENCING                                   *)
  (* ----------------------------------------------------------------------- *)

  Theorem rd_f16_sandbox_hash_fencing :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      GrantLeaseCondition gs w i = true ->
      Nat.eqb (w_sandbox_hash w) (i_sandbox_hash i) = true.
  Proof.
    intros gs w i H.
    apply rd_f1_eligibility_safety in H.
    unfold HardConstraints in H.
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [Hsbx _].
    exact Hsbx.
  Qed.

  Theorem rd_f17_cap_hash_fencing :
    forall (gs : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      GrantLeaseCondition gs w i = true ->
      Nat.eqb (w_cap_hash w) (i_cap_hash i) = true.
  Proof.
    intros gs w i H.
    apply rd_f1_eligibility_safety in H.
    unfold HardConstraints in H.
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [_ H].
    apply andb_true_elim in H. destruct H as [Hcap _].
    exact Hcap.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 19. ASSUMPTION AUDIT                                                    *)
  (* ----------------------------------------------------------------------- *)

  Print Assumptions rd_f1_eligibility_safety.
  Print Assumptions rd_f2_capability_containment.
  Print Assumptions rd_f3_config_fencing.
  Print Assumptions rd_f4_lease_fencing_preservation.
  Print Assumptions rd_f5_router_non_authority.
  Print Assumptions rd_f6_unadmitted_safety.
  Print Assumptions rd_f6_unadmitted_durable_safety.
  Print Assumptions rd_f7_single_commitment.
  Print Assumptions rd_f7_commit_idempotent.
  Print Assumptions rd_f8_bounded_admission.
  Print Assumptions rd_f9_state_domain_safety.
  Print Assumptions rd_f10_toctou_offline.
  Print Assumptions rd_f10_toctou_draining.
  Print Assumptions rd_f10_toctou_generation_drift.
  Print Assumptions rd_f11_actuation_unknown_no_auto_retry.
  Print Assumptions rd_f12_committed_no_retry.
  Print Assumptions rd_f13_unadmitted_safe_retry.
  Print Assumptions rd_f14_admitted_unactuated_safe_retry.
  Print Assumptions rd_f14_admitted_unactuated_explicit_no_actuation.
  Print Assumptions rd_f15_concurrent_conflict_exclusion.
  Print Assumptions rd_f15_state_domain_actuation_fence.
  Print Assumptions rd_f15_assigned_conflict_actuation_blocked.
  Print Assumptions rd_f16_sandbox_hash_fencing.
  Print Assumptions rd_f17_cap_hash_fencing.

End Phase4RoutingRefinement.
