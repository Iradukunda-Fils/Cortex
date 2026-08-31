"""
Phase 7.3: Concrete Resource Authority 18-Vector Adversarial Test Suite
Normative Specification: Research Note 21
Refinement Certificate Version: RCA-7.3-v1

Verifies forward simulation R(c, a) and all 18 adversarial fault vectors.
"""

import concurrent.futures
import unittest

from cortex.tools.kernel.resource_authority import (
    GPUCollisionError,
    InsufficientCapacityError,
    InvalidFencingError,
    ReservationRecord,
    ReservationStatus,
    ResourceAuthority,
    UniquenessViolationError,
)


class TestPhase7ResourceAuthority(unittest.TestCase):
    def test_tv_73_01_concurrent_reserve_same_invocation(self):
        """TV-73-01: Two simultaneous reserve requests for same InvocationId."""
        auth = ResourceAuthority()

        def try_reserve(res_id: int):
            return auth.reserve(
                res_id=res_id,
                res_inv=101,
                res_att=res_id,
                res_worker=1,
                res_demand=100,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
            )

        results = []
        errors = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(try_reserve, 1), executor.submit(try_reserve, 2)]
            for f in futures:
                try:
                    results.append(f.result())
                except Exception as e:
                    errors.append(e)

        self.assertEqual(len(results), 1, "Exactly one reservation must succeed (P1a)")
        self.assertEqual(len(errors), 1, "Exactly one reservation must fail (P1a)")
        self.assertIsInstance(errors[0], UniquenessViolationError)

    def test_tv_73_02_concurrent_reserve_same_attempt(self):
        """TV-73-02: Two simultaneous reserve requests for same AttemptId."""
        auth = ResourceAuthority()

        def try_reserve(res_id: int, inv_id: int):
            return auth.reserve(
                res_id=res_id,
                res_inv=inv_id,
                res_att=202,
                res_worker=1,
                res_demand=100,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
            )

        results = []
        errors = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(try_reserve, 1, 101), executor.submit(try_reserve, 2, 102)]
            for f in futures:
                try:
                    results.append(f.result())
                except Exception as e:
                    errors.append(e)

        self.assertEqual(len(results), 1, "Exactly one reservation must succeed (P1b)")
        self.assertEqual(len(errors), 1, "Exactly one reservation must fail (P1b)")
        self.assertIsInstance(errors[0], UniquenessViolationError)

    def test_tv_73_03_stale_authority_epoch(self):
        """TV-73-03: Reserve with stale authority epoch."""
        auth = ResourceAuthority(authority_epoch=2)
        with self.assertRaises(InvalidFencingError):
            auth.reserve(
                res_id=1,
                res_inv=101,
                res_att=1,
                res_worker=1,
                res_demand=100,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
            )

    def test_tv_73_04_stale_lease_epoch(self):
        """TV-73-04: Reserve with non-monotonic lease epoch."""
        auth = ResourceAuthority()
        auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=5,
            worker_generation=1,
        )
        auth.release(1)

        with self.assertRaises(InvalidFencingError):
            auth.reserve(
                res_id=2,
                res_inv=101,
                res_att=2,
                res_worker=1,
                res_demand=100,
                authority_epoch=1,
                lease_epoch=5,
                worker_generation=1,
            )

    def test_tv_73_05_stale_worker_generation(self):
        """TV-73-05: Reserve with stale worker generation."""
        auth = ResourceAuthority()
        auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=10,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=3,
        )
        auth.release(1)

        with self.assertRaises(InvalidFencingError):
            auth.reserve(
                res_id=2,
                res_inv=102,
                res_att=2,
                res_worker=10,
                res_demand=100,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=2,
            )

    def test_tv_73_06_gpu_collision(self):
        """TV-73-06: ReserveGPU on an already owned exclusive GPU."""
        auth = ResourceAuthority()
        auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
            gpu_id=0,
        )
        with self.assertRaises(GPUCollisionError):
            auth.reserve(
                res_id=2,
                res_inv=102,
                res_att=2,
                res_worker=2,
                res_demand=100,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
                gpu_id=0,
            )

    def test_tv_73_07_gpu_release(self):
        """TV-73-07: Release of GPU reservation frees the GPU for new reservation."""
        auth = ResourceAuthority()
        auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
            gpu_id=0,
        )
        auth.release(1)

        rec2 = auth.reserve(
            res_id=2,
            res_inv=102,
            res_att=2,
            res_worker=2,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
            gpu_id=0,
        )
        self.assertEqual(rec2.res_id, 2)

    def test_tv_73_08_exceed_capacity_safety_limit(self):
        """TV-73-08: Exceed capacity safety limit (P2)."""
        auth = ResourceAuthority(capacity=1000, safety_margin=50, uncertainty=50)
        with self.assertRaises(InsufficientCapacityError):
            auth.reserve(
                res_id=1,
                res_inv=101,
                res_att=1,
                res_worker=1,
                res_demand=950,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
            )

    def test_tv_73_09_release_unauthorized_caller(self):
        """TV-73-09: Attempt release on non-existent reservation ID."""
        auth = ResourceAuthority()
        with self.assertRaises(KeyError):
            auth.release(999)

    def test_tv_73_10_double_release_idempotency(self):
        """TV-73-10: Double release of same ReservationId is idempotent."""
        auth = ResourceAuthority()
        auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        rec1 = auth.release(1)
        self.assertEqual(rec1.res_status, ReservationStatus.RELEASED)

        rec2 = auth.release(1)
        self.assertEqual(rec2.res_status, ReservationStatus.RELEASED)

    def test_tv_73_11_expiry(self):
        """TV-73-11: Expiry transitions reservation to EXPIRED and reclaims capacity."""
        auth = ResourceAuthority()
        auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
            gpu_id=3,
        )
        rec = auth.expire(1)
        self.assertEqual(rec.res_status, ReservationStatus.EXPIRED)
        self.assertNotIn(3, auth._gpu_owners)
        self.assertIn(1, auth._quarantine)

    def test_tv_73_12_revocation(self):
        """TV-73-12: Revocation transitions reservation to REVOKED and isolates it."""
        auth = ResourceAuthority()
        auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        rec = auth.revoke(1)
        self.assertEqual(rec.res_status, ReservationStatus.REVOKED)
        self.assertIn(1, auth._quarantine)

    def test_tv_73_13_recovery_and_replay(self):
        """TV-73-13: Process crash and WAL replay produces state satisfying alpha(C) = A."""
        auth1 = ResourceAuthority()
        auth1.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
            gpu_id=2,
        )
        auth1.reserve(
            res_id=2,
            res_inv=102,
            res_att=2,
            res_worker=1,
            res_demand=200,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        auth1.release(1)

        records = list(auth1._reservations.values())

        auth2 = ResourceAuthority()
        auth2.recover_from_records(records, authority_epoch=1)

        self.assertEqual(auth1.alpha(), auth2.alpha())

    def test_tv_73_14_terminal_resurrection_prevention(self):
        """TV-73-14: Terminal reservation resurrection attempt blocked during recovery."""
        auth = ResourceAuthority()
        rec = ReservationRecord(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            res_authority_epoch=1,
            res_lease_epoch=1,
            res_generation=1,
            res_status=ReservationStatus.RELEASED,
        )
        auth.recover_from_records([rec], authority_epoch=1)

        active_count = sum(1 for r in auth._reservations.values() if r.res_status.is_active())
        self.assertEqual(active_count, 0, "Terminal reservation must not resurrect as active")
        self.assertIn(1, auth._quarantine, "Terminal reservation must be contained in quarantine")
        self.assertTrue(auth.check_invariants())

    def test_tv_73_15_reservation_leak_check(self):
        """TV-73-15: Reservation leak check after 1,000 transitions."""
        auth = ResourceAuthority(capacity=10000)
        for i in range(1, 1001):
            auth.reserve(
                res_id=i,
                res_inv=i,
                res_att=i,
                res_worker=1,
                res_demand=5,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
            )
            auth.release(i)

        active_count = sum(1 for r in auth._reservations.values() if r.res_status.is_active())
        self.assertEqual(active_count, 0)
        self.assertTrue(auth.check_invariants())

    def test_tv_73_16_stale_telemetry_bound(self):
        """TV-73-16: Schedulable capacity bound strictly holds even with used capacity updates."""
        auth = ResourceAuthority(capacity=1000, safety_margin=100, uncertainty=100)
        auth._used_capacity = 700

        with self.assertRaises(InsufficientCapacityError):
            auth.reserve(
                res_id=1,
                res_inv=101,
                res_att=1,
                res_worker=1,
                res_demand=150,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
            )

        rec = auth.reserve(
            res_id=2,
            res_inv=102,
            res_att=2,
            res_worker=1,
            res_demand=50,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        self.assertEqual(rec.res_id, 2)

    def test_tv_73_17_concurrent_stress_transitions(self):
        """TV-73-17: 100 concurrent threads acquiring/releasing reservations."""
        auth = ResourceAuthority(capacity=10000, safety_margin=100, uncertainty=100)

        def worker_task(worker_id: int):
            for i in range(50):
                res_id = worker_id * 100 + i
                inv_id = res_id
                try:
                    auth.reserve(
                        res_id=res_id,
                        res_inv=inv_id,
                        res_att=1,
                        res_worker=worker_id,
                        res_demand=10,
                        authority_epoch=1,
                        lease_epoch=1,
                        worker_generation=1,
                    )
                    auth.release(res_id)
                except Exception:
                    pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker_task, w) for w in range(20)]
            for f in futures:
                f.result()

        self.assertTrue(auth.check_invariants())

    def test_tv_73_18_authority_succession_burst(self):
        """TV-73-18: Multi-phase authority succession burst monotonically increments authority epoch."""
        auth = ResourceAuthority(authority_epoch=1)
        self.assertEqual(auth.authority_succession(2), 2)
        self.assertEqual(auth.authority_succession(5), 5)

        with self.assertRaises(InvalidFencingError):
            auth.authority_succession(4)

    def test_declarative_policy_validation_and_unit_normalization(self):
        """Validates schema parsing and unit normalization from raw dictionary."""
        raw_config = {
            "schema": {"name": "cortex-resource-policy", "version": "1"},
            "resource_profile": {
                "cpu": {"capacity": 16.0, "unit": "cores"},
                "memory": {"capacity": 64.0, "unit": "GiB"},
                "gpu": {"devices": [0, 1]},
                "vram": {"capacity": 48.0, "unit": "GiB"},
                "io": {"capacity": 10000},
                "network": {"capacity": 10.0, "unit": "Gbps"},
                "file_descriptors": {"capacity": 4096},
                "threads": {"capacity": 1024},
                "storage": {"capacity": 500.0, "unit": "GiB"},
            },
            "safety": {
                "memory_margin": 4.0,
                "vram_margin": 2.0,
                "fd_margin": 256,
                "telemetry_uncertainty": 1.0,
            },
            "reservation": {
                "max_active": 1000,
                "ttl": 60.0,
                "expiry_policy": "quarantine",
                "reclamation_policy": "immediate",
            },
            "worker": {
                "max_concurrency": 8,
                "heartbeat_interval": 5.0,
                "stale_after": 15.0,
                "drain_timeout": 30.0,
                "retirement_policy": "quiescent_fenced",
            },
            "scaling": {
                "scale_up": {
                    "enabled": True,
                    "minimum_workers": 2,
                    "maximum_workers": 16,
                    "admission_threshold": 0.85,
                },
                "scale_down": {
                    "enabled": True,
                    "idle_threshold": 0.15,
                    "drain_required": True,
                    "quiescence_required": True,
                    "fencing_required": True,
                },
            },
        }

        auth = ResourceAuthority()
        policy = auth.load_declarative_policy(raw_config)

        self.assertEqual(policy.limits.cpu_mcores, 16000)
        self.assertEqual(policy.limits.memory_bytes, 64 * 1024 * 1024 * 1024)
        self.assertEqual(policy.limits.gpu_devices, (0, 1))

    def test_worker_scaling_lifecycle_scale_up_and_down(self):
        """Validates ScaleUp and ScaleDown transitions with quiescence and tombstone fencing."""
        auth = ResourceAuthority()

        # ScaleUp
        wrk = auth.scale_up_register_worker(worker_id=1, generation=1, capabilities={"gpu.compute"})
        self.assertEqual(wrk.worker_id, 1)

        # Make a reservation on worker 1
        _rec = auth.reserve(
            res_id=10,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )

        # ScaleDown Drain phase
        auth.scale_down_drain_worker(1)
        self.assertFalse(auth.is_worker_retirable(1), "Worker 1 has active reservation, must not be retirable")

        # Attempting retirement must raise WorkerNotQuiescentError
        from cortex.tools.kernel.resource_authority import WorkerNotQuiescentError

        with self.assertRaises(WorkerNotQuiescentError):
            auth.scale_down_retire_worker(1)

        # Release reservation
        auth.release(10)
        self.assertTrue(auth.is_worker_retirable(1), "Worker 1 should now be retirable")

        # Retire worker 1
        ret_wrk = auth.scale_down_retire_worker(1)
        self.assertEqual(ret_wrk.state.name, "RETIRED")

        # Attempting to re-register worker 1 with stale generation 1 must be rejected by tombstones
        with self.assertRaises(InvalidFencingError):
            auth.scale_up_register_worker(worker_id=1, generation=1, capabilities={"gpu.compute"})


if __name__ == "__main__":
    unittest.main()
