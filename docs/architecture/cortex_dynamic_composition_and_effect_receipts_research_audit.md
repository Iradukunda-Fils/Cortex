# CORTEX — DYNAMIC COMPOSITION, EFFECT RECEIPTS & DEPENDENCY ARCHITECTURE AUDIT

**Authoritative Baseline:** `v1.5.1-FINAL-FROZEN`  
**Focus Area:** Research-to-Cortex Structural Mapping (Effects, Dependencies, Lifecycle, Quiescence & Concurrency)

---

# 1. Executive Summary & Philosophical Alignment

A dynamic component research model separates composition into **temporal composability** (behavior upon component removal/drain) and **spatial composability** (runtime resolution of dynamic dependencies). 

Rather than layering a competing dynamic component framework inside Cortex, Cortex strengthens its existing kernel substrate by reifying effects, dependencies, lifecycle, and recovery into explicit, machine-reasoned primitives.

### Concept Mapping: Dynamic Research vs. Cortex Kernel

| Research Concept | Existing Cortex Equivalent | Proposed Cortex Evolution |
| :--- | :--- | :--- |
| **Effect Context** | `AdapterExecutionContext` | **`CortexContext`** ($\Gamma_I$) |
| **Revertible Effect** | Effect Reconciliation / Quarantine | **`EffectReceipt`** ($R_e$) with inverse witness |
| **Coeffect / Dependency** | `ResourceContract` + Capabilities | **`ComponentContract`** ($\langle \text{Requires, Provides, Effects, Resources, Lifecycle} \rangle$) |
| **Dependency Provider** | Worker Node / External Adapter | **Dynamic Capability Provider** |
| **Reactive Dependency** | Worker Readiness & Capability Set | **First-Class Dependency Events** (`DependencyChanged`, `ProviderDraining`) |
| **Component Lifecycle** | Worker Lifecycle (`HEALTHY`, `DRAINING`) | **Formal Quiescence & Fencing** (`QUIESCENT`, `FENCED`) |
| **Context Mediation** | Gateway PEP (`gateway_pep.py`) | **Context Projection** ($\pi_W(\Gamma_I) \subseteq \Gamma_I$) |
| **Failure During Teardown** | `INDETERMINATE` / Quarantine Machine | **Quarantine Containment & Compensation Guard** |

---

# 2. Key Evolutionary Architecture Recommendations

## 2.1 Reifying External Effects: Immutable `EffectReceipt`

In standard adapter execution, an operation returns `SUCCESS` or raises an exception. To enable fine-grained lineage, idempotency validation, and effect reconciliation, adapter operations should produce an **`EffectReceipt`**:

$$R_e = \langle \text{InvocationID}, \text{AttemptID}, \text{Resource}, \text{EffectClass}, \text{BeforeWitness}, \text{AfterWitness}, \text{WitnessSignature}, \text{Compensation}, \text{IdempotencyKey} \rangle$$

### Reversibility Classification (Strict Operational Conservatism)

Cortex explicitly rejects universal effect rollback. Effects are strictly categorized:

$$\text{EffectClass} \in \{\text{REVERSIBLE}, \text{COMPENSATABLE}, \text{IDEMPOTENT}, \text{IDEMPOTENT\_WITH\_KEY}, \text{NON\_IDEMPOTENT}\}$$

* **REVERSIBLE:** Exact inverse operation exists (e.g., `create_temp_object` $\to$ `delete_temp_object`).
* **COMPENSATABLE:** Compensating business operation exists (e.g., `reserve_slot` $\to$ `cancel_reservation`).
* **IDEMPOTENT:** Safe to re-execute with identical parameters.
* **NON_IDEMPOTENT:** Cannot be safely retried or reversed without human-in-the-loop intervention (e.g., `send_email`, `charge_payment`). Failures transition directly to `INDETERMINATE` / `QUARANTINED`.

---

## 2.2 Reifying Component Dependencies: `ComponentContract`

`ResourceContract` is expanded into a declarative **`ComponentContract`**:

$$\text{ComponentContract} = \langle \text{Requires}, \text{Provides}, \text{Effects}, \text{Resources}, \text{Lifecycle} \rangle$$

### Example Contract Specification (TextExtractor)

```yaml
ComponentContract:
  Name: "TextExtractor"
  Requires:
    - capability: "object.read"
    - capability: "storage.resolve"
  Provides:
    - capability: "text.extract"
  Effects:
    - class: "READ"
      target: "ObjectRef"
    - class: "CREATE"
      target: "TextArtifact"
  Lifecycle:
    states: [STARTING, READY, DRAINING, WAITING_FOR_DEPENDENCY, UNAVAILABLE]
```

---

## 2.3 Formal Quiescence & Worker Teardown Lifecycle

Worker replacement and draining are elevated from operational flags to formal lifecycle state transitions:

$$\text{Quiescent}(w) \iff \text{ActiveAssignments}(w) = 0$$

$$\text{Replace}(w) \implies \text{DRAIN}(w) \land \text{Quiescent}(w) \land \text{Fence}(w)$$

### State Transition Diagram

$$\text{HEALTHY} \xrightarrow{\text{Drain Trigger}} \text{DRAINING} \xrightarrow{\text{ActiveAssignments} = 0} \text{QUIESCENT} \xrightarrow{\text{Epoch / Incarnation Advance}} \text{FENCED} \to \text{REMOVED}$$

---

## 2.4 Context Projection ($\pi_W(\Gamma_I)$)

To enforce Complete Mediation and least-privilege authority isolation, workers never receive the global execution context ($\Gamma_I$). A worker receives only the projected subset required for its invocation:

$$\Gamma_I = \langle \text{Identity}, \text{Capabilities}, \text{Lease}, \text{Resources}, \text{ObjectRefs}, \text{Adapters}, \text{Policy}, \text{Deadline} \rangle$$

$$\pi_W(\Gamma_I) \subseteq \Gamma_I$$

---

## 2.5 Effect Independence & Mathematical Concurrency Scheduling

Cortex can mathematically determine when operations may be safely executed in parallel or reordered without race conditions.

### Independence Definition

Two effects $e_1, e_2$ are independent ($Independent(e_1, e_2)$) if for all states $S$:

$$\text{Apply}(e_1, \text{Apply}(e_2, S)) = \text{Apply}(e_2, \text{Apply}(e_1, S))$$

### Concurrency Rules
1. **$Independent(e_1, e_2) \implies$ Parallelize / Reorder Safely** (e.g., concurrent reads on immutable `ObjectRef` handles).
2. **$\neg Independent(e_1, e_2) \implies$ Enforce Monotonic Serialization** (e.g., update followed by delete on identical state key).

---

# 3. Research-to-Cortex Audit Answers (5 Key Questions)

1. **Can `AdapterExecutionContext` evolve into `CortexContext`?**  
   **Yes.** By combining invocation identity, lease tokens, resource bounds, and capability requirements into a single immutable context structure $\Gamma_I$, with worker projections $\pi_W(\Gamma_I)$.

2. **Can every external effect produce an immutable `EffectReceipt`?**  
   **Yes.** Adapters can return an `EffectReceipt` alongside the operation result, providing explicit witnesses for before/after states while preserving `INDETERMINATE` handling for non-idempotent failures.

3. **Can `ResourceContract` gain explicit `Requires` / `Provides` semantics?**  
   **Yes.** Extending `ResourceContract` into `ComponentContract` enables dynamic capability resolution and explicit satisfaction tracking.

4. **Can worker draining/replacement be formally expressed as quiescence + fencing?**  
   **Yes.** Quiescence ($\text{ActiveAssignments}(w) = 0$) and Incarnation Fencing ($g_{presented} = g_{active}$) provide a complete formal foundation for safe teardown.

5. **Can an effect-independence relation be introduced for concurrency scheduling?**  
   **Yes.** Formalizing $Independent(e_1, e_2)$ provides a mathematical justification for GIL-agnostic parallelism across independent data-plane operations.
