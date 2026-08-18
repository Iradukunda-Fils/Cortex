# External Security Review Dossier — Cortex v0.3.0-Experimental-RC1

> **Classification**: Release Candidate / Controlled-Experimental Baseline  
> **Production Sign-Off Status**: NOT SIGNED OFF (Intended for External Adversarial Audit)  
> **Release Tag**: `v0.3.0-experimental-rc1`  
> **Repository Policy**: Immutable Baseline Freeze  

---

## 1. Governance & Baseline Audit Policy

This release candidate establishes the **Assurance Baseline** for the Cortex Spatiotemporal Authority Substrate.

### Immutable Revision Policy
1. **Baseline Freeze**: The codebase and specification at `v0.3.0-experimental-rc1` are frozen against unevidenced architectural drift.
2. **Audit Findings Invariant**: External review findings MUST NOT be addressed by retroactively altering the `rc1` baseline to erase defects.
3. **Non-Alteration of Historical Evidence**: No post-RC1 modification may alter historical RC1 evidence, test results, proof artifacts, or claims. Corrections belong exclusively in subsequent release candidates (RC2+).
4. **Audit Trail Lifecycle**:
   $$\text{v0.3.0-experimental-rc1} \longrightarrow \text{External Findings} \longrightarrow \text{CA-004, CA-005, ...} \longrightarrow \text{Re-certification (136+ PASS)} \longrightarrow \text{v0.3.0-experimental-rc2}$$

---

## 2. Targeted External Adversarial Challenge Surfaces

External security auditors are invited to challenge the system across the following **7 core surfaces** without relying on Cortex's internal test harness as authority:

### Challenge Surface 1: Gate G (Sandbox Isolation, FD Sanitation & IPC Mediation)
- **Target**: `cortex/runtime/sandbox.py`, `cortex/runtime/isolation_profile.py`, `docs/spec/gate_g_remediation_specification.md`
- **Adversarial Vectors**:
  - Landlock LSM bypass via pre-existing inherited file descriptors (evaluating `close_range(4, ~0U, CLOSE_RANGE_UNSHARE)` immunity).
  - Seccomp-BPF filter evasion via unhandled socket domain/type combinations or native FFI calls.
  - PID namespace escape or zombie process survival upon PID 1 termination.
  - IPC domain socket framing buffer overflows and request replay injections.

### Challenge Surface 2: Gate H (Execution Intent Canonicalization & Actuation Boundary)
- **Target**: `cortex/core/gate_h.py`, `docs/spec/gate_h_execution_token_specification.md`
- **Adversarial Vectors**:
  - Canonical serialization ambiguity (CBE encoder/decoder map key reordering, float normalization bypass).
  - Intent parameter substitution (tampering with action, target, or payload without invalidating signature).
  - Capability token presentation replay across distinct epoch bounds.
  - Atomic CAS concurrency race conditions during intent presentation.

### Challenge Surface 3: Gate I (Causal Witness & Crash Fault Recovery Governance)
- **Target**: `cortex/core/gate_i.py`, `docs/spec/gate_i_causal_witness_specification.md`
- **Adversarial Vectors**:
  - Event log tampering (omission, insertion, or reordering of signed events in the rolling chain).
  - Inducing physical side-effects during non-idempotent actuation prior to Gateway crash to falsify state recovery.
  - Genesis state anchor mismatch or unauthorized root anchor mutation.

### Challenge Surface 4: Gate J (Standalone Verifier Independence & Malformed Input Handling)
- **Target**: `cortex/tools/cortex_verifier.py`, `docs/spec/gate_j_independent_verifier.py`
- **Adversarial Vectors**:
  - Denial of service or unhandled exceptions when ingesting malformed/truncated evidence streams.
  - Schema confusion attacks via missing or invalid anchor headers.
  - Verification bypass where invalid evidence yields `VERDICT_VALID` due to permissive fallback checks.

### Challenge Surface 5: F4c Verifier Domain & Equivalence Closure ($\mathcal{D}_{V1}$)
- **Target**: `verification/GateF_F4c_VerifierSpec.v`, `docs/architecture/f4c4_domain_closure_audit.md`
- **Adversarial Vectors**:
  - Boundary misalignment between formal domain $\mathcal{D}_{V1}$ and concrete Python decision procedure.
  - Structural equivalence class collisions across the 10 partitioned differential categories.
- **Auditor Challenge Question**:  
  *Auditors are requested to specifically challenge whether the parser-accepted evidence domain $\mathcal{D}_{parser}$, the formally-proven domain $\mathcal{D}_{formal}$, and the concrete verifier domain $\mathcal{D}_{concrete}$ are strictly identical for $\mathcal{D}_{V1}$:
  $$\text{Parser Accepted Evidence} \implies \text{Evidence} \in \mathcal{D}_{V1} \implies \text{Formal Semantics Cover } \mathcal{D}_{V1} \implies \text{Concrete Verifier Covers } \mathcal{D}_{V1}$$

### Challenge Surface 6: Layer 1 / Layer 2 Hardware Trace Extraction & Refinement
- **Target**: `rtl/cortex_stcr_pipeline.sv`, `cortex-emulator/src/hardware/guard.rs`, `verification/GateL1_StateExtraction.v`
- **Adversarial Vectors**:
  - Hardware HEC 16-bit saturating counter overflow edge cases (`reg_hec = 65535` trapping behavior vs 64-bit formal model expectations).
  - Pipeline timing / clock-cycle stuttering discrepancies between Verilator RTL execution trace and Coq `wb_transition` inductive relations.

### Challenge Surface 7: Cryptographic Identity & Trusted Primitive Boundary
- **Target**: `cortex/cbe/uuidv5.py`, `cortex-emulator/src/cbe.rs`, `verification/GateF_F4b_ConcreteCryptoRefinement.v`
- **Adversarial Vectors**:
  - Trusted primitive assumption validation (`sha256_bytes : list Byte -> Hash256`).
  - Preimage collision resistance in UUIDv5 lineage derivation over CBE serialized structures.

---

## 3. Evidence Classification & Non-Interchangeability Policy

Reviewers MUST distinguish between the three non-interchangeable classes of evidence in this package:

1. **Proof Evidence (`formal/*.v`, `formal/*.vo`)**: Static formal proofs (`coqchk`). Proves state invariants on abstract mathematical models. *Does NOT prove software/hardware realization without explicit refinement proofs.*
2. **Implementation Evidence (`logs/certification_suite_raw.log`, `logs/repository_unittest_raw.log`)**: Dynamic unit/integration/adversarial checks (`136/136 PASS`, `288/288 PASS`). Proves behavior along tested execution paths. *Does NOT prove arbitrary un-tested inputs are safe.*
3. **Execution Evidence (`traces/*.json`, `corpus/`)**: Concrete execution traces and golden bundles. Proves trace parity for specific scenario inputs across runtimes.

For a complete mapping of all 15 assurance claims down to their exact specs, code lines, Coq theorems, test methods, and evidence artifacts, see:
$$\longrightarrow \text{\textbf{CLAIM\_TO\_EVIDENCE\_INDEX.md}}$$

---

## 4. Audit Evidence Package Contents & Layout

```text
artifacts/release_candidates/v0.3.0-experimental-rc1/
├── COMMIT_HASH.txt                    # Git commit hash (dfad89f5cc01...)
├── GIT_STATUS.txt                     # Working tree clean state log
├── TOOLCHAIN_INVENTORY.txt            # System, compilers, binary paths, & SHA-256 hashes
├── CLAIM_TO_EVIDENCE_INDEX.md         # 15-Claim lineage index & evidence taxonomy
├── EXTERNAL_SECURITY_REVIEW_DOSSIER.md # Audit challenge surfaces (this document)
├── SHA256SUMS                         # Cryptographic checksum manifest of all artifacts
├── manifests/
│   ├── cortex_assurance_manifest.json # Formal claim matrix & Corrective Action Register
│   ├── verification_closure_matrix.md # Gate-by-gate verification closure tracking
│   ├── canonical-serialization.md     # Normative CBE byte encoding specification
│   ├── cortex_systems_review_and_phase2_roadmap.md
│   └── reconstruction_audit_log.md
├── logs/
│   ├── certification_suite_raw.log    # Raw output of 136/136 certification suite PASS
│   ├── repository_unittest_raw.log    # Raw output of 288/288 unit test PASS
│   └── coq_verification_raw.log      # Raw output of Coq proof compilation & zero-admit audit
├── formal/
│   ├── *.v                            # Coq formal proof source specifications
│   └── *.vo                           # Compiled Coq proof objects
├── traces/
│   ├── rtl_trace.json                 # 6-step Verilator execution trace
│   └── emulator_trace.json            # 6-step Rust emulator execution trace
└── corpus/
    ├── f4c_evidence_corpus/           # 5 Golden evidence bundle test cases
    └── cbe_vectors/                   # Cross-runtime canonical binary test vectors
```

---

## 5. Verification Command Summary

Auditors can independently verify the baseline using the following standard execution entry points:

```bash
# 1. Run full 136-check integrated certification suite
python3 tests/conformance/run_certification.py

# 2. Run full 288-test repository unit test suite
python3 -m unittest discover -s tests

# 3. Audit Coq formal proofs (verify 0 axioms / 0 admits)
make -C verification
```
