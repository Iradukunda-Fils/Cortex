# Cortex Platform: Spatiotemporal Authority & Semantic Verification Framework

[![PyPI Version](https://img.shields.io/pypi/v/cortex-runtime.svg)](https://pypi.org/project/cortex-runtime/)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Type Checked: Pyright](https://img.shields.io/badge/type--checking-pyright-brightgreen.svg)](https://github.com/microsoft/pyright)
[![Certification: 74/74 PASS](https://img.shields.io/badge/Certification-74%2F74%20PASS-brightgreen.svg)](tests/conformance/run_certification.py)

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
 │ 1. STATIC CAPABILITY NEGOTIATION & STCR MAPPING (Gate K / ADR-008)                         │
 │ Manifests declare required permissions before plugins access the kernel bus.                 │
 └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                │ SignedIntent Payload (CBE Format)
                                                ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 2. EXECUTION TOKEN INTENT PARITY & ACTUATION GATE (Gate H / P2)                             │
 │ Single-use ExecutionTokens bind tokens strictly to intent hashes: D3 == D2                 │
 └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                │ Governed Side-Effect Execution
                                                ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 3. ROLLING CAUSAL WITNESS JOURNALING (Gate I / P3)                                          │
 │ Emits tamper-evident rolling hash commitments: W_{t+1} = SHA256(W_t || D_E || D_I)          │
 └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                │ Raw Evidence Traces (R, E)
                                                ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 4. ZERO-DEPENDENCY INDEPENDENT UNTRUSTED VERIFIER (Gate J / P4)                             │
 │ Standalone CLI tools/cortex-verifier evaluates traces ➔ VALID (0), INVALID (1), INDETERMINATE│
 └─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ Repository Map & Documentation Architecture

For open-source contributors and systems architects, the codebase is structured logically across normative specifications, architecture records, polyglot engines, and verification suites:

```text
Cortex Platform Architecture Map
├── docs/                                    # Master Technical & Specification Portal
│   ├── architecture/                        # Architectural Audits & Verification Matrices
│   │   ├── verification_closure_matrix.md   # Master Phase 13 Assurance Status Matrix
│   │   ├── gate_g_complete_mediation_inventory.md # Complete Mediation Path Analysis
│   │   └── threat_model.md                  # Threat Vectors & Mitigation Catalog
│   ├── spec/                                # Normative Protocol & Security Specifications
│   │   ├── gate_g_remediation_specification.md # Worker Sandbox & Narrow IPC Architecture
│   │   ├── gate_h_execution_token_specification.md # ExecutionToken & Intent Parity Spec (P2)
│   │   ├── gate_i_causal_witness_specification.md  # Rolling Witness Chain Specification (P3)
│   │   ├── gate_j_independent_verifier_specification.md # Untrusted Verifier Engine Spec (P4)
│   │   └── v03_layer2_streaming_spec.md     # Layer 2 Streaming Protocol Framing
│   └── adrs/                                # Architectural Decision Records
│       └── ADR-008-identity-specification-supersession.md # Identity Supersession (UUIDv5/v7)
│
├── tools/                                   # Standalone Tooling & Verification Engines
│   └── cortex_verifier.py                   # Zero-dependency Independent Verifier CLI (Gate J)
│
├── tests/conformance/                       # Conformance & Adversarial Certification Suite
│   ├── run_certification.py                 # Master 74-Check Conformance Test Runner
│   ├── test_gate_h_adversarial.py           # Gate H Parity & Replay Protection Tests (21/21)
│   ├── test_gate_i_causal_witness.py        # Gate I Tamper-Evident Witness Chain Tests (7/7)
│   └── test_gate_j_independent_verifier.py # Gate J Verifier Engine Adversarial Tests (12/12)
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
| **$P2$: Execution Parity** | $D_3 \equiv D_2 \equiv \text{SHA256}(\text{CBE}(\text{SignedIntent}))$ | **CERTIFIED** | 21/21 Gate H Scenarios PASS (`test_gate_h_adversarial.py`). |
| **$P3$: Causal Witness** | $W_{t+1} = \text{SHA256}(W_t \parallel \text{CBE}(E_{t+1}) \parallel \text{CBE}(I_{t+1}))$ | **CERTIFIED** | 7/7 Gate I Scenarios PASS (`test_gate_i_causal_witness.py`). |
| **$P4$: Independent Verifier** | $\text{Verify}(R, E) \to \{\text{VALID, INVALID, INDETERMINATE}\}$ | **CERTIFIED** | 12/12 Gate J Scenarios PASS (`tools/cortex-verifier.py`). |
| **Complete Mediation (Gate G)** | $\forall \text{eff} \in \text{Effects}, \text{eff} \text{ passes through } \text{ExecutionToken}$ | **SPECIFIED** | Sandbox & Narrow IPC Architecture (`gate_g_remediation_specification.md`). |

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

### 3. Run Master Certification Pipeline
Execute the full 74-check conformance suite covering golden corpus vectors, Coq/Rust/RTL cycle assertions, Gate H parity, Gate I witness, and Gate J verification:
```bash
python3 tests/conformance/run_certification.py
```

### 4. Run Independent Verifier Engine CLI
Verify raw untrusted evidence bundles out-of-band without importing runtime modules:
```bash
python3 tools/cortex_verifier.py tests/conformance/fixtures/evidence_bundle_valid.json
# Output: VERDICT: VALID (0) - EVIDENCE_VERIFIED_VALID
```

---

## 💻 Developer Code Example: End-to-End Governed Execution

Here is how an application mints an intent, acquires an `ExecutionToken`, and enforces $D_3 \equiv D_2$ parity:

```python
import hashlib
from cortex.cbe import encode_cbe

# 1. Define SignedIntent
intent_payload = {
    "body": {
        "intent_type": "STORAGE_WRITE",
        "target_resource": "/data/export.csv",
        "payload": {"bytes": 1024},
        "timestamp_ns": 1776274200000000000
    },
    "authority_pubkey": "PUBKEY_NODE_01",
    "signature": "a3f890b..."
}

# 2. Mint ExecutionToken (D2 = SHA256(CBE(SignedIntent)))
signed_intent_cbe = encode_cbe(intent_payload)
intent_hash_d2 = hashlib.sha256(signed_intent_cbe).hexdigest()
token = {"intent_hash": intent_hash_d2, "epoch": 1, "nonce": "abc123nonce"}

# 3. Actuation Boundary Assertion (D3 == D2)
d3_hash = hashlib.sha256(encode_cbe(intent_payload)).hexdigest()
if d3_hash != token["intent_hash"]:
    raise PermissionError(f"TRAP_INTENT_PARITY_MISMATCH: {d3_hash} != {token['intent_hash']}")

print("✅ Governed Side-Effect Actuated Successfully!")
```

---

## 📄 License & Governance

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.
