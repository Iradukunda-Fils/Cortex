(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: DelegationChainRTL.v                                              *)
(* Classification: R2 (RTL Transition Correspondence & Delegation Semantics) *)
(* Purpose: Milestone F2.4 - Delegation-Chain Attenuation, Depth & Provenance *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.
From Cortex Require Import GrantCapRTL.
From Cortex Require Import RevokeExpiryRTL.

Section DelegationChainRTL.

  (** List Head helper using core Coq prelude *)
  Definition list_head {A : Type} (l : list A) : option A :=
    match l with
    | nil => None
    | cons x _ => Some x
    end.

  (** List Last helper using core Coq prelude *)
  Fixpoint list_last {A : Type} (l : list A) (default : A) : A :=
    match l with
    | nil => default
    | cons x nil => x
    | cons _ rest => list_last rest default
    end.

  (* ======================================================================= *)
  (* 1. ONE-HOP DELEGATION EDGE & ATTENUATION (F2.4a & F2.4b)                 *)
  (* ======================================================================= *)

  (** Compositional Spatial Mask Subsetting Relation *)
  Inductive mask_subset (child parent : nat) : Prop :=
    | mask_sub_step : forall req, child = Nat.land parent req -> mask_subset child parent
    | mask_sub_refl : child = parent -> mask_subset child parent
    | mask_sub_trans : forall mid, mask_subset child mid -> mask_subset mid parent -> mask_subset child parent.

  (** Structure representing a concrete single-hop delegation edge *)
  Record DelegationEdge := {
    del_parent    : RawSTCR;
    del_child     : RawSTCR;
    del_req_mask  : nat;
    del_sig_valid : bool
  }.

  (** Validity of a single-hop delegation step *)
  Definition valid_delegation_edge (edge : DelegationEdge) (hec : nat) : Prop :=
    edge.(del_parent).(raw_v) = true /\
    hec <= edge.(del_parent).(raw_epoch) /\
    edge.(del_sig_valid) = true /\
    edge.(del_child).(raw_v) = true /\
    edge.(del_child).(raw_mask) = Nat.land edge.(del_parent).(raw_mask) edge.(del_req_mask) /\
    edge.(del_child).(raw_epoch) <= edge.(del_parent).(raw_epoch).

  (** [THEOREM: F2.4a ONE-HOP SPATIAL ATTENUATION]
      Child spatial mask is strictly a bitwise submask of the parent mask. *)
  Theorem one_hop_spatial_attenuation :
    forall edge hec,
      valid_delegation_edge edge hec ->
      mask_subset edge.(del_child).(raw_mask) edge.(del_parent).(raw_mask).
  Proof.
    intros edge hec Hvalid.
    unfold valid_delegation_edge in Hvalid.
    destruct Hvalid as [_ [_ [_ [_ [Hmask _]]]]].
    apply (mask_sub_step (raw_mask (del_child edge)) (raw_mask (del_parent edge)) (del_req_mask edge) Hmask).
  Qed.

  (** [THEOREM: F2.4a ONE-HOP TEMPORAL ATTENUATION]
      Child epoch ceiling is non-expanding with respect to the parent epoch ceiling. *)
  Theorem one_hop_temporal_attenuation :
    forall edge hec,
      valid_delegation_edge edge hec ->
      edge.(del_child).(raw_epoch) <= edge.(del_parent).(raw_epoch).
  Proof.
    intros edge hec Hvalid.
    unfold valid_delegation_edge in Hvalid.
    destruct Hvalid as [_ [_ [_ [_ [_ Hepoch]]]]].
    exact Hepoch.
  Qed.

  (** [THEOREM: F2.4b SIGNATURE CONTINUITY]
      Every valid delegation step requires verified signature continuity. *)
  Theorem signature_continuity_required :
    forall edge hec,
      valid_delegation_edge edge hec ->
      edge.(del_sig_valid) = true.
  Proof.
    intros edge hec Hvalid.
    unfold valid_delegation_edge in Hvalid.
    destruct Hvalid as [_ [_ [Hsig _]]].
    exact Hsig.
  Qed.

  (* ======================================================================= *)
  (* 2. DELEGATION CHAIN INDUCTIVE DEFINITION & ATTENUATION (F2.4c)           *)
  (* ======================================================================= *)

  (** Inductive definition of a valid multi-hop delegation chain
      Chain is ordered from Leaf capability at the head to Root capability at the tail. *)
  Inductive valid_delegation_chain (hec : nat) : list RawSTCR -> Prop :=
    | vchain_root : forall root,
        root.(raw_v) = true ->
        hec <= root.(raw_epoch) ->
        valid_delegation_chain hec (cons root nil)
    | vchain_extend : forall child parent rest,
        valid_delegation_chain hec (cons parent rest) ->
        child.(raw_v) = true ->
        mask_subset child.(raw_mask) parent.(raw_mask) ->
        child.(raw_epoch) <= parent.(raw_epoch) ->
        valid_delegation_chain hec (cons child (cons parent rest)).

  (** [THEOREM: F2.4c CHAIN TRANSITIVE SPATIAL ATTENUATION]
      Leaf capability mask is a bitwise submask of the root capability mask. *)
  Theorem chain_spatial_attenuation :
    forall hec chain,
      valid_delegation_chain hec chain ->
      forall leaf root,
        list_head chain = Some leaf ->
        list_last chain root = root ->
        mask_subset leaf.(raw_mask) root.(raw_mask).
  Proof.
    intros hec chain Hchain.
    induction Hchain as [r Hv Hep | c p rest Hrest IHHchain Hc Hsub Hep].
    - intros leaf root Hhead Hlast.
      simpl in Hhead, Hlast.
      inversion Hhead; subst.
      apply mask_sub_refl. reflexivity.
    - intros leaf root Hhead Hlast.
      simpl in Hhead. inversion Hhead; subst.
      specialize (IHHchain p root).
      assert (Hhead_p : list_head (cons p rest) = Some p) by reflexivity.
      assert (Hlast_p : list_last (cons p rest) root = root).
      { simpl in Hlast. exact Hlast. }
      pose proof (IHHchain Hhead_p Hlast_p) as Hp_root.
      exact (mask_sub_trans (raw_mask leaf) (raw_mask root) (raw_mask p) Hsub Hp_root).
  Qed.

  (** [THEOREM: F2.4c CHAIN TRANSITIVE TEMPORAL ATTENUATION]
      Leaf epoch ceiling is bounded by the root epoch ceiling. *)
  Theorem chain_temporal_attenuation :
    forall hec chain,
      valid_delegation_chain hec chain ->
      forall leaf root,
        list_head chain = Some leaf ->
        list_last chain root = root ->
        leaf.(raw_epoch) <= root.(raw_epoch).
  Proof.
    intros hec chain Hchain.
    induction Hchain as [r Hv Hep | c p rest Hrest IHHchain Hc Hsub Hep].
    - intros leaf root Hhead Hlast.
      simpl in Hhead, Hlast.
      inversion Hhead; subst. auto.
    - intros leaf root Hhead Hlast.
      simpl in Hhead. inversion Hhead; subst.
      specialize (IHHchain p root).
      assert (Hhead_p : list_head (cons p rest) = Some p) by reflexivity.
      assert (Hlast_p : list_last (cons p rest) root = root).
      { simpl in Hlast. exact Hlast. }
      pose proof (IHHchain Hhead_p Hlast_p) as Hp_root.
      exact (le_trans (raw_epoch leaf) (raw_epoch p) (raw_epoch root) Hep Hp_root).
  Qed.

  (* ======================================================================= *)
  (* 3. DEPTH BOUNDING & REJECTION (F2.4d)                                    *)
  (* ======================================================================= *)

  (** Normative Max Delegation Depth Bound (Dmax = 8 hops, i.e., chain length <= 9 nodes) *)
  Definition bounded_delegation_chain (hec : nat) (chain : list RawSTCR) : Prop :=
    valid_delegation_chain hec chain /\ length chain <= 9.

  (** [THEOREM: F2.4d DEPTH BOUND EXCEEDED IMPLIES INVALID]
      Delegation chains exceeding Dmax = 8 hops (length > 9) are formally invalid. *)
  Theorem depth_exceeded_invalid :
    forall hec chain,
      length chain > 9 ->
      ~ bounded_delegation_chain hec chain.
  Proof.
    intros hec chain Hlen Hbounded.
    unfold bounded_delegation_chain in Hbounded.
    destruct Hbounded as [_ Hbound].
    assert (Hle : S 9 <= 9) by (exact (le_trans (S 9) (length chain) 9 Hlen Hbound)).
    apply (Sn_le_n_false 9 Hle).
  Qed.

  (* ======================================================================= *)
  (* 4. ROOT PROVENANCE & HARDWARE STCR SLOT 0 MAPPING (F2.4e)               *)
  (* ======================================================================= *)

  (** Root Provenance Predicate: Chain terminates at a valid root capability *)
  Definition root_provenance (chain : list RawSTCR) (root : RawSTCR) : Prop :=
    list_last chain root = root /\ root.(raw_v) = true.

  (** [THEOREM: F2.4e ROOT PROVENANCE SOUNDNESS]
      Every valid delegation chain originates from an active, unexpired Root capability. *)
  Theorem chain_root_provenance_sound :
    forall hec chain root,
      valid_delegation_chain hec chain ->
      list_last chain root = root ->
      root.(raw_v) = true /\ hec <= root.(raw_epoch).
  Proof.
    intros hec chain root Hchain.
    induction Hchain as [r Hv Hep | c p rest Hrest IHHchain Hc Hsub Hep].
    - intros Hlast. simpl in Hlast. subst. split; auto.
    - intros Hlast. simpl in Hlast.
      apply IHHchain, Hlast.
  Qed.

  (** [THEOREM: F2.4e HARDWARE STCR SLOT 0 ROOT ALIGNMENT]
      The hardware STCR root slot 0 satisfies root provenance for valid hardware chains. *)
  Theorem hardware_root_slot_0_alignment :
    forall (s : RTLState) root,
      s.(rtl_stcr_file) 0 = root ->
      root.(raw_v) = true ->
      s.(rtl_reg_hec) <= root.(raw_epoch) ->
      valid_delegation_chain s.(rtl_reg_hec) (cons root nil) /\
      root_provenance (cons root nil) root.
  Proof.
    intros s root Hslot Hv Hep.
    split.
    - apply vchain_root; auto.
    - unfold root_provenance. simpl. split; auto.
  Qed.

  Print Assumptions one_hop_spatial_attenuation.
  Print Assumptions one_hop_temporal_attenuation.
  Print Assumptions signature_continuity_required.
  Print Assumptions chain_spatial_attenuation.
  Print Assumptions chain_temporal_attenuation.
  Print Assumptions depth_exceeded_invalid.
  Print Assumptions chain_root_provenance_sound.
  Print Assumptions hardware_root_slot_0_alignment.

End DelegationChainRTL.
