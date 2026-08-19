# Cortex Developer Documentation Portal

Welcome to the **Cortex Platform** developer documentation hub.

Cortex is a spatiotemporal authority and semantic verification framework designed to enforce execution integrity, capability-negotiated sandboxing, and post-facto deterministic verification across autonomous software runtimes and AI agent architectures.

---

## 📚 Central Navigation Taxonomy

```
docs/
├── getting-started/                   # Onboarding & Setup
│   ├── quickstart.md                  # 5-minute developer tutorial
│   ├── setup.md                       # Local environment setup & verify.sh guide
│   └── cli.md                         # Cortex CLI command reference
├── architecture/                      # Kernel Specifications & Architecture
│   ├── overview.md                    # Core System Architecture & Security Boundary
│   ├── systems-engineering-qa-guide.md# Low-Level Systems, IPC, Polyglot & Systems Q&A Guide
│   ├── canonical-serialization.md      # Cortex-CBE Formal Grammar & Serialization
│   ├── identity-model.md              # 4-Domain Identity Taxonomy & UUIDv5 Derivation
│   ├── recovery-and-state.md          # Replay State Machine & Recovery Evidence Model
│   ├── threat_model.md                # Capability Sandbox Threat Model
│   └── api-stability-policy.md        # Public SDK Surface Policy (21 Frozen Symbols)
├── adrs/                              # Architectural Design Records
│   ├── README.md                      # ADR Index & Lifecycle Status Matrix
│   └── ADR-003-polyglot-kernel.md     # Revision #5 FROZEN Polyglot Execution Contract
├── gate-specs/                        # Contract Enforcement & Verification Gates
│   ├── v03_architecture_gate_spec.json# Machine-Readable Gate Specification (FROZEN)
│   └── gate_verification_guide.md     # Human-Readable 5-Gate Verification Guide
├── guides/                            # Developer & Plugin Guides
│   ├── plugin-authoring.md            # Canonical Plugin Development Guide
│   └── manifest-specification.md      # Plugin Manifest Schema Specification
└── operations/                        # Operations & Deployment Reports
    ├── pypi_deployment.md             # Automated OIDC PyPI Release Pipeline
    └── v0.2-dogfood-report.md         # Dogfood Execution & Benchmark Profile Report

research/                              # Empirical Research & Spikes Substrate
└── README.md                          # Research Index & Empirical Data Map
```

---

## 🚀 Quick Navigation Links

### 1. Onboarding & Setup
- **[5-Minute Quickstart Guide](getting-started/quickstart.md)**: Get started building Cortex applications and custom plugins using the pure Python SDK (`cortex.*`).
- **[Developer Environment Setup](getting-started/setup.md)**: Step-by-step setup instructions for contributors (`uv sync`, `./scripts/verify.sh`).
- **[CLI Reference Documentation](getting-started/cli.md)**: Command reference for `cortex init`, `workflow run`, `inspect`, and `replay`.

### 2. Architecture & Kernel Specifications
- **[Kernel Architecture Overview](architecture/overview.md)**: System philosophy, dual-layer framing, 3-layer security boundary, and structural Mermaid diagrams.
- **[Systems Engineering & Q&A Guide](architecture/systems-engineering-qa-guide.md)**: Low-level IPC mechanics, Linux sandboxing, polyglot worker contracts, 50+ plugin scaling, ML/GPU zero-copy DMA, and technical Q&A reference.
- **[Cortex-CBE Serialization Specification](architecture/canonical-serialization.md)**: EBNF count grammar, IEEE 754 float rules, Unicode NFC normalization, and key sorting.
- **[4-Domain Identity Model](architecture/identity-model.md)**: Logical vs. Idempotency vs. Application vs. Runtime identity separation, CBE tuple framing, and cleanroom test vectors.
- **[Replay State Machine & Recovery Evidence](architecture/recovery-and-state.md)**: Evidence model, command execution lifecycle phases, and $P_{\text{semantic}}$ projection.
- **[Public SDK API Stability Policy](architecture/api-stability-policy.md)**: SemVer guarantees and the frozen 21-symbol public boundary.
- **[Capability Sandbox Threat Model](architecture/threat_model.md)**: Capability security sandbox threat vector analysis.

### 3. Architectural Design Records & Gate Specs
- **[ADR Index](adrs/README.md)**: Index of all Cortex Architectural Design Records.
- **[ADR-003 Polyglot Execution Kernel Spec](adrs/ADR-003-polyglot-kernel.md)**: Revision #5 FROZEN contract specification for cross-runtime execution parity.
- **[Machine Spec (JSON)](gate-specs/v03_architecture_gate_spec.json)**: Machine-readable gate specification for automated enforcement.
- **[Gate Verification Guide](gate-specs/gate_verification_guide.md)**: Explanation of the 5 canonical verification gates run by `./scripts/verify.sh`.

### 4. Guides & Operational Deployment
- **[Plugin Authoring Guide](guides/plugin-authoring.md)**: Third-party plugin guide (`PluginManifest`, `has_capability`, event propagation, causal lineage).
- **[Plugin Manifest Specification](guides/manifest-specification.md)**: Manifest schema, required capability declarations, and negotiation states.
- **[PyPI Deployment Guide](operations/pypi_deployment.md)**: Automated PyPI release workflow via GitHub Actions and OIDC.
- **[v0.2 Dogfood Operational Report](operations/v0.2-dogfood-report.md)**: Empirical stress test and performance profile results.

### 5. Dedicated Research Directory
- **[Research Substrate Index](../research/README.md)**: Synthesis papers, crash semantics, telemetry benchmarks, and fault-tolerance reports.
