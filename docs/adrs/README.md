# Cortex Architectural Design Records (ADR) Index

This directory contains the formal Architectural Design Records (ADRs) governing the evolution of the Cortex execution kernel.

---

## ADR Lifecycle Status Table

| ADR ID | Title | Revision Status | Status | Primary Artifact |
|---|---|---|---|---|
| **ADR-003** | Polyglot Execution Kernel & Language-Neutral Semantic Contract | Revision #5 | **FROZEN** | [`ADR-003-polyglot-kernel.md`](ADR-003-polyglot-kernel.md) |
| **ADR-002** | Capability Sandboxing & Intercept Proxy Model | v0.2.0 | **SUPERSEDED** | Embedded in [`../architecture/threat_model.md`](../architecture/threat_model.md) |
| **ADR-001** | Core Event Model & Workflow Lifecycle | v0.1.0 | **HISTORICAL** | Embedded in [`../architecture/overview.md`](../architecture/overview.md) |

---

## Architectural Reference Documents

For modular reference guides extracted from ADR-003, see:
- [Cortex-CBE Canonical Serialization Rules](../architecture/canonical-serialization.md)
- [4-Domain Identity Model & Derivation Formulas](../architecture/identity-model.md)
- [Replay State Machine & Recovery Evidence Model](../architecture/recovery-and-state.md)
- [Machine-Readable Gate Specification Spec](../gate-specs/v03_architecture_gate_spec.json)
