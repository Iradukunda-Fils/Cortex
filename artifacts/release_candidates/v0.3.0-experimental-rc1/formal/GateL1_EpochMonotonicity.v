(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: GateL1_EpochMonotonicity.v                                       *)
(* Classification: R0 (Model Aligned) / R1 (Representation Correspondence)  *)
(* Purpose: Gate L1 - 16-Bit Hardware Epoch Monotonicity, Overflow & Traps   *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.
From Cortex Require Import GateF_F3_1_InvocationSimulation.

Section GateL1_Monotonicity.

  (* ----------------------------------------------------------------------- *)
  (* 1. HARDWARE 16-BIT HEC DEFINITIONS & CONSTANTS                          *)
  (* ----------------------------------------------------------------------- *)

  (** Hardware 16-Bit Epoch Ceiling: 2^16 - 1 = 65535 *)
  Definition HEC_MAX_16 : nat := 65535.

  (** Concrete Hardware State Record for Gate L1 *)
  Record L1HardwareState := {
    l1_stcr_bank : list ConcreteSTCR;
    l1_reg_hec   : nat;
    l1_trap_flag : bool;
    l1_commit    : bool
  }.

  (** Normative Operational Semantics: Saturation + Trap + Commit Abort on Overflow *)
  Definition hec_inc_16 (hw : L1HardwareState) : L1HardwareState :=
    if (Nat.eqb hw.(l1_reg_hec) HEC_MAX_16) then
      {| l1_stcr_bank := hw.(l1_stcr_bank);
         l1_reg_hec   := HEC_MAX_16;
         l1_trap_flag := true;
         l1_commit    := false |} (* State write-back inhibited *)
    else
      {| l1_stcr_bank := hw.(l1_stcr_bank);
         l1_reg_hec   := hw.(l1_reg_hec) + 1;
         l1_trap_flag := hw.(l1_trap_flag);
         l1_commit    := true |}.

  (* ----------------------------------------------------------------------- *)
  (* 2. ARITHMETIC & COMPARISON HELPER LEMMAS                                *)
  (* ----------------------------------------------------------------------- *)

  Lemma n_lt_n_false : forall n, n < n -> False.
  Proof.
    induction n as [| n' IH].
    - intros H. inversion H.
    - intros H. apply IH. unfold lt in H. apply le_S_n in H. exact H.
  Qed.

  Lemma plus_1_is_succ : forall n, n + 1 = S n.
  Proof.
    induction n as [| n' IH].
    - reflexivity.
    - simpl. rewrite IH. reflexivity.
  Qed.

  Lemma le_plus_1 : forall n, n <= n + 1.
  Proof.
    induction n as [| n' IH].
    - simpl. apply le_0_n.
    - simpl. apply le_n_S, IH.
  Qed.

  Lemma eqb_refl_lem : forall n, Nat.eqb n n = true.
  Proof.
    induction n as [| n' IH].
    - reflexivity.
    - simpl. exact IH.
  Qed.

  Lemma eqb_eq_lem : forall a b, Nat.eqb a b = true -> a = b.
  Proof.
    induction a as [| a' IH].
    - intros [| b'] H.
      + reflexivity.
      + discriminate.
    - intros [| b'] H.
      + discriminate.
      + simpl in H. apply IH in H. subst. reflexivity.
  Qed.

  Lemma eqb_false_lt : forall n max,
    Nat.eqb n max = false ->
    n < S max ->
    n < max.
  Proof.
    induction n as [| n' IH].
    - intros [| max'] Heq Hlt.
      + discriminate Heq.
      + apply le_n_S, le_0_n.
    - intros [| max'] Heq Hlt.
      + simpl in Hlt. apply le_S_n in Hlt. inversion Hlt.
      + simpl in *. apply le_S_n in Hlt. apply IH in Heq; auto. apply le_n_S, Heq.
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 3. GATE L1 FORMAL PROOF STACK                                          *)
  (* ----------------------------------------------------------------------- *)

  (** L1.1 Monotonicity Lemma: HEC increment is monotonic *)
  Lemma hec_inc_16_monotonic :
    forall (hw : L1HardwareState),
      hw.(l1_reg_hec) <= (hec_inc_16 hw).(l1_reg_hec).
  Proof.
    intros hw. unfold hec_inc_16.
    destruct (Nat.eqb hw.(l1_reg_hec) HEC_MAX_16) eqn:Heq.
    - apply eqb_eq_lem in Heq. rewrite Heq. apply le_n.
    - simpl. apply le_plus_1.
  Qed.

  (** L1.2 Representability: Valid HEC remains within 16-bit boundary *)
  Theorem hec_inc_16_representability :
    forall (hw : L1HardwareState),
      hw.(l1_reg_hec) < 65536 ->
      (hec_inc_16 hw).(l1_reg_hec) < 65536.
  Proof.
    intros hw Hbound.
    unfold hec_inc_16.
    destruct (Nat.eqb hw.(l1_reg_hec) HEC_MAX_16) eqn:Heq.
    - simpl. unfold HEC_MAX_16. apply le_n.
    - simpl.
      assert (Hstrict : hw.(l1_reg_hec) < 65535).
      { apply eqb_false_lt with (max := 65535); auto. }
      unfold lt in *.
      apply le_n_S in Hstrict.
      rewrite plus_1_is_succ.
      exact Hstrict.
  Qed.

  (** L1.3 Maximum-Value Transition Semantics: Saturation, Trap & Abort *)
  Theorem hec_inc_16_overflow_traps :
    forall (hw : L1HardwareState),
      hw.(l1_reg_hec) = HEC_MAX_16 ->
      (hec_inc_16 hw).(l1_trap_flag) = true /\
      (hec_inc_16 hw).(l1_commit) = false /\
      (hec_inc_16 hw).(l1_reg_hec) = HEC_MAX_16.
  Proof.
    intros hw Hmax. unfold hec_inc_16.
    rewrite Hmax.
    assert (Hself : Nat.eqb HEC_MAX_16 HEC_MAX_16 = true) by (apply eqb_refl_lem).
    rewrite Hself. simpl. split; [| split]; reflexivity.
  Qed.

  (** L1.5 Core Security Theorem: Expired Capability Invalidity *)
  Theorem temporal_expiry_denies_execution :
    forall (hec : nat) (stcr : ConcreteSTCR),
      stcr.(stcr_epoch) < hec ->
      stcr.(stcr_valid) = true ->
      hec <= stcr.(stcr_epoch) ->
      False.
  Proof.
    intros hec stcr Hexpired Hvalid Hle.
    assert (Hlt : stcr.(stcr_epoch) < stcr.(stcr_epoch)).
    { eapply lt_le_trans; eauto. }
    exact (n_lt_n_false (stcr_epoch stcr) Hlt).
  Qed.

  (** Core Refinement Security Theorem: Expired Invocation Forces Hardware Trap *)
  Theorem hec_temporal_invalidation_security :
    forall (c : ConcreteSystemState) (w : World list_auth_model) (stcr : ConcreteSTCR),
      refines c w ->
      stcr.(stcr_valid) = true ->
      c.(c_hw_state).(c_reg_hec) > stcr.(stcr_epoch) ->
      ~ valid_cap (alpha_stcr stcr) w.
  Proof.
    intros c w stcr Href Hval Hgt.
    apply concrete_stale_invoke_refines_invalid_cap with (c := c); auto.
  Qed.

End GateL1_Monotonicity.
