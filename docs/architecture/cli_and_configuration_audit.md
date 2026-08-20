# CLI & Configuration Security Audit

> **Audit Scope**: Configuration lifecycle, CLI authorization, secret boundaries, and Gate G conformance  
> **Audit Status**: `INITIAL REVIEW` — Performed prior to Phase 1–3 implementation  
> **Auditor**: Architecture review pass (pre-implementation gate)

---

## 1. Audit Methodology

This audit evaluates the Cortex configuration and CLI control-plane design against 18 adversarial questions derived from the Gate G capability-security model and the frozen assurance baseline.

Each finding is classified as:
- **PASS**: The architecture explicitly prevents the attack.
- **MITIGATED**: The architecture addresses the concern, but implementation must enforce it.
- **REQUIRES IMPLEMENTATION**: The architectural rule exists, but no code enforces it yet.

---

## 2. Configuration Security Findings

### Q1: Can a plugin modify its own configuration?

**Finding: MITIGATED**

Workers run inside isolated sandboxes (`CLONE_NEWPID`, `CLONE_NEWNET`, `CLONE_NEWNS`) with `seccomp-bpf` syscall filters blocking filesystem writes. Workers communicate only via `FD 3`.

**Remaining Risk**: The Gateway must validate that no IPC message from a worker can trigger a configuration mutation. The control command layer must reject configuration-modifying requests originating from worker IPC channels.

**Required Implementation**: Configuration mutations are accepted only from the CLI/API control path, never from worker IPC frames.

---

### Q2: Can a worker request a stronger capability through configuration?

**Finding: MITIGATED**

The `CapabilityCeilingEnforcement` rule (§4.2 of the control-plane spec) mandates:

$$\Lambda_{\text{requested}} \subseteq \Lambda_{\text{deployment}} \subseteq \Lambda_{\text{ceiling}}$$

**Remaining Risk**: The configuration resolver must enforce this ceiling check during schema validation, not defer it to runtime.

**Required Implementation**: `ConfigurationResolver.validate_semantic()` must assert capability ceiling compliance before admitting any configuration.

---

### Q3: Can CLI override sandbox restrictions?

**Finding: PASS (by design)**

Sandbox profiles are classified as **Security-class configuration** (§4.1). Security-class fields cannot be overridden by CLI flags or environment variables. Changes require:
1. A new config file with `security_override: true`
2. `admin` role authorization
3. Mandatory `SecurityOverride` audit event

---

### Q4: Can environment variables override security policy?

**Finding: PASS (by design)**

The configuration class taxonomy (§4.1) explicitly forbids environment variable overrides for Security-class and Identity-class configuration. Only Scaling-class and Operational-class fields accept environment overrides.

---

### Q5: Can an old worker load a newer configuration?

**Finding: MITIGATED**

Workers do not load configuration independently. The Gateway assigns workers a `ConfigGeneration` at spawn time. Workers report their generation in health check responses.

**Remaining Risk**: The Gateway must reject IPC frames from workers reporting a mismatched `ConfigGeneration`.

**Required Implementation**: Worker handshake must include `config_generation` and `config_hash`. Gateway validates match before admitting the worker to the ready pool.

---

### Q6: Can a stale worker submit against a new generation?

**Finding: MITIGATED**

The `LeaseEpoch` fencing mechanism ensures that stale workers operating under a previous generation cannot commit. However, this depends on the lease being scoped correctly.

**Remaining Risk**: `ConfigGeneration` must be checked independently of `LeaseEpoch`. A worker with a valid lease but stale config generation must still be rejected.

**Required Implementation**: Commit validation must check both:
```
lease_epoch == current_lease_epoch
AND
worker_config_generation == active_config_generation
```

---

### Q7: Can configuration injection bypass CBE validation?

**Finding: PASS (by design)**

Configuration files are parsed by the Gateway's configuration resolver, not by workers. Workers never see raw configuration. The IPC protocol uses CBE-encoded frames on `FD 3`, which are validated independently by the Layer 2 codec.

Configuration injection into the IPC stream is blocked by the 11-byte binary header magic bytes (`0x43`, `0x58`) and sequence monotonicity checks.

---

### Q8: Can a malformed configuration cause unsafe defaults?

**Finding: REQUIRES IMPLEMENTATION**

The architecture specifies strict-mode schema validation (no unknown fields, all required fields present). However, the implementation must ensure:

1. **No implicit defaults for security fields**: If `sandbox_profile` is omitted, the configuration MUST be rejected, not defaulted to a permissive profile.
2. **Explicit fail-closed**: Malformed configuration produces `ConfigRejected` audit event and zero runtime state changes.

**Required Implementation**: Schema validation must distinguish between:
- Operational fields with safe defaults (e.g., `log_level: "info"`)
- Security fields with no defaults (e.g., `sandbox_profile: REQUIRED`)

---

### Q9: Can replica scaling expand authority?

**Finding: PASS (by design)**

Invariant: $\Lambda_{\text{replica}} \subseteq \Lambda_{\text{deployment}}$

Scaling from 1 to 5 replicas produces 5 identical workers with the same frozen capability envelope. No new capabilities are minted.

---

### Q10: Can a replacement replica clone live credentials?

**Finding: PASS (by design)**

Invariant 3 (Non-Cloning of Live Authorization State): Replacement replicas receive fresh `ExecutionIdentity` coordinates, new `LeaseEpoch` assignments, and new IPC socketpairs. No credential material is copied from prior workers.

---

## 3. CLI Authorization Audit

### Q11: Can an unprivileged operator deploy a plugin?

**Finding: MITIGATED**

The CLI authorization model defines three roles: `operator`, `deployer`, `admin`. Plugin deployment requires `deployer` role.

**Remaining Risk**: Role enforcement must be implemented in the control command layer, not in the CLI client itself (which could be bypassed).

---

### Q12: Can CLI directly mutate lease state?

**Finding: PASS (by design)**

The CLI surface exposes only desired-state operations (`deploy`, `scale`, `drain`, `rollout`, `rollback`). No commands expose `LeaseManager`, `InvocationLedger`, or `WorkerLifecycleTracker` internals.

---

### Q13: Can concurrent CLI operations cause split-brain desired state?

**Finding: REQUIRES IMPLEMENTATION**

If two operators simultaneously execute:
```
cortex plugin scale my-plugin --replicas 3
cortex plugin scale my-plugin --replicas 5
```

The desired state store must serialize these operations. The configuration resolver must use optimistic concurrency (compare-and-swap on `config_generation`) or pessimistic locking.

**Required Implementation**: Desired state mutations must be serialized through the Gateway's configuration lock boundary.

---

## 4. Persistence & Recovery Audit

### Q14: Can Gateway restart cause invocation loss?

**Finding: MITIGATED**

The invocation ledger uses a durable persistence substrate (§13 of control-plane spec). Invocation states survive Gateway restarts. On restart, stale leases are invalidated and in-flight invocations transition to `RECOVERY_REQUIRED`.

**Remaining Risk**: The first implementation must actually persist to disk (SQLite WAL or append-only journal), not rely on in-memory state.

---

### Q15: Can historical operations exhaust memory?

**Finding: REQUIRES IMPLEMENTATION**

The memory boundedness rule states:

$$\text{Memory} = O(\text{active\_invocations} + \text{active\_workers} + \text{bounded\_journal\_cache})$$

**Required Implementation**: The ledger must compact completed invocations to disk after `retention_window` and evict them from resident memory.

---

## 5. Configuration Lifecycle Audit

### Q16: Is configuration immutability enforced?

**Finding: REQUIRES IMPLEMENTATION**

The specification mandates `frozen=True` dataclasses for `PluginDeploymentSpec`. The implementation must not use mutable dictionaries or allow in-place mutation of configuration objects referenced by workers.

---

### Q17: Are configuration generations monotonic?

**Finding: REQUIRES IMPLEMENTATION**

`ConfigGeneration` must increment strictly ($g_{n+1} > g_n$) and be scoped per plugin deployment. The implementation must use a Gateway-owned monotonic counter, not timestamps.

---

### Q18: Is rollback safe?

**Finding: MITIGATED**

Rollback restores a previous immutable configuration snapshot from the desired state store. It does not reconstruct state from worker memory. However, invocations admitted under the rolled-back generation must be properly classified (UNADMITTED vs. ACTUATION_UNKNOWN).

**Required Implementation**: Rollback must trigger the standard drain → recovery classification pipeline for workers of the outgoing generation.

---

## 6. Summary & Verdict

```
+----------------------------------------------------+----------------------------+
|                    Audit Category                  |          Status            |
+----------------------------------------------------+----------------------------+
| Plugin self-modification                           | MITIGATED                  |
| Capability escalation via config                   | MITIGATED                  |
| CLI sandbox override                               | PASS                       |
| Environment variable security override             | PASS                       |
| Stale worker config generation                     | MITIGATED                  |
| Configuration injection into IPC                   | PASS                       |
| Unsafe defaults on malformed config                | REQUIRES IMPLEMENTATION    |
| Authority expansion via scaling                    | PASS                       |
| Credential cloning on replica replacement          | PASS                       |
| Unprivileged deployment                            | MITIGATED                  |
| CLI direct lease mutation                          | PASS                       |
| Concurrent CLI split-brain                         | REQUIRES IMPLEMENTATION    |
| Gateway restart invocation loss                    | MITIGATED                  |
| Historical operation memory exhaustion             | REQUIRES IMPLEMENTATION    |
| Configuration immutability enforcement             | REQUIRES IMPLEMENTATION    |
| Configuration generation monotonicity              | REQUIRES IMPLEMENTATION    |
| Rollback safety                                    | MITIGATED                  |
+----------------------------------------------------+----------------------------+
```

### Overall Verdict

```
PASS (by design):           6 / 18
MITIGATED (arch covers it): 7 / 18
REQUIRES IMPLEMENTATION:    5 / 18
```

> **Conclusion**: The architectural design is sound. No fundamental design flaws were identified. Five findings require explicit implementation enforcement before Phase 1–3 code can be promoted. All `REQUIRES IMPLEMENTATION` items must be addressed in the Phase 1–3 code and validated by the RS-1 to RS-12 test suite.
