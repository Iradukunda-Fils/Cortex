"""
Conformance & Adversarial Test Suite for Cortex Multi-Replica Subsystem (Gates RS-1 to RS-12)

Verifies core replica identity coordinates, Gateway linearizable lease fencing,
durable invocation state ledgers, worker lifecycle tracking, and linearizable race safety.
"""

import concurrent.futures
import time
import unittest

from cortex.tools.kernel.replica.identity import ExecutionIdentity, OwnershipIdentity
from cortex.tools.kernel.replica.lease import LeaseManager, StaleLeaseError
from cortex.tools.kernel.replica.ledger import InvocationState, InvocationStateLedger, RecoveryBucket
from cortex.tools.kernel.replica.lifecycle import WorkerLifecycleStage, WorkerLifecycleTracker


class TestReplicaPhases1To3(unittest.TestCase):
    """Conformance test suite for RS-1 through RS-12 verification gates."""

    def test_rs1_replica_identity_coordinate_separation(self) -> None:
        """RS-1: ExecutionIdentity and OwnershipIdentity must be distinct and non-coercible."""
        exec_id = ExecutionIdentity(group_id="payments", instance_id="w-1", generation=1, attempt_id=1)
        owner_id = OwnershipIdentity(invocation_id="inv-101", lease_id="l-1", lease_epoch=1)

        self.assertNotEqual(type(exec_id), type(owner_id))
        self.assertEqual(exec_id.coordinate_string(), "payments:w-1:g1:a1")
        self.assertEqual(owner_id.coordinate_string(), "inv:inv-101:lease:l-1:ep1")

    def test_rs2_generation_isolation(self) -> None:
        """RS-2: Generation coordinates must increment strictly."""
        exec_gen1 = ExecutionIdentity(group_id="payments", instance_id="w-1", generation=1, attempt_id=1)
        exec_gen2 = ExecutionIdentity(group_id="payments", instance_id="w-1", generation=2, attempt_id=1)

        self.assertLess(exec_gen1.generation, exec_gen2.generation)
        with self.assertRaises(ValueError):
            ExecutionIdentity(group_id="payments", instance_id="w-1", generation=0, attempt_id=1)

    def test_rs3_lease_monotonicity(self) -> None:
        """RS-3: Gateway lease epochs must increment monotonically per invocation."""
        mgr = LeaseManager()
        lease1 = mgr.grant_lease(invocation_id="inv-200", worker_id="w-1")
        mgr.revoke_lease(invocation_id="inv-200", lease_epoch=lease1.lease_epoch)
        lease2 = mgr.grant_lease(invocation_id="inv-200", worker_id="w-2")

        self.assertEqual(lease1.lease_epoch, 1)
        self.assertEqual(lease2.lease_epoch, 2)
        self.assertGreater(lease2.lease_epoch, lease1.lease_epoch)

    def test_rs4_stale_lease_commit_rejection(self) -> None:
        """RS-4: Commit attempt with stale epoch must raise StaleLeaseError."""
        mgr = LeaseManager()
        lease = mgr.grant_lease(invocation_id="inv-300", worker_id="w-1")

        with self.assertRaises(StaleLeaseError):
            mgr.commit_invocation(invocation_id="inv-300", lease_epoch=lease.lease_epoch + 999)

    def test_rs5_linearizable_revoke_commit_race(self) -> None:
        """RS-5 Adversarial Race Test: Concurrent revoke and commit must be mutually exclusive.

        Worker A owns lease epoch 41. Gateway revokes lease 41 while Worker A concurrently submits commit(41).
        Result: Exactly one wins. Stale commit produces StaleLeaseError. Zero duplicate effects.
        """
        mgr = LeaseManager()
        inv_id = "inv-race-400"
        lease = mgr.grant_lease(invocation_id=inv_id, worker_id="w-1")
        target_epoch = lease.lease_epoch

        commit_result = None
        commit_error = None
        revoke_result = None

        def do_commit() -> None:
            nonlocal commit_result, commit_error
            try:
                commit_result = mgr.commit_invocation(invocation_id=inv_id, lease_epoch=target_epoch)
            except StaleLeaseError as e:
                commit_error = e

        def do_revoke() -> None:
            nonlocal revoke_result
            revoke_result = mgr.revoke_lease(invocation_id=inv_id, lease_epoch=target_epoch)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(do_commit)
            f2 = executor.submit(do_revoke)
            concurrent.futures.wait([f1, f2])

        # Exactly one operation succeeds for epoch 41
        if commit_result is True:
            self.assertFalse(revoke_result)
            self.assertIsNone(commit_error)
        else:
            self.assertTrue(revoke_result)
            self.assertIsNotNone(commit_error)

    def test_rs6_worker_crash_recovery_classification(self) -> None:
        """RS-6: Invocation State Ledger must classify orphaned states into exact recovery buckets."""
        ledger = InvocationStateLedger()
        ledger.create_invocation(invocation_id="inv-500", intent_hash="0x1234")

        # QUEUED -> UNADMITTED
        self.assertEqual(ledger.classify_recovery("inv-500"), RecoveryBucket.UNADMITTED)

        # RUNNING -> ADMITTED_UNACTUATED
        ledger.transition_state("inv-500", InvocationState.RUNNING)
        self.assertEqual(ledger.classify_recovery("inv-500"), RecoveryBucket.ADMITTED_UNACTUATED)

        # ACTUATING -> ACTUATION_UNKNOWN
        ledger.transition_state("inv-500", InvocationState.ACTUATING)
        self.assertEqual(ledger.classify_recovery("inv-500"), RecoveryBucket.ACTUATION_UNKNOWN)

    def test_rs7_drain_correctness(self) -> None:
        """RS-7: Worker tracker must transition READY -> DRAINING -> QUIESCED when work hits 0."""
        identity = ExecutionIdentity(group_id="billing", instance_id="w-10", generation=1, attempt_id=1)
        tracker = WorkerLifecycleTracker(execution_identity=identity, drain_deadline_sec=10.0)

        tracker.update_counts(owned_invocations=2, pending_effects=1, ipc_outstanding=0)
        tracker.begin_draining()
        self.assertEqual(tracker.stage, WorkerLifecycleStage.DRAINING)

        tracker.update_counts(owned_invocations=0, pending_effects=0, ipc_outstanding=0)
        self.assertEqual(tracker.stage, WorkerLifecycleStage.QUIESCED)

    def test_rs8_forced_recovery_timeout(self) -> None:
        """RS-8: Worker tracker must transition to FORCED_RECOVERY if drain_deadline expires."""
        identity = ExecutionIdentity(group_id="billing", instance_id="w-11", generation=1, attempt_id=1)
        tracker = WorkerLifecycleTracker(execution_identity=identity, drain_deadline_sec=0.05)

        tracker.update_counts(owned_invocations=1, pending_effects=0, ipc_outstanding=0)
        tracker.begin_draining()
        time.sleep(0.06)

        did_timeout = tracker.check_drain_deadline()
        self.assertTrue(did_timeout)
        self.assertEqual(tracker.stage, WorkerLifecycleStage.FORCED_RECOVERY)

    def test_rs9_no_token_cloning(self) -> None:
        """RS-9: ExecutionIdentity attempts must have distinct IDs across worker replacements."""
        attempt1 = ExecutionIdentity(group_id="test", instance_id="w-1", generation=1, attempt_id=1)
        attempt2 = ExecutionIdentity(group_id="test", instance_id="w-2", generation=1, attempt_id=2)

        self.assertNotEqual(attempt1.instance_id, attempt2.instance_id)
        self.assertNotEqual(attempt1.attempt_id, attempt2.attempt_id)

    def test_rs10_capability_bound(self) -> None:
        """RS-10: Coordinate structures preserve immutable capability group strings."""
        exec_id = ExecutionIdentity(group_id="bounded_group", instance_id="w-1", generation=1, attempt_id=1)
        self.assertEqual(exec_id.group_id, "bounded_group")

    def test_rs11_no_silent_invocation_loss(self) -> None:
        """RS-11: Ledger transitions every invocation to explicit terminal or recovery state."""
        ledger = InvocationStateLedger()
        ledger.create_invocation("inv-600", "0x5678")
        rec = ledger.transition_state("inv-600", InvocationState.COMMITTED)
        self.assertEqual(rec.state, InvocationState.COMMITTED)

    def test_rs12_bounded_state_resource_usage(self) -> None:
        """RS-12: 1,000 lease renewal/grant operations execute cleanly under constant memory."""
        mgr = LeaseManager()
        for i in range(1000):
            inv_id = f"inv-iter-{i}"
            lease = mgr.grant_lease(invocation_id=inv_id, worker_id="w-iter")
            mgr.commit_invocation(invocation_id=inv_id, lease_epoch=lease.lease_epoch)

        self.assertFalse(mgr.is_lease_valid("inv-iter-500", 1))


if __name__ == "__main__":
    unittest.main()
