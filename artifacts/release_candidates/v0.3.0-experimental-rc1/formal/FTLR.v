From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import LogicalRelation.
Require Import RelationClasses.
Require Import Relation_Definitions.

(* ================================================================= *
   MODULE: FTLR.v
   ================================================================= *)

Section FTLR.
  Context {A : AuthorityModel}.

  (* Dynamic substitution map: implements direct, executable variable evaluation *)
  Fixpoint subst_env (γ : nat -> Expr) (e : Expr) : Expr :=
    match e with
    | e_var x    => γ x
    | e_val n    => e_val n
    | e_invoke c => e_invoke c
    | e_fork e1  => e_fork (subst_env γ e1)
    end.

  (* Deep-Embedded Static Typing Architecture *)
  Inductive typing : list Ty -> Expr -> Ty -> Prop :=
    | T_Var : forall Γ x t,
        lookup x Γ = Some t ->
        typing Γ (e_var x) t
    | T_Val : forall Γ n,
        typing Γ (e_val n) TInt
    | T_Invoke : forall Γ c,
        typing Γ (e_invoke c) TCap
    | T_Fork : forall Γ e,
        typing Γ e TUnit ->
        typing Γ (e_fork e) TUnit.

  (* Semantic Translation Invariant *)
  Definition semantic_typing (Γ : list Ty) (e : Expr) (t : Ty) : Prop :=
    forall (w : World A) (γ : nat -> Expr) (σ : State),
      env_valid w Γ γ ->
      E_w t w (σ, subst_env γ e).

  (* Mechanized Proof of the Fundamental Theorem of Logical Relations *)
  Theorem fundamental_theorem (Γ : list Ty) (e : Expr) (t : Ty) :
    typing Γ e t -> semantic_typing Γ e t.
  Proof.
    intros Htype.
    induction Htype; red; intros w γ σ Henv; red; intros w' m m' eff cfg' Hstep.
    - (* Case 1: T_Var *)
      simpl in Hstep.
      assert (Hval := Henv x t H).
      destruct t; simpl in *.
      { rewrite Hval in Hstep. inversion Hstep. }
      { destruct Hval as [n Hval]. rewrite Hval in Hstep. inversion Hstep. }
      { destruct Hval as [[c [Hval Hvc]] | Hval].
        { rewrite Hval in Hstep. inversion Hstep; subst; simpl in *.
          { left. exists c. split; [reflexivity | assumption]. }
          { right. reflexivity. } }
        { rewrite Hval in Hstep. inversion Hstep. } }
    - (* Case 2: T_Val *)
      simpl in Hstep. inversion Hstep.
    - (* Case 3: T_Invoke *)
      simpl in Hstep.
      inversion Hstep; subst; simpl in *.
      { left. exists c. split; [reflexivity | assumption]. }
      { right. reflexivity. }
    - (* Case 4: T_Fork *)
      simpl in Hstep. inversion Hstep.
  Qed.

End FTLR.
