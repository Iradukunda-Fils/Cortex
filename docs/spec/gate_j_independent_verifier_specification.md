# Gate J Specification: Independent Standalone Verifier Engine ($P4$)

**Author:** Iradukunda Fils <iradukundafils1@gmail.com>  
**Role:** Systems Architect & Hardware/Software Co-Designer  
**Status:** NORMATIVE SPECIFICATION (PHASE 13 GATE J)  
**Date:** August 15, 2026  

---

## 1. Overview & Problem Definition

Prior to Gate J, verification of Cortex execution logs relied upon local replay tools (`DeterministicReplayEngine`) that imported trusted substrate code directly. This violates the core principle of **Independent Untrusted Verification ($P4$)**: a verifier cannot be self-referential or rely upon the runtime being audited.

**Gate J** defines the normative specification for `cortex-verifier`, a zero-dependency standalone CLI tool and verification engine. `cortex-verifier` evaluates raw binary/JSON evidence bundles produced by untrusted Cortex instances using only standard cryptographic primitives and trusted root anchors.

---

## 2. Fundamental Constraints & Principles

1. **Zero Substrate Imports**: `cortex-verifier` MUST NOT import `cortex`, `cortex-emulator`, or any runtime orchestration module.
2. **Three-State Verdict Architecture**:
   - **`VALID` (`Exit 0`)**: All cryptographic signatures, CBE digests, intent-execution parity, and rolling witness chains hold strictly from a trusted genesis anchor $W_0$.
   - **`INVALID` (`Exit 1`)**: Explicit cryptographic failure, signature forgery, parameter substitution, sequence gap, or tampered payload.
   - **`INDETERMINATE / INCOMPLETE` (`Exit 2`)**: Log trace is truncated, intermediate evidence steps are missing, or the trace is bound to an un-anchored/unknown genesis $W_0$.
3. **Adversarial Resiliency**: Must reject all manipulated evidence streams without throwing unhandled exceptions.

---

## 3. Evidence Bundle Schema & Inputs

An `EvidenceBundle` presented to `cortex-verifier` contains:

```text
EvidenceBundle
 ├── trusted_anchor.json       # Trusted W_0, Node Public Key, and Capability Root
 ├── signed_intents.json       # Array of SignedIntents (IntentBody + Sig + PubKey)
 ├── execution_tokens.json     # Array of ExecutionTokens (intent_hash + epoch + nonce + sig)
 ├── events.json               # Array of concrete Execution Events
 └── witness_chain.json        # Array of WitnessEntries (sequence + prev_w + digests + W_t + sig)
```

---

## 4. Verification Algorithm Steps

`cortex-verifier` performs five strict sequential checks:

1. **Genesis Anchor Verification**:
   Asserts $W_0 \equiv \text{SHA256}(\text{NS}_{\text{CORTEX}} \parallel \text{NodeID} \parallel \text{Epoch}_0)$ against `trusted_anchor.json`.
2. **SignedIntent Authority Verification**:
   For each intent $I_k$, verifies Ed25519/HMAC signature over $\text{CBE}(\text{IntentBody}_k)$ against authorized node/user public key.
3. **ExecutionToken Intent Parity Assertion**:
   Asserts $\text{ExecutionToken}_k.\text{intent\_hash} \equiv \text{SHA256}(\text{CBE}(\text{SignedIntent}_k))$.
4. **Rolling Witness Chain Verification**:
   For each step $k \in [1..N]$:
   - Asserts $\text{Seq}_k == \text{Seq}_{k-1} + 1$.
   - Asserts $W_k.\text{prev\_witness} \equiv W_{k-1}.\text{witness}$.
   - Asserts $W_k.\text{event\_digest} \equiv \text{SHA256}(\text{CBE}(\text{Event}_k))$.
   - Asserts $W_k.\text{intent\_digest} \equiv \text{SHA256}(\text{CBE}(\text{SignedIntent}_k))$.
   - Recomputes $W_k.\text{witness} = \text{SHA256}(W_{k-1} \parallel D_{E,k} \parallel D_{I,k})$ and asserts equality.
   - Verifies witness entry signature.
5. **Chain Completeness Check**:
   If log stream is truncated prior to terminal commit or contains dangling references, return `INDETERMINATE (2)`.

---

## 5. Security Trap Taxonomy & Adversarial Test Scenarios

| Test ID | Scenario | Expected Verdict | Reason |
| :--- | :--- | :--- | :--- |
| **J-ADV-001** | Untampered evidence bundle | `VALID` (`0`) | All cryptographic checks pass. |
| **J-ADV-002** | Event payload byte mutation | `INVALID` (`1`) | $D_E$ mismatch breaks rolling witness $W_k$. |
| **J-ADV-003** | SignedIntent parameter substitution | `INVALID` (`1`) | $D_I$ mismatch breaks parity assertion. |
| **J-ADV-004** | Event omission (dropped step $t+2$) | `INVALID` (`1`) | Sequence gap & prev_witness break. |
| **J-ADV-005** | Event re-ordering (swapped steps) | `INVALID` (`1`) | Witness continuity break. |
| **J-ADV-006** | Invalid / forged authority signature | `INVALID` (`1`) | Signature verification failure. |
| **J-ADV-007** | Untrusted / modified genesis anchor $W_0$ | `INVALID` (`1`) | $W_0$ hash mismatch against anchor. |
| **J-ADV-008** | Recomputed witness rewrite (forged chain) | `INVALID` (`1`) | Disconnect from trusted root $W_0$. |
| **J-ADV-009** | Truncated log stream | `INDETERMINATE` (`2`) | Terminal event missing. |
| **J-ADV-010** | Forked state branch | `INDETERMINATE` (`2`) | Branching without merge entry. |
| **J-ADV-011** | Expired authority key | `INVALID` (`1`) | Key validity window expired. |
| **J-ADV-012** | Mismatched ExecutionToken / Intent | `INVALID` (`1`) | Token intent_hash mismatch. |

---

## 6. Trust Root Lifecycle & Governance ($R$)

To ensure an adversary cannot forge state by replacing `trusted_anchor.json`, the Trusted Root Material ($R$) is bound to a strict governance lifecycle:

1. **Out-of-Band Distribution**: Root anchor configuration MUST be provisioned out-of-band during deployment or anchored via a hardware root of trust (TPM / RoT).
2. **Monotonic Key Rotation**: Public keys in $R$ MUST contain valid epoch windows $[E_{\text{start}}, E_{\text{end}}]$. Signatures presented outside active key validity windows trigger `INVALID (1)`.
3. **Key Revocation List (KRL) Enforcement**: If an authority key is compromised, it is registered on the KRL, invalidating past and present signed intents originating from that key.
4. **Epoch Checkpoint Anchoring**: Long-running witness chains emit periodic signed epoch checkpoints $W_{\text{checkpoint}}$ committed to immutable storage, preventing history rewrites even by compromised local nodes.

