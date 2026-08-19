# Architecture Specification: Multi-Replica Worker Scaling, Lease Fencing & Canonical Commit Sequencing

> **Governance Status**: `SCALING DESIGN` — `ARCHITECTURAL REVIEW REQUIRED`  
> **Pre-requisite Gate**: Must survive evaluation against the frozen Cortex v0.3.0-experimental-rc1 assurance baseline prior to promotion to mainline.

---

## 1. Architectural Philosophy: Execution Agents vs. Stateless Pods

In traditional web orchestration (e.g., Kubernetes), Pods are treated as interchangeable, stateless worker units. If a Pod dies mid-request, a load balancer can safely retry the request on a peer Pod.

**In Cortex, this assumption is false and unsafe.**

Cortex worker replicas execute causal, spatiotemporally bounded operations with potential **irreversible external side-effects** (hardware actuation, state mutations, financial charges). Therefore:

1. **Replicas are Execution Agents**, not interchangeable Pods.
2. **The Gateway TCB retains absolute ownership of Authority, Leases, and Commitment Ordering.**
3. **Execution is parallel, but Commitment is strictly canonical and sequential.**

```
                         CORTEX GATEWAY TCB (Authority & Commit)
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       │                            │                            │
       ▼                            ▼                            ▼
 Replica Controller           Lease Manager                Recovery Engine
 (Lifecycle & Health)     (Fencing Tokens & Epochs)    (State Classification)
       │                            │                            │
       └────────────────────────────┼────────────────────────────┘
                                    ▼
                          Worker Instance Pool
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
       Worker A                Worker B                Worker C
  (Gen 7, Lease 101)      (Gen 7, Lease 104)      (Gen 7, Lease 109)
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                         Gateway Commit Sequencer
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

## 2. Normative Invariants for Multi-Replica Scaling

### Invariant 1: Non-Equivalence of Replica Identity
Every worker execution attempt MUST be uniquely identified by a 5-tuple coordinate:
$$\text{ExecutionCoordinate} = (\text{ReplicaGroupID}, \text{ReplicaInstanceID}, \text{ReplicaGeneration}, \text{LeaseEpoch}, \text{ExecutionAttemptID})$$

A new deployment generation or replacement worker process MUST NEVER inherit an active lease epoch from a previous process.

### Invariant 2: Capability Sub-Set Bound ($\Lambda_{\text{replica}} \subseteq \Lambda_{\text{deployment}}$)
Scaling worker replicas MUST NEVER automatically expand system authority. Every worker replica instance inherits the identical frozen capability envelope:
$$\Lambda_{\text{replica}} \subseteq \Lambda_{\text{deployment}}$$

### Invariant 3: Fenced Lease Ownership (`LeaseEpoch`)
For any given invocation $I_k$, the Gateway grants an exclusive, epoch-bound lease to Worker $W_x$:
$$\text{Lease} = (\text{InvocationID}, W_x, \text{LeaseID}, \text{LeaseEpoch}, \text{ExpiryTimestamp})$$

If Worker $W_x$ stalls or loses connectivity, the Gateway increments $\text{LeaseEpoch} \to \text{LeaseEpoch} + 1$ and re-assigns the lease to Worker $W_y$. If $W_x$ attempts a late commit under stale epoch $e_{\text{old}}$, the Gateway MUST reject the commit with `ERR_STALE_LEASE_EPOCH`.

### Invariant 4: Non-Replay of Actuated Operations
Unacknowledged in-flight requests from a dead worker MUST NOT be naively re-routed. The Gateway Recovery Engine MUST classify invocation state into exactly one of four buckets:

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

## 3. Invocation Ownership & Lifecycle State Machine

Every invocation passing through the Gateway follows a strict 6-phase state machine:

```
                       ┌────────────────────────┐
                       │        QUEUED          │
                       └───────────┬────────────┘
                                   │ Assign Worker & LeaseEpoch
                                   ▼
                       ┌────────────────────────┐
                       │        ASSIGNED        │ ──────► [ORPHANED]
                       └───────────┬────────────┘
                                   │ Worker Acknowledges
                                   ▼
                       ┌────────────────────────┐
                       │        RUNNING         │ ──────► [UNKNOWN]
                       └───────────┬────────────┘
                                   │ Gateway Authorizes Token
                                   ▼
                       ┌────────────────────────┐
                       │       AUTHORIZED       │ ──────► [UNKNOWN]
                       └───────────┬────────────┘
                                   │ Actuation Initiated
                                   ▼
                       ┌────────────────────────┐
                       │       ACTUATING        │ ──────► [INDETERMINATE]
                       └───────────┬────────────┘
                                   │ Gateway Commit Sequencer
                                   ▼
                       ┌────────────────────────┐
                       │       COMMITTED        │
                       └────────────────────────┘
```

---

## 4. Worker Lifecycle & Graceful Drain Protocol

Worker instances do not terminate abruptly when scaling down. They transition through a 5-stage lifecycle:

```
[READY] ──► [DRAINING] ──► [QUIESCED] ──► [TERMINATING] ──► [TERMINATED]
```

1. **`READY`**: Normal operation; worker receives new invocation assignments.
2. **`DRAINING`**: Worker receives **zero new invocations**. Existing assigned invocations continue execution.
3. **`QUIESCED`**: Worker has zero active invocations ($\text{owned\_invocations} = 0$), zero pending effects ($\text{pending\_effects} = 0$), and zero outstanding IPC frames ($\text{ipc\_outstanding} = 0$).
4. **`TERMINATING`**: Gateway sends `SIGTERM` to worker process group.
5. **`TERMINATED`**: Worker process reaped; socket descriptor closed.

---

## 5. Gateway Canonical Commit Sequencer

To prevent nondeterministic witness logs when worker replicas execute tasks in parallel:
- **Parallel Worker Execution**: Worker A, Worker B, and Worker C execute tasks concurrently in separate sandboxes.
- **Canonical Commitment**: Workers push candidate state updates to the **Gateway Commit Sequencer**.
- **Deterministic Witness Ordering**: The Gateway orders updates using a deterministic commit sequence number ($C_n$). Downstream witness evidence chains ($W_n$) depend strictly on $C_n$, ensuring 100% deterministic trace replays regardless of physical worker completion timing.

---

## 6. Implementation Roadmap (Phased Execution)

Scaling must be implemented strictly in the following 10-phase sequence:

1. **Worker Identity & Generation** (`ReplicaInstanceID`, `ReplicaGeneration`).
2. **Durable Invocation Ownership & Fenced Lease Protocol** (`LeaseEpoch`).
3. **Worker Lifecycle State Machine** (`READY` $\to$ `DRAINING` $\to$ `QUIESCED` $\to$ `TERMINATING`).
4. **Assignment & Routing Engine** (Capability & Isolation-aware scoring).
5. **Graceful Drain Protocol**.
6. **Crash State Classification Engine** (`UNADMITTED`, `ADMITTED_UNACTUATED`, `ACTUATED_COMMITTED`, `INDETERMINATE`).
7. **Gateway Canonical Commit Sequencer**.
8. **Evidence & Witness Chain Integration**.
9. **Multi-Replica Security & Fencing Tests**.
10. **Autoscaler & Load Balancer Integration** (Multi-metric controller with hysteresis).

---

## 7. Next Governance Actions
1. Publish `docs/architecture/replica_scaling_specification.md` to repository.
2. Mark status in `docs/README.md` as `SCALING DESIGN` (`ARCHITECTURAL REVIEW REQUIRED`).
3. Do not merge autoscaler/load-balancer code until Phases 1–8 pass all Gate A–E conformance verification gates.
