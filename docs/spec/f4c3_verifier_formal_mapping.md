# F4c.3 Concrete Verifier ↔ Formal Model Mapping Specification

- **Document ID**: `CORTEX-SPEC-F4C3-MAPPING-2026`
- **Status**: **NORMATIVELY LOCKED**
- **Author**: Iradukunda Fils <iradukundafils1@gmail.com>
- **Target**: Correspondence Mapping between Python `IndependentVerifier` (`tools/cortex_verifier.py`) and Coq Specification (`verification/GateF_F4c_VerifierSpec.v`)

---

## 1. Executive Summary & Refinement Classification

Phase **F4c.3** establishes the concrete correspondence mapping between the standalone Python reference verifier (`tools/cortex_verifier.py`) and the machine-checked Coq formal decision procedure (`verification/GateF_F4c_VerifierSpec.v`).

- **Formal Equivalence Classification**: **BOUNDED REFINEMENT**  
  *The Python implementation is verified to conform to the Coq decision procedure over the concrete Evidence Profile V1 domain $\mathcal{D}_{V1}$. Universal infinite-trace domain equivalence remains an open technical gate (F4c.4).*

- **Formal Reporting Precision Policy**:  
  - **0 Admitted Proofs**: Verified 0 `Admitted` statements across all active Coq modules.  
  - **0 Project-Declared Axioms**: Verified 0 `Axiom` keywords declared in the project codebase.  
  - **1 Trusted Cryptographic Primitive**: `sha256_bytes : list Byte -> Hash256` — the sole uninterpreted/trusted parameterized primitive interface across the formal baseline.

---

## 2. State & Field Correspondence Mapping

| Abstract Formal Field (Coq `GateF_F4c_VerifierSpec.v`) | Concrete Implementation Field (Python `tools/cortex_verifier.py`) | Representation Mapping / Type Conversion |
| :--- | :--- | :--- |
| `eb_witness_chain : list ConcreteWitnessState` | `bundle["witness_chain"] : list[dict]` | List of witness state entries. `cw_hash` $\leftrightarrow$ `entry["witness"]` (hex), `cw_parent` $\leftrightarrow$ `entry["prev_witness"]` (hex), `cw_seq` $\leftrightarrow$ `entry["sequence"]` (`int`). |
| `eb_events : list CommitEvent` | `bundle["events"] : list[dict]` | Ordered list of commit event dictionaries serialized via CBE. |
| `eb_intents : list SignedIntent` | `bundle["intents"] : list[dict]` | Ordered list of signed intent dictionaries serialized via CBE. |
| `eb_initial : ConcreteWitnessState` | `bundle["anchor"] : dict` | Genesis anchor $W_0 = \text{SHA256}(NS_{\text{cortex}} \parallel node\_id \parallel genesis\_epoch)$. |

---

## 3. Tripartite Verdict Domain Alignment

| Coq Formal Verdict (`FormalVerdict`) | Python `IndependentVerifier` (`Verdict`) | Semantic Interpretation & Traps Triggered |
| :--- | :--- | :--- |
| `VERDICT_VALID` | `Verdict.VALID (0)` | All witness chain links verified, sequence continuous, genesis anchor authenticated, digests matching. |
| `VERDICT_INVALID` | `Verdict.INVALID (1)` | Input is structurally parseable, but violates semantic/security rules (`TRAP_EVENT_DIGEST_MISMATCH`, `TRAP_SIGNATURE_INVALID`, `TRAP_SEQUENCE_GAP`, `TRAP_CHAIN_BROKEN`, `TRAP_TOKEN_PARITY_MISMATCH`). |
| `VERDICT_MALFORMED` | `Verdict.INDETERMINATE (2)` | Input satisfies schema format but evidence is incomplete/truncated (`TRAP_INCOMPLETE_TRACE`, `TRAP_INCOMPLETE_TRACE_STREAM_LENGTH_MISMATCH`, missing anchor). |

---

## 4. Line-by-Line Decision Procedure Correspondence Audit

| Coq Decision Procedure Step (`GateF_F4c_VerifierSpec.v`) | Python Verifier Implementation Step (`tools/cortex_verifier.py`) | Verification Alignment & Traps |
| :--- | :--- | :--- |
| **Check 1: Non-Empty Chain**<br>`match eb_witness_chain eb with nil => VERDICT_MALFORMED` | `if not witness_chain:`<br>`return Verdict.INDETERMINATE, "TRAP_INCOMPLETE_TRACE"` | **ALIGNED** (Returns `VERDICT_MALFORMED` / `INDETERMINATE`) |
| **Check 2: Stream Length Equality**<br>`if nat_eqb (length events) (length witness_chain) ...` | `if len(events) != n or len(intents) != n or len(tokens) != n:`<br>`return Verdict.INDETERMINATE` | **ALIGNED** (Enforces $|intents| = |tokens| = |events| = |witness\_chain|$) |
| **Check 3: Genesis Anchor Match**<br>`cw_hash w_initial = expected_w0` | `if anchor["expected_w0"] != computed_w0:`<br>`return Verdict.INVALID, "TRAP_UNTRUSTED_ANCHOR_MISMATCH"` | **ALIGNED** (Verifies genesis state anchor link against trusted root) |
| **Check 4: Iterative Chain Link Verification**<br>`verify_chain_links w_prev chain events intents` | `for i in range(n):`<br>Check sequence, parent pointer, event digest, intent digest, witness hash | **ALIGNED** (OBS-C compliant $O(1)$ stack iterative loop, checking link hashes) |
| **Check 5: Signature Verification**<br>Authority signature verification on signable bytes | `verify_signature(entry["signature"], signable_bytes)` | **ALIGNED** (Verifies cryptographic signature per entry) |

---

## 5. Security & Invariant Trap Audit Matrix

1. **Genesis Anchor Verification**: Python verifier computes `expected_w0` from `node_id` and `genesis_epoch` using SHA-256 and rejects mismatched anchors (`TRAP_UNTRUSTED_ANCHOR_MISMATCH`).
2. **Sequence Monotonicity & Continuity**: Python verifier enforces $seq_i = seq_{i-1} + 1$ starting from $seq_1 = 1$. Sequence gaps or non-monotonic indices trigger `TRAP_SEQUENCE_GAP`.
3. **Parent Pointer Chaining**: Enforces $prev\_witness_i = W_{i-1}$ for all $i \ge 1$. Broken chain links trigger `TRAP_CHAIN_BROKEN`.
4. **Event & Intent Digest Matching**: Computes CBE digest of `events[i]` and `intents[i]` and compares against `witness_chain[i]` entries. Mismatches trigger `TRAP_EVENT_DIGEST_MISMATCH` or `TRAP_SIGNATURE_INVALID`.
5. **Token Binding Parity**: Verifies `tokens[i]["intent_hash"] == SHA256(CBE(intents[i]))`. Mismatches trigger `TRAP_TOKEN_PARITY_MISMATCH`.
6. **Stream Length Equality**: Verifies $|intents| = |tokens| = |events| = |witness\_chain|$. Length discrepancies trigger `TRAP_INCOMPLETE_TRACE_STREAM_LENGTH_MISMATCH`.
7. **Cyclic / Malformed Ancestry Protection**: Iterative loop processes entries strictly in sequence index order ($1 \dots N$), preventing graph recursion and cyclic loop traps.

---

## 6. Formal Verification Soundness & Assumption Retainment

- **Soundness Theorem (`verify_witness_link_sound`)**:  
  $\forall w_{prev}, w_{next}, e, i$, if `verify_witness_link` returns `true`, then $w_{next}$ has identical hash, parent pointer, and sequence index to the abstract state computed by `compute_next_concrete_witness`.

- **Retained Trusted Assumption**:  
  The formal proof of link soundness and chain integrity relies exclusively on:
  ```coq
  sha256_bytes : list Byte -> Hash256
  ```
  This primitive represents the trusted cryptographic hashing boundary.
