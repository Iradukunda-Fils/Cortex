"""
Cortex Execution Enforcement Contract & Environment Definitions (Gate A)

Defines immutable constraints and capability classifications for physical OS-level execution enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional

# Explicit Named Constants
DEFAULT_CFS_PERIOD_US: int = 100000
MILLICORES_PER_CORE: float = 1000.0
UNLIMITED_RESOURCE_VALUE: str = "max"


class EnvironmentCapability(Enum):
    """Classification of host OS execution enforcement capabilities."""

    SUPPORTED_AVAILABLE = auto()
    SUPPORTED_UNAVAILABLE = auto()
    PERMISSION_DENIED = auto()
    UNSUPPORTED = auto()


class SupervisorLifecycleState(Enum):
    """Lifecycle state machine for WorkerSupervisor process orchestration."""

    CREATED = auto()
    ATTACHING = auto()
    RUNNING = auto()
    DRAINING = auto()
    KILLING = auto()
    PROCESS_EXITED = auto()
    RESOURCE_RECLAIMING = auto()
    RESOURCE_RECONCILED = auto()
    CGROUP_CLEANED = auto()
    FAILED_CLOSED = auto()


@dataclass(frozen=True)
class EnforcementContract:
    """
    Immutable specification of OS-level constraints required for worker execution.
    Derived directly from an authorized ResourceAuthority reservation.
    """

    reservation_id: int
    worker_id: int
    cpu_mcores: int
    memory_bytes: int
    pids_max: int
    require_physical_enforcement: bool = True

    def to_cgroup_cpu_max(self, period_us: int = DEFAULT_CFS_PERIOD_US) -> str:
        """Converts cpu_mcores into cgroup v2 cpu.max 'quota period' format."""
        if self.cpu_mcores <= 0:
            return f"{UNLIMITED_RESOURCE_VALUE} {period_us}"
        quota_us = int((self.cpu_mcores / MILLICORES_PER_CORE) * period_us)
        return f"{quota_us} {period_us}"

    def to_cgroup_memory_max(self) -> str:
        """Converts memory_bytes into cgroup v2 memory.max string representation."""
        if self.memory_bytes <= 0:
            return UNLIMITED_RESOURCE_VALUE
        return str(self.memory_bytes)

    def to_cgroup_pids_max(self) -> str:
        """Converts pids_max into cgroup v2 pids.max string representation."""
        if self.pids_max <= 0:
            return UNLIMITED_RESOURCE_VALUE
        return str(self.pids_max)


@dataclass
class SupervisorTelemetry:
    """Operational observability telemetry for worker process execution."""

    reservation_id: int
    worker_id: int
    cgroup_path: str
    main_pid: Optional[int] = None
    start_time: float = 0.0
    termination_time: Optional[float] = None
    exit_code: Optional[int] = None
    termination_signal: Optional[int] = None
    reconciliation_time: Optional[float] = None
    cleanup_time: Optional[float] = None
    cpu_usage_us: int = 0
    memory_max_bytes: int = 0
    memory_current_bytes: int = 0
    pids_max_count: int = 0
    pids_current_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reservation_id": self.reservation_id,
            "worker_id": self.worker_id,
            "cgroup_path": self.cgroup_path,
            "main_pid": self.main_pid,
            "start_time": self.start_time,
            "termination_time": self.termination_time,
            "exit_code": self.exit_code,
            "termination_signal": self.termination_signal,
            "reconciliation_time": self.reconciliation_time,
            "cleanup_time": self.cleanup_time,
            "cpu_usage_us": self.cpu_usage_us,
            "memory_max_bytes": self.memory_max_bytes,
            "memory_current_bytes": self.memory_current_bytes,
            "pids_max_count": self.pids_max_count,
            "pids_current_count": self.pids_current_count,
        }
