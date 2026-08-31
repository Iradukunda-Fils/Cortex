"""
Worker Lifecycle State Machine & Tracker (Phase 3)

Tracks worker instance lifecycle stages:
READY -> DRAINING -> FORCED_RECOVERY -> QUIESCED -> TERMINATING -> TERMINATED
Enforces quiescence bounds and drain deadline timeouts.
"""

import threading
import time
from enum import Enum, auto
from typing import Optional

from cortex.tools.kernel.replica.identity import ExecutionIdentity


class WorkerLifecycleStage(Enum):
    READY = auto()
    DRAINING = auto()
    FORCED_RECOVERY = auto()
    QUIESCED = auto()
    TERMINATING = auto()
    TERMINATED = auto()


class WorkerLifecycleTracker:
    """Thread-safe Worker Lifecycle Tracker for Gateway TCB."""

    def __init__(self, execution_identity: ExecutionIdentity, drain_deadline_sec: float = 30.0) -> None:
        self.identity = execution_identity
        self.drain_deadline_sec = drain_deadline_sec
        self._lock = threading.Lock()
        self.stage = WorkerLifecycleStage.READY
        self.owned_invocations: int = 0
        self.pending_effects: int = 0
        self.ipc_outstanding: int = 0
        self.draining_started_at: Optional[float] = None

    def begin_draining(self) -> None:
        with self._lock:
            if self.stage == WorkerLifecycleStage.READY:
                self.stage = WorkerLifecycleStage.DRAINING
                self.draining_started_at = time.monotonic()
                self._check_quiescence_locked()

    def check_drain_deadline(self) -> bool:
        with self._lock:
            if self.stage == WorkerLifecycleStage.DRAINING and self.draining_started_at is not None:
                elapsed = time.monotonic() - self.draining_started_at
                if elapsed >= self.drain_deadline_sec:
                    self.stage = WorkerLifecycleStage.FORCED_RECOVERY
                    return True
            return False

    def update_counts(self, owned_invocations: int, pending_effects: int, ipc_outstanding: int) -> None:
        with self._lock:
            self.owned_invocations = max(0, owned_invocations)
            self.pending_effects = max(0, pending_effects)
            self.ipc_outstanding = max(0, ipc_outstanding)
            if self.stage == WorkerLifecycleStage.DRAINING:
                self._check_quiescence_locked()

    def _check_quiescence_locked(self) -> None:
        if self.owned_invocations == 0 and self.pending_effects == 0 and self.ipc_outstanding == 0:
            self.stage = WorkerLifecycleStage.QUIESCED

    def transition_terminating(self) -> None:
        with self._lock:
            if self.stage in (WorkerLifecycleStage.QUIESCED, WorkerLifecycleStage.FORCED_RECOVERY):
                self.stage = WorkerLifecycleStage.TERMINATING

    def transition_terminated(self) -> None:
        with self._lock:
            self.stage = WorkerLifecycleStage.TERMINATED
