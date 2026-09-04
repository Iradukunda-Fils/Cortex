<p align="left">
  <img src="docs/assets/images/cortex-logo.png" alt="Cortex Logo" width="95" align="left" style="margin-right: 18px; margin-bottom: 10px;" />
  <h1 style="border: none; margin: 0; padding: 0;">Cortex Framework</h1>
  <h3 style="border: none; margin: 4px 0 10px 0; font-weight: 600; font-size: 1.15em;">Spatiotemporal Authority, Capability-Security & Semantic Verification Framework</h3>
  <a href="https://pypi.org/project/cortex-runtime/"><img src="https://img.shields.io/pypi/v/cortex-runtime.svg" alt="PyPI Version"></a> <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python Version"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0"></a> <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/managed--with-uv-purple.svg" alt="Managed with uv"></a> <a href="docs/architecture/cortex_release_readiness_final.md"><img src="https://img.shields.io/badge/Release-v0.7.0rc1-brightgreen.svg" alt="Release Candidate Status"></a>
</p>
<br clear="left"/>

> **Cortex** is an open-source, capability-secured spatiotemporal authority and formal verification framework for autonomous workflows, AI agents, and microservices. It enforces fail-closed physical containment, cryptographic witness journaling, content-addressed evidence tracking, and machine-checked invariant safety across polyglot execution runtimes.

---

## 🏛️ Architecture & Security Principles

Cortex enforces a zero-trust, capability-attenuated execution kernel governed by two core rules:

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

## 📚 Documentation Portal

For detailed architectural specifications, security audits, and release protocols:

| Document | Description |
| :--- | :--- |
| 📋 [**Documentation Truth Audit**](docs/architecture/cortex_documentation_truth_audit.md) | Authoritative claim tracing matrix across documentation tiers. |
| 🔬 [**Architecture Consistency Report**](docs/architecture/cortex_architecture_consistency_report.md) | Architectural DSRP model, execution path, and low-level security audit fixes. |
| 🔌 [**API & Plugin Contract Status**](docs/architecture/cortex_api_and_plugin_contract_status.md) | Boundaries between Native Plugins (`BasePlugin`), Subprocess Workers, and Adapters. |
| 🛡️ [**Deployment Truth Matrix**](docs/architecture/cortex_deployment_truth_matrix.md) | OS kernel dependencies (Landlock LSM, cgroups v2, NetNS) and environment rules. |
| 🏁 [**Release Readiness Final Report**](docs/architecture/cortex_release_readiness_final.md) | Immutable commit binding, defect resolution register, and final release sign-off. |
| ⚙️ [**Release Process & Governance**](docs/release/cortex_release_process_and_governance.md) | Step-by-step release protocol, PyPI OIDC publishing, and release gates. |
| 🔒 [**CI/CD Security & Scalability Audit**](docs/architecture/cortex_cicd_security_and_scalability_audit.md) | Audit of GitHub Actions workflows, OIDC authentication, and security governance. |

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

### 2. Run Verification & Test Suite
```bash
# Run canonical verification pipeline
./scripts/verify.sh

# Run Rust emulator suite
cargo test --manifest-path cortex-emulator/Cargo.toml

# Run Go CBE suite
cd cortex-go && go test -v ./...
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

## 📄 Licensing

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.
