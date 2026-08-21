"""
Repository Auditor Executor Plugin

Consumes PlanGeneratedEvent and issues individual CommandIssuedEvent steps.
"""

from typing import cast

from cortex import (
    BaseEvent,
    BasePlugin,
    CommandIssuedEvent,
    PlanGeneratedEvent,
    PluginManifest,
)
from cortex.compat import override

EXECUTOR_MANIFEST = PluginManifest(
    name="auditor-executor",
    version="0.4.0",
    description="Dispatches command events for each audit plan step",
    consumes_events=["PlanGeneratedEvent"],
    produces_events=["CommandIssuedEvent"],
    required_capabilities=["workflow.command.issue"],
)


class AuditorExecutorPlugin(BasePlugin):
    def __init__(self) -> None:
        super().__init__(EXECUTOR_MANIFEST)

    @override
    def on_event(self, event: BaseEvent) -> None:
        match event:
            case PlanGeneratedEvent() if self.context and self.context.has_capability("workflow.command.issue"):
                for step in event.steps:
                    action_val = step.get("action", "unknown")
                    params_val = step.get("params", {})
                    params_dict = cast(dict[str, object], params_val) if isinstance(params_val, dict) else {}

                    cmd = CommandIssuedEvent(
                        workflow_id=event.workflow_id,
                        plan_id=event.plan_id,
                        causation_id=event.event_id,
                        action=str(action_val),
                        parameters=params_dict,
                    )
                    self.context.publish(cmd)

            case _:
                pass
