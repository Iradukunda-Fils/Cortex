# Coq Formal Proof Inventory Delta & Baseline Reconciliation
**Authoritative Coq/Rocq Theorem Accounting & Delta Map**  
**Date:** August 22, 2026  
**Repository Baseline SHA:** `c9d72d3` (`main`)

---

## 1. Executive Summary & Verification Language Alignment

To eliminate language ambiguity across historical documentation, the formal proof inventory distinguishes between:
- **Normative Architecture Obligations:** High-level safety claims mapped directly to protocol requirements (e.g., `RD-F1` through `RD-F17`).
- **Sub-Case / Supporting Theorems:** Specific sub-case proofs handling edge conditions (e.g. TOCTOU offline/draining/drift variants, idempotency).
- **Helper Lemmas:** Structural Coq arithmetic or boolean lemmas supporting tactics (`nat_eqb_eq`, `andb_true_elim`, etc.).
- **Total Proof Declarations:** Every `Theorem`, `Lemma`, `Corollary`, and `Proposition` declared in the Coq corpus.

---

## 2. Phase 4 Proof Inventory Delta (`Phase4RoutingRefinement.v`)

| Classification | Previous Count | New Additions | Current Count | Mapped Proof Identifiers |
| :--- | :--- | :--- | :--- | :--- |
| **Normative RD Obligations** | 17 | 0 | 17 | `rd_f1_eligibility_safety` through `rd_f17_cap_hash_fencing` |
| **Supporting / Sub-Case Theorems** | 3 | 4 | 7 | `rd_f6_unadmitted_durable_safety`, `rd_f7_commit_idempotent`, `rd_f10_toctou_offline`, `rd_f10_toctou_draining`, `rd_f10_toctou_generation_drift`, `rd_f14_admitted_unactuated_explicit_no_actuation`, `rd_f15_assigned_conflict_actuation_blocked` |
| **Helper Lemmas** | 0 | 4 | 4 | `andb_true_elim`, `nat_eqb_eq`, `nat_eqb_neq`, `nat_ltb_ge` |
| **Total `Phase4RoutingRefinement.v`** | **20** | **8** | **28** | All 28 proof declarations verified closed in Rocq 9.1 |

---

## 3. Full Repository Formal Corpus Accounting (24 `.v` Files)

| Coq Specification File | Proved Theorems / Lemmas | Axioms | Admitted | Assumptions Status |
| :--- | :--- | :--- | :--- | :--- |
| `AuthorityModel.v` | 0 (Definitions) | 0 | 0 | Closed |
| `BinaryLoader.v` | 0 (Definitions) | 0 | 0 | Closed |
| `CBESpec.v` | 6 | 0 | 0 | Closed |
| `DelegationChainRTL.v` | 8 | 0 | 0 | Closed |
| `FTLR.v` | 1 | 0 | 0 | Closed |
| `GateF_F0_ModelReconciliation.v` | 5 | 0 | 0 | Closed |
| `GateF_F1_1_StateCorrespondence.v` | 2 | 0 | 0 | Closed |
| `GateF_F1_2_RealIPC_Stuttering.v` | 3 | 0 | 0 | Closed |
| `GateF_F1_2_StutteringPreservation.v` | 3 | 0 | 0 | Closed |
| `GateF_F2_1_RestrictCap.v` | 1 | 0 | 0 | Closed |
| `GateF_F2_2_GrantCap.v` | 3 | 0 | 0 | Closed |
| `GateF_F3_1_InvocationSimulation.v` | 3 | 0 | 0 | Closed |
| `GateF_F4_EvidenceRefinement.v` | 5 | 0 | 0 | Closed |
| `GateF_F4c_VerifierSpec.v` | 7 | 0 | 0 | Trusted Cryptographic Boundary (`sha256_bytes`) |
| `GateL1_EpochMonotonicity.v` | 11 | 0 | 0 | Closed |
| `GateL1_StateExtraction.v` | 20 | 0 | 0 | Closed |
| `GrantCapRTL.v` | 6 | 0 | 0 | Closed |
| `LogicalRelation.v` | 2 | 0 | 0 | Closed |
| `Phase4RoutingRefinement.v` | **28** | 0 | 0 | Closed |
| `RevokeExpiryRTL.v` | 7 | 0 | 0 | Closed |
| `Semantics.v` | 0 (Definitions) | 0 | 0 | Closed |
| `Soundness.v` | 1 | 0 | 0 | Closed |
| `Substitution.v` | 2 | 0 | 0 | Closed |
| `World.v` | 3 | 0 | 0 | Closed |
| **TOTAL REPOSITORY FORMAL CORPUS** | **127 Proved Declarations** | **0** | **0** | **100% Closed Context** |

---

## 4. Manifest Synchronization Sign-Off

The formal accounting across all repository governance manifests (`cortex_assurance_manifest.json`, `docs/architecture/coq_print_assumptions_audit.json`, `docs/architecture/verification_closure_matrix.md`, and `docs/architecture/cortex_current_repository_inventory.md`) is synchronized to:
- **Phase 4 Proof Declarations:** 28 proof declarations (17 normative obligations + 7 supporting theorems + 4 helper lemmas).
- **Total Corpus Proof Declarations:** 127 proved theorems/lemmas across 24 `.v` files.
- **Axioms / Admitted:** 0 Admitted, 0 Axioms.
