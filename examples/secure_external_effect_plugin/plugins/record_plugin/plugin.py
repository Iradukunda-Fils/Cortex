"""
Record Service Plugin Implementation.

Demonstrates Gateway-mediated external record operations (lookup & store).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cortex import BaseEvent, BasePlugin, CommandIssuedEvent, IntentEvent, PluginManifest
from cortex.tools.kernel.effect_gateway import EffectOutcome, EffectRequest

if TYPE_CHECKING:
    from cortex.tools.kernel.effect_runtime import EffectExecutionPipeline


@dataclass(frozen=True)
class WorkerContext:
    """Sandboxed worker execution identity — provided by the runtime, not the plugin."""

    invocation_id: str
    resource_id: str
    lease_epoch: int
    worker_generation: int


class RecordServicePlugin(BasePlugin):
    """
    Reference plugin demonstrating Gateway-mediated external record operations.

    This plugin:
      - Looks up records via 'api:records' / 'lookup' capability
      - Stores records via 'api:records' / 'store' capability
      - NEVER constructs idempotency keys (Gateway does this)
      - NEVER receives credentials (CredentialBroker injects them)
      - NEVER bypasses capability negotiation
    """

    def __init__(
        self,
        manifest: PluginManifest,
        pipeline: EffectExecutionPipeline | None = None,
        worker_ctx: WorkerContext | None = None,
    ) -> None:
        super().__init__(manifest)
        self.pipeline = pipeline
        self.worker_ctx = worker_ctx

    def on_event(self, event: BaseEvent) -> None:
        """Handles incoming IntentEvent by looking up a record via the Gateway."""
        if isinstance(event, IntentEvent) and self.pipeline and self.worker_ctx:
            outcome = self.lookup_record(
                pipeline=self.pipeline,
                ctx=self.worker_ctx,
                record_id=str(event.parameters.get("record_id", "default")),
            )

            if self.context and self.context.publish_func and outcome.evidence:
                cmd_event = CommandIssuedEvent(
                    workflow_id=event.workflow_id,
                    plan_id="plan_lookup_01",
                    action="record_lookup",
                    parameters={"result": outcome.evidence.data.decode("utf-8")},
                    causation_id=event.event_id,
                )
                self.context.publish_func(cmd_event)

    def lookup_record(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: WorkerContext,
        record_id: str = "rec_001",
        execution_attempt_id: str = "att_lookup_01",
    ) -> EffectOutcome:
        """Submits an unprivileged EffectRequest to look up a record."""
        arguments = json.dumps({
            "tool_name": "lookup_record",
            "arguments": {"record_id": record_id},
        }).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="api:records",
            operation="lookup",
            arguments=arguments,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)

    def store_record(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: WorkerContext,
        key: str,
        value: str,
        execution_attempt_id: str = "att_store_01",
    ) -> EffectOutcome:
        """Submits an unprivileged EffectRequest to store a record."""
        arguments = json.dumps({
            "tool_name": "store_record",
            "arguments": {"key": key, "value": value},
        }).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="api:records",
            operation="store",
            arguments=arguments,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)

    def request_unauthorized_operation(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: WorkerContext,
        execution_attempt_id: str = "att_unauth_01",
    ) -> EffectOutcome:
        """Intentionally requests an UNAUTHORIZED capability for security testing."""
        arguments = json.dumps({
            "tool_name": "delete_all",
            "arguments": {},
        }).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="api:admin",
            operation="delete_all",
            arguments=arguments,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)

    def request_with_stale_lease(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: WorkerContext,
        stale_epoch: int = 1,
        execution_attempt_id: str = "att_stale_01",
    ) -> EffectOutcome:
        """Intentionally uses a STALE lease epoch for fencing testing."""
        arguments = json.dumps({
            "tool_name": "lookup_record",
            "arguments": {"record_id": "rec_stale"},
        }).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="api:records",
            operation="lookup",
            arguments=arguments,
            resource_id=ctx.resource_id,
            lease_epoch=stale_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)

    def request_failed_service(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: WorkerContext,
        execution_attempt_id: str = "att_fail_01",
    ) -> EffectOutcome:
        """Requests an operation that triggers an external service error."""
        arguments = json.dumps({
            "tool_name": "fail",
            "arguments": {},
        }).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="api:records",
            operation="lookup",
            arguments=arguments,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)
