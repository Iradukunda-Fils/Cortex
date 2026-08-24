"""
Cortex External Adapter Contract & Context Specification (v1.5.0-FROZEN)

Canonical Namespace: https://schemas.cortex.internal/v1
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Final, Optional

MAX_INLINE_PAYLOAD_BYTES: Final[int] = 65_536  # 64 KiB Limit
MAX_INLINE_EVIDENCE_BYTES: Final[int] = 4_096  # 4 KiB Limit


class PayloadSizeExceededError(ValueError):
    """Raised when inline effect or evidence payload exceeds protocol limits."""

    pass


class EffectClassification(Enum):
    """Normative side-effect classification for external resource operations."""

    READ_ONLY = "READ_ONLY"
    IDEMPOTENT_WRITE = "IDEMPOTENT_WRITE"
    NON_IDEMPOTENT_WRITE = "NON_IDEMPOTENT_WRITE"
    TRANSACTIONAL = "TRANSACTIONAL"


class ExecutionStatus(Enum):
    """Normative adapter effect execution outcome status."""

    EFFECT_CONFIRMED = "EFFECT_CONFIRMED"
    EFFECT_NOT_APPLIED = "EFFECT_NOT_APPLIED"
    EFFECT_PARTIALLY_APPLIED = "EFFECT_PARTIALLY_APPLIED"
    UNKNOWN_EFFECT = "UNKNOWN_EFFECT"


@dataclass(frozen=True)
class CorrelationLineage:
    """Ephemeral lineage tracking across Gateway, Execution, and Adapter planes."""

    invocation_id: str
    execution_attempt_id: str
    adapter_request_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "invocation_id": self.invocation_id,
            "execution_attempt_id": self.execution_attempt_id,
            "adapter_request_id": self.adapter_request_id,
        }


@dataclass(frozen=True)
class EffectPayload:
    """Bounded control plane payload envelope."""

    data: bytes
    is_reference: bool = False

    def __post_init__(self) -> None:
        if not self.is_reference and len(self.data) > MAX_INLINE_PAYLOAD_BYTES:
            raise PayloadSizeExceededError(
                f"Inline effect payload {len(self.data)} bytes exceeds limit {MAX_INLINE_PAYLOAD_BYTES} bytes"
            )


@dataclass(frozen=True)
class EvidencePayload:
    """Bounded evidence witness payload envelope."""

    data: bytes
    is_reference: bool = False

    def __post_init__(self) -> None:
        if not self.is_reference and len(self.data) > MAX_INLINE_EVIDENCE_BYTES:
            raise PayloadSizeExceededError(
                f"Inline evidence payload {len(self.data)} bytes exceeds limit {MAX_INLINE_EVIDENCE_BYTES} bytes"
            )


@dataclass(frozen=True)
class AdapterExecutionContext:
    """
    Authoritative ephemeral execution context injected by Gateway TCB.
    Schema URI: https://schemas.cortex.internal/v1/adapter-execution-context.json
    """

    invocation_id: str
    execution_attempt_id: str
    adapter_request_id: str
    idempotency_key: str
    lease_epoch: int
    resource_id: str
    operation_type: str
    contract_version: str = "v1"
    schema_uri: str = "https://schemas.cortex.internal/v1/adapter-execution-context.json"

    @property
    def lineage(self) -> CorrelationLineage:
        return CorrelationLineage(
            invocation_id=self.invocation_id,
            execution_attempt_id=self.execution_attempt_id,
            adapter_request_id=self.adapter_request_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "execution_attempt_id": self.execution_attempt_id,
            "adapter_request_id": self.adapter_request_id,
            "idempotency_key": self.idempotency_key,
            "lease_epoch": self.lease_epoch,
            "resource_id": self.resource_id,
            "operation_type": self.operation_type,
            "contract_version": self.contract_version,
            "schema_uri": self.schema_uri,
        }


@dataclass(frozen=True)
class AdapterOutcome:
    """Result returned by a ResourceContract effect execution."""

    status: ExecutionStatus
    evidence: Optional[EvidencePayload] = None
    error_message: Optional[str] = None


class ResourceContract(ABC):
    """
    Normative ResourceContract trait for External System Adapters.
    Adapters NEVER derive idempotency keys or evaluate authorization policies.
    """

    @property
    @abstractmethod
    def resource_type(self) -> str:
        """Returns provider resource type identifier (e.g. 'adapter.s3.v1')."""
        pass

    @property
    @abstractmethod
    def effect_classification(self) -> EffectClassification:
        """Returns normative effect classification."""
        pass

    @abstractmethod
    def execute_effect(
        self,
        ctx: AdapterExecutionContext,
        payload: EffectPayload,
    ) -> AdapterOutcome:
        """Executes adapter effect under Gateway-injected execution context."""
        pass
