"""
Phase 5 System Integration & Distributed Execution Validation Test Suite (v1.5.1-FINAL-FROZEN)

Verifies end-to-end interactions between Gateway, Dynamic Load Balancer (#34), ObjectRef Data Plane (#42),
and Effect Reconciliation Engine (#45).
"""

import hashlib
import unittest

from cortex.tools.kernel.adapter_contract import (
    AdapterExecutionContext,
    AdapterOutcome,
    EffectClassification,
    ExecutionStatus,
)
from cortex.tools.kernel.idempotency import (
    CanonicalOperation,
    GatewayIdempotencyEngine,
    StaleLeaseEpochError,
)
from cortex.tools.kernel.load_balancer import (
    DynamicLoadBalancer,
)
from cortex.tools.kernel.object_ref import (
    BoundedChunkReader,
    DataPlaneResolver,
    ObjectRef,
    StreamProvider,
)
from cortex.tools.kernel.reconciliation import (
    EffectReconciliationEngine,
    IndeterminateEffectError,
    InvocationState,
    QuarantinedResourceError,
)


class MockWitnessProbe:
    def __init__(self, status: ExecutionStatus) -> None:
        self.status = status

    def probe_status(self, ctx: AdapterExecutionContext) -> ExecutionStatus:
        return self.status


class MemoryStream(StreamProvider):
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def read_chunk(self, max_bytes: int) -> bytes:
        if self.offset >= len(self.data):
            return b""
        chunk = self.data[self.offset : self.offset + max_bytes]
        self.offset += len(chunk)
        return chunk


class TestPhase5SystemIntegration(unittest.TestCase):
    """System Integration & Distributed Execution Validation Suite for Phase 5."""

    def setUp(self) -> None:
        self.secrets_vault = {"v1": b"integration_secret_key_32_bytes!"}
        self.idempotency_engine = GatewayIdempotencyEngine(self.secrets_vault)
        self.load_balancer = DynamicLoadBalancer(self.idempotency_engine)
        self.reconciliation_engine = EffectReconciliationEngine()
        self.data_plane = DataPlaneResolver()

        # Register execution workers
        self.load_balancer.register_worker(
            "worker_alpha", capacity=3, capabilities={"compute.heavy", "storage.read", "execution.submit"}
        )
        self.load_balancer.register_worker(
            "worker_beta", capacity=5, capabilities={"compute.heavy", "storage.read", "execution.submit"}
        )

    def test_full_pipeline_success_with_object_ref_and_reconciliation(self) -> None:
        # 1. Prepare ObjectRef
        payload_data = b"Phase 5 Integration Payload Data"
        digest = f"sha256:{hashlib.sha256(payload_data).hexdigest()}"
        obj_ref = ObjectRef(
            object_id="obj_p5_001",
            version="v1",
            content_digest=digest,
            size_bytes=len(payload_data),
        )
        stream_provider = MemoryStream(payload_data)
        self.data_plane.register_object_storage("obj_p5_001", "s3://internal/p5_001.bin", stream_provider)

        # 2. Canonical Operation
        op = CanonicalOperation(
            invocation_id="inv_p5_pipe_100",
            resource_id="db://analytics/job_1",
            operation_type="ANALYZE",
            canonical_payload=b"op_config",
        )

        # 3. Load Balancer Admittance & Worker Selection
        asgn = self.load_balancer.assign_execution(
            op=op,
            execution_attempt_id="att_1",
            adapter_request_id="req_1",
            user_capabilities={"compute.heavy", "storage.read"},
            required_capability="compute.heavy",
        )

        self.assertEqual(asgn.lease_epoch, 1)
        self.assertIn(asgn.worker_id, ("worker_alpha", "worker_beta"))

        # 4. Resolve Opaque PhysicalLocatorHandle & Stream Data
        handle = self.data_plane.resolve_locator_handle(
            auth_ctx=asgn.context,
            obj_ref=obj_ref,
            user_capabilities={"storage.read"},
        )

        reader_stream = self.data_plane.get_stream_provider(
            handle=handle,
            obj_ref=obj_ref,
            request_invocation_id=asgn.context.invocation_id,
            request_attempt_id=asgn.context.execution_attempt_id,
        )
        reader = BoundedChunkReader(reader_stream)
        self.assertTrue(reader.verify_integrity_stream(obj_ref))

        # 5. Execute & Reconcile Confirmed Effect
        outcome = AdapterOutcome(status=ExecutionStatus.EFFECT_CONFIRMED)
        rec_state = self.reconciliation_engine.reconcile_effect(
            ctx=asgn.context,
            classification=EffectClassification.IDEMPOTENT_WRITE,
            outcome=outcome,
        )
        self.assertEqual(rec_state, InvocationState.CONFIRMED)

        # 6. Complete Execution & Release Capacity
        self.load_balancer.complete_execution(op.invocation_id)

    def test_reassignment_prevents_stale_commits_and_quarantines_ambiguous_failure(self) -> None:
        op = CanonicalOperation(
            invocation_id="inv_p5_failover_200",
            resource_id="db://payments/transfer_888",
            operation_type="TRANSFER_FUNDS",
            canonical_payload=b"amount=10000",
        )

        # Step 1: Assign to Worker Alpha at Epoch 1
        asgn1 = self.load_balancer.assign_execution(
            op=op,
            execution_attempt_id="att_1",
            adapter_request_id="req_1",
            user_capabilities={"compute.heavy", "execution.submit"},
        )
        self.assertEqual(asgn1.lease_epoch, 1)
        original_key = asgn1.context.idempotency_key

        # Step 2: Worker Alpha experiences crash/timeout -> Drain & Reassign to Worker Beta at Epoch 2
        self.load_balancer.drain_worker(asgn1.worker_id)

        asgn2 = self.load_balancer.reassign_failed_execution(
            op=op,
            new_attempt_id="att_2",
            new_adapter_request_id="req_2",
            user_capabilities={"compute.heavy", "execution.submit"},
        )
        self.assertEqual(asgn2.lease_epoch, 2)
        # Assert HMAC key invariant preserved across workers!
        self.assertEqual(asgn2.context.idempotency_key, original_key)

        # Step 3: Worker Alpha attempts post-recovery commit with Epoch 1 -> REJECTED by Gateway Fencing
        with self.assertRaises(StaleLeaseEpochError):
            self.idempotency_engine.validate_lease_epoch_and_attempt(
                invocation_id=op.invocation_id,
                execution_attempt_id="att_1_delayed",
                presented_epoch=asgn1.context.lease_epoch,  # Epoch 1 <= active Epoch 2
            )

        # Step 4: Worker Beta experiences UNKNOWN_EFFECT for non-idempotent operation with no witness
        outcome = AdapterOutcome(status=ExecutionStatus.UNKNOWN_EFFECT)
        with self.assertRaises(IndeterminateEffectError):
            self.reconciliation_engine.reconcile_effect(
                ctx=asgn2.context,
                classification=EffectClassification.NON_IDEMPOTENT_WRITE,
                outcome=outcome,
            )

        # Step 5: Assert Resource Scope is Quarantined & Blocked from Further Operations
        self.assertTrue(self.reconciliation_engine.is_resource_quarantined("db://payments/transfer_888"))

        op_subsequent = CanonicalOperation(
            invocation_id="inv_p5_blocked_300",
            resource_id="db://payments/transfer_888",  # Quarantined resource
            operation_type="TRANSFER_FUNDS",
            canonical_payload=b"amount=500",
        )
        asgn3 = self.load_balancer.assign_execution(
            op=op_subsequent,
            execution_attempt_id="att_1",
            adapter_request_id="req_sub",
            user_capabilities={"compute.heavy", "execution.submit"},
        )
        with self.assertRaises(QuarantinedResourceError):
            self.reconciliation_engine.reconcile_effect(
                ctx=asgn3.context,
                classification=EffectClassification.NON_IDEMPOTENT_WRITE,
                outcome=AdapterOutcome(status=ExecutionStatus.EFFECT_CONFIRMED),
            )


if __name__ == "__main__":
    unittest.main()
