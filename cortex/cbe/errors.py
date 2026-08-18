"""
Cortex Canonical Byte Encoding (CBE) Standard Error Taxonomy
"""

from cortex.exceptions import CortexError

CBE_INVALID_UTF8 = "CBE_INVALID_UTF8"
CBE_NON_NFC = "CBE_NON_NFC"
CBE_DUPLICATE_KEY_ERROR = "CBE_DUPLICATE_KEY_ERROR"
CBE_NON_CANONICAL_MAP = "CBE_NON_CANONICAL_MAP"
CBE_INT_OVERFLOW = "CBE_INT_OVERFLOW"
CBE_FLOAT_NONFINITE = "CBE_FLOAT_NONFINITE"
CBE_INVALID_LENGTH = "CBE_INVALID_LENGTH"
CBE_UNKNOWN_TAG = "CBE_UNKNOWN_TAG"


class CBEError(CortexError):
    """Base exception for all CBE encoding/decoding failures."""

    code: str = "CBE_ERROR"


class CBEInvalidUTF8Error(CBEError):
    """Raised when raw string bytes are not valid UTF-8."""

    code: str = CBE_INVALID_UTF8


class CBENonNFCError(CBEError):
    """Raised when decoded UTF-8 string is not in canonical NFC form."""

    code: str = CBE_NON_NFC


class CBEDuplicateKeyError(CBEError):
    """Raised when duplicate map keys are encountered after NFC normalization."""

    code: str = CBE_DUPLICATE_KEY_ERROR


class CBENonCanonicalMapError(CBEError):
    """Raised when map keys are not strictly sorted in ascending UTF-8 byte order."""

    code: str = CBE_NON_CANONICAL_MAP


class CBEIntOverflowError(CBEError):
    """Raised when an integer exceeds signed 64-bit bounds [-2^63, 2^63 - 1]."""

    code: str = CBE_INT_OVERFLOW


class CBEFloatNonFiniteError(CBEError):
    """Raised when a float is NaN, +Infinity, or -Infinity."""

    code: str = CBE_FLOAT_NONFINITE


class CBEInvalidLengthError(CBEError):
    """Raised when a length or count prefix is malformed (e.g. leading zeros, negative)."""

    code: str = CBE_INVALID_LENGTH


class CBEUnknownTagError(CBEError):
    """Raised when an unrecognised type tag is encountered during decoding."""

    code: str = CBE_UNKNOWN_TAG
