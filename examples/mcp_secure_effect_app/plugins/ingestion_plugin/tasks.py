"""
Tasks for IngestionPlugin.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

from cortex import BaseEvent, BasePlugin, CommandIssuedEvent, IntentEvent, PluginManifest
from cortex.tools.kernel.effect_gateway import EffectOutcome, EffectRequest

if TYPE_CHECKING:
    from cortex.tools.kernel.effect_runtime import EffectExecutionPipeline


@dataclass(frozen=True)
class ExecutionContext:
    """Invocation context for sandboxed worker execution."""

    invocation_id: str
    resource_id: str
    lease_epoch: int
    worker_generation: int


class IngestionPlugin(BasePlugin):
    """Plugin responsible for ingesting external payloads via Gateway MCP stdio echo service."""

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
        """Handles incoming IntentEvent, executes Gateway effect, and publishes CommandIssuedEvent."""
        if isinstance(event, IntentEvent) and self.pipeline and self.exec_ctx:
            raw_payload = {"goal": event.goal, "parameters": event.parameters}
            outcome = self.ingest_payload(self.pipeline, self.exec_ctx, raw_payload)

            if self.context and self.context.publish_func and outcome.evidence:
                cmd_event = CommandIssuedEvent(
                    workflow_id=event.workflow_id,
                    plan_id="plan_ingest_01",
                    action="echo",
                    parameters={"ingested_data": outcome.evidence.data.decode("utf-8")},
                    causation_id=event.event_id,
                )
                self.context.publish_func(cmd_event)

    def ingest_payload(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: ExecutionContext,
        raw_data: Dict[str, Any],
        execution_attempt_id: str = "att_ingest_01",
    ) -> EffectOutcome:
        """Submits an unprivileged EffectRequest to ingest external payload."""
        arguments_bytes = json.dumps(
            {
                "tool_name": "echo",
                "arguments": raw_data,
            }
        ).encode("utf-8")

        request = EffectRequest(
            invocation_id=ctx.invocation_id,
            capability="mcp:echo",
            operation="echo",
            arguments=arguments_bytes,
            resource_id=ctx.resource_id,
            lease_epoch=ctx.lease_epoch,
            worker_generation=ctx.worker_generation,
        )

        return pipeline.execute(request, execution_attempt_id=execution_attempt_id)
