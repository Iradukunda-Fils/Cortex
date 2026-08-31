"""
Phase 7.7b: Autoscaling Controller Engine
Normative Specification: Research Note 23 / Directive Phase 7.7b

Architectural Boundaries:
    Autoscaler = Capacity & Control Loop Optimization Layer
    ResourceAuthority = Authoritative Registration & Linearizable Safety Kernel
    WorkerSupervisor = Container Execution & Reclamation Pipeline

Invariants:
    1. Autoscaler NEVER becomes a second resource authority.
    2. Autoscaler NEVER directly mutates live resource accounting (S_R).
    3. Autoscaler ONLY calls authoritative methods:
       scale_up_register_worker(), scale_down_drain_worker(), scale_down_retire_worker().
    4. Scale-Down Safety: CapacityReusable(w) => Quiescent(w) && NoActiveReservations(w)
       && NoExclusiveResourceOwnership(w) && DrainComplete(w).
    5. Autoscaler NEVER reclaims a worker solely because CPU telemetry appears idle.
    6. Hysteresis controls prevent scale-up / scale-down oscillations.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

from cortex.tools.kernel.resource_authority import (
    InvalidFencingError,
    InvalidStateTransitionError,
    ResourceAuthority,
    WorkerLifecycleState,
    WorkerNotQuiescentError,
    WorkerScalingRecord,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Scaling Actions & Decision Types
# -----------------------------------------------------------------------------

class ScalingAction(Enum):
    NO_ACTION = auto()
    SCALE_UP = auto()
    DRAIN_WORKER = auto()
    RETIRE_WORKER = auto()


@dataclass(frozen=True)
class ScalingDecision:
    """Outcome of an autoscaling evaluation loop."""
    action: ScalingAction
    worker_id: Optional[int]
    generation: Optional[int]
    reason: str
    timestamp_sec: float = field(default_factory=time.time)


# -----------------------------------------------------------------------------
# Autoscaler Policy Configuration
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class AutoscalerConfig:
    """
    Autoscaling Hysteresis & Threshold Configuration.
    Prevents destructive scale-up / scale-down thrashing.
    """
    high_queue_threshold: int = 10        # Queue depth triggering scale-up
    low_queue_threshold: int = 0          # Queue depth allowing scale-down
    min_worker_replicas: int = 1          # Minimum active worker count
    max_worker_replicas: int = 20         # Maximum active worker count
    min_residency_sec: float = 30.0       # Minimum residency window before worker retirement
    cooldown_sec: float = 15.0            # Cooldown window after a scaling action
    default_capabilities: Set[str] = field(default_factory=lambda: {"python"})


# -----------------------------------------------------------------------------
# Phase 7.7b Autoscaling Controller
# -----------------------------------------------------------------------------

class AutoscalingController:
    """
    Autoscaling Control Plane (Phase 7.7b).

    Manages the asynchronous control loop:
        Observe Queue Pressure -> Evaluate Policy -> Scale Decision -> ResourceAuthority Transition

    Prohibitions:
        - NEVER directly mutates S_R
        - NEVER bypasses ResourceAuthority retirable checks
        - NEVER scales down active/reserved workers without quiescence
    """

    def __init__(
        self,
        resource_authority: ResourceAuthority,
        config: Optional[AutoscalerConfig] = None,
    ) -> None:
        self._authority = resource_authority
        self._config = config or AutoscalerConfig()

        self._last_scaling_timestamp_sec: float = 0.0
        self._worker_registration_timestamps: Dict[int, float] = {}  # worker_id -> ts
        self._next_worker_id: int = 100
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # Helper Queries
    # -------------------------------------------------------------------------

    def get_active_worker_count(self) -> int:
        """Returns count of non-retired workers registered in ResourceAuthority."""
        with self._lock:
            return sum(
                1 for w in self._authority._worker_states.values()
                if w.state in (WorkerLifecycleState.REGISTERING, WorkerLifecycleState.ACTIVE, WorkerLifecycleState.DRAINING)
            )

    # -------------------------------------------------------------------------
    # Core Control Loop Evaluator
    # -------------------------------------------------------------------------

    def evaluate_scaling(
        self,
        pending_queue_depth: int,
        now_sec: Optional[float] = None,
    ) -> ScalingDecision:
        """
        Evaluates queue pressure and cluster capacity against hysteresis rules.

        Sequence:
            1. Enforce cooldown window
            2. Evaluate Scale-Up (pending demand > high_threshold)
            3. Evaluate Scale-Down (pending demand <= low_threshold)
        """
        current_time = now_sec if now_sec is not None else time.time()

        with self._lock:
            # 1. Hysteresis Check: Cooldown Window
            if (current_time - self._last_scaling_timestamp_sec) < self._config.cooldown_sec:
                return ScalingDecision(
                    action=ScalingAction.NO_ACTION,
                    worker_id=None,
                    generation=None,
                    reason=f"Cooldown active ({current_time - self._last_scaling_timestamp_sec:.1f}s < {self._config.cooldown_sec}s)",
                    timestamp_sec=current_time,
                )

            active_count = self.get_active_worker_count()

            # 2. Scale-Up Evaluation
            if pending_queue_depth > self._config.high_queue_threshold:
                if active_count < self._config.max_worker_replicas:
                    decision = self._execute_scale_up(current_time)
                    if decision.action == ScalingAction.SCALE_UP:
                        self._last_scaling_timestamp_sec = current_time
                    return decision

            # 3. Scale-Down Evaluation
            if pending_queue_depth <= self._config.low_queue_threshold:
                if active_count > self._config.min_worker_replicas:
                    decision = self._execute_scale_down(current_time)
                    if decision.action in (ScalingAction.DRAIN_WORKER, ScalingAction.RETIRE_WORKER):
                        self._last_scaling_timestamp_sec = current_time
                    return decision

            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                worker_id=None,
                generation=None,
                reason="Capacity balanced; queue within threshold",
                timestamp_sec=current_time,
            )

    # -------------------------------------------------------------------------
    # Scale-Up Decision Execution
    # -------------------------------------------------------------------------

    def _execute_scale_up(self, now_sec: float) -> ScalingDecision:
        """
        Executes scale-up by invoking ResourceAuthority.scale_up_register_worker().
        Does NOT bypass authority fencing or tombstone checks.
        """
        self._next_worker_id += 1
        new_w_id = self._next_worker_id
        gen = 1

        try:
            w_rec = self._authority.scale_up_register_worker(
                worker_id=new_w_id,
                generation=gen,
                capabilities=self._config.default_capabilities,
            )
            self._worker_registration_timestamps[new_w_id] = now_sec

            logger.info(f"Autoscaler scale-up registered worker {new_w_id} gen {gen}")
            return ScalingDecision(
                action=ScalingAction.SCALE_UP,
                worker_id=new_w_id,
                generation=gen,
                reason=f"Scale-up registered worker {new_w_id} gen {gen}",
                timestamp_sec=now_sec,
            )
        except Exception as e:
            logger.error(f"Scale-up failed for worker {new_w_id}: {e}")
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                worker_id=new_w_id,
                generation=gen,
                reason=f"Scale-up failed: {e}",
                timestamp_sec=now_sec,
            )

    # -------------------------------------------------------------------------
    # Scale-Down Decision Execution
    # -------------------------------------------------------------------------

    def _execute_scale_down(self, now_sec: float) -> ScalingDecision:
        """
        Executes scale-down by selecting a worker candidate and calling
        ResourceAuthority.scale_down_drain_worker() and scale_down_retire_worker().

        Enforces Scale-Down Safety:
            - Minimum residency window check
            - Quiescence & retirable validation via ResourceAuthority.is_worker_retirable()
            - ZERO physical reuse before full exit.
        """
        # Find candidate worker (active or draining)
        candidates = [
            w for w in self._authority._worker_states.values()
            if w.state in (WorkerLifecycleState.ACTIVE, WorkerLifecycleState.DRAINING, WorkerLifecycleState.QUIESCENT)
        ]

        if not candidates:
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                worker_id=None,
                generation=None,
                reason="No candidate worker eligible for scale-down",
                timestamp_sec=now_sec,
            )

        # Prefer candidate with fewest active assignments and oldest registration
        candidates.sort(key=lambda w: (
            w.active_assignments_count,
            -self._worker_registration_timestamps.get(w.worker_id, 0),
        ))

        candidate = candidates[0]
        w_id = candidate.worker_id
        reg_ts = self._worker_registration_timestamps.get(w_id, 0)

        # Enforce Minimum Residency Window Hysteresis
        if (now_sec - reg_ts) < self._config.min_residency_sec:
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                worker_id=w_id,
                generation=candidate.generation,
                reason=f"Worker {w_id} has not satisfied min residency ({now_sec - reg_ts:.1f}s < {self._config.min_residency_sec}s)",
                timestamp_sec=now_sec,
            )

        # Step 1: Draining Transition (Stop new placements)
        if candidate.state == WorkerLifecycleState.ACTIVE:
            self._authority.scale_down_drain_worker(w_id)
            logger.info(f"Autoscaler transitioned worker {w_id} to DRAINING")

        # Step 2: Quiescence & Retirable Safety Check
        if self._authority.is_worker_retirable(w_id):
            try:
                ret_rec = self._authority.scale_down_retire_worker(w_id)
                self._worker_registration_timestamps.pop(w_id, None)
                logger.info(f"Autoscaler successfully retired worker {w_id} gen {ret_rec.generation}")

                return ScalingDecision(
                    action=ScalingAction.RETIRE_WORKER,
                    worker_id=w_id,
                    generation=ret_rec.generation,
                    reason=f"Worker {w_id} quiescent and successfully retired",
                    timestamp_sec=now_sec,
                )
            except WorkerNotQuiescentError as e:
                return ScalingDecision(
                    action=ScalingAction.DRAIN_WORKER,
                    worker_id=w_id,
                    generation=candidate.generation,
                    reason=f"Worker {w_id} draining; awaiting quiescence: {e}",
                    timestamp_sec=now_sec,
                )

        return ScalingDecision(
            action=ScalingAction.DRAIN_WORKER,
            worker_id=w_id,
            generation=candidate.generation,
            reason=f"Worker {w_id} draining; active assignments/reservations exist",
            timestamp_sec=now_sec,
        )
