"""
Cortex Canonical Byte Encoding (CBE) Strict Non-Delimiter Decoder
"""

import struct
import unicodedata

from cortex.cbe.errors import (
    CBEDuplicateKeyError,
    CBEFloatNonFiniteError,
    CBEIntOverflowError,
    CBEInvalidLengthError,
    CBEInvalidUTF8Error,
    CBENonCanonicalMapError,
    CBENonNFCError,
    CBEUnknownTagError,
)
from cortex.cbe.normalization import (
    check_int64_bounds,
    normalize_float,
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


def _read_count(data: bytes, offset: int) -> tuple[int, int]:
    """Read a non-negative count/length prefix terminated by ':'."""
    end = data.find(b":", offset)
    if end == -1:
        raise CBEInvalidLengthError("Truncated stream: missing ':' length delimiter")
    len_str = data[offset:end].decode("ascii", errors="replace")
    if not len_str.isdigit():
        raise CBEInvalidLengthError(f"Invalid count prefix: {len_str!r}")
    if len(len_str) > 1 and len_str.startswith("0"):
        raise CBEInvalidLengthError(f"Forbidden leading zero in count: {len_str!r}")
    return int(len_str), end + 1


def decode(data: bytes, offset: int = 0) -> tuple[CortexValue, int]:
    """
    Strictly parse canonical CBE bytes without delimiter search loops.
    Enforces exact byte consumption and strict validation checks.
    """
    if offset >= len(data):
        raise CBEInvalidLengthError("Unexpected end of stream")

    tag = data[offset : offset + 1]

    if tag == b"N":
        return Null(), offset + 1

    elif tag == b"B":
        if offset + 1 >= len(data):
            raise CBEInvalidLengthError("Truncated Bool tag")
        val_byte = data[offset + 1 : offset + 2]
        if val_byte == b"1":
            return Bool(True), offset + 2
        elif val_byte == b"0":
            return Bool(False), offset + 2
        else:
            # Bytes tag prefix B<len>:
            length, payload_offset = _read_count(data, offset + 1)
            if payload_offset + length > len(data):
                raise CBEInvalidLengthError("Truncated Bytes payload")
            raw_bytes = data[payload_offset : payload_offset + length]
            return Bytes(raw_bytes), payload_offset + length

    elif tag == b"I":
        curr = offset + 1
        if curr >= len(data):
            raise CBEInvalidLengthError("Truncated Int stream")

        is_neg = False
        if data[curr : curr + 1] == b"-":
            is_neg = True
            curr += 1

        start_digits = curr
        while curr < len(data) and ord(b"0") <= data[curr] <= ord(b"9"):
            curr += 1

        digits_str = data[start_digits:curr].decode("ascii", errors="replace")
        if not digits_str:
            raise CBEInvalidLengthError("Missing integer digits")

        if len(digits_str) > 21:
            raise CBEIntOverflowError(f"Integer digit string exceeds 64-bit bounds length limit: {len(digits_str)}")

        if len(digits_str) > 1 and digits_str.startswith("0"):
            raise CBEInvalidLengthError(f"Forbidden leading zero in int: {digits_str}")

        val_int = int(digits_str)
        if is_neg:
            val_int = -val_int

        check_int64_bounds(val_int)
        return Int(val_int), curr

    elif tag == b"D":
        if offset + 17 > len(data):
            raise CBEInvalidLengthError("Truncated Float D tag")
        hex_bytes = data[offset + 1 : offset + 17]
        try:
            raw_bin = bytes.fromhex(hex_bytes.decode("ascii"))
        except ValueError:
            raise CBEFloatNonFiniteError(f"Invalid float hex digits: {hex_bytes!r}")

        (val_float,) = struct.unpack(">d", raw_bin)
        f_norm = normalize_float(val_float)
        return Float(f_norm), offset + 17

    elif tag == b"S":
        length, payload_offset = _read_count(data, offset + 1)
        if payload_offset + length > len(data):
            raise CBEInvalidLengthError("Truncated String payload")

        raw_payload = data[payload_offset : payload_offset + length]
        try:
            decoded_str = raw_payload.decode("utf-8")
        except UnicodeDecodeError as e:
            raise CBEInvalidUTF8Error(f"Invalid UTF-8 sequence in string: {e}")

        # Strict NFC validation — DO NOT SILENTLY NORMALIZE!
        if unicodedata.normalize("NFC", decoded_str) != decoded_str:
            raise CBENonNFCError(
                f"String payload is not in canonical NFC form: {decoded_str!r}"
            )

        return String(decoded_str), payload_offset + length

    elif tag == b"L":
        count, curr = _read_count(data, offset + 1)
        elements: list[CortexValue] = []
        for _ in range(count):
            elem, curr = decode(data, curr)
            elements.append(elem)
        return List(elements), curr

    elif tag == b"M":
        pair_count, curr = _read_count(data, offset + 1)
        pairs: list[tuple[String, CortexValue]] = []
        prev_k_bytes: bytes | None = None

        for _ in range(pair_count):
            k_node, curr = decode(data, curr)
            if not isinstance(k_node, String):
                raise CBENonCanonicalMapError(f"Map key must be String, got {type(k_node)}")

            utf8_k_bytes = k_node.value.encode("utf-8")

            if prev_k_bytes is not None:
                if utf8_k_bytes < prev_k_bytes:
                    raise CBENonCanonicalMapError(
                        f"Unsorted map key encountered: {k_node.value!r}"
                    )
                elif utf8_k_bytes == prev_k_bytes:
                    raise CBEDuplicateKeyError(
                        f"Duplicate map key encountered: {k_node.value!r}"
                    )

            v_node, curr = decode(data, curr)
            pairs.append((k_node, v_node))
            prev_k_bytes = utf8_k_bytes

        return Map(pairs), curr

    else:
        raise CBEUnknownTagError(f"Unknown CBE tag byte: {tag!r}")
