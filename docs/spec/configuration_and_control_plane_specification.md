# Configuration & Control Plane Specification

> **Governance Status**: `SCALING DESIGN` — `ARCHITECTURAL REVIEW REQUIRED`  
> **Scope**: Configuration lifecycle, CLI semantics, reconciliation model, and deployment generation management  
> **Pre-requisite**: Must be reviewed and approved before Phase 1–3 replica implementation code is merged to mainline.

---

## 1. Foundational Principle

> **All configuration enters through one canonical configuration model; all runtime changes are produced by reconciliation against immutable, versioned desired state.**

Configuration describes what Cortex *should be*. Controllers make reality converge to it.

---

## 2. Desired State vs. Observed State

Cortex adopts a declarative control-plane model. Configuration and runtime state are never conflated.

```
              DesiredState                              ObservedState
   ┌──────────────────────────┐              ┌──────────────────────────┐
   │ PluginDeploymentSpec     │              │ ReplicaGroupObservedState│
   │ ├── plugin_id            │              │ ├── generation           │
   │ ├── config_generation    │              │ ├── ready_replicas       │
   │ ├── config_hash          │              │ ├── draining_replicas    │
   │ ├── min_replicas         │              │ ├── failed_replicas      │
   │ ├── max_replicas         │              │ ├── leases               │
   │ ├── sandbox_profile      │              │ └── active_invocations   │
   │ ├── capability_policy    │              └──────────────────────────┘
   │ ├── resource_limits      │                         ▲
   │ ├── routing_policy       │                         │
   │ └── lifecycle_policy     │                    Reconciliation
   └──────────────────────────┘                    Controller
                │                                       │
                └───────────────────────────────────────┘
                        compare → converge
```

### Normative Rules
- `DesiredState` is **immutable once admitted**. A new configuration creates a new `ConfigGeneration`.
- `ObservedState` is **read-only** to external consumers. Only internal controllers may mutate it.
- The reconciliation controller is the **sole bridge** between desired and observed state.

---

## 3. Configuration Sources & Precedence

### 3.1 Authoritative Sources (Ordered by Precedence)

```
1. Compiled Defaults     (lowest priority — hardcoded safe defaults)
       ↓
2. Config File           (cortex.yaml / deployment.json / deployment.yaml)
       ↓
3. Environment Variables (CORTEX_PLUGIN_*, CORTEX_SCALING_*)
       ↓
4. CLI Flags             (highest priority — explicit operator intent)
```

### 3.2 Precedence Invariant
> Higher-precedence sources override lower-precedence sources **for operational configuration only**. Security-critical configuration is subject to ceiling enforcement (see §4).

### 3.3 Source Resolution Pipeline

```
Config Sources (file, env, CLI)
       ↓
  Read & Merge (precedence order)
       ↓
  Schema Validation (structural correctness)
       ↓
  Semantic Validation (constraint satisfaction)
       ↓
  Security Ceiling Enforcement (§4)
       ↓
  Normalize & Canonicalize
       ↓
  Hash (SHA-256 of canonical representation)
       ↓
  ConfigGeneration Assignment
       ↓
  Persist to Desired State Store
       ↓
  Emit ConfigChangeAuditEvent
       ↓
  Trigger Reconciliation
```

---

## 4. Configuration Classes & Security Boundaries

Not all configuration is equal. Cortex partitions configuration into four classes with distinct authorization requirements.

### 4.1 Configuration Class Taxonomy

| Class | Examples | Override by CLI? | Override by Env? | Override by Config File? |
| :--- | :--- | :---: | :---: | :---: |
| **Security** | `sandbox_profile`, `capability_ceiling`, `worker_isolation`, `ipc_policy` | **NO** | **NO** | Only with `security_override: true` and audit event |
| **Identity** | `plugin_id`, `plugin_version`, `config_schema_version` | **NO** | **NO** | YES (source of truth) |
| **Scaling** | `min_replicas`, `max_replicas`, `drain_deadline_sec`, `backpressure_strategy` | YES | YES | YES |
| **Operational** | `log_level`, `health_check_interval`, `metrics_endpoint` | YES | YES | YES |

### 4.2 Capability Ceiling Enforcement
> **Normative Rule**: No configuration source may grant capabilities exceeding the deployment's frozen capability envelope ($\Lambda_{\text{deployment}}$). CLI flags, environment variables, and config files are all subject to the same ceiling. Attempts to exceed the ceiling MUST be rejected with a `CapabilityCeilingViolation` error and an audit event.

### 4.3 Security Configuration Immutability
> Security-class configuration is locked at deployment admission time. Runtime changes require a new deployment generation with explicit `security_override: true` and a mandatory audit trail.

---

## 5. Configuration Schema & Validation

### 5.1 Schema Version

Every configuration carries a schema version:

```yaml
schema_version: "0.3.0"
```

Schema versions follow SemVer. Breaking schema changes increment the major version. The configuration resolver MUST reject configurations whose `schema_version` is incompatible with the running Gateway version.

### 5.2 Structural Validation (Schema)

- All required fields are present.
- All fields conform to declared types.
- No unknown fields are accepted (strict mode).

### 5.3 Semantic Validation (Constraints)

- `min_replicas <= max_replicas`
- `drain_deadline_sec > 0`
- `max_queue_depth > 0`
- `capability_envelope` entries are valid capability identifiers.
- `sandbox_profile` references a known, registered profile.
- `entrypoint` is non-empty and references a resolvable binary/script path.

### 5.4 Canonicalization

After validation, the configuration is canonicalized:
1. Keys sorted lexicographically.
2. Strings UTF-8 NFC normalized.
3. Numeric values normalized to canonical representation.
4. Result hashed with SHA-256 to produce `config_hash`.

---

## 6. Configuration Generation Semantics

### 6.1 ConfigGeneration vs. ReplicaGeneration

These are related but distinct concepts:

```
ConfigGeneration
    │
    └── Describes a versioned, immutable configuration snapshot.
        A new configuration admission always creates a new ConfigGeneration.

ReplicaGeneration
    │
    └── Describes a deployment wave of worker instances.
        A ReplicaGeneration is always bound to exactly one ConfigGeneration.
        Multiple ReplicaGenerations may exist for the same ConfigGeneration
        (e.g., after a restart without config change).
```

### 6.2 Relationship

$$\text{ReplicaGeneration} \xrightarrow{\text{bound to}} \text{ConfigGeneration}$$

> **Normative Rule**: A worker MUST only execute requests against the `ConfigGeneration` for which it was admitted. Stale workers operating under a previous `ConfigGeneration` MUST be drained and retired.

### 6.3 Generation Identity Record

Every admitted configuration produces:

```
config_generation: 18
config_hash: "sha256:a1b2c3d4..."
config_schema_version: "0.3.0"
admitted_at: "2026-08-19T15:00:00Z"  (wall clock, observability only)
admitted_epoch: 42                    (monotonic, authoritative)
```

Workers report their generation:

```
worker_instance_id: "w-7"
replica_generation: 18
config_generation: 18
config_hash: "sha256:a1b2c3d4..."
```

---

## 7. Immutable Configuration Snapshots

> **Normative Rule**: A running `ReplicaGroup` operates against one immutable configuration snapshot. Configuration is never mutated in place. A new configuration creates a new generation.

```python
# CORRECT: Immutable frozen dataclass
@dataclass(frozen=True)
class PluginDeploymentSpec:
    plugin_id: str
    config_generation: int
    config_hash: str
    ...

# INCORRECT: Mutable dictionary referenced by workers
config = {"replicas": 3}   # ← Workers share a mutable reference
config["replicas"] = 5     # ← Race condition / split-brain risk
```

---

## 8. Secret & Credential Separation

Configuration, secrets, identity material, and ephemeral runtime state occupy separate boundaries:

| Boundary | Contents | Storage | Mutability |
| :--- | :--- | :--- | :--- |
| **Configuration** | Plugin specs, scaling policy, operational settings | Config files, env, CLI | Immutable per generation |
| **Secrets** | Private keys, API tokens, database credentials | Dedicated secret store / sealed files | Rotatable, never in config files |
| **Identity Material** | `ExecutionIdentity`, `OwnershipIdentity`, lease epochs | Gateway runtime state | Generated per-instance |
| **Ephemeral Runtime** | `ExecutionTokens`, IPC socket descriptors, worker PIDs | In-memory only | Volatile, never persisted |

> **Normative Rule**: Plugin configuration files (`deployment.yaml`, `cortex.yaml`) MUST NOT contain private keys, `ExecutionTokens`, lease credentials, or IPC authentication secrets. These belong in the secret-management boundary.

---

## 9. Invocation-to-Configuration Binding

When the Gateway receives an invocation:

```
Invocation
   ↓
PluginID
   ↓
Active DeploymentGeneration
   ↓
ConfigurationSnapshot (immutable)
   ↓
CapabilityPolicy
   ↓
SandboxProfile
   ↓
Eligible Worker Set (matching ConfigGeneration)
```

> **Normative Rule**: An invocation created under `ConfigGeneration N` MUST NOT execute under `ConfigGeneration N+1` unless the invocation is explicitly re-queued under the new generation.

---

## 10. CLI & Control API Contract

### 10.1 Design Principle
> The CLI communicates desired-state operations to the control plane. It MUST NOT directly invoke `LeaseManager`, `WorkerLifecycleTracker`, or any internal TCB component.

```
CLI / API
    ↓
Control Command Layer
    ↓
Configuration Resolver
    ↓
Desired State Store
    ↓
Reconciliation Controller
    ↓
Replica / Lease / Lifecycle subsystems
```

### 10.2 CLI Command Surface

| Command | Operation | Modifies |
| :--- | :--- | :--- |
| `cortex plugin deploy <name> --config <path>` | Admit a new plugin deployment (creates ConfigGeneration) | Desired State |
| `cortex plugin scale <name> --replicas <N>` | Update desired replica count | Desired State (Scaling class) |
| `cortex plugin status <name>` | Read observed state | Nothing (read-only) |
| `cortex plugin drain <name>` | Set desired state to DRAINING for all workers | Desired State |
| `cortex plugin rollout <name>` | Apply pending configuration generation | Desired State |
| `cortex plugin rollback <name> --generation <N>` | Revert desired state to a previous ConfigGeneration | Desired State |
| `cortex plugin inspect <name>` | Display config generation, hash, and observed replica state | Nothing (read-only) |

### 10.3 CLI Authorization Model
- `status`, `inspect`: No authorization required (read-only).
- `scale`, `drain`: Requires `operator` role.
- `deploy`, `rollout`, `rollback`: Requires `deployer` role.
- Security-class overrides: Requires explicit `--security-override` flag + `admin` role + mandatory audit event.

---

## 11. Reconciliation Controller Model

### 11.1 Controller Architecture

The reconciliation controller is a single-threaded, idempotent loop:

```
while true:
    desired = read_desired_state()
    observed = read_observed_state()

    diff = compute_diff(desired, observed)

    for action in diff.actions:
        execute(action)

    sleep(reconciliation_interval)
```

### 11.2 Reconciliation Actions

| Observed Condition | Desired State | Action |
| :--- | :--- | :--- |
| `ready_replicas < min_replicas` | `min_replicas = 3` | Spawn new worker (current ConfigGeneration) |
| `ready_replicas > max_replicas` | `max_replicas = 3` | Begin draining excess workers |
| Worker with stale `ConfigGeneration` | New generation admitted | Drain stale worker; spawn replacement |
| Worker health check failed | `READY` | Transition to `RECOVERY_REQUIRED`; classify |
| Drain deadline expired | `DRAINING` | Transition to `FORCED_RECOVERY` |
| `QUIESCED` worker exists | `TERMINATED` | Send `SIGTERM`; reap process |

### 11.3 Idempotency
> Every reconciliation action MUST be idempotent. Repeated reconciliation cycles with identical desired and observed state MUST produce zero side effects.

---

## 12. Rollout & Rollback Semantics

### 12.1 Rolling Update (Rollout)

```
Generation 17 (active)
       ↓
New config admitted → Generation 18
       ↓
Spawn Gen 18 workers
       ↓
Gen 18 workers pass readiness check
       ↓
Stop assigning new work to Gen 17 workers
       ↓
Drain Gen 17 workers
       ↓
Retire Gen 17 workers (TERMINATED)
       ↓
Generation 18 fully active
```

### 12.2 Rollback

```
Generation 18 (unhealthy — readiness failures)
       ↓
Operator: cortex plugin rollback my-plugin --generation 17
       ↓
Desired state reverts to Generation 17 config snapshot
       ↓
Reconciler drains Gen 18 workers
       ↓
Reconciler spawns Gen 17 workers (from stored immutable snapshot)
       ↓
Generation 17 restored
```

> **Normative Rule**: Rollback restores a previous immutable configuration snapshot. It does NOT reconstruct state from worker memory.

---

## 13. Persistence Substrate for Invocation Ledger

### 13.1 First Implementation: Embedded Append-Only Journal

For the initial single-process Gateway prototype:

- **Substrate**: SQLite WAL-mode database or append-only journal file.
- **Location**: Gateway-local filesystem (`$CORTEX_STATE_DIR/ledger.db`).
- **Durability**: `fsync` after each state transition.
- **Bounded Size**: Completed invocations are compacted after `retention_window` (default: 24h).

### 13.2 Persistence Guarantees

| Event | Survives Worker Restart? | Survives Gateway Restart? | Survives Machine Restart? |
| :--- | :---: | :---: | :---: |
| Invocation state (QUEUED → COMMITTED) | ✅ | ✅ | ✅ |
| Active lease records | ✅ | ✅ (re-validated on startup) | ✅ (stale leases invalidated) |
| Worker PIDs / IPC FDs | N/A | ❌ (ephemeral) | ❌ (ephemeral) |
| Configuration snapshots | ✅ | ✅ | ✅ |

### 13.3 Memory Boundedness

$$\text{Memory} = O(\text{active\_invocations} + \text{active\_workers} + \text{bounded\_journal\_cache})$$

Historical completed operations are persisted to disk and evicted from resident memory. Ten million completed lease operations MUST NOT create unbounded in-memory state.

---

## 14. Lease Epoch Scoping

> **Normative Rule**: `LeaseEpoch` is scoped per `InvocationID`, not globally.

```
LeaseEpoch(invocation_id="inv-42") = 17
LeaseEpoch(invocation_id="inv-43") = 3
```

One replica group's lease operations MUST NOT affect another's epoch counters.

---

## 15. Audit Events

Every configuration change, security override, and control-plane operation emits an immutable audit event:

| Event Type | Trigger | Recorded Fields |
| :--- | :--- | :--- |
| `ConfigAdmitted` | New configuration accepted | `config_generation`, `config_hash`, `source`, `admitted_by` |
| `ConfigRejected` | Validation failure | `reason`, `source`, `attempted_by` |
| `SecurityOverride` | Security-class config change | `field`, `old_value`, `new_value`, `authorized_by` |
| `DeploymentRollout` | New generation activated | `from_generation`, `to_generation` |
| `DeploymentRollback` | Generation reverted | `from_generation`, `to_generation`, `reason` |
| `CapabilityCeilingViolation` | Attempted capability escalation | `requested`, `ceiling`, `source` |

---

## 16. Control Plane Architecture Summary

```
                         CORTEX CONTROL PLANE
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
              CLI/API                     Config Sources
                 │                        (file, env, defaults)
                 └──────────────┬──────────────┘
                                ▼
                      Configuration Resolver
                     (Schema + Semantic + Security Validation)
                                │
                         Canonical Config
                      (Hash + Generation + Snapshot)
                                │
                     Desired State Store
                                │
                                ▼
                  Reconciliation Controller (idempotent loop)
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        Replica Controller  Lease Manager   Lifecycle Manager
              │                 │                 │
              └─────────────────┼─────────────────┘
                                ▼
                    Observed Runtime State
                                │
                                ▼
                    Invocation Ledger (durable)
```
