From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import LogicalRelation.
From Cortex Require Import FTLR.
Require Import RelationClasses.
Require Import Relation_Definitions.

(* ================================================================= *
   MODULE: Soundness.v (Final Composition & Verification Loop)
   ================================================================= *)

Section Soundness.
  Context {A : AuthorityModel}.

  (* Spatiotemporal Provenance Typing Witness for Effects: ⊢_ν eff *)
  Inductive effect_provenance : Effect -> Prop :=
    | P_Idle  : effect_provenance eff_idle
    | P_Write : forall id, effect_provenance (eff_write id).

  (* The Final Mechanized Synthesis *)
  Theorem unified_soundness :
    forall (Γ : list Ty) (e : Expr) (t : Ty) (w w' : World A) 
           (σ : State) (γ : nat -> Expr) (eff : Effect) 
           (cfg' : State * Expr) (m m' : MonState),
      typing Γ e t ->
      env_valid w Γ γ ->
      Epoch_Consistent_Complete_Mediation ->
      step w m (σ, subst_env γ e) eff w' m' cfg' ->
      eff <> eff_idle ->
      effect_provenance eff /\ V_w t w' (snd cfg').
  Proof.
    intros Γ e t w w' σ γ eff cfg' m m' Htype Henv Hmediation Hstep Hnon_idle.
    
    (* Stage 1: Complete Mediation Reduction *)
    destruct (Hmediation w m (σ, subst_env γ e) eff w' m' cfg' Hstep) as [Hidle | Hstep_m].
    { (* Stage 2: Idle Contradiction Elimination *)
      subst. contradiction. }
    
    (* Stage 3: FTLR Instantiation *)
    assert (Hftl : semantic_typing Γ e t) by (apply fundamental_theorem; assumption).
    specialize (Hftl w γ σ Henv).
    
    (* Stage 4: Monitored-Step Inversion & Value Extraction *)
    assert (Hsound : V_w t w' (snd cfg')).
    { eapply Hftl; eauto. }
    
    split.
    - (* Extract effect provenance profile from operational syntax *)
      inversion Hstep_m; subst.
      + apply P_Write.
      + contradiction.
    - assumption.
  Qed.

End Soundness.
