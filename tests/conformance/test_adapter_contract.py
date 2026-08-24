"""
Conformance tests for External ResourceContract & AdapterExecutionContext (Issue #43)
"""

import unittest

from cortex.tools.kernel.adapter_contract import (
    MAX_INLINE_EVIDENCE_BYTES,
    MAX_INLINE_PAYLOAD_BYTES,
    AdapterExecutionContext,
    AdapterOutcome,
    EffectClassification,
    EffectPayload,
    EvidencePayload,
    ExecutionStatus,
    PayloadSizeExceededError,
    ResourceContract,
)


class MockS3Adapter(ResourceContract):
    """Mock implementation of ResourceContract for S3 storage."""

    @property
    def resource_type(self) -> str:
        return "adapter.s3.v1"

    @property
    def effect_classification(self) -> EffectClassification:
        return EffectClassification.IDEMPOTENT_WRITE

    def execute_effect(
        self,
        ctx: AdapterExecutionContext,
        payload: EffectPayload,
    ) -> AdapterOutcome:
        evidence = EvidencePayload(data=b"OK:" + ctx.idempotency_key.encode("utf-8")[:10])
        return AdapterOutcome(status=ExecutionStatus.EFFECT_CONFIRMED, evidence=evidence)


class TestAdapterContract(unittest.TestCase):
    """Test suite for ResourceContract, payloads, and execution context."""

    def test_effect_payload_inline_limit_enforcement(self) -> None:
        # Valid payload <= 64 KiB
        valid_data = b"A" * MAX_INLINE_PAYLOAD_BYTES
        payload = EffectPayload(data=valid_data)
        self.assertEqual(len(payload.data), MAX_INLINE_PAYLOAD_BYTES)

        # Oversized payload > 64 KiB raises error
        invalid_data = b"A" * (MAX_INLINE_PAYLOAD_BYTES + 1)
        with self.assertRaises(PayloadSizeExceededError):
            EffectPayload(data=invalid_data)

    def test_effect_payload_reference_bypasses_inline_limit(self) -> None:
        # Large reference payload > 64 KiB is allowed when is_reference=True
        large_ref_data = b"OBJECT_REF_HANDLE_META"
        payload = EffectPayload(data=large_ref_data, is_reference=True)
        self.assertTrue(payload.is_reference)

    def test_evidence_payload_inline_limit_enforcement(self) -> None:
        # Valid evidence <= 4 KiB
        valid_data = b"E" * MAX_INLINE_EVIDENCE_BYTES
        evidence = EvidencePayload(data=valid_data)
        self.assertEqual(len(evidence.data), MAX_INLINE_EVIDENCE_BYTES)

        # Oversized evidence > 4 KiB raises error
        invalid_data = b"E" * (MAX_INLINE_EVIDENCE_BYTES + 1)
        with self.assertRaises(PayloadSizeExceededError):
            EvidencePayload(data=invalid_data)

    def test_adapter_execution_context_lineage(self) -> None:
        ctx = AdapterExecutionContext(
            invocation_id="inv_1001",
            execution_attempt_id="att_1",
            adapter_request_id="req_999",
            idempotency_key="hmac_key_xyz",
            lease_epoch=3,
            resource_id="res_bucket_alpha",
            operation_type="PUT_OBJECT",
        )

        lineage = ctx.lineage
        self.assertEqual(lineage.invocation_id, "inv_1001")
        self.assertEqual(lineage.execution_attempt_id, "att_1")
        self.assertEqual(lineage.adapter_request_id, "req_999")
        self.assertEqual(ctx.schema_uri, "https://schemas.cortex.internal/v1/adapter-execution-context.json")

    def test_mock_adapter_execution(self) -> None:
        adapter = MockS3Adapter()
        ctx = AdapterExecutionContext(
            invocation_id="inv_1002",
            execution_attempt_id="att_1",
            adapter_request_id="req_1000",
            idempotency_key="sha256_mock_idempotency_key_12345",
            lease_epoch=1,
            resource_id="s3://bucket/test.txt",
            operation_type="WRITE",
        )
        payload = EffectPayload(data=b"hello s3")
        outcome = adapter.execute_effect(ctx, payload)

        self.assertEqual(outcome.status, ExecutionStatus.EFFECT_CONFIRMED)
        self.assertIsNotNone(outcome.evidence)
        self.assertTrue(outcome.evidence.data.startswith(b"OK:"))


if __name__ == "__main__":
    unittest.main()
