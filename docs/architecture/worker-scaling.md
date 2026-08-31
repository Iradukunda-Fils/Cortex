# Cortex Worker Scaling Lifecycle Architecture

**Normative Document Version**: v1.0.0-FINAL  
**Refinement Certificate**: `RCA-7.3-v1`  
**Target Subsystems**: `ResourceAuthority`, `ProductionDynamicLoadBalancer`  
**Implementation Files**: `cortex/tools/kernel/resource_authority.py`, `cortex/tools/kernel/load_balancer.py`  

---

## 1. Governance Architecture: Load Balancer + Resource Authority

Worker scaling (scale-up and scale-down) is managed as a unified, resource-governed state transition sequence rather than an uncoordinated operational feature:

$$\text{Admission} \to \text{Capacity} \to \text{Reservation} \to \text{Placement} \to \text{Lease} \to \text{Execution} \to \text{Observation} \to \text{Release}$$

```text
DRAINING
   ↓
stop new placement
   ↓
wait for / reconcile assignments
   ↓
QUIESCENT
   ↓
FENCE
   ↓
RETIRE
   ↓
retain incarnation tombstone
```

---

## 2. Scale-Up Lifecycle Semantics

Scale-up introduces new worker capacity $w$ under explicit fencing control:

$$\boxed{ \text{ScaleUp}(w) \implies \text{Register}(w) \land \text{ValidateCapability}(w) \land \text{InitializeGeneration}(w) \land \text{PublishCapacity}(w) }$$

1. **Generation Validation**: Monotonic generation check $g_{new} > g_{current}$.
2. **Incarnation Tombstone Gate**: Reject registration if $(w, g_{new})$ matches a previously retired tombstone.
3. **Capability Registration**: Register capabilities in the derived capability index.
4. **State Transition**: Transition worker state to `ACTIVE`.

---

## 3. Scale-Down Lifecycle Semantics & Quiescence Gate

Scale-down removes worker $w$ while guaranteeing zero loss of active assignments or resource leakage:

$$\boxed{ \text{ScaleDown}(w) \implies \text{Drain}(w) \land \text{Quiescent}(w) \land \text{Fence}(w) \land \text{Retire}(w) }$$

### Quiescence Definition

$$\boxed{ \text{Quiescent}(w) \iff \text{ActiveAssignments}(w) = 0 \land \text{ActiveReservations}(w) = 0 }$$

A scale-down decision **never** creates a state where $\text{ActiveAssignments}(w) > 0$ while the worker is considered retired.

---

## 4. Resource-Aware Retirement Predicate

Idle candidate selection is **not** based solely on CPU utilization ($\text{Idle}(w) \neq \text{CPUIdle}(w)$). A worker holding exclusive GPU ownership, active network streams, or persistent leases is **not retirable**.

### Retirable Predicate Formula

$$\boxed{ \text{Retirable}(w) \iff \text{Quiescent}(w) \land \text{NoActiveReservation}(w) \land \text{NoExclusiveResourceOwnership}(w) \land \text{DrainComplete}(w) \land \text{RetirementPolicy}(w) }$$

### Scale-Down Leak Prevention Theorem

$$\boxed{ \text{Retire}(w) \implies \text{ReleasedResources}(w) = \text{AllResources}(w) }$$

---

## 5. Incarnation Fencing & Tombstone Retention

When worker $w$ is retired at generation $g$, its incarnation is tombstoned:

$$\boxed{ \text{WorkerRetired}(w, g) \land g_{presented} = g \implies \text{Reject} }$$

Any subsequent request presenting $(w, g)$ is immediately rejected with `InvalidFencingError`, preventing stale worker resurrection.
