(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: GateF_F3_1_InvocationSimulation.v                                *)
(* Purpose: Milestone F3.1 - Valid & Stale Invocation Refinement Simulation *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.
From Cortex Require Import GateF_F2_1_RestrictCap.
From Cortex Require Import GateF_F2_2_GrantCap.

Section GateF3_1.

  (* ----------------------------------------------------------------------- *)
  (* 1. INVOCATION REFINEMENT THEOREMS AGAINST CANONICAL SEMANTICS.V         *)
  (* ----------------------------------------------------------------------- *)

  Lemma n_lt_n_false : forall n, n < n -> False.
  Proof.
    induction n as [| n' IH].
    - intros H. inversion H.
    - intros H. apply IH. unfold lt in H. apply le_S_n in H. exact H.
  Qed.

  (** Theorem 1: Fresh Invocation Guard Pass Refines Canonical valid_cap *)
  Theorem concrete_fresh_invoke_refines_valid_cap :
    forall (c : ConcreteSystemState) (w : World list_auth_model) (stcr : ConcreteSTCR),
      refines c w ->
      stcr_in stcr c.(c_hw_state).(c_stcr_bank) ->
      stcr.(stcr_valid) = true ->
      valid_cap (alpha_stcr stcr) w.
  Proof.
    intros c w stcr Href Hin Hvalid.
    eapply valid_stcr_maps_to_valid_cap; eauto.
  Qed.

  (** Theorem 2: Stale / Expired Invocation Trap Refines ~ (valid_cap c w) *)
  Theorem concrete_stale_invoke_refines_invalid_cap :
    forall (c : ConcreteSystemState) (w : World list_auth_model) (stcr : ConcreteSTCR),
      refines c w ->
      stcr.(stcr_valid) = true ->
      c.(c_hw_state).(c_reg_hec) > stcr.(stcr_epoch) ->
      ~ valid_cap (alpha_stcr stcr) w.
  Proof.
    intros c w stcr [_ [Hepoch _]] Hvalid Hgt Hcap_valid.
    unfold valid_cap in Hcap_valid.
    destruct Hcap_valid as [_ Hep].
    simpl in Hep. rewrite <- Hepoch in Hgt.
    unfold gt in Hgt.
    apply n_lt_n_false with (n := stcr_epoch stcr).
    eapply lt_le_trans; eauto.
  Qed.

End GateF3_1.
