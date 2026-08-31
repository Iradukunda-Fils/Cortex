"""
Cortex Phase 6.1: Durable State Engine & Write-Ahead Logging (WAL)
Normative Baseline: v1.5.1-FINAL-FROZEN

Provides crash-safe disk persistence for    s, worker assignments,
idempotency tracking, and quarantine records via an append-only WAL with
CRC32 integrity validation and atomic sync semantics.
"""

from __future__ import annotations

import fcntl
import json
import os
import struct
import zlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class WALRecordType(Enum):
    """Normative record types for the Cortex Write-Ahead Log."""

    REGISTER_WORKER = "REGISTER_WORKER"
    ASSIGN_EXECUTION = "ASSIGN_EXECUTION"
    RELEASE_EXECUTION = "RELEASE_EXECUTION"
    EVICT_WORKER = "EVICT_WORKER"
    QUARANTINE_INVOCATION = "QUARANTINE_INVOCATION"
    LEADER_EPOCH_ADVANCE = "LEADER_EPOCH_ADVANCE"


class WALCorruptRecordError(Exception):
    """Raised when CRC32 checksum or binary frame length validation fails during replay."""

    pass


@dataclass(frozen=True)
class WALRecord:
    seq_no: int
    record_type: WALRecordType
    timestamp_ms: int
    data: Dict[str, Any]

    def serialize(self) -> bytes:
        """
        Binary Format:
        [Magic Bytes 4b][Length 4b][SeqNo 8b][CRC32 4b][Payload JSON bytes...]
        Magic Bytes: b'CWAL'
        """
        payload_dict = {
            "seq_no": self.seq_no,
            "record_type": self.record_type.value,
            "timestamp_ms": self.timestamp_ms,
            "data": self.data,
        }
        payload_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
        crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
        header = struct.pack(">4sIIQ", b"CWAL", len(payload_bytes), crc, self.seq_no)
        return header + payload_bytes

    @classmethod
    def deserialize(cls, header_bytes: bytes, payload_bytes: bytes) -> WALRecord:
        magic, payload_len, expected_crc, seq_no = struct.unpack(">4sIIQ", header_bytes)
        if magic != b"CWAL":
            raise WALCorruptRecordError(f"Invalid WAL magic header: {magic!r}")

        if len(payload_bytes) != payload_len:
            raise WALCorruptRecordError(
                f"Payload length mismatch: expected {payload_len}, got {len(payload_bytes)}"
            )

        actual_crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise WALCorruptRecordError(
                f"CRC32 mismatch: calculated {actual_crc:#010x}, expected {expected_crc:#010x}"
            )

        payload_dict = json.loads(payload_bytes.decode("utf-8"))
        return cls(
            seq_no=payload_dict["seq_no"],
            record_type=WALRecordType(payload_dict["record_type"]),
            timestamp_ms=payload_dict["timestamp_ms"],
            data=payload_dict["data"],
        )


class DurableStateStore:
    """
    Crash-Safe Append-Only WAL Engine for Cortex Persistent Authority.
    Guarantees atomic fsync persistence and crash recovery for execution state.
    """

    HEADER_SIZE = 20  # 4s (4) + I (4) + I (4) + Q (8)

    def __init__(self, wal_dir_path: str) -> None:
        self.wal_dir = Path(wal_dir_path)
        self.wal_dir.mkdir(parents=True, exist_ok=True)
        self.wal_file_path = self.wal_dir / "authority.wal"
        self._next_seq_no = 1
        self._file_handle: Optional[Any] = None
        self._open_file()

    def _open_file(self) -> None:
        if self._file_handle is None or self._file_handle.closed:
            self._file_handle = open(self.wal_file_path, "a+b")

    def append_record(self, record_type: WALRecordType, timestamp_ms: int, data: Dict[str, Any]) -> WALRecord:
        """Appends a new record to the WAL with atomic fsync durability."""
        record = WALRecord(
            seq_no=self._next_seq_no,
            record_type=record_type,
            timestamp_ms=timestamp_ms,
            data=data,
        )
        serialized = record.serialize()
        self._open_file()
        if self._file_handle is None:
            raise RuntimeError("WAL file handle failed to open.")
        fd = self._file_handle.fileno()
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            self._file_handle.write(serialized)
            self._file_handle.flush()
            os.fsync(fd)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)

        self._next_seq_no += 1
        return record

    def replay_all_records(self) -> List[WALRecord]:
        """Reads and verifies all records from disk. Stops cleanly at the last valid record on corruption or EOF."""
        if not self.wal_file_path.exists():
            return []

        records: List[WALRecord] = []
        expected_seq_no = 1
        with open(self.wal_file_path, "rb") as f:
            while True:
                header_bytes = f.read(self.HEADER_SIZE)
                if not header_bytes:
                    break  # End of file reached
                if len(header_bytes) < self.HEADER_SIZE:
                    # Truncated header at end of file (crash during write)
                    break

                try:
                    magic, payload_len, expected_crc, seq_no = struct.unpack(">4sIIQ", header_bytes)
                    if magic != b"CWAL":
                        # Invalid magic header / corruption vector -> stop replay at last valid record
                        break

                    payload_bytes = f.read(payload_len)
                    if len(payload_bytes) < payload_len:
                        # Truncated write during payload -> stop replay at last valid record
                        break

                    record = WALRecord.deserialize(header_bytes, payload_bytes)
                    # Enforce strict sequence monotonicity (seq_no == expected_seq_no)
                    if record.seq_no != expected_seq_no:
                        # Sequence gap, duplicate, or rollback -> stop replay at last valid record
                        break

                    records.append(record)
                    expected_seq_no += 1
                except (WALCorruptRecordError, struct.error, ValueError):
                    # Corruption detected -> halt replay safely at last valid record
                    break

        self._next_seq_no = expected_seq_no
        return records

    def close(self) -> None:
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.flush()
            os.fsync(self._file_handle.fileno())
            self._file_handle.close()
            self._file_handle = None
