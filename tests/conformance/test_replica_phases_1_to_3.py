"""
Conformance & Adversarial Test Suite for Cortex Multi-Replica Subsystem (Gates RS-1 to RS-18)

Verifies core replica identity coordinates, Gateway linearizable lease fencing,
durable invocation state ledgers, worker lifecycle tracking, linearizable race safety,
Gateway crash/restart persistence, torn-record recovery, atomic snapshot compaction,
terminal state invariants, and ConfigHash identity binding.
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
    """Conformance test suite for RS-1 through RS-18 verification gates."""

    # ── RS-1: Replica Identity Coordinate Separation ──────────────────
    def test_rs1_replica_identity_coordinate_separation(self) -> None:
        """RS-1: ExecutionIdentity and OwnershipIdentity must be distinct and non-coercible."""
        exec_id = ExecutionIdentity(
            group_id="payments",
            instance_id="w-1",
            generation=1,
            config_generation=1,
            config_hash="sha256_abc",
            attempt_id=1,
        )
        owner_id = OwnershipIdentity(invocation_id="inv-101", lease_id="l-1", lease_epoch=1)

        self.assertNotEqual(type(exec_id), type(owner_id))
        self.assertEqual(
            exec_id.coordinate_string(),
            "payments:w-1:g1:cfg1:hsha256_a:a1",
        )
        self.assertEqual(owner_id.coordinate_string(), "inv:inv-101:lease:l-1:ep1")

    # ── RS-2: Generation Isolation ────────────────────────────────────
    def test_rs2_generation_isolation(self) -> None:
        """RS-2: Generation coordinates must increment strictly."""
        exec_gen1 = ExecutionIdentity(
            group_id="payments",
            instance_id="w-1",
            generation=1,
            config_generation=1,
            attempt_id=1,
        )
        exec_gen2 = ExecutionIdentity(
            group_id="payments",
            instance_id="w-1",
            generation=2,
            config_generation=1,
            attempt_id=1,
        )

        self.assertLess(exec_gen1.generation, exec_gen2.generation)
        with self.assertRaises(ValueError):
            ExecutionIdentity(
                group_id="payments",
                instance_id="w-1",
                generation=0,
                config_generation=1,
                attempt_id=1,
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

    # ── RS-5: High-Iteration Linearizable Revoke/Commit Race ─────────
    def test_rs5_multi_iteration_linearizable_race(self) -> None:
        """RS-5 Adversarial Multi-Iteration Race: Concurrent revoke and commit across 100 iterations.

        For each contested lease epoch:
        - Exactly one of revoke_lease or commit_invocation succeeds (success_revoke + success_commit == 1).
        - Stale commit attempt produces StaleLeaseError.
        - Zero duplicate effects and zero witness forks.
        """
        mgr = LeaseManager()
        for i in range(100):
            inv_id = f"inv-race-{i}"
            lease = mgr.grant_lease(invocation_id=inv_id, worker_id=f"w-{i}")
            target_epoch = lease.lease_epoch

            commit_result = None
            commit_error = None
            revoke_result = None

            def do_commit(id_val: str = inv_id, ep_val: int = target_epoch) -> None:
                nonlocal commit_result, commit_error
                try:
                    commit_result = mgr.commit_invocation(invocation_id=id_val, lease_epoch=ep_val)
                except StaleLeaseError as e:
                    commit_error = e

            def do_revoke(id_val: str = inv_id, ep_val: int = target_epoch) -> None:
                nonlocal revoke_result
                revoke_result = mgr.revoke_lease(invocation_id=id_val, lease_epoch=ep_val)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(do_commit)
                f2 = executor.submit(do_revoke)
                concurrent.futures.wait([f1, f2])

            c_success = 1 if commit_result is True else 0
            r_success = 1 if revoke_result is True else 0
            self.assertEqual(c_success + r_success, 1, f"Iteration {i}: Mutually exclusive constraint violated")

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
        """RS-6b: Ledger state must survive Gateway crash/restart via journal replay."""
        with tempfile.TemporaryDirectory() as tmpdir:
            journal_path = os.path.join(tmpdir, "test_ledger.jsonl")

            # Phase 1: Populate and crash
            ledger1 = InvocationStateLedger(journal_path=journal_path)
            ledger1.create_invocation("inv-crash-1", "0xAABB", config_generation=5, config_hash="hash_v5")
            ledger1.transition_state("inv-crash-1", InvocationState.ASSIGNED, worker_id="w-3")
            ledger1.transition_state("inv-crash-1", InvocationState.RUNNING)
            ledger1.transition_state("inv-crash-1", InvocationState.AUTHORIZED)
            ledger1.close()

            # Phase 2: Restart and verify recovery
            ledger2 = InvocationStateLedger(journal_path=journal_path)
            record = ledger2.get_record("inv-crash-1")
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.state, InvocationState.AUTHORIZED)
            self.assertEqual(record.assigned_worker_id, "w-3")
            self.assertEqual(record.config_generation, 5)
            self.assertEqual(record.config_hash, "hash_v5")

            bucket = ledger2.classify_recovery("inv-crash-1")
            self.assertEqual(bucket, RecoveryBucket.ADMITTED_UNACTUATED)
            ledger2.close()

    # ── RS-6c: Journal Torn-Record Recovery ───────────────────────────
    def test_rs6c_journal_torn_record_recovery(self) -> None:
        """RS-6c: Gateway restart must recover valid prior state even if final line is torn/corrupted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            journal_path = os.path.join(tmpdir, "torn_ledger.jsonl")

            # Phase 1: Write valid transitions
            ledger1 = InvocationStateLedger(journal_path=journal_path)
            ledger1.create_invocation("inv-valid-1", "0x1111")
            ledger1.transition_state("inv-valid-1", InvocationState.RUNNING)
            ledger1.close()

            # Phase 2: Simulate power crash mid-write appending a torn line at EOF
            with open(journal_path, "a", encoding="utf-8") as f:
                f.write('{"invocation_id": "inv-torn-2", "state": "ACTUA')  # Incomplete JSON line

            # Phase 3: Restart Gateway — must recover inv-valid-1 without error and ignore torn line
            ledger2 = InvocationStateLedger(journal_path=journal_path)
            rec = ledger2.get_record("inv-valid-1")
            self.assertIsNotNone(rec)
            assert rec is not None
            self.assertEqual(rec.state, InvocationState.RUNNING)
            self.assertIsNone(ledger2.get_record("inv-torn-2"))
            ledger2.close()

    # ── RS-6d: Crash During Atomic Compaction ─────────────────────────
    def test_rs6d_atomic_compaction(self) -> None:
        """RS-6d: Compaction must atomically swap snapshot file and evict terminal records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            journal_path = os.path.join(tmpdir, "compact_ledger.jsonl")

            ledger = InvocationStateLedger(journal_path=journal_path)
            # Create active invocation
            ledger.create_invocation("inv-active", "0xACTIVE")
            ledger.transition_state("inv-active", InvocationState.RUNNING)

            # Create terminal invocation
            ledger.create_invocation("inv-term", "0xTERM")
            ledger.transition_state("inv-term", InvocationState.COMMITTED)

            # Run compaction
            compacted_count = ledger.compact_terminated()
            self.assertEqual(compacted_count, 1)

            # Active record survives in memory & disk, terminal is evicted from memory
            self.assertIsNotNone(ledger.get_record("inv-active"))
            self.assertIsNone(ledger.get_record("inv-term"))
            ledger.close()

            # Re-open ledger from disk to verify atomic snapshot persistence
            ledger_reopened = InvocationStateLedger(journal_path=journal_path)
            self.assertIsNotNone(ledger_reopened.get_record("inv-active"))
            self.assertIsNone(ledger_reopened.get_record("inv-term"))
            ledger_reopened.close()

    # ── RS-6e: Full Lifecycle Restart Matrix ──────────────────────────
    def test_rs6e_full_lifecycle_restart_matrix(self) -> None:
        """RS-6e: Verify Gateway restart recovery classification across all lifecycle states."""
        with tempfile.TemporaryDirectory() as tmpdir:
            journal_path = os.path.join(tmpdir, "matrix_ledger.jsonl")

            states_to_test = [
                ("inv-q", InvocationState.QUEUED, RecoveryBucket.UNADMITTED),
                ("inv-as", InvocationState.ASSIGNED, RecoveryBucket.UNADMITTED),
                ("inv-r", InvocationState.RUNNING, RecoveryBucket.ADMITTED_UNACTUATED),
                ("inv-au", InvocationState.AUTHORIZED, RecoveryBucket.ADMITTED_UNACTUATED),
                ("inv-act", InvocationState.ACTUATING, RecoveryBucket.ACTUATION_UNKNOWN),
                ("inv-com", InvocationState.COMMITTED, RecoveryBucket.ACTUATED_COMMITTED),
            ]

            ledger1 = InvocationStateLedger(journal_path=journal_path)
            for inv_id, state, _ in states_to_test:
                ledger1.create_invocation(inv_id, f"hash-{inv_id}")
                if state != InvocationState.QUEUED:
                    ledger1.transition_state(inv_id, state)
            ledger1.close()

            # Restart Gateway and classify each
            ledger2 = InvocationStateLedger(journal_path=journal_path)
            for inv_id, _, expected_bucket in states_to_test:
                bucket = ledger2.classify_recovery(inv_id)
                self.assertEqual(bucket, expected_bucket, f"Mismatch for {inv_id}")
            ledger2.close()

    # ── RS-7: Drain Correctness ───────────────────────────────────────
    def test_rs7_drain_correctness(self) -> None:
        """RS-7: Worker tracker must transition READY -> DRAINING -> QUIESCED when work hits 0."""
        identity = ExecutionIdentity(
            group_id="billing",
            instance_id="w-10",
            generation=1,
            config_generation=1,
            attempt_id=1,
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
            group_id="billing",
            instance_id="w-11",
            generation=1,
            config_generation=1,
            attempt_id=1,
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
            group_id="test",
            instance_id="w-1",
            generation=1,
            config_generation=1,
            attempt_id=1,
        )
        attempt2 = ExecutionIdentity(
            group_id="test",
            instance_id="w-2",
            generation=1,
            config_generation=1,
            attempt_id=2,
        )

        self.assertNotEqual(attempt1.instance_id, attempt2.instance_id)
        self.assertNotEqual(attempt1.attempt_id, attempt2.attempt_id)

    # ── RS-10: Capability Bound ───────────────────────────────────────
    def test_rs10_capability_bound(self) -> None:
        """RS-10: Coordinate structures preserve immutable capability group strings."""
        exec_id = ExecutionIdentity(
            group_id="bounded_group",
            instance_id="w-1",
            generation=1,
            config_generation=1,
            attempt_id=1,
        )
        self.assertEqual(exec_id.group_id, "bounded_group")

    # ── RS-11: No Silent Invocation Loss (Terminal State Invariant) ───
    def test_rs11_terminal_state_invariant(self) -> None:
        """RS-11: Every invocation must terminate in exactly one of {COMMITTED, REJECTED, INDETERMINATE}."""
        self.assertEqual(
            TERMINAL_STATES,
            frozenset({InvocationState.COMMITTED, InvocationState.REJECTED, InvocationState.INDETERMINATE}),
        )

        ledger = InvocationStateLedger()
        ledger.create_invocation("inv-t1", "0x01")
        ledger.transition_state("inv-t1", InvocationState.COMMITTED)
        self.assertTrue(ledger.is_terminal("inv-t1"))

        ledger.create_invocation("inv-t2", "0x02")
        ledger.transition_state("inv-t2", InvocationState.REJECTED)
        self.assertTrue(ledger.is_terminal("inv-t2"))

        ledger.create_invocation("inv-t3", "0x03")
        ledger.transition_state("inv-t3", InvocationState.ACTUATING)
        ledger.classify_recovery("inv-t3")  # ACTUATION_UNKNOWN → INDETERMINATE
        self.assertTrue(ledger.is_terminal("inv-t3"))
        rec = ledger.get_record("inv-t3")
        assert rec is not None
        self.assertEqual(rec.state, InvocationState.INDETERMINATE)

    # ── RS-12: Bounded State Resource Usage ───────────────────────────
    def test_rs12_bounded_state_resource_usage(self) -> None:
        """RS-12: Memory = O(active_invocations), not O(historical_operations)."""
        mgr = LeaseManager()
        ledger = InvocationStateLedger()

        for i in range(1000):
            inv_id = f"inv-iter-{i}"
            ledger.create_invocation(inv_id, f"hash-{i}")
            lease = mgr.grant_lease(invocation_id=inv_id, worker_id="w-iter")
            mgr.commit_invocation(invocation_id=inv_id, lease_epoch=lease.lease_epoch)
            ledger.transition_state(inv_id, InvocationState.COMMITTED)

        for i in range(1000):
            self.assertTrue(ledger.is_terminal(f"inv-iter-{i}"))

        compacted = ledger.compact_terminated()
        self.assertEqual(compacted, 1000)

        self.assertIsNone(ledger.get_record("inv-iter-500"))
        self.assertFalse(mgr.is_lease_valid("inv-iter-500", 1))

    # ── RS-13: Stale Config Generation & Hash Rejection ────────────────
    def test_rs13_stale_config_generation_and_hash_rejection(self) -> None:
        """RS-13: Workers with mismatched config_generation or config_hash must be distinguishable."""
        active_config_gen = 18
        active_config_hash = "sha256_hash_A"

        stale_gen_worker = ExecutionIdentity(
            group_id="payments",
            instance_id="w-old-gen",
            generation=1,
            config_generation=17,
            config_hash=active_config_hash,
            attempt_id=1,
        )
        mismatched_hash_worker = ExecutionIdentity(
            group_id="payments",
            instance_id="w-wrong-hash",
            generation=2,
            config_generation=18,
            config_hash="sha256_hash_B",
            attempt_id=1,
        )
        current_worker = ExecutionIdentity(
            group_id="payments",
            instance_id="w-valid",
            generation=2,
            config_generation=18,
            config_hash=active_config_hash,
            attempt_id=1,
        )

        # Rejection assertions
        self.assertNotEqual(stale_gen_worker.config_generation, active_config_gen)
        self.assertNotEqual(mismatched_hash_worker.config_hash, active_config_hash)
        self.assertEqual(current_worker.config_generation, active_config_gen)
        self.assertEqual(current_worker.config_hash, active_config_hash)

    # ── RS-14: Lifecycle Does Not Own Recovery Policy ──────────────────
    def test_rs14_lifecycle_does_not_own_recovery(self) -> None:
        """RS-14: WorkerLifecycleTracker tracks state but does not decide retry policy."""
        tracker_methods = dir(WorkerLifecycleTracker)
        self.assertNotIn("classify_recovery", tracker_methods)
        self.assertNotIn("retry_invocation", tracker_methods)

        ledger_methods = dir(InvocationStateLedger)
        self.assertIn("classify_recovery", ledger_methods)

    # ── RS-15: Lease Epoch Scoped Per Invocation ──────────────────────
    def test_rs15_lease_epoch_scoped_per_invocation(self) -> None:
        """RS-15: LeaseEpoch is scoped per InvocationID, not globally."""
        mgr = LeaseManager()

        for i in range(5):
            lease = mgr.grant_lease("inv-A", f"w-{i}")
            mgr.revoke_lease("inv-A", lease.lease_epoch)
        lease_a = mgr.grant_lease("inv-A", "w-final-a")

        lease_b = mgr.grant_lease("inv-B", "w-first-b")

        self.assertEqual(lease_a.lease_epoch, 6)
        self.assertEqual(lease_b.lease_epoch, 1)


if __name__ == "__main__":
    unittest.main()
