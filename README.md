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
| 🌐 [**Component Communication Topology**](docs/architecture/cortex_component_communication_topology.md) | Low-level asynchronous IPC, CBE wire framing, and sequence diagrams. |

---

## ⚡ Developer Quickstart & Installation

### 📦 1. Installing `cortex-runtime`

#### Stable Releases (PyPI)
```bash
# Using uv (Recommended)
uv add cortex-runtime

# Using pip
pip install cortex-runtime
```

#### Pre-Release Candidates (e.g. `v0.7.0rc1`)
```bash
# Using uv (allow latest pre-release candidate)
uv add --prerelease=allow cortex-runtime

# Using uv (install exact pre-release version)
uv add cortex-runtime==0.7.0rc1

# Using pip (allow latest pre-release candidate)
pip install --pre cortex-runtime

# Using pip (install exact pre-release version)
pip install cortex-runtime==0.7.0rc1
```

### 🛠️ 2. Local Repository Development Setup

#### Option A: Setup via `uv` (Recommended)
```bash
git clone https://github.com/Iradukunda-Fils/Cortex.git
cd Cortex
uv venv && source .venv/bin/activate
uv sync --all-extras
```

#### Option B: Setup via Standard `pip`
```bash
git clone https://github.com/Iradukunda-Fils/Cortex.git
cd Cortex
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 🚀 3. Deploying Pre-Releases to PyPI

To build and deploy a pre-release candidate (such as `v0.7.0rc1`) to PyPI:
```bash
# 1. Build distribution artifacts locally using uv
uv build

# 2. Assign release candidate tag & push to GitHub (triggers keyless PyPI OIDC publish)
git tag -a v0.7.0rc1 -m "Release Candidate v0.7.0rc1"
git push origin v0.7.0rc1
```

### 🧪 4. Run Verification & Test Suite
```bash
# Run canonical 7-gate verification pipeline
./scripts/verify.sh

# Run Rust emulator test suite
cargo test --manifest-path cortex-emulator/Cargo.toml

# Run Go CBE codec conformance suite
cd cortex-go && go test -v ./...
```

---

## 💻 Developer Code Example: Governed Effect Execution

```python
# ---------------------------------------------------------------------------
# Example A: High-Level Workflow Client & Capability Sandboxing
# ---------------------------------------------------------------------------
from cortex import CortexClient, Capability, WorkflowState

# 1. Define explicit Capability objects for sandboxed execution
read_cap = Capability(name="fs:read")
test_cap = Capability(name="exec:pytest")
plan_cap = Capability(name="workflow:plan:create")

# 2. Initialize Cortex Client with granted capability names
client = CortexClient(platform_capabilities={read_cap.name, test_cap.name, plan_cap.name})
print(f"Active Platform Capabilities ({len(client.platform_capabilities)}):", sorted(list(client.platform_capabilities)))

# 3. Inspect active workflow execution states
print("Supported Workflow States:", [state.value for state in WorkflowState])


# ---------------------------------------------------------------------------
# Example B: Low-Level Governed Kernel Effect Request & CAS Store
# ---------------------------------------------------------------------------
from cortex.tools.kernel.effect_gateway import EffectRequest
from cortex.tools.kernel.effect_runtime import ContentAddressableStore

# 1. Formulate unprivileged EffectRequest payload
req = EffectRequest(
    invocation_id="inv_1001",
    capability="mcp:stdio",
    operation="read_record",
    arguments=b'{"record_id": "rec_9901"}',
    resource_id="adapter.mcp.stdio.v1",
    lease_epoch=1,
    worker_generation=1,
)
print(f"Formulated EffectRequest (Resource: {req.resource_id}, Op: {req.operation})")

# 2. Spool large evidence payload into ContentAddressableStore (CAS)
cas = ContentAddressableStore()
ref_key = cas.put(b"Large evidence payload content", owner_id=req.invocation_id)
retrieved_data = cas.get(ref_key, requester_id=req.invocation_id)
print(f"CAS Reference Key: {ref_key}")
print(f"Retrieved CAS Payload: {retrieved_data.decode('utf-8')}")
```

---

## 📄 Licensing

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.
