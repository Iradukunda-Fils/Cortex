# ADR-008: Identity Specification & UUID Supersession Model
**Status:** APPROVED (NORMATIVE ADR)  
**Date:** 2026-08-15  
**Author:** Iradukunda Fils <iradukundafils1@gmail.com>  
**Role:** Systems Architect & Hardware/Software Co-Designer  
**Supersedes:** Informal Domain Model UUIDv7 drafting notes  
**Evidence Base:** Gate K Verification Closure, Tri-Runtime Conformance Corpus (v0.3.1)  
**Target Release:** v0.3.1-Closure  

---

## Executive Summary

During the Phase 1 Architectural Reconstruction of Cortex, an unresolved contradiction emerged between early Domain Model drafting notes (which referenced UUIDv7 for entity identification) and the Layer 0/Layer 3 Wire Specification (which mandated bit-precise RFC 4122 **UUIDv5** derived via SHA-1 over Canonical Binary Encoding preimages).

This Architectural Decision Record (ADR) formally resolves this specification conflict, establishing a clear **Identity Domain Hierarchy** across all 6 Cortex layers ($L_0\text{--}L_5$).

---

## Decision & Rule Matrix

```
                      CORTEX IDENTITY DOMAIN HIERARCHY
                                     │
   ┌─────────────────────────────────┴─────────────────────────────────┐
   │                                                                   │
Deterministic Wire Identity (UUIDv5)                Local Runtime Identity (UUIDv7 / Ephemeral)
• L0 Immutable Identity                            • L4/L5 Database Primary Keys
• L1 CBE Payload Hash                              • Local Log Indexing Optimization
• L2 Frame & Stream Correlation                    • Worker Process Traces
• L3 Invocation & Intent Envelope                  • Ephemeral Session Run Tokens
```

### Rule 1: Wire & Protocol Determinism ($L_0\text{--}L_3$) — MANDATORY UUIDv5
1. All wire envelopes, `SignedIntent` IDs, `InvocationEnvelope` IDs, capability delegation descriptors, and deterministic state witness hashes **MUST** use RFC 4122 **UUIDv5**.
2. **Formula**:
   $$\text{Identity}(S) = \text{UUIDv5}(\text{NS}_{\text{CORTEX}}, \text{CBE}(S))$$
3. **Namespace Constant ($\text{NS}_{\text{CORTEX}}$)**:
   `6ba7b810-9dad-11d1-80b4-00c04fd430c8`
4. **Root Causation Sentinel**: If an event or command has no parent event (root event), `causation_id` **MUST** be set to the Nil UUID string:
   `00000000-0000-0000-0000-000000000000`

### Rule 2: Control Plane & Ephemeral Storage ($L_4\text{--}L_5$) — PERMISSIVE UUIDv7 / Local Primary Keys
1. Host runtime engines (Python, Rust, Go) **MAY** use time-ordered **UUIDv7** or 64-bit integer auto-increment keys for local storage B-Tree index optimization within internal databases (e.g. SQLite/Pebble/RocksDB).
2. However, runtime-ephemeral UUIDv7 values **MUST NOT** leak into Layer 0–3 wire frames, cross-runtime parity comparisons ($P_{\text{semantic}}$), or cryptographic witness hash calculations.

### Rule 3: Parity & Conformance Equivalence ($P_{\text{semantic}}$)
Independent cross-runtime verification between Python, Rust, Go, and Coq **MUST** evaluate parity strictly over deterministic `logical_event_id` (UUIDv5) and `CBE(Payload)` preimages.

---

## Consequences

1. **Elimination of Specification Drift**: Formally retires all ambiguous claims that UUIDv7 supersedes UUIDv5 at the wire layer.
2. **Unbroken Determinism**: Guarantees bit-for-bit identity derivation across all polyglot runtimes (Python reference, Rust emulator, Go transport adapter).
3. **Storage Efficiency**: Permits high-throughput local log storage to leverage UUIDv7 locality without compromising protocol determinism.
