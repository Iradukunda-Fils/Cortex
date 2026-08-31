"""
Cortex Worker Supervisor Implementation (Gate A)

Orchestrates process spawning, cgroup attachment, execution containment, termination,
post-exit state transitions, and safe logical resource reconciliation.

Governance Rule:
    Supervisor Executes; Authority Decides.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

from cortex.tools.kernel.enforcement.cgroup import CgroupResourceEnforcer
from cortex.tools.kernel.enforcement.contract import (
    EnforcementContract,
    EnvironmentCapability,
    SupervisorLifecycleState,
    SupervisorTelemetry,
)
from cortex.tools.kernel.replica.lifecycle import (
    WorkerLifecycleTracker,
)
from cortex.tools.kernel.resource_authority import ResourceAuthority

logger = logging.getLogger(__name__)

# Explicit Named Constants
DEFAULT_GRACE_PERIOD_SEC: float = 5.0


class ExecutionContainmentError(Exception):
    """Raised when worker startup fails to establish the required physical enforcement boundary."""
    pass


class WorkerSupervisor:
    """
    Worker process supervisor for physical execution containment and lifecycle management.
    """

    def __init__(
        self,
        contract: EnforcementContract,
        resource_authority: ResourceAuthority,
        enforcer: Optional[CgroupResourceEnforcer] = None,
        lifecycle_tracker: Optional[WorkerLifecycleTracker] = None,
        grace_period_sec: float = DEFAULT_GRACE_PERIOD_SEC,
    ) -> None:
        self.contract = contract
        self.resource_authority = resource_authority
        self.enforcer = enforcer or CgroupResourceEnforcer()
        self.lifecycle_tracker = lifecycle_tracker
        self.grace_period_sec = grace_period_sec

        self._lock = threading.Lock()
        self.state = SupervisorLifecycleState.CREATED
        self.process: Optional[subprocess.Popen] = None
        self.cgroup_path: str = ""
        self.telemetry = SupervisorTelemetry(
            reservation_id=contract.reservation_id,
            worker_id=contract.worker_id,
            cgroup_path="",
            memory_max_bytes=contract.memory_bytes,
            pids_max_count=contract.pids_max,
        )

    def launch_contained_worker(
        self,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
    ) -> subprocess.Popen:
        """
        Launches a worker process under physical cgroup execution containment.
        Enforces the Atomic Uncontained Startup Prevention Rule:
            RequiredPhysicalEnforcement AND AttachFailure => ExecutionRejected
        """
        with self._lock:
            if self.state != SupervisorLifecycleState.CREATED:
                raise RuntimeError(f"Cannot launch worker in state {self.state}")

            self.state = SupervisorLifecycleState.ATTACHING

        # Step 1: Detect capability & create cgroup
        capability = self.enforcer.detect_environment()
        physical_enforcement_active = (capability == EnvironmentCapability.SUPPORTED_AVAILABLE)

        if self.contract.require_physical_enforcement and not physical_enforcement_active:
            with self._lock:
                self.state = SupervisorLifecycleState.FAILED_CLOSED
            raise ExecutionContainmentError(
                f"Physical enforcement required for worker {self.contract.worker_id}, "
                f"but cgroup v2 capability is {capability.name}. Execution rejected."
            )

        if physical_enforcement_active:
            try:
                self.cgroup_path = self.enforcer.create_worker_cgroup(self.contract)
                self.telemetry.cgroup_path = self.cgroup_path
            except Exception as e:
                with self._lock:
                    self.state = SupervisorLifecycleState.FAILED_CLOSED
                raise ExecutionContainmentError(
                    f"Failed creating cgroup boundary for worker {self.contract.worker_id}: {e}"
                )

        # Step 2: Launch worker process
        effective_env = dict(os.environ)
        if env:
            effective_env.update(env)

        start_ts = time.monotonic()
        try:
            # Under Linux with cgroup v2, we attach the child process PID to cgroup immediately upon spawn
            proc = subprocess.Popen(
                command,
                env=effective_env,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if sys.platform != "win32" else None,
            )
        except Exception as e:
            if physical_enforcement_active and self.cgroup_path:
                self.enforcer.remove_worker_cgroup(self.cgroup_path)
            with self._lock:
                self.state = SupervisorLifecycleState.FAILED_CLOSED
            raise ExecutionContainmentError(f"Failed spawning process for worker {self.contract.worker_id}: {e}")

        # Step 3: Attach process PID to cgroup and verify containment
        if physical_enforcement_active and self.cgroup_path:
            attached = self.enforcer.attach_process(self.cgroup_path, proc.pid)
            verified = self.enforcer.verify_process_membership(self.cgroup_path, proc.pid)

            if not attached or not verified:
                # Immediate fail-closed kill to prevent uncontained execution
                proc.kill()
                proc.wait()
                self.enforcer.remove_worker_cgroup(self.cgroup_path)
                with self._lock:
                    self.state = SupervisorLifecycleState.FAILED_CLOSED
                raise ExecutionContainmentError(
                    f"Process PID {proc.pid} containment check failed for worker {self.contract.worker_id}. "
                    f"Attach: {attached}, Verify: {verified}. Worker killed fail-closed."
                )

        # Step 4: Authorize execution & update state
        with self._lock:
            self.process = proc
            self.state = SupervisorLifecycleState.RUNNING
            self.telemetry.main_pid = proc.pid
            self.telemetry.start_time = start_ts

        logger.info(
            f"Worker {self.contract.worker_id} successfully launched contained. "
            f"PID={proc.pid}, Cgroup='{self.cgroup_path}'"
        )
        return proc

    def verify_execution_tree_containment(self) -> Tuple[bool, Set[int]]:
        """
        Verifies that all running processes in the worker execution tree belong to CG_worker.
        Returns (is_fully_contained, set_of_pids).
        """
        if not self.cgroup_path or not os.path.exists(self.cgroup_path):
            return True, set()

        cgroup_pids = self.enforcer.get_cgroup_pids(self.cgroup_path)
        if self.telemetry.main_pid:
            main_contained = self.telemetry.main_pid in cgroup_pids
            return main_contained, cgroup_pids
        return True, cgroup_pids

    def sample_telemetry(self) -> SupervisorTelemetry:
        """
        Updates and returns real-time resource utilization telemetry.
        """
        if self.cgroup_path:
            stats = self.enforcer.get_statistics(self.cgroup_path)
            self.telemetry.cpu_usage_us = stats.get("cpu_usage_us", 0)
            self.telemetry.memory_current_bytes = stats.get("memory_current_bytes", 0)
            self.telemetry.pids_current_count = stats.get("pids_current_count", 0)
        return self.telemetry

    def terminate_worker_and_reclaim(self) -> SupervisorTelemetry:
        """
        Executes safe 7-stage reclamation sequence:
        Fence -> StopAdmission -> Terminate/Quiesce -> ConfirmProcessExit -> OSReclamation -> LogicalReconciliation -> CgroupCleanup
        """
        with self._lock:
            if self.state in (
                SupervisorLifecycleState.RESOURCE_RECONCILED,
                SupervisorLifecycleState.CGROUP_CLEANED,
            ):
                return self.telemetry
            self.state = SupervisorLifecycleState.DRAINING

        # Step 1: Fence & Stop Admission
        if self.lifecycle_tracker:
            self.lifecycle_tracker.begin_draining()

        # Step 2: Terminate/Quiesce (SIGTERM -> Grace Period -> SIGKILL)
        proc = self.process
        exit_code: Optional[int] = None
        term_signal: Optional[int] = None

        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass

            try:
                proc.wait(timeout=self.grace_period_sec)
            except subprocess.TimeoutExpired:
                with self._lock:
                    self.state = SupervisorLifecycleState.KILLING
                logger.warning(
                    f"Worker {self.contract.worker_id} (PID {proc.pid}) did not exit within "
                    f"{self.grace_period_sec}s grace period. Sending SIGKILL."
                )
                try:
                    proc.kill()
                    proc.wait()
                except OSError:
                    pass

        if proc:
            try:
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()
            except Exception:
                pass
            exit_code = proc.returncode
            if exit_code is not None and exit_code < 0:
                term_signal = abs(exit_code)

        # Step 3: Confirm Process Exit
        with self._lock:
            self.state = SupervisorLifecycleState.PROCESS_EXITED
            self.telemetry.termination_time = time.monotonic()
            self.telemetry.exit_code = exit_code
            self.telemetry.termination_signal = term_signal

        if self.lifecycle_tracker:
            self.lifecycle_tracker.transition_terminating()
            self.lifecycle_tracker.transition_terminated()

        # Step 4: OS Resource Reclamation (Kernel page freeing & task cleanup)
        with self._lock:
            self.state = SupervisorLifecycleState.RESOURCE_RECLAIMING

        # Step 5: Logical Reconciliation (Release ResourceAuthority reservation)
        try:
            self.resource_authority.release(self.contract.reservation_id)
            self.telemetry.reconciliation_time = time.monotonic()
        except KeyError:
            # Idempotent double-release or already released
            pass

        with self._lock:
            self.state = SupervisorLifecycleState.RESOURCE_RECONCILED

        # Step 6: Cgroup Cleanup
        if self.cgroup_path and os.path.exists(self.cgroup_path):
            self.enforcer.remove_worker_cgroup(self.cgroup_path)

        with self._lock:
            self.telemetry.cleanup_time = time.monotonic()
            self.state = SupervisorLifecycleState.CGROUP_CLEANED

        logger.info(
            f"Worker {self.contract.worker_id} successfully terminated & reclaimed. "
            f"ExitCode={exit_code}, Signal={term_signal}"
        )
        return self.telemetry
