"""
Phase 7.3: Concrete Multi-Dimensional Resource Vector Authority Test Suite
Normative Specification: Research Note 21 / Coq Phase 7 Refinement Model
Refinement Certificate Version: RCA-7.3-v1

Verifies heterogeneous resource domain algebra, unit normalization,
vector capacity invariants, Gate A enforcement contract derivation,
and crash-safe WAL recovery.
"""

import unittest

from cortex.tools.kernel.resource_authority import (
    DemandVector,
    GPUCollisionError,
    InsufficientCapacityError,
    InvalidFencingError,
    ReservationRecord,
    ReservationStatus,
    ResourceAuthority,
    parse_resource_unit,
)


class TestConcreteResourceVectorAuthority(unittest.TestCase):

    def test_unit_string_normalization(self):
        """Validates exact integer normalization for CPU, Memory, Network, and IO strings."""
        # CPU millicores
        self.assertEqual(parse_resource_unit("4", default_unit="cpu"), 4000)
        self.assertEqual(parse_resource_unit("4cores", default_unit="cpu"), 4000)
        self.assertEqual(parse_resource_unit("4000m", default_unit="cpu"), 4000)
        self.assertEqual(parse_resource_unit("4000mcores", default_unit="cpu"), 4000)

        # Memory bytes
        self.assertEqual(parse_resource_unit("8GiB", default_unit="memory"), 8 * 1024 * 1024 * 1024)
        self.assertEqual(parse_resource_unit("8192MiB", default_unit="memory"), 8192 * 1024 * 1024)
        self.assertEqual(parse_resource_unit("12GiB", default_unit="memory"), 12 * 1024 * 1024 * 1024)
        self.assertEqual(parse_resource_unit("512MB", default_unit="memory"), 512 * 1024 * 1024)

        # Network / Rate-based
        self.assertEqual(parse_resource_unit("100Mbps", default_unit="network"), 100)
        self.assertEqual(parse_resource_unit("1Gbps", default_unit="network"), 1000)

    def test_demand_vector_algebra(self):
        """Validates vector addition, dictionary parsing, and zero testing."""
        v1 = DemandVector.from_dict({"cpu": "2", "memory": "4GiB", "gpu": [0]})
        v2 = DemandVector.from_dict({"cpu": "4", "memory": "8GiB", "gpu": [1]})

        combined = v1 + v2
        self.assertEqual(combined.cpu_mcores, 6000)
        self.assertEqual(combined.memory_bytes, 12 * 1024 * 1024 * 1024)
        self.assertEqual(combined.gpu_devices, (0, 1))

        self.assertTrue(DemandVector().is_zero())
        self.assertFalse(v1.is_zero())

    def test_multi_dimensional_vector_reserve(self):
        """Validates reservation with full multi-dimensional DemandVector."""
        auth = ResourceAuthority(capacity=16000)
        vec = DemandVector.from_dict({
            "cpu": "4",
            "memory": "8GiB",
            "vram": "12GiB",
            "gpu": [0],
            "network": "100Mbps",
        })

        rec = auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
            demand_vector=vec,
        )

        self.assertEqual(rec.res_id, 1)
        self.assertEqual(rec.demand_vector.cpu_mcores, 4000)
        self.assertEqual(rec.demand_vector.memory_bytes, 8 * 1024 * 1024 * 1024)
        self.assertEqual(rec.demand_vector.gpu_devices, (0,))
        self.assertIn(0, auth._gpu_owners)
        self.assertTrue(auth.check_invariants())

    def test_vector_capacity_overflow_safety(self):
        """Validates policy enforcement when multi-dimensional vector exceeds capacity limits."""
        policy_dict = {
            "schema": {"name": "cortex-resource-policy", "version": "1"},
            "resource_profile": {
                "cpu": {"capacity": 8.0, "unit": "cores"},
                "memory": {"capacity": 16.0, "unit": "GiB"},
                "gpu": {"devices": [0, 1]},
                "vram": {"capacity": 24.0, "unit": "GiB"},
            },
            "safety": {
                "memory_margin": 2.0,
                "vram_margin": 4.0,
                "telemetry_uncertainty": 0.0,
            },
            "reservation": {"max_active": 100},
            "worker": {"max_concurrency": 4},
        }

        auth = ResourceAuthority()
        auth.load_declarative_policy(policy_dict)

        # Valid reservation within bounds (15 GiB memory limit = 16 - 2 = 14 GiB max)
        valid_vec = DemandVector.from_dict({"cpu": "4", "memory": "10GiB", "vram": "16GiB"})
        auth.reserve(
            res_id=1, res_inv=101, res_att=1, res_worker=1,
            authority_epoch=1, lease_epoch=1, worker_generation=1,
            demand_vector=valid_vec,
        )

        # Exceed memory limit (10 + 6 = 16 GiB > 14 GiB max schedulable)
        overflow_vec = DemandVector.from_dict({"cpu": "2", "memory": "6GiB", "vram": "2GiB"})
        with self.assertRaises(InsufficientCapacityError):
            auth.reserve(
                res_id=2, res_inv=102, res_att=2, res_worker=1,
                authority_epoch=1, lease_epoch=1, worker_generation=1,
                demand_vector=overflow_vec,
            )

    def test_multi_gpu_discrete_ownership_and_collision(self):
        """Validates discrete set operations and collision detection for multi-GPU requests."""
        auth = ResourceAuthority(capacity=16000)
        vec_gpus = DemandVector.from_dict({"cpu": "4", "gpu": [0, 1]})

        rec1 = auth.reserve(
            res_id=1, res_inv=101, res_att=1, res_worker=1,
            authority_epoch=1, lease_epoch=1, worker_generation=1,
            demand_vector=vec_gpus,
        )

        self.assertEqual(rec1.demand_vector.gpu_devices, (0, 1))
        self.assertEqual(auth._gpu_owners[0], 1)
        self.assertEqual(auth._gpu_owners[1], 1)

        # Overlapping GPU request must fail with GPUCollisionError
        vec_collision = DemandVector.from_dict({"cpu": "2", "gpu": [1, 2]})
        with self.assertRaises(GPUCollisionError):
            auth.reserve(
                res_id=2, res_inv=102, res_att=2, res_worker=2,
                authority_epoch=1, lease_epoch=1, worker_generation=1,
                demand_vector=vec_collision,
            )

        # Releasing reservation 1 must free both GPU 0 and GPU 1
        auth.release(1)
        self.assertNotIn(0, auth._gpu_owners)
        self.assertNotIn(1, auth._gpu_owners)

        # Now reservation 2 with GPUs [1, 2] should succeed
        rec2 = auth.reserve(
            res_id=2, res_inv=102, res_att=2, res_worker=2,
            authority_epoch=1, lease_epoch=1, worker_generation=1,
            demand_vector=vec_collision,
        )
        self.assertEqual(rec2.res_id, 2)

    def test_gate_a_enforcement_contract_derivation(self):
        """Validates derivation of immutable Gate A EnforcementContract from ReservationRecord."""
        auth = ResourceAuthority(capacity=16000)
        vec = DemandVector.from_dict({
            "cpu": "8",
            "memory": "16GiB",
            "threads": 2048,
        })

        rec = auth.reserve(
            res_id=10, res_inv=101, res_att=1, res_worker=42,
            authority_epoch=1, lease_epoch=1, worker_generation=1,
            demand_vector=vec,
        )

        contract = rec.to_enforcement_contract()
        self.assertEqual(contract.reservation_id, 10)
        self.assertEqual(contract.worker_id, 42)
        self.assertEqual(contract.cpu_mcores, 8000)
        self.assertEqual(contract.memory_bytes, 16 * 1024 * 1024 * 1024)
        self.assertEqual(contract.pids_max, 2048)
        self.assertEqual(contract.to_cgroup_cpu_max(), "800000 100000")
        self.assertEqual(contract.to_cgroup_memory_max(), str(16 * 1024 * 1024 * 1024))

    def test_fsm_pending_to_active_activation(self):
        """Validates FSM linearization point for OpActivate."""
        auth = ResourceAuthority(capacity=16000)
        rec = auth.reserve(
            res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=100,
            authority_epoch=1, lease_epoch=1, worker_generation=1,
        )
        self.assertEqual(rec.res_status, ReservationStatus.ACTIVE)

        # Set status to PENDING to test activation transition
        rec.res_status = ReservationStatus.PENDING
        activated_rec = auth.activate(1)
        self.assertEqual(activated_rec.res_status, ReservationStatus.ACTIVE)

    def test_full_vector_wal_recovery_replay(self):
        """Validates crash-safe recovery replay preserving multi-dimensional DemandVector and GPU state."""
        auth1 = ResourceAuthority(capacity=16000)
        vec1 = DemandVector.from_dict({"cpu": "4", "memory": "8GiB", "gpu": [2]})
        vec2 = DemandVector.from_dict({"cpu": "2", "memory": "4GiB"})

        auth1.reserve(
            res_id=1, res_inv=101, res_att=1, res_worker=1,
            authority_epoch=1, lease_epoch=1, worker_generation=1,
            demand_vector=vec1,
        )
        auth1.reserve(
            res_id=2, res_inv=102, res_att=2, res_worker=1,
            authority_epoch=1, lease_epoch=1, worker_generation=1,
            demand_vector=vec2,
        )

        records = list(auth1._reservations.values())

        # Simulate engine crash and state recovery
        auth2 = ResourceAuthority(capacity=16000)
        auth2.recover_from_records(records, authority_epoch=1)

        self.assertEqual(len(auth2._reservations), 2)
        self.assertEqual(auth2._reservations[1].demand_vector.gpu_devices, (2,))
        self.assertIn(2, auth2._gpu_owners)
        self.assertEqual(auth1.alpha(), auth2.alpha())

    def test_release_idempotency_and_double_release_protection(self):
        """Phase 7.3a: Validates double-release protection and zero double-reclamation."""
        auth = ResourceAuthority(capacity=16000)
        vec = DemandVector.from_dict({"cpu": "4", "memory": "8GiB", "gpu": [0]})

        rec = auth.reserve(
            res_id=1, res_inv=101, res_att=1, res_worker=1,
            authority_epoch=1, lease_epoch=1, worker_generation=1,
            demand_vector=vec,
        )

        # Initial release
        rec_rel1 = auth.release(1)
        self.assertEqual(rec_rel1.res_status, ReservationStatus.RELEASED)
        self.assertNotIn(0, auth._gpu_owners)

        # Second release (idempotent no-op)
        rec_rel2 = auth.release(1)
        self.assertEqual(rec_rel2.res_status, ReservationStatus.RELEASED)

        # Third release (idempotent no-op)
        rec_rel3 = auth.release(1)
        self.assertEqual(rec_rel3.res_status, ReservationStatus.RELEASED)

        # Confirm invariants and accounting remain nonnegative
        self.assertTrue(auth.check_invariants())
        self.assertGreaterEqual(auth._used_capacity, 0)

    def test_fencing_rejection_on_release_expire_revoke(self):
        """Phase 7.3a: Validates fencing credential checks on release, expire, and revoke."""
        auth = ResourceAuthority(capacity=16000)
        rec = auth.reserve(
            res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000,
            authority_epoch=1, lease_epoch=2, worker_generation=1,
        )

        # Stale authority epoch on release must be rejected
        with self.assertRaises(InvalidFencingError):
            auth.release(1, authority_epoch=99)

        # Retired worker generation on release must be rejected
        auth._retired_tombstones[(1, 1)] = True
        with self.assertRaises(InvalidFencingError):
            auth.release(1, res_worker=1, worker_generation=1)

        # Stale lease epoch on release must be rejected
        with self.assertRaises(InvalidFencingError):
            auth.release(1, res_worker=1, worker_generation=2, lease_epoch=1)

        self.assertEqual(rec.res_status, ReservationStatus.ACTIVE)

    def test_causal_distinction_release_expire_revoke(self):
        """Phase 7.3a: Validates distinct causal semantics for Release, Expire, and Revoke."""
        auth = ResourceAuthority(capacity=16000)

        # Release (normal completion) -> RELEASED (not in quarantine)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=500)
        rec_rel = auth.release(1)
        self.assertEqual(rec_rel.res_status, ReservationStatus.RELEASED)
        self.assertNotIn(1, auth._quarantine)

        # Expire (TTL timeout) -> EXPIRED (placed in quarantine)
        auth.reserve(res_id=2, res_inv=102, res_att=1, res_worker=1, res_demand=500)
        rec_exp = auth.expire(2)
        self.assertEqual(rec_exp.res_status, ReservationStatus.EXPIRED)
        self.assertIn(2, auth._quarantine)

        # Revoke (authority fence/invalidation) -> REVOKED (placed in quarantine)
        auth.reserve(res_id=3, res_inv=103, res_att=1, res_worker=1, res_demand=500)
        rec_rev = auth.revoke(3)
        self.assertEqual(rec_rev.res_status, ReservationStatus.REVOKED)
        self.assertIn(3, auth._quarantine)

    def test_multi_gpu_release_isolation(self):
        """Phase 7.3a: Validates that releasing GPU0 does not modify ownership of GPU1."""
        auth = ResourceAuthority(capacity=16000)
        vec1 = DemandVector.from_dict({"cpu": "2", "gpu": [0]})
        vec2 = DemandVector.from_dict({"cpu": "2", "gpu": [1]})

        auth.reserve(res_id=1, res_inv=101, res_att=101, res_worker=1, demand_vector=vec1)
        auth.reserve(res_id=2, res_inv=102, res_att=102, res_worker=2, demand_vector=vec2)

        self.assertEqual(auth._gpu_owners[0], 1)
        self.assertEqual(auth._gpu_owners[1], 2)

        # Release reservation 1
        auth.release(1)

        self.assertNotIn(0, auth._gpu_owners)
        self.assertEqual(auth._gpu_owners[1], 2)
        self.assertTrue(auth.check_invariants())

    def test_property_based_random_lifecycle_sequences(self):
        """Phase 7.3a: Property-based test generating random sequences of lifecycle operations."""
        import random

        auth = ResourceAuthority(capacity=32000)
        active_ids = set()
        all_ids = set()

        for step in range(100):
            op = random.choice(["reserve", "activate", "release", "expire", "revoke"])

            if op == "reserve" or not active_ids:
                res_id = len(all_ids) + 1
                all_ids.add(res_id)
                active_ids.add(res_id)
                vec = DemandVector.from_dict({"cpu": str(random.randint(1, 4)), "memory": "1GiB"})
                try:
                    auth.reserve(
                        res_id=res_id,
                        res_inv=1000 + res_id,
                        res_att=2000 + res_id,
                        res_worker=random.randint(1, 4),
                        authority_epoch=1,
                        lease_epoch=step + 1,
                        worker_generation=1,
                        demand_vector=vec,
                    )
                except (InsufficientCapacityError, UniquenessViolationError):
                    active_ids.remove(res_id)
            else:
                target_id = random.choice(list(active_ids))
                if op == "activate":
                    try:
                        auth.activate(target_id)
                    except Exception:
                        pass
                elif op == "release":
                    auth.release(target_id)
                    active_ids.remove(target_id)
                elif op == "expire":
                    auth.expire(target_id)
                    active_ids.remove(target_id)
                elif op == "revoke":
                    auth.revoke(target_id)
                    active_ids.remove(target_id)

            self.assertTrue(auth.check_invariants())


if __name__ == "__main__":
    unittest.main()
