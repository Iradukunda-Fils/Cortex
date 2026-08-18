"""
Cortex Canonical Byte Encoding (CBE) Deterministic Encoder
"""

import struct
from typing import Any

from cortex.cbe.errors import (
    CBEDuplicateKeyError,
    CBEError,
)
from cortex.cbe.normalization import (
    check_int64_bounds,
    normalize_float,
    normalize_nfc_string,
)
from cortex.cbe.types import (
    Bool,
    Bytes,
    CortexValue,
    Float,
    Int,
    List,
    Map,
    Null,
    String,
)


def encode(val: CortexValue) -> bytes:
    """
    Deterministically encode a CortexValue AST node to canonical CBE bytes.
    Zero intermediate stringification or JSON fallback.
    """
    if not isinstance(val, CortexValue):
        val = CortexValue.from_python(val)

    if isinstance(val, Null):
        return b"N"

    elif isinstance(val, Bool):
        return b"B1" if val.value else b"B0"

    elif isinstance(val, Int):
        v = check_int64_bounds(val.value)
        return f"I{v}".encode("ascii")

    elif isinstance(val, Float):
        f = normalize_float(val.value)
        packed_bytes = struct.pack(">d", f)
        hex_str = packed_bytes.hex().lower()
        return f"D{hex_str}".encode("ascii")

    elif isinstance(val, String):
        nfc_str = normalize_nfc_string(val.value)
        utf8_bytes = nfc_str.encode("utf-8")
        return f"S{len(utf8_bytes)}:".encode("ascii") + utf8_bytes

    elif isinstance(val, Bytes):
        raw_bytes = val.value
        return f"B{len(raw_bytes)}:".encode("ascii") + raw_bytes

    elif isinstance(val, List):
        out = f"L{len(val.elements)}:".encode("ascii")
        for elem in val.elements:
            out += encode(elem)
        return out

    elif isinstance(val, Map):
        pairs_with_utf8_keys: list[tuple[bytes, String, CortexValue]] = []
        seen_keys: set[bytes] = set()

        for k, v in val.pairs:
            nfc_k_str = normalize_nfc_string(k.value)
            nfc_k_bytes = nfc_k_str.encode("utf-8")

            if nfc_k_bytes in seen_keys:
                raise CBEDuplicateKeyError(f"Duplicate key after NFC normalization: {k.value!r}")
            seen_keys.add(nfc_k_bytes)
            pairs_with_utf8_keys.append((nfc_k_bytes, k, v))

        # Sort strictly by UTF-8 byte order of NFC key
        pairs_with_utf8_keys.sort(key=lambda item: item[0])

        out = f"M{len(pairs_with_utf8_keys)}:".encode("ascii")
        for utf8_k_bytes, k_node, v_node in pairs_with_utf8_keys:
            out += encode(k_node)
            out += encode(v_node)
        return out

    else:
        raise CBEError(f"Unsupported AST node type: {type(val)}")


def encode_python(obj: Any) -> bytes:
    """Convenience helper to encode raw Python object by wrapping in CortexValue AST first."""
    return encode(CortexValue.from_python(obj))
