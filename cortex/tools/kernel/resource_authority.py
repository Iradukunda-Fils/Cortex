"""
Phase 7.3: Concrete Python Resource Authority & Scaling Lifecycle Engine
Normative Refinement Specification: Research Note 21 / Directive Phase 7.3
Refinement Certificate Version: RCA-7.3-v1

Formal Refinement Mapping:
    c in C_Python <--- alpha ---> a in A_Coq (Phase7Reservation.v)
    R(c, a) <==> alpha(c) = a and Invariant(a)
    R(c, a) and c --op--> c' ==> A --op*--> A' and R(c', a')

Governance Domains:
    Telemetry != Authority != Enforcement != Execution
    Declaration != LiveAuthority

Authoritative State (S_R):
    _reservations, _used_capacity, _quarantine, _authority_epoch,
    _lease_epochs, _worker_generations, _gpu_owners, _worker_states, _retired_tombstones
"""

from __future__ import annotations

import heapq
import logging
import os
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------


class RefinementCertificateError(Exception):
    """Raised when authoritative state schema changes without updating RCA-7.3 certificate."""

    pass


class InvalidFencingError(Exception):
    """Raised when an operation fails authority epoch, lease epoch, or generation fencing."""

    pass


class InsufficientCapacityError(Exception):
    """Raised when resource request exceeds schedulable available capacity (Proof P2)."""

    pass


class UniquenessViolationError(Exception):
    """Raised when invocation or attempt uniqueness is violated (Proof P1a/P1b/P12)."""

    pass


class GPUCollisionError(Exception):
    """Raised when attempting to reserve an already owned exclusive GPU (Proof P11)."""

    pass


class InvalidStateTransitionError(Exception):
    """Raised when an invalid lifecycle transition is attempted."""

    pass


class DeclarativeSchemaValidationError(Exception):
    """Raised when a declarative resource policy fails schema validation."""

    pass


class WorkerNotQuiescentError(Exception):
    """Raised when attempting to retire a worker that still has active assignments or reservations."""

    pass


# -----------------------------------------------------------------------------
# Declarative Resource Policy & Unit Normalization
# -----------------------------------------------------------------------------


class FieldClassification(Enum):
    AUTHORITATIVE = auto()
    POLICY = auto()
    DERIVED = auto()
    OBSERVATION = auto()
    EXECUTION = auto()
    TELEMETRY = auto()


@dataclass(frozen=True)
class NormalizedResourceLimits:
    cpu_mcores: int  # Millicores (1 core = 1000 mcores)
    memory_bytes: int  # Bytes (1 GiB = 1073741824 B)
    gpu_devices: Tuple[int, ...]
    vram_bytes: int
    io_capacity: int
    network_mbps: int
    fd_capacity: int
    thread_capacity: int
    storage_bytes: int


@dataclass(frozen=True)
class DemandVector:
    """
    Concrete Heterogeneous Resource Demand Vector.
    Domains:
      - Additive: cpu_mcores, memory_bytes, vram_bytes, fd_capacity, thread_capacity, storage_bytes
      - Rate-based: io_capacity, network_mbps
      - Discrete: gpu_devices (tuple of exclusive GPU IDs)
    """

    cpu_mcores: int = 0
    memory_bytes: int = 0
    gpu_devices: Tuple[int, ...] = ()
    vram_bytes: int = 0
    io_capacity: int = 0
    network_mbps: int = 0
    fd_capacity: int = 0
    thread_capacity: int = 0
    storage_bytes: int = 0

    def is_zero(self) -> bool:
        return (
            self.cpu_mcores == 0
            and self.memory_bytes == 0
            and len(self.gpu_devices) == 0
            and self.vram_bytes == 0
            and self.io_capacity == 0
            and self.network_mbps == 0
            and self.fd_capacity == 0
            and self.thread_capacity == 0
            and self.storage_bytes == 0
        )

    def __add__(self, other: DemandVector) -> DemandVector:
        gpu_combined = tuple(sorted(set(self.gpu_devices).union(other.gpu_devices)))
        return DemandVector(
            cpu_mcores=self.cpu_mcores + other.cpu_mcores,
            memory_bytes=self.memory_bytes + other.memory_bytes,
            gpu_devices=gpu_combined,
            vram_bytes=self.vram_bytes + other.vram_bytes,
            io_capacity=self.io_capacity + other.io_capacity,
            network_mbps=self.network_mbps + other.network_mbps,
            fd_capacity=self.fd_capacity + other.fd_capacity,
            thread_capacity=self.thread_capacity + other.thread_capacity,
            storage_bytes=self.storage_bytes + other.storage_bytes,
        )

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> DemandVector:
        """
        Parses and normalizes a human-friendly resource declaration dictionary.
        Supports inputs like:
          {"cpu": "4", "memory": "8GiB", "gpu": 1, "vram": "12GiB", "network": "100Mbps"}
        """
        if not raw:
            return DemandVector()

        cpu_val = raw.get("cpu", raw.get("cpu_mcores", 0))
        cpu_mcores = parse_resource_unit(cpu_val, default_unit="cpu")

        mem_val = raw.get("memory", raw.get("ram", raw.get("memory_bytes", 0)))
        mem_bytes = parse_resource_unit(mem_val, default_unit="memory")

        gpu_val = raw.get("gpu", raw.get("gpus", ()))
        if isinstance(gpu_val, int):
            gpu_devs = (gpu_val,) if gpu_val >= 0 else ()
        elif isinstance(gpu_val, (list, tuple)):
            gpu_devs = tuple(sorted(int(x) for x in gpu_val))
        else:
            gpu_devs = ()

        vram_val = raw.get("vram", raw.get("vram_bytes", 0))
        vram_bytes = parse_resource_unit(vram_val, default_unit="memory")

        io_val = raw.get("io", raw.get("io_capacity", 0))
        io_cap = parse_resource_unit(io_val, default_unit="network")

        net_val = raw.get("network", raw.get("network_mbps", 0))
        net_mbps = parse_resource_unit(net_val, default_unit="network")

        fd_val = raw.get("fd", raw.get("file_descriptors", 0))
        fd_cap = int(fd_val) if fd_val is not None else 0

        thr_val = raw.get("threads", 0)
        thr_cap = int(thr_val) if thr_val is not None else 0

        stor_val = raw.get("storage", 0)
        stor_bytes = parse_resource_unit(stor_val, default_unit="memory")

        return DemandVector(
            cpu_mcores=cpu_mcores,
            memory_bytes=mem_bytes,
            gpu_devices=gpu_devs,
            vram_bytes=vram_bytes,
            io_capacity=io_cap,
            network_mbps=net_mbps,
            fd_capacity=fd_cap,
            thread_capacity=thr_cap,
            storage_bytes=stor_bytes,
        )


def discover_physical_capacity() -> Tuple[int, int]:
    """
    Discovers physical host hardware capacity (CPU millicores, Memory bytes).
    Queries cgroups (/sys/fs/cgroup/cpu.max) and OS primitives (os.cpu_count()).
    Enforces principle: Unknown physical capacity != arbitrary default capacity.
    """
    discovered_cpu_cores: float = float(os.cpu_count() or 1)

    cgroup2_path = "/sys/fs/cgroup/cpu.max"
    if os.path.exists(cgroup2_path):
        try:
            with open(cgroup2_path, "r") as f:
                parts = f.read().strip().split()
                if len(parts) == 2 and parts[0] != "max":
                    quota, period = float(parts[0]), float(parts[1])
                    if period > 0:
                        discovered_cpu_cores = quota / period
        except Exception:
            pass

    cpu_mcores = int(discovered_cpu_cores * 1000)

    memory_bytes = 1024 * 1024 * 1024  # 1 GiB fallback
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_size > 0:
            memory_bytes = pages * page_size
    except Exception:
        pass

    return cpu_mcores, memory_bytes


def parse_resource_unit(val: Any, default_unit: str = "cpu") -> int:
    """
    Normalizes human-friendly resource strings ("4GiB", "2500m", "16cores", "2", "100Mbps")
    into exact base integer quantities.
    """
    if isinstance(val, (int, float)):
        if default_unit == "cpu":
            return int(val * 1000)
        return int(val)

    val_str = str(val).strip()
    if not val_str:
        return 0

    if val_str.endswith("GiB") or val_str.endswith("GB"):
        num_str = val_str[:-3].strip() if val_str.endswith("GiB") else val_str[:-2].strip()
        return int(float(num_str) * 1024 * 1024 * 1024)
    elif val_str.endswith("MiB") or val_str.endswith("MB"):
        num_str = val_str[:-3].strip() if val_str.endswith("MiB") else val_str[:-2].strip()
        return int(float(num_str) * 1024 * 1024)
    elif val_str.endswith("KiB") or val_str.endswith("KB"):
        num_str = val_str[:-3].strip() if val_str.endswith("KiB") else val_str[:-2].strip()
        return int(float(num_str) * 1024)
    elif val_str.endswith("B"):
        return int(float(val_str[:-1].strip()))
    elif val_str.endswith("mcores"):
        return int(float(val_str[:-6].strip()))
    elif val_str.endswith("cores"):
        return int(float(val_str[:-5].strip()) * 1000)
    elif val_str.endswith("m"):
        return int(float(val_str[:-1].strip()))
    elif val_str.endswith("Gbps"):
        return int(float(val_str[:-4].strip()) * 1000)
    elif val_str.endswith("Mbps"):
        return int(float(val_str[:-4].strip()))

    try:
        fval = float(val_str)
        return int(fval * 1000) if default_unit == "cpu" else int(fval)
    except ValueError:
        raise ValueError(f"Unrecognized resource unit format: {val}")


@dataclass(frozen=True)
class DeclarativeResourcePolicy:
    schema_name: str
    schema_version: str
    limits: NormalizedResourceLimits
    memory_margin_bytes: int
    vram_margin_bytes: int
    fd_margin: int
    telemetry_uncertainty: float
    max_active_reservations: int
    reservation_ttl_sec: float
    max_worker_concurrency: int
    drain_timeout_sec: float

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> DeclarativeResourcePolicy:
        """Parses and normalizes a raw dictionary against the declarative policy schema."""
        try:
            schema_info = raw.get("schema", {})
            if schema_info.get("name") != "cortex-resource-policy" or schema_info.get("version") != "1":
                raise DeclarativeSchemaValidationError("Invalid schema name or version")

            prof = raw.get("resource_profile", {})
            cpu_cfg = prof.get("cpu", {})
            cpu_val = (
                f"{cpu_cfg.get('capacity', 0)}{cpu_cfg.get('unit', '')}"
                if "unit" in cpu_cfg
                else cpu_cfg.get("capacity", 0)
            )
            cpu_mcores = parse_resource_unit(cpu_val, default_unit="cpu")

            mem_cfg = prof.get("memory", {})
            mem_val = (
                f"{mem_cfg.get('capacity', 0)}{mem_cfg.get('unit', '')}"
                if "unit" in mem_cfg
                else mem_cfg.get("capacity", 0)
            )
            mem_bytes = parse_resource_unit(mem_val, default_unit="memory")

            gpu_cfg = prof.get("gpu", {})
            gpu_devs = tuple(sorted(gpu_cfg.get("devices", [])))

            vram_cfg = prof.get("vram", {})
            vram_val = (
                f"{vram_cfg.get('capacity', 0)}{vram_cfg.get('unit', '')}"
                if "unit" in vram_cfg
                else vram_cfg.get("capacity", 0)
            )
            vram_bytes = parse_resource_unit(vram_val, default_unit="memory")

            io_cfg = prof.get("io", {})
            io_cap = int(io_cfg.get("capacity", 0))

            net_cfg = prof.get("network", {})
            net_val = (
                f"{net_cfg.get('capacity', 0)}{net_cfg.get('unit', '')}"
                if "unit" in net_cfg
                else net_cfg.get("capacity", 0)
            )
            net_mbps = parse_resource_unit(net_val, default_unit="network")

            fd_cfg = prof.get("file_descriptors", {})
            fd_cap = int(fd_cfg.get("capacity", 4096))

            thr_cfg = prof.get("threads", {})
            thr_cap = int(thr_cfg.get("capacity", 1024))

            stor_cfg = prof.get("storage", {})
            stor_val = (
                f"{stor_cfg.get('capacity', 0)}{stor_cfg.get('unit', '')}"
                if "unit" in stor_cfg
                else stor_cfg.get("capacity", 0)
            )
            stor_bytes = parse_resource_unit(stor_val, default_unit="memory")

            limits = NormalizedResourceLimits(
                cpu_mcores=cpu_mcores,
                memory_bytes=mem_bytes,
                gpu_devices=gpu_devs,
                vram_bytes=vram_bytes,
                io_capacity=io_cap,
                network_mbps=net_mbps,
                fd_capacity=fd_cap,
                thread_capacity=thr_cap,
                storage_bytes=stor_bytes,
            )

            safety = raw.get("safety", {})
            mem_margin_bytes = parse_resource_unit(safety.get("memory_margin", 0), default_unit="memory")
            vram_margin_bytes = parse_resource_unit(safety.get("vram_margin", 0), default_unit="memory")
            fd_margin = int(safety.get("fd_margin", 0))
            uncertainty = float(safety.get("telemetry_uncertainty", 0.0))

            res_cfg = raw.get("reservation", {})
            max_act = int(res_cfg.get("max_active", 1000))
            ttl = float(res_cfg.get("ttl", 60.0))

            wrk_cfg = raw.get("worker", {})
            max_conc = int(wrk_cfg.get("max_concurrency", 8))
            drain_to = float(wrk_cfg.get("drain_timeout", 30.0))

            return DeclarativeResourcePolicy(
                schema_name=schema_info["name"],
                schema_version=schema_info["version"],
                limits=limits,
                memory_margin_bytes=mem_margin_bytes,
                vram_margin_bytes=vram_margin_bytes,
                fd_margin=fd_margin,
                telemetry_uncertainty=uncertainty,
                max_active_reservations=max_act,
                reservation_ttl_sec=ttl,
                max_worker_concurrency=max_conc,
                drain_timeout_sec=drain_to,
            )
        except Exception as e:
            if isinstance(e, DeclarativeSchemaValidationError):
                raise
            raise DeclarativeSchemaValidationError(f"Declarative policy parsing failed: {e}") from e


# -----------------------------------------------------------------------------
# FSM State & Status Enums
# -----------------------------------------------------------------------------


class ReservationStatus(Enum):
    PENDING = auto()
    ACTIVE = auto()
    RELEASED = auto()
    EXPIRED = auto()
    REVOKED = auto()

    def is_active(self) -> bool:
        return self == ReservationStatus.ACTIVE or self == ReservationStatus.PENDING


class WorkerLifecycleState(Enum):
    REGISTERING = auto()
    ACTIVE = auto()
    DRAINING = auto()
    QUIESCENT = auto()
    FENCED = auto()
    RETIRED = auto()


@dataclass
class ReservationRecord:
    res_id: int
    res_inv: int
    res_att: int
    res_worker: int
    res_demand: int  # CPU millicores (backwards compatible)
    res_authority_epoch: int
    res_lease_epoch: int
    res_generation: int
    res_status: ReservationStatus = ReservationStatus.PENDING
    generation_id: int = 1
    expiration_timestamp_ns: Optional[int] = None
    demand_vector: Optional[DemandVector] = None

    def get_effective_demand_vector(self) -> DemandVector:
        """Returns effective DemandVector, auto-constructing from res_demand if None."""
        if self.demand_vector is not None:
            return self.demand_vector
        return DemandVector(cpu_mcores=self.res_demand)

    def to_enforcement_contract(self, require_physical_enforcement: bool = True):
        """
        Derives an immutable EnforcementContract for physical worker execution (Gate A).
        ResourceAuthority -> ReservationRecord -> EnforcementContract -> WorkerSupervisor -> Cgroup.
        """
        from cortex.tools.kernel.enforcement.contract import EnforcementContract

        vec = self.get_effective_demand_vector()
        return EnforcementContract(
            reservation_id=self.res_id,
            worker_id=self.res_worker,
            cpu_mcores=vec.cpu_mcores,
            memory_bytes=vec.memory_bytes,
            pids_max=vec.thread_capacity if vec.thread_capacity > 0 else 1024,
            require_physical_enforcement=require_physical_enforcement,
        )


@dataclass
class WorkerScalingRecord:
    worker_id: int
    generation: int
    state: WorkerLifecycleState
    active_assignments_count: int = 0
    capabilities: Set[str] = field(default_factory=set)


@dataclass(frozen=True)
class AbstractReservationState:
    """Coq-equivalent abstract reservation state S_R."""

    rs_reservations: Tuple[ReservationRecord, ...]
    rs_capacity: int
    rs_used_capacity: int
    rs_safety_margin: int
    rs_uncertainty: int
    rs_authority_epoch: int
    rs_lease_epochs: Tuple[Tuple[int, int], ...]
    rs_generations: Tuple[Tuple[int, int], ...]
    rs_gpu_owners: Tuple[Tuple[int, int], ...]


# -----------------------------------------------------------------------------
# Core Authoritative Resource Kernel
# -----------------------------------------------------------------------------


class ResourceAuthority:
    """
    Authoritative Resource Kernel (Phase 7.3 Concrete Refinement Engine).
    Thread-safe implementation enforcing formal linearizable transitions.
    """

    REFINEMENT_CERTIFICATE_VERSION: str = "RCA-7.3-v1"

    def __init__(
        self,
        capacity: Optional[int] = None,
        safety_margin: int = 50,
        uncertainty: int = 50,
        authority_epoch: int = 1,
        declarative_policy: Optional[DeclarativeResourcePolicy] = None,
        use_min_heap_expiration: bool = False,
        use_batched_sweep: bool = True,
    ) -> None:
        self._lock = threading.RLock()

        # Feature Flag for Candidate E Min-Heap Expiration Prototype
        self.use_min_heap_expiration: bool = use_min_heap_expiration
        self._min_heap: List[Tuple[int, int, int]] = []  # List of (expiration_ns, res_id, generation_id)

        # Feature Flag for Candidate G Batched Expiration Sweep Prototype
        self.use_batched_sweep: bool = use_batched_sweep

        # Discover physical capacity if capacity is not explicitly specified
        if capacity is None:
            discovered_cpu_mcores, _ = discover_physical_capacity()
            capacity = discovered_cpu_mcores

        # Authoritative State Core (S_R)
        self._reservations: Dict[int, ReservationRecord] = {}
        self._used_capacity: int = 0
        self._capacity: int = capacity
        self._safety_margin: int = safety_margin
        self._uncertainty: int = uncertainty
        self._authority_epoch: int = authority_epoch
        self._lease_epochs: Dict[int, int] = {}  # res_inv -> Epoch
        self._worker_generations: Dict[int, int] = {}  # res_worker -> Generation
        self._gpu_owners: Dict[int, int] = {}  # GPUId -> ReservationId
        self._quarantine: Dict[int, ReservationRecord] = {}  # ResID -> Record

        # Worker Scaling Lifecycle State Core
        self._worker_states: Dict[int, WorkerScalingRecord] = {}
        self._retired_tombstones: Dict[Tuple[int, int], bool] = {}  # (worker_id, generation) -> True

        # Policy & Configuration (Non-Authoritative until initialized)
        self._declarative_policy: Optional[DeclarativeResourcePolicy] = declarative_policy
        if declarative_policy is not None:
            self._capacity = declarative_policy.limits.cpu_mcores
            self._safety_margin = int(declarative_policy.memory_margin_bytes / (1024 * 1024))
            self._uncertainty = int(declarative_policy.telemetry_uncertainty * 100)

    # -------------------------------------------------------------------------
    # Abstraction Function alpha: C_Python -> A_Coq
    # -------------------------------------------------------------------------
    def alpha(self) -> AbstractReservationState:
        """Computes alpha(c) mapping concrete Python state to abstract Coq state."""
        with self._lock:
            res_tuple = tuple(self._reservations.values())
            lease_tuple = tuple(sorted(self._lease_epochs.items()))
            gen_tuple = tuple(sorted(self._worker_generations.items()))
            gpu_tuple = tuple(sorted(self._gpu_owners.items()))
            return AbstractReservationState(
                rs_reservations=res_tuple,
                rs_capacity=self._capacity,
                rs_used_capacity=self._used_capacity,
                rs_safety_margin=self._safety_margin,
                rs_uncertainty=self._uncertainty,
                rs_authority_epoch=self._authority_epoch,
                rs_lease_epochs=lease_tuple,
                rs_generations=gen_tuple,
                rs_gpu_owners=gpu_tuple,
            )

    # -------------------------------------------------------------------------
    # Runtime Invariant Checker
    # -------------------------------------------------------------------------
    def check_invariants(self) -> bool:
        """
        Executes runtime verification of Coq properties P1a, P1b, P2, P11, P12, P13.
        Returns True if all invariants hold; raises ValueError if violated.
        """
        with self._lock:
            active_invs: Dict[int, int] = {}
            active_atts: Dict[int, int] = {}
            seen_ids: Set[int] = set()

            sum_active_demand = 0
            sum_active_vector = DemandVector()

            for r in self._reservations.values():
                if r.res_id in seen_ids:
                    raise UniquenessViolationError(f"P12 Violated: Duplicate ReservationId {r.res_id}")
                seen_ids.add(r.res_id)

                if r.res_status.is_active():
                    active_invs[r.res_inv] = active_invs.get(r.res_inv, 0) + 1
                    if active_invs[r.res_inv] > 1:
                        raise UniquenessViolationError(f"P1a Violated: Invocation {r.res_inv} has active count > 1")

                    active_atts[r.res_att] = active_atts.get(r.res_att, 0) + 1
                    if active_atts[r.res_att] > 1:
                        raise UniquenessViolationError(f"P1b Violated: Attempt {r.res_att} has active count > 1")

                    eff_vec = r.get_effective_demand_vector()
                    sum_active_demand += eff_vec.cpu_mcores
                    sum_active_vector += eff_vec

            # P2: Capacity Safety (CPU millicores)
            max_schedulable = self._capacity - self._safety_margin - self._uncertainty
            if sum_active_demand + self._used_capacity > max_schedulable:
                raise InsufficientCapacityError(
                    f"P2 Violated: Active demand ({sum_active_demand}) + used ({self._used_capacity}) > max schedulable ({max_schedulable})"
                )

            # P2: Policy Limits Verification for Declarative Policies
            if self._declarative_policy is not None:
                limits = self._declarative_policy.limits
                if limits.memory_bytes > 0:
                    max_schedulable_mem = limits.memory_bytes - self._declarative_policy.memory_margin_bytes
                    if sum_active_vector.memory_bytes > max_schedulable_mem:
                        raise InsufficientCapacityError(
                            f"P2 Violated: Active memory ({sum_active_vector.memory_bytes}) > max schedulable ({max_schedulable_mem})"
                        )

                if limits.vram_bytes > 0:
                    max_schedulable_vram = limits.vram_bytes - self._declarative_policy.vram_margin_bytes
                    if sum_active_vector.vram_bytes > max_schedulable_vram:
                        raise InsufficientCapacityError(
                            f"P2 Violated: Active VRAM ({sum_active_vector.vram_bytes}) > max schedulable ({max_schedulable_vram})"
                        )

            # Nonnegative Accounting Invariant
            if self._used_capacity < 0:
                raise ValueError("Accounting Invariant Violated: Used capacity < 0")

            # P11: GPU Ownership Uniqueness
            for g_id, res_id in self._gpu_owners.items():
                if res_id not in self._reservations:
                    raise ValueError(f"P11 Violated: GPU {g_id} owned by unknown reservation {res_id}")

            return True

    # -------------------------------------------------------------------------
    # Declarative Policy Loading & Precondition Verification
    # -------------------------------------------------------------------------
    def load_declarative_policy(self, raw_dict: Dict[str, Any]) -> DeclarativeResourcePolicy:
        """
        Loads and validates a declarative resource policy, updating policy bounds without
        magically altering live accounting state S_R (enforcing Declaration != LiveAuthority).
        """
        with self._lock:
            policy = DeclarativeResourcePolicy.from_dict(raw_dict)
            self._declarative_policy = policy

            # Update schedulable policy capacity
            self._capacity = policy.limits.cpu_mcores
            self._safety_margin = int(policy.memory_margin_bytes / (1024 * 1024))
            self._uncertainty = int(policy.telemetry_uncertainty * 100)

            # Verify that current live accounting still satisfies new policy preconditions
            self.check_invariants()
            return policy

    # -------------------------------------------------------------------------
    # Worker Scaling Lifecycle Transitions (Scale-Up / Scale-Down)
    # -------------------------------------------------------------------------
    def scale_up_register_worker(self, worker_id: int, generation: int, capabilities: Set[str]) -> WorkerScalingRecord:
        """
        ScaleUp(w) ==> Register(w) && ValidateCapability(w) && InitializeGeneration(w) && PublishCapacity(w).
        """
        with self._lock:
            # Check Incarnation Tombstones
            if (worker_id, generation) in self._retired_tombstones:
                raise InvalidFencingError(f"Worker incarnation ({worker_id}, {generation}) is retired in tombstones")

            current_gen = self._worker_generations.get(worker_id, 0)
            if generation <= current_gen:
                raise InvalidFencingError(
                    f"Worker {worker_id} registration generation {generation} <= current {current_gen}"
                )

            record = WorkerScalingRecord(
                worker_id=worker_id,
                generation=generation,
                state=WorkerLifecycleState.ACTIVE,
                active_assignments_count=0,
                capabilities=set(capabilities),
            )

            self._worker_states[worker_id] = record
            self._worker_generations[worker_id] = generation
            self.check_invariants()
            return record

    def scale_down_drain_worker(self, worker_id: int) -> WorkerScalingRecord:
        """ScaleDown(w) Phase 1: Transition worker to DRAINING state to stop new placements."""
        with self._lock:
            if worker_id not in self._worker_states:
                raise KeyError(f"Unknown worker ID {worker_id}")

            w_rec = self._worker_states[worker_id]
            if w_rec.state == WorkerLifecycleState.RETIRED:
                raise InvalidStateTransitionError(f"Worker {worker_id} is already RETIRED")

            w_rec.state = WorkerLifecycleState.DRAINING
            self._check_and_update_worker_quiescence(worker_id)
            return w_rec

    def _check_and_update_worker_quiescence(self, worker_id: int) -> bool:
        """Helper evaluating Quiescent(w) <=> ActiveAssignments(w) == 0 and NoActiveReservations(w)."""
        w_rec = self._worker_states[worker_id]
        if w_rec.state != WorkerLifecycleState.DRAINING:
            return w_rec.state == WorkerLifecycleState.QUIESCENT or w_rec.state == WorkerLifecycleState.FENCED

        active_res_for_worker = sum(
            1 for r in self._reservations.values() if r.res_worker == worker_id and r.res_status.is_active()
        )

        if w_rec.active_assignments_count == 0 and active_res_for_worker == 0:
            w_rec.state = WorkerLifecycleState.QUIESCENT
            return True
        return False

    def is_worker_retirable(self, worker_id: int) -> bool:
        """
        Retirable(w) <=> Quiescent(w) && NoActiveReservation(w) && NoExclusiveResourceOwnership(w) && DrainComplete(w).
        Evaluates ALL authoritative resources, not just CPU idle!
        """
        with self._lock:
            if worker_id not in self._worker_states:
                return False

            w_rec = self._worker_states[worker_id]
            self._check_and_update_worker_quiescence(worker_id)

            if w_rec.state not in (WorkerLifecycleState.QUIESCENT, WorkerLifecycleState.FENCED):
                return False

            # Ensure no active reservations belong to this worker
            for r in self._reservations.values():
                if r.res_worker == worker_id and r.res_status.is_active():
                    return False

            # Ensure no exclusive GPU ownership held by reservations of this worker
            for g, r_id in self._gpu_owners.items():
                res = self._reservations.get(r_id)
                if res and res.res_worker == worker_id and res.res_status.is_active():
                    return False

            return True

    def scale_down_retire_worker(self, worker_id: int) -> WorkerScalingRecord:
        """
        ScaleDown(w) Final Phase: Retire(w) ==> Quiescent(w) && Fence(w) && Retire(w) && Tombstone.
        Enforces RetiredResources(w) == AllResources(w).
        """
        with self._lock:
            if not self.is_worker_retirable(worker_id):
                raise WorkerNotQuiescentError(
                    f"ScaleDown Reject: Worker {worker_id} is not retirable (active assignments or reservations exist)"
                )

            w_rec = self._worker_states[worker_id]
            w_rec.state = WorkerLifecycleState.RETIRED

            # Fence worker and record Incarnation Tombstone
            gen = w_rec.generation
            self._retired_tombstones[(worker_id, gen)] = True

            self.check_invariants()
            return w_rec

    # -------------------------------------------------------------------------
    # Authoritative FSM Transition Operations
    # -------------------------------------------------------------------------
    def reserve(
        self,
        res_id: int,
        res_inv: int,
        res_att: int,
        res_worker: int,
        res_demand: int = 0,
        authority_epoch: int = 1,
        lease_epoch: int = 1,
        worker_generation: int = 1,
        gpu_id: Optional[int] = None,
        expiration_timestamp_ns: Optional[int] = None,
        demand_vector: Optional[DemandVector] = None,
    ) -> ReservationRecord:
        """Linearization Point for OpReserve / OpReserveGPU / VectorReserve."""
        with self._lock:
            # Construct effective demand vector
            if demand_vector is not None:
                effective_vector = demand_vector
                if gpu_id is not None and gpu_id not in effective_vector.gpu_devices:
                    gpu_devs = tuple(sorted(set(effective_vector.gpu_devices).union((gpu_id,))))
                    effective_vector = DemandVector(
                        cpu_mcores=effective_vector.cpu_mcores,
                        memory_bytes=effective_vector.memory_bytes,
                        gpu_devices=gpu_devs,
                        vram_bytes=effective_vector.vram_bytes,
                        io_capacity=effective_vector.io_capacity,
                        network_mbps=effective_vector.network_mbps,
                        fd_capacity=effective_vector.fd_capacity,
                        thread_capacity=effective_vector.thread_capacity,
                        storage_bytes=effective_vector.storage_bytes,
                    )
            else:
                gpu_devs = (gpu_id,) if gpu_id is not None else ()
                effective_vector = DemandVector(cpu_mcores=res_demand, gpu_devices=gpu_devs)

            eff_demand = effective_vector.cpu_mcores if res_demand == 0 else res_demand

            # 1. Authority Epoch Fencing Check (P6)
            if authority_epoch != self._authority_epoch:
                raise InvalidFencingError(
                    f"P6 Fencing Reject: Stale authority epoch {authority_epoch} != active {self._authority_epoch}"
                )

            # 2. Incarnation Tombstone & Worker Generation Fencing Check (P7)
            if (res_worker, worker_generation) in self._retired_tombstones:
                raise InvalidFencingError(
                    f"P7 Fencing Reject: Worker {res_worker} gen {worker_generation} is retired in tombstones"
                )

            if res_worker in self._worker_states:
                w_rec = self._worker_states[res_worker]
                if w_rec.state in (
                    WorkerLifecycleState.DRAINING,
                    WorkerLifecycleState.QUIESCENT,
                    WorkerLifecycleState.RETIRED,
                ):
                    raise InvalidFencingError(
                        f"P7 Fencing Reject: Worker {res_worker} is in state {w_rec.state.name} (not accepting placement)"
                    )

            active_gen = self._worker_generations.get(res_worker, worker_generation)
            if worker_generation != active_gen:
                raise InvalidFencingError(
                    f"P7 Fencing Reject: Worker {res_worker} gen {worker_generation} != active {active_gen}"
                )

            # 3. Identity & Uniqueness Check (P1a, P1b, P12)
            if res_id in self._reservations:
                raise UniquenessViolationError(f"P12 Reject: ReservationId {res_id} already exists")

            for r in self._reservations.values():
                if r.res_status.is_active():
                    if r.res_inv == res_inv:
                        raise UniquenessViolationError(
                            f"P1a Reject: Active reservation exists for Invocation {res_inv}"
                        )
                    if r.res_att == res_att:
                        raise UniquenessViolationError(f"P1b Reject: Active reservation exists for Attempt {res_att}")

            # 4. Lease Monotonicity Fencing Check (P14)
            current_lease = self._lease_epochs.get(res_inv, 0)
            if lease_epoch <= current_lease:
                raise InvalidFencingError(f"P14 Fencing Reject: Lease epoch {lease_epoch} <= current {current_lease}")

            # 5. GPU Collision Check (P11)
            for g in effective_vector.gpu_devices:
                if g in self._gpu_owners:
                    raise GPUCollisionError(f"P11 Reject: GPU {g} already owned by reservation {self._gpu_owners[g]}")

            # 6. Capacity Safety Check (P2)
            sum_active = sum(
                r.get_effective_demand_vector().cpu_mcores
                for r in self._reservations.values()
                if r.res_status.is_active()
            )
            max_schedulable = self._capacity - self._safety_margin - self._uncertainty
            if sum_active + eff_demand + self._used_capacity > max_schedulable:
                raise InsufficientCapacityError(
                    f"P2 Reject: Total demand ({sum_active + eff_demand}) + used ({self._used_capacity}) > schedulable ({max_schedulable})"
                )

            # Additional multi-dimensional policy checks
            if self._declarative_policy is not None:
                limits = self._declarative_policy.limits
                sum_active_vec = sum(
                    (r.get_effective_demand_vector() for r in self._reservations.values() if r.res_status.is_active()),
                    DemandVector(),
                )
                total_vec = sum_active_vec + effective_vector

                if limits.memory_bytes > 0:
                    max_mem = limits.memory_bytes - self._declarative_policy.memory_margin_bytes
                    if total_vec.memory_bytes > max_mem:
                        raise InsufficientCapacityError(
                            f"P2 Reject: Total memory demand ({total_vec.memory_bytes}) > max schedulable ({max_mem})"
                        )

                if limits.vram_bytes > 0:
                    max_vram = limits.vram_bytes - self._declarative_policy.vram_margin_bytes
                    if total_vec.vram_bytes > max_vram:
                        raise InsufficientCapacityError(
                            f"P2 Reject: Total VRAM demand ({total_vec.vram_bytes}) > max schedulable ({max_vram})"
                        )

            # Atomic Mutation
            rec = ReservationRecord(
                res_id=res_id,
                res_inv=res_inv,
                res_att=res_att,
                res_worker=res_worker,
                res_demand=eff_demand,
                res_authority_epoch=authority_epoch,
                res_lease_epoch=lease_epoch,
                res_generation=worker_generation,
                res_status=ReservationStatus.ACTIVE,
                generation_id=1,
                expiration_timestamp_ns=expiration_timestamp_ns,
                demand_vector=effective_vector,
            )
            self._reservations[res_id] = rec
            self._lease_epochs[res_inv] = lease_epoch
            self._worker_generations[res_worker] = worker_generation
            for g in effective_vector.gpu_devices:
                self._gpu_owners[g] = res_id

            if self.use_min_heap_expiration and expiration_timestamp_ns is not None:
                heapq.heappush(self._min_heap, (expiration_timestamp_ns, res_id, rec.generation_id))

            if res_worker in self._worker_states:
                self._worker_states[res_worker].active_assignments_count += 1

            self.check_invariants()
            return rec

    def renew_reservation(self, res_id: int, new_expiration_ts_ns: int) -> ReservationRecord:
        """
        Renews an active reservation TTL, updating generation_id token for stale-heap safety.
        """
        with self._lock:
            if res_id not in self._reservations:
                raise KeyError(f"Unknown reservation ID {res_id}")

            rec = self._reservations[res_id]
            if not rec.res_status.is_active():
                raise InvalidStateTransitionError(f"Cannot renew non-active reservation {res_id}")

            # Increment generation_id token to invalidate old heap entries
            rec.generation_id += 1
            rec.expiration_timestamp_ns = new_expiration_ts_ns

            if self.use_min_heap_expiration:
                heapq.heappush(self._min_heap, (new_expiration_ts_ns, res_id, rec.generation_id))

            self.check_invariants()
            return rec

    def expire_reservations_sweep(self, now_ns: int) -> List[ReservationRecord]:
        """
        Executes expiration sweep for reservations where expiration_timestamp_ns <= now_ns.
        Supports three modes:
          - Control Baseline: O(N) scan, per-item expire() with per-item check_invariants().
          - Candidate E: O(log N) Min-Heap selection, per-item expire().
          - Candidate G: Batched transitions with single terminal check_invariants().

        Candidate G transition pattern:
          Identify expired entries -> Validate each against S_A ->
          Apply all valid terminal transitions atomically -> Validate final S_A'

        Safety argument: Each expiration only REMOVES active demand and RELEASES
        exclusive resources. Invariants (P1a, P1b, P2, P11, P12) are monotonically
        preserved because the active set can only shrink during a sweep.
        """
        with self._lock:
            if self.use_batched_sweep:
                return self._expire_reservations_sweep_batched(now_ns)

            expired_records: List[ReservationRecord] = []

            if self.use_min_heap_expiration:
                while self._min_heap:
                    exp_ts, res_id, gen_id = self._min_heap[0]
                    if exp_ts > now_ns:
                        break
                    heapq.heappop(self._min_heap)

                    # Authoritative Revalidation Pattern
                    rec = self._reservations.get(res_id)
                    if rec is None or not rec.res_status.is_active() or rec.generation_id != gen_id:
                        # Stale heap entry (cancelled, renewed, or already expired).
                        # Discard cleanly without mutating authoritative state S_R.
                        continue

                    # Valid active expiration
                    expired_rec = self.expire(res_id)
                    expired_records.append(expired_rec)
            else:
                # Control Baseline: O(N) linear scan over active reservations
                to_expire = [
                    r.res_id
                    for r in self._reservations.values()
                    if r.res_status.is_active()
                    and r.expiration_timestamp_ns is not None
                    and r.expiration_timestamp_ns <= now_ns
                ]
                for res_id in to_expire:
                    expired_rec = self.expire(res_id)
                    expired_records.append(expired_rec)

            return expired_records

    def _expire_reservations_sweep_batched(self, now_ns: int) -> List[ReservationRecord]:
        """
        Candidate G: Batched Expiration + Single Invariant Validation with Transactional Rollback.

        Transition pattern:
          1. Identify all expired candidates (via heap or linear scan).
          2. Validate each candidate against authoritative state S_A.
          3. Apply all valid terminal transitions (ACTIVE -> EXPIRED) atomically.
          4. Validate final S_A' once.

        Transactional safety:
          If check_invariants() or any transition step raises an exception,
          the entire batch rolls back to its exact pre-sweep state.
        """
        # Save a snapshot of mutable states for atomic rollbacks
        backup_status: Dict[int, ReservationStatus] = {}
        backup_gpu_owners = dict(self._gpu_owners)
        backup_worker_states = {
            w_id: (w_rec.active_assignments_count, w_rec.state) for w_id, w_rec in self._worker_states.items()
        }
        backup_quarantine = dict(self._quarantine)
        backup_min_heap = list(self._min_heap)

        try:
            # Phase 1: Identify expired candidates
            candidates: List[int] = []

            if self.use_min_heap_expiration:
                while self._min_heap:
                    exp_ts, res_id, gen_id = self._min_heap[0]
                    if exp_ts > now_ns:
                        break
                    heapq.heappop(self._min_heap)

                    rec = self._reservations.get(res_id)
                    if rec is None or not rec.res_status.is_active() or rec.generation_id != gen_id:
                        continue
                    candidates.append(res_id)
            else:
                candidates = [
                    r.res_id
                    for r in self._reservations.values()
                    if r.res_status.is_active()
                    and r.expiration_timestamp_ns is not None
                    and r.expiration_timestamp_ns <= now_ns
                ]

            if not candidates:
                return []

            # Phase 2: Validate each candidate against S_A and apply terminal transition
            expired_records: List[ReservationRecord] = []

            for res_id in candidates:
                rec = self._reservations.get(res_id)
                if rec is None:
                    continue

                if not rec.res_status.is_active():
                    continue

                # Backup individual status before modification
                backup_status[res_id] = rec.res_status

                # Apply terminal transition: ACTIVE -> EXPIRED
                rec.res_status = ReservationStatus.EXPIRED

                # Release GPU ownership (P11)
                gpus_to_remove = [g for g, owner_id in self._gpu_owners.items() if owner_id == res_id]
                for g in gpus_to_remove:
                    del self._gpu_owners[g]

                # Decrement worker active assignment count
                if rec.res_worker in self._worker_states:
                    w_rec = self._worker_states[rec.res_worker]
                    w_rec.active_assignments_count = max(0, w_rec.active_assignments_count - 1)
                    self._check_and_update_worker_quiescence(rec.res_worker)

                self._quarantine[res_id] = rec
                expired_records.append(rec)

            # Phase 3: Single invariant validation over final S_A'
            self.check_invariants()

            return expired_records

        except Exception as e:
            # Transactional Rollback
            for res_id, status in backup_status.items():
                self._reservations[res_id].res_status = status
            self._gpu_owners = backup_gpu_owners
            for w_id, (count, state) in backup_worker_states.items():
                self._worker_states[w_id].active_assignments_count = count
                self._worker_states[w_id].state = state
            self._quarantine = backup_quarantine
            self._min_heap = backup_min_heap
            raise e

    def activate(self, res_id: int) -> ReservationRecord:
        """Linearization Point for OpActivate (transitions PENDING -> ACTIVE)."""
        with self._lock:
            if res_id not in self._reservations:
                raise KeyError(f"Unknown reservation ID {res_id}")

            rec = self._reservations[res_id]
            if rec.res_status == ReservationStatus.PENDING:
                rec.res_status = ReservationStatus.ACTIVE
            elif rec.res_status != ReservationStatus.ACTIVE:
                raise InvalidStateTransitionError(
                    f"Cannot activate reservation {res_id} in state {rec.res_status.name}"
                )

            self.check_invariants()
            return rec

    def release(
        self,
        res_id: int,
        authority_epoch: Optional[int] = None,
        res_worker: Optional[int] = None,
        worker_generation: Optional[int] = None,
        lease_epoch: Optional[int] = None,
    ) -> ReservationRecord:
        """Linearization Point for OpRelease."""
        with self._lock:
            if res_id not in self._reservations:
                raise KeyError(f"Unknown reservation ID {res_id}")

            rec = self._reservations[res_id]

            if authority_epoch is not None and authority_epoch != self._authority_epoch:
                raise InvalidFencingError(
                    f"P6 Fencing Reject on Release: Stale authority epoch {authority_epoch} != active {self._authority_epoch}"
                )

            if res_worker is not None and worker_generation is not None:
                if (res_worker, worker_generation) in self._retired_tombstones:
                    raise InvalidFencingError(
                        f"P7 Fencing Reject on Release: Worker {res_worker} gen {worker_generation} is retired in tombstones"
                    )
                active_gen = self._worker_generations.get(res_worker, worker_generation)
                if worker_generation != active_gen:
                    raise InvalidFencingError(
                        f"P7 Fencing Reject on Release: Worker {res_worker} gen {worker_generation} != active {active_gen}"
                    )

            if lease_epoch is not None and lease_epoch < rec.res_lease_epoch:
                raise InvalidFencingError(
                    f"P14 Fencing Reject on Release: Stale lease epoch {lease_epoch} < record lease {rec.res_lease_epoch}"
                )

            if rec.res_status not in (ReservationStatus.ACTIVE, ReservationStatus.PENDING):
                return rec

            # Transactional Transition: ACTIVE/PENDING -> RELEASED
            rec.res_status = ReservationStatus.RELEASED

            # Release GPU Ownership (P11)
            gpus_to_remove = [g for g, owner_id in self._gpu_owners.items() if owner_id == res_id]
            for g in gpus_to_remove:
                del self._gpu_owners[g]

            if rec.res_worker in self._worker_states:
                w_rec = self._worker_states[rec.res_worker]
                w_rec.active_assignments_count = max(0, w_rec.active_assignments_count - 1)
                self._check_and_update_worker_quiescence(rec.res_worker)

            self.check_invariants()
            return rec

    def expire(
        self,
        res_id: int,
        authority_epoch: Optional[int] = None,
        res_worker: Optional[int] = None,
        worker_generation: Optional[int] = None,
    ) -> ReservationRecord:
        """Linearization Point for OpExpire."""
        with self._lock:
            if res_id not in self._reservations:
                raise KeyError(f"Unknown reservation ID {res_id}")

            rec = self._reservations[res_id]

            if authority_epoch is not None and authority_epoch != self._authority_epoch:
                raise InvalidFencingError(
                    f"P6 Fencing Reject on Expire: Stale authority epoch {authority_epoch} != active {self._authority_epoch}"
                )

            if res_worker is not None and worker_generation is not None:
                if (res_worker, worker_generation) in self._retired_tombstones:
                    raise InvalidFencingError(
                        f"P7 Fencing Reject on Expire: Worker {res_worker} gen {worker_generation} is retired in tombstones"
                    )

            if rec.res_status not in (ReservationStatus.ACTIVE, ReservationStatus.PENDING):
                return rec

            rec.res_status = ReservationStatus.EXPIRED

            # Release GPU
            gpus_to_remove = [g for g, owner_id in self._gpu_owners.items() if owner_id == res_id]
            for g in gpus_to_remove:
                del self._gpu_owners[g]

            if rec.res_worker in self._worker_states:
                w_rec = self._worker_states[rec.res_worker]
                w_rec.active_assignments_count = max(0, w_rec.active_assignments_count - 1)
                self._check_and_update_worker_quiescence(rec.res_worker)

            self._quarantine[res_id] = rec
            self.check_invariants()
            return rec

    def revoke(
        self,
        res_id: int,
        authority_epoch: Optional[int] = None,
        res_worker: Optional[int] = None,
        worker_generation: Optional[int] = None,
    ) -> ReservationRecord:
        """Linearization Point for OpRevoke."""
        with self._lock:
            if res_id not in self._reservations:
                raise KeyError(f"Unknown reservation ID {res_id}")

            rec = self._reservations[res_id]

            if authority_epoch is not None and authority_epoch != self._authority_epoch:
                raise InvalidFencingError(
                    f"P6 Fencing Reject on Revoke: Stale authority epoch {authority_epoch} != active {self._authority_epoch}"
                )

            if res_worker is not None and worker_generation is not None:
                if (res_worker, worker_generation) in self._retired_tombstones:
                    raise InvalidFencingError(
                        f"P7 Fencing Reject on Revoke: Worker {res_worker} gen {worker_generation} is retired in tombstones"
                    )

            if rec.res_status not in (ReservationStatus.ACTIVE, ReservationStatus.PENDING):
                return rec

            rec.res_status = ReservationStatus.REVOKED

            # Release GPU
            gpus_to_remove = [g for g, owner_id in self._gpu_owners.items() if owner_id == res_id]
            for g in gpus_to_remove:
                del self._gpu_owners[g]

            if rec.res_worker in self._worker_states:
                w_rec = self._worker_states[rec.res_worker]
                w_rec.active_assignments_count = max(0, w_rec.active_assignments_count - 1)
                self._check_and_update_worker_quiescence(rec.res_worker)

            self._quarantine[res_id] = rec
            self.check_invariants()
            return rec

    def authority_succession(self, new_epoch: int) -> int:
        """Linearization Point for OpAuthoritySuccession."""
        with self._lock:
            if new_epoch <= self._authority_epoch:
                raise InvalidFencingError(
                    f"P14 Reject: New authority epoch {new_epoch} <= current {self._authority_epoch}"
                )

            self._authority_epoch = new_epoch
            self.check_invariants()
            return self._authority_epoch

    def recover_from_records(self, records: List[ReservationRecord], authority_epoch: int) -> None:
        """
        WAL Recovery Replay Engine.
        Enforces P10 (Recovery Invariant Preservation & Non-Resurrection).
        """
        with self._lock:
            self._reservations.clear()
            self._gpu_owners.clear()
            self._lease_epochs.clear()
            self._worker_generations.clear()
            self._quarantine.clear()
            self._authority_epoch = authority_epoch
            if self.use_min_heap_expiration:
                self._min_heap.clear()

            for r in records:
                self._reservations[r.res_id] = r
                self._lease_epochs[r.res_inv] = max(self._lease_epochs.get(r.res_inv, 0), r.res_lease_epoch)
                self._worker_generations[r.res_worker] = max(
                    self._worker_generations.get(r.res_worker, 0), r.res_generation
                )

                if r.res_status.is_active():
                    eff_vec = r.get_effective_demand_vector()
                    for g in eff_vec.gpu_devices:
                        self._gpu_owners[g] = r.res_id
                    if self.use_min_heap_expiration and r.expiration_timestamp_ns is not None:
                        heapq.heappush(self._min_heap, (r.expiration_timestamp_ns, r.res_id, r.generation_id))
                else:
                    self._quarantine[r.res_id] = r

            self.check_invariants()
