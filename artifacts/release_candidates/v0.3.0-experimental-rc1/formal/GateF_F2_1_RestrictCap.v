(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: GateF_F2_1_RestrictCap.v                                         *)
(* Purpose: Milestone F2.1 - Proof of Attenuation Refinement (restrict_cap) *)
(* ========================================================================= *)

From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.

Section GateF2_1.

  (* ----------------------------------------------------------------------- *)
  (* 1. CONCRETE & FORMAL RESTRICTION DEFINITIONS                            *)
  (* ----------------------------------------------------------------------- *)

  (** [CONCRETE REPRESENTATION] Concrete Capability Restriction (RTL Opcode 0x03) *)
  Definition concrete_restrict_cap (stcr : ConcreteSTCR) (imm16 : nat) : ConcreteSTCR :=
    {| stcr_valid          := stcr.(stcr_valid);
       stcr_authority_mask := Nat.land stcr.(stcr_authority_mask) imm16;
       stcr_base_addr      := stcr.(stcr_base_addr);
       stcr_epoch          := stcr.(stcr_epoch);
       stcr_id             := stcr.(stcr_id) |}.

  (** [REFINEMENT DEFINITION] Spatial Bitmask Authority Subsetting *)
  Definition authority_subset (sub_mask parent_mask : nat) : Prop :=
    exists mask_constraint : nat, sub_mask = Nat.land parent_mask mask_constraint.

  (* ----------------------------------------------------------------------- *)
  (* 2. THEOREMS & ATTENUATION REFINEMENT PROOFS                             *)
  (* ----------------------------------------------------------------------- *)

  (** Theorem 1: Spatial Bitmask Attenuation Preserves P1 Monotonicity *)
  Theorem restrict_preserves_spatial_attenuation :
    forall (stcr : ConcreteSTCR) (imm16 : nat),
      authority_subset (concrete_restrict_cap stcr imm16).(stcr_authority_mask) stcr.(stcr_authority_mask).
  Proof.
    intros stcr imm16.
    unfold concrete_restrict_cap, authority_subset.
    simpl.
    exists imm16.
    reflexivity.
  Qed.

End GateF2_1.
