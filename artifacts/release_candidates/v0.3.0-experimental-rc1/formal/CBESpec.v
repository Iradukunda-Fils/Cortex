(* ========================================================================= *)
(* CORTEX FORMAL VERIFICATION FRAMEWORK                                      *)
(* Module: CBESpec.v                                                        *)
(* Classification: R3b / Phase 2 (CBE Layer 1 Specification & Refinement)   *)
(* Purpose: Formalize the Canonical Binary Encoding type grammar and        *)
(*          prove correspondence between normative CBE specification and    *)
(*          model-level byte envelopes used in F4b.                         *)
(* ========================================================================= *)

From Cortex Require Import AuthorityModel.
From Cortex Require Import World.
From Cortex Require Import Semantics.
From Cortex Require Import GateF_F0_ModelReconciliation.
From Cortex Require Import GateF_F1_1_StateCorrespondence.
From Cortex Require Import ValidInvocationRTL.
From Cortex Require Import EndToEndRefinementRTL.
From Cortex Require Import GateF_F4_EvidenceRefinement.
From Cortex Require Import GateF_F4b_ConcreteCryptoRefinement.

Section CBESpec.

  (* ======================================================================= *)
  (* 1. CBE TYPE TAG GRAMMAR (7 CANONICAL TAGS)                               *)
  (* ======================================================================= *)

  (** CBE Type Tag Enumeration:
      Each tag occupies exactly 1 byte (represented as nat for model simplicity).
      These correspond to the Python/Rust/Go implementations:
        cortex/cbe/encoder.py, cortex-emulator/src/cbe.rs, cortex-go/cbe/encoder.go *)
  Inductive CBETag : Type :=
    | TAG_NULL    (* 'N' = 0x4E *)
    | TAG_BOOL    (* 'B' = 0x42 *)
    | TAG_INT     (* 'I' = 0x49 *)
    | TAG_FLOAT   (* 'D' = 0x44 *)
    | TAG_STRING  (* 'S' = 0x53 *)
    | TAG_LIST    (* 'L' = 0x4C *)
    | TAG_MAP.    (* 'M' = 0x4D *)

  (** Concrete byte value for each CBE tag *)
  Definition cbe_tag_byte (t : CBETag) : Byte :=
    match t with
    | TAG_NULL   => 78  (* 0x4E = 'N' *)
    | TAG_BOOL   => 66  (* 0x42 = 'B' *)
    | TAG_INT    => 73  (* 0x49 = 'I' *)
    | TAG_FLOAT  => 68  (* 0x44 = 'D' *)
    | TAG_STRING => 83  (* 0x53 = 'S' *)
    | TAG_LIST   => 76  (* 0x4C = 'L' *)
    | TAG_MAP    => 77  (* 0x4D = 'M' *)
    end.

  (** [THEOREM: CBE TAG INJECTIVITY]
      Distinct CBE tags produce distinct byte values.
      Ensures no tag collision in the wire format. *)
  Theorem cbe_tag_injective :
    forall (t1 t2 : CBETag),
      cbe_tag_byte t1 = cbe_tag_byte t2 -> t1 = t2.
  Proof.
    intros t1 t2 H.
    destruct t1; destruct t2; simpl in H;
      try reflexivity; try discriminate.
  Qed.

  (** [THEOREM: CBE TAGS ARE PAIRWISE DISTINCT]
      No two different tags share the same byte value. *)
  Theorem cbe_tags_pairwise_distinct :
    forall (t1 t2 : CBETag),
      t1 <> t2 -> cbe_tag_byte t1 <> cbe_tag_byte t2.
  Proof.
    intros t1 t2 Hneq Habs.
    apply Hneq. apply cbe_tag_injective. exact Habs.
  Qed.

  (* ======================================================================= *)
  (* 2. CBE MAP KEY ORDERING SPECIFICATION                                     *)
  (* ======================================================================= *)

  (** Lexicographic byte-order comparison for map key sorting.
      This is the canonical key ordering rule enforced across all runtimes:
        Python: pairs_with_utf8_keys.sort(key=lambda item: item[0])
        Rust:   keys.sort_by(|a, b| a.cmp(b))
        Go:     sort.Slice(keys, func(i, j int) bool { return keys[i] < keys[j] }) *)
  Fixpoint byte_list_lt (l1 l2 : list Byte) : Prop :=
    match l1, l2 with
    | nil, nil => False
    | nil, _ => True       (* empty < non-empty *)
    | _, nil => False      (* non-empty > empty *)
    | cons b1 rest1, cons b2 rest2 =>
      (b1 < b2) \/ (b1 = b2 /\ byte_list_lt rest1 rest2)
    end.

  (** A CBE map is canonically sorted if keys are in strict ascending byte order *)
  Fixpoint cbe_map_sorted (pairs : list (list Byte * nat)) : Prop :=
    match pairs with
    | nil => True
    | cons _ nil => True
    | cons (k1, _) (cons (k2, _) _ as rest) =>
      byte_list_lt k1 k2 /\ cbe_map_sorted rest
    end.

  (** [THEOREM: BYTE LIST STRICT ORDER IS IRREFLEXIVE]
      No byte list is strictly less than itself. *)
  (** Helper: n < n is absurd *)
  Lemma nat_lt_irrefl : forall n : nat, ~ (n < n).
  Proof.
    unfold lt. intros n H.
    induction n.
    - inversion H.
    - apply IHn. apply le_S_n. exact H.
  Qed.

  Theorem byte_list_lt_irrefl :
    forall (k : list Byte),
      ~ byte_list_lt k k.
  Proof.
    induction k as [| b rest IH]; simpl; intro H.
    - exact H.
    - destruct H as [Hlt | [_ Hrec]].
      + exact (nat_lt_irrefl b Hlt).
      + exact (IH Hrec).
  Qed.

  (* ======================================================================= *)
  (* 3. CBE INTEGER ENCODING SPECIFICATION                                     *)
  (* ======================================================================= *)

  (** [DEFINITION: CBE CANONICAL INTEGER ENCODING]
      Format: 'I' followed by ASCII decimal digits, no leading zeros.
      This specifies the normative serialization rule for int fields
      used in CommitEvent and SignedIntent envelopes.

      Example: 42 → [73, 52, 50] = "I42"

      Simplified to nat here; the full spec extends to signed int64
      with '-' prefix for negative values. *)
  Fixpoint nat_to_ascii_inner (n : nat) (fuel : nat) : list Byte :=
    match fuel with
    | O => cons (Nat.modulo n 10 + 48) nil
    | S fuel' =>
      let q := Nat.div n 10 in
      let r := Nat.modulo n 10 in
      match q with
      | O => cons (r + 48) nil
      | _ => append_bytes (nat_to_ascii_inner q fuel') (cons (r + 48) nil)
      end
    end.

  Definition encode_nat_ascii (n : nat) : list Byte :=
    nat_to_ascii_inner n 20.

  Definition cbe_encode_int (n : nat) : list Byte :=
    cons (cbe_tag_byte TAG_INT) (encode_nat_ascii n).

  (* ======================================================================= *)
  (* 4. CBE STRING ENCODING SPECIFICATION                                      *)
  (* ======================================================================= *)

  (** [DEFINITION: CBE CANONICAL STRING ENCODING]
      Format: 'S' <length> ':' <utf8_payload>
      Payload must be NFC-normalized UTF-8 (enforced at the runtime level).
      58 = ASCII ':' *)
  Definition cbe_encode_string (payload : list Byte) : list Byte :=
    cons (cbe_tag_byte TAG_STRING)
      (append_bytes (encode_nat_ascii (length payload))
        (cons 58 payload)).

  (* ======================================================================= *)
  (* 5. EVENT & INTENT CBE SPECIFICATION ENCODERS                              *)
  (* ======================================================================= *)

  (** [DEFINITION: CBE SPECIFICATION-LEVEL EVENT ENCODER]
      Encodes a CommitEvent as a CBE Map with 4 integer fields.
      Keys are sorted in canonical UTF-8 byte order:
        "evt_id" < "evt_intent_slot" < "evt_payload_hash" < "evt_state_root" *)
  Definition cbe_encode_event_spec (e : CommitEvent) : list Byte :=
    let k_id   := cons 101 (cons 118 (cons 116 (cons 95
                  (cons 105 (cons 100 nil))))) in  (* "evt_id" *)
    let k_slot := cons 101 (cons 118 (cons 116 (cons 95
                  (cons 105 (cons 110 (cons 116 (cons 101 (cons 110 (cons 116
                  (cons 95 (cons 115 (cons 108 (cons 111 (cons 116
                  nil)))))))))))))) in              (* "evt_intent_slot" *)
    let k_hash := cons 101 (cons 118 (cons 116 (cons 95
                  (cons 112 (cons 97 (cons 121 (cons 108 (cons 111 (cons 97
                  (cons 100 (cons 95 (cons 104 (cons 97 (cons 115 (cons 104
                  nil))))))))))))))) in             (* "evt_payload_hash" *)
    let k_root := cons 101 (cons 118 (cons 116 (cons 95
                  (cons 115 (cons 116 (cons 97 (cons 116 (cons 101 (cons 95
                  (cons 114 (cons 111 (cons 111 (cons 116
                  nil))))))))))))) in               (* "evt_state_root" *)
    append_bytes
      (cons (cbe_tag_byte TAG_MAP)
        (append_bytes (encode_nat_ascii 4) (cons 58 nil)))
      (append_bytes (cbe_encode_string k_id)
        (append_bytes (cbe_encode_int e.(evt_id))
          (append_bytes (cbe_encode_string k_slot)
            (append_bytes (cbe_encode_int e.(evt_intent_slot))
              (append_bytes (cbe_encode_string k_hash)
                (append_bytes (cbe_encode_int e.(evt_payload_hash))
                  (append_bytes (cbe_encode_string k_root)
                    (cbe_encode_int e.(evt_state_root))))))))).

  (** [DEFINITION: CBE SPECIFICATION-LEVEL INTENT ENCODER]
      Encodes a SignedIntent as a CBE Map with 3 integer fields.
      Keys in canonical order:
        "intent_payload" < "intent_req_right" < "intent_slot" *)
  Definition cbe_encode_intent_spec (i : SignedIntent) : list Byte :=
    let k_payload := cons 105 (cons 110 (cons 116 (cons 101 (cons 110 (cons 116
                     (cons 95 (cons 112 (cons 97 (cons 121 (cons 108 (cons 111
                     (cons 97 (cons 100 nil))))))))))))) in  (* "intent_payload" *)
    let k_right   := cons 105 (cons 110 (cons 116 (cons 101 (cons 110 (cons 116
                     (cons 95 (cons 114 (cons 101 (cons 113 (cons 95 (cons 114
                     (cons 105 (cons 103 (cons 104 (cons 116
                     nil))))))))))))))) in                    (* "intent_req_right" *)
    let k_slot    := cons 105 (cons 110 (cons 116 (cons 101 (cons 110 (cons 116
                     (cons 95 (cons 115 (cons 108 (cons 111 (cons 116
                     nil)))))))))) in                         (* "intent_slot" *)
    append_bytes
      (cons (cbe_tag_byte TAG_MAP)
        (append_bytes (encode_nat_ascii 3) (cons 58 nil)))
      (append_bytes (cbe_encode_string k_payload)
        (append_bytes (cbe_encode_int i.(intent_payload))
          (append_bytes (cbe_encode_string k_right)
            (append_bytes (cbe_encode_int i.(intent_req_right))
              (append_bytes (cbe_encode_string k_slot)
                (cbe_encode_int i.(intent_slot))))))).

  (* ======================================================================= *)
  (* 6. DETERMINISM & REFINEMENT PROPERTIES                                    *)
  (* ======================================================================= *)

  (** [THEOREM: CBE EVENT SPEC IS DETERMINISTIC]
      Identical CommitEvent field values produce identical byte outputs. *)
  Theorem cbe_encode_event_spec_deterministic :
    forall (e1 e2 : CommitEvent),
      evt_id e1 = evt_id e2 ->
      evt_intent_slot e1 = evt_intent_slot e2 ->
      evt_payload_hash e1 = evt_payload_hash e2 ->
      evt_state_root e1 = evt_state_root e2 ->
      cbe_encode_event_spec e1 = cbe_encode_event_spec e2.
  Proof.
    intros e1 e2 Hid Hslot Hhash Hroot.
    unfold cbe_encode_event_spec.
    rewrite Hid, Hslot, Hhash, Hroot.
    reflexivity.
  Qed.

  (** [THEOREM: CBE INTENT SPEC IS DETERMINISTIC]
      Identical SignedIntent field values produce identical byte outputs. *)
  Theorem cbe_encode_intent_spec_deterministic :
    forall (i1 i2 : SignedIntent),
      intent_slot i1 = intent_slot i2 ->
      intent_req_right i1 = intent_req_right i2 ->
      intent_payload i1 = intent_payload i2 ->
      cbe_encode_intent_spec i1 = cbe_encode_intent_spec i2.
  Proof.
    intros i1 i2 Hslot Hright Hpayload.
    unfold cbe_encode_intent_spec.
    rewrite Hslot, Hright, Hpayload.
    reflexivity.
  Qed.

  (** [DEFINITION: CBE SPEC-TO-MODEL DIGEST REFINEMENT]
      States that for any CommitEvent/SignedIntent, the SHA-256 digest of the
      specification-level encoding and the model-level encoding produce
      the same witness chain hash input.

      This is the formal bridge between F4b.2/F4b.3 (model-level) and the
      actual Layer 1 CBE implementation. It is stated as a refinement
      condition to be discharged by cross-runtime conformance testing. *)
  Definition cbe_event_spec_digest_refines_model : Prop :=
    forall (e : CommitEvent),
      sha256_bytes (cbe_encode_event_spec e) =
      sha256_bytes (cbe_encode_event_model e).

  Definition cbe_intent_spec_digest_refines_model : Prop :=
    forall (i : SignedIntent),
      sha256_bytes (cbe_encode_intent_spec i) =
      sha256_bytes (cbe_encode_intent_model i).

  (* ======================================================================= *)
  (* 7. ASSUMPTION AUDIT                                                       *)
  (* ======================================================================= *)

  Print Assumptions cbe_tag_injective.
  Print Assumptions cbe_tags_pairwise_distinct.
  Print Assumptions byte_list_lt_irrefl.
  Print Assumptions cbe_encode_event_spec_deterministic.
  Print Assumptions cbe_encode_intent_spec_deterministic.

End CBESpec.
