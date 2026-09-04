<p align="left">
  <img src="docs/assets/images/cortex-logo.png" alt="Cortex Logo" width="95" align="left" style="margin-right: 18px; margin-bottom: 10px;" />
  <h1 style="border: none; margin: 0; padding: 0;">Cortex Framework</h1>
  <h3 style="border: none; margin: 4px 0 10px 0; font-weight: 600; font-size: 1.15em;">Spatiotemporal Authority, Capability-Security & Semantic Verification Framework</h3>
  <a href="https://pypi.org/project/cortex-runtime/"><img src="https://img.shields.io/pypi/v/cortex-runtime.svg" alt="PyPI Version"></a> <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python Version"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"></a> <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/managed--with-uv-purple.svg" alt="Managed with uv"></a> <a href="docs/architecture/cortex_release_readiness_final.md"><img src="https://img.shields.io/badge/Release%20Status-RC%20READY%20(v0.7.0rc1)-brightgreen.svg" alt="Release Candidate Status"></a>
</p>
<br clear="left"/>

> **Cortex** is an open-source, capability-secured spatiotemporal authority and formal verification framework for autonomous workflows, AI agents, and microservices. It enforces fail-closed physical containment, cryptographic witness journaling, content-addressed evidence tracking, and machine-checked invariant safety across polyglot execution runtimes.

---

## 🚀 Release Candidate Baseline (`v0.7.0rc1`)

Cortex `v0.7.0rc1` represents the frozen Release Candidate for the **External Effects Subsystem & Physical Containment Kernel**.

$$\boxed{\text{Audited Commit: } \texttt{ec317eb120d0ac1274029361c6b9ac1d78fa52b5}} \quad \vert \quad \boxed{\text{Release Identity: } \texttt{v0.7.0rc1}}$$

```
+--------------------------------------------------------------------------------------+
|                        RELEASE CANDIDATE METADATA & ARTIFACTS                        |
+--------------------------------------------------------------------------------------+
| Git Tag          | v0.7.0rc1                                                         |
| Tag Target Commit| ec317eb120d0ac1274029361c6b9ac1d78fa52b5                          |
| Working Tree     | Clean (git status --porcelain is empty)                           |
| Package Version  | cortex-runtime 0.7.0rc1 (pyproject.toml)                          |
| Rust Emulator    | 0.1.0 (cortex-emulator/Cargo.toml)                                |
| Wheel SHA256     | 91af4ea2140b30ad4452e612d7ca3665d70bf02a7d889475260d9f6b731db66e  |
| Source Tar SHA256| c557a9186d9fdbb99494fe79465e7ed4ab497a12d8d607c4f1dd23d9db06b60e  |
+--------------------------------------------------------------------------------------+
```

---

## 🏛️ Governing Architectural Invariants

Cortex is built on a zero-trust, capability-attenuated kernel governed by two fundamental principles:

$$ \boxed{\textbf{Authority Decides}} \quad \text{and} \quad \boxed{\textbf{Adapter Executes}} $$

```
                                  CANONICAL EXECUTION FLOW
                                  
[ CortexClient ]
       │
       ▼ (1. Reserve Capacity Vector: RAM, CPU, PIDs)
[ ResourceAuthority ] ─── Validates host capacity & issues reservation_id
       │
       ▼ (2. Restrict Capabilities & Issue HMAC Token)
[ GatewayAuthorizationGate ] ─── Computes HMAC execution_token & context
       │
       ▼ (3. Launch Contained Subprocess Worker)
[ WorkerSupervisor ] ─── Setsid, unshares netns/PID, attaches cgroup v2
       │
       ▼ (4. Subprocess Execution)
[ Worker Process ] ─── Formulates EffectRequest (NO secrets embedded)
       │
       ▼ (5. Secure Execution Pipeline)
[ EffectExecutionPipeline ]
   ├── A. Replay Lookup (EffectResultStore)
   ├── B. Gateway Credential Resolution (CredentialBroker vault)
   ├── C. Adapter Invocation (ResourceContract)
   ├── D. Authoritative CAS Spooling (if evidence > 4KiB)
   └── E. Reconcile State (EffectReconciliationEngine)
       │
       ▼ (6. Physical Side-Effect Actuation)
[ External System / Resource ]
```

---

## 📚 Architecture & Truth Documentation Index

For comprehensive systems engineering analysis, low-level security audits, and truth matrices, refer to the authoritative architecture documentation portal:

| Document | Purpose & Key Topics |
| :--- | :--- |
| 📋 [**Documentation Truth Audit**](docs/architecture/cortex_documentation_truth_audit.md) | Authoritative inventory, claim tracing matrix, and tier classification across all docs. |
| 🔬 [**Architecture Consistency Report**](docs/architecture/cortex_architecture_consistency_report.md) | DSRP mental model, execution path, low-level security audit fixes, and master truth matrix. |
| 🔌 [**API & Plugin Contract Status**](docs/architecture/cortex_api_and_plugin_contract_status.md) | Boundaries between Native Plugins (`BasePlugin`), Subprocess Workers, and Adapters. |
| 🛡️ [**Deployment Truth Matrix**](docs/architecture/cortex_deployment_truth_matrix.md) | OS kernel dependencies (Landlock LSM, cgroups v2, NetNS), degradation rules & environments. |
| 🏁 [**Release Readiness Final Report**](docs/architecture/cortex_release_readiness_final.md) | Immutable commit binding, defect resolution register, and final release sign-off. |
| ⚙️ [**Release Process & Governance**](docs/release/cortex_release_process_and_governance.md) | Normative 6-step release protocol, PyPI OIDC publishing, and release gates. |
| 🔒 [**CI/CD Security & Scalability Audit**](docs/architecture/cortex_cicd_security_and_scalability_audit.md) | Audit of GitHub Actions workflows, OIDC authentication, and least-privilege security. |
| 📜 [**CBE Transport Specification**](docs/architecture/cbe_transport_architecture.md) | Canonical Binary Encoding transport protocol, frame layout, and wire grammar. |
| ⚖️ [**Resource Authority Specification**](docs/architecture/resource-authority.md) | Capacity vector accounting, reservation lifecycle, and formal proof alignment. |

---

## 🧪 Authoritative Test Accounting Battery

$$\sum \text{Targeted Release Integrity Battery} = \mathbf{297 / 297 \text{ PASSED}} \quad (100\% \text{ Pass Rate})$$

| Scope / Suite | Runner / Command | Runtime | Unique Tests | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Python Conformance Suite** | `python3 -m unittest discover -s tests/conformance` | Python 3.10+ | **222 Tests** | **PASSED** |
| **Reference Plugin Integration**| `python3 -m unittest discover -s examples/secure_external_effect_plugin/tests` | Python 3.10+ | **14 Tests** | **PASSED** |
| **MCP Secure Application Suite**| `python3 -m unittest discover -s examples/mcp_secure_effect_app/tests` | Python 3.10+ | **11 Tests** | **PASSED** |
| **Rust Emulator Suite** | `cargo test --manifest-path cortex-emulator/Cargo.toml` | Rust 2021 | **32 Tests** | **PASSED** |
| **Go CBE Conformance Suite** | `cd cortex-go && go test -v ./...` | Go 1.20+ | **18 Tests** | **PASSED** |
| **Ruff Code Quality & Linter** | `uv run ruff check .` | AST Analyzer | **0 Errors** | **PASSED** |

> *Note on Test Accounting*: Historical test counts (e.g. 566/650) represented combined multi-runner execution snapshots across legacy targets. The 297 unique tests above represent the exact, complete release integrity battery for `v0.7.0rc1`.

---

## 📐 Formal Verification & Coq Proof Scope

* **Proof Workspace**: `./verification/`
* **Coq Source Modules**: **29 `.v` files**
* **Axiom & Admit Count**: **0 Axioms, 0 Admits**
* **Key Machine-Checked Proofs**:
  * **Phase 4 Routing Safety**: `rd_f6_unadmitted_safety` & `rd_f13_unadmitted_safe_retry` (`Phase4RoutingRefinement.v`)
  * **Phase 5 Simulation**: `phase5_simulation_forward_simulation` (`Phase5Simulation.v`)
  * **Phase 6 Durability**: `phase6_wal_prefix_refinement` (`Phase6WALSafety.v`)
  * **Phase 8 Vector Safety**: `phase8_resource_authority_capacity_safety` (`Phase8ResourceAuthorityConcrete.v`)
  * **Concrete Refinement**: `Phase8ResourceAuthorityConcrete.v` machine-checks concrete Python `ResourceAuthority` logic against abstract Coq models.

---

## 🛡️ Explicit Security Evidence Taxonomy

| Security Control | Exact Evidence Level Classification | Implementation Source |
| :--- | :--- | :--- |
| **CBE Allocation Safety** | `Code Implemented` + `Runtime Verified` (Go & Python decoders) | `cortex-go/cbe/decoder.go`, `cortex/cbe/decoder.py` |
| **Worker Process Group Termination** | `Code Implemented` + `Runtime Verified` (`os.killpg`) | `cortex/tools/kernel/enforcement/supervisor.py` |
| **CAS Evidence Ownership** | `Code Implemented` + `Runtime Verified` (Pipeline Spooling) | `cortex/tools/kernel/effect_runtime.py` |
| **Gateway Capability Fencing** | `Coq Model Proven` + `Concrete Implementation Tested` | `cortex/tools/kernel/effect_gateway.py` |
| **Resource Vector Ceilings** | `Coq Model Proven` + `Refinement Proven` + `Tested` | `cortex/tools/kernel/resource_authority.py` |
| **cgroups v2 Containment** | `Code Implemented` (Kernel Verified when cgroups v2 present) | `cortex/tools/kernel/enforcement/cgroup.py` |
| **Network Namespace Isolation** | `Code Implemented` (Kernel Verified when `unshare` permitted) | `cortex/tools/kernel/enforcement/netns.py` |
| **Profile A Landlock Sandbox** | `Code Implemented in Rust` + `Rust Runtime Verified` | `cortex-emulator/src/sandbox.rs` |
| **Polyglot Boundary** | `Known Limitation` (Native plugins Python-only; Go/Rust via stdio/IPC) | `cortex/plugin.py`, `cortex/tools/kernel/adapters/` |

---

## ⚡ Developer Quickstart

### 1. Environment Setup & Installation

#### Option A: Using `uv` (Recommended — High Performance)
```bash
git clone https://github.com/Iradukunda-Fils/Cortex.git
cd Cortex
uv venv && source .venv/bin/activate
uv sync --all-extras
```

#### Option B: Using Standard `pip` & Virtual Environment
```bash
git clone https://github.com/Iradukunda-Fils/Cortex.git
cd Cortex
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Run Quality & Test Pipeline
```bash
# Run Python Linter
uv run ruff check .

# Run Conformance Test Suite
uv run python -m unittest discover -s tests/conformance

# Run Reference Plugin & App Suites
uv run python -m unittest discover -s examples/secure_external_effect_plugin/tests
uv run python -m unittest discover -s examples/mcp_secure_effect_app/tests

# Run Rust Emulator & Go Codecs
cargo test --manifest-path cortex-emulator/Cargo.toml
cd cortex-go && go test -v ./...
```

### 3. Build Distribution Packages
```bash
uv build
```

---

## 💻 Developer Code Example: Governed Effect Execution

```python
from cortex.client import CortexClient
from cortex.tools.kernel.effect_gateway import CapabilitySet, SignedIntent

# 1. Initialize Cortex Client with strict capability bounds
client = CortexClient(
    granted_capabilities=CapabilitySet({"STORAGE_READ", "HTTP_REQUEST"}),
    host_memory_ceiling_mb=1024,
)

# 2. Formulate signed intent payload
intent = SignedIntent(
    resource_id="adapter.mcp.stdio.v1",
    operation_type="read_record",
    arguments={"record_id": "rec_9901"},
)

# 3. Execute governed effect through secure pipeline
outcome = client.execute_effect(intent)

print(f"Status: {outcome.status}")  # ExecutionStatus.EFFECT_CONFIRMED
if outcome.evidence:
    print(f"Evidence (Ref: {outcome.evidence.is_reference}): {outcome.evidence.data.decode('utf-8')}")
```

---

## 📄 Licensing & Governance

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.  
See [cortex_release_readiness_final.md](docs/architecture/cortex_release_readiness_final.md) for the authoritative release readiness sign-off.
