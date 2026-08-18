# Cortex v0.3 — Formal Protocol Semantics & Invariants

**Specification Authority**: Revision #5 (Frozen 🔒)  
**Document Stage**: Phase 3.3 Formal Baseline  
**Layer Focus**: Layer 0 (Cryptographic Identity) & Layer 1 (CBE Encoding)  
**Governance State**: Authoritative Protocol Specification  

---

## 1. Architectural Scope & Layer Hierarchy

Cortex decouples serialization, framing, semantics, and application logic into a strict 6-layer unidirectional architecture:

```
┌───────────────────────────────────────────────────────────────┐
│ Layer 5 — Applications / Agent Workflows                      │
├───────────────────────────────────────────────────────────────┤
│ Layer 4 — Execution Semantics (State, Lifecycle, Capabilities) │
├───────────────────────────────────────────────────────────────┤
│ Layer 3 — Messages & Operations (RPC, Invocation, Events)     │
├───────────────────────────────────────────────────────────────┤
│ Layer 2 — Streaming & Framing (Sequence, Flow Control, Window) │
├───────────────────────────────────────────────────────────────┤
│ Layer 1 — CBE Canonical Binary Encoding (v0.3 Baseline)        │  ◄── FROZEN 🔒
├───────────────────────────────────────────────────────────────┤
│ Layer 0 — Cryptographic Identity & Bytes (SHA-1 / UUIDv5)    │  ◄── FROZEN 🔒
└───────────────────────────────────────────────────────────────┘
```

### Unidirectional Invariant Rule
$$\forall n \in \{1 \dots 5\}, \quad \text{Layer}_n \text{ may depend on } \text{Layer}_k \quad (k < n)$$
$$\forall k \in \{0 \dots 4\}, \quad \text{Layer}_k \text{ has zero dependency or awareness of } \text{Layer}_m \quad (m > k)$$

---

## 2. Pillar A — Serialization & AST Invariants

### Invariant 1: Serialization Identity & Determinism
For any valid Cortex AST value $v \in \mathcal{V}_{\text{Cortex}}$:

$$\text{encode}(\text{decode}(\text{encode}(v))) \equiv \text{encode}(v)$$

Furthermore, encoding is deterministic across space and time:
$$\forall v_1, v_2 \in \mathcal{V}_{\text{Cortex}}, \quad v_1 \equiv_{\text{sem}} v_2 \iff \text{encode}(v_1) = \text{encode}(v_2)$$

### Invariant 2: Canonical AST Round-Trip Equivalence
For any valid CBE byte sequence $b \in \mathcal{B}_{\text{CBE\_Valid}}$:

$$\text{decode}(\text{encode}(\text{decode}(b))) \equiv \text{decode}(b)$$

---

## 3. Pillar B — Cryptographic Identity Preservation

### Invariant 3: Explicit Namespace UUIDv5 Lineage
The cryptographic identity string $\text{UUIDv5}$ derived from raw CBE payload bytes $B \in \mathcal{B}^*$ and fixed 16-byte namespace $N_{16} \in \mathcal{B}^{16}$ is defined by:

$$\text{Preimage} = N_{16} \mathbin{\Vert} B$$
$$D_{20} = \text{SHA-1}(\text{Preimage})$$
$$R_{16} = D_{20}[0 \dots 15]$$
$$R_{16}[6] = (R_{16}[6] \land \mathtt{0x0F}) \lor \mathtt{0x50} \quad (\text{RFC 4122 Version 5})$$
$$R_{16}[8] = (R_{16}[8] \land \mathtt{0x3F}) \lor \mathtt{0x80} \quad (\text{RFC 4122 Variant})$$

$$\text{UUIDv5}(N_{16}, B) = \text{FormatHexUUID}(R_{16})$$

* **Invariance Guarantee**: $\text{UUIDv5}(N_{16}, B)$ is invariant under host architecture, CPU endianness, language runtime, and memory layout.

---

## 4. Pillar C — Cross-Runtime Rejection Class Parity

### Invariant 4: Fault Domain Homomorphism
For any invalid or adversarial wire byte sequence $x \in \mathcal{B}_{\text{Malformed}}$:

$$\text{Class}(\text{PythonError}(x)) \equiv \text{Class}(\text{RustError}(x)) \equiv \text{Class}(\text{GoError}(x))$$

---

## 5. Pillar D — Boundary & Resource Constraints

### 1. Integer Precision Domain
$$\text{Domain}(\text{Int}) = [ -2^{63}, \, 2^{63} - 1 ] \quad (\text{Signed 64-bit IEEE integer range})$$
- Leading zeros (e.g. `I01`) are forbidden.
- Digit strings exceeding 21 characters trigger `CBE_INT_OVERFLOW`.

### 2. Floating-Point Finiteness Domain
$$\text{Domain}(\text{Float}) = \{ f \in \mathbb{R} \mid -\infty < f < +\infty \}$$
- $\text{NaN}$, $+\infty$, and $-\infty$ are strictly forbidden.
- IEEE 754 Big-Endian 64-bit hex encoding (`D<16_hex_chars>`).
- $-0.0$ is normalized to $+0.0$ (`D0000000000000000`).

### 3. String & Key Canonical Ordering
- All strings must be valid UTF-8 sequences.
- Map keys are sorted strictly by lexicographical UTF-8 byte order of NFC-normalized keys ($K_i <_{\text{byte}} K_{i+1}$). Example: `"aa" < "b"`.
- Duplicate keys after NFC normalization trigger `CBE_DUPLICATE_KEY`.
