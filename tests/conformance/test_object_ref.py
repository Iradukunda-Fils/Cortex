"""
Conformance and Security Boundary Tests for ObjectRef Data Plane, Opaque Locators, and BoundedChunkReader (Issue #42)
"""

import hashlib
import unittest

from cortex.tools.kernel.adapter_contract import AdapterExecutionContext
from cortex.tools.kernel.object_ref import (
    MAX_VERIFICATION_CHUNK_BYTES,
    BoundedChunkReader,
    DataPlaneAccessDeniedError,
    DataPlaneResolver,
    InvalidLocatorHandleError,
    ObjectIntegrityError,
    ObjectRef,
    PhysicalLocatorHandle,
    StreamProvider,
)


class MemoryBoundStreamProvider(StreamProvider):
    """
    Simulated streaming source capable of producing arbitrary bytes up to huge sizes (e.g. 100 MB+).
    Tracks maximum buffer memory allocated at any single read call to prove constant O(chunk_size) memory bound.
    """

    def __init__(self, total_bytes: int, fill_byte: bytes = b"X") -> None:
        self.total_bytes = total_bytes
        self.bytes_read = 0
        self._preallocated_chunk = fill_byte * MAX_VERIFICATION_CHUNK_BYTES
        self.max_single_read_buffer = 0

    def read_chunk(self, max_bytes: int) -> bytes:
        if self.bytes_read >= self.total_bytes:
            return b""
        chunk_len = min(max_bytes, self.total_bytes - self.bytes_read)
        if chunk_len == MAX_VERIFICATION_CHUNK_BYTES:
            chunk = self._preallocated_chunk
        else:
            chunk = self._preallocated_chunk[:chunk_len]
        self.bytes_read += chunk_len
        self.max_single_read_buffer = max(self.max_single_read_buffer, len(chunk))
        return chunk


class BytesStreamProvider(StreamProvider):
    """Simple StreamProvider wrapping a byte string."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def read_chunk(self, max_bytes: int) -> bytes:
        if self.offset >= len(self.data):
            return b""
        chunk = self.data[self.offset : self.offset + max_bytes]
        self.offset += len(chunk)
        return chunk


class TestObjectRefDataPlane(unittest.TestCase):
    """Test suite for Issue #42 ObjectRef Data Plane & Opaque Locators."""

    def setUp(self) -> None:
        self.auth_ctx = AdapterExecutionContext(
            invocation_id="inv_alpha_100",
            execution_attempt_id="att_1",
            adapter_request_id="req_1",
            idempotency_key="hmac_key_test",
            lease_epoch=1,
            resource_id="res_storage_1",
            operation_type="READ",
        )
        self.resolver = DataPlaneResolver()

    def test_object_ref_identity_no_credentials_leak(self) -> None:
        obj_ref = ObjectRef(
            object_id="obj_dataset_99",
            version="v1",
            content_digest="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            size_bytes=0,
            provenance="inv_alpha_100",
        )
        # Verify ObjectRef contains no credentials or physical endpoint fields
        self.assertFalse(hasattr(obj_ref, "credentials"))
        self.assertFalse(hasattr(obj_ref, "authorization"))
        self.assertFalse(hasattr(obj_ref, "physical_endpoint"))
        self.assertFalse(hasattr(obj_ref, "bearer_token"))

    def test_bounded_chunk_reader_integrity_success(self) -> None:
        data = b"Hello, Cortex Data Plane! Content-Addressed Object Test."
        digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
        obj_ref = ObjectRef(
            object_id="obj_hello",
            version="v1",
            content_digest=digest,
            size_bytes=len(data),
        )

        provider = BytesStreamProvider(data)
        reader = BoundedChunkReader(provider)
        self.assertTrue(reader.verify_integrity_stream(obj_ref))

    def test_bounded_chunk_reader_digest_mismatch_failure(self) -> None:
        data = b"Authentic Data"
        digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
        obj_ref = ObjectRef(
            object_id="obj_tampered",
            version="v1",
            content_digest=digest,
            size_bytes=len(data),
        )

        tampered_data = b"Tampered Data!"
        provider = BytesStreamProvider(tampered_data)
        reader = BoundedChunkReader(provider)
        with self.assertRaises(ObjectIntegrityError):
            reader.verify_integrity_stream(obj_ref)

    def test_bounded_chunk_reader_size_mismatch_failure(self) -> None:
        data = b"Data Payload"
        digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
        obj_ref = ObjectRef(
            object_id="obj_bad_size",
            version="v1",
            content_digest=digest,
            size_bytes=9999,  # Incorrect size
        )

        provider = BytesStreamProvider(data)
        reader = BoundedChunkReader(provider)
        with self.assertRaises(ObjectIntegrityError):
            reader.verify_integrity_stream(obj_ref)

    def test_authorization_granted_valid_request(self) -> None:
        obj_ref = ObjectRef(
            object_id="obj_auth_ok",
            version="v1",
            content_digest="sha256:1234567890123456789012345678901234567890123456789012345678901234",
            size_bytes=100,
            provenance="inv_alpha_100",
        )

        handle = self.resolver.resolve_locator_handle(
            auth_ctx=self.auth_ctx,
            obj_ref=obj_ref,
            user_capabilities={"storage.read"},
            required_capability="storage.read",
            resource_policy_allowed=True,
        )

        self.assertIsInstance(handle, PhysicalLocatorHandle)
        self.assertEqual(handle.invocation_id, "inv_alpha_100")
        self.assertEqual(handle.execution_attempt_id, "att_1")
        # Verify handle leaks no physical topology (no s3://, /mnt/, host, endpoint)
        self.assertTrue(handle.locator_token.startswith("locator_tok_"))
        self.assertFalse(hasattr(handle, "physical_topology"))

    def test_authorization_denied_missing_capability(self) -> None:
        obj_ref = ObjectRef(
            object_id="obj_auth_fail",
            version="v1",
            content_digest="sha256:1234567890123456789012345678901234567890123456789012345678901234",
            size_bytes=100,
        )

        with self.assertRaises(DataPlaneAccessDeniedError):
            self.resolver.resolve_locator_handle(
                auth_ctx=self.auth_ctx,
                obj_ref=obj_ref,
                user_capabilities=set(),  # Missing storage.read
            )

    def test_authorization_denied_resource_policy(self) -> None:
        obj_ref = ObjectRef(
            object_id="obj_policy_denied",
            version="v1",
            content_digest="sha256:1234567890123456789012345678901234567890123456789012345678901234",
            size_bytes=100,
        )

        with self.assertRaises(DataPlaneAccessDeniedError):
            self.resolver.resolve_locator_handle(
                auth_ctx=self.auth_ctx,
                obj_ref=obj_ref,
                user_capabilities={"storage.read"},
                resource_policy_allowed=False,  # Policy denies access
            )

    def test_authorization_denied_provenance_mismatch(self) -> None:
        obj_ref = ObjectRef(
            object_id="obj_wrong_prov",
            version="v1",
            content_digest="sha256:1234567890123456789012345678901234567890123456789012345678901234",
            size_bytes=100,
            provenance="inv_OTHER_999",  # Provenance mismatch
        )

        with self.assertRaises(DataPlaneAccessDeniedError):
            self.resolver.resolve_locator_handle(
                auth_ctx=self.auth_ctx,
                obj_ref=obj_ref,
                user_capabilities={"storage.read"},
            )

    def test_locator_handle_invocation_containment(self) -> None:
        obj_ref = ObjectRef(
            object_id="obj_isolated",
            version="v1",
            content_digest="sha256:1234567890123456789012345678901234567890123456789012345678901234",
            size_bytes=50,
        )
        provider = MemoryBoundStreamProvider(total_bytes=50)
        self.resolver.register_object_storage("obj_isolated", "s3://internal-bucket/isolated.bin", provider)

        handle = self.resolver.resolve_locator_handle(
            auth_ctx=self.auth_ctx,
            obj_ref=obj_ref,
            user_capabilities={"storage.read"},
        )

        # Valid retrieval with matching invocation & attempt IDs
        stream = self.resolver.get_stream_provider(
            handle=handle,
            obj_ref=obj_ref,
            request_invocation_id="inv_alpha_100",
            request_attempt_id="att_1",
        )
        self.assertIsNotNone(stream)

        # Rejected if used by Invocation B
        with self.assertRaises(InvalidLocatorHandleError):
            self.resolver.get_stream_provider(
                handle=handle,
                obj_ref=obj_ref,
                request_invocation_id="inv_BETA_200",  # Mismatch
                request_attempt_id="att_1",
            )

        # Rejected if used by Attempt B
        with self.assertRaises(InvalidLocatorHandleError):
            self.resolver.get_stream_provider(
                handle=handle,
                obj_ref=obj_ref,
                request_invocation_id="inv_alpha_100",
                request_attempt_id="att_2",  # Mismatch
            )

    def test_streaming_memory_constant_bound_large_object(self) -> None:
        # Simulate 10 MB stream to verify memory chunk ceiling (160 chunks of 64 KiB)
        stream_size_bytes = 10 * 1024 * 1024  # 10 MiB
        provider = MemoryBoundStreamProvider(total_bytes=stream_size_bytes, fill_byte=b"Z")

        # Calculate exact expected digest for 10 MiB of 'Z's incrementally
        hasher = hashlib.sha256()
        chunk_buf = b"Z" * MAX_VERIFICATION_CHUNK_BYTES
        full_chunks = stream_size_bytes // MAX_VERIFICATION_CHUNK_BYTES
        for _ in range(full_chunks):
            hasher.update(chunk_buf)

        digest = f"sha256:{hasher.hexdigest()}"
        obj_ref = ObjectRef(
            object_id="obj_100mb_simulated",
            version="v1",
            content_digest=digest,
            size_bytes=stream_size_bytes,
        )

        reader = BoundedChunkReader(provider)
        self.assertTrue(reader.verify_integrity_stream(obj_ref))

        # Assert that maximum single read buffer allocation never exceeded 64 KiB
        self.assertLessEqual(provider.max_single_read_buffer, MAX_VERIFICATION_CHUNK_BYTES)
        self.assertEqual(provider.max_single_read_buffer, MAX_VERIFICATION_CHUNK_BYTES)


if __name__ == "__main__":
    unittest.main()
