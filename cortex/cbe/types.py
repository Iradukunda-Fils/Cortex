"""
CortexValue AST Model for Language-Neutral Semantic Value Representation
"""

import math
import unicodedata
from abc import ABC, abstractmethod
from typing import Any, Sequence

from cortex.cbe.errors import (
    CBEDuplicateKeyError,
    CBEFloatNonFiniteError,
    CBEIntOverflowError,
)

INT64_MIN = -9223372036854775808
INT64_MAX = 9223372036854775807


class CortexValue(ABC):
    """Abstract base class for all CortexValue AST nodes."""

    @abstractmethod
    def to_python(self) -> Any:
        """Convert AST node to standard Python primitive object."""
        pass

    @classmethod
    def from_python(cls, val: Any) -> "CortexValue":
        """Convert a standard Python primitive object into a CortexValue AST tree."""
        if val is None:
            return Null()
        elif isinstance(val, bool):
            return Bool(val)
        elif isinstance(val, int):
            return Int(val)
        elif isinstance(val, float):
            return Float(val)
        elif isinstance(val, str):
            return String(val)
        elif isinstance(val, (bytes, bytearray)):
            return Bytes(bytes(val))
        elif isinstance(val, (list, tuple)):
            return List([cls.from_python(item) for item in val])
        elif isinstance(val, dict):
            pairs = []
            for k, v in val.items():
                if not isinstance(k, str):
                    raise TypeError(f"Map key must be str, got {type(k)}")
                pairs.append((String(k), cls.from_python(v)))
            return Map(pairs)
        elif isinstance(val, CortexValue):
            return val
        else:
            raise TypeError(f"Cannot convert type {type(val)} to CortexValue")


class Null(CortexValue):
    """CortexValue Null representation."""

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Null)

    def __hash__(self) -> int:
        return hash("Null")

    def __repr__(self) -> str:
        return "Null()"

    def to_python(self) -> None:
        return None


class Bool(CortexValue):
    """CortexValue Bool representation."""

    def __init__(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError(f"Expected bool, got {type(value)}")
        self._value = value

    @property
    def value(self) -> bool:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Bool) and self._value == other._value

    def __hash__(self) -> int:
        return hash(("Bool", self._value))

    def __repr__(self) -> str:
        return f"Bool({self._value})"

    def to_python(self) -> bool:
        return self._value


class Int(CortexValue):
    """CortexValue 64-bit Signed Integer representation."""

    def __init__(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"Expected int, got {type(value)}")
        if value < INT64_MIN or value > INT64_MAX:
            raise CBEIntOverflowError(
                f"Integer {value} exceeds signed 64-bit bounds [{INT64_MIN}, {INT64_MAX}]"
            )
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Int) and self._value == other._value

    def __hash__(self) -> int:
        return hash(("Int", self._value))

    def __repr__(self) -> str:
        return f"Int({self._value})"

    def to_python(self) -> int:
        return self._value


class Float(CortexValue):
    """CortexValue IEEE 754 64-bit Double Precision Float representation."""

    def __init__(self, value: float) -> None:
        if not isinstance(value, float) or isinstance(value, bool):
            raise TypeError(f"Expected float, got {type(value)}")
        if math.isnan(value) or math.isinf(value):
            raise CBEFloatNonFiniteError(f"Non-finite float value forbidden: {value}")
        # Normalize -0.0 to +0.0
        if value == 0.0:
            value = 0.0
        self._value = value

    @property
    def value(self) -> float:
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Float):
            return self._value == other._value
        return False

    def __hash__(self) -> int:
        return hash(("Float", self._value))

    def __repr__(self) -> str:
        return f"Float({self._value})"

    def to_python(self) -> float:
        return self._value


class String(CortexValue):
    """CortexValue Unicode String representation."""

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value)}")
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, String) and self._value == other._value

    def __hash__(self) -> int:
        return hash(("String", self._value))

    def __repr__(self) -> str:
        return f"String({self._value!r})"

    def to_python(self) -> str:
        return self._value


class Bytes(CortexValue):
    """CortexValue Raw Bytes representation."""

    def __init__(self, value: bytes | bytearray) -> None:
        if isinstance(value, bytearray):
            self._value = bytes(value)
        elif isinstance(value, bytes):
            self._value = value
        else:
            raise TypeError(f"Expected bytes, got {type(value)}")

    @property
    def value(self) -> bytes:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Bytes) and self._value == other._value

    def __hash__(self) -> int:
        return hash(("Bytes", self._value))

    def __repr__(self) -> str:
        return f"Bytes({self._value!r})"

    def to_python(self) -> bytes:
        return self._value


class List(CortexValue):
    """CortexValue List container representation."""

    def __init__(self, elements: Sequence[CortexValue]) -> None:
        elems = []
        for elem in elements:
            if not isinstance(elem, CortexValue):
                elem = CortexValue.from_python(elem)
            elems.append(elem)
        self._elements: tuple[CortexValue, ...] = tuple(elems)

    @property
    def elements(self) -> tuple[CortexValue, ...]:
        return self._elements

    def __eq__(self, other: object) -> bool:
        return isinstance(other, List) and self._elements == other._elements

    def __hash__(self) -> int:
        return hash(("List", self._elements))

    def __repr__(self) -> str:
        return f"List({list(self._elements)!r})"

    def to_python(self) -> list[Any]:
        return [elem.to_python() for elem in self._elements]


class Map(CortexValue):
    """CortexValue Key-Value Map container representation."""

    def __init__(self, pairs: Sequence[tuple[String, CortexValue]]) -> None:
        validated_pairs: list[tuple[String, CortexValue]] = []
        seen_utf8_keys: set[bytes] = set()

        for k, v in pairs:
            if not isinstance(k, String):
                if isinstance(k, str):
                    k = String(k)
                else:
                    raise TypeError(f"Map key must be String, got {type(k)}")
            if not isinstance(v, CortexValue):
                v = CortexValue.from_python(v)

            # Check key collision under NFC -> UTF-8 bytes
            nfc_k_bytes = unicodedata.normalize("NFC", k.value).encode("utf-8")
            if nfc_k_bytes in seen_utf8_keys:
                raise CBEDuplicateKeyError(
                    f"Duplicate map key after NFC normalization: {k.value!r}"
                )
            seen_utf8_keys.add(nfc_k_bytes)
            validated_pairs.append((k, v))

        self._pairs: tuple[tuple[String, CortexValue], ...] = tuple(validated_pairs)

    @property
    def pairs(self) -> tuple[tuple[String, CortexValue], ...]:
        return self._pairs

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Map) and self._pairs == other._pairs

    def __hash__(self) -> int:
        return hash(("Map", self._pairs))

    def __repr__(self) -> str:
        return f"Map({list(self._pairs)!r})"

    def to_python(self) -> dict[str, Any]:
        return {k.to_python(): v.to_python() for k, v in self._pairs}
