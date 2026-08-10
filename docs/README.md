# Cortex Developer Documentation Portal

Welcome to the **Cortex Platform** developer documentation hub.

Cortex is a spatiotemporal authority and semantic verification framework designed to enforce execution integrity, capability-negotiated sandboxing, and post-facto deterministic verification across autonomous software runtimes and AI agent architectures.

---

## 📚 Documentation Index

### 🚀 Getting Started
- **[5-Minute Quickstart Guide](quickstart.md)**: Get started building Cortex applications and custom plugins using the pure Python SDK (`cortex.*`).
- **[CLI Reference Documentation](cli.md)**: Standard CLI command usage (`cortex init`, `workflow run`, `inspect`, `replay`).

### 🛠️ Developer Guides
- **[Plugin Authoring Guide](guides/plugin-authoring.md)**: Canonical guide for third-party plugin authors covering `PluginManifest`, capability checks (`has_capability`), event propagation, and causal lineage.
- **[Developer Environment Setup](development/setup.md)**: Step-by-step instructions for contributors (`uv sync`, `./scripts/verify.sh`, pre-commit hooks).

### 🏛️ Architecture & Governance Policies
- **[Architecture & Security Model](architecture/overview.md)**: System philosophy, dual-layer framing, 3-layer security boundary, and structural Mermaid diagrams.
- **[API Stability Policy](architecture/api-stability-policy.md)**: SemVer 2.0.0 rules, pre/post-1.0 stability guarantees, deprecation lifecycle, and the frozen 21-symbol public boundary.
- **[Plugin Manifest Specification](manifest_spec.md)**: `PluginManifest` schema (JSON/YAML), standard capability namespaces, and capability negotiation lifecycle states.

### 🔬 Operational Reports & Evidence
- **[v0.2 Dogfood Operational Evidence Report](operations/v0.2-dogfood-report.md)**: Empirical stress test and performance profile results (602 events/1.66s, 2.61MB peak RSS).

---

## 🔬 Academic Research & Proof Substrate

- **`verification/`**: Interactive theorem prover (Coq 8.18) formal proof scripts.
- **`cortex-emulator/`**: Hardware state machine emulator (Rust crate).
- **`rtl/`**: SystemVerilog RTL pipeline simulation models.
