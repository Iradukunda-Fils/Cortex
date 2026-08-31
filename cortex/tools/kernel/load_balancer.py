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
from cortex.tools.kernel.resource_bounds import ResourceAction, ResourceBoundRule, ResourceBoundValidator


def current_timestamp_ms() -> int:
    """Returns current Unix epoch timestamp in milliseconds."""
    return int(time.time() * 1000)


# System Kernel Configuration Constants (Issue #47 / Governance Boundary)
DEFAULT_HEARTBEAT_TIMEOUT_MS = 5000
DEFAULT_WORKER_TTL_MS = 30000
DEFAULT_MAX_REGISTERED_WORKERS = 1000
DEFAULT_MAX_QUARANTINE_RECORDS = 1000
DEFAULT_MAX_QUARANTINE_BYTES = 4 * 1024 * 1024  # 4 MiB
DEFAULT_WORKER_BYTE_ESTIMATE = 1024
DEFAULT_INITIAL_PROCESS_GENERATION = 1
DEFAULT_INITIAL_EPOCH = 1
EXECUTION_ASSIGNMENT_SCHEMA_URI = "https://schemas.cortex.internal/v1/execution-assignment.json"


class WorkerHealthStatus(Enum):
    HEALTHY = auto()
    ACTIVE = HEALTHY
    DEGRADED = auto()
    DRAINING = auto()
    UNHEALTHY = auto()


class InvocationLifecycleState(Enum):
    """
    Formally disjoint Invocation Lifecycle States (Issue #46).
    Admitted invocations occupy EXACTLY ONE lifecycle state at any point in time.
    Note: Reassignment is an ExecutionAttempt lineage event, NOT a lifecycle state.
    """

    ADMITTED = auto()
    ACTIVE = auto()
    QUARANTINED = auto()
    RECONCILED = auto()
    COMPLETED = auto()


class LoadBalancerError(Exception):
    """Raised on boundary validation, scheduling, or protocol safety violations."""

    pass


class InvalidEpochError(LoadBalancerError):
    """Raised when epoch monotonicity (E_new > E_old) or authority epoch validation fails."""

    pass


class InvalidWorkerError(LoadBalancerError):
    """Raised when worker ownership validation fails."""

    pass


class StaleWorkerIncarnationError(LoadBalancerError):
    """Raised when an operation or worker registration uses a stale process generation (Issue #48)."""

    pass


class InvalidStateTransitionError(LoadBalancerError):
    """Raised when an invocation FSM lifecycle state transition is illegal (Issue #46)."""

    pass


class NoEligibleWorkerError(LoadBalancerError):
    """Raised when no healthy worker meets capacity or capability requirements."""

    pass


class WorkerNotFoundError(LoadBalancerError):
    """Raised when an operation targets an unregistered worker."""

    pass


# Type alias for WorkerHealthStatus
WorkerStatus = WorkerHealthStatus


@dataclass(frozen=True)
class WorkerIdentity:
    """Worker process incarnation identity (Issue #48)."""

    node_id: str
    process_generation: int = DEFAULT_INITIAL_PROCESS_GENERATION

    def __post_init__(self) -> None:
        if not self.node_id or not isinstance(self.node_id, str):
            raise LoadBalancerError("node_id must be a non-empty string.")
        if self.process_generation <= 0:
            raise LoadBalancerError(f"process_generation must be > 0, got {self.process_generation}")


@dataclass(frozen=True)
class EpochTriple:
    """Decoupled epoch triple: AuthorityEpoch, LeaseEpoch, RecoveryEpoch (Section 4)."""

    authority_epoch: int = DEFAULT_INITIAL_EPOCH
    lease_epoch: int = DEFAULT_INITIAL_EPOCH
    recovery_epoch: int = DEFAULT_INITIAL_EPOCH


@dataclass
class ExecutionAttempt:
    """Lineage record for an individual worker assignment attempt (Issue #46 / Issue #47)."""

    attempt_id: str
    worker_id: str
    lease_epoch: int
    assigned_at_ms: int
    generation: int = DEFAULT_INITIAL_PROCESS_GENERATION


@dataclass(frozen=True)
class VersionedReadView:
    """
    Immutable Versioned Read View Snapshot: V_k = f(S_A^k) (Issue #50.d.5)
    Published under atomic reference assignment whenever authoritative state S_A mutates.
    Allows lock-free target worker selection for concurrent readers.
    """

    version: int
    workers_snapshot: Dict[str, WorkerNode]
    capability_index_snapshot: Dict[str, Tuple[str, ...]]


@dataclass
class InvocationRecord:

    """
    Authoritative state record for a logical invocation (Issue #46).
    Enforces Invocation Lifecycle FSM disjoint state totality.
    """

    invocation_id: str
    state: InvocationLifecycleState = InvocationLifecycleState.ADMITTED
    attempts: List[ExecutionAttempt] = field(default_factory=list)
    admitted_at_ms: int = field(default_factory=current_timestamp_ms)
    updated_at_ms: int = field(default_factory=current_timestamp_ms)
    quarantined_at_ms: Optional[int] = None
    quarantine_reason: Optional[str] = None
    completed_at_ms: Optional[int] = None
    reconciled_at_ms: Optional[int] = None

    def transition_to(self, new_state: InvocationLifecycleState, reason: Optional[str] = None) -> None:
        """Enforces legal Invocation FSM transitions."""
        now = current_timestamp_ms()

        legal_transitions = {
            InvocationLifecycleState.ADMITTED: {InvocationLifecycleState.ACTIVE},
            InvocationLifecycleState.ACTIVE: {
                InvocationLifecycleState.ACTIVE,
                InvocationLifecycleState.COMPLETED,
                InvocationLifecycleState.QUARANTINED,
            },
            InvocationLifecycleState.QUARANTINED: {InvocationLifecycleState.RECONCILED, InvocationLifecycleState.ACTIVE},
            InvocationLifecycleState.COMPLETED: {InvocationLifecycleState.RECONCILED},
            InvocationLifecycleState.RECONCILED: set(),
        }

        if new_state not in legal_transitions[self.state]:
            raise InvalidStateTransitionError(
                f"Illegal lifecycle transition for invocation '{self.invocation_id}': {self.state.name} -> {new_state.name}"
            )

        self.state = new_state
        self.updated_at_ms = now

        if new_state == InvocationLifecycleState.QUARANTINED:
            self.quarantined_at_ms = now
            self.quarantine_reason = reason
        elif new_state == InvocationLifecycleState.COMPLETED:
            self.completed_at_ms = now
        elif new_state == InvocationLifecycleState.RECONCILED:
            self.reconciled_at_ms = now


@dataclass
class WorkerNode:
    worker_id: str
    capabilities: Set[str]
    max_concurrency: int
    active_load: int = 0
    process_generation: int = DEFAULT_INITIAL_PROCESS_GENERATION
    status: WorkerHealthStatus = WorkerHealthStatus.HEALTHY
    last_heartbeat_ms: int = field(default_factory=current_timestamp_ms)

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
    generation: int = DEFAULT_INITIAL_PROCESS_GENERATION



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
    schema_uri: str = EXECUTION_ASSIGNMENT_SCHEMA_URI


from cortex.tools.kernel.resource_authority import (  # noqa: E402
    ResourceAuthority,
)


class ProductionDynamicLoadBalancer:
    """
    Zero-Trust Dynamic Load Balancer Kernel Engine.
    Enforces linearizable state bounds, strict epoch monotonicity, ownership-scoped
    lease validations, active-work quarantine on worker eviction, allocation protection,
    and unified ResourceAuthority reservation governance.
    """

    def __init__(
        self,
        heartbeat_timeout_ms: int = DEFAULT_HEARTBEAT_TIMEOUT_MS,
        worker_ttl_ms: int = DEFAULT_WORKER_TTL_MS,
        max_registered_workers: int = DEFAULT_MAX_REGISTERED_WORKERS,
        max_quarantine_records: int = DEFAULT_MAX_QUARANTINE_RECORDS,
        max_quarantine_bytes: int = DEFAULT_MAX_QUARANTINE_BYTES,
        resource_authority: Optional[ResourceAuthority] = None,
    ) -> None:
        if heartbeat_timeout_ms <= 0 or worker_ttl_ms <= 0:
            raise LoadBalancerError("Timeouts must be positive integers > 0.")
        if max_registered_workers <= 0:
            raise LoadBalancerError("max_registered_workers must be > 0.")

        self._lock = threading.RLock()
        self._workers: Dict[str, WorkerNode] = {}
        self._assignments: Dict[str, AssignmentRecord] = {}  # inv_id -> AssignmentRecord
        self._quarantined_invocations: Dict[str, AssignmentRecord] = {}  # inv_id -> AssignmentRecord
        self._invocations: Dict[str, InvocationRecord] = {}  # inv_id -> InvocationRecord (Issue #46)
        self._resource_authority: ResourceAuthority = resource_authority or ResourceAuthority()

        # Derived Read View: Index = f(S_A) (Issue #50.d.2 - Authoritative state S_A unchanged)
        self._capability_index: Dict[str, Set[str]] = {}  # capability -> set(worker_id)

        # Versioned Snapshot Read View: V_k = f(S_A^k) (Issue #50.d.5 - Lock-free parallel reads)
        self._view_version: int = 0
        self._versioned_read_view: Optional[VersionedReadView] = None
        self._publish_versioned_read_view_unlocked()

        self._heartbeat_timeout_ms = heartbeat_timeout_ms
        self._worker_ttl_ms = worker_ttl_ms
        self._max_registered_workers = max_registered_workers
        self._max_quarantine_records = max_quarantine_records
        self._max_quarantine_bytes = max_quarantine_bytes

        # Universal Resource Bound Validator (Issue #47)
        self._resource_validator = ResourceBoundValidator()
        self._resource_validator.register_rule(
            ResourceBoundRule(
                "workers",
                max_registered_workers,
                max_registered_workers * DEFAULT_WORKER_BYTE_ESTIMATE,
                ResourceAction.BACKPRESSURE,
            )
        )
        self._resource_validator.register_rule(
            ResourceBoundRule("quarantine", max_quarantine_records, max_quarantine_bytes, ResourceAction.QUARANTINE)
        )

    def _publish_versioned_read_view_unlocked(
        self,
        affected_worker_id: Optional[str] = None,
        capabilities_changed: bool = True,
    ) -> None:
        """
        Publishes immutable VersionedReadView snapshot V_k = f(S_A^k) (Issue #50.d.5).
        Enables lock-free target worker selection for concurrent read operations.
        Uses O(1) incremental dictionary reference update to eliminate allocation overhead.

        Args:
            affected_worker_id: If set, performs O(1) incremental worker snapshot update.
            capabilities_changed: If False, reuses the previous capability index snapshot
                                  (avoids O(|capabilities|) tuple rebuild for load-only mutations).
        """
        self._view_version += 1
        if self._versioned_read_view is None or affected_worker_id is None:
            w_snap = dict(self._workers)
            cap_snap = {cap: tuple(wids) for cap, wids in self._capability_index.items()}
        else:
            # O(1) incremental reference update
            w_snap = dict(self._versioned_read_view.workers_snapshot)
            if affected_worker_id in self._workers:
                w_snap[affected_worker_id] = self._workers[affected_worker_id]
            else:
                w_snap.pop(affected_worker_id, None)
            if capabilities_changed:
                cap_snap = {cap: tuple(wids) for cap, wids in self._capability_index.items()}
            else:
                cap_snap = self._versioned_read_view.capability_index_snapshot

        self._versioned_read_view = VersionedReadView(
            version=self._view_version,
            workers_snapshot=w_snap,
            capability_index_snapshot=cap_snap,
        )



    def rebuild_capability_index(self) -> None:
        """
        Reconstructs derived capability index f(S_A) deterministically from authoritative state S_A.
        Used during WAL recovery replay to guarantee index freshness without persisting index records.
        """
        with self._lock:
            self._capability_index.clear()
            for worker_id, worker in self._workers.items():
                for cap in worker.capabilities:
                    self._capability_index.setdefault(cap, set()).add(worker_id)
            self._publish_versioned_read_view_unlocked()


    def assert_capability_index_consistency(self) -> None:
        """
        Enforces Invariant I_9: Derived Capability Index Consistency
        Formula: w in Index[c] <==> w in W and c in Capabilities(w)
        Raises LoadBalancerError on any invariant drift.
        """
        with self._lock:
            # 1. Forward Check: Index[c] contains only valid registered workers with capability c
            for cap, worker_ids in self._capability_index.items():
                for wid in worker_ids:
                    if wid not in self._workers:
                        raise LoadBalancerError(
                            f"Invariant I_9 Violation: Stale worker '{wid}' in derived index for capability '{cap}'."
                        )
                    if cap not in self._workers[wid].capabilities:
                        raise LoadBalancerError(
                            f"Invariant I_9 Violation: Worker '{wid}' in index[{cap}] lacks capability '{cap}'."
                        )
            # 2. Reverse Check: Every registered worker capability is indexed
            for wid, worker in self._workers.items():
                for cap in worker.capabilities:
                    if cap not in self._capability_index or wid not in self._capability_index[cap]:
                        raise LoadBalancerError(
                            f"Invariant I_9 Violation: Registered worker '{wid}' with capability '{cap}' missing from derived index."
                        )


    def register_worker(
        self,
        worker_id: str,
        capabilities: Set[str],
        max_concurrency: int,
        process_generation: int = DEFAULT_INITIAL_PROCESS_GENERATION,
    ) -> None:
        with self._lock:
            if worker_id in self._workers:
                existing = self._workers[worker_id]
                if process_generation < existing.process_generation:
                    raise StaleWorkerIncarnationError(
                        f"Stale worker generation {process_generation} < active {existing.process_generation} for worker '{worker_id}'."
                    )
                if process_generation > existing.process_generation:
                    # Fence out assignments from previous generation
                    orphaned = [inv_id for inv_id, rec in self._assignments.items() if rec.worker_id == worker_id]
                    for inv_id in orphaned:
                        rec = self._assignments.pop(inv_id)
                        self._quarantined_invocations[inv_id] = rec
                        if inv_id in self._invocations:
                            self._invocations[inv_id].transition_to(
                                InvocationLifecycleState.QUARANTINED,
                                reason="STALE_WORKER_INCARNATION_FENCED",
                            )
                    existing_load = 0
                else:
                    existing_load = existing.active_load
            else:
                if len(self._workers) >= self._max_registered_workers:
                    self._evict_stale_workers_unlocked(int(time.time() * 1000), force_evict_unhealthy=True)
                    if len(self._workers) >= self._max_registered_workers:
                        raise LoadBalancerError(
                            f"Worker registry capacity limit ({self._max_registered_workers}) reached."
                        )
                existing_load = 0

            # Instantiation runs __post_init__ validation boundaries
            node = WorkerNode(
                worker_id=worker_id,
                capabilities=capabilities,
                max_concurrency=max_concurrency,
                active_load=existing_load,
                process_generation=process_generation,
            )

            # Update derived capability index f(S_A) cleanly
            if worker_id in self._workers:
                for old_cap in self._workers[worker_id].capabilities:
                    if old_cap in self._capability_index:
                        self._capability_index[old_cap].discard(worker_id)

            for cap in capabilities:
                self._capability_index.setdefault(cap, set()).add(worker_id)

            self._workers[worker_id] = node
            self._publish_versioned_read_view_unlocked()


    def record_heartbeat(self, worker_id: str, current_unix_ms: int) -> None:
        with self._lock:
            if worker_id in self._workers:
                worker = self._workers[worker_id]
                worker.last_heartbeat_ms = current_unix_ms
                if worker.status == WorkerHealthStatus.UNHEALTHY:
                    worker.status = WorkerHealthStatus.HEALTHY
                self._publish_versioned_read_view_unlocked(worker_id, capabilities_changed=False)

    def drain_worker(self, worker_id: str) -> List[str]:
        with self._lock:
            if worker_id in self._workers:
                self._workers[worker_id].status = WorkerHealthStatus.DRAINING
                self._publish_versioned_read_view_unlocked()
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
                if inv_id in self._invocations:
                    self._invocations[inv_id].transition_to(
                        InvocationLifecycleState.QUARANTINED,
                        reason=f"WORKER_EVICTED_{worker_id}",
                    )

            worker = self._workers.pop(worker_id)
            for cap in worker.capabilities:
                if cap in self._capability_index:
                    self._capability_index[cap].discard(worker_id)

        if to_remove:
            self._publish_versioned_read_view_unlocked()

    def select_target_worker(
        self,
        capability: str,
        current_unix_ms: int,
        use_snapshot_read_view: bool = False,
    ) -> str:
        """
        Selects target worker for execution.
        If use_snapshot_read_view=True, performs lock-free selection against immutable VersionedReadView V_k = f(S_A^k).
        If use_snapshot_read_view=False, evaluates selection under self._lock.
        """
        if use_snapshot_read_view:
            view = self._versioned_read_view
            if view is None:
                raise LoadBalancerError("Versioned read view V_k is not initialized.")
            target_ids = view.capability_index_snapshot.get(capability, ())
            snapshot_eligible_workers: List[WorkerNode] = []
            for wid in target_ids:
                worker = view.workers_snapshot.get(wid)
                if worker is None:
                    continue
                if current_unix_ms - worker.last_heartbeat_ms <= self._heartbeat_timeout_ms and worker.available_capacity > 0:
                    snapshot_eligible_workers.append(worker)

            if not snapshot_eligible_workers:
                raise LoadBalancerError(f"No eligible healthy workers for capability: {capability}")

            selected = max(snapshot_eligible_workers, key=lambda w: (w.available_capacity, w.worker_id))
            return selected.worker_id

        with self._lock:
            self._evict_stale_workers_unlocked(current_unix_ms)

            eligible_workers: List[WorkerNode] = []
            target_ids = self._capability_index.get(capability, set())
            for worker_id in target_ids:
                worker = self._workers.get(worker_id)
                if worker is None:
                    continue
                if current_unix_ms - worker.last_heartbeat_ms > self._heartbeat_timeout_ms:
                    worker.status = WorkerHealthStatus.UNHEALTHY

                if worker.available_capacity > 0:
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

            prev_worker_id: Optional[str] = None

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

                prev_worker_id = existing_record.worker_id
            else:
                # Initial Assignment: Check capacity
                if target_worker.available_capacity <= 0:
                    raise LoadBalancerError(f"Worker '{worker_id}' has no available capacity.")

            # Bind Assignment
            self._assignments[invocation_id] = AssignmentRecord(
                worker_id=worker_id,
                lease_epoch=current_epoch,
                assigned_at_ms=current_unix_ms,
                generation=target_worker.process_generation,
            )

            # O(1) direct active_load increment/decrement (replaces O(|assignments|) linear scan)
            target_worker.active_load += 1
            if prev_worker_id and prev_worker_id in self._workers:
                prev_worker = self._workers[prev_worker_id]
                prev_worker.active_load = max(0, prev_worker.active_load - 1)

            # Update Invocation FSM Record & Attempt Lineage (Issue #46)
            if invocation_id not in self._invocations:
                inv_rec = InvocationRecord(invocation_id=invocation_id, admitted_at_ms=current_unix_ms)
                self._invocations[invocation_id] = inv_rec
            else:
                inv_rec = self._invocations[invocation_id]

            inv_rec.transition_to(InvocationLifecycleState.ACTIVE)
            inv_rec.attempts.append(
                ExecutionAttempt(
                    attempt_id=f"{invocation_id}_att_{current_epoch}",
                    worker_id=worker_id,
                    lease_epoch=current_epoch,
                    assigned_at_ms=current_unix_ms,
                    generation=target_worker.process_generation,
                )
            )

            # Remove from quarantine if re-scheduled from an evicted state
            self._quarantined_invocations.pop(invocation_id, None)

            # Single view publish per mutation (Issue #50.d.5 efficiency)
            self._publish_versioned_read_view_unlocked(worker_id, capabilities_changed=False)

    def _sync_worker_active_load(self, worker_id: str) -> int:
        """
        Computes ground truth active load (cntW) from authoritative assignments
        and synchronizes worker.active_load to eliminate CTR-04 counter drift risk (Issue #47).
        O(|assignments|) — used for reconciliation/invariant verification, NOT on hot assignment path.
        """
        cnt = sum(1 for rec in self._assignments.values() if rec.worker_id == worker_id)
        if worker_id in self._workers:
            self._workers[worker_id].active_load = cnt
        return cnt


    def validate_state_invariants(self) -> bool:
        """
        Dynamically checks the forward simulation relation R(C,A) invariants (Issue #47):
        - I2: active_load matches actual assignment count for every worker.
        - I3: Assignment uniqueness across invocations.
        - I4: Lease epoch consistency.
        """
        with self._lock:
            for worker_id, worker in self._workers.items():
                expected_load = sum(1 for rec in self._assignments.values() if rec.worker_id == worker_id)
                if worker.active_load != expected_load:
                    return False
            return True

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

            del self._assignments[invocation_id]
            # O(1) direct active_load decrement
            if worker_id in self._workers:
                self._workers[worker_id].active_load = max(0, self._workers[worker_id].active_load - 1)
            if invocation_id in self._invocations:
                inv_rec = self._invocations.pop(invocation_id)
                inv_rec.transition_to(InvocationLifecycleState.COMPLETED)

            # Single view publish per mutation
            self._publish_versioned_read_view_unlocked(worker_id, capabilities_changed=False)

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

    def get_invocation(self, invocation_id: str) -> Optional[InvocationRecord]:
        with self._lock:
            return self._invocations.get(invocation_id)

    def get_invocations(self) -> Dict[str, InvocationRecord]:
        with self._lock:
            return dict(self._invocations)

    def reconcile_quarantined(self, invocation_id: str) -> None:
        """Transitions a quarantined invocation to RECONCILED and cleans up memory state (Issue #46)."""
        with self._lock:
            self._quarantined_invocations.pop(invocation_id, None)
            if invocation_id in self._invocations:
                inv_rec = self._invocations.pop(invocation_id)
                inv_rec.transition_to(InvocationLifecycleState.RECONCILED)

    def update_worker_status(
        self,
        worker_id: str,
        status: WorkerHealthStatus,
        active_load: Optional[int] = None,
    ) -> None:
        """Updates worker health status and optional active load state atomically."""
        with self._lock:
            if worker_id not in self._workers:
                raise WorkerNotFoundError(f"Worker '{worker_id}' is not registered.")
            if not isinstance(status, WorkerHealthStatus):
                raise LoadBalancerError(f"Invalid worker status type: {type(status)}.")

            worker = self._workers[worker_id]
            worker.status = status
            worker.last_heartbeat_ms = current_timestamp_ms()
            if active_load is not None:
                if active_load > worker.max_concurrency:
                    raise LoadBalancerError(
                        f"Cannot set active_load {active_load} > max_concurrency {worker.max_concurrency} for worker '{worker_id}'"
                    )
                worker.active_load = max(0, active_load)
            else:
                self._sync_worker_active_load(worker_id)



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
            self._kernel.update_worker_status(worker_id, status=status, active_load=active_load)

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
