# Cortex Architecture Decision Register (ADR Index)

> **Governance Principle**: Document major decisions, rejected alternatives, empirical evidence, and future reconsideration criteria.  

---

## 1. ADR Summary Index

| ADR ID | Title | Status | Decision Summary | Primary Trade-Off | Reconsideration Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ADR-001** | Monotonic Lease Epoch Fencing | **APPROVED** | Adopt Gateway-assigned monotonic `LeaseEpoch` ($e \to e+1$) for worker ownership verification. Reject wall-clock authority. | Sacrifices wall-clock convenience for strict split-brain prevention ($ERR\_STALE\_LEASE\_EPOCH$). | Reconsider if single Gateway host becomes a distributed bottleneck requiring multi-master consensus. |
| **ADR-002** | CRC32 Binary Frame WAL Engine | **APPROVED** | Adopt CRC32-checksummed append-only WAL with `os.fsync()` and tail truncation recovery. | Higher write latency per transaction ($\sim 1-5ms$ per fsync) for crash safety guarantees. | Reconsider if write throughput requirements exceed 100k ops/sec on single NVMe disk; introduce asynchronous group commit WAL. |
| **ADR-003** | Capability-Based Routing via Inverted Index | **APPROVED** | Maintain `CapabilityIndex` mapping capability string $\to$ worker set $W_c$. | Memory allocation overhead for index vs $O(1)$ capability lookup time. | Reconsider if capability combinations exceed 10,000 unique sets. |
| **ADR-004** | Snapshot Read Views ($V = f(S_A)$) | **APPROVED** | Support optional point-in-time snapshot reads of capability index to reduce lock wait latency during candidate selection. | Brief snapshot copy allocation vs lock contention reduction under high thread concurrency ($C \ge 16$). | Reconsider when sharded worker pools are introduced. |
| **ADR-005** | cgroups v2 Physical Containment with Degraded Fallback | **APPROVED** | Enforce kernel `cgroups v2` resource limits when available; fall back to unconstrained process execution with warnings when non-root. | Operational flexibility across OS environments vs potential resource leakage in unprivileged dev environments. | Reconsider if strict security isolation requires containerized Docker/WASM sandboxes for all dev environments. |
| **ADR-006** | Declarative Field-Class Normalization | **APPROVED** | Canonicalize configuration fields into ASCII snake_case identifiers, NFC text, and sorted sets. | Minor resolution parsing latency vs elimination of Unicode alias injection vulnerabilities. | Immutable contract; non-reconsiderable. |
| **ADR-007** | Batched Expiration Sweep (Candidate G) | **APPROVED / PROMOTED** | Adopt $O(K+N)$ Candidate G batched expiration sweep engine as default (`use_batched_sweep=True`). Retain baseline linear scan for rollback. | Single terminal invariant check post-batch vs per-item invariant validation loop. | Reconsider if machine-checked theorem invalidates batch invariant monotonicity. |

---

## 2. ADR Detailed Summaries

### ADR-001: Monotonic Lease Epoch Fencing
- **Context**: In distributed execution, worker processes can experience arbitrary GC pauses or network delays. Relying on wall-clock expiration leads to split-brain double-actuation.
- **Decision**: The Gateway retains monotonic authority (`LeaseEpoch`). Reassignments increment epoch $e \to e + 1$. Workers must submit $e$ with task commits.
- **Evidence**: `tests/conformance/test_load_balancer_hardening_gate.py` passes 100% of stale commit injection tests.

### ADR-002: Durable CRC32 Frame WAL Engine
- **Context**: Unexpected process termination during state mutation can corrupt disk state.
- **Decision**: All state mutations are written as framed binary records with 32-bit CRC. Every write is followed by `os.fsync()`.
- **Evidence**: `tests/conformance/test_phase6_wal_adversarial_gate.py` verifies recovery across 50 corrupted write injection scenarios.

### ADR-007: Batched Expiration Sweep (Candidate G) as Production Default
- **Context**: Per-item `check_invariants()` inside the expiration sweep loop created an $O(K \cdot N)$ lock-hold bottleneck at scale ($N \ge 1000$).
- **Decision**: Adopt Candidate G batched transitions with single terminal invariant check as default (`use_batched_sweep=True`). Retain baseline linear scan (`use_batched_sweep=False`) for instant rollback. Defer Candidate E (Min-Heap) until combined evaluation.
- **Evidence**: 112/112 pytest kernel suite passing. Empirical speedup envelope: 1.43x ($N=10$), 15.31x ($N=100$), 56.65x ($N=1000$), 261.95x ($N=3000$). $\Delta S_A = 0$.

