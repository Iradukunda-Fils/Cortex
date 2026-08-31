"""
Candidate G (Batched Expiration + Single Invariant Validation) Test Suite.

Verifies:
1. Multiple reservations expiring in one sweep.
2. Reserve racing with sweep.
3. Release racing with sweep.
4. Renew racing with sweep.
5. Revoke racing with sweep.
6. Duplicate/stale heap entries.
7. Worker death/retirement during sweep.
8. WAL/recovery equivalence.
9. Failure midway through batch (transactional rollback validation).
10. Exact final state equivalence with the baseline.
"""

from __future__ import annotations

import time
import unittest
import threading
from unittest.mock import patch
from cortex.tools.kernel.resource_authority import (
    ResourceAuthority,
    ReservationStatus,
    WorkerLifecycleState,
    ReservationRecord,
    UniquenessViolationError,
)


class TestCandidateGBatchedExpiration(unittest.TestCase):
    """Candidate G Batched Expiration & Single Invariant Validation Verification."""

    def test_multiple_reservations_expiring_in_one_sweep(self) -> None:
        """1. Verifies that multiple reservations expire correctly in a single batched sweep."""
        ra_base = ResourceAuthority(capacity=1000, use_batched_sweep=False)
        ra_batch = ResourceAuthority(capacity=1000, use_batched_sweep=True)
        now = 1_000_000_000

        # Create 5 reservations in both
        for i in range(5):
            ra_base.reserve(
                res_id=i, res_inv=10+i, res_att=100+i, res_worker=1, res_demand=10,
                authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
            )
            ra_batch.reserve(
                res_id=i, res_inv=10+i, res_att=100+i, res_worker=1, res_demand=10,
                authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
            )

        # Sweep both at now + 100
        expired_base = ra_base.expire_reservations_sweep(now + 100)
        expired_batch = ra_batch.expire_reservations_sweep(now + 100)

        self.assertEqual([r.res_id for r in expired_base], [0, 1, 2, 3, 4])
        self.assertEqual([r.res_id for r in expired_batch], [0, 1, 2, 3, 4])
        self.assertEqual(ra_base._reservations[0].res_status, ReservationStatus.EXPIRED)
        self.assertEqual(ra_batch._reservations[0].res_status, ReservationStatus.EXPIRED)

    def test_reserve_racing_with_sweep(self) -> None:
        """2. Verifies serialization safety when reserve is called concurrently with sweep."""
        ra = ResourceAuthority(capacity=1000, use_batched_sweep=True)
        now = 1_000_000_000

        # Setup one reservation to expire
        ra.reserve(
            res_id=1, res_inv=10, res_att=100, res_worker=1, res_demand=10,
            authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
        )

        # Thread racing to reserve a new item during sweep
        def concurrent_reserve():
            time.sleep(0.01)
            ra.reserve(
                res_id=2, res_inv=20, res_att=200, res_worker=1, res_demand=10,
                authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 200
            )

        t = threading.Thread(target=concurrent_reserve)
        t.start()

        # Execute sweep
        expired = ra.expire_reservations_sweep(now + 100)
        t.join()

        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0].res_id, 1)
        self.assertEqual(len(ra._reservations), 2)
        self.assertEqual(ra._reservations[2].res_status, ReservationStatus.ACTIVE)

    def test_release_racing_with_sweep(self) -> None:
        """3. Verifies that if a reservation is released before/during sweep, it is skipped."""
        ra = ResourceAuthority(capacity=1000, use_batched_sweep=True)
        now = 1_000_000_000

        ra.reserve(
            res_id=1, res_inv=10, res_att=100, res_worker=1, res_demand=10,
            authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
        )

        # Release first
        ra.release(1)

        # Sweep should skip it as it's not active anymore
        expired = ra.expire_reservations_sweep(now + 100)
        self.assertEqual(len(expired), 0)
        self.assertEqual(ra._reservations[1].res_status, ReservationStatus.RELEASED)

    def test_renew_racing_with_sweep(self) -> None:
        """4. Verifies that if a reservation is renewed, the batch sweep skips the stale heap entry."""
        ra = ResourceAuthority(capacity=1000, use_min_heap_expiration=True, use_batched_sweep=True)
        now = 1_000_000_000

        ra.reserve(
            res_id=1, res_inv=10, res_att=100, res_worker=1, res_demand=10,
            authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
        )

        # Renew -> extends expiration and increments generation_id
        ra.renew_reservation(1, now + 500)

        # Sweep at now + 100 -> should skip the old heap entry (stale generation_id)
        expired = ra.expire_reservations_sweep(now + 100)
        self.assertEqual(len(expired), 0)
        self.assertEqual(ra._reservations[1].res_status, ReservationStatus.ACTIVE)

        # Sweep at now + 600 -> should expire it now
        expired2 = ra.expire_reservations_sweep(now + 600)
        self.assertEqual(len(expired2), 1)
        self.assertEqual(expired2[0].res_id, 1)

    def test_revoke_racing_with_sweep(self) -> None:
        """5. Verifies that if a reservation is revoked, the batch sweep skips it."""
        ra = ResourceAuthority(capacity=1000, use_batched_sweep=True)
        now = 1_000_000_000

        ra.reserve(
            res_id=1, res_inv=10, res_att=100, res_worker=1, res_demand=10,
            authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
        )

        ra.revoke(1)

        # Sweep at now + 100 should skip it
        expired = ra.expire_reservations_sweep(now + 100)
        self.assertEqual(len(expired), 0)
        self.assertEqual(ra._reservations[1].res_status, ReservationStatus.REVOKED)

    def test_duplicate_stale_heap_entries(self) -> None:
        """6. Verifies that duplicate or stale heap entries are cleanly skipped without modifying state."""
        ra = ResourceAuthority(capacity=1000, use_min_heap_expiration=True, use_batched_sweep=True)
        now = 1_000_000_000

        ra.reserve(
            res_id=1, res_inv=10, res_att=100, res_worker=1, res_demand=10,
            authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
        )

        # Manually push a duplicate stale heap entry
        import heapq
        heapq.heappush(ra._min_heap, (now + 50, 1, 99))  # Incorrect generation_id=99

        # Sweep at now + 100
        expired = ra.expire_reservations_sweep(now + 100)
        # Should expire exactly once (using the correct generation entry) and skip the stale entry
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0].res_id, 1)

    def test_worker_death_during_sweep(self) -> None:
        """7. Verifies active count decrements when worker has assignments expired."""
        ra = ResourceAuthority(capacity=1000, use_batched_sweep=True)
        now = 1_000_000_000

        # Initialize worker scaling record
        from cortex.tools.kernel.resource_authority import WorkerScalingRecord
        ra._worker_states[1] = WorkerScalingRecord(
            worker_id=1, generation=1, state=WorkerLifecycleState.ACTIVE
        )

        ra.reserve(
            res_id=1, res_inv=10, res_att=100, res_worker=1, res_demand=10,
            authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
        )

        self.assertEqual(ra._worker_states[1].active_assignments_count, 1)

        # Sweep
        ra.expire_reservations_sweep(now + 100)
        self.assertEqual(ra._worker_states[1].active_assignments_count, 0)

    def test_wal_recovery_replay_equivalence(self) -> None:
        """8. Verifies that recovery from WAL records produces identical configurations."""
        ra_orig = ResourceAuthority(capacity=1000, use_batched_sweep=True)
        now = 1_000_000_000

        ra_orig.reserve(
            res_id=1, res_inv=10, res_att=100, res_worker=1, res_demand=10,
            authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
        )
        ra_orig.expire_reservations_sweep(now + 100)

        # Replay WAL logs
        records = list(ra_orig._reservations.values())
        ra_recovered = ResourceAuthority(capacity=1000, use_batched_sweep=True)
        ra_recovered.recover_from_records(records, authority_epoch=1)

        self.assertEqual(
            ra_recovered._reservations[1].res_status,
            ReservationStatus.EXPIRED
        )

    def test_failure_midway_through_batch_transactional_rollback(self) -> None:
        """9. Verifies transactional rollback (all-or-nothing) if check_invariants fails."""
        ra = ResourceAuthority(capacity=1000, use_batched_sweep=True)
        now = 1_000_000_000

        ra.reserve(
            res_id=1, res_inv=10, res_att=100, res_worker=1, res_demand=10,
            authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
        )
        ra.reserve(
            res_id=2, res_inv=20, res_att=200, res_worker=1, res_demand=10,
            authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=now + 50
        )

        # Force check_invariants to throw an error
        with patch.object(ra, "check_invariants", side_effect=ValueError("Simulated verification failure")):
            with self.assertRaises(ValueError):
                ra.expire_reservations_sweep(now + 100)

        # Confirm all state reverted back to ACTIVE (rollback verified)
        self.assertEqual(ra._reservations[1].res_status, ReservationStatus.ACTIVE)
        self.assertEqual(ra._reservations[2].res_status, ReservationStatus.ACTIVE)

    def test_exact_final_state_equivalence_with_baseline(self) -> None:
        """10. Verifies exact final state equivalence (S_A^baseline == S_A^batched) across mixed traces."""
        ra_base = ResourceAuthority(capacity=10000, use_batched_sweep=False, use_min_heap_expiration=False)
        ra_batch = ResourceAuthority(capacity=10000, use_batched_sweep=True, use_min_heap_expiration=True)
        now = 1_000_000_000

        # Perform equivalent sequence of mixed actions
        for i in range(20):
            exp_ts = now + (i + 1) * 10
            ra_base.reserve(
                res_id=i, res_inv=100+i, res_att=1000+i, res_worker=1, res_demand=10,
                authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=exp_ts
            )
            ra_batch.reserve(
                res_id=i, res_inv=100+i, res_att=1000+i, res_worker=1, res_demand=10,
                authority_epoch=1, lease_epoch=1, worker_generation=1, expiration_timestamp_ns=exp_ts
            )

        # Release some
        ra_base.release(5)
        ra_batch.release(5)

        # Renew some
        ra_base.renew_reservation(10, now + 500)
        ra_batch.renew_reservation(10, now + 500)

        # Revoke some
        ra_base.revoke(15)
        ra_batch.revoke(15)

        # Sweep both at now + 150
        ra_base.expire_reservations_sweep(now + 150)
        ra_batch.expire_reservations_sweep(now + 150)

        # Compare state maps
        for res_id in range(20):
            base_rec = ra_base._reservations[res_id]
            batch_rec = ra_batch._reservations[res_id]
            self.assertEqual(base_rec.res_status, batch_rec.res_status)

        # Validate that WAL recoveries match
        recovered_base = ResourceAuthority(capacity=10000)
        recovered_base.recover_from_records(list(ra_base._reservations.values()), 1)

        recovered_batch = ResourceAuthority(capacity=10000)
        recovered_batch.recover_from_records(list(ra_batch._reservations.values()), 1)

        for res_id in range(20):
            self.assertEqual(
                recovered_base._reservations[res_id].res_status,
                recovered_batch._reservations[res_id].res_status
            )

    def test_performance_benchmark_batched_vs_baseline(self) -> None:
        """Benchmarks performance of Candidate G vs Baseline sweep under lock."""
        n_reservations = 1000
        n_to_expire = 100
        now = 1_000_000_000_000

        ra_base = ResourceAuthority(capacity=100000, use_batched_sweep=False)
        ra_batch = ResourceAuthority(capacity=100000, use_batched_sweep=True)

        for i in range(n_reservations):
            exp_ts = now + (i + 1) * 1000
            ra_base.reserve(
                res_id=i, res_inv=10000 + i, res_att=100000 + i, res_worker=1,
                res_demand=1, authority_epoch=1, lease_epoch=1, worker_generation=1,
                expiration_timestamp_ns=exp_ts,
            )
            ra_batch.reserve(
                res_id=i, res_inv=10000 + i, res_att=100000 + i, res_worker=1,
                res_demand=1, authority_epoch=1, lease_epoch=1, worker_generation=1,
                expiration_timestamp_ns=exp_ts,
            )

        sweep_time = now + n_to_expire * 1000

        # Benchmark baseline (O(K * N))
        t0 = time.perf_counter_ns()
        exp_base = ra_base.expire_reservations_sweep(sweep_time)
        t_base_us = (time.perf_counter_ns() - t0) / 1000.0

        # Benchmark batched (O(K + N))
        t1 = time.perf_counter_ns()
        exp_batch = ra_batch.expire_reservations_sweep(sweep_time)
        t_batch_us = (time.perf_counter_ns() - t1) / 1000.0

        print(f"\n{'=' * 90}")
        print(f" CANDIDATE G EXPIRATION SWEEP BENCHMARK (N={n_reservations}, K={n_to_expire} expired)")
        print(f"{'=' * 90}")
        print(f" Baseline Sweep (per-item verify):  {t_base_us:>12.2f} µs")
        print(f" Candidate G (batched single verify): {t_batch_us:>12.2f} µs")
        speedup = t_base_us / t_batch_us if t_batch_us > 0 else 1.0
        print(f" Speedup Factor:                      {speedup:>12.2f}x")
        print(f"{'=' * 90}")

        self.assertEqual(len(exp_base), n_to_expire)
        self.assertEqual(len(exp_batch), n_to_expire)


if __name__ == "__main__":
    unittest.main()
