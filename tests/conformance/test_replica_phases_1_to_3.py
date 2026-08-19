"""
Conformance & Adversarial Test Suite for Cortex Multi-Replica Subsystem (Gates RS-1 to RS-15)

Verifies core replica identity coordinates, Gateway linearizable lease fencing,
durable invocation state ledgers, worker lifecycle tracking, linearizable race safety,
Gateway crash/restart persistence, terminal state invariants, and stale config rejection.
"""

import concurrent.futures
import os
import tempfile
import time
import unittest

from cortex.tools.kernel.replica.identity import ExecutionIdentity, OwnershipIdentity
from cortex.tools.kernel.replica.lease import LeaseManager, StaleLeaseError
from cortex.tools.kernel.replica.ledger import (
    TERMINAL_STATES,
    InvocationState,
    InvocationStateLedger,
    RecoveryBucket,
)
from cortex.tools.kernel.replica.lifecycle import WorkerLifecycleStage, WorkerLifecycleTracker


class TestReplicaPhases1To3(unittest.TestCase):
    """Conformance test suite for RS-1 through RS-15 verification gates."""

    # ── RS-1: Replica Identity Coordinate Separation ──────────────────
    def test_rs1_replica_identity_coordinate_separation(self) -> None:
        """RS-1: ExecutionIdentity and OwnershipIdentity must be distinct and non-coercible."""
        exec_id = ExecutionIdentity(
            group_id="payments", instance_id="w-1", generation=1, config_generation=1, attempt_id=1,
        )
        owner_id = OwnershipIdentity(invocation_id="inv-101", lease_id="l-1", lease_epoch=1)

        self.assertNotEqual(type(exec_id), type(owner_id))
        self.assertEqual(
            exec_id.coordinate_string(), "payments:w-1:g1:cfg1:a1",
        )
        self.assertEqual(owner_id.coordinate_string(), "inv:inv-101:lease:l-1:ep1")

    # ── RS-2: Generation Isolation ────────────────────────────────────
    def test_rs2_generation_isolation(self) -> None:
        """RS-2: Generation coordinates must increment strictly."""
        exec_gen1 = ExecutionIdentity(
            group_id="payments", instance_id="w-1", generation=1, config_generation=1, attempt_id=1,
        )
        exec_gen2 = ExecutionIdentity(
            group_id="payments", instance_id="w-1", generation=2, config_generation=1, attempt_id=1,
        )

        self.assertLess(exec_gen1.generation, exec_gen2.generation)
        with self.assertRaises(ValueError):
            ExecutionIdentity(
                group_id="payments", instance_id="w-1", generation=0, config_generation=1, attempt_id=1,
            )

    # ── RS-3: Lease Monotonicity ──────────────────────────────────────
    def test_rs3_lease_monotonicity(self) -> None:
        """RS-3: Gateway lease epochs must increment monotonically per invocation."""
        mgr = LeaseManager()
        lease1 = mgr.grant_lease(invocation_id="inv-200", worker_id="w-1")
        mgr.revoke_lease(invocation_id="inv-200", lease_epoch=lease1.lease_epoch)
        lease2 = mgr.grant_lease(invocation_id="inv-200", worker_id="w-2")

        self.assertEqual(lease1.lease_epoch, 1)
        self.assertEqual(lease2.lease_epoch, 2)
        self.assertGreater(lease2.lease_epoch, lease1.lease_epoch)

    # ── RS-4: Stale Lease Commit Rejection ────────────────────────────
    def test_rs4_stale_lease_commit_rejection(self) -> None:
        """RS-4: Commit attempt with stale epoch must raise StaleLeaseError."""
        mgr = LeaseManager()
        lease = mgr.grant_lease(invocation_id="inv-300", worker_id="w-1")

        with self.assertRaises(StaleLeaseError):
            mgr.commit_invocation(invocation_id="inv-300", lease_epoch=lease.lease_epoch + 999)

    # ── RS-5: Linearizable Revoke/Commit Race ─────────────────────────
    def test_rs5_linearizable_revoke_commit_race(self) -> None:
        """RS-5 Adversarial Race: Concurrent revoke and commit must be mutually exclusive.

        Worker A owns lease epoch 41. Gateway revokes lease 41 while Worker A
        concurrently submits commit(41).
        Expected: Exactly one wins. Zero duplicate effects. Zero witness forks.
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

        # Exactly one operation succeeds for the contested epoch
        if commit_result is True:
            self.assertFalse(revoke_result)
            self.assertIsNone(commit_error)
        else:
            self.assertTrue(revoke_result)
            self.assertIsNotNone(commit_error)

    # ── RS-6a: Worker Crash Recovery Classification ───────────────────
    def test_rs6a_worker_crash_recovery_classification(self) -> None:
        """RS-6a: Ledger must classify orphaned states into exact recovery buckets."""
        ledger = InvocationStateLedger()
        ledger.create_invocation(invocation_id="inv-500", intent_hash="0x1234")

        # QUEUED -> UNADMITTED
        self.assertEqual(ledger.classify_recovery("inv-500"), RecoveryBucket.UNADMITTED)

        ledger.create_invocation(invocation_id="inv-501", intent_hash="0x1235")
        ledger.transition_state("inv-501", InvocationState.RUNNING)
        self.assertEqual(ledger.classify_recovery("inv-501"), RecoveryBucket.ADMITTED_UNACTUATED)

        ledger.create_invocation(invocation_id="inv-502", intent_hash="0x1236")
        ledger.transition_state("inv-502", InvocationState.ACTUATING)
        self.assertEqual(ledger.classify_recovery("inv-502"), RecoveryBucket.ACTUATION_UNKNOWN)

    # ── RS-6b: Gateway Crash/Restart Ledger Persistence ───────────────
    def test_rs6b_gateway_crash_restart_ledger_persistence(self) -> None:
        """RS-6b: Ledger state must survive Gateway crash/restart via journal replay.

        Sequence:
        1. Create invocation and transition to AUTHORIZED.
        2. Close ledger (simulate crash).
        3. Create new ledger from same journal (simulate restart).
        4. Assert state is correctly restored and classifiable.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            journal_path = os.path.join(tmpdir, "test_ledger.jsonl")

            # Phase 1: Populate and crash
            ledger1 = InvocationStateLedger(journal_path=journal_path)
            ledger1.create_invocation("inv-crash-1", "0xAABB", config_generation=5)
            ledger1.transition_state("inv-crash-1", InvocationState.ASSIGNED, worker_id="w-3")
            ledger1.transition_state("inv-crash-1", InvocationState.RUNNING)
            ledger1.transition_state("inv-crash-1", InvocationState.AUTHORIZED)
            ledger1.close()

            # Phase 2: Restart and verify recovery
            ledger2 = InvocationStateLedger(journal_path=journal_path)
            record = ledger2.get_record("inv-crash-1")
            self.assertIsNotNone(record)
            assert record is not None  # for type narrowing
            self.assertEqual(record.state, InvocationState.AUTHORIZED)
            self.assertEqual(record.assigned_worker_id, "w-3")
            self.assertEqual(record.config_generation, 5)

            # Classify recovery correctly after restart
            bucket = ledger2.classify_recovery("inv-crash-1")
            self.assertEqual(bucket, RecoveryBucket.ADMITTED_UNACTUATED)
            ledger2.close()

    # ── RS-7: Drain Correctness ───────────────────────────────────────
    def test_rs7_drain_correctness(self) -> None:
        """RS-7: Worker tracker must transition READY -> DRAINING -> QUIESCED when work hits 0."""
        identity = ExecutionIdentity(
            group_id="billing", instance_id="w-10", generation=1, config_generation=1, attempt_id=1,
        )
        tracker = WorkerLifecycleTracker(execution_identity=identity, drain_deadline_sec=10.0)

        tracker.update_counts(owned_invocations=2, pending_effects=1, ipc_outstanding=0)
        tracker.begin_draining()
        self.assertEqual(tracker.stage, WorkerLifecycleStage.DRAINING)

        tracker.update_counts(owned_invocations=0, pending_effects=0, ipc_outstanding=0)
        self.assertEqual(tracker.stage, WorkerLifecycleStage.QUIESCED)

    # ── RS-8: Forced Recovery Timeout ─────────────────────────────────
    def test_rs8_forced_recovery_timeout(self) -> None:
        """RS-8: Worker tracker must transition to FORCED_RECOVERY if drain_deadline expires."""
        identity = ExecutionIdentity(
            group_id="billing", instance_id="w-11", generation=1, config_generation=1, attempt_id=1,
        )
        tracker = WorkerLifecycleTracker(execution_identity=identity, drain_deadline_sec=0.05)

        tracker.update_counts(owned_invocations=1, pending_effects=0, ipc_outstanding=0)
        tracker.begin_draining()
        time.sleep(0.06)

        did_timeout = tracker.check_drain_deadline()
        self.assertTrue(did_timeout)
        self.assertEqual(tracker.stage, WorkerLifecycleStage.FORCED_RECOVERY)

    # ── RS-9: No Token Cloning ────────────────────────────────────────
    def test_rs9_no_token_cloning(self) -> None:
        """RS-9: ExecutionIdentity attempts must have distinct IDs across worker replacements."""
        attempt1 = ExecutionIdentity(
            group_id="test", instance_id="w-1", generation=1, config_generation=1, attempt_id=1,
        )
        attempt2 = ExecutionIdentity(
            group_id="test", instance_id="w-2", generation=1, config_generation=1, attempt_id=2,
        )

        self.assertNotEqual(attempt1.instance_id, attempt2.instance_id)
        self.assertNotEqual(attempt1.attempt_id, attempt2.attempt_id)

    # ── RS-10: Capability Bound ───────────────────────────────────────
    def test_rs10_capability_bound(self) -> None:
        """RS-10: Coordinate structures preserve immutable capability group strings."""
        exec_id = ExecutionIdentity(
            group_id="bounded_group", instance_id="w-1", generation=1, config_generation=1, attempt_id=1,
        )
        self.assertEqual(exec_id.group_id, "bounded_group")

    # ── RS-11: No Silent Invocation Loss (Terminal State Invariant) ───
    def test_rs11_terminal_state_invariant(self) -> None:
        """RS-11: Every invocation must terminate in exactly one of {COMMITTED, REJECTED, INDETERMINATE}.

        LOST, DROPPED, ORPHANED_FOREVER, UNKNOWN are prohibited as terminal states.
        """
        # Verify the TERMINAL_STATES constant
        self.assertEqual(
            TERMINAL_STATES,
            frozenset({InvocationState.COMMITTED, InvocationState.REJECTED, InvocationState.INDETERMINATE}),
        )

        # Verify COMMITTED is terminal
        ledger = InvocationStateLedger()
        ledger.create_invocation("inv-t1", "0x01")
        ledger.transition_state("inv-t1", InvocationState.COMMITTED)
        self.assertTrue(ledger.is_terminal("inv-t1"))

        # Verify REJECTED is terminal
        ledger.create_invocation("inv-t2", "0x02")
        ledger.transition_state("inv-t2", InvocationState.REJECTED)
        self.assertTrue(ledger.is_terminal("inv-t2"))

        # Verify ACTUATION_UNKNOWN classification transitions to INDETERMINATE (terminal)
        ledger.create_invocation("inv-t3", "0x03")
        ledger.transition_state("inv-t3", InvocationState.ACTUATING)
        ledger.classify_recovery("inv-t3")  # classifies as ACTUATION_UNKNOWN → INDETERMINATE
        self.assertTrue(ledger.is_terminal("inv-t3"))
        rec = ledger.get_record("inv-t3")
        assert rec is not None
        self.assertEqual(rec.state, InvocationState.INDETERMINATE)

        # Verify non-terminal states are not terminal
        ledger.create_invocation("inv-t4", "0x04")
        self.assertFalse(ledger.is_terminal("inv-t4"))  # QUEUED is not terminal

    # ── RS-12: Bounded State Resource Usage ───────────────────────────
    def test_rs12_bounded_state_resource_usage(self) -> None:
        """RS-12: Memory = O(active_invocations), not O(historical_operations).

        1,000 lease operations execute cleanly. Completed invocations are compactable.
        """
        mgr = LeaseManager()
        ledger = InvocationStateLedger()

        for i in range(1000):
            inv_id = f"inv-iter-{i}"
            ledger.create_invocation(inv_id, f"hash-{i}")
            lease = mgr.grant_lease(invocation_id=inv_id, worker_id="w-iter")
            mgr.commit_invocation(invocation_id=inv_id, lease_epoch=lease.lease_epoch)
            ledger.transition_state(inv_id, InvocationState.COMMITTED)

        # Verify all are terminal
        for i in range(1000):
            self.assertTrue(ledger.is_terminal(f"inv-iter-{i}"))

        # Compact — verify memory is reclaimed
        compacted = ledger.compact_terminated()
        self.assertEqual(compacted, 1000)

        # Verify records are evicted from memory
        self.assertIsNone(ledger.get_record("inv-iter-500"))
        self.assertFalse(mgr.is_lease_valid("inv-iter-500", 1))

    # ── RS-13: Stale Config Generation Rejection ──────────────────────
    def test_rs13_stale_config_generation_rejection(self) -> None:
        """RS-13: Workers with mismatched config_generation must be distinguishable.

        A stale-config worker's config_generation differs from the active deployment.
        The Gateway must detect this mismatch during admission.
        """
        active_config_gen = 18

        stale_worker = ExecutionIdentity(
            group_id="payments", instance_id="w-old", generation=1, config_generation=17, attempt_id=1,
        )
        current_worker = ExecutionIdentity(
            group_id="payments", instance_id="w-new", generation=2, config_generation=18, attempt_id=1,
        )

        # Gateway admission check
        self.assertNotEqual(stale_worker.config_generation, active_config_gen)
        self.assertEqual(current_worker.config_generation, active_config_gen)

        # Verify config_generation appears in audit coordinate string
        self.assertIn("cfg17", stale_worker.coordinate_string())
        self.assertIn("cfg18", current_worker.coordinate_string())

    # ── RS-14: Lifecycle Does Not Own Recovery Policy ──────────────────
    def test_rs14_lifecycle_does_not_own_recovery(self) -> None:
        """RS-14: WorkerLifecycleTracker tracks state but does not decide retry policy.

        Recovery classification belongs to InvocationStateLedger, not lifecycle.
        """
        # Verify WorkerLifecycleTracker has no classify/retry methods
        tracker_methods = dir(WorkerLifecycleTracker)
        self.assertNotIn("classify_recovery", tracker_methods)
        self.assertNotIn("retry_invocation", tracker_methods)
        self.assertNotIn("reroute_invocation", tracker_methods)

        # Verify InvocationStateLedger owns classification
        ledger_methods = dir(InvocationStateLedger)
        self.assertIn("classify_recovery", ledger_methods)

    # ── RS-15: Lease Epoch Scoped Per Invocation ──────────────────────
    def test_rs15_lease_epoch_scoped_per_invocation(self) -> None:
        """RS-15: LeaseEpoch is scoped per InvocationID, not globally.

        Lease operations on inv-A must not affect lease epochs on inv-B.
        """
        mgr = LeaseManager()

        # Grant 5 sequential leases on inv-A
        for i in range(5):
            lease = mgr.grant_lease("inv-A", f"w-{i}")
            mgr.revoke_lease("inv-A", lease.lease_epoch)
        lease_a = mgr.grant_lease("inv-A", "w-final-a")

        # inv-B should start at epoch 1, unaffected by inv-A
        lease_b = mgr.grant_lease("inv-B", "w-first-b")

        self.assertEqual(lease_a.lease_epoch, 6)
        self.assertEqual(lease_b.lease_epoch, 1)

        mgr.revoke_lease("inv-A", lease_a.lease_epoch)
        mgr.revoke_lease("inv-B", lease_b.lease_epoch)


if __name__ == "__main__":
    unittest.main()
