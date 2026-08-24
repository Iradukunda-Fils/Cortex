"""
Unit and negative/fencing tests for GatewayIdempotencyEngine & LeaseEpoch Fencing (Issue #44)
"""

import unittest

from cortex.tools.kernel.idempotency import (
    CanonicalOperation,
    DuplicateAttemptIdError,
    GatewayIdempotencyEngine,
    MissingDomainSecretError,
    StaleLeaseEpochError,
)


class TestGatewayIdempotencyEngine(unittest.TestCase):
    """Test suite for Issue #44 Gateway HMAC Idempotency Engine & Fencing."""

    def setUp(self) -> None:
        self.secrets_vault = {
            "v1": b"domain_secret_key_v1_32bytes_long!",
            "v2": b"domain_secret_key_v2_rotated_32b!",
        }
        self.engine = GatewayIdempotencyEngine(self.secrets_vault)

    def test_same_invocation_same_operation_same_key(self) -> None:
        op1 = CanonicalOperation(
            invocation_id="inv_1001",
            resource_id="s3://bucket/data.bin",
            operation_type="PUT",
            canonical_payload=b"payload_data_alpha",
        )
        op2 = CanonicalOperation(
            invocation_id="inv_1001",
            resource_id="s3://bucket/data.bin",
            operation_type="PUT",
            canonical_payload=b"payload_data_alpha",
        )

        key1 = self.engine.derive_idempotency_key(op1, secret_version="v1")
        key2 = self.engine.derive_idempotency_key(op2, secret_version="v1")

        self.assertEqual(key1, key2)
        self.assertTrue(key1.startswith("hmac-sha256:v1:"))

    def test_same_invocation_different_payload_different_key(self) -> None:
        op1 = CanonicalOperation(
            invocation_id="inv_1001",
            resource_id="s3://bucket/data.bin",
            operation_type="PUT",
            canonical_payload=b"payload_data_alpha",
        )
        op2 = CanonicalOperation(
            invocation_id="inv_1001",
            resource_id="s3://bucket/data.bin",
            operation_type="PUT",
            canonical_payload=b"payload_data_BETA_MODIFIED",
        )

        key1 = self.engine.derive_idempotency_key(op1, secret_version="v1")
        key2 = self.engine.derive_idempotency_key(op2, secret_version="v1")

        self.assertNotEqual(key1, key2)

    def test_same_invocation_different_resource_different_key(self) -> None:
        op1 = CanonicalOperation(
            invocation_id="inv_1001",
            resource_id="s3://bucket/resource_A",
            operation_type="PUT",
            canonical_payload=b"payload",
        )
        op2 = CanonicalOperation(
            invocation_id="inv_1001",
            resource_id="s3://bucket/resource_B",
            operation_type="PUT",
            canonical_payload=b"payload",
        )

        key1 = self.engine.derive_idempotency_key(op1, secret_version="v1")
        key2 = self.engine.derive_idempotency_key(op2, secret_version="v1")

        self.assertNotEqual(key1, key2)

    def test_same_invocation_different_operation_different_key(self) -> None:
        op1 = CanonicalOperation(
            invocation_id="inv_1001",
            resource_id="s3://bucket/data.bin",
            operation_type="PUT",
            canonical_payload=b"payload",
        )
        op2 = CanonicalOperation(
            invocation_id="inv_1001",
            resource_id="s3://bucket/data.bin",
            operation_type="DELETE",
            canonical_payload=b"payload",
        )

        key1 = self.engine.derive_idempotency_key(op1, secret_version="v1")
        key2 = self.engine.derive_idempotency_key(op2, secret_version="v1")

        self.assertNotEqual(key1, key2)

    def test_same_invocation_same_operation_retry_same_key(self) -> None:
        op = CanonicalOperation(
            invocation_id="inv_1001",
            resource_id="s3://bucket/data.bin",
            operation_type="PUT",
            canonical_payload=b"retry_payload",
        )

        ctx1 = self.engine.create_adapter_context(
            op=op,
            execution_attempt_id="att_1",
            adapter_request_id="req_1",
            lease_epoch=1,
            secret_version="v1",
        )

        ctx2 = self.engine.create_adapter_context(
            op=op,
            execution_attempt_id="att_2",
            adapter_request_id="req_2",
            lease_epoch=2,
            secret_version="v1",
        )

        self.assertEqual(ctx1.idempotency_key, ctx2.idempotency_key)
        self.assertNotEqual(ctx1.execution_attempt_id, ctx2.execution_attempt_id)
        self.assertGreater(ctx2.lease_epoch, ctx1.lease_epoch)

    def test_epoch_monotonic_progression_fencing(self) -> None:
        # Epoch 5 -> Accepted
        self.engine.validate_lease_epoch_and_attempt("inv_2000", "att_1", 5)

        # Epoch 6 -> Accepted
        self.engine.validate_lease_epoch_and_attempt("inv_2000", "att_2", 6)

        # Epoch 5 (Stale) -> Rejected
        with self.assertRaises(StaleLeaseEpochError):
            self.engine.validate_lease_epoch_and_attempt("inv_2000", "att_3", 5)

        # Epoch 6 (Equal / Stale) -> Rejected
        with self.assertRaises(StaleLeaseEpochError):
            self.engine.validate_lease_epoch_and_attempt("inv_2000", "att_4", 6)

    def test_duplicate_attempt_id_rejection(self) -> None:
        self.engine.validate_lease_epoch_and_attempt("inv_3000", "att_1", 1)

        with self.assertRaises(DuplicateAttemptIdError):
            self.engine.validate_lease_epoch_and_attempt("inv_3000", "att_1", 2)

    def test_key_rotation_persisted_version_isolation(self) -> None:
        op = CanonicalOperation(
            invocation_id="inv_4000",
            resource_id="db://records/user_42",
            operation_type="UPDATE",
            canonical_payload=b"user_data",
        )

        # Historical derivation using v1
        key_v1 = self.engine.derive_idempotency_key(op, secret_version="v1")

        # Active secret rotated to v2, but historical invocation presents persisted v1
        historical_retry_key = self.engine.derive_idempotency_key(op, secret_version="v1")
        new_v2_key = self.engine.derive_idempotency_key(op, secret_version="v2")

        self.assertEqual(key_v1, historical_retry_key)
        self.assertNotEqual(key_v1, new_v2_key)
        self.assertTrue(key_v1.startswith("hmac-sha256:v1:"))
        self.assertTrue(new_v2_key.startswith("hmac-sha256:v2:"))

    def test_missing_secret_version_rejection(self) -> None:
        op = CanonicalOperation(
            invocation_id="inv_5000",
            resource_id="db://records/1",
            operation_type="READ",
            canonical_payload=b"",
        )
        with self.assertRaises(MissingDomainSecretError):
            self.engine.derive_idempotency_key(op, secret_version="v99")


if __name__ == "__main__":
    unittest.main()
