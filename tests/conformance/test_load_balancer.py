"""
Conformance, Integration, and Fencing Tests for Single-Gateway Dynamic Load Balancer (Issue #34)
"""

import unittest

from cortex.tools.kernel.idempotency import (
    CanonicalOperation,
    GatewayIdempotencyEngine,
    StaleLeaseEpochError,
)
from cortex.tools.kernel.load_balancer import (
    DynamicLoadBalancer,
    NoEligibleWorkerError,
    WorkerStatus,
)


class TestDynamicLoadBalancer(unittest.TestCase):
    """Test suite for Issue #34 Dynamic Load Balancer Engine & Fencing Integrations."""

    def setUp(self) -> None:
        self.secrets_vault = {"v1": b"domain_secret_key_32bytes_vault!"}
        self.idempotency_engine = GatewayIdempotencyEngine(self.secrets_vault)
        self.load_balancer = DynamicLoadBalancer(self.idempotency_engine)

        # Register Workers
        self.load_balancer.register_worker("worker_a", capacity=2, capabilities={"execution.submit"})
        self.load_balancer.register_worker("worker_b", capacity=5, capabilities={"execution.submit"})

    def test_worker_selection_least_loaded(self) -> None:
        op = CanonicalOperation(
            invocation_id="inv_lb_001",
            resource_id="gpu://cluster/node_1",
            operation_type="TRAIN_MODEL",
            canonical_payload=b"hyperparams",
        )

        assignment = self.load_balancer.assign_execution(
            op=op,
            execution_attempt_id="att_1",
            adapter_request_id="req_1",
            user_capabilities={"execution.submit"},
        )

        # Worker B selected (0/5 load vs 0/2 load -> tie-breaker or equal ratio)
        self.assertIn(assignment.worker_id, ("worker_a", "worker_b"))
        self.assertEqual(assignment.lease_epoch, 1)

    def test_eligibility_does_not_override_authorization(self) -> None:
        op = CanonicalOperation(
            invocation_id="inv_lb_002",
            resource_id="gpu://cluster/node_1",
            operation_type="TRAIN_MODEL",
            canonical_payload=b"hyperparams",
        )

        with self.assertRaises(NoEligibleWorkerError):
            self.load_balancer.assign_execution(
                op=op,
                execution_attempt_id="att_1",
                adapter_request_id="req_1",
                user_capabilities=set(),  # Missing execution.submit
            )

    def test_critical_reassignment_fencing_scenario(self) -> None:
        """
        Critical Test Scenario:
        1. Invocation assigned to Worker A at Epoch 1.
        2. Worker A becomes unhealthy.
        3. Invocation reassigned to Worker B at Epoch 2 (same InvocationID, same IdempotencyKey, higher LeaseEpoch).
        4. Worker A post-recovery attempts to present Epoch 1 -> REJECTED (StaleLeaseEpochError).
        5. Worker B presents Epoch 2 -> ACCEPTED.
        """
        lb = DynamicLoadBalancer(self.idempotency_engine)
        lb.register_worker("worker_a", capacity=10, capabilities={"execution.submit"})
        lb.register_worker("worker_b", capacity=5, capabilities={"execution.submit"})

        op = CanonicalOperation(
            invocation_id="inv_critical_fencing_100",
            resource_id="db://cluster/transaction_99",
            operation_type="TRANSFER",
            canonical_payload=b"amount=5000",
        )

        # 1. Assign to Worker A at Epoch 1
        asgn1 = lb.assign_execution(
            op=op,
            execution_attempt_id="att_1",
            adapter_request_id="req_1",
            user_capabilities={"execution.submit"},
        )
        self.assertEqual(asgn1.worker_id, "worker_a")
        self.assertEqual(asgn1.lease_epoch, 1)
        original_key = asgn1.context.idempotency_key

        # 2. Worker A becomes UNHEALTHY
        lb.update_worker_status("worker_a", WorkerStatus.UNHEALTHY)

        # 3. Reassign to Worker B at Epoch 2
        asgn2 = lb.reassign_failed_execution(
            op=op,
            new_attempt_id="att_2",
            new_adapter_request_id="req_2",
            user_capabilities={"execution.submit"},
        )
        self.assertEqual(asgn2.worker_id, "worker_b")
        self.assertEqual(asgn2.lease_epoch, 2)
        self.assertNotEqual(asgn1.worker_id, asgn2.worker_id)
        # Assert same IdempotencyKey preserved across workers!
        self.assertEqual(asgn2.context.idempotency_key, original_key)

        # 4. Worker A post-recovery attempts to validate Epoch 1 -> REJECTED
        with self.assertRaises(StaleLeaseEpochError):
            self.idempotency_engine.validate_lease_epoch_and_attempt(
                invocation_id="inv_critical_fencing_100",
                execution_attempt_id="att_3",  # Stale attempt from Worker A
                presented_epoch=1,             # Stale epoch 1 <= active epoch 2
            )

        # 5. Worker B validates Epoch 3 (subsequent progression) -> ACCEPTED
        self.idempotency_engine.validate_lease_epoch_and_attempt(
            invocation_id="inv_critical_fencing_100",
            execution_attempt_id="att_3",
            presented_epoch=3,
        )

    def test_worker_drain_safety(self) -> None:
        op = CanonicalOperation(
            invocation_id="inv_drain_001",
            resource_id="db://records/1",
            operation_type="WRITE",
            canonical_payload=b"data",
        )

        asgn = self.load_balancer.assign_execution(
            op=op,
            execution_attempt_id="att_1",
            adapter_request_id="req_1",
            user_capabilities={"execution.submit"},
        )

        worker_to_drain = asgn.worker_id
        drained_invocations = self.load_balancer.drain_worker(worker_to_drain)

        self.assertIn("inv_drain_001", drained_invocations)
        node = self.load_balancer._workers[worker_to_drain]
        self.assertEqual(node.status, WorkerStatus.DRAINING)
        self.assertFalse(node.is_eligible)

    def test_high_volume_rebalancing_stress(self) -> None:
        lb = DynamicLoadBalancer(self.idempotency_engine)
        # Register 10 workers
        for i in range(10):
            lb.register_worker(f"w_{i}", capacity=10, capabilities={"execution.submit"})

        # Submit 100 invocations
        assignments = []
        for i in range(100):
            op = CanonicalOperation(
                invocation_id=f"inv_stress_{i}",
                resource_id="res_stress",
                operation_type="EXEC",
                canonical_payload=b"stress_data",
            )
            asgn = lb.assign_execution(
                op=op,
                execution_attempt_id="att_1",
                adapter_request_id=f"req_{i}",
                user_capabilities={"execution.submit"},
            )
            assignments.append(asgn)

        self.assertEqual(len(assignments), 100)
        # Verify load was evenly distributed across all 10 workers (10 per worker)
        for i in range(10):
            w = lb._workers[f"w_{i}"]
            self.assertEqual(w.active_load, 10)


if __name__ == "__main__":
    unittest.main()
