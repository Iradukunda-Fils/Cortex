"""
Tasks for AnalyticsPlugin.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from cortex import BaseEvent, BasePlugin, PluginManifest
from cortex.tools.kernel.effect_gateway import EffectOutcome, EffectRequest

if TYPE_CHECKING:
    from cortex.tools.kernel.effect_runtime import EffectExecutionPipeline
    from ..ingestion_plugin.tasks import ExecutionContext


class AnalyticsPlugin(BasePlugin):
    """Plugin responsible for generating analytical report payloads."""

    def __init__(self, manifest: PluginManifest) -> None:
        self.manifest = manifest

    def on_event(self, event: BaseEvent) -> None:
        pass

    def generate_report(
        self,
        pipeline: EffectExecutionPipeline,
        ctx: ExecutionContext,
        size_bytes: int = 8192,
        execution_attempt_id: str = "att_analytics_01",
    ) -> EffectOutcome:
        """Submits an EffectRequest expected to return large evidence (>4KiB auto-spooled to CAS)."""
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
