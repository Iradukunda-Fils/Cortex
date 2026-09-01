# Cortex Core System Architecture Overview

> **Cortex** is a deterministic, secure, and resource-safe Developer Platform and Execution Runtime designed for AI workloads, worker process orchestration, and polyglot execution.

---

## 1. High-Level System Architecture

Cortex is designed around a single-host, high-reliability control plane managing local and containerized worker processes:

```
[ Application / SDK Client ]
           │
           ▼
[ Cortex Gateway TCB (Single-Host Control Plane) ]
   ├── ConfigResolver & Capability Matcher
   ├── CapabilityIndex (Inverted Capability Sets W_c)
   ├── ProductionDynamicLoadBalancer (Worker Registry & Task Assignment)
   ├── ResourceAuthority (Vector Resource Vector Allocation & Expiration)
   └── WriteAheadLog (Durable Frame Storage with CRC32 Verification)
           │
           ▼
[ Worker Execution Enforcer (Tier 3 Containment) ]
   ├── Linux cgroups v2 Controller (/sys/fs/cgroup/cortex)
   ├── Subprocess Driver & Monotonic Lease Epoch Fencing
   └── Worker Process Sandbox
```

---

## 2. Security & Safety Model

Security in Cortex is strictly separated into three non-interchangeable tiers:

1. **Tier 1: Logical Authorization**: Dynamic matching of `Task.capabilities` against `Worker.capabilities`.
2. **Tier 2: Runtime Enforcement**: Monotonic `LeaseEpoch` validation and `InvocationLedger` tracking to eliminate stale worker actuation.
3. **Tier 3: Physical Isolation**: `cgroups v2` containment (`memory.max`, `cpu.max`, `pids.max`) on Linux root environments. Under `strict_mode=True`, missing physical containment causes execution rejection (`ERR_CONTAINMENT_FAILED`).

---

## 3. Scalability & Performance Model

- **Worker Selection**: Optimized from $O(N)$ linear scans to $O(1)$ inverted index lookups (`CapabilityIndex`) and unlocked Snapshot Read Views ($V=f(S_A)$).
- **Resource Allocation**: Atomic vector resource allocations ($\text{CPU}, \text{RAM}, \text{GPU}$) under `ResourceAuthority`.
- **Durable Authority**: WAL binary record framing with atomic disk fsync to guarantee crash safety.

---

## 4. Documentation Suite Index

For deep-dive technical reports, verification matrices, and research decision packages, consult:

- [Full System Architecture Audit](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_full_system_architecture_audit.md)
- [Security Architecture & Threat Register](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_security_and_threat_register.md)
- [Scalability Envelope & Benchmark Report](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_scalability_envelope.md)
- [Maintainability Assessment & Technical Debt Register](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_maintainability_assessment.md)
- [Resource Safety Matrix](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_resource_safety_matrix.md)
- [Dependency & Ownership Graph](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_dependency_and_ownership_graph.md)
- [Contradiction & Truth Reconciliation Register](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_contradiction_register.md)
- [Architecture Decision Register (ADR Index)](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_architecture_decision_register.md)
- [Long-Term Evolution Roadmap](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_long_term_evolution_roadmap.md)
- [Scheduler Concurrency & Authority Scalability Research Gate](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_scheduler_concurrency_and_authority_scalability_research_gate.md)
- [Scheduler Concurrency Decision Package](file:///home/iradukunda/Lost/Projects/Future/Cortex/docs/architecture/cortex_scheduler_concurrency_decision_package.md)
