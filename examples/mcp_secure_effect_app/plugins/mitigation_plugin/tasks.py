"""
Tasks for MitigationPlugin.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from cortex import BaseEvent, BasePlugin, DriverTelemetryEvent, PlanGeneratedEvent, PluginManifest
from cortex.tools.kernel.effect_gateway import EffectOutcome, EffectRequest

if TYPE_CHECKING:
    from cortex.tools.kernel.effect_runtime import EffectExecutionPipeline

    from ..ingestion_plugin.tasks import ExecutionContext


class MitigationPlugin(BasePlugin):
    """Emergent autonomous plugin: reacts to anomalous telemetry and executes Gateway mitigation."""

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
        """Handles DriverTelemetryEvent, checks for anomaly flag, and executes autonomous rebalance."""
        if isinstance(event, DriverTelemetryEvent) and self.pipeline and self.exec_ctx:
            if event.payload.get("anomaly_detected", False):
                outcome = self.execute_mitigation(self.pipeline, self.exec_ctx)

                if self.context and self.context.publish_func and outcome.evidence:
                    plan_event = PlanGeneratedEvent(
                        workflow_id=event.workflow_id,
                        intent_id="intent_mitigate_01",
                        steps=[
                            {
                                "step": 1,
                                "action": "rebalance_resources",
                                "result": outcome.evidence.data.decode("utf-8"),
                            }
                        ],
                        causation_id=event.event_id,
                    )
                    self.context.publish_func(plan_event)

    def execute_mitigation(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: ExecutionContext,
        execution_attempt_id: str = "att_mitigate_01",
    ) -> EffectOutcome:
        """Submits an unprivileged EffectRequest to rebalance resources."""
        arguments_bytes = json.dumps(
            {
                "tool_name": "rebalance_resources",
                "arguments": {"resource_id": ctx.resource_id},
            }
        ).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="mcp:mitigate",
            operation="rebalance_resources",
            arguments=arguments_bytes,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)
