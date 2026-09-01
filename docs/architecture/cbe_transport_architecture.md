# CORTEX — CBE TRANSPORT & DECODER MEMORY BOUND ARCHITECTURE SPECIFICATION

**Document Identifier:** `CORTEX-SPEC-CBE-2026-V1`  
**Classification:** Canonical Protocol Architecture Specification  
**Subsystem:** Layer 2 Canonical Binary Encoding (CBE) Streaming Transport & Decoder Security  
**Status:** IMPLEMENTATION-VERIFIED & SPECIFICATION-LOCKED  

---

## 1. CBE PROTOCOL CALIBRATED SECURITY CLAIMS

Cortex explicitly decouples transport framing boundaries from higher-layer security assertions. The table below defines the authoritative mapping of security properties across system layers:

| Security Property | CBE Layer 2 Transport (`cortex.cbe.streaming`) | Higher Application / Control Layers |
| :--- | :---: | :---: |
| **Framing Boundaries (`b"CF"`, 11-byte Header)** | ✅ Provided | N/A |
| **Payload Length Validation ($\le 16\text{ MiB}$)** | ✅ Provided | N/A |
| **In-Session Sequence Ordering (`uint32`)** | ✅ Provided | N/A |
| **Cross-Session Replay Prevention** | ❌ **NOT Provided** | Monotonic `LeaseEpoch` fencing & `InvocationStateLedger` |
| **Cryptographic Data Integrity** | ❌ **NOT Provided** | `CommitEvent` / `CausalWitness` SHA-256 rolling digest chains |
| **Authentication & Worker Identity** | ❌ **NOT Provided** | `ExecutionToken`, TLS certificates, POSIX socket peer creds |
| **Authorization & Capability Scoping** | ❌ **NOT Provided** | Gateway TCB, `LeaseManager`, Linux Landlock/Seccomp |

> **Normative Security Statement:**  
> *CBE provides bounded framing, length validation, and per-session transport sequence enforcement. Authorization, cryptographic provenance, and cross-session replay resistance are provided strictly by higher layers.*

---

## 2. DERIVATION OF THE FORMAL DECODER MEMORY BOUND

Arbitrary constant memory ceilings (e.g., un-derived 32 MiB guesses) are forbidden in the Cortex architecture. The maximum decoder buffer memory allocation $C_{\text{decoder}}$ is derived strictly from protocol parameters:

### Protocol Parameters:
- $\text{MAX\_FRAME\_SIZE} = 16,777,216 \text{ bytes (16 MiB)}$ (`MAX_FRAME_SIZE` in `streaming.py:17`)
- $\text{HEADER\_SIZE} = 11 \text{ bytes}$ (`HEADER_SIZE` in `streaming.py:16`)
- $N_{\text{max\_buffered\_frames}} = \text{Maximum unconsumed contiguous frames buffered per stream decoder instance}$
- $\text{MARGIN}_{\text{overhead}} = \text{Internal parser state & reassembly overhead margin (64 KiB = 65,536 bytes)}$

### Formal Upper Bound Equation:
$$C_{\text{decoder}} \le N_{\text{max\_buffered\_frames}} \times (\text{MAX\_FRAME\_SIZE} + \text{HEADER\_SIZE}) + \text{MARGIN}_{\text{overhead}}$$

### Derivation Scenarios:
1. **Single In-Flight Frame Decoder ($N_{\text{max\_buffered\_frames}} = 1$):**
   $$C_{\text{decoder}}^{(1)} = 1 \times (16,777,216 + 11) + 65,536 = 16,842,763 \text{ bytes} \approx 16.0625 \text{ MiB}$$

2. **Dual Contiguous Frame Decoder ($N_{\text{max\_buffered\_frames}} = 2$):**
   $$C_{\text{decoder}}^{(2)} = 2 \times (16,777,216 + 11) + 65,536 = 33,620,000 \text{ bytes} \approx 32.0625 \text{ MiB}$$

### Decoder Enforcement Rule:
In `StreamDecoder.feed(chunk)`, if `len(self._buffer) + len(chunk) > C_{\text{decoder}}^{(1)}` (or $C_{\text{decoder}}^{(2)}$ depending on configured stream concurrency), the stream decoder MUST reject the input and raise `CBEFrameTooLargeError`, closing the transport socket immediately to guarantee prevention of memory exhaustion attacks.

---

## 3. FRAME WIRE FORMAT & STATE MACHINE

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Magic 'CF'           |  Frame Type   |               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+             +
|                    Sequence Number (uint32)                   |
+                               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                               |     Payload Length (uint32)   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                     Payload Bytes (N Bytes)                   +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Frame Decoder State Machine:
1. **`READ_MAGIC`**: Read 2 bytes. If $\neq \text{b"CF"}$, raise `CBEMagicMismatchError`.
2. **`READ_HEADER`**: Read 9 bytes (Total header 11 bytes). Parse `FrameType` (1B), `Sequence` (4B `uint32`), `PayloadLen` (4B `uint32`).
3. **`VALIDATE_HEADER`**: Assert `PayloadLen` $\le 16,777,216$. Assert `Sequence` matches expected in-session sequence counter.
4. **`READ_PAYLOAD`**: Read $N = \text{PayloadLen}$ bytes. If EOF before $N$ bytes arrive, raise `CBETruncatedPayloadError`.
5. **`EMIT_FRAME`**: Construct frozen `CortexFrame` AST node and increment expected in-session sequence counter.

---
