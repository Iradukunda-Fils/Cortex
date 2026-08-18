"""
Cortex Layer 2 Transport Framing & Streaming Module
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Final

from cortex.cbe.errors import CBEError

# Layer 2 Protocol Constants
MAGIC_BYTES: Final[bytes] = b"CF"  # 0x43 0x46
HEADER_SIZE: Final[int] = 11
MAX_FRAME_SIZE: Final[int] = 16_777_216  # 16 MiB
MAX_SEQUENCE: Final[int] = 4_294_967_295  # UINT32_MAX


class FrameType(IntEnum):
    """Cortex Layer 2 Frame Type Enums."""

    DATA = 0x01
    PING = 0x02
    PONG = 0x03
    END = 0x04
    ERROR = 0xFF


# Streaming Exception Taxonomy
class CBEFrameError(CBEError):
    """Base exception for Layer 2 framing errors."""

    code: str = "CBE_FRAME_ERROR"


class CBEMagicMismatchError(CBEFrameError):
    """Raised when header magic bytes do not equal b'CF'."""

    code: str = "CBE_FRAME_MAGIC_MISMATCH"


class CBEUnknownFrameTypeError(CBEFrameError):
    """Raised when an unrecognized frame type byte is encountered."""

    code: str = "CBE_FRAME_UNKNOWN_TYPE"


class CBEFrameTooLargeError(CBEFrameError):
    """Raised when payload length prefix exceeds 16 MiB limit."""

    code: str = "CBE_FRAME_TOO_LARGE"


class CBESequenceGapError(CBEFrameError):
    """Raised when frame sequence number does not match expected sequence."""

    code: str = "CBE_FRAME_SEQUENCE_GAP"


class CBESequenceOverflowError(CBEFrameError):
    """Raised when sequence counter exceeds UINT32_MAX."""

    code: str = "CBE_FRAME_SEQUENCE_OVERFLOW"


class CBETruncatedHeaderError(CBEFrameError):
    """Raised when stream ends before reading complete 11-byte header."""

    code: str = "CBE_FRAME_TRUNCATED_HEADER"


class CBETruncatedPayloadError(CBEFrameError):
    """Raised when stream ends before reading N payload bytes."""

    code: str = "CBE_FRAME_TRUNCATED_PAYLOAD"


class CBEInvalidControlPayloadError(CBEFrameError):
    """Raised when control frame payload length violates rules (N!=0 or N!=4 for ERROR)."""

    code: str = "CBE_FRAME_INVALID_CONTROL_PAYLOAD"


class CBEDataEmptyError(CBEFrameError):
    """Raised when a DATA frame is sent with N=0 payload."""

    code: str = "CBE_FRAME_DATA_EMPTY"


@dataclass(frozen=True)
class CortexFrame:
    """Represents a Layer 2 Transport Frame."""

    frame_type: FrameType
    sequence: int
    payload: bytes = b""

    def __post_init__(self) -> None:
        if not (0 <= self.sequence <= MAX_SEQUENCE):
            raise CBESequenceOverflowError(f"Sequence {self.sequence} out of uint32 bounds")

        if len(self.payload) > MAX_FRAME_SIZE:
            raise CBEFrameTooLargeError(f"Payload length {len(self.payload)} > {MAX_FRAME_SIZE}")

        # Control payload validations
        if self.frame_type in (FrameType.PING, FrameType.PONG, FrameType.END):
            if len(self.payload) != 0:
                raise CBEInvalidControlPayloadError(
                    f"Frame {self.frame_type.name} must have 0-byte payload, got {len(self.payload)}"
                )
        elif self.frame_type == FrameType.ERROR:
            if len(self.payload) != 4:
                raise CBEInvalidControlPayloadError(f"ERROR frame must have 4-byte payload, got {len(self.payload)}")
        elif self.frame_type == FrameType.DATA:
            if len(self.payload) == 0:
                raise CBEDataEmptyError("DATA frame cannot have empty payload")


def encode_frame(frame: CortexFrame) -> bytes:
    """Encodes a CortexFrame into raw 11-byte header + N payload bytes."""
    header = MAGIC_BYTES + bytes([frame.frame_type.value]) + struct.pack(">II", frame.sequence, len(frame.payload))
    return header + frame.payload


def decode_frame(data: bytes, expected_sequence: int | None = None) -> CortexFrame:
    """Decodes a single CortexFrame from bytes."""
    if len(data) < HEADER_SIZE:
        raise CBETruncatedHeaderError(f"Data length {len(data)} < header size {HEADER_SIZE}")

    magic = data[:2]
    if magic != MAGIC_BYTES:
        raise CBEMagicMismatchError(f"Invalid magic {magic!r}, expected {MAGIC_BYTES!r}")

    type_byte = data[2]
    try:
        frame_type = FrameType(type_byte)
    except ValueError:
        raise CBEUnknownFrameTypeError(f"Unknown frame type byte: {type_byte:#04x}")

    sequence, payload_len = struct.unpack(">II", data[3:11])

    if expected_sequence is not None and sequence != expected_sequence:
        raise CBESequenceGapError(f"Expected sequence {expected_sequence}, got {sequence}")

    if payload_len > MAX_FRAME_SIZE:
        raise CBEFrameTooLargeError(f"Payload length {payload_len} > {MAX_FRAME_SIZE}")

    payload = data[HEADER_SIZE : HEADER_SIZE + payload_len]
    if len(payload) < payload_len:
        raise CBETruncatedPayloadError(f"Expected payload length {payload_len}, got {len(payload)}")

    return CortexFrame(frame_type=frame_type, sequence=sequence, payload=payload)


class StreamEncoder:
    """Stateful encoder for Layer 2 streaming sessions."""

    def __init__(self, initial_sequence: int = 0) -> None:
        if not (0 <= initial_sequence <= MAX_SEQUENCE):
            raise CBESequenceOverflowError(f"Initial sequence {initial_sequence} invalid")
        self._next_sequence = initial_sequence

    @property
    def next_sequence(self) -> int:
        return self._next_sequence

    def encode(self, frame_type: FrameType, payload: bytes = b"") -> bytes:
        if self._next_sequence > MAX_SEQUENCE:
            raise CBESequenceOverflowError("Sequence counter exceeded UINT32_MAX")

        frame = CortexFrame(frame_type=frame_type, sequence=self._next_sequence, payload=payload)
        encoded = encode_frame(frame)

        if self._next_sequence == MAX_SEQUENCE:
            self._next_sequence = MAX_SEQUENCE + 1  # Will trigger overflow on next frame
        else:
            self._next_sequence += 1

        return encoded


class StreamDecoder:
    """Stateful decoder for Layer 2 streaming sessions."""

    def __init__(self, expected_sequence: int = 0) -> None:
        self._expected_sequence = expected_sequence
        self._buffer = bytearray()

    @property
    def expected_sequence(self) -> int:
        return self._expected_sequence

    def feed(self, chunk: bytes) -> list[CortexFrame]:
        """Feeds chunk of bytes and returns decoded CortexFrames."""
        self._buffer.extend(chunk)
        frames: list[CortexFrame] = []

        while len(self._buffer) >= HEADER_SIZE:
            magic = self._buffer[:2]
            if magic != MAGIC_BYTES:
                raise CBEMagicMismatchError(f"Invalid magic bytes: {magic!r}")

            type_byte = self._buffer[2]
            try:
                _ = FrameType(type_byte)
            except ValueError:
                raise CBEUnknownFrameTypeError(f"Unknown frame type: {type_byte:#04x}")

            sequence, payload_len = struct.unpack(">II", self._buffer[3:11])

            if payload_len > MAX_FRAME_SIZE:
                raise CBEFrameTooLargeError(f"Payload length {payload_len} > {MAX_FRAME_SIZE}")

            total_frame_len = HEADER_SIZE + payload_len
            if len(self._buffer) < total_frame_len:
                break  # Await more payload bytes

            if sequence != self._expected_sequence:
                raise CBESequenceGapError(f"Expected sequence {self._expected_sequence}, got {sequence}")

            frame_data = bytes(self._buffer[:total_frame_len])
            del self._buffer[:total_frame_len]

            frame = decode_frame(frame_data, expected_sequence=self._expected_sequence)
            frames.append(frame)

            if self._expected_sequence == MAX_SEQUENCE:
                self._expected_sequence = MAX_SEQUENCE + 1
            else:
                self._expected_sequence += 1

        return frames
