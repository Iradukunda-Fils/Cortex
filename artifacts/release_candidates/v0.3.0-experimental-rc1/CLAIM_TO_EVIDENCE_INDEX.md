# Cortex v0.3.0-Experimental-RC1 — Claim-to-Evidence Index

> **Purpose**: Machine-readable and human-auditable lineage index connecting each formal/empirical assurance claim in `cortex_assurance_manifest.json` to its precise specification, code implementation, formal Coq theorem, test suite methods, raw log outputs, and evidence artifacts.
> **Release Candidate**: `v0.3.0-experimental-rc1`  
> **Commit Hash**: `dfad89f5cc01b94513c035f4401c8fb0864e8521`

---

## Evidence Taxonomy & Classification Policy

To prevent ambiguity during external security review, evidence in this index is strictly partitioned into three non-interchangeable classes:

```
                  ┌──────────────────────────────────────────────────────────┐
                  │                 CORTEX ASSURANCE CLAIMS                  │
                  └─────────────────────────────┬────────────────────────────┘
                                                │
         ┌──────────────────────────────────────┼──────────────────────────────────────┐
         ▼                                      ▼                                      ▼
┌──────────────────┐                  ┌──────────────────┐                  ┌──────────────────┐
│  PROOF EVIDENCE  │                  │  IMPLEMENTATION  │                  │    EXECUTION     │
│ (Formal Models)  │                  │     EVIDENCE     │                  │     EVIDENCE     │
└────────┬─────────┘                  └────────┬─────────┘                  └────────┬─────────┘
         │                                     │                                     │
 • Coq / coqchk                       • Unit / Integration                  • SystemVerilog RTL
 • Proves state invariants              Adversarial Tests                   • Emulator trace logs
 • Does NOT prove software/           • Proves tested paths                  • Golden test bundles
   hardware realization               • Does NOT prove                      • Proves trace parity for
   without refinement                   arbitrary inputs                      concrete scenarios
```

1. **Proof Evidence (Coq Formal Verification)**: Static proof verification (`coqchk`). Proves invariants on abstract mathematical models. *Caveat*: Does not prove software/hardware realizations are defect-free without explicit refinement proofs.
2. **Implementation Evidence (Empirical Test Harnesses)**: Dynamic unit/integration/adversarial checks (`136/136 PASS`, `288/288 PASS`). Proves behavior along tested execution paths. *Caveat*: Does not prove un-tested arbitrary inputs are safe.
3. **Execution Evidence (Concrete System Traces & Golden Corpus)**: Deterministic execution logs (`rtl_trace.json`, `emulator_trace.json`, golden bundle JSONs). Proves concrete trace equivalence across runtimes for specified scenario inputs.

---

## Comprehensive Claim-to-Evidence Mapping Matrix

### 1. CLAIM-F2-F3-AUTHORITY-MODEL
- **Property**: Spatial attenuation, temporal monotonicity, capability derivation, and fail-closed trap classification.
- **Assurance Classification**: `FORMALLY_VERIFIED`
- **Evidence Class**: **Proof Evidence**
- **Specification Section**: `docs/architecture/gate_f_concrete_refinement.md` §3.1 – §3.3
- **Implementation File/Function**: `verification/AuthorityModel.v`, `verification/World.v`, `verification/Semantics.v`
- **Coq Theorems**: `restrict_cap_attenuation`, `grant_cap_monotonicity`, `soundness_trap_classification` (`verification/GateF_F2_1_RestrictCap.v`)
- **Test(s)**: `coqchk -R . Cortex`
- **Raw Evidence Artifact**: `logs/coq_verification_raw.log` (SHA256: `24b65ad...`)
- **Platform Constraint**: Coq 8.16+ / Rocq 9.1+

---

### 2. CLAIM-F4A-EVIDENCE-MODEL
- **Property**: Causal sequence monotonicity and parent-pointer chain integrity.
- **Assurance Classification**: `FORMALLY_VERIFIED`
- **Evidence Class**: **Proof Evidence**
- **Specification Section**: `docs/architecture/gate_f_concrete_refinement.md` §4.1
- **Implementation File/Function**: `verification/GateF_F4_EvidenceRefinement.v`
- **Coq Theorems**: `causal_sequence_monotonic`, `parent_pointer_integrity`
- **Test(s)**: `coqchk -R . Cortex`
- **Raw Evidence Artifact**: `logs/coq_verification_raw.log` (SHA256: `24b65ad...`)
- **Platform Constraint**: Coq 8.16+ / Rocq 9.1+

---

### 3. CLAIM-F4B-DIGEST-ALIGNMENT
- **Property**: Representation-identity consistency between abstract digest and concrete 256-bit hash domain.
- **Assurance Classification**: `FORMALLY_REFINED`
- **Evidence Class**: **Proof Evidence** (with Trusted Cryptographic Primitive Boundary)
- **Specification Section**: `docs/architecture/gate_f_concrete_refinement.md` §4.2
- **Implementation File/Function**: `verification/GateF_F4b_ConcreteCryptoRefinement.v`
- **Coq Theorems**: `abstract_digest_hash256_embedding`
- **Test(s)**: `coqchk -R . Cortex`
- **Raw Evidence Artifact**: `logs/coq_verification_raw.log` (SHA256: `24b65ad...`)
- **Assumptions**: `sha256_bytes : list Byte -> Hash256` (Trusted Cryptographic Primitive Boundary)

---

### 4. CLAIM-F4C-VERIFIER-MODEL
- **Property**: Formal specification of iterative graph decision procedure for evidence chain verification.
- **Assurance Classification**: `FORMALLY_VERIFIED`
- **Evidence Class**: **Proof Evidence**
- **Specification Section**: `docs/architecture/f4c_evidence_domain_v1.md` §2.0
- **Implementation File/Function**: `verification/GateF_F4c_VerifierSpec.v`
- **Coq Theorems**: `verifier_graph_decision_soundness`, `verifier_completeness`
- **Test(s)**: `coqchk -R . Cortex`
- **Raw Evidence Artifact**: `logs/coq_verification_raw.log` (SHA256: `24b65ad...`)
- **Platform Constraint**: Coq 8.16+ / Rocq 9.1+

---

### 5. CLAIM-F4C-DOMAIN-V1
- **Property**: Normative definition and classification of Evidence Bundle Domain $\mathcal{D}_{V1}$ and Schema Profile V1.
- **Assurance Classification**: `NORMATIVELY_LOCKED`
- **Evidence Class**: **Specification & Schema Constraint**
- **Specification Section**: `docs/architecture/f4c_evidence_domain_v1.md` §3.0 – §5.0
- **Implementation File/Function**: `docs/spec/evidence_profile_v1.schema.json`
- **Test(s)**: Schema validation across golden corpus
- **Raw Evidence Artifact**: `manifests/f4c_evidence_domain_v1.md`
- **Platform Constraint**: JSON Schema Draft 2020-12

---

### 6. CLAIM-F4C-VERIFIER-BRIDGE
- **Property**: Standalone verifier CLI implementation equivalence against abstract domain $\mathcal{D}_{V1}$.
- **Assurance Classification**: `EMPIRICALLY_CONFORMANT`
- **Evidence Class**: **Implementation & Execution Evidence**
- **Specification Section**: `docs/architecture/f4c_evidence_domain_v1.md` §6.0
- **Implementation File/Function**: `cortex/tools/cortex_verifier.py::verify_bundle`
- **Test(s)**: `python3 -m unittest tests/conformance/test_f4c_corpus_conformance.py`
- **Raw Evidence Artifact**: `logs/certification_suite_raw.log` (Section: INDEPENDENT UNTRUSTED VERIFIER)
- **Golden Corpus Artifacts**: `corpus/f4c_evidence_corpus/valid_chain.json`, `invalid_rights.json`, `attenuated_cap.json`, `malformed_ptr.json`, `cyclic_chain.json`

---

### 7. CLAIM-F4C3-VERIFIER-MAPPING
- **Property**: Concrete verifier implementation mapping against Coq decision procedure (`GateF_F4c_VerifierSpec.v`).
- **Assurance Classification**: `BOUNDED_REFINEMENT`
- **Evidence Class**: **Implementation Evidence**
- **Specification Section**: `docs/architecture/f4c3_verifier_formal_mapping.md` §1.0 – §4.0
- **Implementation File/Function**: `cortex/tools/cortex_verifier.py`, `tests/conformance/test_f4c3_verifier_formal_mapping.py`
- **Test(s)**: `TestF4c3VerifierFormalMapping` (5 test methods)
- **Raw Evidence Artifact**: `logs/repository_unittest_raw.log` (SHA256: `bbf22aa...`)

---

### 8. CLAIM-F4C4-DOMAIN-CLOSURE
- **Property**: Partitioned differential auditing of Evidence Profile V1 domain $\mathcal{D}_{V1}$ across 10 structural equivalence classes.
- **Assurance Classification**: `BOUNDED_REFINEMENT`
- **Evidence Class**: **Implementation Evidence**
- **Specification Section**: `docs/architecture/f4c4_domain_closure_audit.md` §2.0 – §3.0
- **Implementation File/Function**: `tests/conformance/test_f4c4_domain_closure_audit.py`
- **Test(s)**: `TestF4c4DomainClosureAudit` (10 differential checks for Class 1..10)
- **Raw Evidence Artifact**: `logs/certification_suite_raw.log` (Section: F4c.4 Class 1-10 Differential Checks)

---

### 9. CLAIM-CBE-CONCRETE-REFINEMENT
- **Property**: Bounded byte-level correspondence between `CBESpec.v` and concrete Python (`cortex/cbe`), Rust (`cortex-emulator/src/cbe.rs`), and Go (`cortex-go/cbe`) implementations. Corrective Action CA-001 closed.
- **Assurance Classification**: `BOUNDED_REFINEMENT_CROSS_RUNTIME_TESTED`
- **Evidence Class**: **Implementation & Execution Evidence**
- **Specification Section**: `docs/architecture/canonical-serialization.md` §3.0 – §4.0 (CA-001 Aligned)
- **Implementation File/Function**: `cortex/cbe/encoder.py`, `cortex-emulator/src/cbe.rs`, `cortex-go/cbe/encoder.go`
- **Test(s)**: `python3 -m unittest tests/test_cbe.py`
- **Raw Evidence Artifact**: `logs/repository_unittest_raw.log`, `corpus/cbe_vectors/`

---

### 10. CLAIM-GATE-G-SUPERVISOR
- **Property**: Complete side-effect trapping and worker isolation under 2-stage supervisor (Seccomp-BPF / Landlock / Mount Isolation / Unwhitelisted FD Sanitation).
- **Assurance Classification**: `IMPLEMENTATION_CERTIFIED`
- **Evidence Class**: **Implementation Evidence**
- **Specification Section**: `docs/spec/gate_g_remediation_specification.md` §5.0 – §7.0
- **Implementation File/Function**: `cortex/runtime/sandbox.py::CapabilitySandbox`, `cortex/runtime/isolation_profile.py`
- **Test(s)**: `python3 tests/conformance/run_certification.py` (Tests G-000B to G-012, PID1 Containment)
- **Raw Evidence Artifact**: `logs/certification_suite_raw.log` (Section: WORKER ISOLATION & MEDIATION)

---

### 11. CLAIM-GATE-H-PARITY
- **Property**: Bit-for-bit intent to actuation canonicalization parity and intent parameter binding across Python, Rust, and Go runtimes.
- **Assurance Classification**: `IMPLEMENTATION_CERTIFIED`
- **Evidence Class**: **Implementation Evidence**
- **Specification Section**: `docs/spec/gate_h_execution_token_specification.md` §2.0 – §4.0
- **Implementation File/Function**: `cortex/core/gate_h.py::GateHMediator`
- **Test(s)**: `tests/conformance/test_gate_h_adversarial.py` (Tests H-TEST-001 to H-TEST-014)
- **Raw Evidence Artifact**: `logs/certification_suite_raw.log` (Section: EXECUTION-INTENT PARITY)

---

### 12. CLAIM-GATE-I-WITNESS
- **Property**: Rolling SHA-256 state chain monotonicity and tamper evidence under crash-fault injection.
- **Assurance Classification**: `IMPLEMENTATION_CERTIFIED`
- **Evidence Class**: **Implementation Evidence**
- **Specification Section**: `docs/spec/gate_i_causal_witness_specification.md` §3.0 – §5.0
- **Implementation File/Function**: `cortex/core/gate_i.py::CausalWitness`
- **Test(s)**: `tests/conformance/test_gate_i_causal_witness.py` (7 adversarial vector tests)
- **Raw Evidence Artifact**: `logs/certification_suite_raw.log` (Section: CRYPTOGRAPHIC CAUSAL WITNESS)

---

### 13. CLAIM-GATE-J-VERIFIER
- **Property**: Standalone evidence chain verification for tested bundle domain (12 adversarial vectors).
- **Assurance Classification**: `IMPLEMENTATION_CERTIFIED`
- **Evidence Class**: **Implementation Evidence**
- **Specification Section**: `docs/spec/gate_j_independent_verifier.py` §2.0 – §3.0
- **Implementation File/Function**: `tests/conformance/test_gate_j_independent_verifier.py`
- **Test(s)**: 12 adversarial vector tests (Event payload mutation, intent parameter substitution, event omission, replay, signature forgery, untrusted anchor)
- **Raw Evidence Artifact**: `logs/certification_suite_raw.log` (Section: INDEPENDENT UNTRUSTED VERIFIER)

---

### 14. CLAIM-HARDWARE-L1-L2-MODEL
- **Property**: 6-opcode forward simulation safety and epoch monotonicity for 16-bit non-wrapping saturating STCR behavioral model.
- **Assurance Classification**: `FORMALLY_VERIFIED`
- **Evidence Class**: **Proof Evidence**
- **Specification Section**: `docs/architecture/gate_f_concrete_refinement.md` §5.0
- **Implementation File/Function**: `verification/GateL1_StateExtraction.v`, `verification/GateL1_EpochMonotonicity.v`
- **Coq Theorems**: `stcr_step_forward_simulation_safety`, `hec_epoch_monotonicity_16bit`
- **Test(s)**: `coqchk -R . Cortex`
- **Raw Evidence Artifact**: `logs/coq_verification_raw.log` (SHA256: `24b65ad...`)

---

### 15. CLAIM-HARDWARE-L1-L2-TRACE
- **Property**: Direct SystemVerilog RTL execution trace extraction correspondence ($O_5/O_6$). CA-002 and CA-003 closed.
- **Assurance Classification**: `BOUNDED_REFINEMENT_TRACE_VERIFIED`
- **Evidence Class**: **Execution Evidence**
- **Specification Section**: `docs/architecture/gate_f_concrete_refinement.md` §5.4
- **Implementation File/Function**: `rtl/cortex_stcr_pipeline.sv`, `cortex-emulator/src/main.rs`, `tests/conformance/test_conformance_rtl.py`
- **Test(s)**: `python3 -m unittest tests.conformance.test_conformance_rtl.TestSVCoqTraceBridge` (17 assertions)
- **Raw Evidence Artifact**: `traces/rtl_trace.json` (SHA256: `487df16...`), `traces/emulator_trace.json` (SHA256: `9ede820...`), `logs/certification_suite_raw.log` (Section: RTL ADAPTER CONFORMANCE)

---

## Matrix Summary Table

| Claim ID | Property / Scope | Classification | Primary Evidence Class | Artifact / Log Reference |
| :--- | :--- | :--- | :--- | :--- |
| `CLAIM-F2-F3-AUTHORITY-MODEL` | Spatial attenuation & temporal monotonicity | `FORMALLY_VERIFIED` | **Proof Evidence** | `logs/coq_verification_raw.log` |
| `CLAIM-F4A-EVIDENCE-MODEL` | Causal sequence monotonicity | `FORMALLY_VERIFIED` | **Proof Evidence** | `logs/coq_verification_raw.log` |
| `CLAIM-F4B-DIGEST-ALIGNMENT` | 256-bit digest representation identity | `FORMALLY_REFINED` | **Proof Evidence** | `logs/coq_verification_raw.log` |
| `CLAIM-F4C-VERIFIER-MODEL` | Iterative graph decision spec | `FORMALLY_VERIFIED` | **Proof Evidence** | `logs/coq_verification_raw.log` |
| `CLAIM-F4C-DOMAIN-V1` | Evidence Bundle Domain $\mathcal{D}_{V1}$ spec | `NORMATIVELY_LOCKED` | **Spec & Schema** | `manifests/f4c_evidence_domain_v1.md` |
| `CLAIM-F4C-VERIFIER-BRIDGE` | Verifier CLI equivalence on corpus | `EMPIRICALLY_CONFORMANT` | **Impl & Exec Evidence** | `corpus/f4c_evidence_corpus/` |
| `CLAIM-F4C3-VERIFIER-MAPPING` | Concrete verifier mapping against Coq | `BOUNDED_REFINEMENT` | **Implementation Evidence** | `logs/repository_unittest_raw.log` |
| `CLAIM-F4C4-DOMAIN-CLOSURE` | $\mathcal{D}_{V1}$ domain closure (10 classes) | `BOUNDED_REFINEMENT` | **Implementation Evidence** | `logs/certification_suite_raw.log` |
| `CLAIM-CBE-CONCRETE-REFINEMENT` | Tri-runtime CBE byte encoding (CA-001) | `BOUNDED_REFINEMENT` | **Impl & Exec Evidence** | `corpus/cbe_vectors/` |
| `CLAIM-GATE-G-SUPERVISOR` | Worker isolation & 2-stage supervisor | `IMPLEMENTATION_CERTIFIED` | **Implementation Evidence** | `logs/certification_suite_raw.log` |
| `CLAIM-GATE-H-PARITY` | Intent canonicalization & token binding | `IMPLEMENTATION_CERTIFIED` | **Implementation Evidence** | `logs/certification_suite_raw.log` |
| `CLAIM-GATE-I-WITNESS` | Rolling SHA-256 witness chain monotonicity | `IMPLEMENTATION_CERTIFIED` | **Implementation Evidence** | `logs/certification_suite_raw.log` |
| `CLAIM-GATE-J-VERIFIER` | Standalone verifier (12 adversarial vectors) | `IMPLEMENTATION_CERTIFIED` | **Implementation Evidence** | `logs/certification_suite_raw.log` |
| `CLAIM-HARDWARE-L1-L2-MODEL` | 6-opcode STCR model & 16-bit HEC | `FORMALLY_VERIFIED` | **Proof Evidence** | `logs/coq_verification_raw.log` |
| `CLAIM-HARDWARE-L1-L2-TRACE` | Verilator RTL ↔ Rust trace parity (CA-002/003) | `BOUNDED_REFINEMENT` | **Execution Evidence** | `traces/rtl_trace.json` |
