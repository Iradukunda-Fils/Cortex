(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: Phase4GatewayConcrete.v (Issue #32)                               *)
(* Classification: Tier D (Formal Proof / Concrete Gateway Bridge)           *)
(*                                                                            *)
(* Scope: Formal Concrete Transition System C_Gateway,formal modeling         *)
(*   Python Gateway Control Plane (router.py, lease.py, ledger.py),          *)
(*   including single-lock atomic revalidation, TOCTOU fencing,              *)
(*   state domain conflict locking, durable recovery state classification,   *)
(*   abstraction map alpha_Gateway, and Universal Forward Simulation          *)
(*   Refinement Theorem R_Phase4(C, A).                                       *)
(*                                                                            *)
(* Assurance Boundary: Zero Axioms, Zero Admits.                              *)
(* ========================================================================= *)

Require Import Cortex.Phase4RoutingRefinement.

Section Phase4GatewayConcrete.

  (* ========================================================================= *)
  (* 1. CONCRETE GATEWAY STATE MODEL (Matching router.py / lease.py / ledger.py)*)
  (* ========================================================================= *)

  Record ConcreteWorkerRef := mkConcreteWorker {
    cw_id                   : nat;
    cw_gen                  : nat;
    cw_hash                 : nat;
    cw_profile              : SandboxProfileId;
    cw_sandbox_hash         : nat;
    cw_cap_hash             : nat;
    cw_stage                : LifecycleStage;
    cw_inflight             : nat;
    cw_limit                : nat;
    cw_n_caps               : nat;
  }.

  Record ConcreteInvocationRecord := mkConcreteInvocation {
    ci_id                   : nat;
    ci_target_gen           : nat;
    ci_target_hash          : nat;
    ci_profile              : SandboxProfileId;
    ci_sandbox_hash         : nat;
    ci_cap_hash             : nat;
    ci_domain_key           : StateDomainKey;
    ci_n_req_caps           : nat;
    ci_recovery_bucket      : RecoveryBucket;
  }.

  Record ConcreteGatewayState := mkConcreteGateway {
    cgs_workers             : list ConcreteWorkerRef;
    cgs_invocations         : list ConcreteInvocationRecord;
    cgs_queue_depth         : nat;
    cgs_max_queue_depth     : nat;
    cgs_active_domains      : list StateDomainKey;
    cgs_active_leases       : list (nat * nat); (* (invocation_id, lease_epoch) *)
  }.

  (* ========================================================================= *)
  (* 2. CONCRETE HELPER FUNCTIONS                                              *)
  (* ========================================================================= *)

  Definition concrete_worker_ready (w : ConcreteWorkerRef) : bool :=
    match cw_stage w with
    | LS_READY => true
    | _ => false
    end.

  Definition concrete_revalidate (w : ConcreteWorkerRef) (i : ConcreteInvocationRecord) (max_inflight : nat) : bool :=
    andb (concrete_worker_ready w)
    (andb (Nat.eqb (cw_gen w) (ci_target_gen i))
    (andb (Nat.eqb (cw_hash w) (ci_target_hash i))
    (andb (Nat.eqb (cw_profile w) (ci_profile i))
    (andb (Nat.eqb (cw_sandbox_hash w) (ci_sandbox_hash i))
    (andb (Nat.eqb (cw_cap_hash w) (ci_cap_hash i))
    (andb (caps_contained (ci_n_req_caps i) (cw_n_caps w))
          (Nat.ltb (cw_inflight w) max_inflight))))))).

  Fixpoint concrete_domain_locked (d : StateDomainKey) (l : list StateDomainKey) : bool :=
    match l with
    | nil => false
    | cons x xs => if Nat.eqb d x then true else concrete_domain_locked d xs
    end.

  Fixpoint remove_domain_lock (target : StateDomainKey) (l : list StateDomainKey) : list StateDomainKey :=
    match l with
    | nil => nil
    | cons x xs => if Nat.eqb target x then xs else cons x (remove_domain_lock target xs)
    end.

  (* ========================================================================= *)
  (* 3. CONCRETE GATEWAY OPERATIONAL TRANSITIONS (C_Gateway,formal)            *)
  (* ========================================================================= *)

  Inductive ConcreteGatewayOp : Type :=
  | CGOpEnqueue             (i : ConcreteInvocationRecord)
  | CGOpAtomicRevalidateGrant(w : ConcreteWorkerRef) (i : ConcreteInvocationRecord) (epoch : nat)
  | CGOpRejectQueueFull     (i : ConcreteInvocationRecord)
  | CGOpRejectTOCTOUStale   (w : ConcreteWorkerRef) (i : ConcreteInvocationRecord)
  | CGOpRejectDomainConflict(i : ConcreteInvocationRecord)
  | CGOpReleaseDomain       (target_domain : StateDomainKey)
  | CGOpClassifyRecovery    (i_id : nat) (bucket : RecoveryBucket).

  Inductive ConcreteGatewayStep : ConcreteGatewayState -> ConcreteGatewayOp -> ConcreteGatewayState -> Prop :=
  (* Successful Enqueue *)
  | CGStepEnqueue : forall (c : ConcreteGatewayState) (i : ConcreteInvocationRecord),
      cgs_queue_depth c < cgs_max_queue_depth c ->
      ConcreteGatewayStep c (CGOpEnqueue i)
        (mkConcreteGateway
           (cgs_workers c)
           (cons i (cgs_invocations c))
           (S (cgs_queue_depth c))
           (cgs_max_queue_depth c)
           (cgs_active_domains c)
           (cgs_active_leases c))

  (* Single-Lock Atomic Revalidation & Lease Grant (Linearization Point) *)
  | CGStepAtomicRevalidateGrant : forall (c : ConcreteGatewayState) (w : ConcreteWorkerRef) (i : ConcreteInvocationRecord) (epoch : nat),
      concrete_revalidate w i (cw_limit w) = true ->
      concrete_domain_locked (ci_domain_key i) (cgs_active_domains c) = false ->
      cgs_queue_depth c > 0 ->
      ConcreteGatewayStep c (CGOpAtomicRevalidateGrant w i epoch)
        (mkConcreteGateway
           (cgs_workers c)
           (cgs_invocations c)
           (pred (cgs_queue_depth c))
           (cgs_max_queue_depth c)
           (cons (ci_domain_key i) (cgs_active_domains c))
           (cons (ci_id i, epoch) (cgs_active_leases c)))

  (* Rejection: Queue Full *)
  | CGStepRejectQueueFull : forall (c : ConcreteGatewayState) (i : ConcreteInvocationRecord),
      cgs_queue_depth c >= cgs_max_queue_depth c ->
      ConcreteGatewayStep c (CGOpRejectQueueFull i) c

  (* Rejection: TOCTOU Revalidation Mismatch (Stale Candidate) *)
  | CGStepRejectTOCTOUStale : forall (c : ConcreteGatewayState) (w : ConcreteWorkerRef) (i : ConcreteInvocationRecord),
      concrete_revalidate w i (cw_limit w) = false ->
      ConcreteGatewayStep c (CGOpRejectTOCTOUStale w i) c

  (* Rejection: State Domain Conflict *)
  | CGStepRejectDomainConflict : forall (c : ConcreteGatewayState) (i : ConcreteInvocationRecord),
      concrete_domain_locked (ci_domain_key i) (cgs_active_domains c) = true ->
      ConcreteGatewayStep c (CGOpRejectDomainConflict i) c

  (* Domain Lock Release *)
  | CGStepReleaseDomain : forall (c : ConcreteGatewayState) (target_domain : StateDomainKey),
      ConcreteGatewayStep c (CGOpReleaseDomain target_domain)
        (mkConcreteGateway
           (cgs_workers c)
           (cgs_invocations c)
           (cgs_queue_depth c)
           (cgs_max_queue_depth c)
           (remove_domain_lock target_domain (cgs_active_domains c))
           (cgs_active_leases c))

  (* Classify Recovery *)
  | CGStepClassifyRecovery : forall (c : ConcreteGatewayState) (i_id : nat) (bucket : RecoveryBucket),
      ConcreteGatewayStep c (CGOpClassifyRecovery i_id bucket) c.

  (* ========================================================================= *)
  (* 4. CANONICAL ABSTRACTION MAP alpha_Gateway                                 *)
  (* ========================================================================= *)

  Definition alpha_worker (cw : ConcreteWorkerRef) : WorkerReplica :=
    mkWorker
      (cw_id cw)
      (cw_gen cw)
      (cw_hash cw)
      (cw_profile cw)
      (cw_sandbox_hash cw)
      (cw_cap_hash cw)
      (cw_stage cw)
      (cw_inflight cw)
      (cw_limit cw)
      (cw_n_caps cw).

  Definition alpha_invocation (ci : ConcreteInvocationRecord) : InvocationRequest :=
    mkInvocation
      (ci_id ci)
      (ci_target_gen ci)
      (ci_target_hash ci)
      (ci_profile ci)
      (ci_sandbox_hash ci)
      (ci_cap_hash ci)
      (ci_domain_key ci)
      (ci_n_req_caps ci).

  Definition alpha_gateway_state (c : ConcreteGatewayState) : GatewayState :=
    mkGateway
      (cgs_queue_depth c)
      (cgs_max_queue_depth c)
      (cgs_active_domains c).

  (* ========================================================================= *)
  (* 5. EQUIVALENCE LEMMAS                                                     *)
  (* ========================================================================= *)

  Lemma concrete_revalidate_equals_hard_constraints : forall (w : ConcreteWorkerRef) (i : ConcreteInvocationRecord),
    concrete_revalidate w i (cw_limit w) = HardConstraints (alpha_worker w) (alpha_invocation i).
  Proof.
    intros w i.
    unfold concrete_revalidate, HardConstraints, alpha_worker, alpha_invocation, concrete_worker_ready, lifecycle_ready.
    simpl. destruct (cw_stage w); reflexivity.
  Qed.

  Lemma concrete_domain_locked_equals_abstract : forall (d : StateDomainKey) (l : list StateDomainKey),
    concrete_domain_locked d l = domain_locked d l.
  Proof.
    intros d l.
    induction l as [| x xs IH]; [reflexivity |].
    simpl. destruct (Nat.eqb d x); [reflexivity | exact IH].
  Qed.

  (* ========================================================================= *)
  (* 6. UNIVERSAL GATEWAY FORWARD SIMULATION REFINEMENT THEOREM (Issue #32)     *)
  (* ========================================================================= *)

  Inductive AbstractGatewayOp : Type :=
  | AGOpEnqueue
  | AGOpGrantLease (w : WorkerReplica) (i : InvocationRequest)
  | AGOpReleaseDomain (target : StateDomainKey)
  | AGOpStutter.

  Inductive AbstractGatewayStep : GatewayState -> AbstractGatewayOp -> GatewayState -> Prop :=
  | AGStepEnqueue : forall (g : GatewayState),
      g_queue_depth g < g_max_queue_depth g ->
      AbstractGatewayStep g AGOpEnqueue
        (mkGateway (S (g_queue_depth g)) (g_max_queue_depth g) (g_active_domains g))

  | AGStepGrantLease : forall (g : GatewayState) (w : WorkerReplica) (i : InvocationRequest),
      GrantLeaseCondition g w i = true ->
      g_queue_depth g > 0 ->
      AbstractGatewayStep g (AGOpGrantLease w i)
        (mkGateway (pred (g_queue_depth g)) (g_max_queue_depth g) (cons (i_domain_key i) (g_active_domains g)))

  | AGStepReleaseDomain : forall (g : GatewayState) (target : StateDomainKey),
      AbstractGatewayStep g (AGOpReleaseDomain target)
        (mkGateway (g_queue_depth g) (g_max_queue_depth g) (remove_domain_lock target (g_active_domains g)))

  | AGStepStutter : forall (g : GatewayState),
      AbstractGatewayStep g AGOpStutter g.

  Inductive AbstractGatewayMultistep : GatewayState -> list AbstractGatewayOp -> GatewayState -> Prop :=
  | AGMultistepNil : forall (g : GatewayState),
      AbstractGatewayMultistep g nil g
  | AGMultistepCons : forall (g : GatewayState) (op : AbstractGatewayOp) (g' : GatewayState) (ops : list AbstractGatewayOp) (g'' : GatewayState),
      AbstractGatewayStep g op g' ->
      AbstractGatewayMultistep g' ops g'' ->
      AbstractGatewayMultistep g (cons op ops) g''.

  Definition RefinementRelationPhase4 (c : ConcreteGatewayState) (a : GatewayState) : Prop :=
    alpha_gateway_state c = a.

  Theorem universal_gateway_forward_simulation :
    forall (c c' : ConcreteGatewayState) (op : ConcreteGatewayOp) (a : GatewayState),
      RefinementRelationPhase4 c a ->
      ConcreteGatewayStep c op c' ->
      exists (ops : list AbstractGatewayOp) (a' : GatewayState),
        AbstractGatewayMultistep a ops a' /\
        RefinementRelationPhase4 c' a'.
  Proof.
    intros c c' op a Href Hcstep.
    unfold RefinementRelationPhase4 in Href. subst a.
    destruct Hcstep.

    - (* CGStepEnqueue *)
      set (a_next := mkGateway (S (cgs_queue_depth c)) (cgs_max_queue_depth c) (cgs_active_domains c)).
      assert (Hstep : AbstractGatewayStep (alpha_gateway_state c) AGOpEnqueue a_next).
      {
        apply AGStepEnqueue. exact H.
      }
      exists (cons AGOpEnqueue nil), a_next.
      split.
      + apply AGMultistepCons with (g' := a_next); [exact Hstep | apply AGMultistepNil].
      + unfold RefinementRelationPhase4, alpha_gateway_state. simpl. reflexivity.

    - (* CGStepAtomicRevalidateGrant *)
      set (w_abs := alpha_worker w).
      set (i_abs := alpha_invocation i).
      set (a_next := mkGateway (pred (cgs_queue_depth c)) (cgs_max_queue_depth c) (cons (i_domain_key i_abs) (cgs_active_domains c))).
      assert (Hgrant : GrantLeaseCondition (alpha_gateway_state c) w_abs i_abs = true).
      {
        unfold GrantLeaseCondition, w_abs, i_abs.
        rewrite <- concrete_revalidate_equals_hard_constraints.
        rewrite H.
        simpl.
        rewrite <- concrete_domain_locked_equals_abstract.
        rewrite H0.
        reflexivity.
      }
      assert (Hstep : AbstractGatewayStep (alpha_gateway_state c) (AGOpGrantLease w_abs i_abs) a_next).
      {
        apply AGStepGrantLease.
        - exact Hgrant.
        - exact H1.
      }
      exists (cons (AGOpGrantLease w_abs i_abs) nil), a_next.
      split.
      + apply AGMultistepCons with (g' := a_next); [exact Hstep | apply AGMultistepNil].
      + unfold RefinementRelationPhase4, alpha_gateway_state. simpl. reflexivity.

    - (* CGStepRejectQueueFull (Stuttering Transition) *)
      exists (cons AGOpStutter nil), (alpha_gateway_state c).
      split.
      + apply AGMultistepCons with (g' := alpha_gateway_state c).
        * apply AGStepStutter.
        * apply AGMultistepNil.
      + unfold RefinementRelationPhase4. reflexivity.

    - (* CGStepRejectTOCTOUStale (Stuttering Transition) *)
      exists (cons AGOpStutter nil), (alpha_gateway_state c).
      split.
      + apply AGMultistepCons with (g' := alpha_gateway_state c).
        * apply AGStepStutter.
        * apply AGMultistepNil.
      + unfold RefinementRelationPhase4. reflexivity.

    - (* CGStepRejectDomainConflict (Stuttering Transition) *)
      exists (cons AGOpStutter nil), (alpha_gateway_state c).
      split.
      + apply AGMultistepCons with (g' := alpha_gateway_state c).
        * apply AGStepStutter.
        * apply AGMultistepNil.
      + unfold RefinementRelationPhase4. reflexivity.

    - (* CGStepReleaseDomain *)
      set (a_next := mkGateway (cgs_queue_depth c) (cgs_max_queue_depth c) (remove_domain_lock target_domain (cgs_active_domains c))).
      assert (Hstep : AbstractGatewayStep (alpha_gateway_state c) (AGOpReleaseDomain target_domain) a_next).
      {
        apply AGStepReleaseDomain.
      }
      exists (cons (AGOpReleaseDomain target_domain) nil), a_next.
      split.
      + apply AGMultistepCons with (g' := a_next); [exact Hstep | apply AGMultistepNil].
      + unfold RefinementRelationPhase4, alpha_gateway_state. simpl. reflexivity.

    - (* CGStepClassifyRecovery (Stuttering Transition) *)
      exists (cons AGOpStutter nil), (alpha_gateway_state c).
      split.
      + apply AGMultistepCons with (g' := alpha_gateway_state c).
        * apply AGStepStutter.
        * apply AGMultistepNil.
      + unfold RefinementRelationPhase4. reflexivity.
  Qed.

End Phase4GatewayConcrete.
