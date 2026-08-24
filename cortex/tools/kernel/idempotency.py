"""
Cortex Authoritative Gateway HMAC Idempotency Engine & LeaseEpoch Fencing (v1.5.0-FROZEN)

Canonical Namespace: https://schemas.cortex.internal/v1
"""

from __future__ import annotations

import hmac
import hashlib
from dataclasses import dataclass
from typing import Dict

from cortex.tools.kernel.adapter_contract import AdapterExecutionContext


class IdempotencyError(ValueError):
    """Base exception for Gateway idempotency errors."""

    pass


class MissingDomainSecretError(IdempotencyError):
    """Raised when no domain secret key is found for a requested secret version."""

    pass


class StaleLeaseEpochError(IdempotencyError):
    """Raised when an execution attempt presents a stale or non-advancing lease epoch."""

    pass


class DuplicateAttemptIdError(IdempotencyError):
    """Raised when an attempt attempts to reuse a predecessor's execution attempt ID."""

    pass


@dataclass(frozen=True)
class CanonicalOperation:
    """Canonical representation of an operation for HMAC idempotency derivation."""

    invocation_id: str
    resource_id: str
    operation_type: str
    canonical_payload: bytes
    contract_version: str = "v1"

    def serialize_canonical_bytes(self) -> bytes:
        """Constructs InvocationID || CanonicalPayload || ResourceID || OperationType || ContractVersion."""
        return (
            self.invocation_id.encode("utf-8") + b"||" +
            self.canonical_payload + b"||" +
            self.resource_id.encode("utf-8") + b"||" +
            self.operation_type.encode("utf-8") + b"||" +
            self.contract_version.encode("utf-8")
        )


class GatewayIdempotencyEngine:
    """
    Authoritative Gateway HMAC-SHA256 Idempotency Engine (TCB scope).
    
    The Gateway turns:
      Invocation + Canonical Operation + Domain Secret Version -> IdempotencyKey
      
    Adapters and workers MUST NOT derive or mutate idempotency keys.
    """

    def __init__(self, secrets_vault: Dict[str, bytes]) -> None:
        """
        secrets_vault maps secret_version (e.g. 'v1', 'v2') -> raw secret bytes.
        """
        self._secrets_vault: Dict[str, bytes] = dict(secrets_vault)
        # Track history of execution_attempt_id per invocation_id to enforce attempt uniqueness
        self._seen_attempt_ids: Dict[str, set[str]] = {}
        # Track active lease epoch per invocation_id to enforce epoch monotonicity
        self._active_epochs: Dict[str, int] = {}

    def register_secret_version(self, version: str, secret_bytes: bytes) -> None:
        """Registers or rotates a domain secret version in the Gateway vault."""
        self._secrets_vault[version] = secret_bytes

    def derive_idempotency_key(
        self,
        op: CanonicalOperation,
        secret_version: str = "v1",
    ) -> str:
        """
        Derives deterministic HMAC-SHA256 idempotency key:
        HMAC-SHA256(S_domain_secret, InvocationID || CanonicalPayload || ResourceID || OperationType || ContractVersion)
        """
        secret = self._secrets_vault.get(secret_version)
        if not secret:
            raise MissingDomainSecretError(f"No domain secret found for version {secret_version!r}")

        message = op.serialize_canonical_bytes()
        digest = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return f"hmac-sha256:{secret_version}:{digest}"

    def validate_lease_epoch_and_attempt(
        self,
        invocation_id: str,
        execution_attempt_id: str,
        presented_epoch: int,
    ) -> None:
        """
        Enforces LeaseEpoch Fencing Invariants:
        1. Epoch_n+1 > Epoch_n
        2. ExecutionAttemptID must be unique per invocation (cannot reuse predecessor attempt ID).
        """
        current_epoch = self._active_epochs.get(invocation_id, 0)

        if presented_epoch <= current_epoch:
            raise StaleLeaseEpochError(
                f"Presented lease epoch {presented_epoch} <= active epoch {current_epoch} for invocation {invocation_id}"
            )

        seen_attempts = self._seen_attempt_ids.setdefault(invocation_id, set())
        if execution_attempt_id in seen_attempts:
            raise DuplicateAttemptIdError(
                f"Execution attempt ID {execution_attempt_id!r} already used for invocation {invocation_id}"
            )

        # Update active epoch and record attempt ID
        self._active_epochs[invocation_id] = presented_epoch
        seen_attempts.add(execution_attempt_id)

    def create_adapter_context(
        self,
        op: CanonicalOperation,
        execution_attempt_id: str,
        adapter_request_id: str,
        lease_epoch: int,
        secret_version: str = "v1",
    ) -> AdapterExecutionContext:
        """
        Authoritative entry point: validates lease epoch, derives HMAC idempotency key,
        and constructs immutable AdapterExecutionContext for adapter execution.
        """
        # Validate fencing invariants first
        self.validate_lease_epoch_and_attempt(
            invocation_id=op.invocation_id,
            execution_attempt_id=execution_attempt_id,
            presented_epoch=lease_epoch,
        )

        # Derive key using persisted secret_version
        idempotency_key = self.derive_idempotency_key(op=op, secret_version=secret_version)

        return AdapterExecutionContext(
            invocation_id=op.invocation_id,
            execution_attempt_id=execution_attempt_id,
            adapter_request_id=adapter_request_id,
            idempotency_key=idempotency_key,
            lease_epoch=lease_epoch,
            resource_id=op.resource_id,
            operation_type=op.operation_type,
            contract_version=op.contract_version,
        )
