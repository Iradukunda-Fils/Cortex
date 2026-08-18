From Cortex Require Import AuthorityModel.
From Cortex Require Import World.

(* ================================================================= *
   MODULE: Semantics.v
   ================================================================= *)

Section Semantics.
  Context {A : AuthorityModel}.

  Inductive Effect :=
    | eff_idle  : Effect
    | eff_write : nat -> Effect.

  Inductive Expr :=
    | e_var    : nat -> Expr
    | e_val    : nat -> Expr
    | e_invoke : Capability -> Expr
    | e_fork   : Expr -> Expr.

  Definition State := nat -> nat.

  Record MonState := mkMonState {
    mon_active_epoch : nat;
  }.

  (* 
     Strict Spatiotemporal Transition Step:
     Successful fresh execution generates side effects but leaves the capability intact.
  *)
  Inductive step_m : World A -> MonState -> (State * Expr) -> 
                     Effect -> World A -> MonState -> (State * Expr) -> Prop :=
    | step_m_invoke_fresh : forall w w' m σ c,
        world_accessible w w' ->
        world_fuel w' < world_fuel w ->
        valid_cap c w' ->
        step_m w m (σ, e_invoke c) (eff_write (cap_id c)) w' m (σ, e_invoke c)
        
    | step_m_invoke_stale : forall w w' m σ c,
        world_accessible w w' ->
        world_fuel w' < world_fuel w ->
        ~ (valid_cap c w') ->
        step_m w m (σ, e_invoke c) eff_idle w' m (σ, e_val 0).

  (* Concrete Unmonitored Transition Semantics tracking the same world transition *)
  Inductive step : World A -> MonState -> (State * Expr) -> 
                   Effect -> World A -> MonState -> (State * Expr) -> Prop :=
    | step_internal : forall w m σ e,
        step w m (σ, e) eff_idle w m (σ, e)
    | step_external : forall w w' m σ c,
        world_accessible w w' ->
        world_fuel w' < world_fuel w ->
        step w m (σ, e_invoke c) (eff_write (cap_id c)) w' m (σ, e_invoke c).

  Definition Epoch_Consistent_Complete_Mediation :=
    forall w m cfg eff w' m' cfg',
      step w m cfg eff w' m' cfg' ->
      eff = eff_idle \/ step_m w m cfg eff w' m' cfg'.

End Semantics.
