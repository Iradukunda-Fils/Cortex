"""
Cortex Single-Gateway Dynamic Load Balancer Engine (v1.5.0-FROZEN)

Canonical Namespace: https://schemas.cortex.internal/v1
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from cortex.tools.kernel.adapter_contract import AdapterExecutionContext
from cortex.tools.kernel.idempotency import CanonicalOperation, GatewayIdempotencyEngine


class LoadBalancerError(Exception):
    """Base exception for load balancer operations."""

    pass


class NoEligibleWorkerError(LoadBalancerError):
    """Raised when no healthy worker meets capacity or capability requirements."""

    pass


class WorkerNotFoundError(LoadBalancerError):
    """Raised when an operation targets an unregistered worker."""

    pass


class WorkerStatus(Enum):
    """Normative status states for registered execution workers."""

    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    UNHEALTHY = "UNHEALTHY"
    OFFLINE = "OFFLINE"


@dataclass
class WorkerNode:
    """Represents a worker instance registered with the Load Balancer."""

    worker_id: str
    capacity: int
    active_load: int = 0
    status: WorkerStatus = WorkerStatus.ACTIVE
    capabilities: Set[str] = field(default_factory=set)
    last_heartbeat_ts: float = field(default_factory=time.time)

    @property
    def is_eligible(self) -> bool:
        return self.status == WorkerStatus.ACTIVE and self.active_load < self.capacity


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


class DynamicLoadBalancer:
    """
    Single-Gateway Dynamic Load Balancer Engine (v1.5.0-FROZEN):
    
    Coordinates worker admittance, capacity management, rebalancing, worker draining,
    and execution assignment while delegating authorization and idempotency key derivation
    strictly to the Gateway PEP and GatewayIdempotencyEngine.
    """

    def __init__(self, idempotency_engine: GatewayIdempotencyEngine) -> None:
        self._idempotency_engine = idempotency_engine
        self._workers: Dict[str, WorkerNode] = {}
        self._active_assignments: Dict[str, ExecutionAssignment] = {}  # invocation_id -> ExecutionAssignment
        self._invocation_epochs: Dict[str, int] = {}  # invocation_id -> current lease_epoch

    def register_worker(
        self,
        worker_id: str,
        capacity: int,
        capabilities: Optional[Set[str]] = None,
    ) -> WorkerNode:
        """Registers a new worker instance or updates registration."""
        if capacity <= 0:
            raise ValueError(f"Worker capacity must be > 0, got {capacity}")

        node = WorkerNode(
            worker_id=worker_id,
            capacity=capacity,
            capabilities=set(capabilities or []),
            status=WorkerStatus.ACTIVE,
        )
        self._workers[worker_id] = node
        return node

    def update_worker_status(
        self,
        worker_id: str,
        status: WorkerStatus,
        active_load: Optional[int] = None,
    ) -> None:
        """Updates health status and current load of a registered worker."""
        worker = self._workers.get(worker_id)
        if not worker:
            raise WorkerNotFoundError(f"Worker {worker_id!r} not registered")

        worker.status = status
        worker.last_heartbeat_ts = time.time()
        if active_load is not None:
            worker.active_load = max(0, active_load)

    def select_target_worker(
        self,
        required_capability: str,
        user_capabilities: Set[str],
    ) -> WorkerNode:
        """
        Selects least-loaded eligible worker matching capability requirements.
        Eligibility check DOES NOT substitute for Gateway authorization.
        """
        # Capability check: user must possess required capability
        if required_capability not in user_capabilities:
            raise NoEligibleWorkerError(
                f"User capabilities {user_capabilities!r} do not include required capability {required_capability!r}"
            )

        eligible = [
            w for w in self._workers.values()
            if w.is_eligible and (not w.capabilities or required_capability in w.capabilities)
        ]

        if not eligible:
            raise NoEligibleWorkerError("No healthy worker with available capacity found")

        # Select least-loaded worker (Tie-breaker: worker_id string sorting for determinism)
        return min(eligible, key=lambda w: (w.active_load / w.capacity, w.worker_id))

    def assign_execution(
        self,
        op: CanonicalOperation,
        execution_attempt_id: str,
        adapter_request_id: str,
        user_capabilities: Set[str],
        required_capability: str = "execution.submit",
        secret_version: str = "v1",
    ) -> ExecutionAssignment:
        """
        Admits an execution request, selects target worker, advances lease epoch,
        derives Gateway idempotency key, and issues ExecutionAssignment.
        """
        target_worker = self.select_target_worker(
            required_capability=required_capability,
            user_capabilities=user_capabilities,
        )

        current_epoch = self._invocation_epochs.get(op.invocation_id, 0)
        next_epoch = current_epoch + 1

        # Create Gateway-authoritative execution context (handles fencing & HMAC derivation)
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

        # Update internal balances
        target_worker.active_load += 1
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
        """
        Reassigns a failed or crashed invocation to a new healthy worker.
        Advances LeaseEpoch (Epoch_n+1 > Epoch_n) and preserves identical HMAC IdempotencyKey.
        """
        prev_assignment = self._active_assignments.get(op.invocation_id)
        if prev_assignment:
            # Decrement load on old worker if still registered
            old_worker = self._workers.get(prev_assignment.worker_id)
            if old_worker and old_worker.active_load > 0:
                old_worker.active_load -= 1

        # Assign to new target worker (automatically increments lease epoch)
        new_assignment = self.assign_execution(
            op=op,
            execution_attempt_id=new_attempt_id,
            adapter_request_id=new_adapter_request_id,
            user_capabilities=user_capabilities,
            required_capability=required_capability,
            secret_version=secret_version,
        )

        # Assert key preservation invariant
        if prev_assignment:
            assert new_assignment.context.idempotency_key == prev_assignment.context.idempotency_key, (
                "Reassignment violated idempotency key preservation invariant"
            )

        return new_assignment

    def complete_execution(self, invocation_id: str) -> None:
        """Marks execution completed and releases worker capacity."""
        assignment = self._active_assignments.pop(invocation_id, None)
        if assignment:
            worker = self._workers.get(assignment.worker_id)
            if worker and worker.active_load > 0:
                worker.active_load -= 1

    def drain_worker(self, worker_id: str) -> List[str]:
        """
        Transitions worker to DRAINING status and returns list of active invocation_ids to reassign.
        """
        worker = self._workers.get(worker_id)
        if not worker:
            raise WorkerNotFoundError(f"Worker {worker_id!r} not registered")

        worker.status = WorkerStatus.DRAINING
        drained_invocations = [
            inv_id for inv_id, asgn in self._active_assignments.items()
            if asgn.worker_id == worker_id
        ]
        return drained_invocations
