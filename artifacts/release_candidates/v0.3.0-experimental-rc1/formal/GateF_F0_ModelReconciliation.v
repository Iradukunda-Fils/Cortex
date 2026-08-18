(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: GateF_F0_ModelReconciliation.v                                   *)
(* Purpose: Milestone F0 - Canonical Model Reconciliation & Type Guardrails *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.

Section GateF0.

  (** Architectural Rule: Gate F must not invent parallel semantic types.
      All formal authority and world structures must reuse canonical Coq types
      from AuthorityModel.v, World.v, and Semantics.v. *)

  (** Sample List-Based Authority Model Instance [EXISTING FORMAL / INSTANTIATION] *)
  Definition list_auth_carrier := list Capability.

  Fixpoint list_in (c : Capability) (l : list Capability) : Prop :=
    match l with
    | nil => False
    | cons c' rest => (cap_id c = cap_id c' /\ cap_max_epoch c = cap_max_epoch c') \/ list_in c rest
    end.

  Fixpoint list_app (l1 l2 : list Capability) : list Capability :=
    match l1 with
    | nil => l2
    | cons a rest => cons a (list_app rest l2)
    end.

  Definition list_auth_preorder (l1 l2 : list_auth_carrier) : Prop :=
    forall c, list_in c l1 -> list_in c l2.

  Definition list_auth_op (l1 l2 : list_auth_carrier) : list_auth_carrier :=
    list_app l1 l2.

  Definition list_auth_unit : list_auth_carrier := nil.

  Definition list_auth_contains (l : list_auth_carrier) (c : Capability) : Prop :=
    list_in c l.

  Lemma list_auth_preorder_is_preorder : RelationClasses.PreOrder list_auth_preorder.
  Proof.
    constructor.
    - intros l c H; exact H.
    - intros l1 l2 l3 H12 H23 c H1. apply H23, H12, H1.
  Qed.

  Lemma list_app_in_or :
    forall x z c, list_in c (list_app x z) -> list_in c x \/ list_in c z.
  Proof.
    induction x as [| a rest IH].
    - intros z c H. right. exact H.
    - intros z c H. simpl in H. destruct H as [Hhead | Htail].
      + left. simpl. left. exact Hhead.
      + apply IH in Htail. destruct Htail as [H1 | H2].
        * left. simpl. right. exact H1.
        * right. exact H2.
  Qed.

  Lemma list_app_in_intro :
    forall x z c, list_in c x \/ list_in c z -> list_in c (list_app x z).
  Proof.
    induction x as [| a rest IH].
    - intros z c [H1 | H2].
      + destruct H1.
      + exact H2.
    - intros z c [H1 | H2].
      + simpl in H1. destruct H1 as [Hhead | Htail].
        * simpl. left. exact Hhead.
        * simpl. right. apply IH. left. exact Htail.
      + simpl. right. apply IH. right. exact H2.
  Qed.

  Lemma list_auth_op_monotone :
    forall x y z : list_auth_carrier,
      list_auth_preorder x y ->
      list_auth_preorder (list_auth_op x z) (list_auth_op y z).
  Proof.
    intros x y z H c Hin.
    unfold list_auth_op in *.
    apply list_app_in_intro.
    apply list_app_in_or in Hin.
    destruct Hin as [Hx | Hz].
    - left. apply H, Hx.
    - right. exact Hz.
  Qed.

  Lemma list_auth_contains_monotone_lem :
    forall x y c,
      list_auth_preorder x y ->
      list_auth_contains x c ->
      list_auth_contains y c.
  Proof.
    intros x y c H Hin. apply H, Hin.
  Qed.

  Instance list_auth_model : AuthorityModel := {|
    auth_carrier           := list_auth_carrier;
    auth_preorder          := list_auth_preorder;
    auth_op                := list_auth_op;
    auth_unit              := list_auth_unit;
    auth_contains          := list_auth_contains;
    auth_preorder_rel      := list_auth_preorder_is_preorder;
    auth_preorder_monotone := list_auth_op_monotone;
    auth_contains_monotone := list_auth_contains_monotone_lem
  |}.

End GateF0.
