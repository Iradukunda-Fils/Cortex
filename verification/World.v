Require Import RelationClasses.
Require Import Relation_Definitions.
From Cortex Require Import AuthorityModel.

(* ================================================================= *
   MODULE: World.v
   ================================================================= *)

Record World (A : AuthorityModel) := mkWorld {
  world_lambda  : auth_carrier;
  world_monitor : nat; 
  world_fuel    : nat;
  world_epoch   : nat;
}.

Arguments world_lambda {A}.
Arguments world_monitor {A}.
Arguments world_fuel {A}.
Arguments world_epoch {A}.

Definition world_accessible {A : AuthorityModel} (w1 w2 : World A) : Prop :=
  auth_preorder (world_lambda w2) (world_lambda w1) /\ 
  (world_monitor w1 <= world_monitor w2) /\ 
  (world_fuel w2 <= world_fuel w1) /\
  (world_epoch w2 >= world_epoch w1).

Definition valid_cap {A : AuthorityModel} (c : Capability) (w : World A) : Prop :=
  auth_contains (world_lambda w) c /\ world_epoch w <= cap_max_epoch c.

Lemma le_trans : forall n m p, n <= m -> m <= p -> n <= p.
Proof.
  intros n m p Hnm Hmp.
  induction Hmp.
  - assumption.
  - apply le_S. assumption.
Qed.

Lemma lt_le_trans : forall n m p, n < m -> m <= p -> n < p.
Proof.
  intros n m p Hlt Hle.
  induction Hle.
  - exact Hlt.
  - apply le_S. exact IHHle.
Qed.

Instance world_accessible_preorder {A : AuthorityModel} : PreOrder (@world_accessible A).
Proof.
  constructor.
  - intros [λ m f e]; red; simpl.
    destruct auth_preorder_rel as [Hl_refl _].
    repeat split; try apply Hl_refl; apply le_n.
  - intros [λ1 m1 f1 e1] [λ2 m2 f2 e2] [λ3 m3 f3 e3].
    intros [Hλ12 [Hm12 [Hf12 He12]]] [Hλ23 [Hm23 [Hf23 He23]]]; red; simpl in *.
    destruct auth_preorder_rel as [_ Hl_trans].
    repeat split.
    + eapply Hl_trans; eauto.
    + eapply le_trans; eauto.
    + eapply le_trans; eauto.
    + eapply le_trans; eauto.
Qed.

Lemma valid_cap_monotone {A : AuthorityModel} (c : Capability) (w1 w2 : World A) :
  world_accessible w1 w2 ->
  valid_cap c w2 ->
  valid_cap c w1.
Proof.
  intros [Hauth [Hmon [Hfuel Hep]]] [Hcontains Hfresh].
  split.
  - eapply auth_contains_monotone; eauto.
  - eapply le_trans.
    + eapply Hep.
    + eapply Hfresh.
Qed.
