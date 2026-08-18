(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: GateF_F4c_VerifierSpec.v                                         *)
(* Classification: R3b / Phase 3 (Verifier Implementation Bridge)           *)
(* Purpose: Formalize the decision procedure for evidence verification and  *)
(*          establish the specification against which cortex_verifier.py     *)
(*          must be shown equivalent.                                       *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.
From Cortex Require Import ValidInvocationRTL.
From Cortex Require Import EndToEndRefinementRTL.
From Cortex Require Import GateF_F4_EvidenceRefinement.
From Cortex Require Import GateF_F4b_ConcreteCryptoRefinement.

Section GateF4c_VerifierSpec.

  (* ======================================================================= *)
  (* 1. EVIDENCE BUNDLE DOMAIN DEFINITION                                      *)
  (* ======================================================================= *)

  (** An EvidenceBundle is the complete input to the verifier decision procedure.
      It contains a concrete witness chain (sequence of witness states),
      the associated commit events and signed intents, and the claimed
      initial witness state. *)
  Record EvidenceBundle := {
    eb_witness_chain : list ConcreteWitnessState;
    eb_events        : list CommitEvent;
    eb_intents       : list SignedIntent;
    eb_initial       : ConcreteWitnessState
  }.

  (* ======================================================================= *)
  (* 2. VERIFIER VERDICT DOMAIN (TRIPARTITE CLASSIFICATION)                    *)
  (* ======================================================================= *)

  (** The formal verifier returns one of three verdicts.
      This matches the EvidenceStatus type in GateF_F4_EvidenceRefinement.v
      and the return codes of cortex_verifier.py. *)
  Inductive FormalVerdict :=
    | VERDICT_VALID         (* All witness chain links verified *)
    | VERDICT_INVALID       (* At least one link failed verification *)
    | VERDICT_MALFORMED.    (* Input does not satisfy well-formedness *)

  (* ======================================================================= *)
  (* 3. LIST EQUALITY DECISION (SELF-CONTAINED)                                *)
  (* ======================================================================= *)

  (** Decidable equality for nat — self-contained, no stdlib dependency *)
  Fixpoint nat_beq (a b : nat) : bool :=
    match a, b with
    | O, O => true
    | S a', S b' => nat_beq a' b'
    | _, _ => false
    end.

  Lemma nat_beq_refl : forall n, nat_beq n n = true.
  Proof.
    induction n; simpl; [reflexivity | exact IHn].
  Qed.

  Lemma nat_beq_sound : forall a b, nat_beq a b = true -> a = b.
  Proof.
    induction a; destruct b; simpl; intro H;
      try discriminate; [reflexivity | f_equal; apply IHa; exact H].
  Qed.

  (** Decidable equality for byte lists (hash comparison) *)
  Fixpoint nat_list_eq (l1 l2 : list Byte) : bool :=
    match l1, l2 with
    | nil, nil => true
    | cons a rest1, cons b rest2 =>
      if nat_beq a b then nat_list_eq rest1 rest2 else false
    | _, _ => false
    end.

  (** [LEMMA: nat_list_eq IS SOUND]
      When nat_list_eq returns true, the lists are indeed equal. *)
  Lemma nat_list_eq_sound :
    forall (l1 l2 : list Byte),
      nat_list_eq l1 l2 = true -> l1 = l2.
  Proof.
    induction l1 as [| a rest1 IH]; intros l2 H.
    - destruct l2; [reflexivity | discriminate].
    - destruct l2 as [| b rest2]; [discriminate |].
      simpl in H.
      destruct (nat_beq a b) eqn:Hab; [| discriminate].
      apply nat_beq_sound in Hab. subst b.
      f_equal. apply IH. exact H.
  Qed.

  (** [LEMMA: nat_list_eq IS COMPLETE]
      Equal lists always produce true. *)
  Lemma nat_list_eq_complete :
    forall (l : list Byte),
      nat_list_eq l l = true.
  Proof.
    induction l as [| a rest IH]; simpl.
    - reflexivity.
    - rewrite nat_beq_refl. exact IH.
  Qed.

  (* ======================================================================= *)
  (* 4. SINGLE-LINK VERIFICATION PREDICATE                                     *)
  (* ======================================================================= *)

  (** Verify a single witness chain link:
      Given a prior witness state, a commit event, and a signed intent,
      check that the next witness state was correctly computed.

      Uses concrete field comparison — no recursive parent-pointer traversal.
      OBS-C compliant: O(1) stack per link. *)
  Definition verify_witness_link
      (w_prev w_next : ConcreteWitnessState)
      (e : CommitEvent)
      (i : SignedIntent) : bool :=
    let expected := compute_next_concrete_witness w_prev e i in
    andb (nat_list_eq (cw_hash w_next) (cw_hash expected))
    (andb (nat_list_eq (cw_parent w_next) (cw_parent expected))
          (nat_beq (cw_seq w_next) (cw_seq expected))).

  (* ======================================================================= *)
  (* 5. ITERATIVE CHAIN VERIFICATION (OBS-C COMPLIANT)                         *)
  (* ======================================================================= *)

  (** Iterative witness chain verification.
      Structurally recursive on the zipped list triple.

      OBS-C compliance: This uses structural recursion on a list,
      which corresponds to a simple for-loop in extracted code.
      The Python verifier MUST implement this as an explicit loop,
      NOT as recursive parent-pointer graph traversal, to guarantee
      O(1) stack memory scaling under adversarial fuzzing. *)
  Fixpoint verify_chain_links
      (w_prev : ConcreteWitnessState)
      (chain : list ConcreteWitnessState)
      (events : list CommitEvent)
      (intents : list SignedIntent) : bool :=
    match chain, events, intents with
    | nil, nil, nil => true
    | cons w_next chain_rest, cons e events_rest, cons i intents_rest =>
      if verify_witness_link w_prev w_next e i then
        verify_chain_links w_next chain_rest events_rest intents_rest
      else
        false
    | _, _, _ => false
    end.

  (* ======================================================================= *)
  (* 6. FORMAL VERIFIER DECISION PROCEDURE                                     *)
  (* ======================================================================= *)

  (** Helper: nat equality as bool — reuse nat_beq *)
  Definition nat_eqb (a b : nat) : bool := nat_beq a b.

  (** [DEFINITION: FORMAL VERIFIER SPECIFICATION]
      The complete decision procedure that cortex_verifier.py must match.
      For all evidence bundles E in the supported domain D:
        FormalVerify(E) = cortex_verifier.py(E)                          *)
  Definition formal_verify (eb : EvidenceBundle) : FormalVerdict :=
    match eb_witness_chain eb with
    | nil => VERDICT_MALFORMED
    | _ =>
      if nat_eqb (length (eb_events eb)) (length (eb_witness_chain eb)) then
        if nat_eqb (length (eb_intents eb)) (length (eb_witness_chain eb)) then
          if verify_chain_links (eb_initial eb)
                                (eb_witness_chain eb)
                                (eb_events eb)
                                (eb_intents eb) then
            VERDICT_VALID
          else
            VERDICT_INVALID
        else
          VERDICT_MALFORMED
      else
        VERDICT_MALFORMED
    end.

  (* ======================================================================= *)
  (* 7. FORMAL VERIFIER SOUNDNESS PROPERTIES                                   *)
  (* ======================================================================= *)

  (** [THEOREM: SINGLE-LINK VERIFICATION SOUNDNESS]
      If verify_witness_link returns true, then the claimed next witness
      state has identical hash, parent, and sequence to the computed one. *)
  Theorem verify_witness_link_sound :
    forall (w_prev w_next : ConcreteWitnessState)
           (e : CommitEvent) (i : SignedIntent),
      verify_witness_link w_prev w_next e i = true ->
      cw_hash w_next = cw_hash (compute_next_concrete_witness w_prev e i) /\
      cw_parent w_next = cw_parent (compute_next_concrete_witness w_prev e i) /\
      cw_seq w_next = cw_seq (compute_next_concrete_witness w_prev e i).
  Proof.
    intros w_prev w_next e i Hverify.
    unfold verify_witness_link in Hverify.
    apply andb_prop in Hverify.
    destruct Hverify as [Hhash Hrest].
    apply andb_prop in Hrest.
    destruct Hrest as [Hparent Hseq].
    split.
    - apply nat_list_eq_sound. exact Hhash.
    - split.
      + apply nat_list_eq_sound. exact Hparent.
      + apply nat_beq_sound. exact Hseq.
  Qed.

  (** [THEOREM: FORMAL VERIFIER REJECTS EMPTY CHAINS]
      An empty witness chain always yields VERDICT_MALFORMED. *)
  Theorem formal_verify_rejects_empty :
    forall (eb : EvidenceBundle),
      eb_witness_chain eb = nil ->
      formal_verify eb = VERDICT_MALFORMED.
  Proof.
    intros eb Hempty.
    unfold formal_verify.
    rewrite Hempty. reflexivity.
  Qed.

  (** [THEOREM: VALID VERDICT IMPLIES CHAIN INTEGRITY]
      If the formal verifier returns VERDICT_VALID, then the iterative
      chain verification predicate holds. *)
  Theorem formal_verify_valid_implies_chain :
    forall (eb : EvidenceBundle),
      formal_verify eb = VERDICT_VALID ->
      verify_chain_links (eb_initial eb)
                          (eb_witness_chain eb)
                          (eb_events eb)
                          (eb_intents eb) = true.
  Proof.
    intros eb Hvalid.
    unfold formal_verify in Hvalid.
    destruct (eb_witness_chain eb) eqn:Hchain; [discriminate |].
    unfold nat_eqb in Hvalid.
    destruct (nat_beq (length (eb_events eb)) (length (c :: l))); [| discriminate].
    destruct (nat_beq (length (eb_intents eb)) (length (c :: l))); [| discriminate].
    destruct (verify_chain_links (eb_initial eb) (c :: l) (eb_events eb) (eb_intents eb)) eqn:Hverify;
      [reflexivity | discriminate].
  Qed.

  (* ======================================================================= *)
  (* 8. ASSUMPTION AUDIT                                                       *)
  (* ======================================================================= *)

  Print Assumptions nat_list_eq_sound.
  Print Assumptions nat_list_eq_complete.
  Print Assumptions verify_witness_link_sound.
  Print Assumptions formal_verify_rejects_empty.
  Print Assumptions formal_verify_valid_implies_chain.

End GateF4c_VerifierSpec.
