# F4c.4 Domain Closure Audit & Equivalence Classification Report

- **Document ID**: `CORTEX-SPEC-F4C4-AUDIT-2026`
- **Status**: **NORMATIVELY LOCKED**
- **Author**: Iradukunda Fils <iradukundafils1@gmail.com>
- **Target Component**: Standalone Untrusted Independent Verifier (`tools/cortex_verifier.py`) & Formal Specification (`verification/GateF_F4c_VerifierSpec.v`)

---

## 1. Executive Summary & Final Classification Verdict

Phase **F4c.4** conducts a rigorous domain closure audit to evaluate whether the verifier equivalence claim can be promoted from **BOUNDED DETERMINISTIC REFINEMENT** to **EXHAUSTIVE DOMAIN EQUIVALENCE**, or whether **BOUNDED DETERMINISTIC REFINEMENT** is the sole defensible formal claim.

### Final Classification Verdict
$$\mathbf{\text{F4c.4 Classification}} = \mathbf{\text{BOUNDED DETERMINISTIC REFINEMENT}}$$

> **NORMATIVE STATEMENT OF FORMAL LIMITATION**:
> The Cortex project **explicitly rejects** claiming *Exhaustive Domain Equivalence* for Phase F4c. The concrete verifier has demonstrated parity with the Coq decision procedure across the 10 currently defined structural equivalence classes used for bounded refinement testing. Exhaustive equivalence over all infinite input traces would require a machine-checked binary extraction proof covering Python's string parsing (`json.loads`), binary CBE codec, and C-native OpenSSL HMAC/SHA256 implementations. 
> 
> Therefore, **BOUNDED DETERMINISTIC REFINEMENT** remains the highest defensible assurance tier.

---

## 2. Input Dimension Enumeration for Evidence Profile V1 ($\mathcal{D}_{V1}$)

The input space of Evidence Profile V1 ($\mathcal{D}_{V1}$) is parameterized across 10 distinct structural dimensions:

1. **Evidence Structure**: Presence and formatting of top-level JSON fields (`anchor`, `intents`, `tokens`, `events`, `witness_chain`).
2. **Stream Length Parity**: Relationship between element counts ($|intents|$, $|tokens|$, $|events|$, $|witness\_chain|$).
3. **Genesis Anchor Inputs ($W_0$)**: Validity of `node_id` (UUIDv5), `genesis_epoch` ($\ge 0$), and `expected_w0` hash string matching.
4. **Sequence Monotonicity & Continuity**: Sequence values $s_i$ for $i \in 1 \dots N$, asserting $s_1 = 1$ and $s_i = s_{i-1} + 1$.
5. **Parent Pointer Chaining**: Relational integrity of $prev\_witness_i = W_{i-1}$.
6. **Intent / Token Pairing**: Verification of `tokens[i].intent_hash == SHA256(CBE(intents[i]))`.
7. **Event / Intent Digest Integrity**: Verification of `event_digest` and `intent_digest` against canonical CBE hashes.
8. **Authority Signatures**: Verification of cryptographic signature bytes across intent payloads and witness chain entries.
9. **Trace Incompleteness & Recovery**: Handling of explicit `is_incomplete: true` flags, empty streams, and missing trace segments.
10. **Schema & Version Values**: Presence and adherence to `$schema` relative path format and version markers.

---

## 3. Partitioning $\mathcal{D}_{V1}$ into Finite Equivalence Classes

To evaluate decision procedure parity, the infinite domain $\mathcal{D}_{V1}$ is partitioned into **10 disjoint structural equivalence classes**:

```
                       ┌───────────────────────────────────────────┐
                       │ Evidence Profile V1 Domain (D_V1)         │
                       └─────────────────────┬─────────────────────┘
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      │                                      │                                      │
      ▼                                      ▼                                      ▼
┌───────────┐                          ┌───────────┐                          ┌───────────┐
│   VALID   │                          │  INVALID  │                          │INDETERMINATE
│  CLASS 1  │                          │CLASSES 2-7│                          │CLASSES 8-10
└─────┬─────┘                          └─────┬─────┘                          └─────┬─────┘
      │                                      │                                      │
      │ C1: Full Verified Valid Trace        │ C2: Anchor Mismatch                  │ C8: Empty Stream
      │                                      │ C3: Signature Violation              │ C9: Missing Section
      │                                      │ C4: Token Parity Mismatch            │ C10: Stream Length
      │                                      │ C5: Sequence Gap                     │      Mismatch / Flagged
      │                                      │ C6: Chain Broken                     │
      │                                      │ C7: Digest Mutation                  │
```

---

## 4. Class-by-Class Equivalence Mapping Matrix

| Class ID | Domain Partition & Equivalence Class Description | F4c.1 Domain Category | Python Verifier Output (`tools/cortex_verifier.py`) | Coq Formal Verdict (`GateF_F4c_VerifierSpec.v`) | Decision Procedure Parity |
| :---: | :--- | :---: | :--- | :--- | :---: |
| **C1** | **Full Verified Trace**: Valid anchor, continuous sequence ($1..N$), valid parent chain, matching CBE digests, valid signatures. | `VALID` | `Verdict.VALID` (`0`) | `VERDICT_VALID` | **PERFECT MATCH** |
| **C2** | **Anchor Mismatch**: Genesis anchor $W_0$ does not match computed `expected_w0`. | `INVALID` | `Verdict.INVALID` (`1`) | `VERDICT_INVALID` | **PERFECT MATCH** |
| **C3** | **Signature Violation**: Intent or witness entry signature verification failure. | `INVALID` | `Verdict.INVALID` (`1`) | `VERDICT_INVALID` | **PERFECT MATCH** |
| **C4** | **Token Parity Mismatch**: `tokens[i].intent_hash != SHA256(CBE(intents[i]))`. | `INVALID` | `Verdict.INVALID` (`1`) | `VERDICT_INVALID` | **PERFECT MATCH** |
| **C5** | **Sequence Gap**: Non-monotonic or discontinuous sequence index ($s_i \neq s_{i-1} + 1$). | `INVALID` | `Verdict.INVALID` (`1`) | `VERDICT_INVALID` | **PERFECT MATCH** |
| **C6** | **Chain Broken**: Discontinuous parent pointer ($prev\_witness_i \neq W_{i-1}$). | `INVALID` | `Verdict.INVALID` (`1`) | `VERDICT_INVALID` | **PERFECT MATCH** |
| **C7** | **Digest Mutation**: Event or intent payload modified after witness creation. | `INVALID` | `Verdict.INVALID` (`1`) | `VERDICT_INVALID` | **PERFECT MATCH** |
| **C8** | **Empty Stream**: $|W| = 0$ or $|E| = 0$. | `INDETERMINATE` | `Verdict.INDETERMINATE` (`2`) | `VERDICT_MALFORMED`* | **PERFECT MATCH** |
| **C9** | **Missing Required Section**: Missing `anchor`, `intents`, `events`, or `witness_chain`. | `INDETERMINATE` | `Verdict.INDETERMINATE` (`2`) | `VERDICT_MALFORMED`* | **PERFECT MATCH** |
| **C10** | **Stream Length Mismatch / Flagged**: $|W| \neq |E|$ or $|E| \neq |I|$ or `is_incomplete: true`. | `INDETERMINATE` | `Verdict.INDETERMINATE` (`2`) | `VERDICT_MALFORMED`* | **PERFECT MATCH** |

*\*Note: In Coq's `GateF_F4c_VerifierSpec.v`, the constructor name `VERDICT_MALFORMED` represents structural incompleteness, which maps 1:1 to the `INDETERMINATE` classification in F4c.1 and Python.*

---

## 5. Technical Justification for Retaining Bounded Refinement

Claiming **Exhaustive Domain Equivalence** requires demonstrating that *every possible string* accepted by the formal spec is identically accepted by the concrete code, and every string rejected by the formal spec is identically rejected by the concrete code.

For Cortex, three unverified compiler/runtime boundaries prevent claiming exhaustive domain equivalence:

1. **Unverified Host Parsers**: Python's standard `json.loads` and string processing are implemented in C and operate outside the Coq mechanized proof framework.
2. **Unverified Binary Codec**: The Python CBE serializer (`tools/cbe_encoder.py`) is verified via 14-vector golden corpus tests (empirical), not via Coq code extraction.
3. **Cryptographic Primitive Assumption**: Hashing relies on the trusted primitive `sha256_bytes : list Byte -> Hash256`. Cryptographic collision resistance and C-OpenSSL SHA-256 implementation equivalence are assumed, not formally extracted.

Consequently, **BOUNDED DETERMINISTIC REFINEMENT** is the only scientifically rigorous and defensible formal claim for F4c.

---

## 6. Uncovered Domain Boundaries & Future Roadmap

To eventually promote F4c to **Exhaustive Equivalence**, the following technical gates must be closed in future phases:

- **Gate F4c.4a**: Coq extraction of the CBE binary codec to pure C/Rust with mechanized AST equivalence.
- **Gate F4c.4b**: Formal verification of the JSON AST parser against the JSON RFC 8259 formal grammar.
- **Gate F4c.4c**: Machine-checked proof linking Python bytecode semantics to Coq's `formal_verify` decision procedure.
