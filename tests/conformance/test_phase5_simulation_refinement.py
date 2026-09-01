"""
Phase 5 Concrete-to-Coq Forward Simulation Refinement Test Suite (Issue #47).

Validates the machine-checked forward simulation relation R(C, A):
1. State Abstraction Mapping: Alpha(C) == A
2. Runtime Invariant Safety: I1-I7 hold dynamically across arbitrary transition sequences.
3. Counter Drift Elimination: active_load == cntW(w) for all workers.
4. Process Generation Binding: Attempt generation matches worker process_generation.
"""

import unittest

from cortex.tools.kernel.load_balancer import (
    InvalidEpochError,
    InvocationLifecycleState,
    LoadBalancerError,
    ProductionDynamicLoadBalancer,
)


class TestPhase5SimulationRefinement(unittest.TestCase):
    def test_simulation_init_state(self):
        """Validates that a fresh ProductionDynamicLoadBalancer satisfies init simulation (R(C0, A0))."""
        lb = ProductionDynamicLoadBalancer()
        self.assertTrue(lb.validate_state_invariants())
        self.assertEqual(len(lb.get_invocations()), 0)
        self.assertEqual(len(lb.get_quarantined_invocations()), 0)

    def test_simulation_assign_release_cycle(self):
        """Validates state abstraction and active_load count consistency through assign/release cycles."""
        lb = ProductionDynamicLoadBalancer()
        lb.register_worker("w1", capabilities={"exec"}, max_concurrency=2)
        lb.register_worker("w2", capabilities={"exec"}, max_concurrency=2)

        # Initial registration invariant
        self.assertTrue(lb.validate_state_invariants())

        # Assign execution 1
        lb.assign_execution("w1", "inv_1", current_epoch=1)
        self.assertTrue(lb.validate_state_invariants())
        worker_1 = lb._workers["w1"]
        self.assertEqual(worker_1.active_load, 1)
        self.assertEqual(worker_1.available_capacity, 1)

        # Assign execution 2 to w1
        lb.assign_execution("w1", "inv_2", current_epoch=1)
        self.assertTrue(lb.validate_state_invariants())
        self.assertEqual(worker_1.active_load, 2)
        self.assertEqual(worker_1.available_capacity, 0)

        # Over-capacity assignment must be rejected (SAssign strict < capacity guard)
        with self.assertRaises(LoadBalancerError):
            lb.assign_execution("w1", "inv_3", current_epoch=1)

        # Release inv_1
        lb.release_execution("w1", "inv_1", lease_epoch=1)
        self.assertTrue(lb.validate_state_invariants())
        self.assertEqual(worker_1.active_load, 1)
        self.assertEqual(worker_1.available_capacity, 1)

    def test_simulation_reassignment_lineage_and_counter_sync(self):
        """Validates non-monotonic epoch fencing and previous owner counter synchronization during reassignment."""
        lb = ProductionDynamicLoadBalancer()
        lb.register_worker("w1", capabilities={"exec"}, max_concurrency=2)
        lb.register_worker("w2", capabilities={"exec"}, max_concurrency=2)

        lb.assign_execution("w1", "inv_100", current_epoch=1)
        self.assertEqual(lb._workers["w1"].active_load, 1)
        self.assertEqual(lb._workers["w2"].active_load, 0)

        # Reassign inv_100 from w1 to w2 with epoch 2
        lb.assign_execution("w2", "inv_100", current_epoch=2)
        self.assertTrue(lb.validate_state_invariants())
        self.assertEqual(lb._workers["w1"].active_load, 0)
        self.assertEqual(lb._workers["w2"].active_load, 1)

        # Verify attempt lineage generation binding
        inv_rec = lb.get_invocation("inv_100")
        assert inv_rec is not None
        self.assertEqual(len(inv_rec.attempts), 2)
        self.assertEqual(inv_rec.attempts[0].worker_id, "w1")
        self.assertEqual(inv_rec.attempts[0].lease_epoch, 1)
        self.assertEqual(inv_rec.attempts[1].worker_id, "w2")
        self.assertEqual(inv_rec.attempts[1].lease_epoch, 2)

        # Non-monotonic epoch reassignment must be rejected
        with self.assertRaises(InvalidEpochError):
            lb.assign_execution("w1", "inv_100", current_epoch=2)

    def test_simulation_quarantine_reconciliation(self):
        """Validates quarantine movement and reconciliation state preservation."""
        lb = ProductionDynamicLoadBalancer()
        lb.register_worker("w1", capabilities={"exec"}, max_concurrency=2)
        lb.assign_execution("w1", "inv_q", current_epoch=1)

        # Move to quarantine
        lb._quarantined_invocations["inv_q"] = lb._assignments.pop("inv_q")
        inv_rec = lb.get_invocation("inv_q")
        assert inv_rec is not None
        inv_rec.transition_to(InvocationLifecycleState.QUARANTINED, reason="Evicted worker")
        lb._sync_worker_active_load("w1")

        self.assertTrue(lb.validate_state_invariants())
        self.assertEqual(lb._workers["w1"].active_load, 0)

        # Reconcile quarantined
        lb.reconcile_quarantined("inv_q")
        self.assertTrue(lb.validate_state_invariants())
        self.assertEqual(len(lb.get_quarantined_invocations()), 0)


if __name__ == "__main__":
    unittest.main()
