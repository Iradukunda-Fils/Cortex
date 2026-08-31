"""
Phase 7.7a: Heterogeneous Distributed Placement Engine
Normative Specification: Research Note 23 / Directive Phase 7.7a

Architectural Boundaries:
    DistributedScheduler = Multi-node placement strategy & locality optimization layer
    ResourceAuthority = Authoritative reservation & safety invariant gate
    WorkerSupervisor = Physical container execution enforcement (cgroup v2)

Globally Unique Identity Governance:
    GPUIdentity = (NodeID, GPUID, PartitionID?)
    WorkerIdentity = (NodeID, WorkerID, Generation)

Invariants:
    1. DistributedScheduler NEVER mutates authoritative resource accounting directly.
    2. DistributedScheduler NEVER bypasses ResourceAuthority.reserve().
    3. PlacementProposal =/=> ReservationSuccess until ResourceAuthority validates.
    4. Multi-node resource fragmentation is detected explicitly.
    5. Local IDs are strictly prohibited as global identities.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from cortex.tools.kernel.resource_authority import (
    DemandVector,
    GPUCollisionError,
    InsufficientCapacityError,
    InvalidFencingError,
    ReservationRecord,
    ResourceAuthority,
    WorkerLifecycleState,
)
from cortex.tools.kernel.scheduler import (
    CostFunction,
    NoFeasibleWorkerError,
    PlacementRejectedError,
    SchedulingIntent,
    WorkerTelemetry,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Globally Unique Identities
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class GlobalGPUIdentity:
    """
    Globally Unique GPU Identity: (NodeID, GPUID, PartitionID?).
    Prevents global namespace collisions across multi-node topologies.
    """

    node_id: str
    gpu_id: int
    partition_id: Optional[int] = None

    def __str__(self) -> str:
        if self.partition_id is not None:
            return f"gpu:{self.node_id}:{self.gpu_id}:p{self.partition_id}"
        return f"gpu:{self.node_id}:{self.gpu_id}"


@dataclass(frozen=True)
class GlobalWorkerIdentity:
    """
    Globally Unique Worker Identity: (NodeID, WorkerID, Generation).
    Eliminates node-local worker ID collisions.
    """

    node_id: str
    worker_id: int
    generation: int

    def __str__(self) -> str:
        return f"worker:{self.node_id}:{self.worker_id}:g{self.generation}"


# -----------------------------------------------------------------------------
# Multi-Node Worker Scheduling View
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class DistributedWorkerView:
    """
    Immutable read-only view of a distributed worker node.
    Combines authoritative registration data with topology & locality metadata.
    """

    identity: GlobalWorkerIdentity
    state: WorkerLifecycleState
    capabilities: frozenset
    total_capacity: DemandVector
    residual_capacity: DemandVector
    available_gpus: Tuple[GlobalGPUIdentity, ...]
    node_region: str = "default-region"
    numa_zone: int = 0
    authority_epoch: int = 1
    lease_epoch: int = 1
    is_healthy: bool = True
    telemetry: Optional[WorkerTelemetry] = None


# -----------------------------------------------------------------------------
# Distributed Placement Exceptions
# -----------------------------------------------------------------------------


class ResourceFragmentationError(Exception):
    """Raised when cluster aggregate capacity is sufficient, but no single node satisfies demand."""

    pass


# -----------------------------------------------------------------------------
# Distributed Cost Ranking
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class DistributedPlacementCost:
    """
    Deterministic cost tuple for multi-node placement ranking.
    Ordering:
        1. Locality penalty (0 = local/preferred region, 100 = cross-region)
        2. Primary cost (strategy dependent, e.g. active tasks)
        3. Residual CPU millicores (higher is better)
        4. Global worker identity string (lexicographical tie-breaking)
    """

    locality_penalty: float
    primary_cost: float
    residual_cpu_mcores: int
    worker_identity_str: str

    def __lt__(self, other: DistributedPlacementCost) -> bool:
        if self.locality_penalty != other.locality_penalty:
            return self.locality_penalty < other.locality_penalty
        if self.primary_cost != other.primary_cost:
            return self.primary_cost < other.primary_cost
        if self.residual_cpu_mcores != other.residual_cpu_mcores:
            return self.residual_cpu_mcores > other.residual_cpu_mcores
        return self.worker_identity_str < other.worker_identity_str


# -----------------------------------------------------------------------------
# Phase 7.7a Distributed Placement Engine
# -----------------------------------------------------------------------------


class DistributedPlacementEngine:
    """
    Heterogeneous Distributed Placement Engine (Phase 7.7a).

    Responsibilities:
        - Multi-node candidate discovery & feasibility filtering
        - Explicit detection of multi-node resource fragmentation
        - Locality and topology-aware placement optimization
        - Stale-state race detection and atomic reservation retry
    """

    def __init__(
        self,
        node_authorities: Dict[str, ResourceAuthority],
        cost_function: CostFunction = CostFunction.LEAST_LOADED,
        default_region: str = "default-region",
    ) -> None:
        self._authorities = dict(node_authorities)  # NodeID -> ResourceAuthority
        self._cost_function = cost_function
        self._default_region = default_region
        self._workers: Dict[GlobalWorkerIdentity, DistributedWorkerView] = {}
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # Worker Registry Management
    # -------------------------------------------------------------------------

    def register_worker(self, view: DistributedWorkerView) -> None:
        """Registers a worker view into the distributed scheduling pool."""
        with self._lock:
            self._workers[view.identity] = view

    def unregister_worker(self, identity: GlobalWorkerIdentity) -> None:
        """Removes a worker view from the distributed pool."""
        with self._lock:
            self._workers.pop(identity, None)

    # -------------------------------------------------------------------------
    # Multi-Node Resource Fragmentation Detection
    # -------------------------------------------------------------------------

    def check_resource_fragmentation(self, demand: DemandVector) -> bool:
        """
        Detects if multi-node resource fragmentation exists:
            sum(R_w) >= demand AND (forall w: demand > R_w)

        Returns True if cluster total resources could theoretically fit demand,
        but no single worker node possesses sufficient contiguous capacity.
        """
        with self._lock:
            if not self._workers:
                return False

            total_cpu = sum(w.residual_capacity.cpu_mcores for w in self._workers.values() if w.is_healthy)
            total_mem = sum(w.residual_capacity.memory_bytes for w in self._workers.values() if w.is_healthy)

            aggregate_sufficient = total_cpu >= demand.cpu_mcores and total_mem >= demand.memory_bytes

            if not aggregate_sufficient:
                return False

            # Check if any single worker satisfies the vector demand
            has_fitting_worker = any(
                w.residual_capacity.cpu_mcores >= demand.cpu_mcores
                and w.residual_capacity.memory_bytes >= demand.memory_bytes
                and w.is_healthy
                and w.state in (WorkerLifecycleState.ACTIVE, WorkerLifecycleState.REGISTERING)
                for w in self._workers.values()
            )

            return not has_fitting_worker

    # -------------------------------------------------------------------------
    # Feasibility Predicate F_i
    # -------------------------------------------------------------------------

    def _is_feasible(
        self,
        intent: SchedulingIntent,
        worker: DistributedWorkerView,
    ) -> bool:
        """Evaluates authoritative feasibility predicate F_i for multi-node worker."""
        if not worker.is_healthy:
            return False

        if worker.state not in (WorkerLifecycleState.ACTIVE, WorkerLifecycleState.REGISTERING):
            return False

        if intent.required_capabilities and not intent.required_capabilities.issubset(worker.capabilities):
            return False

        if worker.authority_epoch != intent.authority_epoch:
            return False

        if worker.identity.generation < intent.worker_generation:
            return False

        dv = intent.demand_vector

        if dv.cpu_mcores > worker.residual_capacity.cpu_mcores:
            return False

        if dv.memory_bytes > worker.residual_capacity.memory_bytes:
            return False

        if dv.gpu_devices:
            # Match requested GPU IDs against worker available global GPU set
            avail_ids = {g.gpu_id for g in worker.available_gpus}
            for g_req in dv.gpu_devices:
                if g_req not in avail_ids:
                    return False

        return True

    def compute_feasible_set(
        self,
        intent: SchedulingIntent,
    ) -> List[DistributedWorkerView]:
        """Computes F_i = {w in W | Feasible(i, w)} across all nodes."""
        with self._lock:
            feasible: List[DistributedWorkerView] = []
            for w in self._workers.values():
                if self._is_feasible(intent, w):
                    feasible.append(w)
            return feasible

    # -------------------------------------------------------------------------
    # Locality & Cost Evaluation
    # -------------------------------------------------------------------------

    def _compute_cost(
        self,
        intent: SchedulingIntent,
        worker: DistributedWorkerView,
        target_region: Optional[str] = None,
    ) -> DistributedPlacementCost:
        """Computes locality-aware placement cost with deterministic tie-breaking."""
        # Locality penalty
        preferred_region = target_region or self._default_region
        locality_penalty = 0.0 if worker.node_region == preferred_region else 100.0

        # Primary load cost
        active_tasks = worker.telemetry.active_task_count if worker.telemetry else 0
        primary_cost = float(active_tasks)

        residual_cpu = worker.residual_capacity.cpu_mcores - intent.demand_vector.cpu_mcores

        return DistributedPlacementCost(
            locality_penalty=locality_penalty,
            primary_cost=primary_cost,
            residual_cpu_mcores=residual_cpu,
            worker_identity_str=str(worker.identity),
        )

    def select_worker(
        self,
        intent: SchedulingIntent,
        target_region: Optional[str] = None,
    ) -> Tuple[DistributedWorkerView, DistributedPlacementCost]:
        """Selects w* = argmin_{w in F_i} Cost(i, w)."""
        feasible = self.compute_feasible_set(intent)

        if not feasible:
            # Check if failure is due to resource fragmentation
            if self.check_resource_fragmentation(intent.demand_vector):
                raise ResourceFragmentationError(
                    f"Cluster aggregate capacity exists, but no single node satisfies vector demand: "
                    f"{intent.demand_vector}"
                )
            raise NoFeasibleWorkerError(
                f"No feasible distributed worker for intent task_id={intent.task_id}: {intent.demand_vector}"
            )

        costs: List[Tuple[DistributedPlacementCost, DistributedWorkerView]] = []
        for w in feasible:
            cost = self._compute_cost(intent, w, target_region)
            costs.append((cost, w))

        costs.sort(key=lambda x: x[0])
        return costs[0][1], costs[0][0]

    # -------------------------------------------------------------------------
    # Atomic Placement & Stale-Read Retry Pipeline
    # -------------------------------------------------------------------------

    def schedule_distributed(
        self,
        intent: SchedulingIntent,
        target_region: Optional[str] = None,
        max_retries: int = 3,
    ) -> Tuple[DistributedWorkerView, ReservationRecord]:
        """
        Executes distributed placement with stale-read retry engine:

        1. Discover candidates & calculate optimal candidate w*
        2. Submit proposal to node ResourceAuthority.reserve()
        3. If ResourceAuthority rejects due to concurrent commit or stale telemetry,
           retry selection excluding the failed candidate up to max_retries.

        Guarantees PlacementProposal =/=> ReservationSuccess without overcommit.
        """
        last_exception: Optional[Exception] = None
        excluded_identities: Set[GlobalWorkerIdentity] = set()

        for attempt in range(max_retries):
            with self._lock:
                feasible = [w for w in self.compute_feasible_set(intent) if w.identity not in excluded_identities]
                if not feasible:
                    break
                costs = [(self._compute_cost(intent, w, target_region), w) for w in feasible]
                costs.sort(key=lambda x: x[0])
                selected_worker = costs[0][1]

            node_id = selected_worker.identity.node_id
            auth = self._authorities.get(node_id)
            if not auth:
                raise KeyError(f"No ResourceAuthority registered for node {node_id}")

            try:
                # Atomic linearizable reservation validation at node ResourceAuthority
                reservation = auth.reserve(
                    res_id=intent.task_id,
                    res_inv=intent.invocation_id,
                    res_att=intent.attempt_id,
                    res_worker=selected_worker.identity.worker_id,
                    demand_vector=intent.demand_vector,
                    authority_epoch=intent.authority_epoch,
                    lease_epoch=intent.lease_epoch,
                    worker_generation=selected_worker.identity.generation,
                    expiration_timestamp_ns=intent.expiration_timestamp_ns,
                )
                return selected_worker, reservation

            except (InsufficientCapacityError, GPUCollisionError, InvalidFencingError) as e:
                # Stale-read detected! Node authority rejected proposal.
                logger.warning(
                    f"Stale placement proposal attempt {attempt + 1}/{max_retries} "
                    f"rejected for worker {selected_worker.identity}: {e}"
                )
                last_exception = e
                excluded_identities.add(selected_worker.identity)
                time.sleep(0.01)

        raise PlacementRejectedError(
            f"Distributed placement rejected after {max_retries} attempts: {last_exception}"
        ) from last_exception
