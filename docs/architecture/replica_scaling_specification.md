# Architecture Specification: Multi-Replica Worker Scaling, Linearizable Lease Fencing & Semantic Commit Domains

> **Governance Status**: `SCALING DESIGN` — `ARCHITECTURAL REVIEW: CONDITIONAL APPROVAL`  
> **Implementation Status**: `BLOCKED UNTIL SPEC AMENDMENTS & PHASES 1–3 VERIFIED`  
> **Pre-requisite Gate**: Must survive evaluation against the frozen Cortex v0.3.0-experimental-rc1 assurance baseline prior to promotion to mainline.

---

## 1. Architectural Philosophy: Execution Agents vs. Stateless Pods

In traditional web orchestration (e.g., Kubernetes), Pods are treated as interchangeable, stateless worker units. If a Pod dies mid-request, a load balancer can safely retry the request on a peer Pod.

**In Cortex, this assumption is false and unsafe.**

Cortex worker replicas execute causal, spatiotemporally bounded operations with potential **irreversible external side-effects** (hardware actuation, state mutations, financial charges). Therefore:

1. **Replicas are Execution Agents**, not interchangeable Pods.
2. **Execution MAY be parallel. Authoritative semantic commitment is serialized per conflict domain, and authoritative witness commitment is totally ordered within each witness domain.**
3. **The Gateway TCB retains absolute ownership of Authority, Leases, and Commitment Ordering.**

```
                         CORTEX GATEWAY TCB (Authority & Commit)
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       │                            │                            │
       ▼                            ▼                            ▼
 Replica Controller         Assignment & Lease Engine     Recovery Controller
 (Lifecycle & Health)     (Linearizable Fencing Epochs)  (State Classification)
       │                            │                            │
       └────────────────────────────┼────────────────────────────┘
                                    ▼
                         Worker Registry / Pools
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
       Worker A                Worker B                Worker C
  (Gen 7, Lease 101)      (Gen 7, Lease 104)      (Gen 7, Lease 109)
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                        Domain Commit Sequencer
                                    │
                      ┌─────────────┴─────────────┐
                      ▼                           ▼
                Effect Ledger               Witness Chain
                      │                           │
                      └─────────────┬─────────────┘
                                    ▼
                           Independent Verifier
```

---

## 2. Separate Coordinate Models: Identity & Ownership

Execution attempts and invocation ownership represent fundamentally different concepts and MUST NOT be interchanged.

### 1. Execution Identity (Worker Runtime Coordinate)
$$\text{ExecutionIdentity} = (\text{ReplicaGroupID}, \text{ReplicaInstanceID}, \text{ReplicaGeneration}, \text{ExecutionAttemptID})$$

### 2. Ownership Identity (Gateway Lease Coordinate)
$$\text{OwnershipIdentity} = (\text{InvocationID}, \text{LeaseID}, \text{LeaseEpoch})$$

> **Normative Invariant**: `InvocationID` identifies the semantic invocation. `ExecutionAttemptID` identifies a particular execution attempt. `LeaseEpoch` identifies ownership authority for that attempt. These identifiers MUST NOT be interchangeable.

---

## 3. Normative System Invariants

### Invariant 1: Capability Sub-Set Bound ($\Lambda_{\text{replica}} \subseteq \Lambda_{\text{deployment}}$)
Scaling worker replicas MUST NEVER automatically expand system authority. Every worker replica instance inherits the identical frozen capability envelope:
$$\Lambda_{\text{replica}} \subseteq \Lambda_{\text{deployment}}$$

### Invariant 2: Linearizable Lease Fencing & Monotonic Authority
- **Monotonic Authority**: Wall-clock timestamps (`ExpiryTimestamp`) MAY trigger operational recovery timeouts, but MUST NOT establish authority invalidation. The Gateway's monotonic `LeaseEpoch` is authoritative.
- **Linearizable Fencing**: Lease fencing MUST be linearizable at the Gateway ownership boundary. A commit and lease revocation MUST NOT both succeed for the same invocation.

If Worker $A$ (Epoch $e$) stalls, the Gateway increments $\text{LeaseEpoch} \to e + 1$ and re-assigns the lease to Worker $B$. If Worker $A$ attempts a late commit under stale epoch $e$, the Gateway MUST atomically reject the commit with `ERR_STALE_LEASE_EPOCH`.

### Invariant 3: Non-Cloning of Live Authorization State
Replica replacement MUST NOT clone live execution tokens, lease credentials, or ephemeral authorization state from a prior replica. Each replica instance receives fresh, execution-specific authorization from the Gateway.

### Invariant 4: Non-Replay of Actuated Operations
Unacknowledged in-flight requests from a failed or disconnected worker MUST NOT be naively re-routed. The Gateway Recovery Controller MUST classify invocation state into exactly one of four recovery buckets:

```
UNACKNOWLEDGED REQUEST
        │
        ├── 1. UNADMITTED (Not admitted to authorization)
        │       └── Action: Safe Retry on Peer Replica
        │
        ├── 2. ADMITTED_UNACTUATED (Authorized, but effect not initiated)
        │       └── Action: Retry only under Fenced Recovery Protocol
        │
        ├── 3. ACTUATED_COMMITTED (Effect executed and recorded)
        │       └── Action: NEVER Replay (Return Recorded Result)
        │
        └── 4. ACTUATION_UNKNOWN (Effect initiated, outcome unconfirmed)
                └── Action: Transition to `Verdict.INDETERMINATE`
                    (NO AUTOMATIC RETRY FOR NON-IDEMPOTENT EFFECTS)
```

---

## 4. Invocation Ownership & Recovery State Machine

Every invocation passing through the Gateway follows a strict state transition model. `RECOVERY_REQUIRED` acts as an explicit observation state during worker failure:

```
                       ┌────────────────────────┐
                       │        QUEUED          │
                       └───────────┬────────────┘
                                   │ Assign Worker & LeaseEpoch
                                   ▼
                       ┌────────────────────────┐
                       │        ASSIGNED        │ ──────► [RECOVERY_REQUIRED]
                       └───────────┬────────────┘              │
                                   │ Worker Acknowledges       │
                                   ▼                           ▼
                       ┌────────────────────────┐      classify_recovery()
                       │        RUNNING         │ ───► ├── UNADMITTED
                       └───────────┬────────────┘      ├── ADMITTED_UNACTUATED
                                   │ Gateway Auth      ├── ACTUATED_COMMITTED
                                   ▼                   └── ACTUATION_UNKNOWN
                       ┌────────────────────────┐              │
                       │       AUTHORIZED       │ ─────────────┤
                       └───────────┬────────────┘              │
                                   │ Actuation                 │
                                   ▼                           │
                       ┌────────────────────────┐              │
                       │       ACTUATING        │ ─────────────┘ (INDETERMINATE)
                       └───────────┬────────────┘
                                   │ Gateway Commit
                                   ▼
                       ┌────────────────────────┐
                       │       COMMITTED        │
                       └────────## 5. Disjoint Ordering Domains & Semantic Conflict Model

Cortex explicitly decouples ordering into five disjoint domains:

```
Transport Sequence (L2 Stream)
       ≠
Client Invocation Sequence (L3 Request)
       ≠
Execution Completion Order (Worker Finish Timing)
       ≠
Commit Sequence (Gateway Canonical Commit)
       ≠
Witness Sequence (Evidence Chain)
```

### Semantic Conflict & Ordering Rule
> **Normative Rule**: Canonical commit ordering provides evidence ordering, but does NOT by itself guarantee semantic determinism for stateful operations. Operations that access overlapping mutable state MUST additionally satisfy an ordering, locking, version-validation, or commutativity rule.

- **Witness Chain Generation**: Workers MUST NOT independently advance the authoritative witness chain. Only the Gateway commit sequencer appends authoritative witness state upon commit.

---

## 6. Worker Lifecycle & Graceful Drain Protocol

Worker instances transition through a 6-stage lifecycle:

```
[READY] ──► [DRAINING] ──► [QUIESCED] ──► [TERMINATING] ──► [TERMINATED]
                │
                └─► (timeout: drain_deadline) ──► [FORCED_RECOVERY]
```

1. **`READY`**: Normal operation; worker receives new invocation assignments.
2. **`DRAINING`**: Worker receives **zero new invocations**. Existing assigned invocations continue execution until `drain_deadline`.
3. **`FORCED_RECOVERY`**: Triggered if `drain_deadline` expires before `owned_invocations == 0`. Outstanding invocations are classified via the crash recovery state machine.
4. **`QUIESCED`**: Worker satisfies:
   $$\text{owned\_invocations} == 0 \quad \text{AND} \quad \text{pending\_effects} == 0 \quad \text{AND} \quad \text{ipc\_outstanding} == 0$$
   where $\text{pending\_effect} \in \{\text{AUTHORIZED}, \text{ACTUATING}, \text{outcome\_unresolved}\}$.
5. **`TERMINATING`**: Gateway sends `SIGTERM` to process group.
6. **`TERMINATED`**: Worker process reaped; socket descriptor closed.

---

## 7. Admission Control & Bounded Resource Backpressure

> **Normative Rule**: Scaling MUST NOT relax bounded-memory guarantees. Queue limits, per-replica inflight limits, and global admission limits MUST remain enforced when `max_replicas` is reached.

When `max_replicas` is reached and system load spikes:
- Gateway applies explicit **Backpressure** (rejecting or shedding non-critical intents).
- Autoscaler decision function incorporates hysteresis and critical age metrics:
  $$\text{AutoscaleTrigger} = f(\text{queue\_depth}, \text{queue\_growth}, \text{oldest\_authorized\_uncommitted\_age}, \text{p95\_latency}, \text{worker\_saturation})$$

---

## 8. Verification Roadmap & Explicit Scaling Gates (RS-1 to RS-12)

Implementation must proceed strictly in 10 phases. Autoscaling and routing code are **BLOCKED** until Phases 1–3 pass all RS-1 to RS-12 verification gates:

### Phased Roadmap
```
1. Worker Identity & Generation (ReplicaInstanceID, ReplicaGeneration)
  └─► 2. Durable Invocation Ownership & Fenced Lease Protocol (LeaseEpoch)
        └─► 3. Worker Lifecycle State Machine (READY ➔ DRAINING ➔ QUIESCED ➔ TERMINATING)
              └─► 4. Capability-Filtered Candidate Assignment & Routing
                    └─► 5. Drain Protocol & Deadline Enforcement
                          └─► 6. Crash State Classification Engine (RECOVERY_REQUIRED)
                                └─► 7. Gateway Canonical Commit Sequencer & Conflict Validation
                                      └─► 8. Witness Chain Integration
                                            └─► 9. Multi-Replica Security & Fencing Tests
                                                  └─► 10. Autoscaler & Admission Control
```

### Verification Gates (RS-1 through RS-12)
- **RS-1 (Replica Identity)**: Generation and attempt coordinate separation.
- **RS-2 (Lease Fencing)**: Stale epoch commit rejection (`ERR_STALE_LEASE_EPOCH`).
- **RS-3 (Invocation Ownership)**: Single-owner lease invariants.
- **RS-4 (Crash Classification)**: Non-replay of actuated operations & `Verdict.INDETERMINATE` flags.
- **RS-5 (Commit Ordering)**: Conflict validation & canonical commit sequence.
- **RS-6 (Witness Ordering)**: Total witness chain ordering.
- **RS-7 (Drain Correctness)**: Quiescence verification & forced recovery timeouts.
- **RS-8 (Backpressure)**: Bounded queue enforcement under max replica saturation.
- **RS-9 (Capability Non-Expansion)**: Assert $\Lambda_{\text{replica}} \subseteq \Lambda_{\text{deployment}}$.
- **RS-10 (Multi-Replica Adversarial)**: Anti-impersonation, stale worker reconnect, and cross-replica token reuse tests.
- **RS-11 (Deterministic Replay)**: 100% trace replay parity under multi-worker parallel execution.
- **RS-12 (Chaos/Recovery)**: Random `SIGKILL` injection during actuation cycles.

### Required Invariant Assertions
```text
NO_UNAUTHORIZED_EFFECT
NO_STALE_LEASE_COMMIT
NO_DUPLICATE_NON_IDEMPOTENT_EFFECT
NO_SILENT_INVOCATION_LOSS
NO_WITNESS_FORK
NO_AUTHORITY_EXPANSION
BOUNDED_RESOURCE_USAGE
```

---

## 9. Declarative Configuration Schemas & Code Examples

### 1. Python SDK Configuration Schema (`cortex.schema.scaling`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List

class BackpressureStrategy(str, Enum):
    REJECT_NEW = "reject_new"          # Reject new intents when max_queue_depth is reached
    SHED_LOW_PRIORITY = "shed_low_priority"

class SchedulingStrategy(str, Enum):
    LEAST_CONCURRENT = "least_concurrent"
    ROUND_ROBIN = "round_robin"

@dataclass(frozen=True)
class LeasePolicy:
    """Governs linearizable lease epochs and ownership fencing."""
    lease_ttl_sec: float = 10.0          # Max lease ownership duration before recovery evaluation
    heartbeat_interval_sec: float = 2.0  # L2 IPC ping/ack health check frequency
    max_lease_renewals: int = 5          # Max renewals before mandatory re-authorization

@dataclass(frozen=True)
class ReplicaPolicy:
    """Governs worker replica pool limits, draining, and admission bounds."""
    min_replicas: int = 2
    max_replicas: int = 5
    drain_deadline_sec: float = 30.0     # Max time in DRAINING state before FORCED_RECOVERY
    max_queue_depth: int = 100           # Global queue limit for bounded memory backpressure
    backpressure_strategy: BackpressureStrategy = BackpressureStrategy.REJECT_NEW
    scheduling_strategy: SchedulingStrategy = SchedulingStrategy.LEAST_CONCURRENT
    lease_policy: LeasePolicy = field(default_factory=LeasePolicy)

@dataclass(frozen=True)
class ReplicaGroupDeploymentSpec:
    """Complete deployment specification for a multi-replica plugin group."""
    plugin_name: str
    plugin_version: str
    entrypoint: List[str]
    capability_envelope: List[str]       # Fixed capability bound (Lambda_replica <= Lambda_deployment)
    replica_policy: ReplicaPolicy = field(default_factory=ReplicaPolicy)
```

### 2. JSON Declarative Manifest (`deployment.json`)

```json
{
  "$schema": "https://cortex.dev/schemas/v0.3/deployment.json",
  "name": "GoDatabaseServiceGroup",
  "version": "1.0.0",
  "plugin": {
    "entrypoint": ["./plugins/go_db/db_worker"],
    "capability_envelope": ["database:write", "database:read"]
  },
  "scaling": {
    "min_replicas": 2,
    "max_replicas": 10,
    "scheduling_strategy": "least_concurrent",
    "drain_deadline_sec": 30.0
  },
  "lease": {
    "lease_ttl_sec": 10.0,
    "heartbeat_interval_sec": 2.0
  },
  "admission_control": {
    "max_queue_depth": 200,
    "backpressure_strategy": "reject_new",
    "max_inflight_per_replica": 10
  }
}
```

### 3. YAML Kubernetes-Style Specification (`cortex-deployment.yaml`)

```yaml
apiVersion: cortex.dev/v0.3
kind: ReplicaGroupDeployment
metadata:
  name: billing-engine-java
  version: 2.1.0
spec:
  plugin:
    entrypoint: ["java", "-jar", "./bin/BillingEngine.jar"]
    capabilities: ["finance:charge", "audit:log"]
  replicas:
    min: 2
    max: 6
    drainDeadlineSeconds: 20
    schedulingStrategy: "least_concurrent"
  lease:
    ttlSeconds: 5.0
    heartbeatSeconds: 1.0
  admissionControl:
    maxQueueDepth: 100
    backpressure: "reject_new"
```

