# Cortex v0.3 — Layer 2 Streaming & Framing Protocol Specification

**Specification Authority**: Revision #5 Baseline + Layer 2 Extension  
**Document Stage**: Phase 3.2 Formal Specification (Normative Baseline)  
**Layer Focus**: Layer 2 (Streaming & Transport Framing)  
**Governance State**: LOCKED & BOUNDARY FROZEN 🔒  

---

## 1. Architectural Role & Layer Decoupling

Layer 2 provides deterministic stream framing and transport boundaries over any byte-oriented stream (TCP, Unix Sockets, QUIC, IPC Pipes, Shared Memory).

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 2 — Streaming & Framing (Transport Boundaries) 🔒     │
├─────────────────────────────────────────────────────────────┤
│ Layer 1 — CBE Canonical Binary Encoding (v0.3 Baseline 🔒)  │
├─────────────────────────────────────────────────────────────┤
│ Layer 0 — Cryptographic Identity & Bytes (SHA-1 / UUIDv5 🔒)│
└─────────────────────────────────────────────────────────────┘
```

### Core Invariants
1. **Value Completeness**: Every `DATA` frame payload contains a complete, valid Layer 1 CBE value. Intra-value chunking across frames is strictly forbidden.
2. **Identity Decoupling**: Frame headers contain zero cryptographic identity parameters (no SHA-1, no UUIDv5). Content identity belongs to Layer 0/1; transport framing belongs strictly to Layer 2.
3. **Bounded Memory Invariant**: Working memory is bounded $O(1)$ relative to total stream size. Individual frame buffers are capped at $\text{MAX\_FRAME\_SIZE} = 16\text{ MiB} \quad (16,777,216\text{ bytes})$.
4. **Round-Trip Frame Determinism**: For any valid frame:
   $$\text{encode\_frame}(\text{decode\_frame}(\text{frame\_bytes})) \equiv \text{frame\_bytes}$$

---

## 2. Frame Wire Grammar & Layout

A Layer 2 Transport Frame consists of an **11-byte fixed header** followed by an $N$-byte payload:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Magic (0x4346)       | Type (0x01)   |               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       Sequence Number (Big-Endian uint32)                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       Payload Length N (Big-Endian uint32, N <= 16MiB)        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                       Payload (N Bytes)                       +
|            (Complete Layer 1 CBE Value or Control Data)       |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Header Fields
- **Magic (2 Bytes)**: Must equal `0x43 0x46` (ASCII `"CF"` for Cortex Frame).
- **Frame Type (1 Byte)**:
  - `0x01` (`DATA`): Payload length $1 \le N \le 16\text{ MiB}$. Payload is a complete, valid Layer 1 CBE binary value.
  - `0x02` (`PING`): Transport keepalive / latency probe ($N=0$ strictly required).
  - `0x03` (`PONG`): Probe response ($N=0$ strictly required).
  - `0x04` (`END`): Graceful stream termination frame ($N=0$ strictly required).
  - `0xFF` (`ERROR`): Explicit stream abort frame ($N=4$ bytes containing 32-bit big-endian uint32 fault code).
- **Sequence Number (4 Bytes)**: Big-endian unsigned 32-bit integer (`uint32`). Monotonically increments from `0` ($S_0 = 0, S_{n+1} = S_n + 1$).
  - **No Wraparound Policy**: Attempting to wrap around at $\text{UINT32\_MAX} \; (4,294,967,295)$ MUST trigger `CBE_FRAME_SEQUENCE_OVERFLOW`.
- **Payload Length (4 Bytes)**: Big-endian unsigned 32-bit integer (`uint32`) specifying length $N$ of payload bytes ($0 \le N \le 16,777,216$).

---

## 3. Layer 2 Fault Taxonomy Expansion

| Fault Code | Code ID | Trigger Condition | Fault Action |
| :--- | :--- | :--- | :--- |
| `CBE_FRAME_MAGIC_MISMATCH` | `0x2001` | Header magic != `0x4346` | Immediate stream abort |
| `CBE_FRAME_UNKNOWN_TYPE` | `0x2002` | Unrecognized frame type byte | Immediate stream abort |
| `CBE_FRAME_TOO_LARGE` | `0x2003` | Length prefix $N > 16,777,216$ | Immediate stream abort |
| `CBE_FRAME_SEQUENCE_GAP` | `0x2004` | Received $S \neq S_{expected}$ | Immediate stream abort |
| `CBE_FRAME_SEQUENCE_OVERFLOW` | `0x2005` | Attempting sequence increment past $2^{32}-1$ | Immediate stream abort |
| `CBE_FRAME_TRUNCATED_HEADER` | `0x2006` | EOF received before 11 header bytes | Immediate stream abort |
| `CBE_FRAME_TRUNCATED_PAYLOAD` | `0x2007` | EOF received before $N$ payload bytes | Immediate stream abort |
| `CBE_FRAME_INVALID_CONTROL_PAYLOAD` | `0x2008` | Non-zero payload on PING/PONG/END or $N \neq 4$ on ERROR | Immediate stream abort |
| `CBE_FRAME_DATA_EMPTY` | `0x2009` | DATA frame with $N=0$ payload | Immediate stream abort |

---

## 4. Normative Layer 2 Streaming Vector Corpus

Ground-truth vector corpus directory: [`research/formalization/streaming/`](../../research/formalization/streaming/)

| Vector Relative Path | Category | Purpose | SHA-256 Digest |
| :--- | :--- | :--- | :--- |
| `valid/st-01-single-frame.cbeframe` | Valid | Single DATA frame ($S=0$) | `1816bed7f8f4f8326e48131de2413ad1ac3396d3257413faf1c568e8cd7423b2` |
| `valid/st-02-multi-frame.cbeframe` | Valid | Multi-frame session ($S_0, S_1, S_{END}$) | `780500d80de5f03f41d2224df903fb537b005deb504b982496e5eb3f514e9283` |
| `valid/st-03-control-sequence.cbeframe` | Valid | Interleaved control frame sequence | `c44aa05d614c1adb463fce41e09ef06303bc81e092fe7f2647ed86ee373e9eab` |
| `valid/st-04-clean-end.cbeframe` | Valid | Graceful stream close with END | `402e825f2955ae01b2415dbb9e8af361d3fcbaa6afa33f244fa1a443860601c2` |
| `boundaries/st-b01-zero-length-control.cbeframe` | Boundary | Zero-payload END control frame | `e622e69064d853a31f91d42f65950711ca64a37e38a8eebebdd7c5ff6de8698c` |
| `boundaries/st-b02-max-frame-16MiB.cbeframe` | Boundary | 16,777,216 byte maximum frame cap | `09c33314d9a58f058d537a0c1f8a4f04673a7bc2b8fd2727479f4240d72c0fe0` |
| `boundaries/st-b03-sequence-zero.cbeframe` | Boundary | Initial frame sequence $S=0$ | `1816bed7f8f4f8326e48131de2413ad1ac3396d3257413faf1c568e8cd7423b2` |
| `boundaries/st-b04-sequence-max.cbeframe` | Boundary | Terminal frame sequence $S=\text{UINT32\_MAX}$ | `b2adeaf2ffa38311d1d95dea9a96fd95631199355c9747fa4dc64bb7f4cd67c5` |
| `invalid/st-err-01-oversized.cbeframe` | Invalid | Frame length $17\text{ MiB} > 16\text{ MiB}$ cap | `dd442207d8498199661c2ae3c01689b82a465c38f423c18e3fff2a49c20a5969` |
| `invalid/st-err-02-truncated-header.cbeframe` | Invalid | Header length 5 bytes < 11 bytes | `607e246b52fba58db57d281cb30bb1713df50c28f28b79d8452ef4306a9a97f9` |
| `invalid/st-err-03-truncated-payload.cbeframe` | Invalid | Stream ends before payload bytes | `e85c9344adc6ba0a133dd827a6c864571279c14a60ced6810b8caa19401be2fb` |
| `invalid/st-err-04-bad-magic.cbeframe` | Invalid | Header magic `XY` != `CF` | `5e0cc94b85d15ff8e0164ee30ec4b811efe64724ae10823f95343afbd94d7453` |
| `invalid/st-err-05-sequence-gap.cbeframe` | Invalid | Sequence gap (skips from $0 \to 2$) | `68e20c6da2a5a20e8e59757c53f856723892f5292267a9fcc6164ea984225ca9` |
| `invalid/st-err-06-sequence-overflow.cbeframe` | Invalid | Sequence wrap attempt past $\text{UINT32\_MAX}$ | `9de49c9b729eada8481b56c5ab36458311fd1e899b24e7d5ad3ddb6bc834f221` |
