"""
Audit Plugin Implementation.

Consumes CommandIssuedEvent from RecordServicePlugin to audit execution via Gateway api:audit capability.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict

from cortex import BaseEvent, BasePlugin, CommandIssuedEvent, PluginManifest, VerificationResultEvent
from cortex.tools.kernel.effect_gateway import EffectOutcome, EffectRequest
from examples.secure_external_effect_plugin.plugins.record_plugin.plugin import WorkerContext

if TYPE_CHECKING:
    from cortex.tools.kernel.effect_runtime import EffectExecutionPipeline


class AuditPlugin(BasePlugin):
    """
    Second plugin in the event DAG — consumes CommandIssuedEvent from RecordServicePlugin.

    Event DAG:
        IntentEvent
          → RecordServicePlugin (api:records / lookup)
            → CommandIssuedEvent
              → AuditPlugin (api:audit / log)
                → VerificationResultEvent

    This plugin independently goes through the Gateway authorization boundary
    to record an audit log entry via the 'api:audit' / 'log' capability.
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
        """Handles incoming CommandIssuedEvent by recording an audit entry via the Gateway."""
        if isinstance(event, CommandIssuedEvent) and self.pipeline and self.worker_ctx:
            outcome = self.record_audit(
                pipeline=self.pipeline,
                ctx=self.worker_ctx,
                action=event.action,
                parameters=event.parameters,
            )

            if self.context and self.context.publish_func:
                verification = VerificationResultEvent(
                    workflow_id=event.workflow_id,
                    passed=outcome.evidence is not None,
                    rule_id="AUDIT_TRAIL_VERIFIED",
                    details={
                        "audited_action": event.action,
                        "audit_status": outcome.status.value,
                    },
                    causation_id=event.event_id,
                )
                self.context.publish_func(verification)

    def record_audit(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: WorkerContext,
        action: str = "unknown",
        parameters: Dict[str, Any] | None = None,
        execution_attempt_id: str = "att_audit_01",
    ) -> EffectOutcome:
        """Submits an unprivileged EffectRequest to record an audit log entry."""
        arguments = json.dumps({
            "tool_name": "store_record",
            "arguments": {
                "key": f"audit_{action}",
                "value": json.dumps({"action": action, "params": parameters or {}}),
            },
        }).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="api:audit",
            operation="log",
            arguments=arguments,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)
