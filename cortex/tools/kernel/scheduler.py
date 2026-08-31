"""
Phase 7.6: Resource-Aware Scheduler Engine
Normative Directive: Phase 7.6 Resource-Aware Scheduler Gate

Architectural Boundary:
    Scheduler = Placement Strategy (optimization layer)
    ResourceAuthority = Safety Constraint (authoritative reservation)
    WorkerSupervisor + Enforcement = Physical Execution Constraint

Invariants:
    1. Scheduler NEVER directly mutates authoritative resource accounting.
    2. Scheduler NEVER bypasses ResourceAuthority.reserve().
    3. Scheduler NEVER creates its own lease authority or manages cgroups.
    4. SchedulerDecision =/=> ReservationSuccess (until ResourceAuthority validates).
    5. Telemetry != Authority.
    6. For identical authoritative state and inputs: Schedule(S,I) = Schedule(S,I).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from cortex.tools.kernel.resource_authority import (
    DemandVector,
    GPUCollisionError,
    InsufficientCapacityError,
    InvalidFencingError,
    ReservationRecord,
    ReservationStatus,
    ResourceAuthority,
    WorkerLifecycleState,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

class SchedulerError(Exception):
    """Base exception for all scheduler errors."""
    pass


class NoFeasibleWorkerError(SchedulerError):
    """Raised when no worker passes the feasibility predicate F_i."""
    pass


class PlacementRejectedError(SchedulerError):
    """Raised when ResourceAuthority rejects the scheduler's placement proposal."""
    pass


class StaleSchedulingViewError(SchedulerError):
    """Raised when the scheduling read view is stale relative to authoritative state."""
    pass


# -----------------------------------------------------------------------------
# Telemetry Snapshot (Non-Authoritative)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkerTelemetry:
    """
    Non-authoritative observational snapshot of worker resource utilization.
    WARNING: Telemetry != Authority. Telemetry may influence R_sched but
    the final reservation decision must be validated atomically by ResourceAuthority.
    """
    worker_id: int
    cpu_used_mcores: int = 0
    memory_used_bytes: int = 0
    gpu_utilization_pct: float = 0.0
    active_task_count: int = 0
    last_heartbeat_ns: int = 0
    observed_latency_p50_us: int = 0
    observed_latency_p99_us: int = 0


# -----------------------------------------------------------------------------
# Worker Scheduling View (Read-Only Snapshot)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkerSchedulingView:
    """
    Immutable read-only snapshot of a worker's schedulable state.
    Combines authoritative registration data with non-authoritative telemetry.
    """
    worker_id: int
    generation: int
    state: WorkerLifecycleState
    capabilities: frozenset
    # Authoritative capacity bounds (from ResourceAuthority)
    total_cpu_mcores: int
    total_memory_bytes: int
    available_gpu_ids: Tuple[int, ...]
    # Non-authoritative telemetry observations (may be stale)
    telemetry: Optional[WorkerTelemetry] = None
    # Scheduling-derived residual capacity estimate R_sched
    residual_cpu_mcores: int = 0
    residual_memory_bytes: int = 0
    authority_epoch: int = 1
    lease_epoch: int = 1
    is_healthy: bool = True


# -----------------------------------------------------------------------------
# Cost Function & Tie-Breaking
# -----------------------------------------------------------------------------

class CostFunction(Enum):
    """Scheduling cost function selector."""
    LEAST_LOADED = auto()          # Minimize active task count
    BEST_FIT = auto()              # Minimize wasted residual capacity
    WORST_FIT = auto()             # Maximize residual capacity after placement
    ROUND_ROBIN = auto()           # Deterministic round-robin (stateful)


@dataclass(frozen=True)
class PlacementCost:
    """Deterministic cost tuple for worker placement ranking."""
    primary_cost: float            # Lower is better
    residual_cpu_mcores: int       # Tie-breaking: higher residual preferred
    worker_id: int                 # Final tie-breaking: lowest worker_id wins (deterministic)

    def __lt__(self, other: PlacementCost) -> bool:
        if self.primary_cost != other.primary_cost:
            return self.primary_cost < other.primary_cost
        if self.residual_cpu_mcores != other.residual_cpu_mcores:
            return self.residual_cpu_mcores > other.residual_cpu_mcores
        return self.worker_id < other.worker_id


# -----------------------------------------------------------------------------
# Scheduling Intent (Public API Input)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class SchedulingIntent:
    """
    Public-facing scheduling request. This is what a developer produces via
    @cortex.task(resources={...}).

    The scheduler normalizes this into a DemandVector and evaluates feasibility.
    """
    task_id: int
    invocation_id: int
    attempt_id: int
    demand_vector: DemandVector
    required_capabilities: frozenset = frozenset()
    affinity_worker_id: Optional[int] = None      # Soft preference, not a guarantee
    authority_epoch: int = 1
    lease_epoch: int = 1
    worker_generation: int = 1
    expiration_timestamp_ns: Optional[int] = None


# -----------------------------------------------------------------------------
# Scheduling Result
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class SchedulingResult:
    """Outcome of a scheduling decision."""
    intent: SchedulingIntent
    selected_worker_id: int
    feasible_set_size: int
    cost: PlacementCost
    reservation: Optional[ReservationRecord]
    scheduling_time_ns: int
    authority_validated: bool


# -----------------------------------------------------------------------------
# Phase 7.6 Resource-Aware Scheduler
# -----------------------------------------------------------------------------

class ResourceAwareScheduler:
    """
    Resource-Aware Scheduling Engine (Phase 7.6).

    Responsibilities:
        - Evaluate candidate workers
        - Filter infeasible candidates
        - Calculate placement cost
        - Select a worker
        - Request a reservation from ResourceAuthority

    Prohibitions:
        - NEVER directly mutates authoritative resource accounting
        - NEVER bypasses ResourceAuthority
        - NEVER creates its own lease authority
        - NEVER directly manages cgroups
        - NEVER terminates workers
        - NEVER maintains an independent resource authority
        - NEVER treats telemetry as authoritative state

    Architectural Sequence:
        Intent -> Demand normalization -> Candidate filtering -> Cost evaluation
        -> Placement proposal -> ResourceAuthority.reserve() -> EnforcementContract
        -> WorkerSupervisor -> Execution
    """

    def __init__(
        self,
        resource_authority: ResourceAuthority,
        cost_function: CostFunction = CostFunction.LEAST_LOADED,
        enable_vector_scheduling: bool = True,
    ) -> None:
        self._authority = resource_authority
        self._cost_function = cost_function
        self._enable_vector_scheduling = enable_vector_scheduling

        # Worker registry (authoritative metadata only, no resource mutation)
        self._workers: Dict[int, WorkerSchedulingView] = {}
        # Non-authoritative telemetry cache (observational only)
        self._telemetry: Dict[int, WorkerTelemetry] = {}

        # Round-robin state (deterministic, documented)
        self._rr_index: int = 0
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # Worker Registry (Read-Only Metadata)
    # -------------------------------------------------------------------------

    def register_worker(self, view: WorkerSchedulingView) -> None:
        """Registers a worker's scheduling metadata. Does NOT mutate ResourceAuthority."""
        with self._lock:
            self._workers[view.worker_id] = view

    def update_telemetry(self, telemetry: WorkerTelemetry) -> None:
        """Updates non-authoritative telemetry cache. Telemetry != Authority."""
        with self._lock:
            self._telemetry[telemetry.worker_id] = telemetry

    def unregister_worker(self, worker_id: int) -> None:
        """Removes a worker from the scheduling view. Does NOT mutate ResourceAuthority."""
        with self._lock:
            self._workers.pop(worker_id, None)
            self._telemetry.pop(worker_id, None)

    # -------------------------------------------------------------------------
    # Feasibility Predicate: F_i = {w in W | Feasible(i, w)}
    # -------------------------------------------------------------------------

    def _is_feasible(
        self,
        intent: SchedulingIntent,
        worker: WorkerSchedulingView,
    ) -> bool:
        """
        Feasible(i, w) <=>
            d_i <= R_w^sched
            AND Capability(i, w)
            AND Health(w)
            AND IncarnationValid(w)
            AND LeaseValid(i, w)
            AND AuthorityValid
        """
        # 1. Health check
        if not worker.is_healthy:
            return False

        # 2. Worker lifecycle state check (must be ACTIVE)
        if worker.state not in (WorkerLifecycleState.ACTIVE, WorkerLifecycleState.REGISTERING):
            return False

        # 3. Capability check
        if intent.required_capabilities and not intent.required_capabilities.issubset(worker.capabilities):
            return False

        # 4. Authority epoch validity
        if worker.authority_epoch != intent.authority_epoch:
            return False

        # 5. Incarnation / generation validity
        if worker.generation < intent.worker_generation:
            return False

        # 6. Resource vector feasibility: d_i <= R_w^sched
        dv = intent.demand_vector

        # CPU feasibility
        if dv.cpu_mcores > worker.residual_cpu_mcores:
            return False

        # Memory feasibility
        if dv.memory_bytes > worker.residual_memory_bytes:
            return False

        # GPU feasibility (discrete: requested GPUs must be available on this worker)
        if dv.gpu_devices:
            avail_set = set(worker.available_gpu_ids)
            for g in dv.gpu_devices:
                if g not in avail_set:
                    return False

        return True

    def compute_feasible_set(
        self,
        intent: SchedulingIntent,
    ) -> List[WorkerSchedulingView]:
        """
        Computes F_i = {w in W | Feasible(i, w)}.
        Feasibility is evaluated BEFORE optimization.
        """
        with self._lock:
            feasible: List[WorkerSchedulingView] = []
            for worker in self._workers.values():
                if self._is_feasible(intent, worker):
                    feasible.append(worker)
            return feasible

    # -------------------------------------------------------------------------
    # Cost Evaluation: w* = argmin_{w in F_i} Cost(i, w)
    # -------------------------------------------------------------------------

    def _compute_cost(
        self,
        intent: SchedulingIntent,
        worker: WorkerSchedulingView,
    ) -> PlacementCost:
        """
        Computes placement cost for a feasible worker.
        The optimization function NEVER selects an infeasible worker.

        Tie-breaking rule (documented):
            1. Primary cost (function-specific, lower is better)
            2. Residual CPU after placement (higher is better)
            3. Worker ID (lower is better, deterministic)
        """
        dv = intent.demand_vector
        telemetry = self._telemetry.get(worker.worker_id)

        if self._cost_function == CostFunction.LEAST_LOADED:
            active_tasks = telemetry.active_task_count if telemetry else 0
            primary = float(active_tasks)

        elif self._cost_function == CostFunction.BEST_FIT:
            # Minimize wasted residual capacity after placement
            residual_after = worker.residual_cpu_mcores - dv.cpu_mcores
            primary = float(residual_after)

        elif self._cost_function == CostFunction.WORST_FIT:
            # Maximize residual capacity after placement (negative for argmin)
            residual_after = worker.residual_cpu_mcores - dv.cpu_mcores
            primary = -float(residual_after)

        elif self._cost_function == CostFunction.ROUND_ROBIN:
            # Deterministic round-robin: use worker index position as cost
            worker_ids = sorted(self._workers.keys())
            try:
                idx = worker_ids.index(worker.worker_id)
            except ValueError:
                idx = 0
            # Cost is distance from current RR pointer
            primary = float((idx - self._rr_index) % len(worker_ids)) if worker_ids else 0.0

        else:
            primary = 0.0

        residual_cpu = worker.residual_cpu_mcores - dv.cpu_mcores

        return PlacementCost(
            primary_cost=primary,
            residual_cpu_mcores=residual_cpu,
            worker_id=worker.worker_id,
        )

    def select_worker(
        self,
        intent: SchedulingIntent,
    ) -> Tuple[WorkerSchedulingView, PlacementCost]:
        """
        Selects the optimal worker from the feasible set.

        1. Compute F_i (feasibility)
        2. Compute Cost(i, w) for each w in F_i
        3. Return w* = argmin Cost(i, w)

        Raises NoFeasibleWorkerError if F_i is empty.
        """
        feasible = self.compute_feasible_set(intent)
        if not feasible:
            raise NoFeasibleWorkerError(
                f"No feasible worker for intent task_id={intent.task_id}: "
                f"demand_vector={intent.demand_vector}, "
                f"required_capabilities={intent.required_capabilities}"
            )

        # Compute costs and select argmin
        costs: List[Tuple[PlacementCost, WorkerSchedulingView]] = []
        for w in feasible:
            cost = self._compute_cost(intent, w)
            costs.append((cost, w))

        costs.sort(key=lambda x: x[0])
        best_cost, best_worker = costs[0]

        # Advance round-robin pointer if applicable
        if self._cost_function == CostFunction.ROUND_ROBIN:
            worker_ids = sorted(self._workers.keys())
            try:
                idx = worker_ids.index(best_worker.worker_id)
                self._rr_index = (idx + 1) % len(worker_ids) if worker_ids else 0
            except ValueError:
                pass

        return best_worker, best_cost

    # -------------------------------------------------------------------------
    # Complete Scheduling Pipeline
    # -------------------------------------------------------------------------

    def schedule(
        self,
        intent: SchedulingIntent,
    ) -> SchedulingResult:
        """
        Executes the full scheduling pipeline:

            Intent
              -> Demand normalization
              -> Candidate filtering (feasibility)
              -> Cost evaluation
              -> Placement proposal
              -> ResourceAuthority.reserve()  [AUTHORITATIVE LINEARIZATION POINT]
              -> SchedulingResult

        There is NO path: Scheduler -> direct resource mutation.
        SchedulerDecision =/=> ReservationSuccess until ResourceAuthority validates.
        """
        start_ns = time.time_ns()

        with self._lock:
            # Step 1-3: Feasibility + Selection
            selected_worker, cost = self.select_worker(intent)
            feasible_set = self.compute_feasible_set(intent)

        # Step 4-5: Placement Proposal -> ResourceAuthority.reserve()
        # This is the AUTHORITATIVE LINEARIZATION POINT.
        # The scheduler does NOT directly mutate resource accounting.
        try:
            reservation = self._authority.reserve(
                res_id=intent.task_id,
                res_inv=intent.invocation_id,
                res_att=intent.attempt_id,
                res_worker=selected_worker.worker_id,
                demand_vector=intent.demand_vector,
                authority_epoch=intent.authority_epoch,
                lease_epoch=intent.lease_epoch,
                worker_generation=selected_worker.generation,
                expiration_timestamp_ns=intent.expiration_timestamp_ns,
            )
            authority_validated = True
        except (InsufficientCapacityError, GPUCollisionError, InvalidFencingError) as e:
            # ResourceAuthority rejected the placement.
            # SchedulerDecision =/=> ReservationSuccess.
            raise PlacementRejectedError(
                f"ResourceAuthority rejected placement of task {intent.task_id} "
                f"on worker {selected_worker.worker_id}: {e}"
            ) from e

        elapsed_ns = time.time_ns() - start_ns

        return SchedulingResult(
            intent=intent,
            selected_worker_id=selected_worker.worker_id,
            feasible_set_size=len(feasible_set),
            cost=cost,
            reservation=reservation,
            scheduling_time_ns=elapsed_ns,
            authority_validated=authority_validated,
        )

    # -------------------------------------------------------------------------
    # Scalar Fallback Path (Backward Compatibility)
    # -------------------------------------------------------------------------

    def schedule_scalar(
        self,
        task_id: int,
        invocation_id: int,
        attempt_id: int,
        cpu_demand: int,
        required_capabilities: Optional[Set[str]] = None,
        authority_epoch: int = 1,
        lease_epoch: int = 1,
        worker_generation: int = 1,
    ) -> SchedulingResult:
        """
        Scalar scheduling fallback. Uses single CPU millicores dimension.
        Existing scalar scheduling behavior remains available as the fallback path.
        """
        intent = SchedulingIntent(
            task_id=task_id,
            invocation_id=invocation_id,
            attempt_id=attempt_id,
            demand_vector=DemandVector(cpu_mcores=cpu_demand),
            required_capabilities=frozenset(required_capabilities or set()),
            authority_epoch=authority_epoch,
            lease_epoch=lease_epoch,
            worker_generation=worker_generation,
        )
        return self.schedule(intent)
