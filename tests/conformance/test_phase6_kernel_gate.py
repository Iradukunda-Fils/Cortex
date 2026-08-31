"""
Phase 6.0 Kernel Gate Conformance Test Suite (Issues #46 - #49)
Normative Architecture Baseline: v1.5.1-FINAL-FROZEN
Specification: Section 2 & 10 Core Kernel Obligations

Coverage:
- Issue #46: State Machine & Invocation Lifecycle FSM (ADMITTED, ACTIVE, QUARANTINED, RECONCILED, COMPLETED)
- Issue #47: Universal Resource Bound & Action Validator (Count >= B_X or ByteSize >= S_X)
- Issue #48: Worker Incarnation Identity (NodeID, ProcessGeneration) & Monotonic Epoch Fencing
- Issue #49: Runtime Enforcement of the 10 Core Kernel Obligations (KernelInvariantChecker)
"""

import time
import unittest

from cortex.tools.kernel.invariant_checker import (
    KernelInvariantChecker,
    KernelInvariantViolationError,
)
from cortex.tools.kernel.load_balancer import (
    InvalidStateTransitionError,
    InvocationLifecycleState,
    InvocationRecord,
    ProductionDynamicLoadBalancer,
    StaleWorkerIncarnationError,
)
from cortex.tools.kernel.resource_bounds import (
    ResourceAction,
    ResourceBoundExceededError,
    ResourceBoundRule,
    ResourceBoundValidator,
)


class TestPhase6KernelGate(unittest.TestCase):
    """Conformance test suite for Phase 6.0 Kernel Gate (Issues #46 - #49)."""

    # --- Issue #46: State Machine & Invocation Lifecycle FSM ---

    def test_issue46_invocation_fsm_disjoint_state_totality(self) -> None:
        """Validates that invocations occupy exactly one disjoint lifecycle state."""
        lb = ProductionDynamicLoadBalancer()
        lb.register_worker("w1", capabilities={"task"}, max_concurrency=5)

        # Initial Assignment -> ACTIVE
        lb.assign_execution("w1", "inv_1", current_epoch=1)
        inv = lb.get_invocation("inv_1")
        assert inv is not None
        self.assertEqual(inv.state, InvocationLifecycleState.ACTIVE)
        self.assertEqual(len(inv.attempts), 1)
        self.assertEqual(inv.attempts[0].worker_id, "w1")
        self.assertEqual(inv.attempts[0].lease_epoch, 1)

        # Reassignment -> remains ACTIVE, appends ExecutionAttempt lineage
        lb.register_worker("w2", capabilities={"task"}, max_concurrency=5)
        lb.assign_execution("w2", "inv_1", current_epoch=2)
        inv_reassigned = lb.get_invocation("inv_1")
        assert inv_reassigned is not None
        self.assertEqual(inv_reassigned.state, InvocationLifecycleState.ACTIVE)
        self.assertEqual(len(inv_reassigned.attempts), 2)
        self.assertEqual(inv_reassigned.attempts[1].worker_id, "w2")
        self.assertEqual(inv_reassigned.attempts[1].lease_epoch, 2)

        # Completion -> COMPLETED
        lb.release_execution("w2", "inv_1", lease_epoch=2)
        self.assertEqual(inv.state, InvocationLifecycleState.COMPLETED)

        # Separate invocation for Quarantine -> Reconciliation
        lb.assign_execution("w1", "inv_quarantine", current_epoch=3)
        # Evict worker w1 to move inv_quarantine to QUARANTINED state
        lb._evict_stale_workers_unlocked(int(time.time() * 1000) + 100000, force_evict_unhealthy=True)
        inv_q = lb.get_invocation("inv_quarantine")
        assert inv_q is not None
        self.assertEqual(inv_q.state, InvocationLifecycleState.QUARANTINED)

        # Reconciliation -> RECONCILED
        lb.reconcile_quarantined("inv_quarantine")
        self.assertEqual(inv_q.state, InvocationLifecycleState.RECONCILED)

    def test_issue46_reject_illegal_fsm_transitions(self) -> None:
        """Enforces rejection of illegal lifecycle transitions (e.g. COMPLETED -> ACTIVE)."""
        inv = InvocationRecord(invocation_id="inv_test")
        inv.transition_to(InvocationLifecycleState.ACTIVE)
        inv.transition_to(InvocationLifecycleState.COMPLETED)

        with self.assertRaises(InvalidStateTransitionError):
            inv.transition_to(InvocationLifecycleState.ACTIVE)

        inv.transition_to(InvocationLifecycleState.RECONCILED)

        with self.assertRaises(InvalidStateTransitionError):
            inv.transition_to(InvocationLifecycleState.ACTIVE)

    # --- Issue #47: Universal Resource Bound & Action Validator ---

    def test_issue47_resource_bound_count_and_byte_triggers(self) -> None:
        """Validates Count >= B_X or ByteSize >= S_X triggers with action policies."""
        validator = ResourceBoundValidator()
        validator.register_rule(ResourceBoundRule("test_queue", max_count=5, max_bytes=100, action=ResourceAction.REJECT))

        # Under limit -> PASS
        validator.validate_or_raise("test_queue", prospective_count=4, prospective_bytes=80)

        # Count limit exceeded -> REJECT
        with self.assertRaises(ResourceBoundExceededError) as ctx_count:
            validator.validate_or_raise("test_queue", prospective_count=5, prospective_bytes=50)
        self.assertEqual(ctx_count.exception.bound_type, "count")

        # Byte limit exceeded -> REJECT
        with self.assertRaises(ResourceBoundExceededError) as ctx_bytes:
            validator.validate_or_raise("test_queue", prospective_count=3, prospective_bytes=100)
        self.assertEqual(ctx_bytes.exception.bound_type, "bytes")

    # --- Issue #48: Worker Incarnation & Monotonic Epoch Fencing ---

    def test_issue48_worker_incarnation_identity_and_fencing(self) -> None:
        """Validates process generation tracking and fencing out stale incarnations."""
        lb = ProductionDynamicLoadBalancer()

        # Worker Alpha (Generation 1)
        lb.register_worker("w1", capabilities={"task"}, max_concurrency=5, process_generation=1)
        lb.assign_execution("w1", "inv_10", current_epoch=1)

        # Re-registering with stale generation (Gen 0 < Gen 1) -> REJECT
        with self.assertRaises(StaleWorkerIncarnationError):
            lb.register_worker("w1", capabilities={"task"}, max_concurrency=5, process_generation=0)

        # Re-registering with higher generation (Gen 2 > Gen 1) -> Fences out Gen 1 active tasks to Quarantine
        lb.register_worker("w1", capabilities={"task"}, max_concurrency=5, process_generation=2)

        quarantined = lb.get_quarantined_invocations()
        self.assertIn("inv_10", quarantined)

        inv_rec = lb.get_invocation("inv_10")
        assert inv_rec is not None
        self.assertEqual(inv_rec.state, InvocationLifecycleState.QUARANTINED)

    # --- Issue #49: Runtime Enforcement of the 10 Core Kernel Obligations ---

    def test_issue49_kernel_invariant_checker_all_proofs(self) -> None:
        """Executes runtime assertions for all 10 Core Kernel Proof Obligations."""
        # Proof 1: Assignment Uniqueness
        KernelInvariantChecker.verify_proof_1_assignment_uniqueness({"inv_1": "w1", "inv_2": "w2"})

        # Proof 2: Worker Capacity Bounds
        class MockWorker:
            def __init__(self, active: int, max_c: int) -> None:
                self.active_load = active
                self.max_concurrency = max_c

        workers = {"w1": MockWorker(2, 5), "w2": MockWorker(0, 5)}
        KernelInvariantChecker.verify_proof_2_worker_capacity_bounds(workers)

        with self.assertRaises(KernelInvariantViolationError):
            KernelInvariantChecker.verify_proof_2_worker_capacity_bounds({"w1": MockWorker(6, 5)})

        # Proof 3: Capacity Conservation
        KernelInvariantChecker.verify_proof_3_capacity_conservation(workers, {"inv_1": "w1", "inv_2": "w1"})

        with self.assertRaises(KernelInvariantViolationError):
            KernelInvariantChecker.verify_proof_3_capacity_conservation(workers, {"inv_1": "w1"})

        # Proof 4: Lease Fencing
        KernelInvariantChecker.verify_proof_4_lease_fencing(requested_lease_epoch=10, active_lease_epoch=10, invocation_id="inv_1")
        with self.assertRaises(KernelInvariantViolationError):
            KernelInvariantChecker.verify_proof_4_lease_fencing(requested_lease_epoch=9, active_lease_epoch=10, invocation_id="inv_1")

        # Proof 5: Worker Incarnation Fencing
        KernelInvariantChecker.verify_proof_5_incarnation_fencing(presented_generation=2, active_generation=2, worker_id="w1")
        with self.assertRaises(KernelInvariantViolationError):
            KernelInvariantChecker.verify_proof_5_incarnation_fencing(presented_generation=1, active_generation=2, worker_id="w1")

        # Proof 6: Authority Epoch Fencing
        KernelInvariantChecker.verify_proof_6_authority_epoch_fencing(presented_authority_epoch=5, active_authority_epoch=5)
        with self.assertRaises(KernelInvariantViolationError):
            KernelInvariantChecker.verify_proof_6_authority_epoch_fencing(presented_authority_epoch=4, active_authority_epoch=5)

        # Proof 7: Quarantine Containment
        quarantined = {"inv_q1": True}
        with self.assertRaises(KernelInvariantViolationError):
            KernelInvariantChecker.verify_proof_7_quarantine_containment(quarantined, "inv_q1")

        # Proof 8: WAL Deterministic Replay
        def dummy_replay(wal_bytes: bytes) -> str:
            return f"replayed_{len(wal_bytes)}"

        KernelInvariantChecker.verify_proof_8_wal_replay_determinism(dummy_replay, b"frame_1", b"frame_1")

        # Proof 9: Universal Resource Bounds
        validator = ResourceBoundValidator()
        validator.register_rule(ResourceBoundRule("res1", max_count=10, max_bytes=1000))
        KernelInvariantChecker.verify_proof_9_universal_resource_bounds(validator, {"res1": 5}, {"res1": 500})

        with self.assertRaises(KernelInvariantViolationError):
            KernelInvariantChecker.verify_proof_9_universal_resource_bounds(validator, {"res1": 15}, {"res1": 500})

        # Proof 10: Recovery Invariant Preservation
        def invariant_fn(state: str) -> bool:
            return state.startswith("replayed_")

        KernelInvariantChecker.verify_proof_10_recovery_invariant_preservation(dummy_replay, invariant_fn, b"valid_prefix")

    def test_derived_capability_index_invariant_i9(self) -> None:
        """
        Issue #50.d / Invariant I_9: Derived Capability Index Consistency Test.
        Formula: w in Index[c] <==> w in W and c in Capabilities(w).
        Validates index consistency across registration, eviction, generation updates, and WAL rebuild.
        """
        lb = ProductionDynamicLoadBalancer()
        lb.register_worker("w1", capabilities={"task_a", "task_b"}, max_concurrency=5, process_generation=1)
        lb.register_worker("w2", capabilities={"task_b", "task_c"}, max_concurrency=5, process_generation=1)

        # 1. Check initial index consistency
        lb.assert_capability_index_consistency()
        KernelInvariantChecker.verify_derived_capability_index_consistency(lb._workers, lb._capability_index)

        # 2. Update process generation / replacement
        lb.register_worker("w1", capabilities={"task_a", "task_d"}, max_concurrency=5, process_generation=2)
        lb.assert_capability_index_consistency()

        # 3. Evict worker
        now_ms = int(time.time() * 1000)
        lb._evict_stale_workers_unlocked(now_ms + 1000000, force_evict_unhealthy=True)
        lb.assert_capability_index_consistency()
        KernelInvariantChecker.verify_derived_capability_index_consistency(lb._workers, lb._capability_index)

        # 4. Test WAL Recovery Rebuild Semantics (WAL -> Replay(S_A) -> Index = f(S_A))
        lb.register_worker("w3", capabilities={"inference", "embedding"}, max_concurrency=10)
        lb.rebuild_capability_index()
        lb.assert_capability_index_consistency()
        KernelInvariantChecker.verify_derived_capability_index_consistency(lb._workers, lb._capability_index)


if __name__ == "__main__":
    unittest.main()

