# Cortex 4-Domain Identity Model Specification

**Status**: FROZEN  
**Version**: Revision #5  
**Authoritative Source**: `docs/adrs/ADR-003-polyglot-kernel.md` (§3.2)

---

## 1. Overview & Identity Domain Separation

To decouple causal lineage from storage implementations and external application tokens, Cortex formalizes identity into four distinct, non-overlapping domains:

| Identity Domain | Generator / Origin | Primary Purpose | Contract Status |
|---|---|---|---|
| `logical_event_id` | Cortex Contract Kernel | Causal DAG node identity; drives $P_{\text{semantic}}$ cross-runtime parity | **Normative / Frozen** |
| `idempotency_token` | Cortex Contract Kernel | External mutation deduplication key across runtimes | **Normative / Frozen** |
| `application_idempotency_key` | Caller / Application | Opaque business/request metadata carried outside payload hash | **Informational / Metadata** |
| `runtime_event_id` | Runtime EventStore | Physical storage primary key (UUIDv4/v7 or DB PK) | **Implementation Detail** |

---

## 2. Deterministic Derivation Formulas

### 2.1 Logical Event ID (`logical_event_id`)
Derived deterministically via UUIDv5 using standard DNS namespace constant `NAMESPACE_CORTEX_SYSTEM`:

$$\text{NAMESPACE\_CORTEX\_SYSTEM} = \text{a1b2c3d4-0000-5000-8000-000000000001}$$

Formally derived over the raw byte sequence of a CBE 4-element List (`L4:...`):

$$\text{logical\_event\_id} = \text{UUIDv5}\left(\text{NAMESPACE\_CORTEX\_SYSTEM}, \text{Canonical\_CBE\_Bytes}\Big(\big[\text{workflow\_id}, \text{command\_type}, \text{causation\_id}, \text{payload}\big]\Big)\right)$$

### 2.2 Idempotency Token (`idempotency_token`)
Derived deterministically via UUIDv5 using dedicated namespace constant `NAMESPACE_CORTEX_IDEMPOTENCY`:

$$\text{NAMESPACE\_CORTEX\_IDEMPOTENCY} = \text{a1b2c3d4-0000-5000-8000-000000000002}$$

$$\text{op\_identity\_hash} = \text{SHA-256}\Big(\text{Canonical\_CBE\_Bytes}(\text{parameters})\Big)$$

$$\text{idempotency\_token} = \text{UUIDv5}\left(\text{NAMESPACE\_CORTEX\_IDEMPOTENCY}, \text{UTF-8}\Big(\text{"idempotency:"} + \text{workflow\_id} + \text{":"} + \text{command\_type} + \text{":"} + \text{op\_identity\_hash}\Big)\right)$$

- **Presence Contract**: Typed `OPTIONAL` (evaluates to canonical lowercase UUID string when present, or `null` when omitted). Sentinels like `"NONE"` are prohibited.

---

## 3. Normative Cleanroom Test Vectors

Derived under `NAMESPACE_CORTEX_SYSTEM` (`a1b2c3d4-0000-5000-8000-000000000001`):

| Vector ID | `workflow_id` | `command_type` | `causation_id` | Canonical CBE Tuple Input (`L4:...`) | Locked `logical_event_id` |
|---|---|---|---|---|---|
| **TV-A** | `wf-101` | `payment:charge` | `caus-999` | `L4:S6:wf-101S14:payment:chargeS8:caus-999M2:S6:amountI100S8:currencyS3:USD` | `a6afec1e-b59d-55f4-ac38-f6ae6d37d268` |
| **TV-B** | `wf-102` | `file:write` | `caus-1000` | `L4:S6:wf-102S10:file:writeS9:caus-1000M1:S4:pathS13:/tmp/data.txt` | `d926fda1-f3ea-5672-bd7f-d2858358b002` |
| **TV-C** | `wf-103` | `email:send` | `caus-1001` | `L4:S6:wf-103S10:email:sendS9:caus-1001M1:S2:toS16:user@example.com` | `c588d5ca-4c8b-5f7b-8ebc-0227244f6820` |
| **TV-Root** | `wf-777` | `order:process` | `00000000-0000-0000-0000-000000000000` | `L4:S6:wf-777S13:order:processS36:00000000-0000-0000-0000-000000000000L0:` | `983e24da-d481-5a1b-8624-26c18f8b6b01` |
