# Cortex-CBE Formal Canonical Serialization Specification

**Status**: FROZEN  
**Version**: Revision #5  
**Authoritative Source**: `docs/adrs/ADR-003-polyglot-kernel.md` (§3.1)

---

## 1. Overview & Objectives

Cortex Canonical Byte Encoding (Cortex-CBE) is a rigid, zero-ambiguity binary serialization grammar designed to guarantee deterministic serialization across all runtimes (Python, Rust, Go, Zig). CBE ensures that identical semantic data structures yield bit-for-bit identical byte streams across heterogeneous platforms.

---

## 2. Formal CBE Grammar (EBNF)

```ebnf
CBEValue     ::= NullVal | BoolVal | IntVal | FloatVal | StringVal | ListVal | DictVal ;
NullVal      ::= "N" ;              (* Note: Tag byte 0x4E 'N' in wire format; EBNF 'NULL' notation marked as OPEN RECONCILIATION *)
BoolVal      ::= "B1" | "B0" ;
IntVal       ::= "I" ("0" | ("-"? [1-9] [0-9]*)) ;
FloatVal     ::= "D" IEEE754_BE_HEX ; (* Note: Tag byte 0x44 'D' for Double-Precision Float64; EBNF 'F' notation marked as OPEN RECONCILIATION *)
StringVal    ::= "S" ByteLen ":" ByteSeq ;
ListVal      ::= "L" ElementCount ":" { CBEValue } ;
DictVal      ::= "M" PairCount ":" { StringVal CBEValue } ;

ByteLen      ::= "0" | ([1-9] [0-9]*) ;
ElementCount ::= "0" | ([1-9] [0-9]*) ;
PairCount    ::= "0" | ([1-9] [0-9]*) ;
```

---

## 3. Strict Decoder Trailing-Byte Invariant

To guarantee zero parser ambiguity, every conforming CBE decoder MUST enforce exact consumed length equality:

$$\text{decode}(x) = (v, n) \implies n = |x| \quad \text{for all complete top-level CBE byte streams } x$$

If $n < |x|$, the trailing bytes MUST be rejected with `CBE_TRAILING_BYTES_ERROR`.

---

## 3. Normative Encoding Rules

### 3.1 Integers (`IntVal`)
- **Domain**: Signed 64-bit Integers (`INT64`), range $[-9223372036854775808, 9223372036854775807]$.
- **Format**: `I<decimal_string>` (e.g., `I100`, `I-42`, `I0`).
- **Prohibitions**:
  - `UINT64` is strictly forbidden.
  - Leading zeros are prohibited except for literal zero (`I0`). `I00` and `I-0` trigger `CBE_SYNTAX_ERROR`.

### 3.2 Floating-Point Numbers (`FloatVal`)
- **Format**: `F` followed by a 16-character uppercase hexadecimal string representing 64-bit IEEE 754 Big-Endian binary encoding (`F` + 8 bytes in hex).
- **Normalization**:
  - Negative Zero (`-0.0`) MUST be normalized to Positive Zero (`+0.0`, hex `0000000000000000`) before serialization.
- **Prohibitions**:
  - All `NaN` bit patterns, `+Infinity`, and `-Infinity` trigger immediate, unrecoverable `CBE_FLOAT_OUT_OF_BOUNDS` errors.

### 3.3 Strings (`StringVal`)
- **Format**: `S<byte_length>:<utf8_bytes>` (e.g., `S3:USD`, `S6:amount`).
- **Normalization**:
  - All string inputs MUST be normalized to Unicode **NFC** (Normalization Form C) prior to byte length calculation and UTF-8 encoding.
  - Length indicator `<byte_length>` specifies exact raw UTF-8 byte count, NOT character count.
- **Validation**:
  - Any malformed or invalid UTF-8 byte sequence triggers an immediate `CBE_INVALID_UTF8` error.

### 3.4 Maps & Objects (`DictVal`)
- **Format**: `M<pair_count>:<key_1><val_1><key_2><val_2>...` (e.g., `M2:S6:amountI100S8:currencyS3:USD`).
- **Key Sorting**:
  - Map keys MUST be sorted in ascending lexicographical order based on raw UTF-8 byte sequence after NFC normalization.
- **Duplicate Keys**:
  - Duplicate keys are strictly illegal. Encountering duplicate keys triggers a `CBE_NON_CANONICAL_MAP` parser error.

### 3.5 Lists & Containers (`ListVal`)
- **Format**: `L<element_count>:<elem_1><elem_2>...` (e.g., `L0:`, `L2:S1:aI10`).
- **Recursive Parsing**:
  - Containers support arbitrary nesting governed by explicit count prefixes (`L<count>`, `M<count>`), eliminating structural delimiter collision.

---

## 4. Reserved Namespace Convention & Offline Resolution

> **NORMATIVE NAMESPACE POLICY**:
> `cortex.security` is a reserved future namespace identifier (`$id`) and is **not an operational dependency** until explicitly activated.
>
> 1. **Identifier Only**: Any URL matching `https://cortex.security/...` inside a JSON Schema is an immutable schema identifier (`$id`), not a fetchable endpoint.
> 2. **Offline Resolution**: All manifest and profile schema resolution (`$schema`) MUST execute locally using deterministic relative paths (e.g. `./docs/architecture/...` or `./docs/spec/...`).
> 3. **Zero Network Dependence**: No build step, test harness, validator, CI workflow, or runtime binary is permitted to execute DNS resolution or HTTP requests targeting `cortex.security`.
