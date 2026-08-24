"""
Issue #34 (Phase 5.1): Hardened Dynamic Load Balancer Kernel Engine
Normative Architecture Version: v1.5.1-FINAL-FROZEN
Coq Proof Target: Phase4RoutingRefinement.v (rd_f1_eligibility_safety)

Zero-Trust Hardening Constraints:
1. Monotonic epoch advancement (E_new > E_old) on reassignment.
2. Ownership-scoped commit validation: (invocation_id, worker_id, lease_epoch).
3. Ownership-validated release accounting (rejects stale/invalid releases).
4. No self-reassignment (w_new != w_old).
5. Strict constructor parameter boundary validation.
6. Quarantine lifecycle for active tasks when workers expire or drop.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

from cortex.tools.kernel.adapter_contract import AdapterExecutionContext
from cortex.tools.kernel.idempotency import CanonicalOperation, GatewayIdempotencyEngine


class WorkerHealthStatus(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    DRAINING = auto()
    UNHEALTHY = auto()


class LoadBalancerError(Exception):
    """Raised on boundary validation, scheduling, or protocol safety violations."""

    pass


class InvalidEpochError(LoadBalancerError):
    """Raised when epoch monotonicity (E_new > E_old) is violated."""

    pass


class InvalidWorkerError(LoadBalancerError):
    """Raised when worker ownership validation fails."""

    pass


class NoEligibleWorkerError(LoadBalancerError):
    """Raised when no healthy worker meets capacity or capability requirements."""

    pass


class WorkerNotFoundError(LoadBalancerError):
    """Raised when an operation targets an unregistered worker."""

    pass


# Backward-compatible alias for WorkerHealthStatus
WorkerStatus = WorkerHealthStatus
WorkerStatus.ACTIVE = WorkerHealthStatus.HEALTHY


@dataclass
class WorkerNode:
    worker_id: str
    capabilities: Set[str]
    max_concurrency: int
    active_load: int = 0
    status: WorkerHealthStatus = WorkerHealthStatus.HEALTHY
    last_heartbeat_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    def __post_init__(self) -> None:
        if not self.worker_id or not isinstance(self.worker_id, str):
            raise LoadBalancerError("Worker ID must be a non-empty string.")
        if self.max_concurrency <= 0:
            raise LoadBalancerError(f"max_concurrency must be > 0, got {self.max_concurrency}")
        if not isinstance(self.capabilities, set):
            raise LoadBalancerError("Capabilities must be provided as a set.")

    @property
    def capacity(self) -> int:
        return self.max_concurrency

    @property
    def available_capacity(self) -> int:
        if self.status != WorkerHealthStatus.HEALTHY:
            return 0
        return max(0, self.max_concurrency - self.active_load)

    @property
    def is_eligible(self) -> bool:
        return self.available_capacity > 0


@dataclass
class AssignmentRecord:
    worker_id: str
    lease_epoch: int
    assigned_at_ms: int


@dataclass(frozen=True)
class ExecutionAssignment:
    """
    Authoritative worker assignment record created by Load Balancer.
    Schema URI: https://schemas.cortex.internal/v1/execution-assignment.json
    """

    invocation_id: str
    execution_attempt_id: str
    worker_id: str
    lease_epoch: int
    context: AdapterExecutionContext
    schema_uri: str = "https://schemas.cortex.internal/v1/execution-assignment.json"


class ProductionDynamicLoadBalancer:
    """
    Zero-Trust Dynamic Load Balancer Kernel Engine.
    Enforces linearizable state bounds, strict epoch monotonicity, ownership-scoped
    lease validations, active-work quarantine on worker eviction, and allocation protection.
    """

    def __init__(
        self,
        heartbeat_timeout_ms: int = 5000,
        worker_ttl_ms: int = 30000,
        max_registered_workers: int = 1000,
    ) -> None:
        if heartbeat_timeout_ms <= 0 or worker_ttl_ms <= 0:
            raise LoadBalancerError("Timeouts must be positive integers > 0.")
        if max_registered_workers <= 0:
            raise LoadBalancerError("max_registered_workers must be > 0.")

        self._lock = threading.RLock()
        self._workers: Dict[str, WorkerNode] = {}
        self._assignments: Dict[str, AssignmentRecord] = {}  # inv_id -> AssignmentRecord
        self._quarantined_invocations: Dict[str, AssignmentRecord] = {}  # inv_id -> AssignmentRecord

        self._heartbeat_timeout_ms = heartbeat_timeout_ms
        self._worker_ttl_ms = worker_ttl_ms
        self._max_registered_workers = max_registered_workers

    def register_worker(self, worker_id: str, capabilities: Set[str], max_concurrency: int) -> None:
        with self._lock:
            if worker_id not in self._workers and len(self._workers) >= self._max_registered_workers:
                self._evict_stale_workers_unlocked(int(time.time() * 1000), force_evict_unhealthy=True)
                if len(self._workers) >= self._max_registered_workers:
                    raise LoadBalancerError(
                        f"Worker registry capacity limit ({self._max_registered_workers}) reached."
                    )

            existing_load = self._workers[worker_id].active_load if worker_id in self._workers else 0

            # Instantiation runs __post_init__ validation boundaries
            node = WorkerNode(
                worker_id=worker_id,
                capabilities=capabilities,
                max_concurrency=max_concurrency,
                active_load=existing_load,
            )
            self._workers[worker_id] = node

    def record_heartbeat(self, worker_id: str, current_unix_ms: int) -> None:
        with self._lock:
            if worker_id in self._workers:
                worker = self._workers[worker_id]
                worker.last_heartbeat_ms = current_unix_ms
                if worker.status == WorkerHealthStatus.UNHEALTHY:
                    worker.status = WorkerHealthStatus.HEALTHY

    def drain_worker(self, worker_id: str) -> List[str]:
        with self._lock:
            if worker_id in self._workers:
                self._workers[worker_id].status = WorkerHealthStatus.DRAINING
            drained_invocations = [
                inv_id for inv_id, record in self._assignments.items()
                if record.worker_id == worker_id
            ]
            return drained_invocations

    def _evict_stale_workers_unlocked(self, current_unix_ms: int, force_evict_unhealthy: bool = False) -> None:
        to_remove = []
        for worker_id, worker in self._workers.items():
            idle = current_unix_ms - worker.last_heartbeat_ms
            if idle > self._worker_ttl_ms or (force_evict_unhealthy and worker.status == WorkerHealthStatus.UNHEALTHY):
                to_remove.append(worker_id)

        for worker_id in to_remove:
            # Shift active assignments associated with evicted worker to quarantine
            orphaned_invocations = [
                inv_id for inv_id, record in self._assignments.items()
                if record.worker_id == worker_id
            ]
            for inv_id in orphaned_invocations:
                record = self._assignments.pop(inv_id)
                self._quarantined_invocations[inv_id] = record

            del self._workers[worker_id]

    def select_target_worker(self, capability: str, current_unix_ms: int) -> str:
        with self._lock:
            self._evict_stale_workers_unlocked(current_unix_ms)

            eligible_workers: List[WorkerNode] = []
            for worker in self._workers.values():
                if current_unix_ms - worker.last_heartbeat_ms > self._heartbeat_timeout_ms:
                    worker.status = WorkerHealthStatus.UNHEALTHY

                if capability in worker.capabilities and worker.available_capacity > 0:
                    eligible_workers.append(worker)

            if not eligible_workers:
                raise LoadBalancerError(f"No eligible healthy workers for capability: {capability}")

            selected = max(eligible_workers, key=lambda w: (w.available_capacity, w.worker_id))
            return selected.worker_id

    def assign_execution(
        self,
        worker_id: str,
        invocation_id: str,
        current_epoch: int,
        current_unix_ms: Optional[int] = None,
    ) -> None:
        if current_unix_ms is None:
            current_unix_ms = int(time.time() * 1000)

        with self._lock:
            if worker_id not in self._workers:
                raise InvalidWorkerError(f"Worker '{worker_id}' is not registered.")

            target_worker = self._workers[worker_id]

            # Reassignment Validation Protocols
            if invocation_id in self._assignments:
                existing_record = self._assignments[invocation_id]

                if existing_record.worker_id == worker_id:
                    raise LoadBalancerError(
                        f"Self-reassignment rejected for invocation '{invocation_id}' on worker '{worker_id}'."
                    )
                if current_epoch <= existing_record.lease_epoch:
                    raise InvalidEpochError(
                        f"Non-monotonic epoch reassignment rejected: {current_epoch} <= {existing_record.lease_epoch}"
                    )

                # Reassignment target must have capacity
                if target_worker.available_capacity <= 0:
                    raise LoadBalancerError(f"Target worker '{worker_id}' has no available capacity.")

                # Release load on previous owner safely
                prev_worker_id = existing_record.worker_id
                if prev_worker_id in self._workers:
                    self._workers[prev_worker_id].active_load = max(
                        0, self._workers[prev_worker_id].active_load - 1
                    )
            else:
                # Initial Assignment: Check capacity
                if target_worker.available_capacity <= 0:
                    raise LoadBalancerError(f"Worker '{worker_id}' has no available capacity.")

            # Bind Assignment
            target_worker.active_load += 1
            self._assignments[invocation_id] = AssignmentRecord(
                worker_id=worker_id,
                lease_epoch=current_epoch,
                assigned_at_ms=current_unix_ms,
            )
            # Remove from quarantine if re-scheduled from an evicted state
            self._quarantined_invocations.pop(invocation_id, None)

    def release_execution(self, worker_id: str, invocation_id: str, lease_epoch: Optional[int] = None) -> None:
        """
        Releases an active invocation. Requires strict worker ownership and matching epoch
        if lease_epoch is provided. Rejects un-owned decrements.
        """
        with self._lock:
            if invocation_id not in self._assignments:
                # Execution may have been quarantined or already released; safe no-op or reject
                return

            record = self._assignments[invocation_id]

            # Enforce ownership during release
            if record.worker_id != worker_id:
                raise InvalidWorkerError(
                    f"Release rejected: worker '{worker_id}' does not own invocation '{invocation_id}' "
                    f"(owned by '{record.worker_id}')."
                )

            if lease_epoch is not None and record.lease_epoch != lease_epoch:
                raise InvalidEpochError(
                    f"Release rejected: lease epoch mismatch ({lease_epoch} != active {record.lease_epoch})."
                )

            if worker_id in self._workers:
                self._workers[worker_id].active_load = max(0, self._workers[worker_id].active_load - 1)

            del self._assignments[invocation_id]

    def validate_commit_lease(self, invocation_id: str, worker_id: str, execution_epoch: int) -> bool:
        """
        Strict triple validation: (Invocation, Worker, Epoch) == Active State.
        """
        with self._lock:
            if invocation_id not in self._assignments:
                return False
            record = self._assignments[invocation_id]
            return record.worker_id == worker_id and record.lease_epoch == execution_epoch

    def get_quarantined_invocations(self) -> Dict[str, AssignmentRecord]:
        with self._lock:
            return dict(self._quarantined_invocations)


class DynamicLoadBalancer:
    """
    Gateway-integrated Dynamic Load Balancer wrapper for backwards compatibility
    with existing test suites and Gateway PEP integration.
    """

    def __init__(self, idempotency_engine: GatewayIdempotencyEngine) -> None:
        self._idempotency_engine = idempotency_engine
        self._kernel = ProductionDynamicLoadBalancer()
        self._active_assignments: Dict[str, ExecutionAssignment] = {}
        self._invocation_epochs: Dict[str, int] = {}
        self._lock = threading.RLock()

    @property
    def _workers(self) -> Dict[str, WorkerNode]:
        return self._kernel._workers

    def register_worker(
        self,
        worker_id: str,
        capacity: int,
        capabilities: Optional[Set[str]] = None,
    ) -> WorkerNode:
        with self._lock:
            self._kernel.register_worker(
                worker_id=worker_id,
                capabilities=set(capabilities or []),
                max_concurrency=capacity,
            )
            return self._kernel._workers[worker_id]

    def update_worker_status(
        self,
        worker_id: str,
        status: WorkerStatus,
        active_load: Optional[int] = None,
    ) -> None:
        with self._lock:
            worker = self._kernel._workers.get(worker_id)
            if not worker:
                raise WorkerNotFoundError(f"Worker {worker_id!r} not registered")

            if status == WorkerStatus.UNHEALTHY:
                worker.status = WorkerHealthStatus.UNHEALTHY
            elif status == WorkerStatus.DRAINING:
                worker.status = WorkerHealthStatus.DRAINING
            elif status == WorkerStatus.ACTIVE:
                worker.status = WorkerHealthStatus.HEALTHY

            worker.last_heartbeat_ms = int(time.time() * 1000)
            if active_load is not None:
                worker.active_load = max(0, active_load)

    def select_target_worker(
        self,
        required_capability: str,
        user_capabilities: Set[str],
    ) -> WorkerNode:
        with self._lock:
            if required_capability not in user_capabilities:
                raise NoEligibleWorkerError(
                    f"User capabilities {user_capabilities!r} do not include required capability {required_capability!r}"
                )

            eligible = [
                w for w in self._kernel._workers.values()
                if w.is_eligible and (not w.capabilities or required_capability in w.capabilities)
            ]

            if not eligible:
                raise NoEligibleWorkerError("No healthy worker with available capacity found")

            selected_id = self._kernel.select_target_worker(required_capability, int(time.time() * 1000))
            return self._kernel._workers[selected_id]

    def assign_execution(
        self,
        op: CanonicalOperation,
        execution_attempt_id: str,
        adapter_request_id: str,
        user_capabilities: Set[str],
        required_capability: str = "execution.submit",
        secret_version: str = "v1",
    ) -> ExecutionAssignment:
        with self._lock:
            target_worker = self.select_target_worker(
                required_capability=required_capability,
                user_capabilities=user_capabilities,
            )

            current_epoch = self._invocation_epochs.get(op.invocation_id, 0)
            next_epoch = current_epoch + 1

            ctx = self._idempotency_engine.create_adapter_context(
                op=op,
                execution_attempt_id=execution_attempt_id,
                adapter_request_id=adapter_request_id,
                lease_epoch=next_epoch,
                secret_version=secret_version,
            )

            assignment = ExecutionAssignment(
                invocation_id=op.invocation_id,
                execution_attempt_id=execution_attempt_id,
                worker_id=target_worker.worker_id,
                lease_epoch=next_epoch,
                context=ctx,
            )

            self._kernel.assign_execution(
                worker_id=target_worker.worker_id,
                invocation_id=op.invocation_id,
                current_epoch=next_epoch,
            )

            self._active_assignments[op.invocation_id] = assignment
            self._invocation_epochs[op.invocation_id] = next_epoch

            return assignment

    def reassign_failed_execution(
        self,
        op: CanonicalOperation,
        new_attempt_id: str,
        new_adapter_request_id: str,
        user_capabilities: Set[str],
        required_capability: str = "execution.submit",
        secret_version: str = "v1",
    ) -> ExecutionAssignment:
        with self._lock:
            prev_assignment = self._active_assignments.get(op.invocation_id)

            new_assignment = self.assign_execution(
                op=op,
                execution_attempt_id=new_attempt_id,
                adapter_request_id=new_adapter_request_id,
                user_capabilities=user_capabilities,
                required_capability=required_capability,
                secret_version=secret_version,
            )

            if prev_assignment:
                assert new_assignment.context.idempotency_key == prev_assignment.context.idempotency_key, (
                    "Reassignment violated idempotency key preservation invariant"
                )

            return new_assignment

    def complete_execution(self, invocation_id: str) -> None:
        with self._lock:
            assignment = self._active_assignments.pop(invocation_id, None)
            if assignment:
                self._kernel.release_execution(
                    worker_id=assignment.worker_id,
                    invocation_id=invocation_id,
                    lease_epoch=assignment.lease_epoch,
                )

    def drain_worker(self, worker_id: str) -> List[str]:
        with self._lock:
            return self._kernel.drain_worker(worker_id)
