"""
Issue #34 (Phase 5.1 Hardening Gate): Adversarial Verification & Heap Memory Soak
Coq Target: Phase4RoutingRefinement.v
"""

import gc
import time
import tracemalloc
import unittest

from cortex.tools.kernel.load_balancer import (
    InvalidEpochError,
    InvalidWorkerError,
    LoadBalancerError,
    ProductionDynamicLoadBalancer,
    WorkerHealthStatus,
)


class TestLoadBalancerHardeningGate(unittest.TestCase):
    """Phase 5.1 Hardening Gate Adversarial Test Suite."""

    def test_invalid_constructor_and_registration_boundaries(self) -> None:
        """Validates constructor and boundary parameters."""
        with self.assertRaises(LoadBalancerError):
            ProductionDynamicLoadBalancer(heartbeat_timeout_ms=-10)

        with self.assertRaises(LoadBalancerError):
            ProductionDynamicLoadBalancer(max_registered_workers=0)

        lb = ProductionDynamicLoadBalancer()

        with self.assertRaises(LoadBalancerError):
            lb.register_worker("", capabilities={"compute"}, max_concurrency=5)

        with self.assertRaises(LoadBalancerError):
            lb.register_worker("w1", capabilities={"compute"}, max_concurrency=-1)

    def test_epoch_monotonicity_and_self_reassignment(self) -> None:
        """Rejects E_new <= E_old and same-worker reassignment."""
        lb = ProductionDynamicLoadBalancer()
        lb.register_worker("w1", capabilities={"task"}, max_concurrency=5)
        lb.register_worker("w2", capabilities={"task"}, max_concurrency=5)

        lb.assign_execution("w1", "inv_1", current_epoch=10)

        # Rejects equal epoch
        with self.assertRaises(InvalidEpochError):
            lb.assign_execution("w2", "inv_1", current_epoch=10)

        # Rejects lower epoch
        with self.assertRaises(InvalidEpochError):
            lb.assign_execution("w2", "inv_1", current_epoch=5)

        # Rejects self-reassignment even with monotonic epoch
        with self.assertRaises(LoadBalancerError):
            lb.assign_execution("w1", "inv_1", current_epoch=11)

        # Valid monotonic reassignment
        lb.assign_execution("w2", "inv_1", current_epoch=11)
        self.assertTrue(lb.validate_commit_lease("inv_1", "w2", 11))
        self.assertEqual(lb._workers["w1"].active_load, 0)
        self.assertEqual(lb._workers["w2"].active_load, 1)

    def test_ownership_scoped_lease_validation_and_release(self) -> None:
        """Validates that wrong-worker commit and stale-worker releases are safely rejected."""
        lb = ProductionDynamicLoadBalancer()
        lb.register_worker("w1", capabilities={"task"}, max_concurrency=5)
        lb.register_worker("w2", capabilities={"task"}, max_concurrency=5)

        lb.assign_execution("w1", "inv_100", current_epoch=1)

        # Wrong worker with correct epoch MUST fail validation
        self.assertFalse(lb.validate_commit_lease("inv_100", "w2", 1))

        # Monotonic reassignment to w2
        lb.assign_execution("w2", "inv_100", current_epoch=2)

        # Stale Worker w1 tries to release -> rejected, w2 load unaffected
        with self.assertRaises(InvalidWorkerError):
            lb.release_execution("w1", "inv_100")

        self.assertEqual(lb._workers["w2"].active_load, 1)

        # Legitimate owner release -> load decremented correctly
        lb.release_execution("w2", "inv_100", lease_epoch=2)
        self.assertEqual(lb._workers["w2"].active_load, 0)

    def test_worker_eviction_and_task_quarantine(self) -> None:
        """Ensures active tasks on evicted workers move to quarantine state rather than floating."""
        lb = ProductionDynamicLoadBalancer(heartbeat_timeout_ms=100, worker_ttl_ms=200)
        lb.register_worker("w1", capabilities={"task"}, max_concurrency=5)

        t0 = int(time.time() * 1000)
        lb.assign_execution("w1", "inv_orphan", current_epoch=1, current_unix_ms=t0)

        # Expire worker w1 via TTL
        lb._evict_stale_workers_unlocked(t0 + 500, force_evict_unhealthy=True)

        self.assertNotIn("w1", lb._workers)
        self.assertNotIn("inv_orphan", lb._assignments)

        quarantined = lb.get_quarantined_invocations()
        self.assertIn("inv_orphan", quarantined)
        self.assertEqual(quarantined["inv_orphan"].worker_id, "w1")

    def test_real_heap_memory_and_object_retention_soak(self) -> None:
        """
        Uses tracemalloc to prove real memory flatness (zero leak) over 100,000 cycles.
        """
        lb = ProductionDynamicLoadBalancer(max_registered_workers=10)
        for i in range(5):
            lb.register_worker(f"w_{i}", capabilities={"task"}, max_concurrency=50)

        gc.collect()
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        for i in range(100_000):
            inv_id = f"task_{i}"
            w_id = f"w_{i % 5}"
            lb.assign_execution(w_id, inv_id, current_epoch=1)
            lb.release_execution(w_id, inv_id, lease_epoch=1)

        gc.collect()
        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_memory_diff_kb = sum(stat.size_diff for stat in top_stats) / 1024

        self.assertEqual(len(lb._assignments), 0)
        self.assertEqual(len(lb.get_quarantined_invocations()), 0)
        # Memory diff threshold < 50 KB noise margin over 100,000 cycles
        self.assertLess(total_memory_diff_kb, 50.0)


if __name__ == "__main__":
    unittest.main()
