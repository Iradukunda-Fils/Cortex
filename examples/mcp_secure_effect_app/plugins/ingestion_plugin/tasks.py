"""
Tasks for IngestionPlugin.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

from cortex import BaseEvent, BasePlugin, PluginManifest
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

    def __init__(self, manifest: PluginManifest) -> None:
        self.manifest = manifest

    def on_event(self, event: BaseEvent) -> None:
        pass

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
