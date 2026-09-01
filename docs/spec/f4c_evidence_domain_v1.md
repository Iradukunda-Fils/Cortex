# F4c.1 Normative Evidence Profile V1 & Domain Definition ($\mathcal{D}_{V1}$)

- **Document ID**: `CORTEX-SPEC-F4C1-2026-V1`
- **Status**: **NORMATIVE LOCK**
- **Phase**: **F4c.1 (Verifier Evidence Domain Definition)**
- **Target Component**: Standalone Untrusted Independent Verifier (`tools/cortex_verifier.py` / `verification/GateF_F4c_VerifierSpec.v` / `Gate J`)
- **Normative Schema Companion**: [`docs/spec/evidence_profile_v1.schema.json`](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/spec/evidence_profile_v1.schema.json)

---

## 1. Executive Overview & Formal Domain Framing

The Cortex evidence verification model separates formal authority verification from untrusted evidence ingestion. Phase **F4c.1** establishes the **Normative Evidence Profile V1** ($\mathcal{D}_{V1}$), defining the exact domain of inputs accepted, rejected, or classified as incomplete by the zero-trust Independent Verifier.

### 1.1 Formal Domain Definition

The accepted evidence domain $\mathcal{D}_{V1}(R)$ is parameterized strictly by a set of **Trusted Inputs** $R$:

$$\mathcal{D}_{V1}(R) = \left\{ E \;\middle|\; \text{Parse}_{V1}(E) = \text{accepted under trusted root } R \right\}$$

where:

#### Trusted Root Context ($R$)
1. **Verification Secret / Public Keys** ($K_{\text{root}}$): HMAC-SHA256 / ECDSA keys used to authenticate intent signatures and witness chain entries.
2. **Genesis Namespace Anchor** ($\text{NS}_{\text{CORTEX}}$): Fixed UUIDv5 namespace identifier (`6ba7b810-9dad-11d1-80b4-00c04fd430c8`).
3. **Verifier Engine & Profile Version**: Frozen execution binary and schema specification version (`V1`).

#### Untrusted Evidence Bundle ($E$)
The untrusted, external JSON artifact presented to the verifier containing claimed execution traces, signed intents, tokens, state transition events, and witness chain records.

---

## 2. Tripartite Decision Taxonomy

The Independent Verifier maps every candidate evidence bundle $E$ to exactly one of three disjoint formal verdicts:

$$\text{Verdict}(E, R) \in \{ \text{VALID}, \text{INVALID}, \text{INDETERMINATE} \}$$

```
                          ┌──────────────────────────┐
                          │   Untrusted Input (E)    │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────┐
                         │   Parser & Schema V1     │
                         └─────────────┬────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │ Structural Failure       │ Well-Formed              │ Truncated / Missing
            ▼                          ▼                          ▼
 ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
 │       INVALID       │    │     CRYPTOGRAPHIC   │    │    INDETERMINATE    │
 │ (Trap / Violation)  │    │     VERIFICATION    │    │ (Incomplete Trace)  │
 └─────────────────────┘    └──────────┬──────────┘    └─────────────────────┘
                                       │
                          ┌────────────┴────────────┐
                          │ Pass                    │ Fail
                          ▼                         ▼
               ┌─────────────────────┐   ┌─────────────────────┐
               │        VALID        │   │       INVALID       │
               │ (Verified Evidence) │   │ (Signature/Digest)  │
               └─────────────────────┘   └─────────────────────┘
```

### 2.1 Domain Classifications

1. **VALID INPUT DOMAIN ($\mathcal{D}_{V1}^{\text{VALID}}$)**:
   - Evidence bundles that satisfy all JSON Schema Profile V1 structural requirements, pass all intent and witness signature checks, preserve sequence monotonicity ($1 \dots N$), maintain token parity ($D_3 = D_2$), and exhibit bit-precise rolling witness chain continuity ($W_{t+1} = \text{SHA256}(W_t \parallel D_E \parallel D_I)$).

2. **INVALID INPUT DOMAIN ($\mathcal{D}_{V1}^{\text{INVALID}}$)**:
   - Parseable or near-parseable bundles that violate semantic, cryptographic, or security invariants. Includes malformed JSON types, unauthentic signatures, sequence gaps/reorderings, hash rewrites, token-intent mismatches, tampered event payloads, or unanchored genesis claims.

3. **INCOMPLETE / INDETERMINATE DOMAIN ($\mathcal{D}_{V1}^{\text{INDETERMINATE}}$)**:
   - Structurally valid or partial bundles where evidence is insufficient to reach a definitive security verdict. Includes empty streams, missing required sections (`anchor`, `intents`, `tokens`, `events`, `witness_chain`), stream length mismatches ($|W| \neq |E|$ or $|E| \neq |I|$), unreadable files, or traces explicitly flagged with `is_incomplete: true`.

> [!IMPORTANT]
> **Non-Collapse Principle**: `INVALID` and `INDETERMINATE` must **never** collapse into a single failure state. An `INVALID` verdict signifies an active adversarial attack or corruption (fail-closed security trap), whereas an `INDETERMINATE` verdict signifies partial observation requiring trace backfill or failure containment.

---

## 3. Dual-Axis Classification Model

Cortex explicitly decouples the **Evidence Verification Status** from the **Recorded Execution Outcome**.

$$\text{Verdict}(E) = \text{EvidenceStatus} \;\times\; \text{ExecutionOutcome}$$

| Axis | System Component | Value Domain | Meaning |
| :--- | :--- | :--- | :--- |
| **Axis 1** | **Evidence Status** | `VALID`, `INVALID`, `INDETERMINATE` | Authenticity, integrity, and completeness of the evidence trace itself. |
| **Axis 2** | **Execution Outcome** | `SUCCESS`, `DENIED` / `TRAPPED`, `EXCEPTION`, `UNKNOWN` | Operational result of the recorded system action embedded in event payloads. |

> [!TIP]
> **Denied Executions are Valid Evidence**: An evidence bundle recording a `CAPABILITY_VIOLATION` or intercepted sandbox escape (Gate G / Gate H) is a **`VALID` evidence bundle** carrying a **`DENIED` execution outcome**. The verifier confirms that the security trap occurred deterministically and authenticates the trap evidence.

---

## 4. Evidence Bundle Anatomy & Structural Boundary

An Evidence Bundle $E \in \mathcal{D}_{V1}$ is composed of six normative sections:

```
EvidenceBundle (JSON Object)
├── anchor (Genesis State Anchor)
│   ├── node_id (UUID string)
│   ├── genesis_epoch (Integer >= 0)
│   └── expected_w0 (Hex String [64], Optional)
├── intents (Array of SignedIntent)
│   └── [idx] ── body (Dict), signature (Hex String [64])
├── tokens (Array of ExecutionToken)
│   └── [idx] ── intent_hash (Hex String [64]), epoch, node_id, capability
├── events (Array of CommitEvent)
│   └── [idx] ── event_type (String), payload (Dict), timestamp_ns (Integer)
├── witness_chain (Array of WitnessChain Entry)
│   └── [idx] ── version, sequence, timestamp_ns, prev_witness, event_digest, intent_digest, witness, signature
└── is_incomplete (Boolean, Optional)
```

### 4.1 Field Binding Invariants

1. **Length Equivalence**: For any complete bundle, $|W| = |E| = |I|$.
2. **Genesis Anchor $W_0$**: Computed deterministically as:
   $$W_0 = \text{SHA256}(\text{NS}_{\text{CORTEX}} \parallel \text{UUID}_{\text{bytes}}(\text{node\_id}) \parallel \text{uint64}_{\text{be}}(\text{genesis\_epoch}))$$
3. **Intent Digest $D_I$**: Computed over Canonical Binary Encoding (CBE) of intent object:
   $$D_I = \text{SHA256}(\text{CBE}(\text{SignedIntent}))$$
4. **Event Digest $D_E$**: Computed over CBE serialization of commit event:
   $$D_E = \text{SHA256}(\text{CBE}(\text{CommitEvent}))$$
5. **Rolling State Chain $W_{t+1}$**:
   $$W_{t+1} = \text{SHA256}(W_t \parallel D_E \parallel D_I)$$

---

## 5. Parser Semantics & Diagnostic Classification Matrix

The parser and Independent Verifier execute a deterministic 2-pass decision procedure. The table below codifies the exact mapping from input condition to formal verdict and diagnostic trap code:

| Input Condition | Structural Validity | Cryptographic Check | Formal Verdict | Diagnostic Trap Code |
| :--- | :--- | :--- | :--- | :--- |
| **File Read Error / Unparseable JSON** | Invalid | N/A | `INDETERMINATE` | `TRAP_FILE_READ_ERROR` |
| **Missing Required Section** (`anchor`, `intents`, etc.) | Invalid | N/A | `INDETERMINATE` | `TRAP_INCOMPLETE_TRACE_MISSING_<SEC>` |
| **Empty Stream** ($|W| = 0$ or $|E| = 0$) | Invalid | N/A | `INDETERMINATE` | `TRAP_INCOMPLETE_TRACE_EMPTY_STREAM` |
| **Stream Length Mismatch** ($|W| \neq |E|$) | Invalid | N/A | `INDETERMINATE` | `TRAP_INCOMPLETE_TRACE_STREAM_LENGTH_MISMATCH` |
| **Explicit Incomplete Flag** (`is_incomplete: true`) | Valid | N/A | `INDETERMINATE` | `TRAP_INCOMPLETE_TRACE_FLAGGED` |
| **Malformed Anchor UUID / Epoch Format** | Invalid | N/A | `INVALID` | `TRAP_UNTRUSTED_ANCHOR_MALFORMED` |
| **Genesis Anchor Mismatch** ($W_0 \neq \text{expected\_w0}$) | Valid | Failed | `INVALID` | `TRAP_UNTRUSTED_ANCHOR_MISMATCH` |
| **Intent Signature Violation** | Valid | Failed | `INVALID` | `TRAP_SIGNATURE_INVALID_AT_STEP_N` |
| **Token Parity Mismatch** ($D_3 \neq D_2$) | Valid | Failed | `INVALID` | `TRAP_TOKEN_PARITY_MISMATCH_AT_STEP_N` |
| **Sequence Gap or Out-of-Order Step** | Valid | Failed | `INVALID` | `TRAP_SEQUENCE_GAP_AT_STEP_N` |
| **Chain Continuity Broken** ($\text{prev\_witness} \neq W_t$) | Valid | Failed | `INVALID` | `TRAP_CHAIN_BROKEN_AT_STEP_N` |
| **Event Digest Mismatch** ($D_E \neq \text{SHA256}(E)$) | Valid | Failed | `INVALID` | `TRAP_EVENT_DIGEST_MISMATCH_AT_STEP_N` |
| **Intent Digest Mismatch** ($D_I \neq \text{SHA256}(I)$) | Valid | Failed | `INVALID` | `TRAP_INTENT_DIGEST_MISMATCH_AT_STEP_N` |
| **Witness Rewrite Mismatch** ($W_{t+1} \neq \text{computed}$) | Valid | Failed | `INVALID` | `TRAP_WITNESS_REWRITE_MISMATCH_AT_STEP_N` |
| **Witness Entry Signature Violation** | Valid | Failed | `INVALID` | `TRAP_WITNESS_ENTRY_SIGNATURE_INVALID_AT_STEP_N` |
| **Complete & Fully Verified Trace** | Valid | Passed | `VALID` | `EVIDENCE_VERIFIED_VALID` |

---

## 6. Calibration of Assurance Accounting Metrics

To prevent accounting ambiguity between test runner outputs, the Cortex baseline establishes three explicit, non-overlapping testing metrics:

```
CORTEX ASSURANCE ACCOUNTING METRICS
│
├── 1. Total Repository Test Cases (250)
│      Full test suite discovered by `python3 -m unittest discover -s tests`
│      (Includes CLI, app scaffolding, unit tests, and integration vectors).
│
├── 2. Standalone Certification Test Methods (88)
│      Discovered unittest methods inside `tests/conformance/`
│      (Focusing on isolated contract gates Gate G, H, I, J).
│
└── 3. Integrated Certification Assertions (104)
       Integrated assertions executed and output by `python3 tests/conformance/run_certification.py`
       (Includes full end-to-end sandbox, cycle-accurate RTL assertions, and mutation immunity checks).
```

---

## 7. Next Work Order Sequence

With Phase **F4c.1 Domain Definition** normatively frozen:

```
F4c.1 Domain Definition (D_V1 Locked)
                  │
                  ▼
F4c.2 Verifier Totality & Determinism Proofs
                  │
                  ▼
F4c.3 Concrete Verifier ↔ Formal State Mapping
                  │
                  ▼
F4c.4 Equivalence Classification (Bounded Conformance vs. Exhaustive Equivalence)
```
