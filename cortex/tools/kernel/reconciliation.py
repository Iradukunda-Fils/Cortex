"""
Cortex Effect Reconciliation Engine & Layered Quarantine Machine (v1.5.0-FROZEN)

Canonical Namespace: https://schemas.cortex.internal/v1
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Protocol

from cortex.tools.kernel.adapter_contract import (
    AdapterExecutionContext,
    AdapterOutcome,
    EffectClassification,
    ExecutionStatus,
)


class ReconciliationError(Exception):
    """Base exception for reconciliation operations."""

    pass


class IndeterminateEffectError(ReconciliationError):
    """Raised when a non-idempotent operation enters INDETERMINATE state."""

    pass


class QuarantinedResourceError(ReconciliationError):
    """Raised when an operation targets a quarantined resource scope."""

    pass


class InvocationState(Enum):
    """Normative state machine states for invocation attempts."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    NOT_APPLIED = "NOT_APPLIED"
    INDETERMINATE = "INDETERMINATE"
    QUARANTINED = "QUARANTINED"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class QuarantineRecord:
    """
    Metadata record created when a non-idempotent operation enters INDETERMINATE state.
    Schema URI: https://schemas.cortex.internal/v1/quarantine-record.json
    """

    quarantine_id: str
    invocation_id: str
    execution_attempt_id: str
    idempotency_key: str
    resource_id: str
    reason: str
    schema_uri: str = "https://schemas.cortex.internal/v1/quarantine-record.json"


class WitnessProbe(Protocol):
    """Protocol for external witness/status probes."""

    def probe_status(self, ctx: AdapterExecutionContext) -> ExecutionStatus:
        ...


class EffectReconciliationEngine:
    """
    3-Layer Effect Reconciliation Engine (v1.5.0-FROZEN):

    1. Layer 1: Idempotency Querying
    2. Layer 2: External Witness Probing
    3. Layer 3: Indeterminate Quarantine Isolation

    Invariant:
    UnknownEffect ^ NonIdempotent ==> State = INDETERMINATE ==> QuarantineScope <= StateDomain
    """

    def __init__(self) -> None:
        self._quarantined_resources: Dict[str, QuarantineRecord] = {}
        self._invocation_states: Dict[str, InvocationState] = {}

    def is_resource_quarantined(self, resource_id: str) -> bool:
        """Returns True if the given resource scope is quarantined."""
        return resource_id in self._quarantined_resources

    def get_quarantine_record(self, resource_id: str) -> Optional[QuarantineRecord]:
        return self._quarantined_resources.get(resource_id)

    def reconcile_effect(
        self,
        ctx: AdapterExecutionContext,
        classification: EffectClassification,
        outcome: AdapterOutcome,
        witness_probe: Optional[WitnessProbe] = None,
    ) -> InvocationState:
        """
        Executes 3-layer reconciliation flow for an adapter execution attempt.
        """
        # Guard against executing on already quarantined sub-resources
        if self.is_resource_quarantined(ctx.resource_id):
            raise QuarantinedResourceError(
                f"Resource {ctx.resource_id!r} is currently quarantined under quarantine ID {self._quarantined_resources[ctx.resource_id].quarantine_id!r}"
            )

        # Layer 1: Known deterministic outcome
        if outcome.status == ExecutionStatus.EFFECT_CONFIRMED:
            self._invocation_states[ctx.invocation_id] = InvocationState.CONFIRMED
            return InvocationState.CONFIRMED

        if outcome.status == ExecutionStatus.EFFECT_NOT_APPLIED:
            self._invocation_states[ctx.invocation_id] = InvocationState.NOT_APPLIED
            return InvocationState.NOT_APPLIED

        # Read-only or idempotent writes with unknown status can safely be marked NOT_APPLIED for retry
        if classification in (EffectClassification.READ_ONLY, EffectClassification.IDEMPOTENT_WRITE):
            if outcome.status == ExecutionStatus.UNKNOWN_EFFECT:
                self._invocation_states[ctx.invocation_id] = InvocationState.NOT_APPLIED
                return InvocationState.NOT_APPLIED

        # Layer 2: External Witness Probing for non-idempotent operations
        if outcome.status in (ExecutionStatus.UNKNOWN_EFFECT, ExecutionStatus.EFFECT_PARTIALLY_APPLIED):
            if witness_probe is not None:
                probed_status = witness_probe.probe_status(ctx)
                if probed_status == ExecutionStatus.EFFECT_CONFIRMED:
                    self._invocation_states[ctx.invocation_id] = InvocationState.CONFIRMED
                    return InvocationState.CONFIRMED
                elif probed_status == ExecutionStatus.EFFECT_NOT_APPLIED:
                    self._invocation_states[ctx.invocation_id] = InvocationState.NOT_APPLIED
                    return InvocationState.NOT_APPLIED

        # Layer 3: Indeterminate Quarantine Isolation for Non-Idempotent Operations
        self._invocation_states[ctx.invocation_id] = InvocationState.INDETERMINATE

        quarantine_record = QuarantineRecord(
            quarantine_id=f"quar_{ctx.invocation_id}_{ctx.execution_attempt_id}",
            invocation_id=ctx.invocation_id,
            execution_attempt_id=ctx.execution_attempt_id,
            idempotency_key=ctx.idempotency_key,
            resource_id=ctx.resource_id,
            reason=f"Ambiguous execution outcome {outcome.status.value} for non-idempotent operation {ctx.operation_type!r}",
        )

        self._quarantined_resources[ctx.resource_id] = quarantine_record
        raise IndeterminateEffectError(
            f"Invocation {ctx.invocation_id} entered INDETERMINATE state. Resource {ctx.resource_id!r} quarantined."
        )

    def lift_quarantine(self, resource_id: str, operator_reason: str) -> None:
        """Allows manual/operator intervention to resolve an INDETERMINATE quarantine scope."""
        if resource_id in self._quarantined_resources:
            del self._quarantined_resources[resource_id]
