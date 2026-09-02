"""
Cortex External Effect Write-Ahead Log (WAL) Engine — Sub-Gate B.3

Provides crash-safe binary disk persistence for external effect lifecycle transitions:
    EFFECT_ADMITTED   -> Pre-actuation intent persisted with fsync
    EFFECT_ACTUATING  -> External execution registered with fsync
    EFFECT_COMMITTED  -> Final outcome (including evidence & ObjectRef) persisted
    EFFECT_QUARANTINED -> Indeterminate effect quarantined following Gateway crash

Binary Format (CWAL):
    [Magic 4b: b"CWAL"][Length 4b][CRC32 4b][SeqNo 8b][Payload JSON bytes...]
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
from typing import Any, List, Optional

from cortex.tools.kernel.adapter_contract import (
    EvidencePayload,
    ExecutionStatus,
)
from cortex.tools.kernel.effect_gateway import EffectOutcome


class EffectWALState(str, Enum):
    ADMITTED = "EFFECT_ADMITTED"
    ACTUATING = "EFFECT_ACTUATING"
    COMMITTED = "EFFECT_COMMITTED"
    QUARANTINED = "EFFECT_QUARANTINED"


class WALCorruptRecordError(Exception):
    """Raised when CRC32 checksum or binary frame validation fails during replay."""


@dataclass(frozen=True)
class EffectWALRecord:
    seq_no: int
    invocation_id: str
    effect_key: str
    lease_epoch: int
    authority_epoch: int
    state: EffectWALState
    payload: bytes
    outcome: Optional[EffectOutcome] = None
    error_message: Optional[str] = None

    def serialize(self) -> bytes:
        """
        Binary Format:
        [Magic Bytes 4b: b'CWAL'][Length 4b][CRC32 4b][SeqNo 8b][Payload JSON bytes...]
        """
        outcome_dict = None
        if self.outcome is not None:
            evidence_dict = None
            if self.outcome.evidence is not None:
                evidence_dict = {
                    "data_hex": self.outcome.evidence.data.hex(),
                    "is_reference": self.outcome.evidence.is_reference,
                }
            outcome_dict = {
                "invocation_id": self.outcome.invocation_id,
                "execution_attempt_id": self.outcome.execution_attempt_id,
                "status": self.outcome.status.value,
                "evidence": evidence_dict,
                "error_message": self.outcome.error_message,
            }

        payload_dict = {
            "seq_no": self.seq_no,
            "invocation_id": self.invocation_id,
            "effect_key": self.effect_key,
            "lease_epoch": self.lease_epoch,
            "authority_epoch": self.authority_epoch,
            "state": self.state.value,
            "payload_hex": self.payload.hex(),
            "outcome": outcome_dict,
            "error_message": self.error_message,
        }

        payload_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
        crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
        header = struct.pack(">4sIIQ", b"CWAL", len(payload_bytes), crc, self.seq_no)
        return header + payload_bytes

    @classmethod
    def deserialize(cls, header_bytes: bytes, payload_bytes: bytes) -> EffectWALRecord:
        magic, payload_len, expected_crc, seq_no = struct.unpack(">4sIIQ", header_bytes)
        if magic != b"CWAL":
            raise WALCorruptRecordError(f"Invalid WAL magic header: {magic!r}")

        if len(payload_bytes) != payload_len:
            raise WALCorruptRecordError(f"Payload length mismatch: expected {payload_len}, got {len(payload_bytes)}")

        actual_crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise WALCorruptRecordError(f"CRC32 mismatch: calculated {actual_crc:#010x}, expected {expected_crc:#010x}")

        p = json.loads(payload_bytes.decode("utf-8"))

        outcome = None
        if p.get("outcome") is not None:
            o_dict = p["outcome"]
            ev = None
            if o_dict.get("evidence") is not None:
                ev_dict = o_dict["evidence"]
                ev = EvidencePayload(
                    data=bytes.fromhex(ev_dict["data_hex"]),
                    is_reference=ev_dict["is_reference"],
                )
            outcome = EffectOutcome(
                invocation_id=o_dict["invocation_id"],
                execution_attempt_id=o_dict["execution_attempt_id"],
                status=ExecutionStatus(o_dict["status"]),
                evidence=ev,
                error_message=o_dict.get("error_message"),
            )

        return cls(
            seq_no=p["seq_no"],
            invocation_id=p["invocation_id"],
            effect_key=p["effect_key"],
            lease_epoch=p["lease_epoch"],
            authority_epoch=p["authority_epoch"],
            state=EffectWALState(p["state"]),
            payload=bytes.fromhex(p["payload_hex"]),
            outcome=outcome,
            error_message=p.get("error_message"),
        )


class EffectWALEngine:
    """
    Crash-Safe Binary WAL Engine for External Effect Lifecycles.
    Enforces CRC32 binary frames, fcntl flock, and physical os.fsync on append.
    """

    HEADER_SIZE = 20  # 4s (4) + I (4) + I (4) + Q (8)

    def __init__(self, wal_dir_path: str) -> None:
        self.wal_dir = Path(wal_dir_path)
        self.wal_dir.mkdir(parents=True, exist_ok=True)
        self.wal_file_path = self.wal_dir / "effect_lifecycle.wal"
        self._next_seq_no = 1
        self._file_handle: Optional[Any] = None
        self._open_file()

    def _open_file(self) -> None:
        if self._file_handle is None or self._file_handle.closed:
            self._file_handle = open(self.wal_file_path, "a+b")

    def append_record(
        self,
        invocation_id: str,
        effect_key: str,
        lease_epoch: int,
        authority_epoch: int,
        state: EffectWALState,
        payload: bytes,
        outcome: Optional[EffectOutcome] = None,
        error_message: Optional[str] = None,
    ) -> EffectWALRecord:
        """Appends a record with atomic fcntl lock and physical os.fsync durability."""
        self._open_file()
        if self._file_handle is None:
            raise RuntimeError("WAL file handle failed to open.")
        fd = self._file_handle.fileno()
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            record = EffectWALRecord(
                seq_no=self._next_seq_no,
                invocation_id=invocation_id,
                effect_key=effect_key,
                lease_epoch=lease_epoch,
                authority_epoch=authority_epoch,
                state=state,
                payload=payload,
                outcome=outcome,
                error_message=error_message,
            )
            serialized = record.serialize()
            self._file_handle.seek(0, os.SEEK_END)
            self._file_handle.write(serialized)
            self._file_handle.flush()
            os.fsync(fd)  # Strict fsync barrier before return
            self._next_seq_no += 1
            return record
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)

    def replay_all_records(self) -> List[EffectWALRecord]:
        """
        Reads and verifies all CRC32 binary records from disk.
        Stops cleanly at the last valid record on crash-tail truncation or EOF.
        Raises WALCorruptRecordError if mid-file corruption is detected.
        """
        if not self.wal_file_path.exists():
            return []

        records: List[EffectWALRecord] = []
        with open(self.wal_file_path, "rb") as f:
            while True:
                header_bytes = f.read(self.HEADER_SIZE)
                if not header_bytes:
                    break

                if len(header_bytes) < self.HEADER_SIZE:
                    # Incomplete tail frame written before crash -> clean stop
                    break

                magic, payload_len, expected_crc, seq_no = struct.unpack(">4sIIQ", header_bytes)
                payload_bytes = f.read(payload_len)

                if len(payload_bytes) < payload_len:
                    # Incomplete payload written before crash -> clean stop
                    break

                try:
                    record = EffectWALRecord.deserialize(header_bytes, payload_bytes)
                    records.append(record)
                    self._next_seq_no = max(self._next_seq_no, record.seq_no + 1)
                except WALCorruptRecordError:
                    # Check if EOF reached after read
                    rest = f.read(1)
                    if not rest:
                        # Tail corruption from partial write during crash
                        break
                    raise  # Mid-file corruption

        return records

    def close(self) -> None:
        if self._file_handle is not None and not self._file_handle.closed:
            self._file_handle.close()
            self._file_handle = None

    def __enter__(self) -> EffectWALEngine:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
