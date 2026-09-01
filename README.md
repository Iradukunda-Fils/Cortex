<p align="left">
  <img src="docs/assets/images/cortex-logo.png" alt="Cortex Logo" width="95" align="left" style="margin-right: 18px; margin-bottom: 10px;" />
  <h1 style="border: none; margin: 0; padding: 0;">Cortex Platform</h1>
  <h3 style="border: none; margin: 4px 0 10px 0; font-weight: 600; font-size: 1.15em;">Spatiotemporal Authority & Semantic Verification Framework</h3>
  <a href="https://pypi.org/project/cortex-runtime/"><img src="https://img.shields.io/pypi/v/cortex-runtime.svg" alt="PyPI Version"></a> <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python Version"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"></a> <a href="https://github.com/microsoft/pyright"><img src="https://img.shields.io/badge/type--checking-pyright-brightgreen.svg" alt="Type Checked: Pyright"></a> <a href="scripts/verify.sh"><img src="https://img.shields.io/badge/Verification%20Gate-566%2F566%20PASS-brightgreen.svg" alt="Verification Gate: 566/566 PASS"></a>
</p>
<br clear="left"/>

> **Cortex** is a spatiotemporal authority and semantic verification framework designed to enforce execution integrity, capability-negotiated sandboxing, and post-facto deterministic verification across autonomous software runtimes and AI agent architectures.

---

## 🚀 Current Milestone & Release Train Status

$$\boxed{ \text{v0.5.0} \rightarrow \text{v0.6.0} \rightarrow \text{v1.0.0-RC1} } \quad \text{with} \quad \Delta \text{Architecture} = 0$$

- **Current Milestone**: `v1.0.0-RC1` (Release Candidate 1 — Active Architecture Freeze).
- **External Security Gate**: Governed by **Issue #23** (External Security Review & Audit Sign-off).
- **Verification Status**: 566/566 tests pass cleanly; Phase 8.0 Coq formal proofs machine-checked with **0 Axioms / 0 Admits**.

| Release Version | Release Status | Primary Milestone Deliverables | Release Documentation |
| :--- | :--- | :--- | :--- |
| **`v1.0.0-RC1`** | **Release Candidate** | Frozen baseline prepared for external security audit gate (Issue #23) | [`cortex_open_work_register.md`](docs/architecture/cortex_open_work_register.md) |
| **`v0.6.0`** | Formal Proof Milestone | Phase 8.0 Machine-Checked Refinement Proofs & WASM Profile B | [`coq_formal_proof_inventory_delta.md`](docs/architecture/coq_formal_proof_inventory_delta.md) |
| **`v0.5.0`** | Durable Authority Baseline | Dynamic Load Balancing, Write-Ahead Logging & Placement Subsystem | [`replica_scaling_specification.md`](docs/architecture/replica_scaling_specification.md) |
| **`v0.4.0-experimental`** | Experimental Baseline | Multi-tier IPC channels and streaming message codec | [`v0.3.0-experimental.md`](docs/release/v0.3.0-experimental.md) |
| **`v0.2.1`** | Production Release | Host gateway admission control & execution state machine | [`cortex_completed_work_register.md`](docs/architecture/cortex_completed_work_register.md) |
| **`v0.2.0`** | Initial Release | Core Python control plane and capability context baseline | [`cortex_system_architecture_current.md`](docs/architecture/cortex_system_architecture_current.md) |

---

## 📖 System Architecture & Security Layers

Traditional security architectures rely on static user identity roles (POSIX permissions, IAM roles, cgroups) which fail under non-deterministic AI agent workloads and dynamic plugin executions:
* **Ambient Authority Leakage**: Agents executing inside shell environments inherit full ambient process permissions, allowing unmediated filesystem or network access.
* **Subshell Script Bypasses**: Malicious or miscalibrated plugins invoke shell scripts (`.sh`), subprocesses, or eval blocks to bypass application-level checks.
* **Trace Non-Repudiation**: Without cryptographic trace verification, auditing *why* an autonomous agent performed a destructive side-effect is impossible.

Cortex replaces ambient authority with a **Hardware/Kernel-Enforced Security Boundary**:

```text
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 1. STATIC CAPABILITY NEGOTIATION & STCR MAPPING (ConfigResolver)                            │
 │ Manifests declare required permissions before plugins access the kernel bus.                │
 └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                │ SignedIntent Payload (CBE Format)
                                                ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 2. RESOURCE AUTHORITY & PHYSICAL CONTAINMENT GATE (ResourceAuthority / Cgroups v2)          │
 │ Attenuated resource vectors enforce R_task <= R_plugin <= R_system limits.                  │
 └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                │ Governed Side-Effect Execution
                                                ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 3. ROLLING CAUSAL WITNESS JOURNALING & WAL (Durable Write-Ahead Logging)                     │
 │ Emits tamper-evident rolling hash commitments: W_{t+1} = SHA256(W_t || D_E || D_I)          │
 └──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                │ Raw Evidence Traces (R, E)
                                                ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────┐
 │ 4. ZERO-DEPENDENCY INDEPENDENT UNTRUSTED VERIFIER (tools/cortex_verifier.py)                  │
 │ Standalone CLI tools/cortex-verifier evaluates traces ➔ VALID (0), INVALID (1), INDETERMINATE │
 └───────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ Repository Map & Documentation Taxonomy

The repository follows a strict **Separation of Concerns** taxonomy across security, formal verification, protocol specs, governance, and release records:

```text
Cortex Platform Repository Map
├── docs/                                    # Master Documentation Portal
│   ├── architecture/                        # Architectural Audits & Verification Matrices
│   │   ├── cortex_open_work_register.md     # Master Issue & Engineering Obligation Register
│   │   ├── coq_formal_proof_inventory_delta.md # Phase 8.0 Machine-Checked Proof Inventory
│   │   ├── coq_print_assumptions_audit.json # Audit JSON Artifact (0 Axioms / 0 Admits)
│   │   ├── configuration_and_control_plane_specification.md # Control Plane Spec
│   │   └── phase_4_routing_and_dispatch_specification.md    # Routing Protocol Spec
│   │
│   ├── spec/                                # Normative Protocol Specifications
│   │   ├── gate_g_remediation_specification.md # Worker Sandbox Architecture
│   │   ├── gate_h_execution_token_specification.md # ExecutionToken Spec (P2)
│   │   └── evidence_profile_v1.schema.json  # Evidence Profile JSON Schema
│   │
│   ├── release/                             # Historical & Milestone Release Records
│   │   └── v0.3.0-experimental.md           # Experimental Baseline Record
│   │
│   └── history/                             # Historical Audits & Post-Implementation Logs
│
├── .github/                                 # GitHub Actions Workflows & Templates
├── cortex/                                  # Python Control Plane & Kernel Subsystem
├── verification/                            # Coq Formal Verification Source (.v files)
├── tests/                                   # Full Test Suite (566 Unit & Conformance Tests)
├── scripts/                                 # Verification & Build Automation Scripts
│   ├── verify.sh                            # Master 7-Gate Canonical Verification Pipeline
│   └── verify_coq_assumptions.py            # Coq Proof Assumptions Audit Script
└── tools/                                   # Verification & Audit CLI Tools
    ├── cortex_verifier.py                   # Zero-Dependency Verifier CLI
    └── tools/assurance/docs_audit.py        # Repository Documentation Coherence Audit
```

---

## 🛡️ Safety Invariants Matrix ($P1$–$P4$)

| Security Invariant | Mathematical / Normative Definition | Status | Verification Engine & Test Harness |
| :--- | :--- | :---: | :--- |
| **$P1$: Authority Attenuation** | $\Lambda_{t+1} \subseteq \Lambda_t \land \vec{R}_{\text{task}} \le \vec{R}_{\text{plugin}} \le \vec{R}_{\text{system}}$ | **IMPLEMENTED** | `ConfigResolver` & `ResourceAuthority` cgroups v2 |
| **$P2$: Execution Parity** | $D_3 \equiv D_2 \equiv \text{SHA256}(\text{CBE}(\text{SignedIntent}))$ | **VERIFIED** | Gate H Conformance Suite (`test_gate_h_adversarial.py`) |
| **$P3$: Causal Witness** | $W_{t+1} = \text{SHA256}(W_t \parallel \text{CBE}(E_{t+1}) \parallel \text{CBE}(I_{t+1}))$ | **VERIFIED** | Gate I Tamper-Evident Suite (`test_gate_i_causal_witness.py`) |
| **$P4$: Independent Verifier** | $\text{Verify}(R, E) \to \{\text{VALID, INVALID, INDETERMINATE}\}$ | **VERIFIED** | Untrusted Verifier Engine (`tools/cortex_verifier.py`) |

---

## ⚡ Contributor Quickstart & Verification Commands

### 1. Development Environment Setup (via Astral `uv`)
Clone the repository and synchronize the isolated virtual environment:

```bash
git clone https://github.com/Iradukunda-Fils/Cortex.git
cd Cortex
uv venv && source .venv/bin/activate
uv sync --all-extras
```

### 2. Run Canonical 7-Gate Verification Pipeline
Execute the full master quality, linting, type-checking, test, and documentation audit pipeline:
```bash
./scripts/verify.sh
```

### 3. Run Static Code Analysis & Documentation Audit
```bash
# Code quality check
uv run ruff check .

# Strict static type checking
uv run pyright

# Documentation coherence audit
uv run python3 tools/assurance/docs_audit.py
```

### 4. Build PyPI Distribution Packages
Construct wheel and source distribution artifacts for PyPI release:
```bash
uv build
```

---

## 💻 Developer Code Example: Governed Task Execution

Here is how an application creates a task context, resolves configuration ceilings, and enforces resource attenuation:

```python
from cortex.tools.kernel.config_resolver import ConfigResolver

# 1. Initialize Resolver with Declared Security Profile
resolver = ConfigResolver()

# 2. Resolve Configuration with Strict Security Ceiling
config = resolver.resolve(
    profile_name="Profile_A_Linux_Strict",
    declared_manifest={
        "plugin_id": "com.cortex.analytics",
        "capabilities": ["STORAGE_READ", "COMPUTE_EXEC"],
        "resources": {"cpu_cores": 2.0, "memory_mib": 2048}
    }
)

# 3. Assert Attenuation Limits (R_task <= R_plugin <= R_system)
print(f"✅ Configuration Resolved: {config.snapshot_id}")
print(f"🔒 Enforced RAM Limit: {config.resources['memory_mib']} MiB")
```

---

## 📄 Licensing & Governance

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.
See **[Contributor Guide](CONTRIBUTING.md)** for contribution policies.
