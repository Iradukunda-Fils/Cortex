(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: RevokeExpiryRTL.v                                                 *)
(* Classification: R2 (RTL Transition Correspondence & Authority Invalidation) *)
(* Purpose: Milestone F2.3 - Revocation, Temporal Expiry & Execution Denial  *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.
From Cortex Require Import GrantCapRTL.

Section RevokeExpiryRTL.

  (** Helper Lemma: S n <= n is impossible for any Peano natural n *)
  Lemma Sn_le_n_false : forall n, S n <= n -> False.
  Proof.
    induction n as [| n' IHn'].
    - intros H. inversion H.
    - intros H. apply IHn'. apply le_S_n. exact H.
  Qed.

  (* ======================================================================= *)
  (* 1. EXPLICIT REVOCATION TRANSITION RELATION (F2.3a)                       *)
  (* ======================================================================= *)

  (** Operational RTL Transition Relation for Opcode 0x03 (revoke_cap)
      Models STCR zeroization and writeback retirement in cortex_stcr_pipeline.sv *)
  Inductive rtl_revoke_cap_step (slot : nat) (s s' : RTLState) : Prop :=
    | rtl_revoke_success :
        s'.(rtl_reg_hec) = s.(rtl_reg_hec) ->
        s'.(rtl_eff_trap) = false ->
        s'.(rtl_trap_cause) = 0 ->
        s'.(rtl_wb_retired) = true ->
        s'.(rtl_stcr_file) slot = {|
          raw_v     := false;
          raw_mask  := 0;
          raw_base  := 0;
          raw_epoch := 0
        |} ->
        (forall k, k <> slot -> s'.(rtl_stcr_file) k = s.(rtl_stcr_file) k) ->
        rtl_revoke_cap_step slot s s'.

  (** [THEOREM: F2.3a REVOCATION ZEROIZATION]
      Revoking a capability slot explicitly zeroes the valid bit and spatial mask. *)
  Theorem revoke_cap_zeroizes :
    forall slot s s',
      rtl_revoke_cap_step slot s s' ->
      (s'.(rtl_stcr_file) slot).(raw_v) = false /\
      (s'.(rtl_stcr_file) slot).(raw_mask) = 0.
  Proof.
    intros slot s s' Hstep.
    destruct Hstep as [Hhec Htrap Hcause Hret Hslot Hother].
    rewrite Hslot. simpl. split; reflexivity.
  Qed.

  (** [THEOREM: F2.3a REVOCATION REFINEMENT CORRESPONDENCE]
      Explicit revocation preserves refinement R(C, W). *)
  Theorem revoke_refinement_correspondence :
    forall slot s s' w,
      refines_rtl s w ->
      rtl_revoke_cap_step slot s s' ->
      exists (w' : World list_auth_model), refines_rtl s' w'.
  Proof.
    intros slot s s' w Href_rtl Hstep.
    destruct Hstep as [Hhec Htrap Hcause Hret Hslot Hother].
    destruct Href_rtl as [Hwf [Hepoch Hlambda]].
    exists (mkWorld list_auth_model
            (alpha_stcr_bank (c_stcr_bank (c_hw_state (rtl_to_concrete s'))))
            (world_monitor w)
            (world_fuel w)
            (s'.(rtl_reg_hec))).
    unfold refines_rtl, refines. simpl.
    split.
    + unfold concrete_well_formed, hardware_well_formed.
      intros stcr_elem Hin. simpl in Hin.
      destruct Hin as [[Hid [Hep Hv]] | Hin_nil].
      * split.
        { intros Hv_true. revert Hother Hslot. destruct slot as [| slot_prev]; intros Hother Hslot.
          - rewrite Hslot in *. unfold alpha_raw_stcr in *. simpl in Hv. discriminate Hv.
          - specialize (Hother 0).
            assert (Hneq : 0 <> S slot_prev).
            { unfold not. intros H. discriminate. }
            apply Hother in Hneq. rewrite Hneq in *.
            unfold concrete_well_formed, hardware_well_formed in Hwf.
            simpl in Hwf.
            assert (Hin_s : stcr_in stcr_elem (cons (alpha_raw_stcr 0 (rtl_stcr_file s 0)) nil)) by (left; split; auto).
            pose proof (Hwf stcr_elem Hin_s) as [Hepoch_s _].
            simpl. rewrite Hhec. apply Hepoch_s, Hv_true. }
        { unfold stcr_mask_representable.
          revert Hother Hslot. destruct slot as [| slot_prev]; intros Hother Hslot.
          - rewrite Hslot in *. unfold alpha_raw_stcr in *. simpl in Hv. discriminate Hv.
          - specialize (Hother 0).
            assert (Hneq : 0 <> S slot_prev).
            { unfold not. intros H. discriminate. }
            apply Hother in Hneq. rewrite Hneq in *.
            unfold concrete_well_formed, hardware_well_formed in Hwf.
            simpl in Hwf.
            assert (Hin_s : stcr_in stcr_elem (cons (alpha_raw_stcr 0 (rtl_stcr_file s 0)) nil)) by (left; split; auto).
            pose proof (Hwf stcr_elem Hin_s) as [_ Hmask_s].
            exact Hmask_s. }
      * contradiction Hin_nil.
    + split; reflexivity.
  Qed.

  (* ======================================================================= *)
  (* 2. TEMPORAL EXPIRY SEMANTICS & INVARIANTS (F2.3b)                        *)
  (* ======================================================================= *)

  (** Definition of Capability Temporal Executability *)
  Definition stcr_temporally_valid (raw : RawSTCR) (hec : nat) : Prop :=
    raw.(raw_v) = true /\ hec <= raw.(raw_epoch).

  (** Definition of Capability Executability Condition *)
  Definition concrete_executable (s : RTLState) (slot : nat) : Prop :=
    stcr_temporally_valid (s.(rtl_stcr_file) slot) s.(rtl_reg_hec).

  (** [THEOREM: F2.3b TEMPORAL EXPIRY IMPLIES INVALIDITY]
      If active hardware HEC exceeds parent epoch ceiling, capability is non-executable. *)
  Theorem epoch_expiry_implies_invalid :
    forall s slot,
      s.(rtl_reg_hec) > (s.(rtl_stcr_file) slot).(raw_epoch) ->
      ~ concrete_executable s slot.
  Proof.
    intros s slot Hexp Hexec.
    unfold concrete_executable, stcr_temporally_valid in Hexec.
    destruct Hexec as [_ Hbound].
    assert (Hle : S (s.(rtl_stcr_file) slot).(raw_epoch) <= (s.(rtl_stcr_file) slot).(raw_epoch)) by (exact (le_trans (S (s.(rtl_stcr_file) slot).(raw_epoch)) s.(rtl_reg_hec) (s.(rtl_stcr_file) slot).(raw_epoch) Hexp Hbound)).
    apply (Sn_le_n_false (s.(rtl_stcr_file) slot).(raw_epoch) Hle).
  Qed.

  (* ======================================================================= *)
  (* 3. POST-INVALIDATION EXECUTION DENIAL & MONOTONICITY (F2.3c)             *)
  (* ======================================================================= *)

  (** Definition of Invalidated State (Revoked OR Expired) *)
  Definition stcr_invalidated (s : RTLState) (slot : nat) : Prop :=
    (s.(rtl_stcr_file) slot).(raw_v) = false \/ s.(rtl_reg_hec) > (s.(rtl_stcr_file) slot).(raw_epoch).

  (** [THEOREM: F2.3c POST-REVOCATION EXECUTION DENIAL]
      Explicit revocation guarantees subsequent execution denial. *)
  Theorem revoked_capability_not_executable :
    forall slot s s',
      rtl_revoke_cap_step slot s s' ->
      ~ concrete_executable s' slot.
  Proof.
    intros slot s s' Hstep Hexec.
    destruct Hstep as [Hhec Htrap Hcause Hret Hslot Hother].
    unfold concrete_executable, stcr_temporally_valid in Hexec.
    rewrite Hslot in Hexec. simpl in Hexec.
    destruct Hexec as [Hfalse _].
    discriminate Hfalse.
  Qed.

  (** [THEOREM: F2.3c COMBINED LIFETIME SOUNDNESS]
      Any capability that is either revoked or expired MUST be denied execution. *)
  Theorem capability_lifetime_sound :
    forall s slot,
      stcr_invalidated s slot ->
      ~ concrete_executable s slot.
  Proof.
    intros s slot Hinv Hexec.
    unfold stcr_invalidated in Hinv.
    unfold concrete_executable, stcr_temporally_valid in Hexec.
    destruct Hexec as [Hv Hep].
    destruct Hinv as [Hv_false | Hexp].
    - rewrite Hv in Hv_false. discriminate Hv_false.
    - assert (Hle : S (s.(rtl_stcr_file) slot).(raw_epoch) <= (s.(rtl_stcr_file) slot).(raw_epoch)) by (exact (le_trans (S (s.(rtl_stcr_file) slot).(raw_epoch)) s.(rtl_reg_hec) (s.(rtl_stcr_file) slot).(raw_epoch) Hexp Hep)).
      apply (Sn_le_n_false (s.(rtl_stcr_file) slot).(raw_epoch) Hle).
  Qed.

  (** [THEOREM: F2.3c MONOTONIC INVALIDATION PRESERVATION]
      Revoking a capability preserves invalidation unless explicitly re-granted. *)
  Theorem revocation_monotonic_preservation :
    forall slot s s',
      rtl_revoke_cap_step slot s s' ->
      stcr_invalidated s' slot.
  Proof.
    intros slot s s' Hstep.
    destruct Hstep as [Hhec Htrap Hcause Hret Hslot Hother].
    unfold stcr_invalidated.
    left. rewrite Hslot. reflexivity.
  Qed.

  Print Assumptions revoke_cap_zeroizes.
  Print Assumptions revoke_refinement_correspondence.
  Print Assumptions epoch_expiry_implies_invalid.
  Print Assumptions revoked_capability_not_executable.
  Print Assumptions capability_lifetime_sound.
  Print Assumptions revocation_monotonic_preservation.

End RevokeExpiryRTL.
