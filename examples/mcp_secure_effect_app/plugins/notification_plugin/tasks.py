"""
Tasks for NotificationPlugin.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from cortex import BaseEvent, BasePlugin, DriverTelemetryEvent, PluginManifest, VerificationResultEvent
from cortex.tools.kernel.effect_gateway import EffectOutcome, EffectRequest

if TYPE_CHECKING:
    from cortex.tools.kernel.effect_runtime import EffectExecutionPipeline
    from ..ingestion_plugin.tasks import ExecutionContext


class NotificationPlugin(BasePlugin):
    """Concurrent fan-out consumer: sends emergency operational alerts when telemetry anomalies are detected."""

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
        """Handles DriverTelemetryEvent concurrently alongside MitigationPlugin, sending an emergency alert."""
        if isinstance(event, DriverTelemetryEvent) and self.pipeline and self.exec_ctx:
            if event.payload.get("anomaly_detected", False):
                outcome = self.send_alert(self.pipeline, self.exec_ctx)

                if self.context and self.context.publish_func and outcome.evidence:
                    alert_result = VerificationResultEvent(
                        workflow_id=event.workflow_id,
                        passed=True,
                        rule_id="ALERT_DISPATCHED",
                        details={"alert_status": outcome.evidence.data.decode("utf-8")},
                        causation_id=event.event_id,
                    )
                    self.context.publish_func(alert_result)

    def send_alert(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: ExecutionContext,
        execution_attempt_id: str = "att_notify_01",
    ) -> EffectOutcome:
        """Submits an unprivileged EffectRequest to dispatch notification alert."""
        arguments_bytes = json.dumps(
            {
                "tool_name": "send_alert",
                "arguments": {"alert_level": "WARNING"},
            }
        ).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="mcp:notify",
            operation="send_alert",
            arguments=arguments_bytes,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)
