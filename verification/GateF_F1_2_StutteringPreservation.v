(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: GateF_F1_2_StutteringPreservation.v                               *)
(* Classification: R1 (Representation Correspondence & Stutter Preservation) *)
(* Purpose: Milestone F1.2 - Two-Layer Stuttering Framework & IPC Parse Step  *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.

Section GateF1_Stuttering_Refined.

  (* ----------------------------------------------------------------------- *)
  (* 1. SEMANTIC RUNTIME PROJECTION                                          *)
  (* ----------------------------------------------------------------------- *)

  (** [TRIPLE STATE PROJECTION] 
      Semantic Runtime Projection extracts only semantic runtime fields required 
      for World correspondence (c_supervisor_pid). Excludes operational state 
      (IPC buffers, token pools) and evidence state (c_audit_chain_head). *)
  Record SemanticRuntimeState := {
    proj_supervisor_pid : nat
  }.

  Definition project_semantic_runtime (rt : RuntimeState) : SemanticRuntimeState := {|
    proj_supervisor_pid := rt.(c_supervisor_pid)
  |}.

  (* ----------------------------------------------------------------------- *)
  (* 2. REFINED CONCRETE STUTTERING RELATION                                 *)
  (* ----------------------------------------------------------------------- *)

  (** A concrete step is a stutter iff:
      1. Hardware state (HEC, STCRs) remains strictly invariant.
      2. The semantic runtime projection remains strictly invariant. *)
  Definition concrete_stutter (c c' : ConcreteSystemState) : Prop :=
    c'.(c_hw_state) = c.(c_hw_state) /\
    project_semantic_runtime c'.(c_rt_state) = project_semantic_runtime c.(c_rt_state).

  (* ----------------------------------------------------------------------- *)
  (* 3. LAYER 1: GENERIC STUTTERING PRESERVATION THEOREM                     *)
  (* ----------------------------------------------------------------------- *)

  (** [LAYER 1 THEOREM] Generic Stuttering Preservation Theorem
      Proves that implementation-only runtime evolutions preserve the 
      abstraction relation R(C, W) without advancing the semantic World state. *)
  Theorem stuttering_preserves_refinement :
    forall (c c' : ConcreteSystemState) (w : World list_auth_model),
      refines c w ->
      concrete_stutter c c' ->
      refines c' w.
  Proof.
    intros c c' w Href Hstutter.
    unfold refines in *.
    unfold concrete_stutter in Hstutter.
    destruct Href as [Hwf [Hepoch Hlambda]].
    destruct Hstutter as [Hhw_eq Hproj_eq].
    destruct c as [hw rt], c' as [hw' rt'].
    simpl in *.
    subst hw'.
    split; [exact Hwf | split; [exact Hepoch | exact Hlambda]].
  Qed.

  (* ----------------------------------------------------------------------- *)
  (* 4. LAYER 2: CONCRETE STEP FORMALIZATION (IPC ENVELOPE PARSING)           *)
  (* ----------------------------------------------------------------------- *)

  (** Operational Buffer State for IPC Envelope Decoding *)
  Record IPCBuffer := {
    ipc_raw_bytes  : list nat;
    ipc_parsed_len : nat
  }.

  Record ConcreteStateWithIPC := {
    sys_state  : ConcreteSystemState;
    ipc_buffer : IPCBuffer
  }.

  Definition ipc_parse_step (s s' : ConcreteStateWithIPC) : Prop :=
    (sys_state s').(c_hw_state) = (sys_state s).(c_hw_state) /\
    (sys_state s').(c_rt_state).(c_supervisor_pid) = (sys_state s).(c_rt_state).(c_supervisor_pid) /\
    (ipc_buffer s').(ipc_parsed_len) = (ipc_buffer s).(ipc_parsed_len) + 1.

  (** [LAYER 2 LEMMA] Concrete IPC Parse is a Stuttering Step *)
  Lemma ipc_parse_is_stutter :
    forall (s s' : ConcreteStateWithIPC),
      ipc_parse_step s s' ->
      concrete_stutter (sys_state s) (sys_state s').
  Proof.
    intros s s' Hparse.
    destruct s as [cs ib], s' as [cs' ib'].
    destruct cs as [hw rt], cs' as [hw' rt'].
    unfold ipc_parse_step in Hparse.
    simpl in Hparse.
    destruct Hparse as [Hhw [Hpid Hlen]].
    subst hw'.
    unfold concrete_stutter.
    simpl.
    split.
    - reflexivity.
    - unfold project_semantic_runtime. simpl. f_equal. exact Hpid.
  Qed.

  (** [COROLLARY] IPC Parsing Preserves Refinement *)
  Corollary ipc_parse_preserves_refinement :
    forall (s s' : ConcreteStateWithIPC) (w : World list_auth_model),
      refines (sys_state s) w ->
      ipc_parse_step s s' ->
      refines (sys_state s') w.
  Proof.
    intros s s' w Href Hparse.
    apply (stuttering_preserves_refinement (sys_state s) (sys_state s') w); auto.
    apply ipc_parse_is_stutter. exact Hparse.
  Qed.

End GateF1_Stuttering_Refined.
