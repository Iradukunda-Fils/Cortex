<p align="left">
  <img src="docs/assets/images/cortex-logo.png" alt="Cortex Logo" width="95" align="left" style="margin-right: 18px; margin-bottom: 10px;" />
  <h1 style="border: none; margin: 0; padding: 0;">Cortex Platform</h1>
  <h3 style="border: none; margin: 4px 0 10px 0; font-weight: 600; font-size: 1.15em;">Spatiotemporal Authority & Semantic Verification Framework</h3>
  <a href="https://pypi.org/project/cortex-runtime/"><img src="https://img.shields.io/badge/version-v1.0.0--RC1-blue.svg" alt="Cortex Version: v1.0.0-RC1"></a> <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python Version"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"></a> <a href="https://github.com/microsoft/pyright"><img src="https://img.shields.io/badge/type--checking-pyright-brightgreen.svg" alt="Type Checked: Pyright"></a> <a href="tests/conformance/run_certification.py"><img src="https://img.shields.io/badge/Certification-566%2F566%20PASS-brightgreen.svg" alt="Certification: 566/566 PASS"></a>
</p>
<br clear="left"/>

> **Cortex** is a spatiotemporal authority and semantic verification framework designed to enforce execution integrity, capability-negotiated sandboxing, and post-facto deterministic verification across autonomous software runtimes and AI agent architectures.

---

## 📖 System Architecture & Design Overview

Traditional security architectures rely on static user identity roles (POSIX permissions, IAM roles, cgroups) which fail under non-deterministic AI agent workloads and dynamic plugin executions:
* **Ambient Authority Leakage**: Agents executing inside shell environments inherit full ambient process permissions, allowing unmediated filesystem or network access.
* **Subshell Script Bypasses**: Malicious or miscalibrated plugins invoke shell scripts (`.sh`), subprocesses, or eval blocks to bypass application-level checks.
* **Trace Non-Repudiation**: Without cryptographic trace verification, auditing *why* an autonomous agent performed a destructive side-effect is impossible.

Cortex replaces ambient authority with a **Hardware/Kernel-Enforced 4-Layer Security Boundary**:

```text
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 1. STATIC CAPABILITY NEGOTIATION & STCR MAPPING (Gate K / ADR-008)                          │
 │ Manifests declare required permissions before plugins access the kernel bus.                │
 └──────────────────────────────┬──────────────────────────────────────────────┘
                                │ SignedIntent Payload (CBE Format)
                                ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 2. EXECUTION TOKEN INTENT PARITY & ACTUATION GATE (Gate H / P2)                             │
 │ Single-use ExecutionTokens bind tokens strictly to intent hashes: D3 == D2                  │
 └──────────────────────────────┬──────────────────────────────────────────────┘
                                │ Governed Side-Effect Execution
                                ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 3. ROLLING CAUSAL WITNESS JOURNALING (Gate I / P3)                                          │
 │ Emits tamper-evident rolling hash commitments: W_{t+1} = SHA256(W_t || D_E || D_I)          │
 └──────────────────────────────┬──────────────────────────────────────────────┘
                                │ Raw Evidence Traces (R, E)
                                ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 4. ZERO-DEPENDENCY INDEPENDENT UNTRUSTED VERIFIER (Gate J / P4)                               │
 │ Standalone CLI tools/cortex-verifier evaluates traces ➔ VALID (0), INVALID (1), INDETERMINATE │
 └───────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ Repository Map & Documentation Architecture

For open-source contributors and systems architects, the codebase is structured logically across normative specifications, security dossiers, verification proofs, and governance registers:

```text
Cortex Platform Architecture Map
├── docs/                                    # Master Technical & Documentation Portal
│   ├── architecture/                        # Kernel Core Architecture Specifications
│   │   ├── overview.md                      # Core System Architecture & Security Boundary
│   │   └── resource-authority.md            # Heterogeneous Resource Vector & Authority FSM
│   ├── security/                            # Authoritative Security Dossiers & Threat Registers
│   │   ├── cortex_external_security_review_dossier.md # Master Security Review Dossier (#23)
│   │   ├── cortex_security_and_threat_register.md     # System Threat Register & Mitigation Matrix
│   │   └── threat_model.md                  # Capability Sandbox Threat Vector Model
│   ├── verification/                        # Coq Formal Proof Inventories & Theorems
│   │   ├── coq_formal_proof_inventory_delta.md       # Coq Refinement Proof Inventory (0 Axioms)
│   │   └── verification_closure_matrix.md            # Phase 8 Formal Verification Status
│   ├── spec/                                # Normative Control Plane & Protocol Specs
│   │   ├── configuration_and_control_plane_specification.md # Control Plane & Schema Spec
│   │   └── phase_5_load_balancing_specification.md          # Dynamic Load Balancer Spec
│   ├── governance/                          # Project Governance, Policies & Work Registers
│   │   ├── cortex_open_work_register.md     # Authoritative Open Work Register & Priority
│   │   └── cortex-developer-contract.md     # Platform Developer & Kernel Safety Contract
│   ├── release/                             # Versioned Release Documentation (v0.2.0 to v1.0.0-RC1)
│   └── adrs/                                # Architectural Decision Records
│
├── tools/                                   # Standalone Tooling & Verification Engines
│   └── cortex_verifier.py                   # Zero-dependency Independent Verifier CLI (Gate J)
│
├── tests/conformance/                       # Conformance & Adversarial Certification Suite
│   ├── test_gate_h_adversarial.py           # Gate H Parity & Replay Protection Tests
│   ├── test_gate_i_causal_witness.py        # Gate I Tamper-Evident Witness Chain Tests
│   ├── test_gate_j_independent_verifier.py # Gate J Verifier Engine Adversarial Tests
│   └── test_wasm_profile_b_sandbox.py       # WASM Profile B Sandbox Conformance Suite
│
├── cortex/                                  # Python Control Plane & Reference Runtime
├── cortex-emulator/                         # Rust STCR Hardware State Machine Emulator
├── cortex-go/                               # Go Layer 2 High-Concurrency Transport Adapter
└── rtl/                                     # SystemVerilog STCR Hardware Pipeline
```

---

## 🛡️ The Safety Invariants Matrix ($P1$–$P4$)

| Security Invariant | Mathematical / Normative Definition | Status | Empirical Verification & Test Harness |
| :--- | :--- | :---: | :--- |
| **$P1$: Authority Attenuation** | $\Lambda_{t+1} \subseteq \Lambda_t \land w_1 \sqsubseteq w_2$ | **PARTIAL** | Python `PluginContext` & Rust `cortex-emulator` STCR. |
| **$P2$: Execution Parity** | $D_3 \equiv D_2 \equiv \text{SHA256}(\text{CBE}(\text{SignedIntent}))$ | **CERTIFIED** | Gate H Scenarios PASS (`test_gate_h_adversarial.py`). |
| **$P3$: Causal Witness** | $W_{t+1} = \text{SHA256}(W_t \parallel \text{CBE}(E_{t+1}) \parallel \text{CBE}(I_{t+1}))$ | **CERTIFIED** | Gate I Scenarios PASS (`test_gate_i_causal_witness.py`). |
| **$P4$: Independent Verifier** | $\text{Verify}(R, E) \to \{\text{VALID, INVALID, INDETERMINATE}\}$ | **CERTIFIED** | Gate J Scenarios PASS (`tools/cortex_verifier.py`). |
| **Complete Mediation (Gate G)** | $\forall \text{eff} \in \text{Effects}, \text{eff} \text{ passes through } \text{ExecutionToken}$ | **SPECIFIED** | Sandbox & Narrow IPC Architecture (`docs/spec/gate_g_remediation_specification.md`). |

---

## ⚡ Contributor Quickstart & Test Commands

### 1. Prerequisites & Environment Setup
Clone the repository and install dependencies via `uv` or standard Python 3.10+:

```bash
git clone https://github.com/Iradukunda-Fils/Cortex.git
cd Cortex
uv venv && source .venv/bin/activate
uv pip install -e .
```

### 2. Run Static Analysis & Type Checking
Ensure 0 type errors across the codebase:
```bash
pyright
```

### 3. Run Test & Conformance Suite
Execute the full unit and conformance suite (566 tests):
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

### 4. Run Independent Verifier Engine CLI
Verify raw untrusted evidence bundles out-of-band without importing runtime modules:
```bash
python3 tools/cortex_verifier.py tests/golden/f4c_evidence_corpus/valid_chain.json
# Output: VERDICT: VALID (0) - EVIDENCE_VERIFIED_VALID
```

---

## 📄 License & Governance

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.
