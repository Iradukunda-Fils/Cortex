"""
Cortex External Effect Gateway & Authorization Gate (Gate B)

Freezes the security boundary between sandboxed AI workers and external systems.
The worker emits an unprivileged EffectRequest; the Gateway resolves authorization,
derives authoritative effect classification, computes the HMAC idempotency key,
and constructs an immutable AdapterExecutionContext for adapter execution.

Governing Principle: Adapter Executes; Authority Decides.

Security Invariants:
    S1. Worker NEVER supplies effect classification (Gateway resolves authoritatively).
    S2. Worker NEVER supplies idempotency key (Gateway derives via HMAC-SHA256).
    S3. Worker NEVER supplies credentials (Credential Broker injects at adapter boundary).
    S4. Effect execution requires valid reservation, capability grant, and lease epoch.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass
from typing import Optional, Protocol, Tuple

from cortex.tools.kernel.adapter_contract import (
    AdapterExecutionContext,
    EffectClassification,
    EvidencePayload,
    ExecutionStatus,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CapabilityDeniedError(Exception):
    """Raised when the worker lacks authority for the requested capability."""

    pass


class EffectFencingError(Exception):
    """Raised when lease epoch or worker generation validation fails at effect boundary."""

    pass


class UnregisteredOperationError(Exception):
    """Raised when capability/operation pair is not registered in the Gateway effect registry."""

    pass


# ---------------------------------------------------------------------------
# Worker → Gateway: Unprivileged Effect Request
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EffectRequest:
    """
    Unprivileged Worker → Gateway effect request.

    The worker supplies ONLY invocation intent, routing metadata, and raw arguments.
    The worker NEVER supplies:
      - Effect classification (authoritatively resolved by Gateway)
      - Idempotency key (authoritatively derived by Gateway)
      - Credentials / tokens (injected by Credential Broker at adapter boundary)
    """

    invocation_id: str
    capability: str  # e.g. "mcp:echo", "storage:write"
    operation: str  # e.g. "echo", "put_object"
    arguments: bytes  # Serialized operation payload
    resource_id: str  # Target resource identifier
    lease_epoch: int  # Worker's current lease epoch
    worker_generation: int  # Worker's incarnation generation
    contract_version: str = "v1"


# ---------------------------------------------------------------------------
# Gateway → Worker: Effect Outcome
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EffectOutcome:
    """
    Gateway → Worker effect response.

    Contains execution status and bounded evidence. Internal secrets,
    raw provider details, and adapter state are stripped before delivery.
    """

    invocation_id: str
    execution_attempt_id: str
    status: ExecutionStatus
    evidence: Optional[EvidencePayload] = None
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Protocol Interfaces (Dependency Inversion)
# ---------------------------------------------------------------------------


class EffectAuthorityInterface(Protocol):
    """Protocol for validating worker reservation state at effect boundary."""

    def validate_effect_reservation(
        self,
        worker_generation: int,
        lease_epoch: int,
    ) -> bool:
        """Returns True if the reservation is valid for the given generation and epoch."""
        ...


class EffectCapabilityRegistryInterface(Protocol):
    """Protocol for resolving capability permissions and authoritative effect classifications."""

    def is_capability_granted(
        self,
        capability: str,
        operation: str,
    ) -> bool:
        """Returns True if the capability/operation pair is granted to the active plugin."""
        ...

    def resolve_effect_classification(
        self,
        capability: str,
        operation: str,
    ) -> EffectClassification:
        """
        Returns the authoritative effect classification for the given capability/operation.
        The worker MUST NOT be trusted to provide this classification.
        """
        ...


# ---------------------------------------------------------------------------
# Gateway Authorization Gate (Gate B — Policy Enforcement Point)
# ---------------------------------------------------------------------------


class GatewayAuthorizationGate:
    """
    Policy Enforcement Point (PEP) for External Side-Effects (Gate B).

    Governing Principle: Adapter Executes; Authority Decides.

    Authorization Sequence:
        1. Validate reservation (lease epoch + worker generation)
        2. Validate capability grant
        3. Resolve authoritative effect classification
        4. Derive deterministic HMAC-SHA256 idempotency key
        5. Construct immutable AdapterExecutionContext

    The Gate NEVER:
        - Trusts worker-supplied effect classification
        - Passes credentials to the worker
        - Allows adapter execution without completing all 5 steps
    """

    def __init__(
        self,
        effect_authority: EffectAuthorityInterface,
        capability_registry: EffectCapabilityRegistryInterface,
        domain_secret: bytes,
        domain_separator: str = "cortex.v1.effect_idempotency",
    ) -> None:
        if len(domain_secret) < 16:
            raise ValueError("Domain secret must be at least 16 bytes for HMAC-SHA256 security.")
        self._authority = effect_authority
        self._registry = capability_registry
        self._domain_secret = domain_secret
        self._domain_separator = domain_separator

    def derive_idempotency_key(self, request: EffectRequest) -> str:
        """
        Derives deterministic HMAC-SHA256 idempotency key.

        K = HMAC-SHA256(
            S_domain,
            DomainSeparator || InvocationID || Operation || SHA256(Payload)
            || ResourceID || LeaseEpoch || ContractVersion
        )

        The execution_attempt_id is intentionally EXCLUDED from key derivation.
        Retries of the same logical operation MUST produce the same key.
        The attempt_id is attached for tracing, not for effect identity.
        """
        payload_hash = hashlib.sha256(request.arguments).hexdigest()
        canonical_message = (
            f"{self._domain_separator}||"
            f"{request.invocation_id}||"
            f"{request.operation}||"
            f"{payload_hash}||"
            f"{request.resource_id}||"
            f"{request.lease_epoch}||"
            f"{request.contract_version}"
        ).encode("utf-8")

        digest = hmac.new(self._domain_secret, canonical_message, hashlib.sha256).hexdigest()
        return f"hmac-sha256:v1:{digest}"

    def authorize_and_prepare(
        self,
        request: EffectRequest,
        execution_attempt_id: str,
    ) -> Tuple[AdapterExecutionContext, EffectClassification]:
        """
        Evaluates policy, fencing, and classification.
        Returns a pre-authorized (AdapterExecutionContext, EffectClassification) tuple.

        Raises:
            EffectFencingError: If reservation/lease validation fails.
            CapabilityDeniedError: If capability is not granted.
        """
        # Step 1: Lease Epoch & Worker Generation Fencing
        if not self._authority.validate_effect_reservation(request.worker_generation, request.lease_epoch):
            raise EffectFencingError(
                f"Effect reservation invalid: generation={request.worker_generation}, "
                f"epoch={request.lease_epoch}. Request rejected."
            )

        # Step 2: Capability Permission Grant Check
        if not self._registry.is_capability_granted(request.capability, request.operation):
            raise CapabilityDeniedError(
                f"Capability '{request.capability}' operation '{request.operation}' "
                f"is not granted. Effect request rejected."
            )

        # Step 3: Resolve Authoritative Effect Classification (Gateway-Driven)
        classification = self._registry.resolve_effect_classification(request.capability, request.operation)

        # Step 4: Derive Deterministic Idempotency Key
        idempotency_key = self.derive_idempotency_key(request)

        # Step 5: Construct Pre-Authorized Adapter Context
        adapter_request_id = f"areq_{uuid.uuid4().hex[:16]}"

        ctx = AdapterExecutionContext(
            invocation_id=request.invocation_id,
            execution_attempt_id=execution_attempt_id,
            adapter_request_id=adapter_request_id,
            idempotency_key=idempotency_key,
            lease_epoch=request.lease_epoch,
            resource_id=request.resource_id,
            operation_type=request.operation,
            contract_version=request.contract_version,
        )

        return ctx, classification
