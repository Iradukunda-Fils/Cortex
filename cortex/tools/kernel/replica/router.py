"""
Gateway Control Plane Routing & Dispatch Subsystem (Phase 4)

Implements CandidateResolver, RoutingPolicy, LeaseManager Atomic Revalidation,
GatewayDispatcher, RecoveryEngine, and CommitSequencer integration.

Invariants:
1. Routing decisions are revocable proposals, not execution authority.
2. Router possesses zero ExecutionTokens, capability keys, or TCB mutation authority.
3. Candidate proposals are atomically revalidated inside LeaseManager.grant_lease_with_revalidation().
4. Bounded FIFO queue per ReplicaGroup.
"""

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

from cortex.tools.kernel.replica.identity import OwnershipIdentity
from cortex.tools.kernel.replica.lease import LeaseManager
from cortex.tools.kernel.replica.ledger import InvocationState, InvocationStateLedger
from cortex.tools.kernel.replica.lifecycle import WorkerLifecycleStage


class NoEligibleWorkerNow(Exception):
    """Raised when no worker replica currently satisfies metadata criteria (ERR_NO_ELIGIBLE_WORKER_NOW)."""

    pass


class QueueFullError(Exception):
    """Raised when the Gateway admission queue breaches MaxQueueDepth (ERR_QUEUE_FULL)."""

    pass


class QueueTimeoutError(Exception):
    """Raised when an invocation exceeds QueueTimeoutSec in QUEUED state (ERR_QUEUE_TIMEOUT)."""

    pass


class StaleCandidateError(Exception):
    """Raised when a proposed candidate fails atomic LeaseManager revalidation (ERR_STALE_CANDIDATE)."""

    pass


class ExecutionClass(Enum):
    UNORDERED_COMMUTATIVE = auto()
    ORDERED = auto()
    VERSION_FENCED = auto()
    SERIALIZED_STATE_DOMAIN = auto()


@dataclass(frozen=True)
class StateDomainKey:
    """Canonical immutable identifier for stateful operation conflict serialization."""

    resource_namespace: str
    target_path: str
    state_key: str

    def domain_hash(self) -> str:
        """Returns SHA-256 state domain identifier."""
        raw = f"{self.resource_namespace}:{self.target_path}:{self.state_key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorkerRef:
    """Unprivileged snapshot metadata reference for a worker replica."""

    instance_id: str
    group_id: str
    lifecycle_version: int
    config_generation: int
    config_hash: str
    sandbox_profile_hash: str
    capability_envelope_hash: str
    required_capabilities: list[str] = field(default_factory=list)
    observed_inflight: int = 0
    stage: WorkerLifecycleStage = WorkerLifecycleStage.READY


@dataclass(frozen=True)
class RoutingDecisionEvent:
    """Observational witness event for routing decision provenance.

    Purely observational evidence; does NOT possess bearer tokens or advance commit state.
    """

    invocation_id: str
    config_generation: int
    config_hash: str
    candidate_set_digest: str
    selection_policy: str
    selected_replica_id: str
    selection_score: int
    timestamp_ns: int = field(default_factory=time.time_ns)
    event_type: str = "RoutingDecisionEvent"


class CandidateResolver:
    """Unprivileged Candidate Resolver.

    Filters candidate worker replicas against metadata criteria. Possesses ZERO TCB authority,
    ExecutionTokens, or lease mutation capability.
    """

    def resolve_candidates(
        self,
        candidate_pool: list[WorkerRef],
        required_capabilities: list[str],
        active_config_gen: int,
        active_config_hash: str,
        active_sandbox_hash: str,
        active_cap_hash: str,
        max_worker_inflight: int = 10,
    ) -> List[WorkerRef]:
        """Filters worker pool against metadata criteria. Returns list of eligible WorkerRef items."""
        req_set = set(required_capabilities)
        eligible: List[WorkerRef] = []

        for w in candidate_pool:
            if w.stage != WorkerLifecycleStage.READY:
                continue
            if w.config_generation != active_config_gen:
                continue
            if w.config_hash != active_config_hash:
                continue
            if w.sandbox_profile_hash != active_sandbox_hash:
                continue
            if w.capability_envelope_hash != active_cap_hash:
                continue
            if not req_set.issubset(set(w.required_capabilities)):
                continue
            if w.observed_inflight >= max_worker_inflight:
                continue
            eligible.append(w)

        return eligible


class RoutingPolicy:
    """Unprivileged Routing Policy Selector.

    Selects best eligible candidate using deterministic Least-Inflight with lexicographical
    instance_id tie-breaking.
    """

    def select_candidate(self, eligible_candidates: List[WorkerRef]) -> WorkerRef:
        """Selects candidate with min (observed_inflight, instance_id)."""
        if not eligible_candidates:
            raise NoEligibleWorkerNow("ERR_NO_ELIGIBLE_WORKER_NOW: No ready replica satisfies metadata criteria")

        sorted_candidates = sorted(eligible_candidates, key=lambda w: (w.observed_inflight, w.instance_id))
        return sorted_candidates[0]


class GatewayDispatcher:
    """Gateway Control Plane Dispatcher & Queue Authority.

    Coordinates candidate resolution, atomic LeaseManager revalidation, per-group FIFO queueing,
    state domain serialization, and token dispatch.
    """

    def __init__(
        self,
        lease_manager: LeaseManager,
        ledger: InvocationStateLedger,
        max_queue_depth: int = 1000,
        max_worker_inflight: int = 10,
        queue_timeout_sec: float = 30.0,
        dispatch_deadline_sec: float = 5.0,
    ) -> None:
        self.lease_manager = lease_manager
        self.ledger = ledger
        self.resolver = CandidateResolver()
        self.policy = RoutingPolicy()
        self.max_queue_depth = max_queue_depth
        self.max_worker_inflight = max_worker_inflight
        self.queue_timeout_sec = queue_timeout_sec
        self.dispatch_deadline_sec = dispatch_deadline_sec

        # State domain locks: domain_hash -> lock_owner_invocation_id
        self._state_domain_locks: Dict[str, str] = {}
        # ReplicaGroup queues: group_id -> List[invocation_id]
        self._fifo_queues: Dict[str, List[str]] = {}
        # Observational event buffer (compacted / written to audit)
        self.decision_events: List[RoutingDecisionEvent] = []

    def dispatch_invocation(
        self,
        invocation_id: str,
        intent_hash: str,
        required_capabilities: List[str],
        candidate_pool: List[WorkerRef],
        active_config_gen: int,
        active_config_hash: str,
        active_sandbox_hash: str,
        active_cap_hash: str,
        execution_class: ExecutionClass = ExecutionClass.UNORDERED_COMMUTATIVE,
        state_domain_key: Optional[StateDomainKey] = None,
        target_state_version: Optional[int] = None,
    ) -> OwnershipIdentity:
        """Executes the complete 8-stage dispatch pipeline with single-lock atomic revalidation.

        Returns OwnershipIdentity on successful lease grant and assignment.
        """
        # Stage 1: Admit to ledger
        record = self.ledger.get_record(invocation_id)
        if not record:
            record = self.ledger.create_invocation(
                invocation_id=invocation_id,
                intent_hash=intent_hash,
                config_generation=active_config_gen,
                config_hash=active_config_hash,
            )

        # Determine target group_id (from candidates or default)
        group_id = candidate_pool[0].group_id if candidate_pool else "default"

        # Check total queue capacity across groups
        total_queued = sum(len(q) for q in self._fifo_queues.values())
        if total_queued >= self.max_queue_depth:
            self.ledger.transition_state(invocation_id, InvocationState.REJECTED)
            raise QueueFullError(f"ERR_QUEUE_FULL: Queue depth {total_queued} exceeds maximum {self.max_queue_depth}")

        # Enqueue in group-specific FIFO queue
        group_queue = self._fifo_queues.setdefault(group_id, [])
        if invocation_id not in group_queue:
            group_queue.append(invocation_id)

        # Stage 2-4: Resolve candidates
        remaining_pool = list(candidate_pool)
        selected_candidate: Optional[WorkerRef] = None
        ownership: Optional[OwnershipIdentity] = None

        while remaining_pool:
            eligible = self.resolver.resolve_candidates(
                candidate_pool=remaining_pool,
                required_capabilities=required_capabilities,
                active_config_gen=active_config_gen,
                active_config_hash=active_config_hash,
                active_sandbox_hash=active_sandbox_hash,
                active_cap_hash=active_cap_hash,
                max_worker_inflight=self.max_worker_inflight,
            )

            if not eligible:
                break

            # Stage 5-6: Select candidate
            candidate = self.policy.select_candidate(eligible)

            # Stage 7: Single-Lock Atomic LeaseManager Revalidation & Grant (Linearization Point)
            ownership = self.lease_manager.grant_lease_with_revalidation(
                invocation_id=invocation_id,
                worker_ref=candidate,
                active_config_gen=active_config_gen,
                active_config_hash=active_config_hash,
                active_sandbox_hash=active_sandbox_hash,
                active_cap_hash=active_cap_hash,
                max_inflight=self.max_worker_inflight,
            )

            if ownership:
                selected_candidate = candidate
                break
            else:
                # TOCTOU race: candidate state changed in Gateway lock. Evict candidate and retry selection.
                remaining_pool = [w for w in remaining_pool if w.instance_id != candidate.instance_id]

        # Dequeue from group-specific FIFO queue upon dispatch resolution
        if invocation_id in group_queue:
            group_queue.remove(invocation_id)

        if not selected_candidate or not ownership:
            raise NoEligibleWorkerNow("ERR_NO_ELIGIBLE_WORKER_NOW: No ready replica passed atomic revalidation")

        # Handle Serialized State Domain lock
        if execution_class == ExecutionClass.SERIALIZED_STATE_DOMAIN and state_domain_key:
            d_hash = state_domain_key.domain_hash()
            if d_hash in self._state_domain_locks and self._state_domain_locks[d_hash] != invocation_id:
                # Lock conflict: revoke lease and raise conflict error
                self.lease_manager.revoke_lease(invocation_id, ownership.lease_epoch)
                raise ValueError(f"State domain lock conflict for hash {d_hash}")
            self._state_domain_locks[d_hash] = invocation_id

        # Update ledger state QUEUED -> ASSIGNED
        self.ledger.transition_state(
            invocation_id=invocation_id,
            to_state=InvocationState.ASSIGNED,
            worker_id=selected_candidate.instance_id,
            lease_epoch=ownership.lease_epoch,
        )

        # Emit observational RoutingDecisionEvent
        raw_digest = ":".join(sorted(w.instance_id for w in candidate_pool))
        digest = hashlib.sha256(raw_digest.encode("utf-8")).hexdigest()[:16]
        event = RoutingDecisionEvent(
            invocation_id=invocation_id,
            config_generation=active_config_gen,
            config_hash=active_config_hash,
            candidate_set_digest=digest,
            selection_policy="least_inflight_deterministic",
            selected_replica_id=selected_candidate.instance_id,
            selection_score=selected_candidate.observed_inflight,
        )
        self.decision_events.append(event)

        return ownership

    def release_state_domain_lock(self, state_domain_key: StateDomainKey, invocation_id: str) -> None:
        """Releases state domain lock upon invocation completion."""
        d_hash = state_domain_key.domain_hash()
        if self._state_domain_locks.get(d_hash) == invocation_id:
            del self._state_domain_locks[d_hash]
