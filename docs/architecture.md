# Cortex Architecture Overview

Cortex enforces semantic execution integrity across autonomous systems through a strict event hierarchy, isolated kernel boundaries, capability sandboxing, and formal verification.

---

## Architectural Principles

1. **Universal Event Hierarchy vs. Verification Isolation**:
   - Core Kernel events (`IntentEvent`, `PlanGeneratedEvent`, `CommandIssuedEvent`, `DriverTelemetryEvent`, `VerificationResultEvent`) derive from `BaseEvent`.
   - `CommitEventV1` belongs exclusively to the verification domain to prevent hardware ISA details from leaking into general workflow orchestration.

2. **Kernel ≠ Verification**:
   - Verification runs as a decoupled service on top of the Kernel Runtime.

3. **Workflows as Execution Boundaries**:
   - All state transitions execute within an explicit `Workflow` lifecycle (`PENDING` -> `RUNNING` -> `COMPLETED`/`FAILED`).

4. **Plugin Sandboxing & Capability Negotiation**:
   - Plugins declare required capabilities in a `PluginManifest`.
   - Runtimes validate grants via `CapabilityNegotiator`. Unregistered capabilities trigger a `CAPABILITY_VIOLATION` verification failure.
