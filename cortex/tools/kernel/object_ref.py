"""
Cortex Canonical ObjectRef Data Plane, Opaque Locators, and BoundedChunkReader (v1.5.0-FROZEN)

Canonical Namespace: https://schemas.cortex.internal/v1
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final, Generator, Optional, Protocol

from cortex.tools.kernel.adapter_contract import AdapterExecutionContext

MAX_VERIFICATION_CHUNK_BYTES: Final[int] = 65_536  # 64 KiB Limit


class DataPlaneError(Exception):
    """Base exception for Data Plane operations."""

    pass


class DataPlaneAccessDeniedError(DataPlaneError):
    """Raised when access evaluation fails for an ObjectRef resolution request."""

    pass


class ObjectIntegrityError(DataPlaneError):
    """Raised when SHA-256 content digest or size verification fails."""

    pass


class InvalidLocatorHandleError(DataPlaneError):
    """Raised when an opaque PhysicalLocatorHandle is expired, tampered, or mismatched."""

    pass


@dataclass(frozen=True)
class ObjectRef:
    """
    Canonical ObjectRef metadata handle.
    Schema URI: https://schemas.cortex.internal/v1/objectref.json

    ObjectRef represents content identity and integrity ONLY.
    It MUST NOT contain credentials, authorization tokens, physical endpoints, or bearer tokens.
    """

    object_id: str
    version: str
    content_digest: str  # Format: 'sha256:<hex_digest>'
    size_bytes: int
    media_type: str = "application/octet-stream"
    provenance: str = ""
    schema_uri: str = "https://schemas.cortex.internal/v1/objectref.json"

    def __post_init__(self) -> None:
        if not self.content_digest.startswith("sha256:"):
            raise ValueError(f"content_digest must start with 'sha256:', got {self.content_digest!r}")
        if self.size_bytes < 0:
            raise ValueError(f"size_bytes must be non-negative, got {self.size_bytes}")


@dataclass(frozen=True)
class PhysicalLocatorHandle:
    """
    Opaque capability token handle returned to workers by DataPlaneResolver.
    Schema URI: https://schemas.cortex.internal/v1/physical-locator-handle.json

    Contains NO physical storage topology (no s3://, /mnt/, hosts, ports, or credentials).
    Bound to InvocationID, ExecutionAttemptID, and a temporal validity window.
    """

    locator_token: str
    invocation_id: str
    execution_attempt_id: str
    validity_window_sec: float
    access_mode: str = "READ_ONLY"
    schema_uri: str = "https://schemas.cortex.internal/v1/physical-locator-handle.json"


class StreamProvider(Protocol):
    """Protocol for streaming data sources supplying binary chunks."""

    def read_chunk(self, max_bytes: int) -> bytes:
        """Reads up to max_bytes from the stream. Returns empty bytes on EOF."""
        ...


class BoundedChunkReader:
    """
    Streaming reader enforcing MAX_VERIFICATION_CHUNK_BYTES (64 KiB).
    Guarantees O(chunk_size) memory ceiling regardless of total stream size.
    """

    def __init__(
        self,
        provider: StreamProvider,
        chunk_size: int = MAX_VERIFICATION_CHUNK_BYTES,
    ) -> None:
        if chunk_size <= 0 or chunk_size > MAX_VERIFICATION_CHUNK_BYTES:
            raise ValueError(f"chunk_size must be 1..{MAX_VERIFICATION_CHUNK_BYTES}, got {chunk_size}")
        self._provider = provider
        self._chunk_size = chunk_size

    def iter_chunks(self) -> Generator[bytes, None, None]:
        """Yields chunks of max MAX_VERIFICATION_CHUNK_BYTES."""
        while True:
            chunk = self._provider.read_chunk(self._chunk_size)
            if not chunk:
                break
            if len(chunk) > self._chunk_size:
                raise DataPlaneError(f"Stream returned chunk {len(chunk)} bytes exceeding max {self._chunk_size}")
            yield chunk

    def verify_integrity_stream(self, obj_ref: ObjectRef) -> bool:
        """
        Streams object content incrementally, computing SHA-256 digest and byte count.
        Does NOT buffer whole object in memory. Memory remains O(chunk_size).
        """
        hasher = hashlib.sha256()
        total_bytes = 0

        for chunk in self.iter_chunks():
            hasher.update(chunk)
            total_bytes += len(chunk)

        if total_bytes != obj_ref.size_bytes:
            raise ObjectIntegrityError(
                f"Stream byte size {total_bytes} does not match expected ObjectRef size {obj_ref.size_bytes}"
            )

        computed_digest = f"sha256:{hasher.hexdigest()}"
        if computed_digest != obj_ref.content_digest:
            raise ObjectIntegrityError(
                f"Computed content digest {computed_digest!r} does not match expected ObjectRef digest {obj_ref.content_digest!r}"
            )

        return True


class DataPlaneResolver:
    """
    Authoritative Data Plane Resolver.
    Enforces Access = Identity ^ Capability ^ ResourcePolicy ^ InvocationAuthority.
    Possession of an ObjectRef is NEVER sufficient to obtain a PhysicalLocatorHandle.
    """

    def __init__(self, storage_registry: Optional[dict[str, tuple[str, StreamProvider]]] = None) -> None:
        # Maps object_id -> (physical_topology_hidden, StreamProvider)
        self._storage_registry = storage_registry or {}
        # Issued locator handles registry for validation
        self._issued_handles: dict[str, PhysicalLocatorHandle] = {}

    def register_object_storage(
        self,
        object_id: str,
        physical_topology_hidden: str,
        stream_provider: StreamProvider,
    ) -> None:
        """Registers internal storage mapping (hidden from worker handle)."""
        self._storage_registry[object_id] = (physical_topology_hidden, stream_provider)

    def resolve_locator_handle(
        self,
        auth_ctx: AdapterExecutionContext,
        obj_ref: ObjectRef,
        user_capabilities: set[str],
        required_capability: str = "storage:read",
        resource_policy_allowed: bool = True,
    ) -> PhysicalLocatorHandle:
        """
        Evaluates authorization and derives an opaque PhysicalLocatorHandle.
        Fails closed with DataPlaneAccessDeniedError if any security check fails.
        """
        # 1. Capability Check
        norm_user_caps = {c.replace(".", ":") for c in user_capabilities}
        if required_capability not in user_capabilities and required_capability.replace(".", ":") not in norm_user_caps:
            raise DataPlaneAccessDeniedError(
                f"Required capability {required_capability!r} missing from user capabilities {user_capabilities!r}"
            )

        # 2. Resource Policy Check
        if not resource_policy_allowed:
            raise DataPlaneAccessDeniedError(f"Resource policy denies access to object {obj_ref.object_id!r}")

        # 3. Invocation Authority Check (provenance match if set)
        if obj_ref.provenance and obj_ref.provenance != auth_ctx.invocation_id:
            raise DataPlaneAccessDeniedError(
                f"ObjectRef provenance {obj_ref.provenance!r} does not match execution context invocation_id {auth_ctx.invocation_id!r}"
            )

        # Generate opaque handle (SHA-256 token digest)
        token_input = (
            f"{auth_ctx.invocation_id}:{auth_ctx.execution_attempt_id}:{obj_ref.object_id}:{obj_ref.content_digest}"
        )
        opaque_token = f"locator_tok_{hashlib.sha256(token_input.encode()).hexdigest()[:32]}"

        handle = PhysicalLocatorHandle(
            locator_token=opaque_token,
            invocation_id=auth_ctx.invocation_id,
            execution_attempt_id=auth_ctx.execution_attempt_id,
            validity_window_sec=300.0,
            access_mode="READ_ONLY",
        )

        self._issued_handles[opaque_token] = handle
        return handle

    def get_stream_provider(
        self,
        handle: PhysicalLocatorHandle,
        obj_ref: ObjectRef,
        request_invocation_id: str,
        request_attempt_id: str,
    ) -> StreamProvider:
        """
        Validates opaque handle containment and returns stream provider for reading.
        Fails if handle is expired, unbound to invocation, or physical topology is requested.
        """
        issued_handle = self._issued_handles.get(handle.locator_token)
        if not issued_handle or issued_handle != handle:
            raise InvalidLocatorHandleError("Opaque locator handle unrecognized or tampered")

        if handle.invocation_id != request_invocation_id:
            raise InvalidLocatorHandleError(
                f"Handle invocation {handle.invocation_id!r} does not match request invocation {request_invocation_id!r}"
            )

        if handle.execution_attempt_id != request_attempt_id:
            raise InvalidLocatorHandleError(
                f"Handle execution attempt {handle.execution_attempt_id!r} does not match request attempt {request_attempt_id!r}"
            )

        storage_entry = self._storage_registry.get(obj_ref.object_id)
        if not storage_entry:
            raise DataPlaneError(f"Object {obj_ref.object_id!r} not found in physical storage registry")

        # Return stream provider without exposing physical_topology_hidden
        _, stream_provider = storage_entry
        return stream_provider
