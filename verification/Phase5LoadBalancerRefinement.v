(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: Phase5LoadBalancerRefinement.v  (Issue #46)                       *)
(* Classification: Tier D (Formal Proof / Architecture Critical)              *)
(*                                                                            *)
(* Assurance boundary:                                                        *)
(*   Phase 5 abstract transition system: MACHINE-CHECKED PROVEN.             *)
(*   Concrete Python implementation: RUNTIME-VERIFIED;                       *)
(*     CONCRETE-TO-FORMAL REFINEMENT PENDING (#47).                          *)
(*                                                                            *)
(* Scope: Phase 5 Load Balancer Abstract State, Transitions, Inductive Safety *)
(*   I1  Capacity Bounds       I2  Cache Consistency (trivial in abstract)   *)
(*   I3  Assignment Uniqueness  I4  Lease Epoch Consistency                   *)
(*   I5  Generation Binding     I7  Quarantine Containment                   *)
(*   I6  = corollary of I5 (generation completeness), proved separately      *)
(*                                                                            *)
(* Architectural notes:                                                       *)
(*   st_EA (authority epoch): Carried inert; deferred to #49 (TLA+).         *)
(*     Not read/written by any transition — prevents smuggling distributed-   *)
(*     consensus assumptions into the scheduler proof.                        *)
(*   st_EL: Grows monotonically (head-shadowed append-list). Observable       *)
(*     equivalence to Python's dict-based _lease_epoch_tracker must be        *)
(*     bridged explicitly in the #47 simulation relation — not a triviality.  *)
(*   Concurrency: Step is a sequential relation over one global StateA.       *)
(*     Safety depends on Python's self._lock wrapping full read-check-write   *)
(*     atomically. TOCTOU freedom is #49/TLA+ scope, not provable here.      *)
(*   SAssign guard: strict < (room for +1). SRegWorker guard: non-strict <=  *)
(*     (existing load fits). #47 must diff these against the Python operator. *)
(*                                                                            *)
(* Non-Scope: #47 (Simulation R), #48 (WAL), #49 (TLA+)                     *)
(* ========================================================================= *)

Section Phase5LoadBalancerRefinement.

  Definition WorkerId     := nat.
  Definition InvocationId := nat.
  Definition AttemptId    := nat.
  Definition Generation   := nat.
  Definition Epoch        := nat.

  Record WorkerNode := mkWorkerNode { w_max : nat; w_healthy : bool }.
  Record Attempt := mkAttempt {
    att_id : AttemptId; att_worker : WorkerId;
    att_gen : Generation; att_epoch : Epoch }.

  (* ==== NAT HELPERS ==== *)

  Lemma nat_eqb_refl : forall n, Nat.eqb n n = true.
  Proof. induction n; simpl; exact IHn || reflexivity. Qed.
  Lemma nat_eqb_eq : forall n m, Nat.eqb n m = true -> n = m.
  Proof.
    induction n; destruct m; simpl; try reflexivity; try discriminate.
    intros. f_equal. apply IHn. exact H.
  Qed.
  Lemma nat_eqb_neq : forall n m, n <> m -> Nat.eqb n m = false.
  Proof.
    induction n; destruct m; simpl; try reflexivity;
    try (intros []; reflexivity).
    intros H. apply IHn. intros E. apply H. f_equal. exact E.
  Qed.
  Lemma nat_eqb_sym : forall n m, Nat.eqb n m = Nat.eqb m n.
  Proof.
    induction n; destruct m; simpl; try reflexivity. apply IHn.
  Qed.
  Lemma Sn_le_m : forall n m, S n <= m -> n <= m.
  Proof.
    intros n m H.
    assert (Hle : n <= S n) by apply le_S, le_n.
    induction H. exact Hle. apply le_S. exact IHle.
  Qed.

  (* ==== STATE ==== *)

  (* st_EA is inert in this model; deferred to #49 (TLA+ distributed). *)
  Record StateA := mkStateA {
    st_W : list (WorkerId * WorkerNode);
    st_A : list (InvocationId * Attempt);
    st_EA : Epoch;
    st_EL : list (InvocationId * Epoch);
    st_G : list (WorkerId * Generation);
    st_Q : list InvocationId;
    st_D : nat }.

  (* ==== LOOKUPS ==== *)

  Fixpoint fW (w:WorkerId) l : option WorkerNode :=
    match l with nil => None | cons (k,v) xs =>
      if Nat.eqb w k then Some v else fW w xs end.
  Fixpoint fA (i:InvocationId) l : option Attempt :=
    match l with nil => None | cons (k,v) xs =>
      if Nat.eqb i k then Some v else fA i xs end.
  Fixpoint fE (i:InvocationId) l : option Epoch :=
    match l with nil => None | cons (k,v) xs =>
      if Nat.eqb i k then Some v else fE i xs end.
  Fixpoint fG (w:WorkerId) l : option Generation :=
    match l with nil => None | cons (k,v) xs =>
      if Nat.eqb w k then Some v else fG w xs end.
  Fixpoint inQ (i:InvocationId) q : bool :=
    match q with nil => false | cons x xs =>
      if Nat.eqb i x then true else inQ i xs end.
  Fixpoint cntW (w:WorkerId) (l : list (InvocationId * Attempt)) : nat :=
    match l with nil => 0 | cons (pair _ a) xs =>
      if Nat.eqb (att_worker a) w then S (cntW w xs) else cntW w xs end.
  Fixpoint unique_keys (l : list (InvocationId * Attempt)) : Prop :=
    match l with nil => True | cons (pair k _) xs =>
      fA k xs = None /\ unique_keys xs end.

  (* ==== CONSTRUCTIVE REMOVAL (Adversarial finding #3 fix) ==== *)

  (* remove_key removes the first occurrence of key i from an association list.
     Under unique_keys, "first" = "only". This is the constructive witness
     that proves SRelease's existential is always inhabited. *)
  Fixpoint remove_key (i : InvocationId) (l : list (InvocationId * Attempt))
      : list (InvocationId * Attempt) :=
    match l with
    | nil => nil
    | cons (pair k v) xs =>
        if Nat.eqb i k then xs
        else cons (pair k v) (remove_key i xs)
    end.

  Lemma remove_key_fA_none : forall ii l,
    unique_keys l -> fA ii (remove_key ii l) = None.
  Proof.
    intros ii l. induction l as [| [k v] xs IH]; simpl.
    - reflexivity.
    - intros [Hdup Huk]. destruct (Nat.eqb ii k) eqn:Eik.
      + apply nat_eqb_eq in Eik. subst k. exact Hdup.
      + simpl. rewrite Eik. apply IH. exact Huk.
  Qed.

  Lemma remove_key_fA_other : forall ii j l,
    Nat.eqb j ii = false -> fA j (remove_key ii l) = fA j l.
  Proof.
    intros ii j l Hneq. induction l as [| [k v] xs IH]; simpl.
    - reflexivity.
    - destruct (Nat.eqb ii k) eqn:Eik.
      + apply nat_eqb_eq in Eik. subst k. simpl. rewrite Hneq. reflexivity.
      + simpl. destruct (Nat.eqb j k); try reflexivity. apply IH.
  Qed.

  Lemma remove_key_unique : forall ii l,
    unique_keys l -> unique_keys (remove_key ii l).
  Proof.
    intros ii l. induction l as [| [k v] xs IH]; simpl.
    - intros H. exact H.
    - intros [Hdup Huk]. destruct (Nat.eqb ii k) eqn:Eik.
      + exact Huk.
      + simpl. split.
        * rewrite (remove_key_fA_other ii k xs).
          -- exact Hdup.
          -- rewrite nat_eqb_sym. exact Eik.
        * apply IH. exact Huk.
  Qed.

  (* FIX: unique_keys l is required as a hypothesis. Without it, a stale
     duplicate ii entry deeper in the list could carry a different value
     than the head occurrence that was removed. unique_keys rules this out:
     if j = ii, the tail can't contain a binding for ii at all
     (Hdup : fA ii xs = None), so fA ii xs = Some a2 is a contradiction. *)
  Lemma remove_key_back : forall ii j a2 l,
    unique_keys l ->
    fA j (remove_key ii l) = Some a2 -> fA j l = Some a2.
  Proof.
    intros ii j a2 l. induction l as [| [k v] xs IH]; simpl.
    - intros _ H. exact H.
    - intros [Hdup Huk]. destruct (Nat.eqb ii k) eqn:Eik.
      + apply nat_eqb_eq in Eik. subst k. intros H.
        destruct (Nat.eqb j ii) eqn:Eji.
        * apply nat_eqb_eq in Eji. subst j.
          rewrite H in Hdup. discriminate.
        * exact H.
      + simpl. destruct (Nat.eqb j k) eqn:Ejk.
        * intros H. exact H.
        * intros H. apply IH; assumption.
  Qed.

  Lemma remove_key_cnt_target : forall ii at_ l,
    unique_keys l ->
    fA ii l = Some at_ ->
    S (cntW (att_worker at_) (remove_key ii l)) =
      cntW (att_worker at_) l.
  Proof.
    intros ii at_ l. induction l as [| [k v] xs IH]; simpl.
    - intros _ H. discriminate.
    - intros [Hdup Huk]. destruct (Nat.eqb ii k) eqn:Eik.
      + intros H. apply nat_eqb_eq in Eik. subst k.
        injection H as <-. simpl. rewrite nat_eqb_refl. reflexivity.
      + intros H.
        destruct (Nat.eqb (att_worker v) (att_worker at_)) eqn:Ew; simpl;
          rewrite Ew.
        * f_equal. apply IH; assumption.
        * apply IH; assumption.
  Qed.

  (* Note: not_eq_sym flips w <> att_worker at_ to att_worker at_ <> w,
     matching nat_eqb_neq's argument order. This direction bug was caught
     in the adversarial review (finding #4, argument-order mismatch). *)
  Lemma remove_key_cnt_other : forall ii at_ w l,
    unique_keys l ->
    fA ii l = Some at_ ->
    w <> att_worker at_ ->
    cntW w (remove_key ii l) = cntW w l.
  Proof.
    intros ii at_ w l. induction l as [| [k v] xs IH]; simpl.
    - intros _ H _. discriminate.
    - intros [Hdup Huk] HfA Hneq. destruct (Nat.eqb ii k) eqn:Eik.
      + apply nat_eqb_eq in Eik. subst k.
        injection HfA as <-.
        simpl. rewrite (nat_eqb_neq _ _ (not_eq_sym Hneq)). reflexivity.
      + simpl.
        destruct (Nat.eqb (att_worker v) w) eqn:Ew.
        * f_equal. apply IH; assumption.
        * apply IH; assumption.
  Qed.

  (* ==== INVARIANTS ==== *)

  Definition I1 s := forall wi wn, fW wi (st_W s) = Some wn ->
    cntW wi (st_A s) <= w_max wn.

  (* I2: Structurally satisfied by the abstract representation; concrete
     capacity conservation remains a refinement obligation.

     In the abstract model, "active load" IS cntW (a pure list scan),
     making I2 trivially True by definition. In the concrete Python model,
     active_load is a cached integer field on WorkerNode (w_active_load).
     The #47 refinement relation must prove:
       w_active_load(concrete_w) = cntW w_id (abstract_assignments)
     CTR-04 demonstrates this is non-trivial in practice: a cached counter
     can silently drift from the ground-truth assignment map on any mutation
     path that forgets to decrement/increment the cached field. *)
  Definition I2 (s : StateA) : Prop := True.

  Definition I3 s := unique_keys (st_A s).
  Definition I4 s := forall ii a, fA ii (st_A s) = Some a ->
    fE ii (st_EL s) = Some (att_epoch a).
  Definition I5 s := forall ii a, fA ii (st_A s) = Some a ->
    fG (att_worker a) (st_G s) = Some (att_gen a).
  Definition I7 s := forall ii, inQ ii (st_Q s) = true ->
    fA ii (st_A s) = None.

  (* I6 is a strict corollary of I5; proved once, not duplicated per-case.
     Keeping it as a separate lemma makes it available to external consumers
     without requiring them to re-derive it from I5. *)
  Lemma I6_from_I5 : forall s, I5 s ->
    (forall ii a, fA ii (st_A s) = Some a ->
      exists g, fG (att_worker a) (st_G s) = Some g).
  Proof.
    intros s HI5 ii a Hfa. exists (att_gen a). exact (HI5 _ _ Hfa).
  Qed.

  Definition Inv s := I1 s /\ I2 s /\ I3 s /\ I4 s /\ I5 s /\ I7 s.

  (* Constructive existence: SRelease is always fireable when I3 holds.
     Proved here, before Step, so the obligation is visible and explicit. *)
  Lemma release_constructive : forall s ii at_,
    I3 s ->
    fA ii (st_A s) = Some at_ ->
    let na := remove_key ii (st_A s) in
    fA ii na = None /\
    (forall j, Nat.eqb j ii = false -> fA j na = fA j (st_A s)) /\
    unique_keys na /\
    (forall w, w = att_worker at_ ->
       S (cntW w na) = cntW w (st_A s)) /\
    (forall w, w <> att_worker at_ ->
       cntW w na = cntW w (st_A s)) /\
    (forall j a2, fA j na = Some a2 -> fA j (st_A s) = Some a2).
  Proof.
    intros s ii at_ HI3 HfA. unfold I3 in HI3. simpl.
    repeat split.
    - apply remove_key_fA_none. exact HI3.
    - intros j Hj. apply remove_key_fA_other. exact Hj.
    - apply remove_key_unique. exact HI3.
    - intros w Hw. subst w. apply remove_key_cnt_target; assumption.
    - intros w Hw. apply remove_key_cnt_other with at_; assumption.
    - intros j a2 Hfa. apply (remove_key_back ii j a2 (st_A s) HI3 Hfa).
  Qed.

  (* ==== INITIAL STATE ==== *)

  Definition Init : StateA := mkStateA nil nil 0 nil nil nil 0.
  Theorem init_inv : Inv Init.
  Proof.
    unfold Inv, I1, I2, I3, I4, I5, I7; simpl.
    repeat split; intros; try discriminate.
  Qed.

  (* ==== TRANSITIONS ==== *)

  Inductive Step : StateA -> StateA -> Prop :=
    | SAssign : forall s ii a wi wn gn,
        fW wi (st_W s) = Some wn ->
        cntW wi (st_A s) < w_max wn ->   (* strict < : room for +1 *)
        fA ii (st_A s) = None ->
        inQ ii (st_Q s) = false ->
        att_worker a = wi ->
        fG wi (st_G s) = Some gn ->
        att_gen a = gn ->
        (match fE ii (st_EL s) with Some pe => att_epoch a > pe | None => True end) ->
        Step s (mkStateA (st_W s) (cons (ii,a) (st_A s)) (st_EA s)
          (cons (ii, att_epoch a) (st_EL s)) (st_G s) (st_Q s) (S (st_D s)))
    | SRelease : forall s ii at_ na,
        fA ii (st_A s) = Some at_ ->
        fA ii na = None ->
        (forall j, Nat.eqb j ii = false -> fA j na = fA j (st_A s)) ->
        unique_keys na ->
        (forall w, w = att_worker at_ -> S (cntW w na) = cntW w (st_A s)) ->
        (forall w, w <> att_worker at_ -> cntW w na = cntW w (st_A s)) ->
        (forall j a2, fA j na = Some a2 -> fA j (st_A s) = Some a2) ->
        Step s (mkStateA (st_W s) na (st_EA s) (st_EL s)
          (st_G s) (st_Q s) (S (st_D s)))
    | SRegWorker : forall s wi gn wn,
        (forall ii a, fA ii (st_A s) = Some a ->
           att_worker a = wi -> att_gen a = gn) ->
        cntW wi (st_A s) <= w_max wn ->  (* non-strict <= : existing load fits *)
        Step s (mkStateA (cons (wi,wn) (st_W s)) (st_A s) (st_EA s)
          (st_EL s) (cons (wi,gn) (st_G s)) (st_Q s) (st_D s))
    | SQuarantine : forall s ii,
        fA ii (st_A s) = None ->
        Step s (mkStateA (st_W s) (st_A s) (st_EA s) (st_EL s)
          (st_G s) (cons ii (st_Q s)) (st_D s)).

  (* ==== STEP PRESERVATION ==== *)

  Theorem step_inv : forall s s', Inv s -> Step s s' -> Inv s'.
  Proof.
    intros s s' [pI1 [pI2 [pI3 [pI4 [pI5 pI7]]]]] HS.
    destruct HS as
      [ s ii a wi wn gn HfW Hcap HnoA HnoQ Haw Hfg Hag Hep
      | s ii at_ na HfA HnoA Hoth Huk Hcnt_s Hcnt_d Hback
      | s wi gn wn Hgen Hcap2
      | s ii HnoA ].

    (* ---- Case: SAssign ---- *)
    { unfold Inv; split; [|split; [|split; [|split; [|split]]]].
      - (* I1 *) unfold I1 in *; simpl; intros w2 w2n Hf2.
        simpl. destruct (Nat.eqb (att_worker a) w2) eqn:Ew.
        + apply nat_eqb_eq in Ew. rewrite Haw in Ew. subst w2.
          rewrite HfW in Hf2. injection Hf2 as <-. exact Hcap.
        + exact (pI1 _ _ Hf2).
      - (* I2 *) exact I.
      - (* I3 *) unfold I3 in *; simpl. exact (conj HnoA pI3).
      - (* I4 *) unfold I4. intros j a2.
        change (fA j (cons (ii, a) (st_A s)) = Some a2 ->
                fE j (cons (ii, att_epoch a) (st_EL s)) = Some (att_epoch a2)).
        unfold fA; fold fA. unfold fE; fold fE.
        destruct (Nat.eqb j ii) eqn:Ej; intros Hfa.
        + injection Hfa as <-. reflexivity.
        + exact (pI4 _ _ Hfa).
      - (* I5 *) unfold I5. intros j a2.
        change (fA j (cons (ii, a) (st_A s)) = Some a2 ->
                fG (att_worker a2) (st_G s) = Some (att_gen a2)).
        unfold fA; fold fA.
        destruct (Nat.eqb j ii) eqn:Ej; intros Hfa.
        + injection Hfa as <-. rewrite Haw, Hag. exact Hfg.
        + exact (pI5 _ _ Hfa).
      - (* I7 *) unfold I7. intros j.
        change (inQ j (st_Q s) = true -> fA j (cons (ii, a) (st_A s)) = None).
        unfold fA; fold fA.
        destruct (Nat.eqb j ii) eqn:Ej; intros Hq.
        + apply nat_eqb_eq in Ej. subst j. rewrite Hq in HnoQ. discriminate.
        + exact (pI7 _ Hq). }

    (* ---- Case: SRelease ---- *)
    { unfold Inv; split; [|split; [|split; [|split; [|split]]]].
      - (* I1 *) unfold I1 in *; simpl; intros w2 w2n Hf2.
        destruct (Nat.eqb w2 (att_worker at_)) eqn:Ew.
        + apply nat_eqb_eq in Ew. subst w2.
          specialize (Hcnt_s _ eq_refl). specialize (pI1 _ _ Hf2).
          rewrite <- Hcnt_s in pI1. apply Sn_le_m. exact pI1.
        + assert (Hn : w2 <> att_worker at_).
          { intro E. rewrite E, nat_eqb_refl in Ew. discriminate. }
          rewrite (Hcnt_d _ Hn). exact (pI1 _ _ Hf2).
      - (* I2 *) exact I.
      - (* I3 *) exact Huk.
      - (* I4 *) unfold I4 in *. simpl. intros j a2 Hfa.
        exact (pI4 _ _ (Hback _ _ Hfa)).
      - (* I5 *) unfold I5 in *. simpl. intros j a2 Hfa.
        exact (pI5 _ _ (Hback _ _ Hfa)).
      - (* I7 *) unfold I7 in *. simpl. intros j Hq.
        destruct (Nat.eqb j ii) eqn:Ej.
        + apply nat_eqb_eq in Ej. subst j. exact HnoA.
        + rewrite (Hoth _ Ej). exact (pI7 _ Hq). }

    (* ---- Case: SRegWorker ---- *)
    { unfold Inv; split; [|split; [|split; [|split; [|split]]]].
      - (* I1 *) unfold I1 in *; simpl; intros w2 w2n Hf2.
        destruct (Nat.eqb w2 wi) eqn:Ew.
        + apply nat_eqb_eq in Ew. subst w2. injection Hf2 as <-. exact Hcap2.
        + exact (pI1 _ _ Hf2).
      - (* I2 *) exact I.
      - (* I3 *) exact pI3.
      - (* I4 *) exact pI4.
      - (* I5 *) unfold I5 in *. intros j a2 Hfa.
        specialize (pI5 _ _ Hfa).
        change (fG (att_worker a2) (cons (wi, gn) (st_G s)) = Some (att_gen a2)).
        unfold fG; fold fG.
        destruct (Nat.eqb (att_worker a2) wi) eqn:Ew.
        + apply nat_eqb_eq in Ew. specialize (Hgen _ _ Hfa Ew).
          f_equal. symmetry. exact Hgen.
        + exact pI5.
      - (* I7 *) exact pI7. }

    (* ---- Case: SQuarantine ---- *)
    { unfold Inv; split; [|split; [|split; [|split; [|split]]]].
      - exact pI1.
      - (* I2 *) exact I.
      - exact pI3.
      - exact pI4.
      - exact pI5.
      - unfold I7 in *; simpl; intros j Hq.
        destruct (Nat.eqb j ii) eqn:Ej.
        + apply nat_eqb_eq in Ej. subst j. exact HnoA.
        + apply pI7. exact Hq. }
  Qed.

  (* ==== WORKER RETIREMENT & QUIESCENCE SAFETY ==== *)

  Definition Quiescent (s : StateA) (w : WorkerId) : Prop :=
    cntW w (st_A s) = 0.

  Definition WorkerRetired (s : StateA) (w : WorkerId) (gen : Generation) : Prop :=
    fG w (st_G s) = Some gen /\ fW w (st_W s) = None.

  Theorem retirement_quiescence_fencing_safety : forall (s : StateA) (w : WorkerId) (gen : Generation),
    Inv s ->
    WorkerRetired s w gen ->
    Quiescent s w ->
    forall (ii : InvocationId) (att : Attempt),
      fA ii (st_A s) = Some att ->
      att_worker att = w ->
      False.
  Proof.
    intros s w gen Hinv Hret Hquiescent ii att Hfa Haw.
    unfold Quiescent in Hquiescent.
    subst w.
    induction (st_A s) as [| [k v] xs IH]; simpl in Hfa.
    - discriminate Hfa.
    - destruct (Nat.eqb ii k) eqn:Eik.
      + injection Hfa as <-.
        simpl in Hquiescent.
        rewrite nat_eqb_refl in Hquiescent.
        discriminate Hquiescent.
      + simpl in Hquiescent.
        destruct (Nat.eqb (att_worker v) (att_worker att)) eqn:Ew.
        * discriminate Hquiescent.
        * apply IH; assumption.
  Qed.

  (* ==== REACHABILITY & GLOBAL SAFETY ==== *)


  Fixpoint reachable s0 n sn : Prop :=
    match n with
    | 0 => s0 = sn
    | S m => exists sm, reachable s0 m sm /\ Step sm sn
    end.

  Theorem inductive_safety : forall n sn, reachable Init n sn -> Inv sn.
  Proof.
    induction n; simpl; intros sn Hr.
    - subst sn. exact init_inv.
    - destruct Hr as [sm [Hreach Hstep]].
      apply (step_inv sm sn (IHn sm Hreach) Hstep).
  Qed.

  (* ==== ASSUMPTION AUDIT ==== *)
  Print Assumptions init_inv.
  Print Assumptions step_inv.
  Print Assumptions inductive_safety.
  Print Assumptions release_constructive.

  (* ==== PROOF-TO-RUNTIME CORRESPONDENCE CHECKLIST (Issue #47 prep) ====
     Coq StateA              <--> Python ProductionDynamicLoadBalancer
     Coq Attempt             <--> Python InvocationRecord
     Coq I1 (cntW<=w_max)    <--> Python assign_execution capacity check
     Coq I2 (True abstract)  <--> Python w_active_load = cntW (CTR-04 scope)
     Coq I3 (unique_keys)    <--> Python _assignments dict uniqueness
     Coq I4 (fE=att_epoch)   <--> Python _lease_epoch_tracker
     Coq I5 (fG=att_gen)     <--> Python process_generation check
     Coq I6_from_I5          <--> corollary; no separate runtime obligation
     Coq I7 (quarantine)     <--> Python _quarantine set
     Coq SAssign             <--> Python assign_execution()
     Coq SRelease+remove_key <--> Python release_execution()
       release_constructive proves remove_key satisfies SRelease's 7 props
     Coq SRegWorker          <--> Python register_worker()
     Coq SQuarantine         <--> Python _evict_stale_workers() quarantine
     KernelInvariantChecker   <--> Runtime enforcement of I1..I7
     test_phase6_kernel_gate  <--> Adversarial conformance tests

     #47 refinement R(C,A) must prove:
       R(C,A) /\ C -->c C' ==> exists A'. A -->a* A' /\ R(C',A')
     Acceptance gates:
       1. active_load = cntW — cached runtime accounting = mathematical capacity
       2. _lease_epoch_tracker ~ st_EL — runtime epoch repr = formal history
       3. Lock covers read-check-write — atomicity behind the abstract step
       4. < vs <= equivalence — prevents subtle transition mismatch
       5. Python dict deletion <-> remove_key — release correspondence
  *)

End Phase5LoadBalancerRefinement.
