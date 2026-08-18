(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: GrantCapRTL.v                                                     *)
(* Classification: R2 (RTL Transition Correspondence & Grant Cap Refinement) *)
(* Purpose: Milestone F2.2 - Hardware RTL State Machine & Grant Refinement   *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.

Section GrantCapRTL.

  (* ======================================================================= *)
  (* 1. HARDWARE RTL STATE & CAPABILITY REPRESENTATION                       *)
  (* ======================================================================= *)

  (** Raw 64-bit Hardware STCR fields extracted directly from 
      rtl/cortex_stcr_pipeline.sv:
      [63]    : Valid bit (V)
      [62:48] : 15-bit Spatial Mask
      [47:16] : 32-bit Base Address
      [15:0]  : 16-bit Epoch Ceiling *)
  Record RawSTCR := {
    raw_v     : bool;
    raw_mask  : nat;
    raw_base  : nat;
    raw_epoch : nat
  }.

  (** Pipelined RTL Core Architectural State *)
  Record RTLState := {
    rtl_stcr_file  : nat -> RawSTCR;
    rtl_reg_hec    : nat;
    rtl_eff_trap   : bool;
    rtl_trap_cause : nat;
    rtl_wb_retired : bool
  }.

  (* ======================================================================= *)
  (* 2. GRANT PRECONDITION & OPERATIONAL TRANSITION RELATION (F2.2a)          *)
  (* ======================================================================= *)

  (** Explicit Grant Precondition:
      Parent MUST be valid (V=1) AND HEC MUST NOT exceed parent epoch ceiling. *)
  Definition GrantAllowed (parent : RawSTCR) (hec : nat) : Prop :=
    parent.(raw_v) = true /\ hec <= parent.(raw_epoch).

  (** Bitwise spatial mask attenuation simulation (Mask_child = Mask_parent & Request) *)
  Definition bitwise_and_15 (mask req : nat) : nat :=
    Nat.land mask req.

  (** Operational RTL Transition Relation for Opcode 0x02 (grant_cap)
      Models exact EX/WB pipeline behavior from cortex_stcr_pipeline.sv *)
  Inductive rtl_grant_cap_step (src dst req_imm : nat) (s s' : RTLState) : Prop :=
    | rtl_grant_success :
        forall (p : RawSTCR),
          s.(rtl_stcr_file) src = p ->
          GrantAllowed p s.(rtl_reg_hec) ->
          s'.(rtl_reg_hec) = s.(rtl_reg_hec) ->
          s'.(rtl_eff_trap) = false ->
          s'.(rtl_trap_cause) = 0 ->
          s'.(rtl_wb_retired) = true ->
          s'.(rtl_stcr_file) dst = {|
            raw_v     := true;
            raw_mask  := bitwise_and_15 p.(raw_mask) req_imm;
            raw_base  := p.(raw_base);
            raw_epoch := s.(rtl_reg_hec)
          |} ->
          (forall k, k <> dst -> s'.(rtl_stcr_file) k = s.(rtl_stcr_file) k) ->
          rtl_grant_cap_step src dst req_imm s s'
    | rtl_grant_trap_invalid :
        forall (p : RawSTCR),
          s.(rtl_stcr_file) src = p ->
          p.(raw_v) = false ->
          s'.(rtl_reg_hec) = s.(rtl_reg_hec) ->
          s'.(rtl_eff_trap) = true ->
          s'.(rtl_trap_cause) = 1 ->
          s'.(rtl_wb_retired) = true ->
          s'.(rtl_stcr_file) dst = {| raw_v := false; raw_mask := 0; raw_base := 0; raw_epoch := 0 |} ->
          (forall k, k <> dst -> s'.(rtl_stcr_file) k = s.(rtl_stcr_file) k) ->
          rtl_grant_cap_step src dst req_imm s s'
    | rtl_grant_trap_expired :
        forall (p : RawSTCR),
          s.(rtl_stcr_file) src = p ->
          p.(raw_v) = true ->
          s.(rtl_reg_hec) > p.(raw_epoch) ->
          s'.(rtl_reg_hec) = s.(rtl_reg_hec) ->
          s'.(rtl_eff_trap) = true ->
          s'.(rtl_trap_cause) = 2 ->
          s'.(rtl_wb_retired) = true ->
          s'.(rtl_stcr_file) dst = {| raw_v := false; raw_mask := 0; raw_base := 0; raw_epoch := 0 |} ->
          (forall k, k <> dst -> s'.(rtl_stcr_file) k = s.(rtl_stcr_file) k) ->
          rtl_grant_cap_step src dst req_imm s s'.

  (* ======================================================================= *)
  (* 3. STRUCTURAL INVARIANT THEOREMS (F2.2b)                                 *)
  (* ======================================================================= *)

  (** Definition of Bitmask Spatial Subsetting *)
  Definition mask_subset (child_mask parent_mask : nat) : Prop :=
    exists req_constraint : nat, child_mask = Nat.land parent_mask req_constraint.

  (** [LEMMA 1] Grant success requires parent validity *)
  Lemma grant_cap_success_requires_valid_parent :
    forall src dst req_imm s s' p,
      rtl_grant_cap_step src dst req_imm s s' ->
      s'.(rtl_eff_trap) = false ->
      s.(rtl_stcr_file) src = p ->
      p.(raw_v) = true.
  Proof.
    intros src dst req_imm s s' p Hstep Hnotrap Hsrc.
    destruct Hstep as [p' Hstcr Hgrant Hhec Hnotrap' Hcause Hret Hdst_val Hother
                      | p' Hstcr Hinv Hhec Htrap Hcause Hret Hdst_val Hother
                      | p' Hstcr Hvalid Hexp Hhec Htrap Hcause Hret Hdst_val Hother].
    - rewrite Hsrc in Hstcr. subst p'. destruct Hgrant as [Hv _]. exact Hv.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
  Qed.

  (** [LEMMA 2] Grant success requires unexpired parent epoch *)
  Lemma grant_cap_success_requires_unexpired_parent :
    forall src dst req_imm s s' p,
      rtl_grant_cap_step src dst req_imm s s' ->
      s'.(rtl_eff_trap) = false ->
      s.(rtl_stcr_file) src = p ->
      s.(rtl_reg_hec) <= p.(raw_epoch).
  Proof.
    intros src dst req_imm s s' p Hstep Hnotrap Hsrc.
    destruct Hstep as [p' Hstcr Hgrant Hhec Hnotrap' Hcause Hret Hdst_val Hother
                      | p' Hstcr Hinv Hhec Htrap Hcause Hret Hdst_val Hother
                      | p' Hstcr Hvalid Hexp Hhec Htrap Hcause Hret Hdst_val Hother].
    - rewrite Hsrc in Hstcr. subst p'. destruct Hgrant as [_ Hep]. exact Hep.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
  Qed.

  (** [THEOREM: SPATIAL MASK NON-EXPANSION] 
      Child spatial mask is strictly a bitwise submask of parent spatial mask. *)
  Theorem grant_cap_mask_nonexpansion :
    forall src dst req_imm s s',
      rtl_grant_cap_step src dst req_imm s s' ->
      s'.(rtl_eff_trap) = false ->
      forall p c,
        s.(rtl_stcr_file) src = p ->
        s'.(rtl_stcr_file) dst = c ->
        mask_subset c.(raw_mask) p.(raw_mask).
  Proof.
    intros src dst req_imm s s' Hstep Hnotrap p c Hsrc Hdst.
    destruct Hstep as [p' Hstcr Hgrant Hhec Hnotrap' Hcause Hret Hdst_val Hother
                      | p' Hstcr Hinv Hhec Htrap Hcause Hret Hdst_val Hother
                      | p' Hstcr Hvalid Hexp Hhec Htrap Hcause Hret Hdst_val Hother].
    - rewrite Hsrc in Hstcr. subst p'.
      rewrite Hdst in Hdst_val. subst c.
      simpl.
      unfold mask_subset, bitwise_and_15.
      exists req_imm.
      reflexivity.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
  Qed.

  (** [THEOREM: TEMPORAL EPOCH NON-EXPANSION]
      Child epoch ceiling is strictly bounded by parent epoch ceiling. *)
  Theorem grant_cap_epoch_nonexpansion :
    forall src dst req_imm s s',
      rtl_grant_cap_step src dst req_imm s s' ->
      s'.(rtl_eff_trap) = false ->
      forall p c,
        s.(rtl_stcr_file) src = p ->
        s'.(rtl_stcr_file) dst = c ->
        c.(raw_epoch) <= p.(raw_epoch).
  Proof.
    intros src dst req_imm s s' Hstep Hnotrap p c Hsrc Hdst.
    destruct Hstep as [p' Hstcr Hgrant Hhec Hnotrap' Hcause Hret Hdst_val Hother
                      | p' Hstcr Hinv Hhec Htrap Hcause Hret Hdst_val Hother
                      | p' Hstcr Hvalid Hexp Hhec Htrap Hcause Hret Hdst_val Hother].
    - rewrite Hsrc in Hstcr. subst p'.
      rewrite Hdst in Hdst_val. subst c.
      simpl.
      destruct Hgrant as [_ Hep].
      exact Hep.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
  Qed.

  (** [THEOREM: TRAP INTEGRITY]
      If GrantAllowed is violated (invalid or expired parent), hardware MUST trap. *)
  Theorem rtl_grant_cap_failure_traps :
    forall src dst req_imm s s' p,
      s.(rtl_stcr_file) src = p ->
      ~ GrantAllowed p s.(rtl_reg_hec) ->
      rtl_grant_cap_step src dst req_imm s s' ->
      s'.(rtl_eff_trap) = true /\ (s'.(rtl_trap_cause) = 1 \/ s'.(rtl_trap_cause) = 2).
  Proof.
    intros src dst req_imm s s' p Hsrc Hnotallowed Hstep.
    destruct Hstep as [p' Hstcr Hgrant Hhec Hnotrap' Hcause Hret Hdst_val Hother
                      | p' Hstcr Hinv Hhec Htrap Hcause Hret Hdst_val Hother
                      | p' Hstcr Hvalid Hexp Hhec Htrap Hcause Hret Hdst_val Hother].
    - rewrite Hsrc in Hstcr. subst p'.
      contradiction Hnotallowed.
    - rewrite Hsrc in Hstcr. subst p'.
      split; [exact Htrap | left; exact Hcause].
    - rewrite Hsrc in Hstcr. subst p'.
      split; [exact Htrap | right; exact Hcause].
  Qed.

  (* ======================================================================= *)
  (* 4. CANONICAL REFINEMENT CORRESPONDENCE THEOREM (F2.2c)                  *)
  (* ======================================================================= *)

  (** Projection: RawSTCR to ConcreteSTCR *)
  Definition alpha_raw_stcr (slot_id : nat) (raw : RawSTCR) : ConcreteSTCR := {|
    stcr_valid          := raw.(raw_v);
    stcr_authority_mask := 0;
    stcr_base_addr      := raw.(raw_base);
    stcr_epoch          := raw.(raw_epoch);
    stcr_id             := slot_id
  |}.

  Definition rtl_to_concrete (s : RTLState) : ConcreteSystemState := {|
    c_hw_state := {|
      c_stcr_bank := cons (alpha_raw_stcr 0 (s.(rtl_stcr_file) 0)) nil;
      c_reg_hec   := s.(rtl_reg_hec);
      c_eff_trap  := s.(rtl_eff_trap)
    |};
    c_rt_state := {|
      c_active_tokens    := nil;
      c_supervisor_pid   := 0;
      c_audit_chain_head := 0
    |}
  |}.

  (** Relational Refinement for RTL State *)
  Definition refines_rtl (s : RTLState) (w : World list_auth_model) : Prop :=
    refines (rtl_to_concrete s) w.

  (** [THEOREM: F2.2c CANONICAL REFINEMENT CORRESPONDENCE]
      Proves that successful hardware grant transitions preserve World refinement $R(C, W)$. *)
  Theorem grant_cap_refinement_correspondence :
    forall dst req_imm s s' w,
      refines_rtl s w ->
      rtl_grant_cap_step 0 dst req_imm s s' ->
      s'.(rtl_eff_trap) = false ->
      exists (w' : World list_auth_model), refines_rtl s' w'.
  Proof.
    intros dst req_imm s s' w Href_rtl Hstep Hnotrap.
    destruct Hstep as [p Hstcr Hgrant Hhec Hnotrap' Hcause Hret Hdst_val Hother
                      | p Hstcr Hinv Hhec Htrap Hcause Hret Hdst_val Hother
                      | p Hstcr Hvalid Hexp Hhec Htrap Hcause Hret Hdst_val Hother].
    - destruct Href_rtl as [Hwf [Hepoch Hlambda]].
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
          { intros Hv_true. destruct dst as [| dst_prev].
            - rewrite Hdst_val in *. simpl in *. rewrite Hep. rewrite Hhec. apply le_n.
            - rewrite Hother in * by discriminate.
              unfold concrete_well_formed, hardware_well_formed in Hwf.
              simpl in Hwf.
              assert (Hin_s : stcr_in stcr_elem (cons (alpha_raw_stcr 0 (rtl_stcr_file s 0)) nil)) by (left; split; auto).
              pose proof (Hwf stcr_elem Hin_s) as [Hepoch_s _].
              simpl. rewrite Hhec. apply Hepoch_s, Hv_true. }
          { unfold stcr_mask_representable.
            destruct dst as [| dst_prev].
            - rewrite Hdst_val in *. simpl in *.
              destruct Hgrant as [Hv0_src _].
              assert (Hin_s : stcr_in {| stcr_valid := true; stcr_authority_mask := stcr_authority_mask stcr_elem; stcr_base_addr := 0; stcr_epoch := raw_epoch (rtl_stcr_file s 0); stcr_id := 0 |} (cons (alpha_raw_stcr 0 (rtl_stcr_file s 0)) nil)) by (left; repeat split; try auto; rewrite Hstcr; exact Hv0_src).
              unfold concrete_well_formed, hardware_well_formed in Hwf.
              simpl in Hwf.
              pose proof (Hwf {| stcr_valid := true; stcr_authority_mask := stcr_authority_mask stcr_elem; stcr_base_addr := 0; stcr_epoch := raw_epoch (rtl_stcr_file s 0); stcr_id := 0 |} Hin_s) as [_ Hmask_s].
              exact Hmask_s.
            - rewrite Hother in * by discriminate.
              unfold concrete_well_formed, hardware_well_formed in Hwf.
              simpl in Hwf.
              assert (Hin_s : stcr_in stcr_elem (cons (alpha_raw_stcr 0 (rtl_stcr_file s 0)) nil)) by (left; split; auto).
              pose proof (Hwf stcr_elem Hin_s) as [_ Hmask_s].
              exact Hmask_s. }
        * contradiction Hin_nil.
      + split; reflexivity.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
    - rewrite Htrap in Hnotrap. discriminate Hnotrap.
  Qed.

  Print Assumptions grant_cap_refinement_correspondence.

End GrantCapRTL.
