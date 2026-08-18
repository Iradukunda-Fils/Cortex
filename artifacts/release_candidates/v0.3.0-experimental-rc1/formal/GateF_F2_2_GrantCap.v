(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: GateF_F2_2_GrantCap.v                                            *)
(* Purpose: Milestone F2.2 - Hardware Gate L2 RTL Opcode 0x02 Audit          *)
(* ========================================================================= *)

From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.
From Cortex Require Import GateF_F2_1_RestrictCap.

Section GateF2_2.

  (* ----------------------------------------------------------------------- *)
  (* 1. RTL OPCODE 0x02 (grant_cap) HARDWARE TRANSITION MODEL                *)
  (* ----------------------------------------------------------------------- *)

  (** [CONCRETE REPRESENTATION] Concrete grant_cap Transition (Reflecting RTL Opcode 0x02 line 177)
      ex_result_val = {1'b1, imm16[14:0], ex_stcr_base, reg_hec} *)
  Definition concrete_grant_cap (parent_stcr : ConcreteSTCR) (hec : nat) (imm16 : nat) (child_id : nat) : ConcreteSTCR :=
    {| stcr_valid          := true;
       stcr_authority_mask := Nat.land parent_stcr.(stcr_authority_mask) imm16;
       stcr_base_addr      := parent_stcr.(stcr_base_addr);
       stcr_epoch          := hec; (* Assigned from current HEC per RTL line 179 *)
       stcr_id             := child_id |}.

  (* ----------------------------------------------------------------------- *)
  (* 2. THEOREMS & RTL CORRESPONDENCE AUDIT PROOFS                           *)
  (* ----------------------------------------------------------------------- *)

  (** Theorem 1: Derived Capability Preserves Spatial Monotonicity *)
  Theorem grant_cap_spatial_non_expansion :
    forall (parent_stcr : ConcreteSTCR) (hec imm16 child_id : nat),
      authority_subset (concrete_grant_cap parent_stcr hec imm16 child_id).(stcr_authority_mask) parent_stcr.(stcr_authority_mask).
  Proof.
    intros parent_stcr hec imm16 child_id.
    unfold concrete_grant_cap, authority_subset.
    simpl.
    exists imm16.
    reflexivity.
  Qed.

  (** Theorem 2: Derived Capability Epoch Equals Current HEC (Temporal Monotonicity) *)
  Theorem grant_cap_epoch_equals_hec :
    forall (parent_stcr : ConcreteSTCR) (hec imm16 child_id : nat),
      (concrete_grant_cap parent_stcr hec imm16 child_id).(stcr_epoch) = hec.
  Proof.
    intros parent_stcr hec imm16 child_id.
    unfold concrete_grant_cap.
    simpl. reflexivity.
  Qed.

  (** Theorem 3: Derived Capability Inherits Validity at Current HEC *)
  Theorem grant_cap_valid_at_current_hec :
    forall (parent_stcr : ConcreteSTCR) (hec imm16 child_id : nat),
      stcr_epoch_valid hec (concrete_grant_cap parent_stcr hec imm16 child_id).
  Proof.
    intros parent_stcr hec imm16 child_id.
    unfold stcr_epoch_valid, concrete_grant_cap.
    simpl. intros _. apply le_n.
  Qed.

End GateF2_2.
