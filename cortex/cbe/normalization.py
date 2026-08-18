"""
Cortex Canonical Byte Encoding (CBE) Normalization and Invariant Validation
"""

import math
import unicodedata

from cortex.cbe.errors import (
    CBEFloatNonFiniteError,
    CBEIntOverflowError,
)

INT64_MIN = -9223372036854775808
INT64_MAX = 9223372036854775807


def normalize_nfc_string(s: str) -> str:
    """Normalize string to Unicode NFC form."""
    return unicodedata.normalize("NFC", s)


def is_nfc_canonical(s: str) -> bool:
    """Return True if string is strictly in Unicode NFC form."""
    return unicodedata.normalize("NFC", s) == s


def normalize_float(val: float) -> float:
    """
    Validate float finite bounds and normalize -0.0 to +0.0.
    Raises CBEFloatNonFiniteError if NaN or Infinity.
    """
    if math.isnan(val) or math.isinf(val):
        raise CBEFloatNonFiniteError(f"Non-finite float value forbidden: {val}")
    if val == 0.0:
        return 0.0
    return val


def check_int64_bounds(val: int) -> int:
    """
    Validate integer signed 64-bit bounds [-2^63, 2^63 - 1].
    Raises CBEIntOverflowError if out of bounds.
    """
    if val < INT64_MIN or val > INT64_MAX:
        raise CBEIntOverflowError(f"Integer {val} exceeds signed 64-bit bounds [{INT64_MIN}, {INT64_MAX}]")
    return val
