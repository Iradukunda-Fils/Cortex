"""
Tasks for AnalyticsPlugin.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from cortex import BaseEvent, BasePlugin, CommandIssuedEvent, DriverTelemetryEvent, PluginManifest
from cortex.tools.kernel.effect_gateway import EffectOutcome, EffectRequest

if TYPE_CHECKING:
    from cortex.tools.kernel.effect_runtime import EffectExecutionPipeline

    from ..ingestion_plugin.tasks import ExecutionContext


class AnalyticsPlugin(BasePlugin):
    """Plugin responsible for generating analytical report payloads."""

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
        """Handles incoming CommandIssuedEvent, generates analytics report, and publishes DriverTelemetryEvent."""
        if isinstance(event, CommandIssuedEvent) and self.pipeline and self.exec_ctx:
            outcome = self.generate_report(self.pipeline, self.exec_ctx, size_bytes=8192)

            if self.context and self.context.publish_func and outcome.evidence:
                # When evidence is spooled (>4KiB), is_reference=True and data contains the CAS ref key.
                # When inline (<4KiB), is_reference=False and data contains the raw evidence bytes.
                evidence_ref = outcome.evidence.data.decode("utf-8") if outcome.evidence.is_reference else ""
                telemetry_event = DriverTelemetryEvent(
                    workflow_id=event.workflow_id,
                    driver_id="analytics_engine_01",
                    status="SUCCESS",
                    payload={
                        "is_reference": outcome.evidence.is_reference,
                        "evidence_ref": evidence_ref,
                        "anomaly_detected": True,
                    },
                    causation_id=event.event_id,
                )
                self.context.publish_func(telemetry_event)

    def generate_report(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: ExecutionContext,
        size_bytes: int = 8192,
        execution_attempt_id: str = "att_analytics_01",
    ) -> EffectOutcome:
        """Submits an EffectRequest expected to return large evidence (>4KiB auto-spooled)."""
        arguments_bytes = json.dumps(
            {
                "tool_name": "generate_report",
                "arguments": {"size_bytes": size_bytes},
            }
        ).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="mcp:report",
            operation="generate_report",
            arguments=arguments_bytes,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)
