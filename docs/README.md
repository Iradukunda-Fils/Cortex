# Cortex Developer Documentation Portal

Welcome to the **Cortex Platform** master technical documentation portal.

Cortex is a spatiotemporal authority and semantic verification framework designed to enforce execution integrity, capability-negotiated sandboxing, and post-facto deterministic verification across autonomous software runtimes and AI agent architectures.

---

## 📚 Central Documentation Navigation Taxonomy

```text
docs/
├── getting-started/                   # Developer Onboarding & Setup Guides
│   ├── quickstart.md                  # 5-minute developer tutorial
│   ├── setup.md                       # Local environment setup & verify.sh guide
│   └── cli.md                         # Cortex CLI command reference
├── architecture/                      # Kernel Core System Architecture Specifications
│   ├── overview.md                    # Core System Architecture & Security Boundary
│   ├── resource-authority.md          # Heterogeneous Resource Vector & Authority FSM
│   ├── worker_execution_model.md      # Worker Lifecycle & Placement Mechanics
│   └── canonical-serialization.md      # Cortex-CBE Formal Grammar & Serialization
├── security/                          # Authoritative Security Dossiers & Threat Registers
│   ├── cortex_external_security_review_dossier.md # Authoritative Security Review Dossier
│   ├── cortex_security_and_threat_register.md     # System Threat Register & Mitigation Matrix
│   ├── threat_model.md                # Capability Sandbox Threat Vector Model
│   └── gate_a_physical_execution_isolation.md    # Physical Process & Container Isolation
├── verification/                      # Coq Formal Proof Inventories & Verification Theorems
│   ├── coq_formal_proof_inventory_delta.md       # Coq Refinement Proof Inventory (0 Axioms)
│   ├── verification_closure_matrix.md            # Phase 8 Verification Closure Matrix
│   └── gate_verification_guide.md                 # 5-Gate Automated Verification Guide
├── spec/                              # Normative Control Plane & Security Specifications
│   ├── configuration_and_control_plane_specification.md # Configuration & Control Plane Spec
│   ├── phase_4_routing_and_dispatch_specification.md    # Phase 4 Routing & Dispatch Spec
│   ├── phase_5_load_balancing_specification.md          # Phase 5 Dynamic Load Balancer Spec
│   └── v03_architecture_gate_spec.json       # Machine-Readable Architecture Gate Spec
├── governance/                        # Project Work Registers, Quality Policies & Roadmaps
│   ├── cortex_open_work_register.md   # Open Work Obligations & Priority Backlog
│   ├── cortex-developer-contract.md   # Platform Developer & Kernel Safety Contract
│   └── api-stability-policy.md        # Public SDK Stability Policy (SemVer Guarantees)
├── release/                           # Versioned Release Artifacts (v0.2.0 to v1.0.0-RC1)
│   ├── v0.5.0.md                      # v0.5.0 Runtime Baseline Release Document
│   ├── v0.6.0.md                      # v0.6.0 Formal Assurance Release Document
│   └── v1.0.0-rc1.md                  # v1.0.0-RC1 Frozen Candidate Security Record
├── adrs/                              # Architectural Decision Records
├── guides/                            # Developer & Plugin Authoring Guides
├── operations/                        # Operational Runbooks & Release Pipelines
└── history/                           # Historical Audit Logs & System Reconstruction Reports
```

---

## 🚀 Quick Navigation Links

### 1. Onboarding & Setup
- **[5-Minute Quickstart Guide](getting-started/quickstart.md)**: Build Cortex applications and custom plugins using the Python SDK (`cortex.*`).
- **[Developer Environment Setup](getting-started/setup.md)**: Environment setup instructions for contributors (`uv sync`, `python3 tests/conformance/run_certification.py`).
- **[CLI Reference Documentation](getting-started/cli.md)**: Command reference for `cortex init`, `workflow run`, `inspect`, and `replay`.

### 2. Architecture & Kernel Specifications
- **[Kernel Architecture Overview](architecture/overview.md)**: System philosophy, dual-layer framing, 4-layer security boundary, and Mermaid diagrams.
- **[ResourceAuthority Specification](architecture/resource-authority.md)**: Heterogeneous resource vector algebra, reservation FSM, and capacity bounds.
- **[Worker Execution Model](architecture/worker_execution_model.md)**: Worker lifecycle management, process containment, and capability isolation.
- **[Cortex-CBE Serialization Specification](architecture/canonical-serialization.md)**: EBNF count grammar, IEEE 754 float rules, Unicode NFC normalization, and key sorting.

### 3. Authoritative Security & Governance Portals
- **[Authoritative External Security Dossier](security/cortex_external_security_review_dossier.md)**: Master evidence package for auditor sign-off and 17-boundary dual-column matrix.
- **[System Security & Threat Register](security/cortex_security_and_threat_register.md)**: Comprehensive threat vector analysis and mitigation catalog.
- **[Open Work Register & Governance Obligations](governance/cortex_open_work_register.md)**: Tracking issue #23 gate, issue #37 hardware track, and issue status.
- **[Public SDK API Stability Policy](governance/api-stability-policy.md)**: SemVer guarantees and the frozen public symbol boundary.

### 4. Verification & Specifications
- **[Coq Formal Proof Inventory](verification/coq_formal_proof_inventory_delta.md)**: Machine-checked zero-axiom Coq proof theorems and forward simulation relations.
- **[Master Verification Closure Matrix](verification/verification_closure_matrix.md)**: Verification status across formal proofs, runtime tests, and property fuzzing.
- **[Configuration & Control Plane Spec](spec/configuration_and_control_plane_specification.md)**: Declarative snapshot identity normalization and security ceiling enforcement.
- **[Phase 5 Load Balancing Spec](spec/phase_5_load_balancing_specification.md)**: FSM load balancing, worker capability routing, and incarnation fencing.

### 5. Release Documents & Version History
- **[Release Records Index](release/)**: Complete release documentation for all deployed tags (`v0.2.0`, `v0.2.1`, `v0.3.0`, `v0.4.0`, `v0.5.0`, `v0.6.0`, `v1.0.0-rc1`).
