# Cross-Runtime Fault Domain Taxonomy Matrix

**Specification Authority**: Revision #5 (Frozen 🔒)  
**Document Stage**: Phase 3.3 Formal Baseline  
**Coverage**: Python Kernel (#1), Rust Engine (#2), Go Adapter (#3)  

---

## 1. Unified Error Classification Taxonomy

Every CBE wire violation maps deterministically to one of the 8 canonical error classes defined in Revision #5:

```
                               CBE WIRE PARSING
                                      │
                                      ▼
                      ┌───────────────┴───────────────┐
                      │    WIRE GRAMMAR VALIDATION    │
                      └───────────────┬───────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
  TAG & LENGTH                  VALUE DOMAIN                 CANONICALITY
  • CBE_UNKNOWN_TAG             • CBE_INT_OVERFLOW           • CBE_NON_CANONICAL_MAP
  • CBE_INVALID_LENGTH          • CBE_FLOAT_NONFINITE        • CBE_DUPLICATE_KEY
                                • CBE_INVALID_UTF8
                                • CBE_NON_NFC
```

---

## 2. Cross-Runtime Fault Mapping Matrix

| Formal Fault Code | Trigger Condition | Python Impl (#1) | Rust Impl (#2) | Go Impl (#3) |
| :--- | :--- | :--- | :--- | :--- |
| `CBE_INVALID_UTF8` | Non-UTF-8 byte sequence in String or Map key | `UnicodeDecodeError` | `CbeError::InvalidUtf8` | `cbe.CodeInvalidUTF8` |
| `CBE_NON_NFC` | String payload not in canonical NFC form | `NonNFCError` | `CbeError::NonNFC` | `cbe.CodeNonNFC` |
| `CBE_DUPLICATE_KEY` | Map contains duplicate keys (NFC normalized) | `DuplicateKeyError` | `CbeError::DuplicateKey` | `cbe.CodeDuplicateKey` |
| `CBE_NON_CANONICAL_MAP` | Map keys not in ascending UTF-8 byte order | `NonCanonicalMapError` | `CbeError::UnsortedMap` | `cbe.CodeNonCanonicalMap` |
| `CBE_INT_OVERFLOW` | Integer string > 21 chars or out of $[-2^{63}, 2^{63}-1]$ | `OverflowError` / `ValueError` | `CbeError::IntOverflow` | `cbe.CodeIntOverflow` |
| `CBE_FLOAT_NONFINITE` | Decoding or encoding NaN, $+\infty$, or $-\infty$ | `ValueError` | `CbeError::FloatNonFinite` | `cbe.CodeFloatNonFinite` |
| `CBE_INVALID_LENGTH` | Leading zeros in len, truncated payload, missing `:` | `TruncatedFrameError` | `CbeError::Truncated` | `cbe.CodeInvalidLength` |
| `CBE_UNKNOWN_TAG` | Unrecognized type tag byte | `UnknownTagError` | `CbeError::UnknownTag` | `cbe.CodeUnknownTag` |

---

## 3. Formal Rejection Parity Invariant Rule

$$\forall x \in \mathcal{B}_{\text{Malformed}}, \quad \mathcal{M}_{\text{Python}}(x) \equiv \mathcal{M}_{\text{Rust}}(x) \equiv \mathcal{M}_{\text{Go}}(x)$$

Where $\mathcal{M}_{R}(x)$ represents the mapping function of runtime $R$ from raw malformed wire bytes to the unified fault domain classification set $\mathcal{F} = \{ \text{CBE\_INVALID\_UTF8}, \dots, \text{CBE\_UNKNOWN\_TAG} \}$.
