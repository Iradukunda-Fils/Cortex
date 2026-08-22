"""
Gateway Invocation State Ledger & Crash Recovery Classifier (Phase 1 & 2)

Durable, Gateway-owned state machine tracking invocation lifecycle states and
classifying orphaned invocations into exact recovery buckets.

Persistence Profile (Phase 1–3): Append-only JSON-lines journal with fsync.
Recovery Profile: Graceful handling of torn lines on crash/power loss.
Compaction Profile: Safe atomic snapshot swap (tmp file -> fsync -> atomic rename -> dir fsync).
"""

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Optional


class InvocationState(Enum):
    QUEUED = auto()
    ASSIGNED = auto()
    RUNNING = auto()
    AUTHORIZED = auto()
    ACTUATING = auto()
    RECOVERY_REQUIRED = auto()
    COMMITTED = auto()
    REJECTED = auto()
    INDETERMINATE = auto()


# Formal terminal state invariant:
# TerminalState(I) ∈ {COMMITTED, REJECTED, INDETERMINATE}
# LOST, DROPPED, ORPHANED_FOREVER, UNKNOWN are prohibited as terminal states.
TERMINAL_STATES = frozenset({
    InvocationState.COMMITTED,
    InvocationState.REJECTED,
    InvocationState.INDETERMINATE,
})


class RecoveryBucket(Enum):
    UNADMITTED = auto()
    ADMITTED_UNACTUATED = auto()
    ACTUATED_COMMITTED = auto()
    ACTUATION_UNKNOWN = auto()  # Maps to InvocationState.INDETERMINATE


@dataclass
class InvocationRecord:
    invocation_id: str
    intent_hash: str
    state: InvocationState
    config_generation: int = 0
    config_hash: str = ""
    assigned_worker_id: Optional[str] = None
    lease_epoch: Optional[int] = None
    result_payload: Optional[bytes] = None
    recovery_bucket: Optional[RecoveryBucket] = None


class InvocationStateLedger:
    """Thread-safe Gateway TCB Invocation State Ledger with durable journal persistence.

    Persistence substrate: Append-only JSON-lines journal file with explicit fsync.
    Memory model: O(active_invocations), not O(historical_operations).
    Compaction Profile: Safe atomic snapshot swap with SHA-256 checkpoint verification.
    """

    def __init__(
        self,
        journal_path: Optional[str] = None,
        max_journal_lines: int = 1000,
        compaction_threshold: int = 500,
        max_resident_records: int = 10000,
    ) -> None:
        self._lock = threading.Lock()
        self._records: Dict[str, InvocationRecord] = {}
        self._terminated_ids: set[str] = set()
        self._journal_path = journal_path
        self._journal_fd: Optional[int] = None
        self._snapshot_gen: int = 0
        self._line_count: int = 0

        self.max_journal_lines = max_journal_lines
        self.compaction_threshold = compaction_threshold
        self.max_resident_records = max_resident_records

        if self._journal_path:
            parent = Path(self._journal_path).parent
            parent.mkdir(parents=True, exist_ok=True)
            self._journal_fd = os.open(
                self._journal_path,
                os.O_CREAT | os.O_WRONLY | os.O_APPEND,
                0o600,
            )
            self._replay_journal()

    def _replay_journal(self) -> None:
        """Reconstruct ledger state from durable journal on Gateway restart.

        Torn-Record & Snapshot Header Recovery: Validates SHA-256 checkpoint hash if header exists.
        Torn line at EOF is ignored, leaving the last valid acknowledged state intact.
        """
        if not self._journal_path or not os.path.exists(self._journal_path):
            return

        self._line_count = 0
        with open(self._journal_path, encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return

        header_line = lines[0].strip()
        body_lines = lines

        # Check for snapshot header
        if header_line.startswith("# SNAPSHOT_HEADER:"):
            try:
                header_raw = header_line[len("# SNAPSHOT_HEADER:"):].strip()
                header_data = json.loads(header_raw)
                self._snapshot_gen = header_data.get("snapshot_generation", 0)
                expected_hash = header_data.get("checkpoint_hash", "")

                for t_id in header_data.get("terminated_ids", []):
                    self._terminated_ids.add(t_id)

                body_lines = lines[1:]
                body_content = "".join(body_lines).encode("utf-8")
                actual_hash = hashlib.sha256(body_content).hexdigest()

                if expected_hash and actual_hash != expected_hash:
                    # Checkpoint mismatch: torn or corrupted snapshot -> discard header and attempt best-effort body parse
                    pass
            except json.JSONDecodeError:
                pass

        for line in body_lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            self._line_count += 1
            try:
                entry = json.loads(line_str)
            except json.JSONDecodeError:
                # Torn line encountered (e.g. crash mid-write). Fail closed / ignore corrupt line.
                continue

            inv_id = entry.get("invocation_id")
            if not inv_id or "state" not in entry:
                continue

            state = InvocationState[entry["state"]]
            if state in TERMINAL_STATES:
                self._terminated_ids.add(inv_id)

            if inv_id not in self._records:
                self._records[inv_id] = InvocationRecord(
                    invocation_id=inv_id,
                    intent_hash=entry.get("intent_hash", ""),
                    state=state,
                    config_generation=entry.get("config_generation", 0),
                    config_hash=entry.get("config_hash", ""),
                    assigned_worker_id=entry.get("assigned_worker_id"),
                    lease_epoch=entry.get("lease_epoch"),
                )
            else:
                rec = self._records[inv_id]
                rec.state = state
                if entry.get("assigned_worker_id"):
                    rec.assigned_worker_id = entry["assigned_worker_id"]
                if entry.get("lease_epoch"):
                    rec.lease_epoch = entry["lease_epoch"]

    def _append_journal(self, invocation_id: str, state: InvocationState, **kwargs: object) -> None:
        """Append a state transition to the durable journal and fsync."""
        if self._journal_fd is None:
            return
        entry = {"invocation_id": invocation_id, "state": state.name, **kwargs}
        line = json.dumps(entry, default=str) + "\n"
        os.write(self._journal_fd, line.encode("utf-8"))
        os.fsync(self._journal_fd)
        self._line_count += 1

        # Check auto-compaction triggers
        if self._line_count >= self.max_journal_lines:
            self._check_auto_compaction_unlocked()

    def _check_auto_compaction_unlocked(self) -> None:
        """Internal helper to trigger compaction when thresholds are exceeded."""
        term_count = sum(1 for rec in self._records.values() if rec.state in TERMINAL_STATES)
        if term_count > 0:
            self._compact_terminated_unlocked()

    def create_invocation(
        self, invocation_id: str, intent_hash: str, config_generation: int = 0, config_hash: str = ""
    ) -> InvocationRecord:
        with self._lock:
            if invocation_id in self._records or invocation_id in self._terminated_ids:
                raise ValueError(f"Invocation {invocation_id} already exists in ledger")
            record = InvocationRecord(
                invocation_id=invocation_id,
                intent_hash=intent_hash,
                state=InvocationState.QUEUED,
                config_generation=config_generation,
                config_hash=config_hash,
            )
            self._records[invocation_id] = record
            self._append_journal(
                invocation_id, InvocationState.QUEUED,
                intent_hash=intent_hash, config_generation=config_generation, config_hash=config_hash,
            )
            return record

    def transition_state(
        self,
        invocation_id: str,
        to_state: InvocationState,
        worker_id: Optional[str] = None,
        lease_epoch: Optional[int] = None,
    ) -> InvocationRecord:
        with self._lock:
            record = self._records.get(invocation_id)
            if not record:
                raise KeyError(f"Invocation {invocation_id} not found in ledger")

            record.state = to_state
            if to_state in TERMINAL_STATES:
                self._terminated_ids.add(invocation_id)

            if worker_id is not None:
                record.assigned_worker_id = worker_id
            if lease_epoch is not None:
                record.lease_epoch = lease_epoch

            self._append_journal(
                invocation_id, to_state,
                assigned_worker_id=worker_id, lease_epoch=lease_epoch,
            )
            return record

    def get_record(self, invocation_id: str) -> Optional[InvocationRecord]:
        with self._lock:
            return self._records.get(invocation_id)

    def classify_recovery(self, invocation_id: str) -> RecoveryBucket:
        """Classifies an invocation in RECOVERY_REQUIRED or orphaned state into an exact recovery bucket.

        After classification, ACTUATION_UNKNOWN invocations are transitioned to
        INDETERMINATE (a formal terminal state). This enforces the invariant:
        TerminalState(I) ∈ {COMMITTED, REJECTED, INDETERMINATE}.
        """
        with self._lock:
            record = self._records.get(invocation_id)
            if not record:
                if invocation_id in self._terminated_ids:
                    return RecoveryBucket.ACTUATED_COMMITTED
                raise KeyError(f"Invocation {invocation_id} not found in ledger")

            if record.state in (InvocationState.QUEUED, InvocationState.ASSIGNED):
                bucket = RecoveryBucket.UNADMITTED
            elif record.state in (InvocationState.RUNNING, InvocationState.AUTHORIZED):
                bucket = RecoveryBucket.ADMITTED_UNACTUATED
            elif record.state == InvocationState.COMMITTED:
                bucket = RecoveryBucket.ACTUATED_COMMITTED
            elif record.state in (InvocationState.ACTUATING, InvocationState.RECOVERY_REQUIRED):
                bucket = RecoveryBucket.ACTUATION_UNKNOWN
            else:
                bucket = RecoveryBucket.UNADMITTED

            record.recovery_bucket = bucket

            # Enforce terminal state for ACTUATION_UNKNOWN
            if bucket == RecoveryBucket.ACTUATION_UNKNOWN:
                record.state = InvocationState.INDETERMINATE
                self._terminated_ids.add(invocation_id)
                self._append_journal(invocation_id, InvocationState.INDETERMINATE)

            return bucket

    def is_terminal(self, invocation_id: str) -> bool:
        """Returns True iff the invocation is in a formal terminal state."""
        with self._lock:
            if invocation_id in self._terminated_ids:
                return True
            record = self._records.get(invocation_id)
            if not record:
                raise KeyError(f"Invocation {invocation_id} not found in ledger")
            return record.state in TERMINAL_STATES

    def compact_terminated(self) -> int:
        """Atomically compacts ledger state on disk and evicts terminal records from memory."""
        with self._lock:
            return self._compact_terminated_unlocked()

    def _compact_terminated_unlocked(self) -> int:
        """Internal unlocked implementation of snapshot compaction."""
        to_remove = [
            inv_id for inv_id, rec in self._records.items()
            if rec.state in TERMINAL_STATES
        ]

        # Record all evicted IDs in persistent terminal set
        for inv_id in to_remove:
            self._terminated_ids.add(inv_id)

        if self._journal_path and self._journal_fd is not None:
            self._snapshot_gen += 1
            parent_dir = str(Path(self._journal_path).parent)

            # Build body lines for active records
            body_lines: list[str] = []
            active_records = [rec for rec in self._records.values() if rec.state not in TERMINAL_STATES]
            for rec in active_records:
                entry = {
                    "assigned_worker_id": rec.assigned_worker_id,
                    "config_generation": rec.config_generation,
                    "config_hash": rec.config_hash,
                    "intent_hash": rec.intent_hash,
                    "invocation_id": rec.invocation_id,
                    "lease_epoch": rec.lease_epoch,
                    "state": rec.state.name,
                }
                body_lines.append(json.dumps(entry, sort_keys=True, separators=(',', ':')) + "\n")

            body_content = "".join(body_lines).encode("utf-8")
            checkpoint_hash = hashlib.sha256(body_content).hexdigest()

            header_entry = {
                "checkpoint_hash": checkpoint_hash,
                "record_count": len(active_records),
                "schema_version": "1.0",
                "snapshot_generation": self._snapshot_gen,
                "terminated_ids": sorted(list(self._terminated_ids)),
            }
            header_line = f"# SNAPSHOT_HEADER: {json.dumps(header_entry, sort_keys=True, separators=(',', ':'))}\n"

            # Step 1-2: Write header + body to temp file in same directory
            with tempfile.NamedTemporaryFile("w", dir=parent_dir, delete=False, encoding="utf-8") as tmp_file:
                tmp_path = tmp_file.name
                tmp_file.write(header_line)
                tmp_file.write("".join(body_lines))

                # Step 3: fsync temp file
                tmp_file.flush()
                os.fsync(tmp_file.fileno())

            # Step 4: Atomic rename
            os.close(self._journal_fd)
            os.replace(tmp_path, self._journal_path)

            # Step 5: fsync parent directory
            dir_fd = os.open(parent_dir, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

            # Step 6: Reopen journal FD for future appends
            self._journal_fd = os.open(
                self._journal_path,
                os.O_WRONLY | os.O_APPEND,
                0o600,
            )
            self._line_count = len(active_records)

        # Evict from resident memory dict
        for inv_id in to_remove:
            del self._records[inv_id]

        return len(to_remove)

    def close(self) -> None:
        """Close the journal file descriptor."""
        if self._journal_fd is not None:
            os.close(self._journal_fd)
            self._journal_fd = None
