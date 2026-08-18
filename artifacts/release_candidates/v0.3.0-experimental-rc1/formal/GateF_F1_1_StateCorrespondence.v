(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: GateF_F1_1_StateCorrespondence.v                                 *)
(* Purpose: Milestone F1.1 - Concrete State to Canonical World.v Mapping    *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import GateF_F0_ModelReconciliation.

Section GateF1_1.

  (* ----------------------------------------------------------------------- *)
  (* 1. CONCRETE REPRESENTATION STRUCTURES                                   *)
  (* ----------------------------------------------------------------------- *)

  (** [CONCRETE REPRESENTATION] Single Hardware Spatiotemporal Capability Register (STCR) *)
  Record ConcreteSTCR := {
    stcr_valid          : bool;
    stcr_authority_mask : nat;  (* 15-bit hardware mask [62:48] *)
    stcr_base_addr      : nat;  (* 32-bit base address [47:16] *)
    stcr_epoch          : nat;  (* 16-bit epoch ceiling [15:0] *)
    stcr_id             : nat   (* 5-bit STCR slot index [25:21] *)
  }.

  Fixpoint stcr_in (stcr : ConcreteSTCR) (bank : list ConcreteSTCR) : Prop :=
    match bank with
    | nil => False
    | cons s rest => (stcr.(stcr_id) = s.(stcr_id) /\ stcr.(stcr_epoch) = s.(stcr_epoch) /\ s.(stcr_valid) = true) \/ stcr_in stcr rest
    end.

  (** [CONCRETE REPRESENTATION] Physical RTL Hardware State *)
  Record HardwareState := {
    c_stcr_bank : list ConcreteSTCR;
    c_reg_hec   : nat;         (* Current HEC counter value *)
    c_eff_trap  : bool
  }.

  (** [CONCRETE REPRESENTATION] Rust Supervisor & Platform Runtime State *)
  Record RuntimeState := {
    c_active_tokens   : list nat;
    c_supervisor_pid  : nat;
    c_audit_chain_head: nat
  }.

  (** [CONCRETE REPRESENTATION] Unified Concrete System State *)
  Record ConcreteSystemState := {
    c_hw_state : HardwareState;
    c_rt_state : RuntimeState
  }.

  (* ----------------------------------------------------------------------- *)
  (* 2. HARDWARE INVARIANTS & REPRESENTATION BOUNDS                          *)
  (* ----------------------------------------------------------------------- *)

  (** [REFINEMENT DEFINITION] Correct Hardware Validity Invariant:
      Capability traps if HEC > stcr_epoch (i.e. valid requires c_reg_hec <= stcr_epoch) *)
  Definition stcr_epoch_valid (hec : nat) (stcr : ConcreteSTCR) : Prop :=
    stcr.(stcr_valid) = true -> hec <= stcr.(stcr_epoch).

  (** [REFINEMENT DEFINITION] 15-bit STCR Mask Representability *)
  Definition stcr_mask_representable (mask : nat) : Prop := mask < 32768.

  (** [REFINEMENT DEFINITION] 16-bit Instruction Immediate Representability *)
  Definition imm_mask_representable (imm : nat) : Prop := imm < 65536.

  (** [REFINEMENT DEFINITION] Hardware Well-Formedness *)
  Definition hardware_well_formed (hw : HardwareState) : Prop :=
    forall stcr, stcr_in stcr hw.(c_stcr_bank) ->
      (stcr.(stcr_valid) = true -> hw.(c_reg_hec) <= stcr.(stcr_epoch)) /\ stcr_mask_representable stcr.(stcr_authority_mask).

  (** [REFINEMENT DEFINITION] Unified Concrete Well-Formedness *)
  Definition concrete_well_formed (c : ConcreteSystemState) : Prop :=
    hardware_well_formed c.(c_hw_state).

  (* ----------------------------------------------------------------------- *)
  (* 3. ABSTRACTION PROJECTIONS & RELATIONAL REFINEMENT R(C, W)             *)
  (* ----------------------------------------------------------------------- *)

  (** Projection: STCR to Canonical Formal Capability *)
  Definition alpha_stcr (stcr : ConcreteSTCR) : Capability :=
    {| cap_id        := stcr.(stcr_id);
       cap_max_epoch := stcr.(stcr_epoch) |}.

  (** Projection: Hardware STCR Bank to Canonical Authority Carrier *)
  Fixpoint alpha_stcr_bank (bank : list ConcreteSTCR) : list_auth_carrier :=
    match bank with
    | nil => nil
    | cons stcr rest =>
        if stcr.(stcr_valid)
        then cons (alpha_stcr stcr) (alpha_stcr_bank rest)
        else alpha_stcr_bank rest
    end.

  (** [REFINEMENT DEFINITION] Relational Refinement R(C, W) against Canonical World *)
  Definition refines (c : ConcreteSystemState) (w : World list_auth_model) : Prop :=
    concrete_well_formed c /\
    world_epoch w = c.(c_hw_state).(c_reg_hec) /\
    world_lambda w = alpha_stcr_bank c.(c_hw_state).(c_stcr_bank).

  (* ----------------------------------------------------------------------- *)
  (* 4. CORE CORRESPONDENCE THEOREMS                                         *)
  (* ----------------------------------------------------------------------- *)

  Lemma alpha_stcr_bank_in :
    forall bank stcr,
      stcr_in stcr bank ->
      stcr.(stcr_valid) = true ->
      list_in (alpha_stcr stcr) (alpha_stcr_bank bank).
  Proof.
    induction bank as [| s rest IH].
    - intros stcr Hin Hv. destruct Hin.
    - intros stcr Hin Hv. destruct Hin as [[Hid [Hep Hvalid_s]] | Hin_rest].
      + simpl. rewrite Hvalid_s. simpl. left. unfold alpha_stcr. simpl. split; auto.
      + simpl. destruct (stcr_valid s) eqn:Hs_v.
        * simpl. right. apply IH; auto.
        * apply IH; auto.
  Qed.

  (** Theorem 1: Valid Concrete STCR Map to Valid Canonical Capabilities *)
  Theorem valid_stcr_maps_to_valid_cap :
    forall (c : ConcreteSystemState) (w : World list_auth_model) (stcr : ConcreteSTCR),
      refines c w ->
      stcr_in stcr c.(c_hw_state).(c_stcr_bank) ->
      stcr.(stcr_valid) = true ->
      valid_cap (alpha_stcr stcr) w.
  Proof.
    intros c w stcr [Hwf [Hepoch Hlambda]] Hin Hvalid.
    unfold valid_cap. split.
    - rewrite Hlambda. unfold auth_contains, list_auth_model, list_auth_contains.
      apply alpha_stcr_bank_in; auto.
    - rewrite Hepoch.
      unfold concrete_well_formed, hardware_well_formed in Hwf.
      specialize (Hwf stcr Hin).
      destruct Hwf as [Hepoch_v _].
      apply Hepoch_v, Hvalid.
  Qed.

End GateF1_1.
