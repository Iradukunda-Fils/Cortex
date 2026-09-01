# Cortex Security Architecture & Threat Register

> **Security Baseline**: Ground-Truth Threat-Model Audit  
> **Governance Separation**: Logical Authorization $\neq$ Runtime Enforcement $\neq$ Physical Isolation  
> **Physical Isolation Policy**: $\boxed{ \text{RequiredPhysicalEnforcement} \land \text{Unavailable} \Longrightarrow \text{ExecutionRejected} }$  

---

## 1. Security Architecture & Boundary Model

Cortex delineates security into three explicit, non-interchangeable tiers:

```
[ Tier 1: Logical Authorization ]
  └─► Capability Matcher (Task.capabilities <= Worker.capabilities)
        │
        ▼
[ Tier 2: Runtime Enforcement ]
  └─► LeaseEpoch Monotonic Fencing + Invocation Ownership Ledger
        │
        ▼
[ Tier 3: Physical Isolation ]
  └─► cgroups v2 Containment / Seccomp / Namespaces / Isolated Subprocesses
```

> **Normative Security Rule**: Passing Tier 1 (Logical Authorization) does NOT guarantee Tier 3 (Physical Isolation). Physical isolation requires kernel-level cgroups v2 containment and process boundary enforcement.

---

## 2. Threat Register & Security Controls

| Threat ID | Threat Vector | Targeted Property | Implementation Mechanism | Enforcement Boundary | Failure Behavior | Assurance Level | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **THREAT-01** | Stale Worker Late Actuation | Monotonic Lease Epoch | Monotonic `LeaseEpoch` validation at commit | Gateway ownership boundary | Fail-closed (`ERR_STALE_LEASE_EPOCH`) | `ADVERSARIALLY-TESTED` & `PROVEN` | `test_load_balancer_hardening_gate.py`, Coq proof |
| **THREAT-02** | Bitflip / Disk Corruption in WAL | Durable State Integrity | 32-bit CRC framing on header + payload | WAL reader recovery loop | Truncate corrupted tail; preserve valid frames | `ADVERSARIALLY-TESTED` | `test_phase6_wal_adversarial_gate.py` |
| **THREAT-03** | Worker Memory Exhaustion | Capacity Safety | `ResourceAuthority` vector allocation + cgroups v2 `memory.max` | Host cgroups v2 controller | SIGKILL by Linux OOM killer; worker quarantined | `RUNTIME-VERIFIED` (Linux Root) / `DEGRADED` (User) | `test_execution_enforcement.py` |
| **THREAT-04** | Duplicate Task Replay | Idempotency | `InvocationLedger` key tracking | Gateway admission control | Return cached result without re-actuation | `ADVERSARIALLY-TESTED` | `test_idempotency_engine.py` |
| **THREAT-05** | Capability Impersonation | Capability Isolation | Cryptographic capability token validation | Task submission gateway | Intention rejected with `ERR_UNAUTHORIZED` | `RUNTIME-VERIFIED` | `test_v020_capability_enforcement.py` |
| **THREAT-06** | Configuration Injection | Configuration Integrity | Field-class normalization & regex validation | ConfigResolver loading pipeline | Schema parsing failure; default fallback | `RUNTIME-VERIFIED` | `test_gate_h_canonicalization.py` |
| **THREAT-07** | FD / Socket Leakage | Process Boundary | Explicit socket cleanup & `close_fds=True` in subprocess launcher | OS process spawner | Warning logged; non-zero leak detected | `RUNTIME-VERIFIED` | `test_v021_security_audit.py` |
| **THREAT-08** | In-flight Request Loss | Intention Recovery | Recovery classifier (`UNADMITTED`, `ADMITTED_UNACTUATED`, `ACTUATED_COMMITTED`, `ACTUATION_UNKNOWN`) | Gateway Recovery Controller | Non-idempotent operations transition to `INDETERMINATE` | `RUNTIME-VERIFIED` | `test_v020_crash_semantics.py` |

---

## 3. Physical Containment Audit & Policy Details

- **Linux cgroups v2 Integration**:
  - Path: `/sys/fs/cgroup/cortex/<worker_id>/`
  - Limits enforced: `memory.max`, `cpu.max`, `pids.max`.
- **Strict Enforcement Policy**:
  $$\boxed{ \text{RequiredPhysicalEnforcement} \land \text{Unavailable} \Longrightarrow \text{ExecutionRejected} }$$
  - When `strict_mode=True` or physical containment is explicitly requested by a task specification, the system fails closed with `ContainmentEnforcementError` if cgroups v2 is unavailable or non-root.
- **Unconstrained Process Fallback (Developer Convenience Only)**:
  - When running in non-strict development mode (`strict_mode=False`) without explicit containment requirements, the runtime emits warning logs and spawns unconstrained subprocesses.
  - **Normative Rule**: Unconstrained subprocess execution is strictly a developer convenience path and is NEVER treated or documented as equivalent to physical containment.
