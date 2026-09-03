"""
Tasks for AuditPlugin.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from cortex import BaseEvent, BasePlugin, PlanGeneratedEvent, PluginManifest, VerificationResultEvent
from cortex.tools.kernel.effect_gateway import EffectOutcome, EffectRequest

if TYPE_CHECKING:
    from cortex.tools.kernel.effect_runtime import EffectExecutionPipeline

    from ..ingestion_plugin.tasks import ExecutionContext


class AuditPlugin(BasePlugin):
    """Plugin responsible for audit log verification."""

    def __init__(
        self,
        manifest: PluginManifest,
        pipeline: EffectExecutionPipeline | None = None,
        exec_ctx: ExecutionContext | None = None,
    ) -> None:
        self.manifest = manifest
        self.pipeline = pipeline
        self.exec_ctx = exec_ctx

    def on_event(self, event: BaseEvent) -> None:
        """Handles incoming PlanGeneratedEvent, records Gateway audit log, and publishes VerificationResultEvent."""
        if isinstance(event, PlanGeneratedEvent) and self.pipeline and self.exec_ctx:
            outcome = self.run_audit(self.pipeline, self.exec_ctx)

            if self.context and self.context.publish_func and outcome.evidence:
                audit_event = VerificationResultEvent(
                    workflow_id=event.workflow_id,
                    passed=True,
                    rule_id="EMERGENT_MITIGATION_VERIFIED",
                    details={
                        "audit_outcome": outcome.evidence.data.decode("utf-8"),
                        "mitigation_steps": event.steps,
                    },
                    causation_id=event.event_id,
                )
                self.context.publish_func(audit_event)

    def run_audit(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: ExecutionContext,
        execution_attempt_id: str = "att_audit_01",
    ) -> EffectOutcome:
        """Submits an EffectRequest for audit log recording."""
        arguments_bytes = json.dumps(
            {
                "tool_name": "audit_log",
                "arguments": {"invocation_id": ctx.invocation_id},
            }
        ).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="mcp:audit",
            operation="audit_log",
            arguments=arguments_bytes,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)
