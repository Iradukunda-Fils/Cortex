# Phase 4 Architecture Audit Report

> **Audit Target**: Phase 4 Routing & Dispatch Subsystem (`docs/architecture/phase_4_routing_and_dispatch_specification.md`)  
> **Audit Status**: `DESIGN APPROVED / IMPLEMENTATION BLOCKED`  
> **Auditor**: Architecture Review Pass (Pre-Implementation Gate)  
> **Baseline Commit**: Frozen Phase 1–3 Baseline SHA `56afb86` (307/307 tests pass)

---

## 1. Audit Summary & Architectural Invariants

This audit evaluates the Phase 4 Routing & Dispatch design against 12 critical distributed-systems requirements identified during the architectural review.

### Governance Status Matrix

```text
Phase 1–3 Control Plane Kernel:     FROZEN & APPROVED (SHA: 56afb86, 307/307 PASS)
Phase 4 Specification:             DESIGN APPROVED
Phase 4 Audit Report:              APPROVED
Phase 4 Code Implementation:       STRICTLY BLOCKED
Load Balancing & Autoscaling:      STRICTLY BLOCKED
```

---

## 2. Detailed Audit Findings (AUD4-01 through AUD4-12)

| ID | Focus Area | Architectural Requirement | Specification Status | Compliance Evidence / Design Gate |
| :--- | :--- | :--- | :---: | :--- |
| **AUD4-01** | **TOCTOU Lease Race** | Candidate proposed by Router must be atomically revalidated inside `LeaseManager.grant_lease()` TCB lock against `WorkerRef.lifecycle_version` before lease assignment. | **DESIGN APPROVED** | §3: Atomic revalidation checks worker existence, `lifecycle_version`, `stage==READY`, generation, hash, profile, capabilities, and inflight limit. |
| **AUD4-02** | **Ordering Separation** | `LeaseEpoch` is scoped per-invocation lineage and must NOT be used to order cross-invocation completion. | **DESIGN APPROVED** | §5.1: Explicitly removes `LeaseEpoch` from cross-invocation completion ordering. Keeps `ExecutionCompletionOrder` and `CommitSequence` distinct. |
| **AUD4-03** | **Zero-Candidate Queue & Fairness** | Reconcile zero-candidate policy with bounded queue semantics (`ERR_NO_ELIGIBLE_WORKER_NOW` vs `ERR_QUEUE_FULL` / `ERR_QUEUE_TIMEOUT`) and FIFO fairness. | **DESIGN APPROVED** | §4.3: Internal dispatch condition `ERR_NO_ELIGIBLE_WORKER_NOW` causes FIFO enqueueing; external rejections issued only on queue full or timeout. |
| **AUD4-04** | **State Conflict Fencing** | Explicitly classify operations into Unordered, Ordered, Version-Fenced, or Serialized State Domains using `StateDomainKey`. | **DESIGN APPROVED** | §5.2: `StateDomainKey` schema defined (`domain_hash = sha256(ns:path:key)`) with 4 execution classes. |
| **AUD4-05** | **Zero-Authority Boundary** | Router operates strictly on derived eligibility metadata and is prohibited from holding bearer tokens, capability keys, or TCB mutation APIs. | **DESIGN APPROVED** | §1.1, §1.2: Revocable proposal invariant and explicit possession prohibitions defined. |
| **AUD4-06** | **Routing Decision Events** | `RoutingDecisionEvent` is purely observational audit evidence appended to `WitnessSequence`; does not carry bearer tokens or advance commit state. | **DESIGN APPROVED** | §6.1: Schema defined; purely observational witness log entry. |
| **AUD4-07** | **6-Component Decomposition** | Clear boundary separation into `CandidateResolver`, `RoutingPolicy`, `LeaseManager`, `Dispatcher`, `RecoveryEngine`, and `CommitSequencer`. | **DESIGN APPROVED** | §2: Component responsibility matrix and pipeline sequence diagram formalize 6 distinct roles. |
| **AUD4-08** | **Precise Inflight Definition** | Standardized inflight definition across Router, Lifecycle Tracker, and Gateway TCB: non-terminal assigned invocations. | **DESIGN APPROVED** | §4.2: Formal mathematical set definition $\text{Inflight}(W) \equiv \| \{ I \mid I.\text{state} \notin \text{TERMINAL} \land I.\text{worker} == W \} \|$. |
| **AUD4-09** | **UNADMITTED Safety** | Invariant $\text{UNADMITTED} \implies \neg\text{Authorized} \land \neg\text{ActuationStarted}$ enforced before re-queueing post-assignment crash. | **DESIGN APPROVED** | §3: Re-queue permitted only when ledger proves authorization and actuation boundaries were uncrossed. |
| **AUD4-10** | **Full Config Identity** | Candidate context includes `WorkerRef` with `instance_id`, `lifecycle_version`, `config_generation`, `config_hash`, `sandbox_profile_hash`, `capability_envelope_hash`. | **DESIGN APPROVED** | §4.1: Immutable `WorkerRef` versioned dataclass specified. |
| **AUD4-11** | **Bounded Router Memory** | Router memory bounded to $O(\text{ActiveInvocations} + \text{ReadyWorkers})$. Telemetry streams to log/disk; not accumulated in RAM. | **DESIGN APPROVED** | §6.1: Non-bypassable memory ceiling and event streaming requirement enforced. |
| **AUD4-12** | **Authoritative Commit Path** | Routing proposals can NEVER bypass Gateway commit verification. Path remains `Router -> LeaseManager -> Worker -> Gateway -> CommitSequencer -> Witness`. | **DESIGN APPROVED** | §5.1: Commit Path Invariant explicitly prohibits direct routing-to-commit shortcuts. |

---

## 3. Expanded Verification Gate Plan (RD-1 through RD-22)

When code implementation is authorized in the future, the test suite must pass all 22 verification gates:

- **RD-1**: Unprivileged Router Boundary Isolation
- **RD-2**: Monotonic ConfigGeneration Filtering
- **RD-3**: ConfigHash Mismatch Rejection
- **RD-4**: Capability Envelope Containment
- **RD-5**: Worker Lifecycle Readiness Filter
- **RD-6**: Least-Inflight Selection Policy
- **RD-7**: Bounded FIFO Queue Fairness & Handling
- **RD-8**: Atomic Revalidation Gate at LeaseManager Boundary
- **RD-9**: Post-Assignment Worker Crash Recovery
- **RD-10**: State Domain Key Conflict Fencing
- **RD-11**: Queue Capacity Ceiling Enforcement
- **RD-12**: Routing Decision Provenance Logging
- **RD-13**: TOCTOU Candidate Draining Race
- **RD-14**: TOCTOU ConfigGeneration Increment Race
- **RD-15**: TOCTOU ConfigHash Mismatch Race
- **RD-16**: Pre-Grant Worker Death Race
- **RD-17**: Pre-Grant Inflight Capacity Breach Race
- **RD-18**: Parallel State Conflict Fencing
- **RD-19**: Per-Invocation Lease Scope Isolation
- **RD-20**: Bounded Metadata Memory
- **RD-21**: Deterministic Tie-Breaking Verification
- **RD-22**: Router Zero-Token Possession Isolation

---

## 4. Final Audit Verdict

```text
PHASE 4 ARCHITECTURE SPECIFICATION: DESIGN APPROVED
PHASE 4 ARCHITECTURE AUDIT:         DESIGN APPROVED (12/12 AUD4 findings resolved)
CODE IMPLEMENTATION STATUS:         STRICTLY BLOCKED PENDING AUTHORIZATION
```
