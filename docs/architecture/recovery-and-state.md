# Cortex Replay State Machine & Recovery Evidence Specification

**Status**: FROZEN  
**Version**: Revision #5  
**Authoritative Source**: `docs/adrs/ADR-003-polyglot-kernel.md` (§3.3)

---

## 1. Overview & Recovery Evidence Model

The Cortex Kernel relies on an evidence-based recovery model derived entirely from lifecycle events recorded in the event store. It operates without external audit logs or dynamic state inspection.

---

## 2. Command Execution Lifecycle Phases

Every command execution moves through explicit, immutable lifecycle phases:

```
[INTENT_RECORDED] ──► [EXECUTION_STARTED] ──► [SIDE_EFFECT_COMMITTED] ──► [COMPLETION_RECORDED]
```

1. **`INTENT_RECORDED`**: Command intent is safely persisted to journal.
2. **`EXECUTION_STARTED`**: Execution context initialized; capabilities checked.
3. **`SIDE_EFFECT_COMMITTED`**: External mutation or driver side-effect completed.
4. **`COMPLETION_RECORDED`**: Event store state finalized; workflow context updated.

---

## 3. Crash Window Mapping & Recovery Matrix

When a crash occurs, the recovery state machine determines the recovery state based strictly on the highest recorded lifecycle phase:

| Crash Window | Last Recorded Lifecycle Phase | Recovery Classification | Authorized Recovery Action |
|---|---|---|---|
| **Window B1 (Pre-Execution)** | `none` or `INTENT_RECORDED` | **RECOVERABLE** | Safe Re-Execution |
| **Window B2 (In-Flight)** | `EXECUTION_STARTED` (Idempotent) | **RECOVERABLE** | Safe Re-Execution via `idempotency_token` |
| **Window B2 (In-Flight)** | `EXECUTION_STARTED` (Non-Idempotent) | **IN_DOUBT** | Mandatory Operator Escalation / HALT |
| **Window B3 (Post-Commit)** | `SIDE_EFFECT_COMMITTED` | **RECOVERED_BY_REPLAY** | Synthetic Reconciliation Event Emission |

---

## 4. Semantic Parity Projection ($P_{\text{semantic}}$)

Cross-runtime equivalence between Python, Rust, Go, and Zig implementations is evaluated by computing the $P_{\text{semantic}}$ tuple sequence over execution event streams:

$$P_{\text{semantic}}(E) = \Big( \text{logical\_event\_id}, \text{causation\_id}, \text{logical\_sequence\_index}, \text{payload\_hash}, \text{lifecycle\_phase}, \text{recovery\_state}, \text{idempotency\_token} \Big)$$

Where:
- `payload_hash` $= \text{SHA-256}\Big(\text{Canonical\_CBE\_Bytes}(\text{payload})\Big)$
- `logical_sequence_index` is constrained to signed non-negative `INT64` $[0, 9223372036854775807]$.

Two implementations $A$ and $B$ achieve **Semantic Parity** if and only if for any workload $W$:

$$\forall i, \quad P_{\text{semantic}}(E_{A, i}) == P_{\text{semantic}}(E_{B, i})$$
