From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import LogicalRelation.
From Cortex Require Import FTLR.
Require Import RelationClasses.
Require Import Relation_Definitions.

Section Substitution.
  Context {A : AuthorityModel}.

  (* Self-contained comparison for index boundary detection *)
  Fixpoint ge_dec (x d : nat) : bool :=
    match d with
    | O => true
    | S d' =>
        match x with
        | O => false
        | S x' => ge_dec x' d'
        end
    end.

  (* 
     The Structural Core of Deep-Embedded Variable Shifting:
     Inserting a new type into a context requires shifting all subsequent 
     free De Bruijn indices to prevent variable capture.
  *)
  Fixpoint shift (d : nat) (e : Expr) : Expr :=
    match e with
    | e_var x    => if ge_dec x d then e_var (S x) else e_var x
    | e_val n    => e_val n
    | e_invoke c => e_invoke c
    | e_fork e1  => e_fork (shift d e1)
    end.

  (* 
     Required Structural Lemma for the Variable Case:
     Typing must be stable under context extension (weakening).
  *)
  Lemma context_weakening : forall Γ e t t_fresh,
    typing Γ e t ->
    typing (t_fresh :: Γ) (shift 0 e) t.
  Proof.
    intros Γ e t t_fresh Htype.
    induction Htype.
    - (* T_Var *)
      simpl.
      assert (Hge : ge_dec x 0 = true).
      { destruct x; simpl; reflexivity. }
      rewrite Hge.
      apply T_Var.
      simpl.
      exact H.
    - (* T_Val *)
      simpl. apply T_Val.
    - (* T_Invoke *)
      simpl. apply T_Invoke.
    - (* T_Fork *)
      simpl. apply T_Fork. apply IHHtype.
  Qed.

  (* 
     The Definitive Milestone: The Semantic Substitution Theorem
     Maps environmental validity directly to semantic execution safety.
  *)
  Theorem semantic_substitution_preserves_typing : 
    forall (Γ : list Ty) (γ : nat -> Expr) (e : Expr) (t : Ty) (w : World A),
      env_valid w Γ γ ->
      typing Γ e t ->
      E_w t w (fun x => x, subst_env γ e).
  Proof.
    intros Γ γ e t w Henv Htype.
    eapply fundamental_theorem; eauto.
  Qed.

End Substitution.
