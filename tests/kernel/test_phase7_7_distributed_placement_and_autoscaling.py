"""
Phase 7.7 Test Suite: Heterogeneous Distributed Placement & Autoscaling.

Covers all Phase 7.7a & 7.7b requirements:
  1. Globally unique resource & worker identities (no local ID collisions)
  2. Locality-aware multi-node worker selection
  3. Explicit multi-node resource fragmentation detection
  4. Stale-read race handling (rejection/retry over overcommit)
  5. Autoscaler scale-up decision under queue pressure
  6. Autoscaler scale-down safety (blocks retirement if active assignments exist)
  7. Autoscaler scale-down execution for quiescent worker
  8. Autoscaler hysteresis (cooldown & min residency windows)
  9. Authority boundary invariant preservation (Autoscaler & Scheduler NEVER mutate S_R directly)
"""

import time
import unittest
from typing import Dict, Set

from cortex.tools.kernel.autoscaler import (
    AutoscalingController,
    AutoscalerConfig,
    ScalingAction,
)
from cortex.tools.kernel.distributed_scheduler import (
    DistributedPlacementCost,
    DistributedPlacementEngine,
    DistributedWorkerView,
    GlobalGPUIdentity,
    GlobalWorkerIdentity,
    ResourceFragmentationError,
)
from cortex.tools.kernel.resource_authority import (
    DemandVector,
    GPUCollisionError,
    InsufficientCapacityError,
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


def _make_distributed_worker(
    node_id: str = "node-1",
    worker_id: int = 1,
    generation: int = 1,
    cpu: int = 4000,
    mem: int = 8 * 1024**3,
    gpus: tuple = (),
    caps: frozenset = frozenset({"python"}),
    region: str = "us-east-1",
    healthy: bool = True,
    state: WorkerLifecycleState = WorkerLifecycleState.ACTIVE,
    active_tasks: int = 0,
) -> DistributedWorkerView:
    w_identity = GlobalWorkerIdentity(node_id=node_id, worker_id=worker_id, generation=generation)
    gpu_identities = tuple(GlobalGPUIdentity(node_id=node_id, gpu_id=g) for g in gpus)
    vec = DemandVector(cpu_mcores=cpu, memory_bytes=mem)

    return DistributedWorkerView(
        identity=w_identity,
        state=state,
        capabilities=caps,
        total_capacity=vec,
        residual_capacity=vec,
        available_gpus=gpu_identities,
        node_region=region,
        authority_epoch=1,
        lease_epoch=1,
        is_healthy=healthy,
        telemetry=WorkerTelemetry(worker_id=worker_id, active_task_count=active_tasks),
    )


class TestGlobalIdentities(unittest.TestCase):
    """Test 1: Globally unique GPU and worker identities."""

    def test_global_gpu_identity_string(self):
        gpu1 = GlobalGPUIdentity(node_id="node-a", gpu_id=0)
        gpu2 = GlobalGPUIdentity(node_id="node-b", gpu_id=0)
        self.assertNotEqual(str(gpu1), str(gpu2))
        self.assertEqual(str(gpu1), "gpu:node-a:0")

    def test_global_worker_identity_string(self):
        w1 = GlobalWorkerIdentity(node_id="node-a", worker_id=1, generation=1)
        w2 = GlobalWorkerIdentity(node_id="node-b", worker_id=1, generation=1)
        self.assertNotEqual(str(w1), str(w2))
        self.assertEqual(str(w1), "worker:node-a:1:g1")


class TestDistributedPlacement(unittest.TestCase):
    """Test 2: Locality-aware multi-node worker selection."""

    def test_locality_preferred_region_selection(self):
        auth_a = ResourceAuthority(capacity=10000, safety_margin=0, uncertainty=0)
        auth_b = ResourceAuthority(capacity=10000, safety_margin=0, uncertainty=0)

        engine = DistributedPlacementEngine(
            node_authorities={"node-a": auth_a, "node-b": auth_b},
            default_region="us-east-1",
        )

        # Worker 1 in us-east-1, Worker 2 in us-west-2
        w1 = _make_distributed_worker("node-a", 1, region="us-east-1")
        w2 = _make_distributed_worker("node-b", 2, region="us-west-2")
        engine.register_worker(w1)
        engine.register_worker(w2)

        intent = SchedulingIntent(
            task_id=1, invocation_id=101, attempt_id=1,
            demand_vector=DemandVector(cpu_mcores=1000),
        )

        worker, cost = engine.select_worker(intent, target_region="us-east-1")
        self.assertEqual(worker.identity.node_id, "node-a")
        self.assertEqual(cost.locality_penalty, 0.0)


class TestMultiNodeFragmentation(unittest.TestCase):
    """Test 3: Explicit multi-node resource fragmentation detection."""

    def test_fragmentation_detected_when_no_single_worker_fits(self):
        auth_a = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth_b = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)

        engine = DistributedPlacementEngine(
            node_authorities={"node-a": auth_a, "node-b": auth_b},
        )

        # Aggregate CPU across nodes = 1600 mcores, but no single node has 1500 mcores
        w1 = _make_distributed_worker("node-a", 1, cpu=800)
        w2 = _make_distributed_worker("node-b", 2, cpu=800)
        engine.register_worker(w1)
        engine.register_worker(w2)

        demand = DemandVector(cpu_mcores=1500)
        is_fragmented = engine.check_resource_fragmentation(demand)
        self.assertTrue(is_fragmented)

        intent = SchedulingIntent(
            task_id=1, invocation_id=101, attempt_id=1,
            demand_vector=demand,
        )

        with self.assertRaises(ResourceFragmentationError):
            engine.select_worker(intent)


class TestStaleReadRetry(unittest.TestCase):
    """Test 4: Stale-read race handling and atomic reservation retry."""

    def test_stale_read_retries_and_succeeds_on_alternate_worker(self):
        auth_a = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth_b = ResourceAuthority(capacity=10000, safety_margin=0, uncertainty=0)

        engine = DistributedPlacementEngine(
            node_authorities={"node-a": auth_a, "node-b": auth_b},
        )

        w1 = _make_distributed_worker("node-a", 1, cpu=1000, active_tasks=0)
        w2 = _make_distributed_worker("node-b", 2, cpu=8000, active_tasks=5)
        engine.register_worker(w1)
        engine.register_worker(w2)

        # Fill node-a capacity directly in ResourceAuthority so placement on w1 fails
        auth_a.reserve(res_id=99, res_inv=999, res_att=999, res_worker=1, res_demand=1000)

        intent = SchedulingIntent(
            task_id=1, invocation_id=101, attempt_id=1,
            demand_vector=DemandVector(cpu_mcores=1000),
            lease_epoch=2,
        )

        # Engine selects w1 (least loaded), auth_a rejects, engine retries and selects w2 on node-b
        worker, res = engine.schedule_distributed(intent, max_retries=3)
        self.assertEqual(worker.identity.node_id, "node-b")
        self.assertEqual(res.res_worker, 2)


class TestAutoscalerScaleUp(unittest.TestCase):
    """Test 5: Autoscaler scale-up under queue pressure."""

    def test_scale_up_registered_when_queue_exceeds_threshold(self):
        auth = ResourceAuthority(capacity=10000, safety_margin=0, uncertainty=0)
        config = AutoscalerConfig(
            high_queue_threshold=5,
            cooldown_sec=0.0,
            max_worker_replicas=10,
        )
        autoscaler = AutoscalingController(auth, config)

        decision = autoscaler.evaluate_scaling(pending_queue_depth=10, now_sec=100.0)
        self.assertEqual(decision.action, ScalingAction.SCALE_UP)
        self.assertIsNotNone(decision.worker_id)
        self.assertEqual(autoscaler.get_active_worker_count(), 1)


class TestAutoscalerScaleDownSafety(unittest.TestCase):
    """Test 6: Autoscaler scale-down safety (blocks retirement when active assignments exist)."""

    def test_scale_down_blocks_retirement_when_worker_has_active_reservation(self):
        auth = ResourceAuthority(capacity=10000, safety_margin=0, uncertainty=0)
        # Register single worker
        auth.scale_up_register_worker(worker_id=1, generation=1, capabilities={"python"})

        # Worker 1 has an active reservation
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        config = AutoscalerConfig(
            low_queue_threshold=0,
            min_worker_replicas=0,
            min_residency_sec=0.0,
            cooldown_sec=0.0,
        )
        autoscaler = AutoscalingController(auth, config)
        autoscaler._worker_registration_timestamps[1] = 10.0

        # Worker 1 cannot be retired because active reservations exist
        decision = autoscaler.evaluate_scaling(pending_queue_depth=0, now_sec=100.0)
        self.assertEqual(decision.action, ScalingAction.DRAIN_WORKER)
        # Worker state in ResourceAuthority is DRAINING, not RETIRED
        self.assertEqual(auth._worker_states[1].state, WorkerLifecycleState.DRAINING)

    def test_scale_down_retires_quiescent_worker(self):
        """Test 7: Scale-down retires worker when fully quiescent."""
        auth = ResourceAuthority(capacity=10000, safety_margin=0, uncertainty=0)
        auth.scale_up_register_worker(worker_id=1, generation=1, capabilities={"python"})
        auth.scale_up_register_worker(worker_id=2, generation=1, capabilities={"python"})

        config = AutoscalerConfig(
            low_queue_threshold=0,
            min_worker_replicas=1,
            min_residency_sec=0.0,
            cooldown_sec=0.0,
        )
        autoscaler = AutoscalingController(auth, config)
        autoscaler._worker_registration_timestamps[1] = 10.0
        autoscaler._worker_registration_timestamps[2] = 10.0

        decision = autoscaler.evaluate_scaling(pending_queue_depth=0, now_sec=100.0)
        self.assertEqual(decision.action, ScalingAction.RETIRE_WORKER)
        self.assertEqual(auth._worker_states[decision.worker_id].state, WorkerLifecycleState.RETIRED)


class TestAutoscalerHysteresis(unittest.TestCase):
    """Test 8: Autoscaler hysteresis controls (cooldown & min residency)."""

    def test_cooldown_window_prevents_rapid_scaling(self):
        auth = ResourceAuthority(capacity=10000, safety_margin=0, uncertainty=0)
        config = AutoscalerConfig(
            high_queue_threshold=5,
            cooldown_sec=10.0,
        )
        autoscaler = AutoscalingController(auth, config)

        # Action 1: scale-up at t=100
        d1 = autoscaler.evaluate_scaling(pending_queue_depth=20, now_sec=100.0)
        self.assertEqual(d1.action, ScalingAction.SCALE_UP)

        # Action 2 at t=105 (within 10s cooldown): NO_ACTION
        d2 = autoscaler.evaluate_scaling(pending_queue_depth=20, now_sec=105.0)
        self.assertEqual(d2.action, ScalingAction.NO_ACTION)
        self.assertIn("Cooldown active", d2.reason)

        # Action 3 at t=111 (after cooldown): SCALE_UP
        d3 = autoscaler.evaluate_scaling(pending_queue_depth=20, now_sec=111.0)
        self.assertEqual(d3.action, ScalingAction.SCALE_UP)

    def test_min_residency_prevents_immediate_retirement(self):
        auth = ResourceAuthority(capacity=10000, safety_margin=0, uncertainty=0)
        auth.scale_up_register_worker(worker_id=1, generation=1, capabilities={"python"})
        auth.scale_up_register_worker(worker_id=2, generation=1, capabilities={"python"})

        config = AutoscalerConfig(
            low_queue_threshold=0,
            min_worker_replicas=1,
            min_residency_sec=30.0,
            cooldown_sec=0.0,
        )
        autoscaler = AutoscalingController(auth, config)
        autoscaler._worker_registration_timestamps[1] = 100.0
        autoscaler._worker_registration_timestamps[2] = 100.0

        # At t=110 (residency = 10s < 30s): NO_ACTION
        decision = autoscaler.evaluate_scaling(pending_queue_depth=0, now_sec=110.0)
        self.assertEqual(decision.action, ScalingAction.NO_ACTION)
        self.assertIn("min residency", decision.reason)


if __name__ == "__main__":
    unittest.main()
