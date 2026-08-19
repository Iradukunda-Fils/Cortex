"""
Gateway Invocation State Ledger & Crash Recovery Classifier (Phase 1 & 2)

Durable, Gateway-owned state machine tracking invocation lifecycle states and
classifying orphaned invocations into exact recovery buckets.
"""

import threading
from dataclasses import dataclass
from enum import Enum, auto
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


class RecoveryBucket(Enum):
    UNADMITTED = auto()
    ADMITTED_UNACTUATED = auto()
    ACTUATED_COMMITTED = auto()
    ACTUATION_UNKNOWN = auto()  # Maps to Verdict.INDETERMINATE


@dataclass
class InvocationRecord:
    invocation_id: str
    intent_hash: str
    state: InvocationState
    assigned_worker_id: Optional[str] = None
    lease_epoch: Optional[int] = None
    result_payload: Optional[bytes] = None
    recovery_bucket: Optional[RecoveryBucket] = None


class InvocationStateLedger:
    """Thread-safe Gateway TCB Invocation State Ledger."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: Dict[str, InvocationRecord] = {}

    def create_invocation(self, invocation_id: str, intent_hash: str) -> InvocationRecord:
        with self._lock:
            if invocation_id in self._records:
                raise ValueError(f"Invocation {invocation_id} already exists in ledger")
            record = InvocationRecord(
                invocation_id=invocation_id,
                intent_hash=intent_hash,
                state=InvocationState.QUEUED,
            )
            self._records[invocation_id] = record
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
            if worker_id is not None:
                record.assigned_worker_id = worker_id
            if lease_epoch is not None:
                record.lease_epoch = lease_epoch
            return record

    def get_record(self, invocation_id: str) -> Optional[InvocationRecord]:
        with self._lock:
            return self._records.get(invocation_id)

    def classify_recovery(self, invocation_id: str) -> RecoveryBucket:
        """Classifies an invocation in RECOVERY_REQUIRED or orphaned state into an exact recovery bucket."""
        with self._lock:
            record = self._records.get(invocation_id)
            if not record:
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
            return bucket
